<test_report>
  <meta project="bids-recon" mode="test" timestamp="2026-08-27T13:04:46Z" />
  <pre_design_run>
    <total>636</total>
    <passed>539</passed>
    <failed>2</failed>
    <errors>0</errors>
    <coverage_pct />
    <failures>
      <failure test="test_an_absent_defacing_tool_stops_rather_than_reporting_success" file="tests/test_deface.py" line="">
        <error_type>ToolUnavailableError (raised by production code; unexpected by the test)</error_type>
        <message>Defacing tool 'pydeface' binary not found: [Errno 2] No such file or directory: 'pydeface'</message>
        <traceback>FileNotFoundError: [Errno 2] No such file or directory: 'pydeface'
fmri_bids_recon.errors.ToolUnavailableError: Defacing tool 'pydeface' binary not found
/Users/tjkeding/bids-recon/fmri_bids_recon/deface.py:135</traceback>
      </failure>
      <failure test="test_a_defacing_tool_that_fails_stops_rather_than_reporting_success" file="tests/test_deface.py" line="">
        <error_type>ToolUnavailableError (raised by production code; unexpected by the test)</error_type>
        <message>Defacing tool 'pydeface' failed on sub-001_ses-01_T1w.nii.gz: exit code 1</message>
        <traceback>subprocess.CalledProcessError: Command '['pydeface']' returned non-zero exit status 1.
fmri_bids_recon.errors.ToolUnavailableError: Defacing tool 'pydeface' failed on sub-001_ses-01_T1w.nii.gz: exit code 1
/Users/tjkeding/bids-recon/fmri_bids_recon/deface.py:125</traceback>
      </failure>
    </failures>
  </pre_design_run>
  <failing_test_dispositions>
    <disposition test="test_an_absent_defacing_tool_stops_rather_than_reporting_success" file="tests/test_deface.py" classification="obsolete-test">
      <intended_contract>deface() must fail loudly (never silently report an empty output list) when the defacing tool binary is absent, per the test's own docstring comment.</intended_contract>
      <current_test_claim>with pytest.raises(FileNotFoundError): deface(study)</current_test_claim>
      <evidence>fmri_bids_recon/deface.py:134-141 (the except FileNotFoundError block that re-raises as ToolUnavailableError, added this session); bids-recon_clean_20260826_225214.md finding F3 (locked resolution: wrap and re-raise as ToolUnavailableError so main() maps the failure to exit 4); bids-recon_implement_plan_20260826_225753.md change C3.</evidence>
      <action>re-express: changed the expected exception type from FileNotFoundError to ToolUnavailableError; strengthened by asserting excinfo.value.__cause__ is the original FileNotFoundError (verifies the "from exc" chain) and excinfo.value.context["tool"] == "pydeface". The fail-loud postcondition is preserved; the assertion is strictly more specific than before.</action>
    </disposition>
    <disposition test="test_a_defacing_tool_that_fails_stops_rather_than_reporting_success" file="tests/test_deface.py" classification="obsolete-test">
      <intended_contract>deface() must fail loudly when the defacing tool exits non-zero, per the test's own docstring comment ("must still stop the pipeline rather than be swallowed here").</intended_contract>
      <current_test_claim>with pytest.raises(subprocess.CalledProcessError): deface(study)</current_test_claim>
      <evidence>fmri_bids_recon/deface.py:124-133 (the except CalledProcessError block that re-raises as ToolUnavailableError, added this session); bids-recon_clean_20260826_225214.md finding F3 (same locked resolution as above); bids-recon_implement_plan_20260826_225753.md change C3.</evidence>
      <action>re-express: changed the expected exception type from subprocess.CalledProcessError to ToolUnavailableError; strengthened by asserting excinfo.value.__cause__ is the original CalledProcessError, excinfo.value.context["tool"] == "pydeface", and excinfo.value.context["returncode"] == 1. The fail-loud postcondition is preserved; the assertion is strictly more specific than before.</action>
    </disposition>
  </failing_test_dispositions>
  <design_phase>
    <tests_created>3</tests_created>
    <tests_modified>2</tests_modified>
    <files_created>
      <file path="tests/test_deface.py" test_count="0 (2 modified)" coverage_target="re-express 2 obsolete exit-code assertions per the dispositions above" />
      <file path="tests/test_config.py" test_count="1" coverage_target="TaskRegistryEntry.prefix round-trips through save_registry()/load_config() (config.py half of the prefix-persistence fix)" />
      <file path="tests/conftest.py" test_count="0 (fixture change)" coverage_target="registry_entry fixture gains a prefix parameter, required by the new test_runs.py coverage below" />
      <file path="tests/test_runs.py" test_count="1" coverage_target="check_volume_counts() carries prefix and signature from a prior registry entry into the merged entry (runs.py half of the prefix-persistence fix)" />
      <file path="tests/test_cli_integration.py" test_count="1" coverage_target="the written conversion report's engine_version line shows the package version, distinct from the mocked dcm2niix version" />
    </files_created>
    <design_rationale>
      Two dispositions required re-expression per the Test Design Discipline (both obsolete-test,
      driven by the locked, user-approved exit-code fix from the preceding implement build). The
      remaining three additions close coverage gaps identified by cross-referencing the just-built
      changes against the existing suite: TaskRegistryEntry.prefix had a signature-round-trip
      sibling test in test_config.py but no prefix equivalent; check_volume_counts() had a
      first_seen-preservation sibling test in test_runs.py but nothing proving prefix/signature
      also survive the merge (the exact defect class the prior clean-mode finding described); and
      no test anywhere distinguished engine_version from dcm2niix_version at the pipeline level,
      so the previous defect (both fields carrying the dcm2niix version) could recur silently. The
      _emit_series extraction (stage4_assemble.py) is a pure refactor with no behavioral contract
      change and is already covered by the existing 35-test assembly suite (all passed in both
      runs); no new tests were added for it. The non-reentrancy docstring change is documentation
      only and requires no test.
    </design_rationale>
  </design_phase>
  <post_design_run>
    <total>639</total>
    <passed>544</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct />
    <failures />
  </post_design_run>
  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>0</bugs_routed_to_implement>
    <recommendation>proceed_to_document</recommendation>
  </summary>
  <action_items />
</test_report>
