<test_report>
  <meta project="bids-recon" mode="test" timestamp="2026-08-27T18:04:00Z" />
  <pre_design_run>
    <total>642</total>
    <passed>546</passed>
    <failed>1</failed>
    <errors>0</errors>
    <coverage_pct>null</coverage_pct>
    <failures>
      <failure test="test_the_real_lockfile_probes_dcm2niix_and_skips_deface_tools_by_default" file="tests/test_tool_registry.py" line="522">
        <error_type>AssertionError</error_type>
        <message>assert 'warning' == 'ok'</message>
        <traceback>AssertionError: assert 'warning' == 'ok'
  - ok
  + warning
tests/test_tool_registry.py:522: AssertionError: assert 'warning' == 'ok'</traceback>
      </failure>
    </failures>
  </pre_design_run>
  <failing_test_dispositions>
    <disposition test="test_the_real_lockfile_probes_dcm2niix_and_skips_deface_tools_by_default" file="tests/test_tool_registry.py" classification="obsolete-test">
      <intended_contract>The test verifies that preflight_tool_environments(), run against the real shipped tools.lock.yaml (not a synthetic fixture), reports status "ok" when the probed dcm2niix version exactly matches the lockfile's pinned floor for a Class A pin.</intended_contract>
      <current_test_claim>Mocked subprocess.run returns stdout="v1.0.20260416" (the prior dcm2niix floor value) and asserts report.tools["dcm2niix"].status == "ok".</current_test_claim>
      <evidence>This session's orchestrator-level edit to fmri_bids_recon/tools.lock.yaml (user-approved, outside the test skill's write scope) lowered the dcm2niix floor from 1.0.20260416 to 1.0.20220720. The mocked found-version literal in this test was not updated in that edit, so found (1,0,20260416) now exceeds the new pinned floor (1,0,20220720), triggering the pin_class A lenient "warning" branch in _compare_versions (fmri_bids_recon/tool_registry.py:123-126) rather than the exact-match "ok" branch. Two other occurrences of "v1.0.20260416" in this file (line 92: test_parse_version's format check; line 292: test_an_unconditional_tool_is_always_probed, which pins its own synthetic lockfile to "1.0.20260416" and is self-consistent) are unaffected by the real-lockfile floor change and were left untouched.</evidence>
      <action>re-express: updated the mocked subprocess.run stdout from "v1.0.20260416" to "v1.0.20220720" (the new real-lockfile floor), preserving the original assertion's intent (exact match to the pinned floor yields "ok") against the new pinned value rather than weakening the assertion to accept "warning".</action>
    </disposition>
  </failing_test_dispositions>
  <design_phase>
    <tests_created>0</tests_created>
    <tests_modified>1</tests_modified>
    <files_created>
      <file path="tests/test_tool_registry.py" test_count="0 (existing test modified, no new tests)" coverage_target="Re-expresses test_the_real_lockfile_probes_dcm2niix_and_skips_deface_tools_by_default's mocked found-version to match the new dcm2niix floor (1.0.20220720), restoring exact-match coverage of the real project lockfile's Class A pin semantics." />
    </files_created>
    <design_rationale>
      The user directed a lockfile edit (fmri_bids_recon/tools.lock.yaml) lowering the dcm2niix floor
      from 1.0.20260416 to 1.0.20220720 and the pydeface floor from 2.1.0 to 2.0.0, correcting floors
      that had been auto-populated from the development machine's installed tool versions during the
      v1.6.0 harmonization rather than derived from validated minimum feature requirements. This is an
      intentional, user-approved contract change to the real lockfile, not a regression. One test
      exercises the real lockfile end-to-end (mocked only at the subprocess boundary) and hardcoded the
      prior floor value as its mocked found-version; that hardcoded value needed re-expression to track
      the new floor, per the obsolete-test disposition above. No other test in the suite references the
      dcm2niix or pydeface floor values from the real lockfile end-to-end, so no further edits were needed.
    </design_rationale>
  </design_phase>
  <post_design_run>
    <total>642</total>
    <passed>547</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct>null</coverage_pct>
    <failures></failures>
  </post_design_run>
  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>0</bugs_routed_to_implement>
    <recommendation>proceed_to_document</recommendation>
  </summary>
  <action_items>
  </action_items>
</test_report>
