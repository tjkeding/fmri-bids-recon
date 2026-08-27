<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-18T14:30:00Z" />
  <input_reports>
    <report path="bids-recon_brainstorm_20260818_140000.md" mode="brainstorm" key_items="13" />
  </input_reports>

  <architectural_note>
    The brainstorm report specified adding guard names `fieldmap_pair_complete` and `patient_id_unique` to `ALL_GUARD_NAMES` in `stage6_validate.py` for the two new halt conditions. This tech spec deviates from that specification for an architectural reason:

    The pipeline's guard architecture has two layers:
    - PHASE 1 guards: tracked in `guard_log`, verified by `assert_guards_executed()` in PHASE 2 (before any BIDS files are written to disk)
    - PHASE 3 checks: self-enforcing exceptions raised inline during assembly

    The UNPAIRED_FIELDMAP and PATIENT_ID checks run inside `assemble()` (PHASE 3), which executes AFTER the meta-guard assertion (PHASE 2). Adding their names to `ALL_GUARD_NAMES` would cause the meta-guard to report them as "not executed" before assembly even starts, producing a false positive. The correct pattern is to raise `GuardError` directly from the PHASE 3 code path; the exception propagates to `main()` and maps to exit code 1 identically to a PHASE 1 guard failure.

    VOLUME_COUNT_MISMATCH already has the guard name `exact_volume_counts` in `ALL_GUARD_NAMES` and runs in PHASE 1 via `check_volume_counts()`, so its halt elevation is architecturally consistent with the existing guard system.
  </architectural_note>

  <newly_observed_issue>
    During plan-phase code review, a pre-existing exit code misalignment was identified:

    `ToolVersionError` (raised by `tool_registry.py:preflight_tool_environments()` when a binary version check fails) inherits from `BidsReconError`, not `ToolUnavailableError`. In `__main__.py`, it is caught by `except BidsReconError`, mapping to exit code 2 ("config/input validation error"). The correct mapping per the orchestrator contract is exit code 4 ("external tool unavailable or crashed, environment issue"). This is directly relevant to H5 (Python pin runtime check): a Python version floor violation would also raise `ToolVersionError`, and it should map to exit code 4, not exit code 2.

    The fix is included in C7 as a one-line addition (`except ToolVersionError` handler before `except BidsReconError`). This is a newly observed issue not in the brainstorm; user approval is required before build proceeds.
  </newly_observed_issue>

  <changes>
    <change id="C1" priority="P0" source_item="H1">
      <file path="tools.lock.yaml" action="modify" />
      <file path="fmri_bids_recon/tool_registry.py" action="modify" />
      <description>Rename lockfile keys to match cross-module schema: schema_version to lockfile_version, tools: to binaries:. Update tool_registry.py to read the new key.</description>
      <spec>
        tools.lock.yaml:
        - Line 1: `schema_version: "1.0.0"` → `lockfile_version: "1.0.0"`
        - Line 2: `tools:` → `binaries:`
        - All indented per-tool entries unchanged.

        fmri_bids_recon/tool_registry.py:
        - Line 145: `lock_data.get("tools", {})` → `lock_data.get("binaries", {})`
        - No other references to "schema_version" or "tools" as dict keys exist in this file.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - mechanical key rename, no behavioral change</risk>
      <rollback>Revert the two key renames and the one get() call.</rollback>
    </change>

    <change id="C2" priority="P0" source_item="H5">
      <file path="tools.lock.yaml" action="modify" />
      <file path="fmri_bids_recon/tool_registry.py" action="modify" />
      <description>Add Python 3.12.13 pin to tools.lock.yaml and runtime Class B floor check in preflight_tool_environments().</description>
      <spec>
        tools.lock.yaml (after C1 applied):
        - Add `python: "3.12.13"` as line 2 (between lockfile_version and binaries:).

        fmri_bids_recon/tool_registry.py:
        - Add `import sys` to the imports block (after existing `import subprocess`).
        - In `preflight_tool_environments()`, BEFORE the `for name, spec in lock_data.get("binaries", {}).items():` loop, add a Python version check block:

        ```python
        python_pin = lock_data.get("python")
        if python_pin:
            pinned_tuple = _parse_pinned_version(python_pin)
            found_tuple = (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
            found_str = f"{found_tuple[0]}.{found_tuple[1]}.{found_tuple[2]}"
            if found_tuple < pinned_tuple:
                py_status = "error" if strict else "warning"
                py_message = f"Python {found_str} is below floor {python_pin}"
            else:
                py_status = "ok"
                py_message = f"Python {found_str} meets floor {python_pin}"
            report.tools["python"] = ToolStatus(
                name="python",
                pinned_version=python_pin,
                found_version=found_str,
                pin_class="B",
                status=py_status,
                message=py_message,
            )
            logger.info("Tool python: %s (%s)", py_status, py_message)
        ```

        This block uses `_parse_pinned_version()` (already exists) and produces a `ToolStatus` entry that flows through the existing `has_errors` check. In strict mode, a floor violation sets status="error", which triggers the `ToolVersionError` raise at line 215. In lenient mode, it sets status="warning", which is informational only.
      </spec>
      <dependencies>C1 (tools.lock.yaml key rename must be applied first)</dependencies>
      <risk>low - additive check, no change to existing tool validation paths</risk>
      <rollback>Remove the python: line from tools.lock.yaml, remove the Python check block and sys import from tool_registry.py.</rollback>
    </change>

    <change id="C3" priority="P0" source_item="H2a">
      <file path="fmri_bids_recon/warnings.py" action="modify" />
      <description>Replace severity constants: remove SEVERITY_WARN/SEVERITY_CRITICAL, add SEVERITY_LOW/SEVERITY_MEDIUM/SEVERITY_HIGH.</description>
      <spec>
        fmri_bids_recon/warnings.py:
        - Line 12: `SEVERITY_WARN = "warn"` → `SEVERITY_LOW = "low"`
        - Line 13: `SEVERITY_CRITICAL = "strong"` → `SEVERITY_MEDIUM = "medium"`
        - Add line 14: `SEVERITY_HIGH = "high"`
        - Module docstring (line 3-5): update "adopted verbatim from the fmri-preproc sister module" to reflect the new vocabulary. The function signature and behavior of graded_warning() itself are unchanged.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - constant rename, but all downstream importers must be updated (C4, C5, C6)</risk>
      <rollback>Revert the three constant definitions.</rollback>
    </change>

    <change id="C4" priority="P0" source_item="H2a">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>Update severity imports and reclassify 3 call sites: UNCLASSIFIED_SERIES and NAVIGATOR_CANDIDATE to low, AMBIGUOUS_CLASSIFICATION to medium.</description>
      <spec>
        fmri_bids_recon/stage2_classify.py:
        - Line 19: `from .warnings import graded_warning, SEVERITY_WARN` → `from .warnings import graded_warning, SEVERITY_LOW, SEVERITY_MEDIUM`
        - Line 331: `SEVERITY_WARN` → `SEVERITY_LOW` (UNCLASSIFIED_SERIES)
        - Line 351: `SEVERITY_WARN` → `SEVERITY_LOW` (NAVIGATOR_CANDIDATE)
        - Line 371: `SEVERITY_WARN` → `SEVERITY_MEDIUM` (AMBIGUOUS_CLASSIFICATION)
      </spec>
      <dependencies>C3 (new constants must exist)</dependencies>
      <risk>low - import and constant swap only</risk>
      <rollback>Revert import line and three constant references.</rollback>
    </change>

    <change id="C5" priority="P0" source_item="H2a, H2b halt elevation">
      <file path="fmri_bids_recon/runs.py" action="modify" />
      <description>Update severity imports, elevate VOLUME_COUNT_MISMATCH to GuardError halt, reclassify VOLUME_COUNT_DRIFT to high.</description>
      <spec>
        fmri_bids_recon/runs.py:
        - Line 16: `from .warnings import graded_warning, SEVERITY_WARN` → `from .warnings import graded_warning, SEVERITY_HIGH`
        - Add import: `from .errors import GuardError` (after the existing `.config` import at line 15)

        VOLUME_COUNT_MISMATCH halt (lines 121-133):
        Replace the entire `if len(top) > 1 and top[0][1] == top[1][1]:` block:

        Current:
        ```python
        if len(top) > 1 and top[0][1] == top[1][1]:
            review_flags.append(
                graded_warning(
                    _logger, SEVERITY_WARN, "VOLUME_COUNT_MISMATCH",
                    ...
                )
            )
            for series, tlabel in group:
                surviving_bolds.append((series, tlabel))
        ```

        New:
        ```python
        if len(top) > 1 and top[0][1] == top[1][1]:
            raise GuardError(
                f"Task {task_label!r}: no unique modal volume count among "
                f"{sorted(set(counts))} ({n_runs} runs). Cannot determine "
                f"expected volume count; manual review required.",
                context={
                    "guard": "exact_volume_counts",
                    "task_label": task_label,
                    "counts": sorted(set(counts)),
                    "n_runs": n_runs,
                },
            )
        ```

        The `for series, tlabel in group: surviving_bolds.append(...)` lines and the `# do NOT create` comment below the old block become dead code and are removed.

        VOLUME_COUNT_DRIFT (line 183):
        - `SEVERITY_WARN` → `SEVERITY_HIGH`
      </spec>
      <dependencies>C3 (SEVERITY_HIGH constant)</dependencies>
      <risk>medium - VOLUME_COUNT_MISMATCH elevation changes pipeline behavior: tied modal volume counts now halt the entire pipeline instead of retaining all runs with a warning. This is the intended behavioral change per brainstorm decision.</risk>
      <rollback>Restore graded_warning call and surviving_bolds.append loop; revert import.</rollback>
    </change>

    <change id="C6" priority="P0" source_item="H2a, H2b halt elevations">
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>Update severity imports, elevate UNPAIRED_FIELDMAP to GuardError halt, migrate PATIENT_ID_WARNING to graded_warning + GuardError halt.</description>
      <spec>
        fmri_bids_recon/stage4_assemble.py:
        - Line 26: `from .errors import PhaseEncodingError` → `from .errors import PhaseEncodingError, GuardError`
        - Line 27: `from .warnings import graded_warning, SEVERITY_WARN` → `from .warnings import graded_warning, SEVERITY_HIGH`

        UNPAIRED_FIELDMAP halt (lines 379-390):
        Replace the block inside `if snum not in fmap_pair_lookup:`:

        Current:
        ```python
        if snum not in fmap_pair_lookup:
            sd_dest = sd_base / "unpaired_fmap" / series.nifti_path.name
            sd_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(series.nifti_path, sd_dest)
            sourcedata_files.append(sd_dest)
            review_flags.append(graded_warning(
                _logger, SEVERITY_WARN, "UNPAIRED_FIELDMAP",
                ...
            ))
            continue
        ```

        New:
        ```python
        if snum not in fmap_pair_lookup:
            raise GuardError(
                f"sub-{sub} ses-{ses}: fieldmap series {snum} has no validated "
                f"pair. An unpaired fieldmap indicates a pairing or acquisition "
                f"issue that requires manual review before assembly can proceed.",
                context={
                    "guard": "fieldmap_pair_complete",
                    "sub": sub,
                    "ses": ses,
                    "series_number": snum,
                },
            )
        ```

        The sourcedata copy, sourcedata_files.append, and `continue` are removed (pipeline halts).

        PATIENT_ID_WARNING halt (lines 524-538):
        Replace the patient_id_warnings block:

        Current:
        ```python
        patient_id_warnings: list[str] = []
        patient_ids: set[str] = set()
        for snum, series in series_map.items():
            pid = series.raw.get("PatientID")
            if pid is not None:
                patient_ids.add(str(pid))
        if len(patient_ids) > 1:
            patient_id_warnings.append(...)
        ```

        New:
        ```python
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
        ```

        The `patient_id_warnings` local variable is removed. In the `return AssemblyResult(...)` at line 547-553, change `patient_id_warnings=patient_id_warnings` to `patient_id_warnings=[]`.

        Note: AssemblyResult.patient_id_warnings field (line 57) and report.py's patient_id_warnings parameter are retained unchanged. In practice, patient_id_warnings will always be an empty list because the non-empty case raises GuardError before the return. The report's "PatientID cross-check" section will always show "All consistent." This preserves backward compatibility with no additional file changes.
      </spec>
      <dependencies>C3 (SEVERITY_HIGH constant)</dependencies>
      <risk>medium - Two behavioral changes: (1) unpaired fieldmaps now halt the pipeline instead of being preserved in sourcedata with a warning; (2) multiple PatientIDs now halt instead of producing a warning string. Both are intended per brainstorm decision.</risk>
      <rollback>Restore graded_warning calls, sourcedata copy logic, and patient_id_warnings list; revert imports.</rollback>
    </change>

    <change id="C7" priority="P0" source_item="H2c, H3, newly observed ToolVersionError fix">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>Exit code 3 union gating (BIDS errors OR high-severity warnings), exit code 5 docstring reservation, and ToolVersionError exit code fix (newly observed).</description>
      <spec>
        fmri_bids_recon/__main__.py:

        Import (line 44): `from .errors import GuardError, ConfigError, ToolUnavailableError, BidsReconError`
        → `from .errors import GuardError, ConfigError, ToolUnavailableError, ToolVersionError, BidsReconError`

        Docstring (lines 122-128): Add exit code 5:
        ```
        Exit codes (orchestrator contract):
            0 = Success (proceed to next stage)
            1 = Pipeline invariant violation / GuardError (stop, do not retry)
            2 = Config / input validation error (stop, user must fix config)
            3 = Completed with warnings (proceed, flag for QC review)
            4 = External tool unavailable or version mismatch (stop, environment issue)
            5 = Model error (reserved; not raised by bids-recon)
        ```
        Note: exit code 4 description updated to include "version mismatch" alongside "unavailable."

        Exit code 3 union (lines 153-155):
        Current:
        ```python
        if result.status == "warning":
            sys.exit(3)
        sys.exit(0)
        ```

        New:
        ```python
        has_high_warnings = any(
            w.get("severity") == "high" for w in result.warnings
        )
        if result.status == "warning" or has_high_warnings:
            sys.exit(3)
        sys.exit(0)
        ```

        ToolVersionError handler (newly observed fix): Add between the ToolUnavailableError handler (line 159) and the ConfigError handler (line 161):
        ```python
        except ToolVersionError as exc:
            logger.error('Tool version mismatch: %s', exc)
            sys.exit(4)
        ```
      </spec>
      <dependencies>C3 (severity string "high" must match SEVERITY_HIGH constant value)</dependencies>
      <risk>low - exit code 3 union is additive (preserves existing BIDS-error trigger, adds severity-driven trigger). ToolVersionError fix corrects a pre-existing misalignment (was exit code 2, should be 4).</risk>
      <rollback>Revert import, docstring, exit code 3 condition, and remove ToolVersionError handler.</rollback>
    </change>

    <change id="C8" priority="P0" source_item="H4">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <description>Add output_dir: Path field to BidsReconResult, set to bids_root / "derivatives" / "fmri-bids-recon" in the result construction.</description>
      <spec>
        fmri_bids_recon/pipeline.py:

        BidsReconResult dataclass (line 41-48): Add `output_dir: Path` field after `manifest_path`:
        ```python
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
        ```

        Note: `output_dir` is a positional field (no default), placed before the defaulted fields. It must come after `manifest_path` and before `warnings`.

        Result construction (lines 314-322): Add `output_dir` argument:
        ```python
        return BidsReconResult(
            status=status,
            manifest_path=manifest_path,
            output_dir=bids_root / "derivatives" / "fmri-bids-recon",
            warnings=all_review_flags,
            participants_processed=participants_processed,
            bids_validation_errors=error_count,
            bids_validation_warnings=warning_count,
            tool_report=tool_report,
        )
        ```

        The `bids_root` variable is already in scope (line 125).
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive field, no existing consumers reference BidsReconResult by positional args (all use keyword args)</risk>
      <rollback>Remove the output_dir field and the construction argument.</rollback>
    </change>

    <change id="C9" priority="P0" source_item="H6a">
      <file path="pyproject.toml" action="modify" />
      <description>Register the 8-level pytest marker taxonomy in pyproject.toml.</description>
      <spec>
        pyproject.toml: Append after the `[tool.setuptools.packages.find]` section:

        ```toml
        [tool.pytest.ini_options]
        markers = [
            "level0_unit: Pure-function unit tests",
            "level1_internal_integration: Cross-function integration within a module",
            "level2_tool_equivalence: Verify tool wrapper output matches known reference",
            "level3_checkpoint: Checkpoint/resume round-trip",
            "level4_stage_integration: Single pipeline stage end-to-end",
            "level5_adversarial: Edge cases, malformed input, boundary conditions",
            "level6_cross_stage: Multi-stage integration",
            "level7_pipeline: Full pipeline end-to-end",
        ]
        ```
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive metadata, no behavioral change until markers are applied to test functions</risk>
      <rollback>Remove the [tool.pytest.ini_options] section.</rollback>
    </change>
  </changes>

  <execution_order>C1, C2, C3, C4, C5, C6, C7, C8, C9</execution_order>

  <execution_notes>
    C1 and C2 are grouped (both modify tools.lock.yaml and tool_registry.py). C2 must follow C1.
    C4, C5, C6 all depend on C3 (severity constants) and touch different files, so they can be executed in parallel after C3.
    C7 depends on C3 for the severity string "high" and is logically the last behavioral change.
    C8 and C9 are independent and can execute in any order.
  </execution_notes>
</implement_plan>
