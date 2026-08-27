<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-08-19T18:10:45Z" />
  <spec_ref>bids-recon_implement_plan_20260819_175830.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/config.py" lines_changed="9" />
      </files_modified>
      <notes>load_and_validate() now wraps the _load_raw(path) call in a try/except that catches FileNotFoundError and re-raises as ConfigError with the path embedded in the message. The docstring's Raises section was updated: FileNotFoundError narrowed to the subjects-file-only case, ConfigError expanded to cover the missing-config-file case. No changes outside config.py. Applied exactly as specified, no deviations.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>1</total_changes>
    <completed>1</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate that test_a_config_error_exits_two now passes and that test_a_missing_subjects_file_is_refused (which asserts FileNotFoundError for the subjects-file case) remains unaffected.</next_steps>
</implement_report>
