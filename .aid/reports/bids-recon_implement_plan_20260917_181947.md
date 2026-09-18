<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-09-17T18:19:47+00:00" />
  <input_reports>
    <report path="bids-recon_brainstorm_20260917_181615.md" mode="brainstorm" key_items="1" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="brainstorm action item 1 (group_report.py module)">
      <file path="fmri_bids_recon/group_report.py" action="create" />
      <description>Create the group-level conversion summary module. Contains: (1) a ParsedReport dataclass for structured per-subject report data, (2) FOLLOWUP_INSTRUCTIONS dictionary mapping all 21 (severity, code) pairs to plain-language follow-up text, (3) parse_conversion_report() to extract structured data from a per-subject Markdown report, (4) write_group_summary() to glob all per-subject reports, aggregate, and write group_conversion_summary_{timestamp}.txt.</description>
      <spec>
## Module: fmri_bids_recon/group_report.py

### Docstring
"""Group-level conversion summary for fmri-bids-recon.

Aggregates per-subject conversion reports into a single plain-text summary
with actionable follow-up instructions for findings requiring review.
"""

### Imports
from __future__ import annotations
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

### Data structure: ParsedReport

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

Each dict in excluded_runs has keys: task_label (str), observed_volumes (str), expected_volumes (str).
Each dict in unclassified_series has keys: series_number (str), description (str), reason (str).
Each dict in new_tasks has keys: description (str), label (str).
Each dict in review_flags has keys: severity (str), code (str), message (str).

### Dictionary: FOLLOWUP_INSTRUCTIONS

Type: dict[tuple[str, str], str] keyed by (severity_lowercase, CODE_UPPERCASE).

HIGH severity entries (13):
- ("high", "ABORTED_RUN_DETECTED"): "Verify that the accepted run is the complete acquisition. Open the per-subject report to confirm which run was kept and which was excluded. If the excluded run was actually the intended acquisition, re-run with a corrected registry."
- ("high", "REGISTRY_VOLUME_MISMATCH"): "This series has a different volume count than previously registered for this task. In advisory mode, the series was retained but may represent a protocol change, aborted scan, or cross-subject inconsistency. Open the per-subject report and compare the observed vs. expected volume counts. If the mismatch is expected (e.g., different protocol version), no action is needed. If unexpected, investigate the source DICOM."
- ("high", "VOLUME_COUNT_DRIFT"): "This task's volume count was registered from a single run with no within-session corroboration. The count may be correct, but it could not be verified against a second run of the same task. Review the per-subject report to confirm the volume count is plausible for this task's protocol."
- ("high", "ANAT_CALIBRATION_DEMOTION"): "A calibration/navigator series was demoted because the anatomical count exceeded the expected count. This is typically correct behavior. Verify that the demoted series is not the intended clinical acquisition by checking its series description in the per-subject report."
- ("high", "DUPLICATE_MODALITY"): "After calibration demotion, more anatomical series remain than expected. Open the per-subject report to identify which series were retained and manually determine which is the intended acquisition."
- ("high", "ABSENT_PE_DIRECTION"): "PhaseEncodingDirection is missing from the DICOM metadata for this fieldmap series. The fieldmap was routed to sourcedata (not included in the BIDS tree). Check whether dcm2niix failed to extract this field, or whether the acquisition protocol omitted it."
- ("high", "ODD_FIELDMAP_COUNT"): "An odd number of fieldmap series were found in a geometry group that requires opposite-PE pairs. The unpaired series was routed to sourcedata. Check whether a fieldmap acquisition was interrupted or whether the protocol includes a single-direction fieldmap by design."
- ("high", "FIELDMAP_COVERAGE_GAP"): "This functional or diffusion series has no geometry-compatible fieldmap. Susceptibility distortion correction will not be available for this series. Check whether fieldmaps were acquired for this geometry, or whether they were excluded due to pairing issues."
- ("high", "GRE_CASE_INDETERMINATE"): "A GRE (gradient-echo) fieldmap set could not be classified into a known BIDS case. The phase/magnitude pairing is ambiguous. Manual inspection of the DICOM series is required to determine the correct BIDS representation."
- ("high", "PATIENT_ID_MISMATCH"): "Multiple distinct PatientID values were found across series for this subject/session. This may indicate mixed-subject data in the source directory. This requires immediate investigation: verify that all DICOM files in this subject's source directory belong to the same individual."
- ("high", "BIDS_VALIDATION_ERRORS"): "The BIDS validator reported structural errors in the output dataset. Open the BIDS validation log to identify and resolve the specific errors before using this data."
- ("high", "LABEL_DRIFT_ADVISORY"): "A task label in the registry no longer matches what the pipeline would derive from the current series description. This may indicate a protocol rename or a registry entry that was manually edited. Review the per-subject report to determine whether the existing registry label should be updated."
- ("high", "TASK_RENAME_ADVISORY"): "A new series description produces a label that collides with an existing registry entry from a different description. This may indicate a protocol change across subjects. Review the per-subject report and decide whether to merge or distinguish these tasks."

