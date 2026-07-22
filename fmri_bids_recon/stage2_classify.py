"""Stage 2: series classification for fmri-bids-recon.

Assigns a :class:`Role` to every :class:`~fmri_bids_recon.sidecar.Series` loaded
from the staging directory. Classification applies ten ordered rules with
first-match-wins semantics, followed by an anatomical NORM/ND twin resolution
pass.
"""

from __future__ import annotations

import re

from enum import StrEnum

from .errors import AnatSuffixError, NavigatorDropError, ReviewFlag
from .sidecar import Series, modality_token


class Role(StrEnum):
    """BIDS role assigned to a classified series."""

    BOLD = "bold"
    SBREF = "sbref"
    FMAP_FUNC = "fmap_func"
    FMAP_DWI = "fmap_dwi"
    DWI = "dwi"
    DWI_SBREF = "dwi_sbref"
    T1W = "t1w"
    T2W = "t2w"
    DROP_DERIVED = "drop_derived"
    DROP_SCOUT = "drop_scout"
    DROP_NAVIGATOR = "drop_navigator"
    DROP_ANAT_ND_T1W = "drop_anat_nd_t1w"
    DROP_ANAT_ND_T2W = "drop_anat_nd_t2w"
    UNCLASSIFIED = "unclassified"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _description_anat_hint(description: str) -> str | None:
    """Extract 't1w' or 't2w' from a series description (case-insensitive).

    Parameters
    ----------
    description : str
        SeriesDescription string.

    Returns
    -------
    str | None
        ``'t1w'``, ``'t2w'``, or ``None`` if neither token is present.
    """
    lower = description.lower()
    if "t1w" in lower:
        return "t1w"
    if "t2w" in lower:
        return "t2w"
    return None


_SBREF_SUFFIX_RE = re.compile(r"[_\s]*sbref\s*$", re.IGNORECASE)


def _description_stem(desc: str) -> str:
    """Strip trailing _SBRef (case-insensitive) and whitespace from a description."""
    return _SBREF_SUFFIX_RE.sub("", desc).lower().strip()


def _is_spin_echo(s: Series) -> bool:
    """Detect spin-echo EPI using multiple signals.

    On Siemens XA30, ScanningSequence='EP' only (no 'SE').
    Checks: (1) SE in scanning_sequence, (2) _se in PulseSequenceDetails,
    (3) SS absent from SequenceVariant.
    """
    if "SE" in s.scanning_sequence:
        return True
    psd = s.raw.get("PulseSequenceDetails", "")
    if isinstance(psd, str) and "_se" in psd.lower():
        return True
    sv_raw = s.raw.get("SequenceVariant", "")
    if isinstance(sv_raw, str):
        sv_tokens = sv_raw.split("\\") if "\\" in sv_raw else [sv_raw]
    elif isinstance(sv_raw, list):
        sv_tokens = sv_raw
    else:
        sv_tokens = []
    if sv_tokens and "SS" not in sv_tokens:
        return True
    return False


