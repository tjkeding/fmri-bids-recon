<document_report>
  <meta project="bids-recon" mode="document" timestamp="2026-09-15T17:35:00Z" />
  <files_updated>
    <file path="README.md" changes="Updated the exact_volume_counts guard table row to describe the within-session tie-handling behavior (2-run tie accepts the longer run and excludes the shorter as a probable aborted acquisition; 3-or-more-run tie halts via GuardError). Added a one-sentence note to the Usage section documenting the [sub-X ses-Y] participant-context log prefix.">
      <type>readme</type>
    </file>
    <file path="INPUT_SPECIFICATION.md" changes="Added a DWI (SBRef) row to the Supported Modalities table. Added two new paragraphs: the DWI SBRef bval guard (single-volume EPI passenger preceding a diffusion series routes to UNCLASSIFIED, not DWI_SBREF, when the successor's .bval exists but is all-zero) and per-phase-encoding-direction DWI run indexing (independent sequential numbering per direction group, with DWI_SBREF passengers inheriting their temporally-nearest parent DWI's run index).">
      <type>input_spec</type>
    </file>
    <file path="AID_LOG.md" changes="Updated two stale test-count references (654 to 664) in Section 2 (Scope) and Section 5 item (d) (Human Oversight) to reflect the current suite size. No Version History row added; that section is authored by /publish.">
      <type>aid_log</type>
    </file>
    <file path="fmri_bids_recon/runs.py" changes="Corrected check_volume_counts()'s docstring, which described within-session reasoning as uniformly mode-then-exclude; it now accurately describes the tie-handling split (clear mode vs. 2-run tie vs. 3-or-more-run tie) that the accept/exclude loop dedent fix depends on.">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/stage2_classify.py" changes="Added one-line inline comments at the two DWI_SBREF bval-guard branches (Rule 5 and Rule 9) explaining why an all-zero .bval successor routes the passenger to UNCLASSIFIED rather than DWI_SBREF.">
      <type>inline_comment</type>
    </file>
    <file path="fmri_bids_recon/stage4_assemble.py" changes="Added a comment block above the DWI run-indexing code explaining the per-phase-encoding-direction grouping rationale and the DWI_SBREF-to-parent-DWI temporal pairing heuristic.">
      <type>inline_comment</type>
    </file>
    <file path="fmri_bids_recon/pipeline.py" changes="Added a paragraph to run()'s docstring documenting the participant-context log tagging mechanism and the try/finally cleanup guarantee. Added one-line comments above each per-participant loop's try/finally block explaining why cleanup is guaranteed via finally rather than an explicit end-of-body reset.">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/__main__.py" changes="Added a docstring to _ParticipantFormatter (previously undocumented) explaining its transparent contextvars-based injection mechanism and its graceful-degradation behavior when no participant loop is active.">
      <type>docstring</type>
    </file>
  </files_updated>
  <aid_log>
    <status>updated</status>
    <sections_modified>Section 2 (Scope), Section 5 (Human Oversight)</sections_modified>
  </aid_log>
  <coverage>
    <public_functions_documented>all touched functions already had docstrings; gaps closed rather than added from zero</public_functions_documented>
    <classes_documented>1/1 newly-covered (_ParticipantFormatter, previously undocumented)</classes_documented>
    <modules_with_docstrings>5/5 touched modules already had module-level docstrings; unchanged</modules_with_docstrings>
  </coverage>
  <summary>Documentation now reflects the current, corrected behavior of the two bug fixes applied this session (the runs.py accept/exclude loop dedent and the pipeline.py ContextVar try/finally fix) as well as three previously-undocumented behaviors from earlier this session's implement pass: the DWI_SBREF bval guard, per-direction DWI run indexing, and participant-context log tagging. All five documentation-edited Python files pass a syntax check and the full test suite (569 passed, 95 skipped, 0 failed) re-ran clean after the edits, confirming no functional code was altered. The mandatory PII/PHI and LLM-attribution security gate ran as five independent parallel scans against all eight created/modified files; all five returned zero violations.</summary>
</document_report>
