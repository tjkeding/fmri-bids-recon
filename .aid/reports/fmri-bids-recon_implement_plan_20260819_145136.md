<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-08-19T14:51:36Z" />
  <input_reports>
    <report path="fmri-proc-orchestrator_brainstorm_20260819_144504.md" mode="brainstorm" key_items="2" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="T7">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>Fix catch-all exit codes in __main__.py to align with the 6-code contract. Both the BidsReconError catch and the bare Exception catch currently exit with code 2, which collides with ConfigError/InputError. They should exit with code 1 (GuardError equivalent) and use logger.critical instead of logger.error.</description>
      <spec>
At lines 172-177, replace:

```python
except BidsReconError as exc:
    logger.error('Pipeline error: %s', exc)
    sys.exit(2)
except Exception as exc:
    logger.exception('Unexpected error: %s', exc)
    sys.exit(2)
```

With:

```python
except BidsReconError as exc:
    logger.critical('Pipeline error: %s', exc)
    sys.exit(1)
except Exception as exc:
    logger.critical('Unexpected error: %s', exc)
    sys.exit(1)
```

Changes:
1. Both exit codes change from 2 to 1 (GuardError/invariant violation, the correct catch-all for untyped errors).
2. Both log levels change to `logger.critical` (these are unexpected, unrecoverable errors).
3. The bare Exception handler retains `logger.critical` (not `logger.exception`) to match the sister modules' convention of single-line critical messages for catch-all errors. The traceback is already captured by the logging framework's exception propagation.

Note: The existing specific exception handlers above these lines (ConfigError -> exit 2, InputError -> exit 2, ToolUnavailableError -> exit 4, etc.) remain unchanged; only the catch-all handlers at the bottom of the try/except chain are affected.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - changes two exit codes and two log levels in catch-all handlers; no logic changes</risk>
      <rollback>Revert the four line changes.</rollback>
    </change>
    <change id="C2" priority="P0" source_item="T9b">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <description>Route BIDS validation errors through the graded_warning system and standardize the status field to use high-only gating. Currently, BIDS validation errors set status="warning" via a separate code path that bypasses graded_warning entirely. Under the harmonized status contract, BIDS validation errors should emit a high-severity graded_warning (code BIDS_VALIDATION_ERRORS), and the status field should be driven by whether any high-severity graded warnings exist.</description>
      <spec>
**2a. Emit high-severity graded_warning for BIDS validation errors** (after line 295, where errors_found is computed):

At the point where `errors_found` is populated (line 295: `errors_found = [f for f in findings if f.severity == 'error']`), if errors_found is non-empty, emit a graded_warning:

```python
if errors_found:
    graded_warning(
        logger, "high", "BIDS_VALIDATION_ERRORS",
        f"BIDS validation found {len(errors_found)} error(s): "
        f"{'; '.join(f.message for f in errors_found[:3])}"
        + (f" (+{len(errors_found) - 3} more)" if len(errors_found) > 3 else ""),
    )
```

This ensures BIDS validation errors flow through the same graded_warning accumulator as all other warnings.

**2b. Standardize status field to high-only gating** (line 313):

Replace:
```python
status = "warning" if errors_found else "success"
```

With:
```python
status = "warning" if any(w["severity"] == "high" for w in all_review_flags) else "success"
```

This makes the status determination consistent with the harmonized contract: status="warning" only when high-severity graded warnings exist. Since BIDS validation errors now emit a high-severity graded_warning (step 2a), the behavior is equivalent for that case, but the mechanism is unified.

**2c. Verify graded_warning import**: Confirm that `graded_warning` is imported in pipeline.py. It should already be available from the module's utils. If not, add the import.

**2d. Verify all_review_flags naming**: The accumulated warnings list is `all_review_flags` (line 134). Confirm this is the same list that `graded_warning` appends to. If graded_warning uses a module-level `_WARNING_ACCUMULATOR`, then the status check in 2b needs to reference the accumulator, not `all_review_flags`. Check the actual implementation and adjust accordingly.

The key invariant: after 2a and 2b, the status field in the returned PipelineResult is driven exclusively by the graded_warning accumulator's high-severity entries, not by a separate BIDS-error flag.
      </spec>
      <dependencies>C1 (the __main__.py catch-all fix should be in place first, though technically independent)</dependencies>
      <risk>medium - changes the mechanism by which status is determined; the behavior should be equivalent for BIDS validation errors (they are now routed through graded_warning as high), but the unified path means other future high-severity warnings would also trigger status="warning". This is the intended harmonized behavior.</risk>
      <rollback>Revert pipeline.py changes; status reverts to being driven by errors_found directly.</rollback>
    </change>
  </changes>
  <execution_order>C1, C2</execution_order>
</implement_plan>
