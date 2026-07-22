"""Stage 5: render fieldmap association metadata into BIDS sidecars for fmri-bids-recon.

Writes IntendedFor (subject-relative legacy paths) and B0FieldIdentifier /
B0FieldSource into the sidecar JSON files already produced by stage4_assemble.
Both renderings derive from the same Mapping object and are therefore internally
consistent.
"""

from __future__ import annotations

import json
from pathlib import Path

from .stage3_map import Mapping, FieldmapPair, PE_DIRECTION_TO_LABEL  # noqa: F401


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_sidecar(path: Path) -> dict:
    """Read a JSON sidecar file and return its contents as a dict."""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_sidecar(path: Path, data: dict) -> None:
    """Write a dict back to a JSON sidecar file with 2-space indentation."""
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def _subject_relative_path(bids_root: Path, sub: str, nii_path: Path) -> str:
    """Return the subject-relative path for a NIfTI file.

    The subject-relative path is relative to the subject directory
    (``<bids_root>/sub-<sub>/``), e.g.
    ``ses-01/func/sub-001_ses-01_task-rest_run-01_bold.nii.gz``.

    Parameters
    ----------
    bids_root : Path
        Root of the BIDS dataset.
    sub : str
        Subject label (without the ``sub-`` prefix).
    nii_path : Path
        Absolute path to the NIfTI file within the BIDS tree.

    Returns
    -------
    str
        Subject-relative path string.
    """
    sub_dir = bids_root / f"sub-{sub}"
    return str(nii_path.relative_to(sub_dir))


def _pair_identifier(pair: FieldmapPair) -> str:
    """Generate a stable B0FieldIdentifier for a FieldmapPair.

    Pattern: ``pepolar{modality}{run_index:02d}``
    Examples: ``pepolarfunc01``, ``pepolarfunc02``, ``pepolardwi01``.

    Parameters
    ----------
    pair : FieldmapPair
        The fieldmap pair for which to generate an identifier.

    Returns
    -------
    str
        Stable identifier string.
    """
    return f"pepolar{pair.modality}{pair.run_index:02d}"


def _sidecar_path(nii_path: Path) -> Path:
    """Return the sidecar JSON path corresponding to a NIfTI file path.

    Handles both ``.nii.gz`` and ``.nii`` extensions.

    Parameters
    ----------
    nii_path : Path
        Path to the NIfTI file.

    Returns
    -------
    Path
        Corresponding ``.json`` sidecar path.
    """
    name = nii_path.name
    if name.endswith(".nii.gz"):
        stem = name[: -len(".nii.gz")]
    elif name.endswith(".nii"):
        stem = name[: -len(".nii")]
    else:
        stem = nii_path.stem
    return nii_path.parent / f"{stem}.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render(mapping: Mapping, bids_root: Path, sub: str, ses: str) -> None:
    """Write fieldmap association metadata into existing BIDS sidecar JSON files.

    For each FieldmapPair in ``mapping.pairs`` and its targets from
    ``mapping.pair_to_targets``, this function:

    1. Adds ``IntendedFor`` (subject-relative legacy paths) to each fieldmap
       member's sidecar, listing the NIfTI targets that pair covers.
    2. Adds ``B0FieldIdentifier`` (a list containing the pair's stable identifier)
       to each fieldmap member's sidecar.
    3. Adds ``B0FieldSource`` (a list containing the pair's stable identifier)
       to each target series' sidecar.

    Both renderings originate from the same ``Mapping`` object, ensuring they
    cannot contradict each other.  The renderer only adds fieldmap association
    keys; all other sidecar content produced by stage4_assemble is preserved.

    Parameters
    ----------
    mapping : Mapping
        Complete fieldmap-to-target assignment produced by stage3_map.
    bids_root : Path
        Root of the BIDS dataset.
    sub : str
        Subject label (without the ``sub-`` prefix).
    ses : str
        Session label (without the ``ses-`` prefix).
    """
    sub_dir = bids_root / f"sub-{sub}"

    for pair_idx, pair in enumerate(mapping.pairs):
        targets = mapping.pair_to_targets.get(pair_idx, [])
        identifier = _pair_identifier(pair)

        # Compute subject-relative IntendedFor paths for this pair's targets.
        intended_for: list[str] = []
        for target in targets:
            rel = mapping.bids_relative_paths.get(target.series_number)
            if rel is None:      # target not emitted (e.g. excluded); skip its IntendedFor entry
                continue
            bids_nii = sub_dir / rel
            intended_for.append(_subject_relative_path(bids_root, sub, bids_nii))

        # Update each fieldmap member's sidecar with IntendedFor and
        # B0FieldIdentifier.
        for member in (pair.member_a, pair.member_b):
            member_rel = mapping.bids_relative_paths.get(member.series_number)
            if member_rel is None:      # member not emitted into the BIDS tree; nothing to annotate
                continue
            fmap_nii = sub_dir / member_rel
            fmap_sidecar = _sidecar_path(fmap_nii)

            data = _read_sidecar(fmap_sidecar)
            data["IntendedFor"] = intended_for
            data["B0FieldIdentifier"] = [identifier]
            _write_sidecar(fmap_sidecar, data)

        # Update each target's sidecar with B0FieldSource.
        for target in targets:
            rel = mapping.bids_relative_paths.get(target.series_number)
            if rel is None:
                continue
            bids_nii = sub_dir / rel
            target_sidecar = _sidecar_path(bids_nii)

            data = _read_sidecar(target_sidecar)
            data["B0FieldSource"] = [identifier]
            _write_sidecar(target_sidecar, data)
