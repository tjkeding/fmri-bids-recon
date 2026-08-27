"""Stage 4: BIDS assembly for fmri-bids-recon.

Copies staged NIfTI/sidecar files into a BIDS-compliant directory tree,
writes JSON sidecars, routes dropped/excluded/unclassified series
to sourcedata/, and upserts dataset-level TSV manifests.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_logger = logging.getLogger(__name__)

from .sidecar import Series, _parse_acquisition_datetime, nifti_stem
from .stage2_classify import Role
from .stage3_map import Mapping, FieldmapUnit, GREFieldmapSet, PE_DIRECTION_TO_LABEL
from .config import StudyConfig, ParticipantEntry
from .runs import Excluded
from .tsv import upsert_tsv
from .errors import PhaseEncodingError, GuardError
from .warnings import graded_warning, SEVERITY_HIGH


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
    review_flags : list[dict]
        Graded warning dicts with keys: severity, code, message.
    patient_id_warnings : list[str]
        Warnings about PatientID inconsistencies (counts only, no values).
    """

    bids_files: list[Path] = field(default_factory=list)
    sourcedata_files: list[Path] = field(default_factory=list)
    demographics: dict = field(default_factory=dict)
    review_flags: list[dict] = field(default_factory=list)
    patient_id_warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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
    gre_sets: list[GREFieldmapSet],
    unpaired_fmaps: list[Series],
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
    gre_sets : list[GREFieldmapSet]
        GRE (gradient-echo) fieldmap sets from stage3_map.group_gre_fieldmaps /
        map_gre_fieldmaps, with targets already assigned.
    unpaired_fmaps : list[Series]
        SE-EPI fieldmap series that could not be paired (absent PE direction
        or odd-count remainder; CR F3/F7), from
        ``mapping.unpaired_fmaps``. Routed to sourcedata/unpaired_fmap.

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
    review_flags: list[dict] = []
    scans_rows: list[dict] = []

    # sourcedata base for this participant/session
    sd_base = config.sourcedata_root / f"sub-{sub}" / f"ses-{ses}"

    # Build reverse lookup: series_number -> (FieldmapUnit, member index)
    fmap_unit_lookup: dict[int, tuple[FieldmapUnit, int]] = {}
    for unit in mapping.units:
        for member_idx, member in enumerate(unit.members):
            fmap_unit_lookup[member.series_number] = (unit, member_idx)

    unpaired_sns: set[int] = {s.series_number for s in unpaired_fmaps}

    def _emit_series(series, subdir, stem, *, json_data=None, companions=()):
        """Write one series' NIfTI + JSON (+ optional companions) into the BIDS tree.

        Shared epilogue for every per-role emission site: creates ``subdir``,
        copies the NIfTI, writes the JSON sidecar (``series.raw`` unless
        ``json_data`` overrides it), copies any ``companions`` extensions
        (e.g. ``.bval``/``.bvec``) that exist alongside the source NIfTI, and
        records the output in ``bids_files``, ``mapping.bids_relative_paths``,
        and ``scans_rows``. Per-role guards (phase-encoding validation,
        fieldmap unit lookup) run in the caller before this is invoked.
        """
        subdir.mkdir(parents=True, exist_ok=True)
        dest = subdir / f"{stem}.nii.gz"
        _copy_nifti(series, dest)
        _write_json(subdir / f"{stem}.json",
                    json_data if json_data is not None else series.raw)
        for ext in companions:
            src = series.nifti_path.parent / (nifti_stem(series.nifti_path) + ext)
            if src.exists():
                shutil.copy2(src, subdir / (stem + ext))
        bids_files.append(dest)
        mapping.bids_relative_paths[series.series_number] = (
            dest.relative_to(sub_dir).as_posix()
        )
        scans_rows.append({
            "filename": str(dest.relative_to(ses_dir)),
            "acq_time": _normalize_acq_time(series.raw),
        })

    def _write_gre_output(series, suffix, run_idx):
        _emit_series(series, ses_dir / "fmap",
                     f"sub-{sub}_ses-{ses}_run-{run_idx:02d}_{suffix}")

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
            run_idx = anat_run_index[snum]
            _emit_series(series, ses_dir / "anat",
                         f"sub-{sub}_ses-{ses}_run-{run_idx:02d}_T1w")

        elif role == Role.T2W:
            run_idx = anat_run_index[snum]
            _emit_series(series, ses_dir / "anat",
                         f"sub-{sub}_ses-{ses}_run-{run_idx:02d}_T2w")

        elif role == Role.BOLD:
            task_label = labels[snum]
            run_idx = run_indices[snum]
            data = dict(series.raw)
            data["TaskName"] = labels[snum]
            _emit_series(series, ses_dir / "func",
                         f"sub-{sub}_ses-{ses}_task-{task_label}_run-{run_idx:02d}_bold",
                         json_data=data)

        elif role == Role.SBREF:
            task_label = labels[snum]
            sbref_key = _acq_sort_key(snum)
            bold_snums_same_task = sorted(
                [sn for sn, r in roles.items()
                 if r == Role.BOLD and labels.get(sn) == task_label],
                key=_acq_sort_key,
            )
            parent_bold_snum = next(
                (sn for sn in bold_snums_same_task
                 if _acq_sort_key(sn) > sbref_key),
                bold_snums_same_task[0] if bold_snums_same_task else None,
            )
            run_idx = (run_indices[parent_bold_snum]
                       if parent_bold_snum is not None else 1)
            data = dict(series.raw)
            data["TaskName"] = labels[snum]
            _emit_series(series, ses_dir / "func",
                         f"sub-{sub}_ses-{ses}_task-{task_label}_run-{run_idx:02d}_sbref",
                         json_data=data)

        elif role == Role.DWI:
            dir_label = PE_DIRECTION_TO_LABEL.get(series.phase_encoding_direction or "")
            if dir_label is None:
                raise PhaseEncodingError(
                    f"Diffusion series {snum} has phase-encoding direction "
                    f"{series.phase_encoding_direction!r}, which does not "
                    f"map to a known BIDS dir- label; refusing to emit "
                    f"dir-UNK.",
                    context={
                        "series_number": snum,
                        "phase_encoding_direction":
                            series.phase_encoding_direction,
                        "role": role.name,
                    },
                )
            run_idx = dwi_run_index[snum]
            _emit_series(
                series, ses_dir / "dwi",
                f"sub-{sub}_ses-{ses}_dir-{dir_label}_run-{run_idx:02d}_dwi",
                companions=(".bval", ".bvec"),
            )

        elif role == Role.DWI_SBREF:
            dir_label = PE_DIRECTION_TO_LABEL.get(series.phase_encoding_direction or "")
            if dir_label is None:
                raise PhaseEncodingError(
                    f"Diffusion series {snum} has phase-encoding direction "
                    f"{series.phase_encoding_direction!r}, which does not "
                    f"map to a known BIDS dir- label; refusing to emit "
                    f"dir-UNK.",
                    context={
                        "series_number": snum,
                        "phase_encoding_direction":
                            series.phase_encoding_direction,
                        "role": role.name,
                    },
                )
            run_idx = dwi_run_index.get(snum, 1)
            _emit_series(
                series, ses_dir / "dwi",
                f"sub-{sub}_ses-{ses}_dir-{dir_label}_run-{run_idx:02d}_sbref",
            )

        elif role in (Role.FMAP_FUNC, Role.FMAP_DWI):
            if snum not in fmap_unit_lookup:
                if snum in unpaired_sns:
                    continue
                raise GuardError(
                    f"Fieldmap series {snum} (role={role.name}) is absent from "
                    f"both the paired-unit lookup and the unpaired-fieldmap "
                    f"list; this indicates a wiring defect in the grouping "
                    f"stage.",
                    context={
                        "guard": "fieldmap_pair_complete",
                        "series_number": snum,
                        "role": role.name,
                    },
                )
            unit, member_idx = fmap_unit_lookup[snum]
            if unit.mode == "single":
                # Structurally supported by FieldmapUnit but not currently
                # produced by group_fieldmaps(); route defensively rather
                # than emit a malformed dir- entity from a lone member.
                sd_dest = sd_base / "unpaired_fmap" / series.nifti_path.name
                sd_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(series.nifti_path, sd_dest)
                sourcedata_files.append(sd_dest)
                continue
            fmap_dir = ses_dir / "fmap"
            acq = "func" if role == Role.FMAP_FUNC else "dwi"
            dir_label = PE_DIRECTION_TO_LABEL[unit.dir_labels[member_idx]]
            run_idx = unit.run_index
            _emit_series(
                series, fmap_dir,
                f"sub-{sub}_ses-{ses}_acq-{acq}_dir-{dir_label}"
                f"_run-{run_idx:02d}_epi",
            )

        elif role in (Role.DROP_ANAT_ND_T1W, Role.DROP_ANAT_ND_T2W):
            # ND anatomical twin: copy NIfTI to sourcedata/dropped
            sd_dest = sd_base / "dropped" / series.nifti_path.name
            sd_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(series.nifti_path, sd_dest)
            sourcedata_files.append(sd_dest)

        # Role.DROP_DERIVED, DROP_SCOUT, DROP_NAVIGATOR, DROP_CALIBRATION:
        # silently discarded.
        # Role.UNCLASSIFIED: handled below via the dedicated `unclassified` list.
        # Role.FMAP_GRE_PHASE, FMAP_GRE_MAG: handled set-wise by the dedicated
        # GRE fieldmap assembly block below, not per-series.

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
    # Unpaired SE-EPI fieldmaps -> sourcedata/unpaired_fmap (CR F3, CR F7)
    # ------------------------------------------------------------------
    for s in unpaired_fmaps:
        sd_dest = sd_base / "unpaired_fmap" / s.nifti_path.name
        sd_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s.nifti_path, sd_dest)
        sourcedata_files.append(sd_dest)

    # ------------------------------------------------------------------
    # GRE fieldmap assembly (BIDS Cases 1-3; CR F5)
    # ------------------------------------------------------------------
    for gs in gre_sets:
        if gs.bids_case == 0:
            # Indeterminate: route all series to sourcedata/unclassified.
            for s in (*gs.phase_series, *gs.magnitude_series):
                sd_dest = sd_base / "unclassified" / s.nifti_path.name
                sd_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s.nifti_path, sd_dest)
                sourcedata_files.append(sd_dest)
            continue

        if gs.bids_case == 1:
            _write_gre_output(gs.phase_series[0], "phasediff", gs.run_index)
            if len(gs.magnitude_series) >= 1:
                _write_gre_output(gs.magnitude_series[0], "magnitude1", gs.run_index)
            if len(gs.magnitude_series) >= 2:
                _write_gre_output(gs.magnitude_series[1], "magnitude2", gs.run_index)

        elif gs.bids_case == 2:
            _write_gre_output(gs.phase_series[0], "phase1", gs.run_index)
            _write_gre_output(gs.phase_series[1], "phase2", gs.run_index)
            if len(gs.magnitude_series) >= 1:
                _write_gre_output(gs.magnitude_series[0], "magnitude1", gs.run_index)
            if len(gs.magnitude_series) >= 2:
                _write_gre_output(gs.magnitude_series[1], "magnitude2", gs.run_index)

        elif gs.bids_case == 3:
            _write_gre_output(gs.phase_series[0], "fieldmap", gs.run_index)
            if len(gs.magnitude_series) >= 1:
                _write_gre_output(gs.magnitude_series[0], "magnitude", gs.run_index)

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
    patient_ids: set[str] = set()
    for snum, series in series_map.items():
        pid = series.raw.get("PatientID")
        if pid is not None:
            patient_ids.add(str(pid))

    if len(patient_ids) > 1:
        graded_warning(
            _logger, SEVERITY_HIGH, "PATIENT_ID_MISMATCH",
            f"sub-{sub}: {len(patient_ids)} distinct PatientID values found "
            f"across {len(series_map)} series. Manual identity review required.",
            user_facing=True,
        )
        raise GuardError(
            f"sub-{sub}: {len(patient_ids)} distinct PatientID values found "
            f"across {len(series_map)} series. Halting: possible identity mix-up.",
            context={
                "guard": "patient_id_unique",
                "sub": sub,
                "n_patient_ids": len(patient_ids),
                "n_series": len(series_map),
            },
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
        patient_id_warnings=[],
    )
