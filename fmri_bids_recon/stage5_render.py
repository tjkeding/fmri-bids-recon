"""Stage 5: render fieldmap association metadata into BIDS sidecars for fmri-bids-recon.

Writes IntendedFor (subject-relative legacy paths) and B0FieldIdentifier /
B0FieldSource into the sidecar JSON files already produced by stage4_assemble.
Both renderings derive from the same Mapping object and are therefore internally
consistent.
"""

from __future__ import annotations

import json
from pathlib import Path

from .sidecar import nifti_stem
from .stage3_map import Mapping, FieldmapUnit


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


def _unit_identifier(unit: FieldmapUnit) -> str:
    """Generate a stable B0FieldIdentifier for a FieldmapUnit.

    Pattern: ``pepolar{modality}{run_index:02d}``
    Examples: ``pepolarfunc01``, ``pepolarfunc02``, ``pepolardwi01``.

    Parameters
    ----------
    unit : FieldmapUnit
        The fieldmap unit for which to generate an identifier.

    Returns
    -------
    str
        Stable identifier string.
    """
    return f"pepolar{unit.modality}{unit.run_index:02d}"


def _sidecar_path(nii_path: Path) -> Path:
    """Return the sidecar JSON path corresponding to a NIfTI file path."""
    return nii_path.parent / f"{nifti_stem(nii_path)}.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render(mapping: Mapping, bids_root: Path, sub: str, ses: str) -> None:
    """Write fieldmap association metadata into existing BIDS sidecar JSON files.

    For each FieldmapUnit in ``mapping.units`` and its targets from
    ``mapping.unit_to_targets``, this function:

    1. Adds ``IntendedFor`` (subject-relative legacy paths) to each fieldmap
       member's sidecar, listing the NIfTI targets that unit covers.
    2. Adds ``B0FieldIdentifier`` (a list containing the unit's stable identifier)
       to each fieldmap member's sidecar.
    3. Adds ``B0FieldSource`` (a list containing the unit's stable identifier)
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

    for unit_idx, unit in enumerate(mapping.units):
        targets = mapping.unit_to_targets.get(unit_idx, [])
        identifier = _unit_identifier(unit)

        # Compute subject-relative IntendedFor paths for this unit's targets.
        intended_for: list[str] = []
        for target in targets:
            rel = mapping.bids_relative_paths.get(target.series_number)
            if rel is None:      # target not emitted (e.g. excluded); skip its IntendedFor entry
                continue
            bids_nii = sub_dir / rel
            intended_for.append(_subject_relative_path(bids_root, sub, bids_nii))

        # Update each fieldmap member's sidecar with IntendedFor and
        # B0FieldIdentifier.
        for member in unit.members:
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
