"""Group-level conversion summary for fmri-bids-recon.

Aggregates per-subject conversion reports into a single plain-text summary
with actionable follow-up instructions for findings requiring review.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_logger = logging.getLogger(__name__)


@dataclass
class ParsedReport:
    """Structured data extracted from a single per-subject conversion report."""

    sub: str
    ses: str
    dcm2niix_version: str
    engine_version: str
    config_path: str
    timestamp: str
    excluded_runs: list[dict] = field(default_factory=list)
    unclassified_series: list[dict] = field(default_factory=list)
    new_tasks: list[dict] = field(default_factory=list)
    review_flags: list[dict] = field(default_factory=list)
    patient_id_ok: bool = True
    patient_id_warnings: list[str] = field(default_factory=list)
    source_filename: str = ""


FOLLOWUP_INSTRUCTIONS: dict[tuple[str, str], str] = {
    # HIGH severity
    ("high", "ABORTED_RUN_DETECTED"): (
        "Verify that the accepted run is the complete acquisition. Open the "
        "per-subject report to confirm which run was kept and which was "
        "excluded. If the excluded run was actually the intended acquisition, "
        "re-run with a corrected registry."
    ),
    ("high", "REGISTRY_VOLUME_MISMATCH"): (
        "This series has a different volume count than previously registered "
        "for this task. In advisory mode, the series was retained but may "
        "represent a protocol change, aborted scan, or cross-subject "
        "inconsistency. Open the per-subject report and compare the observed "
        "vs. expected volume counts. If the mismatch is expected (e.g., "
        "different protocol version), no action is needed. If unexpected, "
        "investigate the source DICOM."
    ),
    ("high", "VOLUME_COUNT_DRIFT"): (
        "This task's volume count was registered from a single run with no "
        "within-session corroboration. The count may be correct, but it could "
        "not be verified against a second run of the same task. Review the "
        "per-subject report to confirm the volume count is plausible for this "
        "task's protocol."
    ),
    ("high", "ANAT_CALIBRATION_DEMOTION"): (
        "A calibration/navigator series was demoted because the anatomical "
        "count exceeded the expected count. This is typically correct "
        "behavior. Verify that the demoted series is not the intended "
        "clinical acquisition by checking its series description in the "
        "per-subject report."
    ),
    ("high", "DUPLICATE_MODALITY"): (
        "After calibration demotion, more anatomical series remain than "
        "expected. Open the per-subject report to identify which series were "
        "retained and manually determine which is the intended acquisition."
    ),
    ("high", "ABSENT_PE_DIRECTION"): (
        "PhaseEncodingDirection is missing from the DICOM metadata for this "
        "fieldmap series. The fieldmap was routed to sourcedata (not included "
        "in the BIDS tree). Check whether dcm2niix failed to extract this "
        "field, or whether the acquisition protocol omitted it."
    ),
    ("high", "ODD_FIELDMAP_COUNT"): (
        "An odd number of fieldmap series were found in a geometry group that "
        "requires opposite-PE pairs. The unpaired series was routed to "
        "sourcedata. Check whether a fieldmap acquisition was interrupted or "
        "whether the protocol includes a single-direction fieldmap by design."
    ),
    ("high", "FIELDMAP_COVERAGE_GAP"): (
        "This functional or diffusion series has no geometry-compatible "
        "fieldmap. Susceptibility distortion correction will not be available "
        "for this series. Check whether fieldmaps were acquired for this "
        "geometry, or whether they were excluded due to pairing issues."
    ),
    ("high", "GRE_CASE_INDETERMINATE"): (
        "A GRE (gradient-echo) fieldmap set could not be classified into a "
        "known BIDS case. The phase/magnitude pairing is ambiguous. Manual "
        "inspection of the DICOM series is required to determine the correct "
        "BIDS representation."
    ),
    ("high", "PATIENT_ID_MISMATCH"): (
        "Multiple distinct PatientID values were found across series for this "
        "subject/session. This may indicate mixed-subject data in the source "
        "directory. This requires immediate investigation: verify that all "
        "DICOM files in this subject's source directory belong to the same "
        "individual."
    ),
    ("high", "BIDS_VALIDATION_ERRORS"): (
        "The BIDS validator reported structural errors in the output dataset. "
        "Open the BIDS validation log to identify and resolve the specific "
        "errors before using this data."
    ),
    ("high", "LABEL_DRIFT_ADVISORY"): (
        "A task label in the registry no longer matches what the pipeline "
        "would derive from the current series description. This may indicate "
        "a protocol rename or a registry entry that was manually edited. "
        "Review the per-subject report to determine whether the existing "
        "registry label should be updated."
    ),
    ("high", "TASK_RENAME_ADVISORY"): (
        "A new series description produces a label that collides with an "
        "existing registry entry from a different description. This may "
        "indicate a protocol change across subjects. Review the per-subject "
        "report and decide whether to merge or distinguish these tasks."
    ),
    # MEDIUM severity
    ("medium", "NO_FIELDMAP_SERIES"): (
        "No fieldmap series were found for this session. Susceptibility "
        "distortion correction will not be available. Verify whether the "
        "protocol was designed without fieldmaps, or whether they were "
        "acquired but failed to classify."
    ),
    ("medium", "DUPLICATE_MODALITY"): (
        "Multiple series were classified as the same anatomical modality. No "
        "expected count was configured, so no demotion was applied. If only "
        "one is needed, set expected_anat_count in the study config."
    ),
    ("medium", "AMBIGUOUS_CLASSIFICATION"): (
        "An anatomical series is in a geometry-paired group but no NORM token "
        "was found in any member. The pipeline could not determine which is "
        "the preferred reconstruction. Manual review of the image quality is "
        "recommended."
    ),
    ("medium", "CALIBRATION_PE_AXIS_MISMATCH"): (
        "A fieldmap's phase-encoding axis does not match any of its expected "
        "target modalities. The series may have been acquired for a different "
        "purpose. Check whether it should be excluded or remapped."
    ),
    ("medium", "CALIBRATION_KEYWORD_MATCH"): (
        "A series matches a calibration keyword but was not demoted "
        "(conditions for demotion were not met). Review the per-subject "
        "report to verify this series is correctly classified."
    ),
    ("medium", "ORPHAN_FIELDMAP_UNIT"): (
        "A fieldmap pair has no functional or diffusion targets to correct. "
        "It was included in the BIDS tree but has an empty IntendedFor "
        "field. This is typically harmless but may indicate a protocol or "
        "geometry mismatch."
    ),
    ("medium", "GRE_MAGNITUDE_MISSING"): (
        "A GRE fieldmap phase series has no geometry-compatible magnitude "
        "partner. The phase map cannot be used for distortion correction "
        "without its magnitude. Check whether the magnitude was acquired and "
        "whether it classified correctly."
    ),
    ("medium", "PHILIPS_EPI_INCONCLUSIVE"): (
        "Philips EPI detection was inconclusive for this series. The pipeline "
        "used a fallback classification. Verify the assigned role in the "
        "per-subject report."
    ),
    # LOW severity
    ("low", "NAVIGATOR_CANDIDATE"): (
        "This series is likely a navigator/setter sequence and was correctly "
        "excluded from the BIDS tree. No follow-up needed unless the series "
        "was an intended clinical acquisition."
    ),
    ("low", "UNCLASSIFIED_SERIES"): (
        "No classification rule matched this series. Check the per-subject "
        "report's Unclassified Series table for the series description. If "
        "this series should have been classified, the classification rules "
        "may need updating."
    ),
}


_HEADER_RE = re.compile(r"^#\s+BIDS Conversion Report:\s+sub-(\S+)\s+ses-(\S+)")
_SECTION_RE = re.compile(r"^##\s+\d+\.\s+")
_PROVENANCE_RE = re.compile(r"^\s*-\s+\*\*(.+?)\*\*:\s*(.+)$")
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
_FLAG_RE = re.compile(r"^-\s+\[(\w+):([A-Z_]+)\]\s+(.+)$")


def _parse_table_rows(lines: list[str]) -> list[list[str]]:
    """Parse Markdown table rows, skipping header and separator lines."""
    rows: list[list[str]] = []
    for line in lines:
        m = _TABLE_ROW_RE.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if cells and all(c.replace("-", "") == "" for c in cells):
            continue
        rows.append(cells)
    if rows:
        rows = rows[1:]
    return rows


def parse_conversion_report(path: Path) -> ParsedReport:
    """Parse a per-subject Markdown conversion report into structured data.

    Parameters
    ----------
    path : Path
        Path to a ``sub-*_ses-*_conversion_report.md`` file.

    Returns
    -------
    ParsedReport
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    sub = ses = ""
    for line in lines:
        m = _HEADER_RE.match(line)
        if m:
            sub, ses = m.group(1), m.group(2)
            break

    sections: dict[int, list[str]] = {}
    current_section = 0
    for line in lines:
        if _SECTION_RE.match(line):
            num_match = re.search(r"(\d+)", line)
            if num_match:
                current_section = int(num_match.group(1))
                sections[current_section] = []
                continue
        if current_section > 0:
            sections.setdefault(current_section, []).append(line)

    dcm2niix_version = engine_version = config_path = timestamp = ""
    provenance_map: dict[str, str] = {}
    for line in sections.get(1, []):
        m = _PROVENANCE_RE.match(line)
        if m:
            provenance_map[m.group(1).strip().lower()] = m.group(2).strip()
    dcm2niix_version = provenance_map.get("dcm2niix version", "")
    engine_version = provenance_map.get("fmri-bids-recon engine version", "")
    config_path = provenance_map.get("config path", "")
    timestamp = provenance_map.get("timestamp", "")

    excluded_runs: list[dict] = []
    sec2 = sections.get(2, [])
    sec2_text = "\n".join(sec2).strip()
    if sec2_text and sec2_text != "None":
        for cells in _parse_table_rows(sec2):
            if len(cells) >= 3:
                excluded_runs.append({
                    "task_label": cells[0],
                    "observed_volumes": cells[1],
                    "expected_volumes": cells[2],
                })

    unclassified_series: list[dict] = []
    sec3 = [l for l in sections.get(3, []) if not l.startswith(">")]
    sec3_text = "\n".join(sec3).strip()
    if sec3_text and sec3_text != "None":
        for cells in _parse_table_rows(sec3):
            if len(cells) >= 3:
                unclassified_series.append({
                    "series_number": cells[0],
                    "description": cells[1],
                    "reason": cells[2],
                })

    new_tasks: list[dict] = []
    sec4 = sections.get(4, [])
    sec4_text = "\n".join(sec4).strip()
    if sec4_text and sec4_text != "None":
        for cells in _parse_table_rows(sec4):
            if len(cells) >= 2:
                new_tasks.append({
                    "description": cells[0],
                    "label": cells[1],
                })

    review_flags: list[dict] = []
    for line in sections.get(5, []):
        m = _FLAG_RE.match(line.strip())
        if m:
            review_flags.append({
                "severity": m.group(1),
                "code": m.group(2),
                "message": m.group(3),
            })

    patient_id_ok = True
    patient_id_warnings: list[str] = []
    sec7 = [l for l in sections.get(7, []) if not l.startswith(">")]
    sec7_text = "\n".join(sec7).strip()
    if sec7_text and "All consistent" not in sec7_text:
        patient_id_ok = False
        for line in sec7:
            stripped = line.strip()
            if stripped.startswith("- "):
                patient_id_warnings.append(stripped[2:])

    return ParsedReport(
        sub=sub,
        ses=ses,
        dcm2niix_version=dcm2niix_version,
        engine_version=engine_version,
        config_path=config_path,
        timestamp=timestamp,
        excluded_runs=excluded_runs,
        unclassified_series=unclassified_series,
        new_tasks=new_tasks,
        review_flags=review_flags,
        patient_id_ok=patient_id_ok,
        patient_id_warnings=patient_id_warnings,
        source_filename=path.name,
    )