MEDIUM severity entries (8):
- ("medium", "NO_FIELDMAP_SERIES"): "No fieldmap series were found for this session. Susceptibility distortion correction will not be available. Verify whether the protocol was designed without fieldmaps, or whether they were acquired but failed to classify."
- ("medium", "DUPLICATE_MODALITY"): "Multiple series were classified as the same anatomical modality. No expected count was configured, so no demotion was applied. If only one is needed, set expected_anat_count in the study config."
- ("medium", "AMBIGUOUS_CLASSIFICATION"): "An anatomical series is in a geometry-paired group but no NORM token was found in any member. The pipeline could not determine which is the preferred reconstruction. Manual review of the image quality is recommended."
- ("medium", "CALIBRATION_PE_AXIS_MISMATCH"): "A fieldmap's phase-encoding axis does not match any of its expected target modalities. The series may have been acquired for a different purpose. Check whether it should be excluded or remapped."
- ("medium", "CALIBRATION_KEYWORD_MATCH"): "A series matches a calibration keyword but was not demoted (conditions for demotion were not met). Review the per-subject report to verify this series is correctly classified."
- ("medium", "ORPHAN_FIELDMAP_UNIT"): "A fieldmap pair has no functional or diffusion targets to correct. It was included in the BIDS tree but has an empty IntendedFor field. This is typically harmless but may indicate a protocol or geometry mismatch."
- ("medium", "GRE_MAGNITUDE_MISSING"): "A GRE fieldmap phase series has no geometry-compatible magnitude partner. The phase map cannot be used for distortion correction without its magnitude. Check whether the magnitude was acquired and whether it classified correctly."
- ("medium", "PHILIPS_EPI_INCONCLUSIVE"): "Philips EPI detection was inconclusive for this series. The pipeline used a fallback classification. Verify the assigned role in the per-subject report."

LOW severity entries (2):
- ("low", "NAVIGATOR_CANDIDATE"): "This series is likely a navigator/setter sequence and was correctly excluded from the BIDS tree. No follow-up needed unless the series was an intended clinical acquisition."
- ("low", "UNCLASSIFIED_SERIES"): "No classification rule matched this series. Check the per-subject report's Unclassified Series table for the series description. If this series should have been classified, the classification rules may need updating."

### Function: parse_conversion_report(path: Path) -> ParsedReport

Parameters:
- path: Path to a sub-*_ses-*_conversion_report.md file.

Returns: ParsedReport with all fields populated from the parsed Markdown.

Logic:
1. Read the file text. Split into sections by "## N." headers.
2. Extract sub, ses from the "# BIDS Conversion Report: sub-{sub} ses-{ses}" header line using regex r"sub-(\S+)\s+ses-(\S+)".
3. Parse Section 1 (PROVENANCE): extract dcm2niix_version, engine_version, config_path, timestamp from "- **key**: value" lines using regex r"\*\*(.+?)\*\*:\s*(.+)".
4. Parse Section 2 (EXCLUDED RUNS): if content is "None", empty list. Otherwise, parse Markdown table rows (skip header and separator rows). Each row yields {task_label, observed_volumes, expected_volumes}. Sourcedata Path column is present but not needed in the parsed output.
5. Parse Section 3 (UNCLASSIFIED SERIES): skip the "> **Note:**" line. If "None", empty list. Parse table rows into {series_number, description, reason}.
6. Parse Section 4 (NEW TASKS AUTO-REGISTERED): if "None", empty list. Parse table rows into {description, label}.
7. Parse Section 5 (REVIEW FLAGS): if "None", empty list. Parse lines matching r"- \[(\w+):(\w+)\] (.+)" into {severity, code, message}.
8. Section 6 (FIELDMAP MAPPING) and Section 7 (PatientID CROSS-CHECK): Section 6 is informational and not aggregated in the group summary (the per-subject report is the reference for fieldmap details). For Section 7, check for "All consistent"; if not present, extract warning lines as patient_id_warnings and set patient_id_ok = False.
9. Set source_filename = path.name.

### Function: write_group_summary(report_dir: Path, engine_version: str, dcm2niix_version: str, config_path: str) -> Path | None

Parameters:
- report_dir: Path to derivatives/fmri-bids-recon/ directory containing per-subject reports.
- engine_version: fmri-bids-recon version string.
- dcm2niix_version: dcm2niix version string.
- config_path: Path to the study config file (as string).

Returns: Path to the written group summary file, or None if no per-subject reports found.

Logic:
1. Glob report_dir for "sub-*_ses-*_conversion_report.md". Sort by filename for deterministic order.
2. If no reports found, log a warning and return None.
3. Parse each report via parse_conversion_report(). Collect into a list[ParsedReport], sorted by (sub, ses).
4. Generate a UTC timestamp: datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S").
5. Build output_path = report_dir / f"group_conversion_summary_{timestamp}.txt".
6. Build the 7 sections as plain text using the format below.
7. Write via output_path.write_text(content, encoding="utf-8").
8. Log the path.
9. Return output_path.