def _bval_path(s: Series):
    """Return the .bval companion path for a series."""
    stem = s.nifti_path.name
    for ext in (".nii.gz", ".nii"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    return s.nifti_path.parent / (stem + ".bval")


def _bval_exists(s: Series) -> bool:
    """Return True if a .bval file exists alongside the series NIfTI."""
    return _bval_path(s).exists()


def _has_nonzero_bval(s: Series) -> bool:
    """Return True if the .bval companion exists and contains non-zero values."""
    bp = _bval_path(s)
    if not bp.exists():
        return False
    try:
        vals = bp.read_text().split()
        return any(float(v) > 0 for v in vals if v.strip())
    except (ValueError, OSError):
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify(
    series: list[Series],
) -> tuple[dict[int, Role], list[ReviewFlag]]:
    """Classify each series into a :class:`Role`.

    Rules are evaluated in order; the first matching rule wins.  After the
    initial per-series pass, an anatomical NORM/ND twin resolution pass
    demotes ND reconstructions to ``DROP_ANAT_ND_T1W`` / ``DROP_ANAT_ND_T2W``
    where a NORM partner with identical matrix geometry exists.

    Parameters
    ----------
    series : list[Series]
        Series list as returned by :func:`~fmri_bids_recon.sidecar.load_series`,
        sorted by ``series_number``.

    Returns
    -------
    tuple[dict[int, Role], list[ReviewFlag]]
        ``(roles, flags)`` where *roles* maps each ``series_number`` to its
        assigned :class:`Role` and *flags* is the (possibly empty) list of
        non-blocking :class:`~fmri_bids_recon.errors.ReviewFlag` instances.
    """
    roles: dict[int, Role] = {}
    flags: list[ReviewFlag] = []

    # ------------------------------------------------------------------
    # Sort chronologically to support SBREF look-ahead (rule 9)
    # ------------------------------------------------------------------
    by_time: list[Series] = sorted(series, key=lambda s: s.acquisition_datetime)

    for s in series:
        if s.series_number in roles:
            continue
        tok = modality_token(s)

        # Rule 1: DROP_DERIVED
        if s.image_type and s.image_type[0] == "DERIVED":
            roles[s.series_number] = Role.DROP_DERIVED
            continue

        # Rule 2: DROP_SCOUT
        if (
            "DIS2D" in s.image_type_text
            and s.mr_acquisition_type == "2D"
            and s.multiband_factor is None
        ):
            roles[s.series_number] = Role.DROP_SCOUT
            continue

        # Rule 3: DROP_NAVIGATOR
        if s.n_volumes > 1 and tok not in {"FMRI", "DIFFUSION"}:
            if "EP" in s.scanning_sequence:
                raise NavigatorDropError(
                    f"Series {s.series_number} is multi-volume EPI physics "
                    f"(ImageType[2]={tok!r}, SoftwareVersions={s.software_versions!r}) "
                    f"and would be dropped as a navigator; halting for adjudication.",
                    context={"series_number": s.series_number,
                             "image_type": list(s.image_type),
                             "software_versions": s.software_versions})
            roles[s.series_number] = Role.DROP_NAVIGATOR
            continue

        # Rule 4: T1W / T2W
        if (
            s.mr_acquisition_type == "3D"
            and tok == "M"
            and "EP" not in s.scanning_sequence
        ):
            if s.inversion_time is not None and "GR" in s.scanning_sequence:
                physics_role: Role = Role.T1W
            elif "SE" in s.scanning_sequence and s.inversion_time is None:
                physics_role = Role.T2W
            else:
                roles[s.series_number] = Role.UNCLASSIFIED
                continue

            # Cross-check description hint vs physics verdict
            hint = _description_anat_hint(s.description)
            if hint is not None:
                if hint != physics_role.value:
                    raise AnatSuffixError(
                        f"Physics verdict '{physics_role.value}' disagrees with "
                        f"description hint '{hint}' for series {s.series_number}.",
                        context={
                            "series_number": s.series_number,
                            "description": s.description,
                            "physics_role": physics_role.value,
                            "description_hint": hint,
                            "inversion_time": s.inversion_time,
                            "scanning_sequence": list(s.scanning_sequence),
                        },
                    )

            roles[s.series_number] = physics_role
            continue

        # Rule 5: FMAP_FUNC
        if (
            tok == "FMRI"
            and _is_spin_echo(s)
            and "GR" not in s.scanning_sequence
            and s.n_volumes == 1
        ):
            roles[s.series_number] = Role.FMAP_FUNC
            continue

        # Rule 6: FMAP_DWI
        if (
            tok == "DIFFUSION"
            and "GR" not in s.scanning_sequence
            and s.n_volumes == 1
            and not _has_nonzero_bval(s)
        ):
            roles[s.series_number] = Role.FMAP_DWI
            continue

        # Rule 7: DWI
        if (
            tok == "DIFFUSION"
            and s.image_type
            and s.image_type[0] == "ORIGINAL"
            and _bval_exists(s)
        ):
            roles[s.series_number] = Role.DWI
            continue

        # Rule 8: BOLD
        if tok == "FMRI" and s.n_volumes > 1:
            roles[s.series_number] = Role.BOLD
            continue

        # Rule 9: SBREF
        # A single-volume FMRI whose immediately next series (by
        # acquisition_datetime) with the same description stem is BOLD.
        if tok == "FMRI" and s.n_volumes == 1:
            # Find the next series chronologically
            pos = next(
                (i for i, t in enumerate(by_time) if t.series_number == s.series_number),
                None,
            )
            next_bold = False
            if pos is not None and pos + 1 < len(by_time):
                nxt = by_time[pos + 1]
                # Same description stem: compare lower-cased descriptions
                same_stem = _description_stem(s.description) == _description_stem(nxt.description)
                # The next series must itself eventually be classified BOLD
                # (n_volumes > 1 and FMRI token is sufficient here since we
                # haven't finished classifying; use raw attributes directly)
                nxt_tok = modality_token(nxt)
                if same_stem and nxt_tok == "FMRI" and nxt.n_volumes > 1:
                    next_bold = True

            if next_bold:
                roles[s.series_number] = Role.SBREF
                continue

        # Rule 9b: diffusion single-band reference.
        if tok == "M" and s.n_volumes == 1 and "EP" in s.scanning_sequence:
            pos = next(
                (i for i, t in enumerate(by_time) if t.series_number == s.series_number),
                None,
            )
            next_dwi = False
            if pos is not None and pos + 1 < len(by_time):
                nxt = by_time[pos + 1]
                same_stem = _description_stem(s.description) == _description_stem(nxt.description)
                nxt_tok = modality_token(nxt)
                if same_stem and nxt_tok == "DIFFUSION" and _bval_exists(nxt):
                    next_dwi = True

            if next_dwi:
                roles[s.series_number] = Role.DWI_SBREF
                continue

        # Rule 10: UNCLASSIFIED
        roles[s.series_number] = Role.UNCLASSIFIED

    # ------------------------------------------------------------------
    # Anatomical NORM / ND twin resolution pass
    # ------------------------------------------------------------------
    for suffix, drop_role in (
        (Role.T1W, Role.DROP_ANAT_ND_T1W),
        (Role.T2W, Role.DROP_ANAT_ND_T2W),
    ):
        seen_sn: set[int] = set()
        anat_series: list[Series] = []
        for s in series:
            if s.series_number not in seen_sn and roles.get(s.series_number) == suffix:
                anat_series.append(s)
                seen_sn.add(s.series_number)

        if len(anat_series) < 2:
            # Zero or one series: if the sole series has no NORM, flag it.
            for s in anat_series:
                if "NORM" not in s.image_type_text:
                    flags.append(
                        ReviewFlag(
                            f"Series {s.series_number} ({suffix.value}) has no "
                            f"NORM reconstruction and no ND twin; manual review required.",
                            context={
                                "series_number": s.series_number,
                                "description": s.description,
                                "suffix": suffix.value,
                            },
                        )
                    )
            continue

        # Group by matrix geometry to find paired reconstructions.
        # Key: matrix tuple; value: list of Series with that geometry.
        by_geometry: dict[tuple[int, int, int], list[Series]] = {}
        for s in anat_series:
            by_geometry.setdefault(s.matrix, []).append(s)

        for geometry, group in by_geometry.items():
            if len(group) < 2:
                # Unpaired: emit review flag if no NORM token present.
                s = group[0]
                if "NORM" not in s.image_type_text:
                    flags.append(
                        ReviewFlag(
                            f"Series {s.series_number} ({suffix.value}) has no "
                            f"NORM reconstruction and no ND twin at geometry "
                            f"{geometry}; manual review required.",
                            context={
                                "series_number": s.series_number,
                                "description": s.description,
                                "suffix": suffix.value,
                                "matrix": geometry,
                            },
                        )
                    )
                continue

            # Paired group: promote NORM, demote ND twin.
            norm_members = [s for s in group if "NORM" in s.image_type_text]
            nd_members = [s for s in group if "NORM" not in s.image_type_text]

            if norm_members and nd_members:
                for s in nd_members:
                    roles[s.series_number] = drop_role
            elif not norm_members:
                # All members lack NORM: flag all.
                for s in group:
                    flags.append(
                        ReviewFlag(
                            f"Series {s.series_number} ({suffix.value}) is in a "
                            f"paired group at geometry {geometry} but no NORM "
                            f"reconstruction found; manual review required.",
                            context={
                                "series_number": s.series_number,
                                "description": s.description,
                                "suffix": suffix.value,
                                "matrix": geometry,
                            },
                        )
                    )

    return roles, flags