def _pad_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format a fixed-width text table with dynamic column widths."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))
    gap = "  "
    header_line = gap.join(h.ljust(w) for h, w in zip(headers, col_widths))
    body_lines: list[str] = []
    for row in rows:
        padded = []
        for i, w in enumerate(col_widths):
            cell = row[i] if i < len(row) else ""
            padded.append(cell.ljust(w))
        body_lines.append(gap.join(padded))
    return header_line + "\n" + "\n".join(body_lines)


def _format_flags_section(
    reports: list[ParsedReport],
    severities: frozenset[str],
) -> str:
    """Format review flags for the given severity levels, grouped by subject."""
    lines: list[str] = []
    any_found = False
    for rpt in reports:
        flags = [f for f in rpt.review_flags if f["severity"] in severities]
        if not flags:
            continue
        any_found = True
        lines.append(f"  sub-{rpt.sub} ses-{rpt.ses}:")
        lines.append("")
        for flag in flags:
            lines.append(f"    [{flag['code']}] {flag['message']}")
            key = (flag["severity"], flag["code"])
            instruction = FOLLOWUP_INSTRUCTIONS.get(key)
            if instruction:
                lines.append(f"    FOLLOW-UP: {instruction}")
            else:
                lines.append(
                    f"    FOLLOW-UP: No follow-up instruction registered for "
                    f"code {flag['code']} at severity {flag['severity']}. "
                    f"Consult the per-subject report for details."
                )
            lines.append("")
    return "\n".join(lines) if any_found else ""


