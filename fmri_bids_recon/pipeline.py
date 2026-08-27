"""Core pipeline logic for fmri-bids-recon.

Provides run() and BidsReconResult: the programmatic API for executing
the DICOM-to-BIDS reconstruction pipeline without CLI or sys.exit()
dependencies.
"""

from __future__ import annotations

import datetime
import logging
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .config import StudyConfig, save_registry
from .tool_registry import preflight_tool_environments, ToolReport
from .stage1_convert import convert_to_staging
from .sidecar import load_series
from .stage2_classify import classify, Role
from .labels import resolve_labels, RegistryDelta
from .runs import check_volume_counts, assign_run_indices
from .stage3_map import (
    order_series, group_fieldmaps, map_fieldmaps, Mapping,
    group_gre_fieldmaps, map_gre_fieldmaps,
)
from .physio import discover_native_physio, associate_native_physio, write_physio
from .stage4_assemble import assemble
from .stage5_render import render
from .stage6_validate import (
    assert_guards_executed, run_bids_validator, generate_cubids_report, ALL_GUARD_NAMES,
)
from .report import write_conversion_report
from .manifest import read_manifest, update_manifest, should_skip, ManifestEntry
from .deface import deface
from .json_intermediate import dump_intermediate, load_intermediate
from .errors import GuardError
from . import __version__
from .warnings import graded_warning, get_warnings, clear_warnings

logger = logging.getLogger(__name__)


@dataclass
class BidsReconResult:
    status: str
    manifest_path: Path
    output_dir: Path
    warnings: list[dict] = field(default_factory=list)
    participants_processed: list[str] = field(default_factory=list)
    bids_validation_errors: int = 0
    bids_validation_warnings: int = 0
    tool_report: ToolReport | None = None


def _render_findings(findings) -> tuple[int, int]:
    errors = [f for f in findings if f.severity == 'error']
    warnings = [f for f in findings if f.severity == 'warning']
    logger.info('BIDS validation completed: %d error(s), %d warning(s).', len(errors), len(warnings))

    grouped: dict = defaultdict(list)
    for f in findings:
        grouped[(f.severity, f.code)].append(f)

    for severity in ('error', 'warning'):
        level = logging.ERROR if severity == 'error' else logging.WARNING
        for (sev, code), group in grouped.items():
            if sev != severity:
                continue
            locations = [f.location for f in group if f.location]
            msg = group[0].message or code
            if len(locations) > 5:
                location_str = ', '.join(locations[:5]) + f' ... ({len(locations)} total)'
            else:
                location_str = ', '.join(locations)
            logger.log(level, '  [%s] %s: %s (%s)', severity.upper(), code, msg, location_str)

    return len(errors), len(warnings)


def _migrate_manifest(bids_root: Path, new_manifest_path: Path) -> None:
    old_path = bids_root / 'manifest.tsv'
    if old_path.exists() and not new_manifest_path.exists():
        new_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_manifest_path))
        logger.info('Migrated manifest.tsv from %s to %s', old_path, new_manifest_path)


