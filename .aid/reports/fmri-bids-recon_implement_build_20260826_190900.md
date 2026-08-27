<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-08-26T19:09:00Z" />
  <spec_ref>bids-recon_implement_plan_20260826_190814.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage4_assemble.py" lines_changed="12" />
      </files_modified>
      <notes>Added unpaired_sns set construction from unpaired_fmaps; replaced unconditional continue with a conditional that checks membership in unpaired_sns before continuing (legitimate CR F3/F7 case) or raising GuardError with guard="fieldmap_pair_complete" (wiring-defect case).</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/report.py" lines_changed="1" />
      </files_modified>
      <notes>Changed format string from f"dir-{'/'.join(anatomical_labels)}" to f"{'/'.join(f'dir-{l}' for l in anatomical_labels)}" so each direction label is independently prefixed with dir-.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage3_map.py" lines_changed="14" />
      </files_modified>
      <notes>Added consecutive-timestamp-tie detection loop (variable k to avoid shadowing the outer pairing loop variable i) after the odd-count check and before the pairing loop. Raises PhaseEncodingError when two consecutive members share identical acquisition_datetime.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>3</total_changes>
    <completed>3</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test run_suite to validate all three proof tests now pass (538+3=541 expected passes, 0 expected failures).</next_steps>
</implement_report>
