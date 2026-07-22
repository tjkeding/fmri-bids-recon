"""Stage 4: BIDS assembly for fmri-bids-recon.

Copies staged NIfTI/sidecar files into a BIDS-compliant directory tree,
writes JSON sidecars, routes dropped/excluded/unclassified series
to sourcedata/, and upserts dataset-level TSV manifests.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .sidecar import Series, _parse_acquisition_datetime
from .stage2_classify import Role
from .stage3_map import Mapping, FieldmapPair, PE_DIRECTION_TO_LABEL  # noqa: F401
from .config import StudyConfig, ParticipantEntry
from .runs import Excluded
from .labels import RegistryDelta  # noqa: F401
from .tsv import upsert_tsv
from .errors import ReviewFlag, PhaseEncodingError


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class AssemblyResult:
    """Outcome record for one participant/session assembly pass.

    Parameters
    ----------
    bids_files : list[Path]
        Absolute paths to all NIfTI files written under ``bids_root``.
    sourcedata_files : list[Path]
        Absolute paths to all files written under ``sourcedata_root``.
    demographics : dict
        Non-PHI demographic summary (sex, age, wave).
    review_flags : list[ReviewFlag]
        Non-blocking advisory flags raised during assembly.
    patient_id_warnings : list[str]
        Warnings about PatientID inconsistencies (counts only, no values).
    """

    bids_files: list[Path] = field(default_factory=list)
    sourcedata_files: list[Path] = field(default_factory=list)
    demographics: dict = field(default_factory=dict)
    review_flags: list[ReviewFlag] = field(default_factory=list)
    patient_id_warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _nifti_filestem(nifti_path: Path) -> str:
    """Return the bare stem of *nifti_path* with both .nii and .gz removed."""
    name = nifti_path.name
    if name.endswith(".nii.gz"):
        return name[:-7]
    if name.endswith(".nii"):
        return name[:-4]
    return nifti_path.stem


def _normalize_acq_time(raw: dict) -> str:
    """Return a zero-padded ISO-8601 acquisition timestamp, or 'n/a'."""
    val = raw.get('AcquisitionDateTime')
    if val is None:
        return 'n/a'
    try:
        return _parse_acquisition_datetime(val).isoformat()
    except (ValueError, TypeError):
        return 'n/a'


def _write_json(dest: Path, data: dict) -> None:
    """Write *data* as a JSON file at *dest*, creating parent dirs as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def _copy_nifti(series: Series, dest: Path) -> None:
    """Copy the NIfTI at *series.nifti_path* to *dest*, creating dirs as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(series.nifti_path, dest)


def _decimal_age(birth_date_str: str, study_dt: datetime) -> float | None:
    """Compute exact age in decimal years from PatientBirthDate and study datetime.

    Parameters
    ----------
    birth_date_str : str
        DICOM PatientBirthDate string (YYYYMMDD or YYYY-MM-DD).
    study_dt : datetime
        Study acquisition datetime.

    Returns
    -------
    float or None
        Age in decimal years (rounded to 4 places), or None if parsing fails.
    """
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            bd = datetime.strptime(birth_date_str.strip(), fmt)
            delta = study_dt - bd
            return round(delta.days / 365.2425, 4)
        except (ValueError, TypeError):
            continue
    return None


# ---------------------------------------------------------------------------
# Primary assembly function
# ---------------------------------------------------------------------------


def assemble(
    roles: dict[int, Role],
    series_map: dict[int, Series],
    labels: dict[int, str],
    run_indices: dict[int, int],
    mapping: Mapping,
    excluded: list[Excluded],
    unclassified: list[Series],
    config: StudyConfig,
    participant: ParticipantEntry,
    staging_dir: Path,
) -> AssemblyResult:
    """Assemble BIDS outputs for one participant/session.

    Copies staged NIfTI files to a BIDS-compliant tree under
    ``config.bids_root``, writes JSON sidecars, routes
    dropped/excluded/unclassified series to ``config.sourcedata_root``,
    and upserts four dataset-level manifest files.  ``ses-`` is ALWAYS
    emitted, zero-padded to at least two digits as specified by
    ``participant.ses``.

    Parameters
    ----------
    roles : dict[int, Role]
        Mapping of ``series_number`` to classified :class:`~.stage2_classify.Role`.
    series_map : dict[int, Series]
        Mapping of ``series_number`` to :class:`~.sidecar.Series`.
    labels : dict[int, str]
        Mapping of ``series_number`` to BIDS task label (BOLD/SBREF only).
    run_indices : dict[int, int]
        Mapping of ``series_number`` to 1-based run index (BOLD/SBREF only).
    mapping : Mapping
        Validated fieldmap-to-target assignments.
    excluded : list[Excluded]
        BOLD series excluded for volume-count mismatch.
    unclassified : list[Series]
        Series assigned :attr:`~.stage2_classify.Role.UNCLASSIFIED`.
    config : StudyConfig
        Study-level configuration (BIDS root, sourcedata root, etc.).
    participant : ParticipantEntry
        Subject/session identifiers and metadata.
    staging_dir : Path
        dcm2niix staging directory (informational; NIfTI paths are taken
        from ``series.nifti_path``).

    Returns
    -------
    AssemblyResult
        Paths to all written files, demographics summary, and any warnings.
    """
    sub = participant.sub
    ses = participant.ses

    sub_dir = config.bids_root / f"sub-{sub}"
    ses_dir = sub_dir / f"ses-{ses}"

    bids_files: list[Path] = []
    sourcedata_files: list[Path] = []
    review_flags: list[ReviewFlag] = []
    scans_rows: list[dict] = []

    # sourcedata base for this participant/session
    sd_base = config.sourcedata_root / f"sub-{sub}" / f"ses-{ses}"

    # Build reverse lookup: series_number -> (FieldmapPair, member 'a' or 'b')
    fmap_pair_lookup: dict[int, tuple[FieldmapPair, str]] = {}
    for pair in mapping.pairs:
        fmap_pair_lookup[pair.member_a.series_number] = (pair, "a")
        fmap_pair_lookup[pair.member_b.series_number] = (pair, "b")

    # ------------------------------------------------------------------
    # Acquisition-order helpers for run-index disambiguation
    # ------------------------------------------------------------------
    def _acq_sort_key(sn: int) -> tuple:
        raw_dt = series_map[sn].raw.get("AcquisitionDateTime", "")
        try:
            dt = _parse_acquisition_datetime(raw_dt) if raw_dt else None
        except Exception:
            dt = None
        return (dt is None, dt or datetime.min, sn)

    t1w_snums = sorted(
        [sn for sn, r in roles.items() if r == Role.T1W],
        key=_acq_sort_key,
    )
    t2w_snums = sorted(
        [sn for sn, r in roles.items() if r == Role.T2W],
        key=_acq_sort_key,
    )
    anat_run_index: dict[int, int] = {sn: i + 1 for i, sn in enumerate(t1w_snums)}
    anat_run_index.update({sn: i + 1 for i, sn in enumerate(t2w_snums)})

    dwi_snums = sorted(
        [sn for sn, r in roles.items() if r in (Role.DWI, Role.DWI_SBREF)],
        key=_acq_sort_key,
    )
    dwi_run_index: dict[int, int] = {sn: i + 1 for i, sn in enumerate(dwi_snums)}

    # ------------------------------------------------------------------
    # Provenance: copy original staging sidecars to sourcedata
    # ------------------------------------------------------------------
    for snum, series in series_map.items():
        dest_sc = sd_base / "provenance" / series.sidecar_path.name
        dest_sc.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(series.sidecar_path, dest_sc)
        sourcedata_files.append(dest_sc)

    # ------------------------------------------------------------------
    # Per-series BIDS assembly
    # ------------------------------------------------------------------
    for snum, role in roles.items():
        series = series_map[snum]

        if role == Role.T1W:
            anat_dir = ses_dir / "anat"
            anat_dir.mkdir(parents=True, exist_ok=True)
            run_idx = anat_run_index[snum]
            stem = f"sub-{sub}_ses-{ses}_run-{run_idx:02d}_T1w"
            dest = anat_dir / f"{stem}.nii.gz"
            _copy_nifti(series, dest)
            _write_json(anat_dir / f"{stem}.json", series.raw)
            bids_files.append(dest)
            mapping.bids_relative_paths[snum] = dest.relative_to(sub_dir).as_posix()
            scans_rows.append({
                "filename": str(dest.relative_to(ses_dir)),
                "acq_time": _normalize_acq_time(series.raw),
            })

        elif role == Role.T2W:
            anat_dir = ses_dir / "anat"
            anat_dir.mkdir(parents=True, exist_ok=True)
            run_idx = anat_run_index[snum]
            stem = f"sub-{sub}_ses-{ses}_run-{run_idx:02d}_T2w"
            dest = anat_dir / f"{stem}.nii.gz"
            _copy_nifti(series, dest)
            _write_json(anat_dir / f"{stem}.json", series.raw)
            bids_files.append(dest)
            mapping.bids_relative_paths[snum] = dest.relative_to(sub_dir).as_posix()
            scans_rows.append({
                "filename": str(dest.relative_to(ses_dir)),
                "acq_time": _normalize_acq_time(series.raw),
            })

        elif role == Role.BOLD:
            func_dir = ses_dir / "func"
            func_dir.mkdir(parents=True, exist_ok=True)
            task_label = labels[snum]
            run_idx = run_indices[snum]
            stem = f"sub-{sub}_ses-{ses}_task-{task_label}_run-{run_idx:02d}_bold"
            dest = func_dir / f"{stem}.nii.gz"
            _copy_nifti(series, dest)
            data = dict(series.raw)
            data["TaskName"] = labels[snum]
            _write_json(func_dir / f"{stem}.json", data)
            bids_files.append(dest)
            mapping.bids_relative_paths[snum] = dest.relative_to(sub_dir).as_posix()
            scans_rows.append({
                "filename": str(dest.relative_to(ses_dir)),
                "acq_time": _normalize_acq_time(series.raw),
            })

        elif role == Role.SBREF:
            func_dir = ses_dir / "func"
            func_dir.mkdir(parents=True, exist_ok=True)
            task_label = labels[snum]
            # Derive run index from the parent BOLD: next chronological BOLD with same task label
            sbref_key = _acq_sort_key(snum)
            bold_snums_same_task = sorted(
                [sn for sn, r in roles.items() if r == Role.BOLD and labels.get(sn) == task_label],
                key=_acq_sort_key,
            )
            parent_bold_snum = next(
                (sn for sn in bold_snums_same_task if _acq_sort_key(sn) > sbref_key),
                bold_snums_same_task[0] if bold_snums_same_task else None,
            )
            run_idx = run_indices[parent_bold_snum] if parent_bold_snum is not None else 1
            stem = f"sub-{sub}_ses-{ses}_task-{task_label}_run-{run_idx:02d}_sbref"
            dest = func_dir / f"{stem}.nii.gz"
            _copy_nifti(series, dest)
            data = dict(series.raw)
            data["TaskName"] = labels[snum]
            _write_json(func_dir / f"{stem}.json", data)
            bids_files.append(dest)
            mapping.bids_relative_paths[snum] = dest.relative_to(sub_dir).as_posix()
            scans_rows.append({
                "filename": str(dest.relative_to(ses_dir)),
                "acq_time": _normalize_acq_time(series.raw),
            })

        elif role == Role.DWI:
            dwi_dir = ses_dir / "dwi"
            dwi_dir.mkdir(parents=True, exist_ok=True)
            dir_label = PE_DIRECTION_TO_LABEL.get(series.phase_encoding_direction or "")
            if dir_label is None:
                raise PhaseEncodingError(
                    f"Diffusion series {snum} has phase-encoding direction "
                    f"{series.phase_encoding_direction!r}, which does not map to a "
                    f"known BIDS dir- label; refusing to emit dir-UNK.",
                    context={
                        "series_number": snum,
                        "phase_encoding_direction": series.phase_encoding_direction,
                        "role": role.name,
                    },
                )
            run_idx = dwi_run_index[snum]
            stem = f"sub-{sub}_ses-{ses}_dir-{dir_label}_run-{run_idx:02d}_dwi"
            dest = dwi_dir / f"{stem}.nii.gz"
            _copy_nifti(series, dest)
            _write_json(dwi_dir / f"{stem}.json", series.raw)
            # Copy companion .bval / .bvec if present
            src_stem = _nifti_filestem(series.nifti_path)
            for ext in (".bval", ".bvec"):
                src = series.nifti_path.parent / (src_stem + ext)
                if src.exists():
                    shutil.copy2(src, dwi_dir / (stem + ext))
            bids_files.append(dest)
            mapping.bids_relative_paths[snum] = dest.relative_to(sub_dir).as_posix()
            scans_rows.append({
                "filename": str(dest.relative_to(ses_dir)),
                "acq_time": _normalize_acq_time(series.raw),
            })

        elif role == Role.DWI_SBREF:
            dwi_dir = ses_dir / "dwi"
            dwi_dir.mkdir(parents=True, exist_ok=True)
            dir_label = PE_DIRECTION_TO_LABEL.get(series.phase_encoding_direction or "")
            if dir_label is None:
                raise PhaseEncodingError(
                    f"Diffusion series {snum} has phase-encoding direction "
                    f"{series.phase_encoding_direction!r}, which does not map to a "
                    f"known BIDS dir- label; refusing to emit dir-UNK.",
                    context={
                        "series_number": snum,
                        "phase_encoding_direction": series.phase_encoding_direction,
                        "role": role.name,
                    },
                )
            run_idx = dwi_run_index.get(snum, 1)
            stem = f"sub-{sub}_ses-{ses}_dir-{dir_label}_run-{run_idx:02d}_sbref"
            dest = dwi_dir / f"{stem}.nii.gz"
            _copy_nifti(series, dest)
            _write_json(dwi_dir / f"{stem}.json", series.raw)
            bids_files.append(dest)
            mapping.bids_relative_paths[snum] = dest.relative_to(sub_dir).as_posix()
            scans_rows.append({
                "filename": str(dest.relative_to(ses_dir)),
                "acq_time": _normalize_acq_time(series.raw),
            })

        elif role in (Role.FMAP_FUNC, Role.FMAP_DWI):
            if snum not in fmap_pair_lookup:
                sd_dest = sd_base / "unpaired_fmap" / series.nifti_path.name
                sd_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(series.nifti_path, sd_dest)
                sourcedata_files.append(sd_dest)
                review_flags.append(ReviewFlag(
                    f"sub-{sub} ses-{ses}: fieldmap series {snum} has no validated pair; "
                    f"preserved under sourcedata/unpaired_fmap and not placed in fmap/.",
                    {"code": "unpaired_fieldmap"},
                ))
                continue
            pair, member = fmap_pair_lookup[snum]
            fmap_dir = ses_dir / "fmap"
            fmap_dir.mkdir(parents=True, exist_ok=True)
            acq = "func" if role == Role.FMAP_FUNC else "dwi"
            dir_label = pair.dir_a if member == "a" else pair.dir_b
            run_idx = pair.run_index
            stem = (
                f"sub-{sub}_ses-{ses}_acq-{acq}_dir-{dir_label}"
                f"_run-{run_idx:02d}_epi"
            )
            dest = fmap_dir / f"{stem}.nii.gz"
            _copy_nifti(series, dest)
            _write_json(fmap_dir / f"{stem}.json", series.raw)
            bids_files.append(dest)
            mapping.bids_relative_paths[snum] = dest.relative_to(sub_dir).as_posix()
            scans_rows.append({
                "filename": str(dest.relative_to(ses_dir)),
                "acq_time": _normalize_acq_time(series.raw),
            })

        elif role in (Role.DROP_ANAT_ND_T1W, Role.DROP_ANAT_ND_T2W):
            # ND anatomical twin: copy NIfTI to sourcedata/dropped
            sd_dest = sd_base / "dropped" / series.nifti_path.name
            sd_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(series.nifti_path, sd_dest)
            sourcedata_files.append(sd_dest)

        # Role.DROP_DERIVED, DROP_SCOUT, DROP_NAVIGATOR: silently discarded.
        # Role.UNCLASSIFIED: handled below via the dedicated `unclassified` list.

    # ------------------------------------------------------------------
    # Excluded runs -> sourcedata/excluded
    # ------------------------------------------------------------------
    for exc in excluded:
        sd_dest = sd_base / "excluded" / exc.series.nifti_path.name
        sd_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(exc.series.nifti_path, sd_dest)
        sourcedata_files.append(sd_dest)

    # ------------------------------------------------------------------
    # Unclassified series -> sourcedata/unclassified
    # ------------------------------------------------------------------
    for s in unclassified:
        sd_dest = sd_base / "unclassified" / s.nifti_path.name
        sd_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s.nifti_path, sd_dest)
        sourcedata_files.append(sd_dest)

    # ------------------------------------------------------------------
    # Dataset-level files
    # ------------------------------------------------------------------

    # dataset_description.json: create only if absent
    dd_path = config.bids_root / "dataset_description.json"
    if not dd_path.exists():
        config.bids_root.mkdir(parents=True, exist_ok=True)
        _write_json(
            dd_path,
            {
                "Name": config.study_name,
                "BIDSVersion": "1.9.0",
                "DatasetType": "raw",
            },
        )

    # Extract first available raw sidecar for demographic fields
    first_raw: dict = {}
    if series_map:
        first_raw = next(iter(series_map.values())).raw

    sex: str = first_raw.get("PatientSex", "n/a") or "n/a"
    acq_time_raw: str = first_raw.get("AcquisitionDateTime", "n/a") or "n/a"

    # Compute age: prefer exact decimal years from PatientBirthDate
    age_val: str = "n/a"
    birth_date_str: str = first_raw.get("PatientBirthDate", "") or ""
    patient_age_raw = first_raw.get("PatientAge", "") or ""
    study_dt: datetime | None = None

    if acq_time_raw and acq_time_raw != "n/a":
        try:
            study_dt = _parse_acquisition_datetime(acq_time_raw)
        except Exception:
            study_dt = None

    if birth_date_str and study_dt is not None:
        computed = _decimal_age(birth_date_str, study_dt)
        if computed is not None:
            age_val = str(computed)

    if age_val == "n/a" and patient_age_raw:
        # PatientAge is commonly encoded as "025Y"; strip trailing alpha chars
        age_str = str(patient_age_raw).upper().rstrip("YMWD").strip()
        try:
            age_val = str(float(age_str))
        except ValueError:
            age_val = str(patient_age_raw)

    # participants.tsv: upsert by participant_id
    participants_tsv = config.bids_root / "participants.tsv"
    upsert_tsv(
        participants_tsv,
        [{"participant_id": f"sub-{sub}", "sex": sex}],
        "participant_id",
    )

    # sub-{sub}/sub-{sub}_sessions.tsv: upsert by session_id
    sessions_tsv = sub_dir / f"sub-{sub}_sessions.tsv"
    upsert_tsv(
        sessions_tsv,
        [{
            "session_id": f"ses-{ses}",
            "wave": participant.wave,
            "acq_time": _normalize_acq_time(first_raw),
            "age": age_val,
        }],
        "session_id",
    )

    # sub-{sub}/sub-{sub}_sessions.json: column-level sidecar for sessions.tsv
    _write_json(
        sub_dir / f"sub-{sub}_sessions.json",
        {
            "wave": {"Description": "Study wave identifier."},
            "age": {"Description": "Age at scan.", "Units": "years"},
        },
    )

    # ses-{ses}/sub-{sub}_ses-{ses}_scans.tsv: per-session file listing
    if scans_rows:
        scans_tsv = ses_dir / f"sub-{sub}_ses-{ses}_scans.tsv"
        upsert_tsv(scans_tsv, scans_rows, "filename")

    # ------------------------------------------------------------------
    # PatientID cross-check (PHI-safe: counts only, no values emitted)
    # ------------------------------------------------------------------
    patient_id_warnings: list[str] = []
    patient_ids: set[str] = set()
    for snum, series in series_map.items():
        pid = series.raw.get("PatientID")
        if pid is not None:
            patient_ids.add(str(pid))

    if len(patient_ids) > 1:
        patient_id_warnings.append(
            f"sub-{sub}: {len(patient_ids)} distinct PatientID values found "
            f"across {len(series_map)} series. Manual identity review required."
        )

    # Build non-PHI demographics summary
    demographics: dict = {
        "sex": sex,
        "age": age_val,
        "wave": participant.wave,
    }

    return AssemblyResult(
        bids_files=bids_files,
        sourcedata_files=sourcedata_files,
        demographics=demographics,
        review_flags=review_flags,
        patient_id_warnings=patient_id_warnings,
    )
