<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-07-24T13:30:00-04:00" />
  <spec_ref>bids-recon_implement_plan_20260724_130000.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/config.py" lines_changed="5" />
      </files_modified>
      <notes>Added deface:bool field to StudyConfig docstring, dataclass field (default False), YAML parsing in load_config(), and constructor argument. Mirrors the existing physio toggle pattern exactly.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/deface.py" lines_changed="18" />
      </files_modified>
      <notes>Added ToolUnavailableError import and assert_deface_tools() function. Removed the try/except FileNotFoundError handler around subprocess.run calls, unwrapping the subprocess calls to sit directly in the for-loop body. Both CalledProcessError and FileNotFoundError now propagate naturally (hard enforcement).</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" lines_changed="9" />
      </files_modified>
      <notes>Updated deface import to include assert_deface_tools. Added deface pre-flight block after the dcm2niix version check, gated on config.deface, catching ToolUnavailableError with exit code 4. Gated the Phase 5 deface call on config.deface.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="config/study.example.yaml" lines_changed="5" />
      </files_modified>
      <notes>Added deface: false field with FSL requirement comment, mirroring the physio entry.</notes>
    </change>
    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="README.md" lines_changed="2" />
      </files_modified>
      <notes>Added FSL to Prerequisites section (conditional on deface: true). Annotated pydeface row in Dependencies table with "(requires FSL `flirt` on PATH)".</notes>
    </change>
    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="INPUT_SPECIFICATION.md" lines_changed="2" />
      </files_modified>
      <notes>Updated FSL enforcement column from "Soft" to conditional enforcement. Updated Known Limitations to describe the pre-flight check behavior.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>6</total_changes>
    <completed>6</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate all changes. Specific test work needed: re-express test_deface.py FileNotFoundError test (currently asserts caught + empty return; FileNotFoundError now propagates), add tests for assert_deface_tools() (raises ToolUnavailableError when pydeface/flirt absent), add config toggle tests (deface defaults to False, parses True from YAML).</next_steps>
</implement_report>
