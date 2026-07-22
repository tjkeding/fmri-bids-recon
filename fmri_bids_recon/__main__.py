"""Entry point for the fmri-bids-recon pipeline.

Single-command invocation: one config file, one Python command, one positional argument.
Pipeline stages: convert, assemble, deface, validate.

Logging uses field names, series numbers, counts, and derived labels only.
PHI values are never logged.
"""

from __future__ import annotations

import argparse
import datetime
import logging
from .json_intermediate import dump_intermediate, load_intermediate
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from .config import load_config, save_registry
from .versions import assert_dcm2niix_version
from .stage1_convert import convert_to_staging
from .sidecar import load_series
from .stage2_classify import classify, Role
from .labels import resolve_labels
from .runs import check_volume_counts, assign_run_indices
from .stage3_map import order_series, pair_fieldmaps, map_fieldmaps
from .physio import parse_physio_dicom, associate_physio, write_physio
from .stage4_assemble import assemble
from .stage5_render import render
from .stage6_validate import assert_guards_executed, run_bids_validator, generate_cubids_report, ALL_GUARD_NAMES
from .report import write_conversion_report
from .manifest import read_manifest, update_manifest, should_skip, ManifestEntry
from .deface import deface
from .errors import GuardError, ConfigError, ToolUnavailableError, BidsReconError
from . import __version__

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _render_findings(findings) -> None:
    """Log grouped BIDS validation findings by severity and code."""
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


