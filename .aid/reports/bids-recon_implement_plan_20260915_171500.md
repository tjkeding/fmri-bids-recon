<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-09-15T17:15:00Z" />
  <input_reports>
    <report path="bids-recon_test_20260915_163400.md" mode="test" key_items="2" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="action_items[0]">
      <file path="fmri_bids_recon/runs.py" action="modify" />
      <description>The accept/exclude loop in check_volume_counts is unreachable for the 2-run tied-mode branch. The `for series, tlabel in group:` loop (lines 151-178) sits at column 16, nested inside the tie-check's `else:` (no-tie) branch only. The n_runs==2 branch sets mode_count and emits the ABORTED_RUN_DETECTED warning but then falls through without populating surviving_bolds, excluded_list, or new_registry_entries. The accepted run silently vanishes from the BIDS tree.</description>
      <spec>Dedent the `for series, tlabel in group:` loop and its entire body (current lines 151-178) from column 16 to column 12, making it a sibling of the `if len(top) > 1 and top[0][1] == top[1][1]:` / `else:` block rather than a child of the `else:` branch. After this change, mode_count is set in both the n_runs==2 branch (`mode_count = max(counts)`) and the no-tie branch (`mode_count = top[0][0]`), and the accept/exclude loop runs after either branch. The GuardError branch (n_runs > 2 tie) raises before reaching the loop, which is the correct behavior. No other lines change; the loop body's internal indentation relative to the `for` statement is preserved.</spec>
      <dependencies>none</dependencies>
      <risk>low - mechanical indentation change; no logic modification; the loop body is unchanged</risk>
      <rollback>Re-indent lines 151-178 back to column 16 (restore the `else:` nesting)</rollback>
    </change>
    <change id="C2" priority="P1" source_item="action_items[1]">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <description>Both the Phase 1 (CONVERT) and Phase 3 (ASSEMBLE) per-participant loops set _current_sub/_current_ses via ContextVar.set() unconditionally at the top of the loop body, but each loop has a pre-existing `continue` path (Phase 1: `if should_skip(...)`, line 163; Phase 3: `if not json_path.exists()`, line 277) that exits before reaching the reset() calls at the loop body's end. A skipped participant's sub/ses context leaks into all subsequent log messages and run() calls in the same process.</description>
      <spec>In both the Phase 1 and Phase 3 per-participant loops, wrap the loop body (from the first statement after the set() calls through the last statement before the current reset() calls) in a `try:` block, and move the two reset() calls into a `finally:` block. The set() calls remain before the `try:` (the token must exist for the finally to reset it). The explicit reset() calls at the current end of each loop body are removed (they are now in finally:). This ensures cleanup on all exit paths: normal completion, `continue`, and any raised exception that propagates.

Phase 1 structure after the change (line references are approximate):

```python
for p in config.participants:
    sub, ses = p.sub, p.ses
    _sub_token = _current_sub.set(sub)
    _ses_token = _current_ses.set(ses)
    try:
        if should_skip(manifest, sub, ses):
            logger.info('Skipping already-validated sub=%s ses=%s', sub, ses)
            continue
        # ... existing loop body, indented +4 from current ...
        logger.info('convert complete: ...')
    finally:
        _current_sub.reset(_sub_token)
        _current_ses.reset(_ses_token)
```

Phase 3 structure after the change:

```python
for p in config.participants:
    sub, ses = p.sub, p.ses
    _sub_token = _current_sub.set(sub)
    _ses_token = _current_ses.set(ses)
    try:
        staging_dir = Path(config.staging_root) / f'sub-{sub}' / f'ses-{ses}'
        json_path = staging_dir / f'{sub}_{ses}_intermediate.json'
        if not json_path.exists():
            continue
        # ... existing loop body, indented +4 from current ...
        participants_processed.append(f"sub-{sub}_ses-{ses}")
    finally:
        _current_sub.reset(_sub_token)
        _current_ses.reset(_ses_token)
```

The only semantic change is the guaranteed cleanup; no other logic is modified. The re-indentation of the loop body contents is mechanical.</spec>
      <dependencies>none</dependencies>
      <risk>low - mechanical try/finally wrapping; Python's finally semantics guarantee cleanup on continue, return, and exception; no logic change to the loop body itself</risk>
      <rollback>Remove try/finally, dedent loop body contents, restore explicit reset() calls at the end of each loop body</rollback>
    </change>
  </changes>
  <execution_order>C1, C2 (independent; may execute in parallel)</execution_order>
</implement_plan>