def write_group_summary(
    report_dir: Path,
    engine_version: str,
    dcm2niix_version: str,
    config_path: str,
) -> Path | None:
    """Aggregate per-subject conversion reports into a group summary.

    Parameters
    ----------
    report_dir : Path
        The ``derivatives/fmri-bids-recon/`` directory containing per-subject
        conversion reports.
    engine_version : str
        fmri-bids-recon version string.
    dcm2niix_version : str
        dcm2niix version string.
    config_path : str
        Path to the study configuration file.

    Returns
    -------
    Path or None
        Path to the written group summary file, or ``None`` if no per-subject
        reports were found.
    """
    report_paths = sorted(report_dir.glob("sub-*_ses-*_conversion_report.md"))
    if not report_paths:
        _logger.warning("No per-subject conversion reports found in %s", report_dir)
        return None

    reports = sorted(
        [parse_conversion_report(p) for p in report_paths],
        key=lambda r: (r.sub, r.ses),
    )

    now = datetime.now(timezone.utc)
    ts_filename = now.strftime("%Y%m%d_%H%M%S")
    ts_display = now.isoformat(timespec="seconds") + "Z"
    output_path = report_dir / f"group_conversion_summary_{ts_filename}.txt"

    sep = "=" * 80
    sub_sep = "-" * 80
    lines: list[str] = []

    lines.append(sep)
    lines.append("GROUP CONVERSION SUMMARY")
    lines.append(f"Generated: {ts_display}")
    lines.append(sep)
    lines.append("")

    # Section 1: Run Overview
    lines.append("SECTION 1: RUN OVERVIEW")
    lines.append(sub_sep)
    overview_headers = [
        "Subject", "Session", "Warnings (H/M/L)",
        "Excluded Runs", "Unclassified Series",
    ]
    overview_rows: list[list[str]] = []
    total_h = total_m = total_l = 0
    for rpt in reports:
        h = sum(1 for f in rpt.review_flags if f["severity"] == "high")
        m = sum(1 for f in rpt.review_flags if f["severity"] == "medium")
        low = sum(1 for f in rpt.review_flags if f["severity"] == "low")
        total_h += h
        total_m += m
        total_l += low
        overview_rows.append([
            f"sub-{rpt.sub}",
            f"ses-{rpt.ses}",
            f"{h} / {m} / {low}",
            str(len(rpt.excluded_runs)),
            str(len(rpt.unclassified_series)),
        ])
    lines.append(_pad_table(overview_headers, overview_rows))
    lines.append(sub_sep)
    lines.append(
        f"Total: {len(reports)} subject(s), "
        f"{total_h} high / {total_m} medium / {total_l} low warning(s)"
    )
    lines.append("")

    # Section 2: Action Required
    lines.append("SECTION 2: ACTION REQUIRED")
    lines.append(sub_sep)
    lines.append(
        "High-severity findings requiring follow-up, grouped by subject/session."
    )
    lines.append("")
    high_text = _format_flags_section(reports, frozenset({"high"}))
    if high_text:
        lines.append(high_text)
    else:
        lines.append("  No action required.")
        lines.append("")

    # Section 3: Warnings for Review
    lines.append("SECTION 3: WARNINGS FOR REVIEW")
    lines.append(sub_sep)
    lines.append(
        "Medium and low-severity findings for optional review, "
        "grouped by subject/session."
    )
    lines.append("")
    warn_text = _format_flags_section(reports, frozenset({"medium", "low"}))
    if warn_text:
        lines.append(warn_text)
    else:
        lines.append("  No warnings for review.")
        lines.append("")

    # Section 4: Excluded Runs
    lines.append("SECTION 4: EXCLUDED RUNS")
    lines.append(sub_sep)
    all_excluded: list[list[str]] = []
    for rpt in reports:
        for exc in rpt.excluded_runs:
            all_excluded.append([
                f"sub-{rpt.sub}",
                f"ses-{rpt.ses}",
                exc["task_label"],
                exc["observed_volumes"],
                exc["expected_volumes"],
            ])
    if all_excluded:
        exc_headers = [
            "Subject", "Session", "Task Label",
            "Observed Vols", "Expected Vols",
        ]
        lines.append(_pad_table(exc_headers, all_excluded))
    else:
        lines.append("  No runs were excluded.")
    lines.append("")

    # Section 5: Unclassified Series
    lines.append("SECTION 5: UNCLASSIFIED SERIES")
    lines.append(sub_sep)
    all_unclass: list[list[str]] = []
    for rpt in reports:
        for u in rpt.unclassified_series:
            all_unclass.append([
                f"sub-{rpt.sub}",
                f"ses-{rpt.ses}",
                u["series_number"],
                u["description"],
                u["reason"],
            ])
    if all_unclass:
        unc_headers = [
            "Subject", "Session", "Series #",
            "Description", "Reason",
        ]
        lines.append(_pad_table(unc_headers, all_unclass))
    else:
        lines.append("  No unclassified series.")
    lines.append("")

    # Section 6: Auto-Registered Tasks
    lines.append("SECTION 6: AUTO-REGISTERED TASKS")
    lines.append(sub_sep)
    all_tasks: list[list[str]] = []
    for rpt in reports:
        for t in rpt.new_tasks:
            all_tasks.append([
                f"sub-{rpt.sub}",
                f"ses-{rpt.ses}",
                t["description"],
                t["label"],
            ])
    if all_tasks:
        task_headers = [
            "Subject", "Session", "Series Description", "Assigned Label",
        ]
        lines.append(_pad_table(task_headers, all_tasks))
    else:
        lines.append("  No new tasks were auto-registered.")
    lines.append("")

    # Section 7: Provenance
    lines.append("SECTION 7: PROVENANCE")
    lines.append(sub_sep)
    lines.append(f"Engine version:    {engine_version}")
    lines.append(f"dcm2niix version:  {dcm2niix_version}")
    lines.append(f"Config path:       {config_path}")
    lines.append("")
    lines.append(f"Reports aggregated ({len(reports)} total):")
    for rpt in reports:
        lines.append(f"  - {rpt.source_filename}")
    lines.append(sep)
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    _logger.info("Group conversion summary written to %s", output_path)
    return output_path
