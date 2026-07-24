<test_report>
  <meta project="bids-recon" mode="test" timestamp="2026-07-24T13:30:00-04:00" />
  <pre_design_run>
    <total>418</total>
    <passed>415</passed>
    <failed>1</failed>
    <errors>0</errors>
    <coverage_pct></coverage_pct>
    <failures>
      <failure test="test_an_absent_defacing_tool_does_not_claim_to_have_defaced_anything" file="tests/test_deface.py" line="213">
        <error_type>FileNotFoundError</error_type>
        <message>[Errno 2] No such file or directory: 'pydeface'</message>
        <traceback>fmri_bids_recon/deface.py:65 in deface -&gt; subprocess.run raises FileNotFoundError (handler removed by implement build)</traceback>
      </failure>
    </failures>
  </pre_design_run>
  <failing_test_dispositions>
    <disposition test="test_an_absent_defacing_tool_does_not_claim_to_have_defaced_anything" file="tests/test_deface.py" classification="obsolete-test">
      <intended_contract>Per the locked brainstorm decision (bids-recon_brainstorm_20260724_120000.md, topic T1), once config.deface is true the pipeline commits to hard enforcement: every anatomical must be defaced or the pipeline halts. The build report (bids-recon_implement_build_20260724_133000.md, change C2) removed the FileNotFoundError handler in deface.py so that a missing tool at runtime propagates rather than being caught, matching the existing CalledProcessError contract.</intended_contract>
      <current_test_claim>assert deface(study) == [] -- asserted that a FileNotFoundError from the defacing tool is caught and degrades to an empty return list.</current_test_claim>
      <evidence>fmri_bids_recon/deface.py: the try/except FileNotFoundError block (formerly lines 95-101) was removed in the implement build (change C2). bids-recon_implement_plan_20260724_130000.md change C2 spec explicitly directs this removal. The sibling test test_a_defacing_tool_that_fails_stops_rather_than_reporting_success already encodes the equivalent hard-enforcement contract for CalledProcessError.</evidence>
      <action>re-express: renamed to test_an_absent_defacing_tool_stops_rather_than_reporting_success; assertion changed from `deface(study) == []` to `pytest.raises(FileNotFoundError)`. This strengthens the assertion (from allowing silent success-shaped output to requiring loud failure) rather than weakening it.</action>
    </disposition>
  </failing_test_dispositions>
  <design_phase>
    <tests_created>5</tests_created>
    <tests_modified>2</tests_modified>
    <files_created>
      <file path="tests/test_deface.py" test_count="3" coverage_target="assert_deface_tools() pre-flight function: raises ToolUnavailableError when pydeface absent, raises when flirt absent, passes when both present" />
      <file path="tests/test_config.py" test_count="2" coverage_target="deface config toggle: defaults to False when omitted from YAML, loads True when explicitly set" />
    </files_created>
    <design_rationale>Two gaps existed after the implement build: (1) the FileNotFoundError test in test_deface.py encoded the pre-redesign soft-degradation contract and needed re-expression to match the new hard-enforcement contract; (2) the new assert_deface_tools() function and the new StudyConfig.deface field had zero test coverage. Both gaps map directly to changes C1-C3 in the implement build (bids-recon_implement_build_20260724_133000.md). No coverage was added for the __main__.py pre-flight wiring (C3) or the exit-code-4 path, since __main__.py is an integration entry point without existing test infrastructure (no test___main__.py exists in the suite) and adding one would exceed the scope of gap-filling for this design pass; this is noted as a P2 follow-up below rather than silently skipped.</design_rationale>
  </design_phase>
  <post_design_run>
    <total>423</total>
    <passed>421</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct></coverage_pct>
    <failures>
    </failures>
  </post_design_run>
  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>0</bugs_routed_to_implement>
    <recommendation>proceed_to_document</recommendation>
  </summary>
  <action_items>
    <item priority="P2" target_mode="implement" description="Consider adding integration-level coverage for fmri_bids_recon/__main__.py's deface pre-flight block (the config.deface=true branch that calls assert_deface_tools() and exits with code 4 on ToolUnavailableError). No test___main__.py currently exists in the suite; this was out of scope for the current gap-filling pass, which focused on the deface.py and config.py unit-level changes." />
  </action_items>
</test_report>
