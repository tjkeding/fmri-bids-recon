"""Stage 2: series classification for fmri-bids-recon.

Assigns a :class:`Role` to every :class:`~fmri_bids_recon.sidecar.Series` loaded
from the staging directory. Classification applies ten ordered rules with
first-match-wins semantics, followed by an anatomical NORM/ND twin resolution
pass.
"""

from __future__ import annotations

from enum import StrEnum

import logging

from .errors import AnatSuffixError, NavigatorDropError
from .sidecar import Series, modality_token, description_stem, nifti_stem
from .warnings import graded_warning, SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH

_logger = logging.getLogger(__name__)


class Role(StrEnum):
    """BIDS role assigned to a classified series."""

    BOLD = "bold"
    SBREF = "sbref"
    FMAP_FUNC = "fmap_func"
    FMAP_DWI = "fmap_dwi"
    FMAP_GRE_PHASE = "fmap_gre_phase"
    FMAP_GRE_MAG = "fmap_gre_mag"
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


_SIEMENS_MODALITY_MAP = {
    "FMRI": "FMRI", "DIFFUSION": "DIFFUSION", "M": "MAGNITUDE",
    "P": "PHASE", "ASL": "ASL",
}
_PHILIPS_MODALITY_MAP = {
    "T2": "FMRI", "T1": "MAGNITUDE", "M": "MAGNITUDE",
    "DIFFUSION": "DIFFUSION", "PHASE MAP": "PHASE",
    "PERFUSION": "ASL",
}
_FALLBACK_MODALITY_MAP = {"M": "MAGNITUDE", "P": "PHASE"}


def canonical_modality(s: Series) -> str:
    """Map vendor-specific ImageType[2] to a canonical modality token.

    Canonical vocabulary: FMRI, DIFFUSION, MAGNITUDE, PHASE, ASL,
    SE_EPI (GE context-gated intermediate), EPI, DERIVED, OTHER.
    """
    raw_tok = modality_token(s)

    if s.vendor == "siemens":
        return _SIEMENS_MODALITY_MAP.get(raw_tok, raw_tok)

    if s.vendor == "ge":
        if raw_tok == "EPI":
            if "EP" in s.scanning_sequence and "GR" in s.scanning_sequence:
                return "FMRI"
            if "EP" in s.scanning_sequence and "SE" in s.scanning_sequence:
                return "SE_EPI"
            return "EPI"
        if raw_tok == "OTHER":
            if "EP" in s.scanning_sequence and "SE" in s.scanning_sequence:
                return "SE_EPI"
            return "OTHER"
        return raw_tok

    if s.vendor == "philips":
        return _PHILIPS_MODALITY_MAP.get(raw_tok, raw_tok)

    return _FALLBACK_MODALITY_MAP.get(raw_tok, raw_tok)


def _is_spin_echo(s: Series) -> bool:
    """Detect spin-echo EPI using vendor-dispatched signals.

    Siemens: (1) SE in ScanningSequence, (2) _se in PulseSequenceDetails,
    (3) 'epse' in SequenceName (replaces SS-absent SequenceVariant check).
    GE/Philips/Unknown: SE in ScanningSequence only.
    """
    if s.vendor == "siemens":
        if "SE" in s.scanning_sequence:
            return True
        psd = s.raw.get("PulseSequenceDetails", "")
        if isinstance(psd, str) and "_se" in psd.lower():
            return True
        sn = s.sequence_name or ""
        if "epse" in sn.lower():
            return True
        return False
    return "SE" in s.scanning_sequence


def _is_epi(s: Series) -> bool:
    """Detect EPI acquisition using vendor-appropriate signals.

    Siemens/GE/Unknown: EP in ScanningSequence.
    Philips: layered detection (physics-primary, SequenceName secondary,
    graded_warning fallback).
    """
    if s.vendor in ("siemens", "ge"):
        return "EP" in s.scanning_sequence

    if s.vendor == "philips":
        etl = s.raw.get("EchoTrainLength")
        has_ees = (
            s.raw.get("EffectiveEchoSpacing") is not None
            or s.raw.get("EstimatedEffectiveEchoSpacing") is not None
        )
        if etl is not None and int(etl) > 10 and has_ees:
            return True
        sn = (s.sequence_name or "").lower()
        if any(tok in sn for tok in ("epi", "dwi", "grase")):
            return True
        if has_ees:
            graded_warning(
                _logger, SEVERITY_MEDIUM, "PHILIPS_EPI_INCONCLUSIVE",
                f"Series {s.series_number}: Philips EPI detection inconclusive "
                f"(EchoTrainLength={etl}, SequenceName={s.sequence_name!r}). "
                f"EstimatedEffectiveEchoSpacing present suggests EPI.",
            )
            return True
        return False

    return "EP" in s.scanning_sequence


