<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-08-19T16:53:35Z" />
  <context_files>
    <file path="fmri-bids-recon_implement_plan_20260819_145136.md" relevance="Harmonization report from fmri-proc-orchestrator proposing 2 changes (C1, C2)" />
    <file path="fmri_bids_recon/__main__.py" relevance="Contains the catch-all exit code handlers targeted by C1" />
    <file path="fmri_bids_recon/pipeline.py" relevance="Contains run(), BidsReconResult, BIDS validation routing, and status determination targeted by C2" />
    <file path="fmri_bids_recon/warnings.py" relevance="graded_warning() implementation: pure function returning a dict, no accumulator" />
    <file path="fmri_bids_recon/errors.py" relevance="Exception hierarchy: BidsReconError base, GuardError/ConfigError/ToolUnavailableError/ToolVersionError subclasses" />
  </context_files>
  <topics>
    <topic id="T1" title="Catch-all exit codes and log levels">
      <summary>The BidsReconError and bare Exception catch-all handlers in __main__.py (lines 172-177) both exit with code 2, which collides with the ConfigError/InputError semantic. Exit code 2 tells the orchestrator "user must fix their config," which is semantically wrong for unexpected errors. The report proposes changing both to exit code 1 (invariant violation, stop, do not retry) and upgrading log levels from logger.error to logger.critical.</summary>
      <research>No external research required. Codebase-internal contract verification only. The 6-code exit contract was verified from __main__.py lines 123-130. The exception hierarchy was verified from errors.py. The catch-all handler structure was verified at __main__.py lines 160-177, confirming that all typed exceptions (GuardError, ToolUnavailableError, ToolVersionError, ConfigError) are handled by specific handlers above the catch-alls.</research>
      <approaches>
        <approach id="A1" label="Report as-is" feasibility="high" risk="low">
          <description>Accept the report's proposal exactly: both handlers change to exit 1, both use logger.critical, bare Exception handler drops the traceback.</description>
          <pros>Exact cross-module consistency with sister modules (fmri-preproc, fmri-first-level-proc).</pros>
          <cons>Loses the traceback for bare Exception errors. logger.critical() does not include exc_info by default, despite the report's claim that "the traceback is already captured by the logging framework's exception propagation." On HPC, where reproducing failures is expensive, the traceback is valuable debugging information.</cons>
        </approach>
        <approach id="A2" label="Report + exc_info preservation" feasibility="high" risk="low">
          <description>Accept exit code changes and logger.critical for the BidsReconError handler. For the bare Exception handler, use logger.critical('Unexpected error: %s', exc, exc_info=True) to preserve the traceback at CRITICAL level.</description>
          <pros>Cross-module consistency on exit codes and log levels. Preserves traceback for truly unexpected errors (programming bugs, third-party crashes). exc_info=True is a standard Python logging parameter, not a divergent pattern.</pros>
          <cons>Minor divergence from sister modules if they use plain logger.critical for bare Exception handlers.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A2">Exit codes change from 2 to 1 for both catch-alls. BidsReconError handler uses logger.critical (exception message is self-descriptive). Bare Exception handler uses logger.critical(..., exc_info=True) to preserve the traceback. This satisfies the cross-module convention while retaining debugging value.</decision>
    </topic>
    <topic id="T2" title="BIDS validation routing through graded_warning + status unification">
      <summary>The report proposes routing BIDS validation errors through graded_warning() as a high-severity entry and unifying the BidsReconResult.status field to be driven by any high-severity graded_warning rather than BIDS validation errors alone. Two issues were identified with the spec as written: (1) a mechanical bug where graded_warning()'s return value is not appended to all_review_flags, and (2) a status-semantics expansion that, while correct for the harmonized contract, needed explicit approval.</summary>
      <research>No external research required. The graded_warning() implementation was verified as a pure function (warnings.py:17-33) that returns a dict without any accumulator side effect. All existing call sites (stage2_classify.py:330/350/370, runs.py:181, stage4_assemble.py:534) explicitly capture and append the returned dict to local lists. The __main__.py union check (lines 154-158) was verified to already trigger exit code 3 on high-severity warnings OR BIDS errors, confirming the exit code behavioral impact is nil. BidsReconResult.bids_validation_errors (integer field) was confirmed as the BIDS-specific count available to consumers needing that distinction.</research>
      <approaches>
        <approach id="A1" label="Report as-is (buggy)" feasibility="low" risk="high">
          <description>Implement the spec's code verbatim, calling graded_warning() without capturing the return value.</description>
          <pros>None.</pros>
          <cons>The BIDS_VALIDATION_ERRORS dict is lost. The subsequent status check against all_review_flags never sees it. Status remains driven by errors_found implicitly (the old behavior), defeating the unification purpose.</cons>
        </approach>
        <approach id="A2" label="Fixed routing + unified status" feasibility="high" risk="low">
          <description>Accept C2's principle but fix the mechanical bug: all_review_flags.append(graded_warning(...)). Status is driven by any high-severity entry in all_review_flags. BIDS validation errors join the same accumulator as pipeline warnings.</description>
          <pros>Single canonical mechanism for all warning/error signals. Status field answers "does this run need QC review?" for any source. bids_validation_errors field provides BIDS-specific counts for consumers that need them. No exit code behavior change (union check in __main__.py already covers this).</pros>
          <cons>Status="warning" can now fire on high-severity pipeline warnings (e.g., VOLUME_COUNT_DRIFT) even when BIDS validation passes cleanly. This is the intended harmonized semantic but represents a change from BIDS-validation-only status.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A2">Accept C2 with the mechanical fix. graded_warning() return value is appended to all_review_flags. Status field becomes unified: driven by any high-severity entry in all_review_flags. The BIDS-specific count remains available via bids_validation_errors.</decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P0" target_mode="implement" description="C1: Change catch-all exit codes from 2 to 1 in __main__.py. BidsReconError handler: logger.critical. Bare Exception handler: logger.critical with exc_info=True." />
    <item priority="P0" target_mode="implement" description="C2: In pipeline.py, after errors_found is computed (line 295), emit graded_warning for BIDS validation errors and append the return to all_review_flags. Replace status determination (line 313) with high-severity check against all_review_flags." />
    <item priority="P0" target_mode="test" description="Update test assertions for catch-all exit codes (2 to 1) and status determination logic. Add test for BIDS_VALIDATION_ERRORS graded_warning emission." />
  </action_items>
  <next_steps>Run /implement plan+build to execute C1 and C2 with the approved adjustments, then /test to verify.</next_steps>
</brainstorm_report>
