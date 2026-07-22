<test_report>
  <meta project="fmri-bids-recon" mode="test" timestamp="2026-07-22T20:33:00Z" />

  <pre_design_run>
    <total>409</total>
    <passed>324</passed>
    <failed>37</failed>
    <errors>46</errors>
    <coverage_pct />
    <failures>
      <failure test="test_a_well_formed_config_loads" file="tests/test_config.py" line="59">
        <error_type>KeyError</error_type>
        <message>KeyError: 'dicom_template'</message>
        <traceback>fmri_bids_recon/config.py:213: dicom_template = str(raw["dicom_template"]); fixture still writes the old "dicom_pattern" key.</traceback>
      </failure>
      <failure test="test_a_clean_session_runs_end_to_end" file="tests/test_cli_integration.py" line="178">
        <error_type>AssertionError</error_type>
        <message>assert 2 == 0 (Configuration load failed: 'dicom_template')</message>
        <traceback>Same root cause: inline config dict at test_cli_integration.py:129 still writes "dicom_pattern".</traceback>
      </failure>
      <failure test="test_anatomical_lands_under_anat_with_the_t1w_suffix (ERROR at setup)" file="tests/test_assemble.py" line="430">
        <error_type>TypeError</error_type>
        <message>StudyConfig.__init__() got an unexpected keyword argument 'dicom_pattern'</message>
        <traceback>conftest.py:434 study_config fixture still passes dicom_pattern= kwarg to StudyConfig, which no longer declares that field.</traceback>
      </failure>
      <failure test="test_an_unsupported_tool_is_refused_before_anything_is_written[mri_deface] (ERROR at setup)" file="tests/test_deface.py" line="39">
        <error_type>TypeError</error_type>
        <message>StudyConfig.__init__() got an unexpected keyword argument 'dicom_pattern'</message>
        <traceback>test_deface.py's local study fixture, same stale kwarg.</traceback>
      </failure>
    </failures>
  </pre_design_run>

  <failing_test_dispositions>
    <disposition test="test_a_well_formed_config_loads and all 27 other tests in tests/test_config.py using the study fixture" file="tests/test_config.py" classification="obsolete-test">
      <intended_contract>The study() fixture writes a well-formed YAML config that exercises the current load_config() schema.</intended_contract>
      <current_test_claim>raw["dicom_pattern"] = "{sub}/{ses}"</current_test_claim>
      <evidence>fmri_bids_recon/config.py:213 requires raw["dicom_template"] and config.py:214-221 validates the {subject} and {session} placeholders; this schema change was applied by the implement build recorded in fmri-bids-recon_implement_build_20260722_173500.md, change C1. The fixture was never updated because /implement build's write scope excludes tests/.</evidence>
      <action>re-express — rename the fixture's dict key from dicom_pattern to dicom_template and its placeholder value from {sub}/{ses} to {subject}/{session}; no assertion in any dependent test was touched or weakened</action>
    </disposition>

    <disposition test="test_a_clean_session_runs_end_to_end and the other 8 tests in tests/test_cli_integration.py using the inline config fixture" file="tests/test_cli_integration.py" classification="obsolete-test">
      <intended_contract>The inline config dict at line 125 constructs a well-formed study YAML for full end-to-end CLI invocation tests.</intended_contract>
      <current_test_claim>raw["dicom_pattern"] = "{sub}/{ses}" (line 129)</current_test_claim>
      <evidence>Same root cause as test_config.py: config.py:213 now requires the dicom_template key.</evidence>
      <action>re-express — same rename, single line (test_cli_integration.py:129)</action>
    </disposition>

    <disposition test="every test that consumes the shared study_config fixture across tests/test_assemble.py, tests/test_map.py, tests/test_render.py" file="tests/conftest.py" classification="obsolete-test">
      <intended_contract>study_config is a StudyConfig instance constructed directly (bypassing YAML) with staging_root outside bids_root, as load_config would produce.</intended_contract>
      <current_test_claim>StudyConfig(..., dicom_pattern="{sub}/{ses}", ...) at conftest.py:434</current_test_claim>
      <evidence>fmri_bids_recon/config.py's StudyConfig dataclass (line 123) declares the field as dicom_template, not dicom_pattern; constructing with the old kwarg raises TypeError before the test body runs. This is the single most load-bearing fixture in the suite: its cascade accounts for the majority of the 46 setup errors (test_assemble.py: 18, test_map.py: 1, test_render.py: 4, plus 15 more in test_deface.py's separate local fixture).</evidence>
      <action>re-express — rename the constructor kwarg from dicom_pattern to dicom_template; StudyConfig's other fields and the participant fixture are untouched</action>
    </disposition>

    <disposition test="every test that consumes the local study fixture in tests/test_deface.py" file="tests/test_deface.py" classification="obsolete-test">
      <intended_contract>study is a StudyConfig instance with a T1w already staged in bids_root, used to exercise the defacing stage independent of the full pipeline.</intended_contract>
      <current_test_claim>StudyConfig(..., dicom_pattern="{sub}/{ses}", ...) at test_deface.py:43</current_test_claim>
      <evidence>Same TypeError as the conftest.py fixture; this is a separate, file-local fixture (not the shared study_config), so it required its own rename.</evidence>
      <action>re-express — rename the constructor kwarg; no other change</action>
    </disposition>
  </failing_test_dispositions>

  <design_phase>
    <tests_created>9</tests_created>
    <tests_modified>0</tests_modified>
    <files_created>
      <file path="tests/test_config_template_and_subjects_file.py" test_count="9" coverage_target="Two code paths introduced by the config field rename (fmri_bids_recon/config.py:213-250) that had zero prior test coverage: (1) dicom_template placeholder validation — missing {subject} raises ValueError, missing {session} raises ValueError, and a template with literal directory segments interleaved with both placeholders resolves correctly; (2) subjects specified as an absolute path to a single-column text file — happy path, blank-line and #-comment skipping, relative-path rejection, missing-file rejection, zero-valid-entries rejection, and unsupported-type (non-str, non-list) rejection." />
    </files_created>
    <files_modified />
    <design_rationale>
      All 83 pre-design failures/errors traced to a single pattern: four test fixtures (tests/test_config.py's study, tests/test_cli_integration.py's inline config dict, tests/conftest.py's shared study_config, tests/test_deface.py's local study) still used the pre-rename dicom_pattern key/kwarg and {sub}/{ses} placeholders. This is expected fixture drift, not a product regression: /implement build's write scope is restricted to non-test files, so the field rename in fmri_bids_recon/config.py could not update tests/ in the same invocation. Every disposition in this report is obsolete-test, re-expressed as a pure rename with zero assertion weakening. Separately, the same implement build introduced two new code paths (dicom_template placeholder validation and subjects-as-file-path) with no prior test coverage at all, since they are new features rather than modifications to existing tested behavior; the design phase closed both gaps with 9 new tests grounded directly in the implementation at fmri_bids_recon/config.py:213-250.
    </design_rationale>
  </design_phase>

  <post_design_run>
    <total>418</total>
    <passed>416</passed>
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