def _bval_path(s: Series):
    """Return the .bval companion path for a series."""
    return s.nifti_path.parent / (nifti_stem(s.nifti_path) + ".bval")


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


_SCOUT_KEYWORDS = frozenset({"scout", "localizer", "survey", "3-plane", "3plane"})


def _is_epi_bold_physics(s: Series) -> bool:
    return (
        s.mr_acquisition_type == "2D"
        and _is_epi(s)
        and s.n_volumes >= 10
        and not _bval_exists(s)
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify(
    series: list[Series],
) -> tuple[dict[int, Role], list[dict]]:
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
    tuple[dict[int, Role], list[dict]]
        ``(roles, flags)`` where *roles* maps each ``series_number`` to its
        assigned :class:`Role` and *flags* is the (possibly empty) list of
        graded warning dicts with keys: severity, code, message.
    """
    roles: dict[int, Role] = {}
    flags: list[dict] = []

    # ------------------------------------------------------------------
    # Sort chronologically to support SBREF look-ahead (rule 9)
    # ------------------------------------------------------------------
    by_time: list[Series] = sorted(series, key=lambda s: s.acquisition_datetime)
    position_by_sn = {t.series_number: i for i, t in enumerate(by_time)}

    for s in series:
        if s.series_number in roles:
            continue
        tok = canonical_modality(s)

        # Rule 1: DROP_DERIVED
        if s.image_type and s.image_type[0] == "DERIVED":
            roles[s.series_number] = Role.DROP_DERIVED
            continue

        # Rule 2: DROP_SCOUT
        # Signal 1: Siemens DIS2D mosaic scout (negative guard: GRE fieldmaps carry DIS2D)
        _is_gre_fieldmap_candidate = (
            "GR" in s.scanning_sequence
            and ("PHASE" in s.image_type or s.echo_number is not None)
        )
        if (
            "DIS2D" in s.image_type_text
            and s.mr_acquisition_type == "2D"
            and s.multiband_factor is None
            and not _is_gre_fieldmap_candidate
        ):
            roles[s.series_number] = Role.DROP_SCOUT
            continue

        # Signal 2: LOCALIZER token in ImageType (vendor-agnostic)
        if "LOCALIZER" in s.image_type:
            roles[s.series_number] = Role.DROP_SCOUT
            continue

        # Signal 3: description keyword match with physics guard
        desc_lower = s.description.lower()
        if any(kw in desc_lower for kw in _SCOUT_KEYWORDS):
            if s.mr_acquisition_type == "2D" and s.n_volumes <= 3:
                roles[s.series_number] = Role.DROP_SCOUT
                continue

        # Rule 3: DROP_NAVIGATOR
        if s.n_volumes > 1 and tok not in {"FMRI", "DIFFUSION", "SE_EPI"}:
            if _is_epi(s):
                if _is_epi_bold_physics(s):
                    pass
                else:
                    raise NavigatorDropError(
                        f"Series {s.series_number} is multi-volume EPI physics "
                        f"(ImageType[2]={tok!r}, SoftwareVersions={s.software_versions!r}) "
                        f"and would be dropped as a navigator; halting for adjudication.",
                        context={"series_number": s.series_number,
                                 "image_type": list(s.image_type),
                                 "software_versions": s.software_versions})
            else:
                roles[s.series_number] = Role.DROP_NAVIGATOR
                continue

        # Rule 3.5: GRE fieldmap phase image
        if (
            tok == "PHASE"
            and not _is_epi(s)
            and "GR" in s.scanning_sequence
        ):
            roles[s.series_number] = Role.FMAP_GRE_PHASE
            continue

        # Rule 4: T1W / T2W
        if (
            s.mr_acquisition_type == "3D"
            and tok in ("M", "MAGNITUDE")
            and not _is_epi(s)
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

        # Rule 5: single-volume spin-echo EPI (FMAP_FUNC or DWI_SBREF)
        _r5_tok_eligible = (
            tok not in ("DIFFUSION", "SE_EPI")
            or (tok == "SE_EPI"
                and s.raw.get("DiffusionDirectionality") is None
                and not _bval_exists(s))
        )
        if (
            _r5_tok_eligible
            and _is_epi(s)
            and _is_spin_echo(s)
            and "GR" not in s.scanning_sequence
            and s.n_volumes == 1
        ):
            _r5_pos = position_by_sn.get(s.series_number)
            if _r5_pos is not None and _r5_pos + 1 < len(by_time):
                _r5_nxt = by_time[_r5_pos + 1]
                if (
                    description_stem(s.description)
                    == description_stem(_r5_nxt.description)
                    and canonical_modality(_r5_nxt) in ("DIFFUSION", "SE_EPI")
                    and _bval_exists(_r5_nxt)
                ):
                    roles[s.series_number] = Role.DWI_SBREF
                    continue
            roles[s.series_number] = Role.FMAP_FUNC
            continue

        # Rule 6: FMAP_DWI
        if (
            (tok == "DIFFUSION"
             or (tok == "SE_EPI"
                 and (s.raw.get("DiffusionDirectionality") is not None
                      or _bval_exists(s))))
            and "GR" not in s.scanning_sequence
            and s.n_volumes == 1
            and not _has_nonzero_bval(s)
        ):
            roles[s.series_number] = Role.FMAP_DWI
            continue

        # Rule 7: DWI
        if (
            tok in ("DIFFUSION", "SE_EPI")
            and s.image_type
            and s.image_type[0] == "ORIGINAL"
            and _bval_exists(s)
        ):
            roles[s.series_number] = Role.DWI
            continue

        # Rule 8: BOLD
        if (tok == "FMRI" or _is_epi_bold_physics(s)) and s.n_volumes > 1:
            roles[s.series_number] = Role.BOLD
            continue

        # Rule 9: SBRef (functional or diffusion)
        if s.n_volumes == 1 and _is_epi(s):
            pos = position_by_sn.get(s.series_number)
            if pos is not None and pos + 1 < len(by_time):
                nxt = by_time[pos + 1]
                same_stem = description_stem(s.description) == description_stem(nxt.description)
                if same_stem:
                    nxt_tok = canonical_modality(nxt)
                    if (nxt_tok == "FMRI" or _is_epi_bold_physics(nxt)) and nxt.n_volumes > 1:
                        roles[s.series_number] = Role.SBREF
                        continue
                    if nxt_tok in ("DIFFUSION", "SE_EPI") and _bval_exists(nxt):
                        roles[s.series_number] = Role.DWI_SBREF
                        continue

        # Rule 10: UNCLASSIFIED
        roles[s.series_number] = Role.UNCLASSIFIED

    # ------------------------------------------------------------------
    # Anatomical NORM / ND twin resolution pass
    # ------------------------------------------------------------------
    has_norm = any("NORM" in s.image_type_text for s in series)
    if has_norm:
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
                            graded_warning(
                                _logger, SEVERITY_LOW, "UNCLASSIFIED_SERIES",
                                f"Series {s.series_number} ({suffix.value}) has no "
                                f"NORM reconstruction and no ND twin; manual review required.",
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
                            graded_warning(
                                _logger, SEVERITY_LOW, "NAVIGATOR_CANDIDATE",
                                f"Series {s.series_number} ({suffix.value}) has no "
                                f"NORM reconstruction and no ND twin at geometry "
                                f"{geometry}; manual review required.",
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
                            graded_warning(
                                _logger, SEVERITY_MEDIUM, "AMBIGUOUS_CLASSIFICATION",
                                f"Series {s.series_number} ({suffix.value}) is in a "
                                f"paired group at geometry {geometry} but no NORM "
                                f"reconstruction found; manual review required.",
                            )
                        )

    for role_check in (Role.T1W, Role.T2W):
        count = sum(1 for r in roles.values() if r == role_check)
        if count > 1:
            flags.append(
                graded_warning(
                    _logger, SEVERITY_MEDIUM, "DUPLICATE_MODALITY",
                    f"{count} series classified as {role_check.value} after "
                    f"classification; only one expected per session. "
                    f"Manual review recommended.",
                )
            )

    return roles, flags
