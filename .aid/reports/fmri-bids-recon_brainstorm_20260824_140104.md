<brainstorm_report>
  <meta project="fmri-bids-recon" mode="brainstorm" timestamp="2026-08-24T14:01:04Z" source_project="fmri-proc-orchestrator" source_report="fmri-proc-orchestrator_brainstorm_20260824_140104.md" />
  <context>This report contains the subset of harmonization decisions from the fmri-proc-orchestrator brainstorm that require changes in fmri-bids-recon. These decisions were made during a cross-module harmonization audit of the four-project pipeline (orchestrator, bids-recon, preproc, first-level-proc).</context>
  <topics>
    <topic id="T3" title="graded_warning return dict: add user_facing to four-key schema">
      <summary>The cross-pipeline contract for graded_warning return dicts is standardized to four keys: {severity, code, message, user_facing}. bids-recon's warnings.py currently returns three keys (missing user_facing). The user_facing parameter already exists in the function signature; the return dict must include it.</summary>
      <decision status="decided">Add "user_facing": user_facing to the return dict in warnings.py graded_warning(). The parameter already exists in the signature (user_facing: bool = False); only the return statement needs updating.</decision>
    </topic>
    <topic id="T4" title="Warning accumulation: add module-level _WARNING_ACCUMULATOR">
      <summary>The cross-pipeline contract standardizes warning accumulation via a module-level _WARNING_ACCUMULATOR list with get_warnings()/clear_warnings() API. bids-recon's warnings.py currently returns dicts without accumulating; the pipeline collects them manually via all_review_flags. The accumulator pattern must be adopted for plumbing consistency across sister modules.</summary>
      <decision status="decided">Add _WARNING_ACCUMULATOR (list[dict]), get_warnings() -> list[dict], and clear_warnings() -> None to warnings.py. Have graded_warning() append to the accumulator. Update pipeline.py: call clear_warnings() at pipeline entry; replace manual all_review_flags collection with get_warnings() at status determination. The ReviewFlag exception class is unaffected (it serves a distinct purpose as a raisable sentinel).</decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P1" target_mode="implement" description="T3: Add user_facing to graded_warning return dict in warnings.py" />
    <item priority="P1" target_mode="implement" description="T4: Add _WARNING_ACCUMULATOR, get_warnings(), clear_warnings() to warnings.py; update pipeline.py to call clear_warnings() at entry and get_warnings() at status determination instead of manual all_review_flags collection" />
  </action_items>
</brainstorm_report>
