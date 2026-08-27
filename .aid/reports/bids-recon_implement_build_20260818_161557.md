<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-08-18T16:15:57Z" />
  <spec_ref>bids-recon_implement_plan_20260818_143000.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools.lock.yaml" lines_changed="14" />
        <file path="fmri_bids_recon/tool_registry.py" lines_changed="1" />
      </files_modified>
      <notes>Lockfile key renamed from `tools` to `binaries`, `pin` to `pin_class`, `version_cmd` to `version_flag`. Enforcement field added to flirt entry. tool_registry.py updated to read `binaries` key.</notes>
    </change>

    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools.lock.yaml" lines_changed="1" />
        <file path="fmri_bids_recon/tool_registry.py" lines_changed="17" />
      </files_modified>
      <notes>Python version pin added to lockfile. Runtime floor check added to preflight_tool_environments() before the binaries loop, reporting via ToolStatus with pin_class B.</notes>
    </change>

    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/warnings.py" lines_changed="6" />
      </files_modified>
      <notes>Replaced SEVERITY_WARN/SEVERITY_INFO with three-level taxonomy: SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH. graded_warning() signature unchanged.</notes>
    </change>

    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="4" />
      </files_modified>
      <notes>UNCLASSIFIED_SERIES and NAVIGATOR_CANDIDATE mapped to SEVERITY_LOW. AMBIGUOUS_CLASSIFICATION mapped to SEVERITY_MEDIUM.</notes>
    </change>

    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/runs.py" lines_changed="18" />
      </files_modified>
      <notes>VOLUME_COUNT_MISMATCH elevated from graded_warning to GuardError with context dict. VOLUME_COUNT_DRIFT mapped to SEVERITY_HIGH. Dead code (surviving_bolds append after mismatch) removed.</notes>
    </change>

    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage4_assemble.py" lines_changed="22" />
      </files_modified>
      <notes>UNPAIRED_FIELDMAP elevated from graded_warning + sourcedata copy + continue to GuardError with context dict. PATIENT_ID_WARNING elevated from patient_id_warnings list accumulation to graded_warning(SEVERITY_HIGH) followed by GuardError. patient_id_warnings variable removed; AssemblyResult constructed with patient_id_warnings=[].</notes>
    </change>

    <change id="C7" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" lines_changed="12" />
      </files_modified>
      <notes>Exit code 3 union gating: triggers on BIDS validation errors OR high-severity graded_warnings. Exit code 4/5 docstring updated. Dedicated ToolVersionError handler added before ConfigError to map version mismatches to exit code 4 (was incorrectly caught by BidsReconError handler as exit code 2).</notes>
    </change>

    <change id="C8" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/pipeline.py" lines_changed="2" />
      </files_modified>
      <notes>Added output_dir: Path as a positional field on BidsReconResult (after manifest_path, before defaulted fields). Set to bids_root / "derivatives" / "fmri-bids-recon" in result construction.</notes>
    </change>

    <change id="C9" status="done" user_decision="n/a">
      <files_modified>
        <file path="pyproject.toml" lines_changed="11" />
      </files_modified>
      <notes>Appended [tool.pytest.ini_options] with 8-level marker taxonomy (level0_unit through level7_pipeline). Per-function marker assignment deferred to /test.</notes>
    </change>
  </changes_applied>

  <summary>
    <total_changes>9</total_changes>
    <completed>9</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>

  <next_steps>Recommended: run /test to validate all changes. Key areas requiring new or updated tests:
    - Lockfile key renames (test fixtures referencing `tools`/`pin`/`version_cmd` must be updated to `binaries`/`pin_class`/`version_flag`)
    - Python version floor check in preflight_tool_environments()
    - Three-level severity vocabulary across all call sites
    - Halt elevation: VOLUME_COUNT_MISMATCH, UNPAIRED_FIELDMAP, PATIENT_ID_WARNING now raise GuardError
    - Exit code 3 union gating (BIDS errors OR high-severity warnings)
    - ToolVersionError mapped to exit code 4
    - BidsReconResult.output_dir field
    - Per-function marker assignment (deferred from this build)
  </next_steps>
</implement_report>