def _migrate_manifest(bids_root: Path, new_manifest_path: Path) -> None:
    """Move manifest.tsv from the BIDS root to the derivatives location if needed."""
    old_path = bids_root / 'manifest.tsv'
    if old_path.exists() and not new_manifest_path.exists():
        new_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_manifest_path))
        logger.info('Migrated manifest.tsv from %s to %s', old_path, new_manifest_path)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fmri-bids-recon",
        description="DICOM-to-BIDS reconstruction pipeline (v{})".format(__version__),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {}".format(__version__),
    )
    parser.add_argument(
        'config',
        metavar='CONFIG',
        help='Path to the study configuration YAML file.',
    )
    return parser


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Single-command pipeline entry point: convert, assemble, deface, validate."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S',
    )
    parser = _build_parser()
    args = parser.parse_args()

    # --- Config ---
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        logger.error('Configuration error: %s', exc)
        sys.exit(2)
    except Exception as exc:
        logger.error('Configuration load failed: %s', exc)
        sys.exit(2)

    # --- Version check ---
    try:
        version_str = assert_dcm2niix_version()
    except Exception as exc:
        logger.error('dcm2niix version check failed: %s', exc)
        sys.exit(2)

    bids_root = Path(config.bids_root)

    # --- Manifest in derivatives ---
    manifest_path = bids_root / 'derivatives' / 'fmri-bids-recon' / 'manifest.tsv'
    _migrate_manifest(bids_root, manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest(manifest_path)

    merged_registry: dict = dict(config.task_registry)
    all_review_flags: list = []
    combined_guard_log: dict = {}

    physio_disabled_logged = False

    try:
        # === PHASE 1: CONVERT ALL PARTICIPANTS ===
        for p in config.participants:
            sub, ses = p.sub, p.ses
            if should_skip(manifest, sub, ses):
                logger.info('Skipping already-validated sub=%s ses=%s', sub, ses)
                continue

            staging_dir = Path(config.staging_root) / f'sub-{sub}' / f'ses-{ses}'

            # Guard log (all-False; stages set True after successful return)
            guard_log: dict = {name: False for name in ALL_GUARD_NAMES}

            # Stage 1
            staging = convert_to_staging(p.source, staging_dir, 'dcm2niix')
            all_series = load_series(staging.staging_dir)
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
            pairs = pair_fieldmaps(fmaps, ordered, guard_log)
            targets = [(series_map[sn], role) for sn, role in roles.items() if role in (Role.BOLD, Role.DWI, Role.SBREF, Role.DWI_SBREF)]
            mapping = map_fieldmaps(pairs, targets, ordered, guard_log)

            # Physio gate (convert phase)
            physio_pairs: dict = {}
            if config.physio:
                try:
                    physio_logs = []
                    for rec in staging.dicom_index.values():
                        if rec.sop_class_uid == '1.2.840.10008.5.1.4.1.1.66':
                            for fp in rec.file_paths:
                                physio_logs.append(parse_physio_dicom(fp))
                    bold_series = [series_map[sn] for sn, role in roles.items() if role == Role.BOLD]
                    physio_pairs = associate_physio(physio_logs, bold_series)
                except Exception as physio_exc:
                    if isinstance(physio_exc, GuardError):
                        raise
                    logger.warning('Physio extraction skipped for sub=%s ses=%s: %s', sub, ses, physio_exc)
            elif not physio_disabled_logged:
                logger.info('Physio extraction disabled (config.physio=false); skipping.')
                physio_disabled_logged = True

            # Guard log + registry accumulation
            combined_guard_log.update(guard_log)

            # registry_delta may be object with .new_entries or a raw dict
            if hasattr(registry_delta, 'new_entries'):
                merged_registry.update(registry_delta.new_entries)
            else:
                merged_registry.update(registry_delta)
            merged_registry.update(vol_updates)
            all_review_flags.extend(review_flags)

            # Serialize intermediate
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
            registry_delta = intermediate.get('registry_delta', {})
            review_flags = intermediate.get('review_flags', [])
            version_str_i = intermediate.get('version_str', version_str)
            series_map = intermediate['series_map']
            unclassified = intermediate['unclassified']
            excluded = intermediate.get('excluded', [])

            result = assemble(roles=roles, series_map=series_map, labels=labels_dict,
                              run_indices=run_indices, mapping=mapping_i, excluded=excluded,
                              unclassified=unclassified, config=config, participant=p,
                              staging_dir=staging_dir)

            render(mapping_i, bids_root, sub, ses)

            # Physio write gate
            if config.physio:
                for bold_snum, log in physio_pairs.items():
                    label = labels_dict[bold_snum]
                    run_idx = run_indices[bold_snum]
                    run_prefix = f'sub-{sub}_ses-{ses}_task-{label}_run-{run_idx:02d}'
                    func_dir = bids_root / f'sub-{sub}' / f'ses-{ses}' / 'func'
                    write_physio(log, run_prefix, func_dir, series_map[bold_snum])

            # registry_delta from the intermediate may be object with .new_entries or raw dict
            if hasattr(registry_delta, 'new_entries'):
                new_tasks = {desc: e.label for desc, e in registry_delta.new_entries.items()}
            else:
                new_tasks = {}

            write_conversion_report(bids_root=bids_root, sub=sub, ses=ses,
                excluded=excluded, unclassified=unclassified,
                new_tasks=new_tasks,
                review_flags=review_flags, mapping=mapping_i,
                patient_id_warnings=result.patient_id_warnings,
                dcm2niix_version=version_str_i, engine_version=version_str_i,
                config_path=Path(args.config))

            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            update_manifest(manifest_path,
                ManifestEntry(sub=sub, ses=ses, status='assembled',
                              timestamp=timestamp, dcm2niix_version=version_str_i))

        # === PHASE 4: SAVE REGISTRY ===
        config.task_registry.clear()
        config.task_registry.update(merged_registry)
        save_registry(config, args.config)

        # === PHASE 5: DEFACE (hardcoded pydeface) ===
        deface(config)

        # === PHASE 6: VALIDATE ===
        findings = run_bids_validator(bids_root)
        _render_findings(findings)
        errors_found = [f for f in findings if f.severity == 'error']

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

        # === EXIT ===
        if errors_found:
            sys.exit(3)
        logger.info('Pipeline complete: bids_root=%s', bids_root)
        sys.exit(0)

    except GuardError as exc:
        logger.error('Pipeline invariant violated: %s', exc, exc_info=True)
        sys.exit(1)
    except ToolUnavailableError as exc:
        logger.error('Tool unavailable, dataset is UNCHECKED: %s', exc)
        sys.exit(4)
    except ConfigError as exc:
        logger.error('Configuration error: %s', exc)
        sys.exit(2)
    except BidsReconError as exc:
        logger.error('Pipeline error: %s', exc)
        sys.exit(2)
    except Exception as exc:
        logger.exception('Unexpected error: %s', exc)
        sys.exit(2)


if __name__ == '__main__':
    main()