### Output format (plain text)

Section separator: a line of 80 "=" characters.
Sub-separator: a line of 80 "-" characters.

```
================================================================================
GROUP CONVERSION SUMMARY
Generated: {ISO8601 UTC timestamp}
================================================================================

SECTION 1: RUN OVERVIEW
--------------------------------------------------------------------------------
Subject   Session   Warnings (H/M/L)   Excluded Runs   Unclassified Series
{sub}     {ses}     {h} / {m} / {l}    {n}             {n}
...
--------------------------------------------------------------------------------
Total: {N} subject(s), {H} high / {M} medium / {L} low warning(s)

SECTION 2: ACTION REQUIRED
--------------------------------------------------------------------------------
High-severity findings requiring follow-up, grouped by subject/session.

{If no high-severity flags across all subjects:}
  No action required.

{Otherwise, for each subject/session that has high-severity flags:}
  sub-{sub} ses-{ses}:

    [{CODE}] {message}
    FOLLOW-UP: {instruction from FOLLOWUP_INSTRUCTIONS[(severity, code)]}

    [{CODE}] {message}
    FOLLOW-UP: {instruction}

SECTION 3: WARNINGS FOR REVIEW
--------------------------------------------------------------------------------
Medium and low-severity findings for optional review, grouped by subject/session.

{Same structure as Section 2, but for medium and low severity.}
{If no medium/low flags:}
  No warnings for review.

SECTION 4: EXCLUDED RUNS
--------------------------------------------------------------------------------
{If no excluded runs across all subjects:}
  No runs were excluded.

{Otherwise, fixed-width table:}
Subject   Session   Task Label    Observed Vols   Expected Vols
{sub}     {ses}     {label}       {obs}           {exp}

SECTION 5: UNCLASSIFIED SERIES
--------------------------------------------------------------------------------
{If no unclassified series:}
  No unclassified series.

{Otherwise:}
Subject   Session   Series #   Description                         Reason
{sub}     {ses}     {sn}       {desc}                              {reason}

SECTION 6: AUTO-REGISTERED TASKS
--------------------------------------------------------------------------------
{If no new tasks:}
  No new tasks were auto-registered.

{Otherwise:}
Subject   Session   Series Description              Assigned Label
{sub}     {ses}     {desc}                           {label}

SECTION 7: PROVENANCE
--------------------------------------------------------------------------------
Engine version:    {engine_version}
dcm2niix version:  {dcm2niix_version}
Config path:       {config_path}

Reports aggregated ({N} total):
  - {filename1}
  - {filename2}
  ...
================================================================================
```

Table column widths: use dynamic padding based on the longest value in each column, with a minimum of 2 spaces between columns. Use a helper function _pad_table(headers: list[str], rows: list[list[str]]) -> str that computes column widths and formats the table.
      </spec>
      <dependencies>None</dependencies>
      <risk>low - new file, no existing code modified</risk>
      <rollback>Delete fmri_bids_recon/group_report.py</rollback>
    </change>
    <change id="C2" priority="P0" source_item="brainstorm action item 1 (pipeline.py Phase 8 integration)">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <description>Add Phase 8 to pipeline.run() that calls write_group_summary() after Phase 7 (CUBIDS). Import the function at the top of the file alongside other report imports. Wrap in try/except so a group summary failure does not affect the pipeline's exit code or per-subject data.</description>
      <spec>
### Import addition (top of file, after line 34)

Add after the existing `from .report import write_conversion_report` line:
```python
from .group_report import write_group_summary
```

### Phase 8 insertion (after Phase 7 CUBIDS block, before the `all_warnings = get_warnings()` line)

Insert between the Phase 7 try/except block (lines 396-400) and the `all_warnings = get_warnings()` line (line 402):

```python
    # === PHASE 8: GROUP SUMMARY ===
    try:
        write_group_summary(
            report_dir=bids_root / "derivatives" / "fmri-bids-recon",
            engine_version=__version__,
            dcm2niix_version=version_str,
            config_path=str(effective_config_path) if effective_config_path else "",
        )
    except Exception as group_exc:
        logger.warning('Group summary generation failed (non-blocking): %s', group_exc)
```

The try/except mirrors the Phase 7 CUBIDS pattern: the group summary is a convenience output, not a pipeline invariant. A failure in group summary generation must not alter the exit code or the BidsReconResult.
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - small insertion at end of run() before the return block; wrapped in try/except; no effect on existing pipeline behavior</risk>
      <rollback>Remove the import line and the Phase 8 block from pipeline.py</rollback>
    </change>
  </changes>
  <execution_order>C1, C2</execution_order>
</implement_plan>
