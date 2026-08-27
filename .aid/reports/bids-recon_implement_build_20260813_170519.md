<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-08-13T17:05:19Z" />
  <spec_ref>bids-recon_implement_plan_20260813_164648.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/warnings.py" lines_changed="34" />
      </files_modified>
      <notes>Created graded_warning() framework with SEVERITY_WARN and SEVERITY_CRITICAL constants. Signature, return schema, and log-line format match fmri-preproc verbatim.</notes>
    </change>

    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools.lock.yaml" lines_changed="19" />
        <file path="fmri_bids_recon/tool_registry.py" lines_changed="195" />
        <file path="fmri_bids_recon/errors.py" lines_changed="15" />
      </files_modified>
      <notes>Created lockfile with dcm2niix (Class A), pydeface (Class B, conditional), flirt (Class A, conditional, declarative). Created tool_registry.py with preflight_tool_environments(), ToolStatus, ToolReport. Added ToolVersionError to errors.py, deprecated VersionFloorError with docstring note.</notes>
    </change>

    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/config.py" lines_changed="120" />
      </files_modified>
      <notes>Refactored monolithic load_config() into _load_raw(), _validate_raw(), _resolve_config() 3-stage pipeline. Added schema_version and config_path fields to StudyConfig. Created load_and_validate() as public API with subject parameter for orchestrator single-subject mode. Retained load_config() as thin backward-compat wrapper.</notes>
    </change>

    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="25" />
        <file path="fmri_bids_recon/runs.py" lines_changed="20" />
        <file path="fmri_bids_recon/stage4_assemble.py" lines_changed="15" />
        <file path="fmri_bids_recon/json_intermediate.py" lines_changed="12" />
        <file path="fmri_bids_recon/report.py" lines_changed="4" />
        <file path="fmri_bids_recon/errors.py" lines_changed="6" />
        <file path="tests/test_classify.py" lines_changed="6" />
        <file path="tests/test_runs.py" lines_changed="4" />
        <file path="tests/test_json_intermediate.py" lines_changed="10" />
      </files_modified>
      <notes>Migrated all 6 ReviewFlag instantiation sites to graded_warning() with appropriate codes (UNCLASSIFIED_SERIES, NAVIGATOR_CANDIDATE, AMBIGUOUS_CLASSIFICATION, VOLUME_COUNT_MISMATCH, VOLUME_COUNT_DRIFT, UNPAIRED_FIELDMAP). Removed ReviewFlag encoder/decoder from json_intermediate.py. Updated report rendering to structured format. Deprecated ReviewFlag class in errors.py. Updated 3 test files to assert on dict keys instead of ReviewFlag.context attributes.</notes>
    </change>

    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/pipeline.py" lines_changed="260" />
      </files_modified>
      <notes>Created pipeline.py with BidsReconResult dataclass and run() function. Extracted all pipeline logic from __main__.py. run() does not call sys.exit() or set up logging. Exceptions propagate to caller. Version string obtained from tool_report instead of assert_dcm2niix_version(). config_path falls back to config.config_path for report provenance.</notes>
    </change>

    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" lines_changed="155" />
        <file path="tests/test_cli_integration.py" lines_changed="25" />
      </files_modified>
      <notes>Rewrote __main__.py as thin CLI wrapper: _setup_logging() factory (console to stderr at INFO, optional file at DEBUG), dual-form config argument (positional or --config), --subject, --log-file, --strict-versions. Exit code mapping in main() docstring. Updated test_cli_integration.py to target pipeline_mod for AST scanning and monkeypatches.</notes>
    </change>

    <change id="C7" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__init__.py" lines_changed="3" />
      </files_modified>
      <notes>Added public API exports: load_and_validate from config, run and BidsReconResult from pipeline.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>7</total_changes>
    <completed>7</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <test_results>429 passed, 91 skipped, 0 failed (bids-recon conda env)</test_results>
  <next_steps>Recommended: run /test to validate all changes, migrate test_versions.py to use tool_registry, apply function-level 8-level test taxonomy markers, and add test coverage for the new public API (load_and_validate, run, BidsReconResult).</next_steps>
</implement_report>