def run(
    config: StudyConfig,
    *,
    strict_versions: bool = False,
    config_path: Path | None = None,
) -> BidsReconResult:
    """Execute the DICOM-to-BIDS reconstruction pipeline.

    Parameters
    ----------
    config : StudyConfig
        Loaded and validated study configuration.
    strict_versions : bool
        When True, enforce exact version matches for Class A tool pins.
    config_path : Path, optional
        Path to the config YAML file (for report provenance). Falls back
        to config.config_path if None.

    Returns
    -------
    BidsReconResult

    Raises
    ------
    GuardError
        On pipeline invariant violations.
    ToolUnavailableError
        If a required external tool is absent.
    ToolVersionError
        If a tool version does not match the pinned version.
    ConfigError
        On config validation errors.
    BidsReconError
        On other pipeline errors.

    Notes
    -----
    This function is not reentrant. The warning framework uses a
    process-global accumulator (``warnings._WARNING_ACCUMULATOR``)
    that is cleared on entry and snapshotted on exit. Concurrent
    in-process calls would interleave on the accumulator, producing
    nondeterministic session status and exit codes. Parallelize at
    the process level (one ``run()`` per process).
    """
    effective_config_path = config_path or config.config_path
    clear_warnings()

    tool_report = preflight_tool_environments(config, strict=strict_versions)
    dcm2niix_status = tool_report.tools.get("dcm2niix")
    version_str = dcm2niix_status.found_version if dcm2niix_status else "unknown"

    bids_root = Path(config.bids_root)

    manifest_path = bids_root / 'derivatives' / 'fmri-bids-recon' / 'manifest.tsv'
    _migrate_manifest(bids_root, manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest(manifest_path)

    merged_registry: dict = dict(config.task_registry)
    combined_guard_log: dict = {}
    participants_processed: list[str] = []

    physio_disabled_logged = False

    # === PHASE 1: CONVERT ALL PARTICIPANTS ===
    for p in config.participants:
        sub, ses = p.sub, p.ses
        if should_skip(manifest, sub, ses):
            logger.info('Skipping already-validated sub=%s ses=%s', sub, ses)
            continue

        staging_dir = Path(config.staging_root) / f'sub-{sub}' / f'ses-{ses}'
        guard_log: dict = {name: False for name in ALL_GUARD_NAMES}

        # Stage 1
        staging = convert_to_staging(p.source, staging_dir, 'dcm2niix')
        all_series, physio_sidecar_paths = load_series(staging.staging_dir)
        guard_log['dcm2niix_version_floor'] = True

        # Stage 2
        roles, review_flags = classify(all_series)
        series_map = {s.series_number: s for s in all_series}
        series_by_role = {sn: (series_map[sn], role) for sn, role in roles.items()}
        guard_log['anat_suffix_physics'] = True

        # Labels
        labels_dict, registry_delta = resolve_labels(series_by_role, config.task_registry)
        guard_log['label_injectivity'] = True
        guard_log['non_empty_labels'] = True
        guard_log['no_label_drift'] = True
        guard_log['no_rename_collision'] = True
        bolds = [(series_map[sn], labels_dict[sn]) for sn, role in roles.items() if role == Role.BOLD]
        surviving, excluded, vol_updates, vol_flags = check_volume_counts(bolds, config.task_registry)
        guard_log['exact_volume_counts'] = True
        review_flags.extend(vol_flags)
        run_indices = assign_run_indices(surviving)

        # Stage 3
        ordered = order_series(all_series)
        fmaps = [(series_map[sn], role) for sn, role in roles.items() if role in (Role.FMAP_FUNC, Role.FMAP_DWI)]
        units, unpaired_fmaps = group_fieldmaps(fmaps, ordered, guard_log)
        excluded_sns = {e.series.series_number for e in excluded}
        targets = [
            (series_map[sn], role)
            for sn, role in roles.items()
            if role in (Role.BOLD, Role.DWI, Role.SBREF, Role.DWI_SBREF)
            and sn not in excluded_sns
        ]
        if not units:
            graded_warning(
                logger, "medium", "NO_FIELDMAP_SERIES",
                "No fieldmap series found; proceeding without fieldmap correction.",
            )
            mapping = Mapping(units=[], unit_to_targets={}, unpaired_fmaps=unpaired_fmaps)
            guard_log["opposite_pe_within_pair"] = True
            guard_log["dir_label_pe_agreement"] = True
            guard_log["fieldmap_target_geometry_match"] = True
            guard_log["pe_axis_target_match"] = True
            guard_log["association_unambiguous"] = True
            guard_log["no_orphan_pairs"] = True
        else:
            mapping = map_fieldmaps(units, targets, ordered, guard_log, unpaired_fmaps=unpaired_fmaps)

        # GRE fieldmap grouping (mutates `roles`: rescued magnitude series are
        # reclassified from UNCLASSIFIED to FMAP_GRE_MAG). Must run before the
        # `unclassified` list is computed below.
        gre_sets, _unassociated_gre_magnitudes = group_gre_fieldmaps(roles, series_map, guard_log)
        gre_sets = map_gre_fieldmaps(gre_sets, targets, guard_log)

        # Physio gate (convert phase)
        physio_pairs: dict = {}
        if config.physio:
            try:
                recordings = discover_native_physio(physio_sidecar_paths)
                bold_series = [series_map[sn] for sn, role in roles.items() if role == Role.BOLD]
                physio_pairs = associate_native_physio(recordings, bold_series)
            except Exception as physio_exc:
                if isinstance(physio_exc, GuardError):
                    raise
                logger.warning('Physio extraction skipped for sub=%s ses=%s: %s', sub, ses, physio_exc)
        elif not physio_disabled_logged:
            logger.info('Physio extraction disabled (config.physio=false); skipping.')
            physio_disabled_logged = True

        combined_guard_log.update(guard_log)

        merged_registry.update(registry_delta.new_entries)
        merged_registry.update(vol_updates)

        intermediate = {
            'roles': roles,
            'labels_dict': labels_dict,
            'run_indices': run_indices,
            'mapping': mapping,
            'excluded': excluded,
            'review_flags': review_flags,
            'physio_pairs': physio_pairs,
            'registry_delta': registry_delta,
            'vol_updates': vol_updates,
            'guard_log': guard_log,
            'version_str': version_str,
            'series_map': series_map,
            'unclassified': [series_map[sn] for sn, role in roles.items() if role == Role.UNCLASSIFIED],
            'gre_sets': gre_sets,
        }
        json_path = staging.staging_dir / f'{sub}_{ses}_intermediate.json'
        dump_intermediate(intermediate, json_path)
        logger.info('convert complete: sub=%s ses=%s series=%d excluded=%d', sub, ses, len(all_series), len(excluded))

    # === PHASE 2: ASSERT GUARDS (before any assembly write) ===
    assert_guards_executed(combined_guard_log)

    # === PHASE 3: ASSEMBLE ALL PARTICIPANTS ===
    for p in config.participants:
        sub, ses = p.sub, p.ses
        staging_dir = Path(config.staging_root) / f'sub-{sub}' / f'ses-{ses}'
        json_path = staging_dir / f'{sub}_{ses}_intermediate.json'
        if not json_path.exists():
            continue
        intermediate = load_intermediate(json_path)

        roles = intermediate['roles']
        labels_dict = intermediate['labels_dict']
        run_indices = intermediate['run_indices']
        mapping_i = intermediate['mapping']
        physio_pairs = intermediate['physio_pairs']
        registry_delta = intermediate.get('registry_delta') or RegistryDelta()
        review_flags = intermediate.get('review_flags', [])
        version_str_i = intermediate.get('version_str', version_str)
        series_map = intermediate['series_map']
        unclassified = intermediate['unclassified']
        excluded = intermediate.get('excluded', [])
        gre_sets = intermediate.get('gre_sets', [])

        result = assemble(roles=roles, series_map=series_map, labels=labels_dict,
                          run_indices=run_indices, mapping=mapping_i, excluded=excluded,
                          unclassified=unclassified, config=config, participant=p,
                          staging_dir=staging_dir, gre_sets=gre_sets,
                          unpaired_fmaps=mapping_i.unpaired_fmaps)

        render(mapping_i, bids_root, sub, ses)

        if config.physio:
            for bold_snum, physio_snum in physio_pairs.items():
                label = labels_dict[bold_snum]
                run_idx = run_indices[bold_snum]
                run_prefix = f'sub-{sub}_ses-{ses}_task-{label}_run-{run_idx:02d}'
                func_dir = bids_root / f'sub-{sub}' / f'ses-{ses}' / 'func'
                write_physio(physio_snum, staging_dir, run_prefix, func_dir)

        new_tasks = {desc: e.label for desc, e in registry_delta.new_entries.items()}

        write_conversion_report(bids_root=bids_root, sub=sub, ses=ses,
            excluded=excluded, unclassified=unclassified,
            new_tasks=new_tasks,
            review_flags=review_flags, mapping=mapping_i,
            patient_id_warnings=result.patient_id_warnings,
            dcm2niix_version=version_str_i, engine_version=__version__,
            config_path=effective_config_path)

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        update_manifest(manifest_path,
            ManifestEntry(sub=sub, ses=ses, status='assembled',
                          timestamp=timestamp, dcm2niix_version=version_str_i))

        participants_processed.append(f"sub-{sub}_ses-{ses}")

    # === PHASE 4: SAVE REGISTRY ===
    config.task_registry.clear()
    config.task_registry.update(merged_registry)
    if effective_config_path is not None:
        save_registry(config, effective_config_path)

    # === PHASE 5: DEFACE ===
    if config.deface:
        deface(config)

    # === PHASE 6: VALIDATE ===
    findings = run_bids_validator(bids_root)
    error_count, warning_count = _render_findings(findings)
    errors_found = [f for f in findings if f.severity == 'error']
    if errors_found:
        graded_warning(
            logger, "high", "BIDS_VALIDATION_ERRORS",
            f"BIDS validation found {len(errors_found)} error(s): "
            f"{'; '.join(f.message for f in errors_found[:3])}"
            + (f" (+{len(errors_found) - 3} more)" if len(errors_found) > 3 else ""),
        )

    if not errors_found:
        manifest = read_manifest(manifest_path)
        for p in config.participants:
            entry = manifest.get((p.sub, p.ses))
            if entry is not None and entry.status == 'assembled':
                timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                update_manifest(manifest_path,
                    ManifestEntry(sub=p.sub, ses=p.ses, status='validated',
                                  timestamp=timestamp, dcm2niix_version=entry.dcm2niix_version))

    # === PHASE 7: CUBIDS ===
    try:
        generate_cubids_report(bids_root, bids_root / 'code' / 'cubids')
    except Exception as cubids_exc:
        logger.warning('cubids report generation failed (non-blocking): %s', cubids_exc)

    all_warnings = get_warnings()
    status = "warning" if any(w["severity"] == "high" for w in all_warnings) else "success"

    return BidsReconResult(
        status=status,
        manifest_path=manifest_path,
        output_dir=bids_root / "derivatives" / "fmri-bids-recon",
        warnings=all_warnings,
        participants_processed=participants_processed,
        bids_validation_errors=error_count,
        bids_validation_warnings=warning_count,
        tool_report=tool_report,
    )
