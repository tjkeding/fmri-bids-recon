"""Conversion report generation for fmri-bids-recon.

Writes a human-readable Markdown report summarising the provenance,
exclusions, unclassified series, fieldmap mapping, and PatientID cross-check
for a single subject/session conversion.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .runs import Excluded
from .sidecar import Series
from .stage3_map import Mapping, FieldmapPair

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_conversion_report(
    bids_root: Path,
    sub: str,
    ses: str,
    excluded: list[Excluded],
    unclassified: list[Series],
    new_tasks: dict[str, str],
    review_flags: list,
    mapping: Mapping,
    patient_id_warnings: list[str],
    dcm2niix_version: str,
    engine_version: str,
    config_path: Path,
) -> Path:
    """Write a human-readable conversion report as a Markdown file.

    The report covers seven sections: provenance, excluded runs, unclassified
    series, auto-registered tasks, review flags, fieldmap mapping, and PatientID
    cross-check.

    Parameters
    ----------
    bids_root : Path
        Root of the BIDS dataset.
    sub : str
        Subject label (without ``sub-`` prefix).
    ses : str
        Session label (without ``ses-`` prefix).
    excluded : list[Excluded]
        Runs excluded due to volume-count mismatches.
    unclassified : list[Series]
        Series that did not match any classification rule.
    new_tasks : dict[str, str]
        Mapping of series description to auto-registered task label.
    review_flags : list
        Collection of ReviewFlag instances.
    mapping : Mapping
        Fieldmap-to-target assignment for all pairs.
    patient_id_warnings : list[str]
        Cross-check warning strings (no PHI values).
    dcm2niix_version : str
        Version string reported by dcm2niix.
    engine_version : str
        Version string of the fmri-bids-recon engine.
    config_path : Path
        Absolute path to the study configuration file used.

    Returns
    -------
    Path
        Absolute path to the written Markdown report file.
    """
    report_dir = bids_root / "derivatives" / "fmri-bids-recon"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"sub-{sub}_ses-{ses}_conversion_report.md"

    lines: list[str] = []

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    lines.append(f"# BIDS Conversion Report: sub-{sub} ses-{ses}")
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 1: PROVENANCE
    # -----------------------------------------------------------------------
    lines.append("## 1. PROVENANCE")
    lines.append("")
    lines.append(f"- **dcm2niix version**: {dcm2niix_version}")
    lines.append(f"- **fmri-bids-recon engine version**: {engine_version}")
    lines.append(f"- **Config path**: {config_path}")
    lines.append(f"- **Timestamp**: {datetime.now(timezone.utc).isoformat(timespec='seconds')}Z")
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 2: EXCLUDED RUNS
    # -----------------------------------------------------------------------
    lines.append("## 2. EXCLUDED RUNS")
    lines.append("")
    if not excluded:
        lines.append("None")
    else:
        lines.append(
            "| Task Label | Observed Volumes | Expected Volumes | Sourcedata Path |"
        )
        lines.append("|---|---|---|---|")
        for exc in excluded:
            src = exc.series.sourcedata_path if hasattr(exc.series, "sourcedata_path") else "N/A"
            lines.append(
                f"| {exc.task_label} | {exc.observed_volumes} | {exc.expected_volumes} | {src} |"
            )
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 3: UNCLASSIFIED SERIES
    # -----------------------------------------------------------------------
    lines.append("## 3. UNCLASSIFIED SERIES")
    lines.append("")
    lines.append(
        "> **Note:** The series listed below did NOT enter the BIDS tree. "
        "No rule matched their acquisition parameters."
    )
    lines.append("")
    if not unclassified:
        lines.append("None")
    else:
        lines.append("| Series Number | Description | No-Match Reason | Sourcedata Path |")
        lines.append("|---|---|---|---|")
        for s in unclassified:
            src = s.sourcedata_path if hasattr(s, "sourcedata_path") else "N/A"
            reason = getattr(s, "no_match_reason", "No classification rule matched")
            lines.append(
                f"| {s.series_number} | {s.description} | {reason} | {src} |"
            )
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 4: NEW TASKS AUTO-REGISTERED
    # -----------------------------------------------------------------------
    lines.append("## 4. NEW TASKS AUTO-REGISTERED")
    lines.append("")
    if not new_tasks:
        lines.append("None")
    else:
        lines.append("| Series Description | Auto-Assigned Task Label |")
        lines.append("|---|---|")
        for description, label in new_tasks.items():
            lines.append(f"| {description} | {label} |")
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 5: REVIEW FLAGS
    # -----------------------------------------------------------------------
    lines.append("## 5. REVIEW FLAGS")
    lines.append("")
    if not review_flags:
        lines.append("None")
    else:
        for flag in review_flags:
            lines.append(f"- {flag}")
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 6: FIELDMAP MAPPING
    # -----------------------------------------------------------------------
    lines.append("## 6. FIELDMAP MAPPING")
    lines.append("")
    if not mapping.pairs:
        lines.append("None")
    else:
        lines.append("| Pair (dir labels, run index) | Target Filenames |")
        lines.append("|---|---|")
        for idx, pair in enumerate(mapping.pairs):
            pair_label = f"dir-{pair.dir_a}/dir-{pair.dir_b}, run-{pair.run_index:02d}"
            targets = mapping.pair_to_targets.get(idx, [])
            if targets:
                target_names = ", ".join(
                    getattr(t, "bids_filename", getattr(t, "description", str(t)))
                    for t in targets
                )
            else:
                target_names = "(no targets)"
            lines.append(f"| {pair_label} | {target_names} |")
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 7: PatientID CROSS-CHECK
    # -----------------------------------------------------------------------
    lines.append("## 7. PatientID CROSS-CHECK")
    lines.append("")
    lines.append(
        "> **Note:** PatientID values are never recorded in this report. "
        "Only consistency warnings are listed."
    )
    lines.append("")
    if not patient_id_warnings:
        lines.append("All consistent")
    else:
        for warning in patient_id_warnings:
            lines.append(f"- {warning}")
    lines.append("")

    # -----------------------------------------------------------------------
    # Write report
    # -----------------------------------------------------------------------
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
