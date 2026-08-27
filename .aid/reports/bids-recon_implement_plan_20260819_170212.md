<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-19T17:02:12Z" />
  <input_reports>
    <report path="bids-recon_brainstorm_20260819_165335.md" mode="brainstorm" key_items="2" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="T1">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>Fix catch-all exit codes (2 to 1) and log levels (error/exception to critical) for the BidsReconError and bare Exception handlers at lines 172-177. These catch-alls currently exit with code 2 (ConfigError semantic), which misrepresents unexpected errors to the orchestrator. Exit code 1 (invariant violation, stop, do not retry) is the correct catch-all.</description>
      <spec>
Replace lines 172-177:

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
        logger.critical('Unexpected error: %s', exc, exc_info=True)
        sys.exit(1)
```

Four changes:
1. BidsReconError exit code: 2 to 1.
2. BidsReconError log level: logger.error to logger.critical.
3. Bare Exception exit code: 2 to 1.
4. Bare Exception log level: logger.exception to logger.critical with exc_info=True (preserves traceback at CRITICAL level).

No other lines in __main__.py are affected. The specific handlers above (GuardError exit 1, ToolUnavailableError exit 4, ToolVersionError exit 4, ConfigError exit 2) remain unchanged.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - changes two exit codes and two log calls in catch-all handlers; no logic changes; all typed exceptions are handled by specific handlers above these lines</risk>
      <rollback>Revert the four line changes.</rollback>
    </change>
    <change id="C2" priority="P0" source_item="T2">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <description>Route BIDS validation errors through graded_warning and unify the BidsReconResult.status field to be driven by high-severity entries in all_review_flags. Three sub-changes: add graded_warning import, emit BIDS_VALIDATION_ERRORS warning and append to accumulator, replace status determination.</description>
      <spec>
**C2a. Add graded_warning import** (line 35):

Replace:
```python
from .errors import GuardError
```

With:
```python
from .errors import GuardError
from .warnings import graded_warning
```

**C2b. Emit high-severity graded_warning for BIDS validation errors** (after line 295):

After:
```python
    errors_found = [f for f in findings if f.severity == 'error']
```

Insert:
```python
    if errors_found:
        all_review_flags.append(
            graded_warning(
                logger, "high", "BIDS_VALIDATION_ERRORS",
                f"BIDS validation found {len(errors_found)} error(s): "
                f"{'; '.join(f.message for f in errors_found[:3])}"
                + (f" (+{len(errors_found) - 3} more)" if len(errors_found) > 3 else ""),
            )
        )
```

This appends the returned dict to all_review_flags (the accumulator). graded_warning() is a pure function; the explicit append follows the established pattern at stage2_classify.py:330 and runs.py:181.

**C2c. Unify status determination** (line 313):

Replace:
```python
    status = "warning" if errors_found else "success"
```

With:
```python
    status = "warning" if any(w["severity"] == "high" for w in all_review_flags) else "success"
```

Status is now driven by ANY high-severity entry in all_review_flags, not by BIDS validation errors alone. Since BIDS validation errors are now routed through graded_warning as high severity (C2b), the behavior is equivalent for that case but unified with other high-severity pipeline warnings.

Key invariant: after C2b and C2c, the status field is driven exclusively by the graded_warning accumulator's high-severity entries.
      </spec>
      <dependencies>none (C1 and C2 are independent; C2's sub-changes C2a/C2b/C2c are sequential within the file)</dependencies>
      <risk>low - adds one import, inserts one conditional block, replaces one status expression; the behavioral change (status can now be "warning" from non-BIDS high-severity warnings) is the intended harmonized semantic and has no exit code impact (union check in __main__.py already covers this)</risk>
      <rollback>Revert pipeline.py to remove the import, the graded_warning call block, and the status expression change.</rollback>
    </change>
  </changes>
  <execution_order>C1, C2 (independent; order is arbitrary but listed for determinism)</execution_order>
</implement_plan>
