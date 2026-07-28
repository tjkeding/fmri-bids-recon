<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-07-28T13:05:00Z" />
  <spec_ref>bids-recon_implement_plan_20260728_091500.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/deface.py" lines_changed="56" />
      </files_modified>
      <notes>Added _resolve_flirt() for FSLDIR-based tool resolution with PATH fallback. Rewrote assert_deface_tools() to use _resolve_flirt() and provide FSLDIR hint in error message. Added _ensure_fsl_env() to append $FSLDIR/bin to PATH and set FSLOUTPUTTYPE before subprocess calls. deface() now calls _ensure_fsl_env() after tool validation.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/config.py" lines_changed="4" />
      </files_modified>
      <notes>Updated deface field docstring to reference FSLDIR environment variable resolution with PATH fallback, replacing prior "on PATH" phrasing.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path=".gitignore" lines_changed="1" />
      </files_modified>
      <notes>Changed bids-recon_*.md pattern to /bids-recon_*.md (root-only match) so .aid/reports/ markdown files no longer require git add -f.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="README.md" lines_changed="4" />
      </files_modified>
      <notes>Replaced two GitHub URL placeholders (pip install, git clone) with the repository owner username. Updated FSL prerequisite description and pydeface dependency table to reference FSLDIR resolution with PATH fallback.</notes>
    </change>
    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="INPUT_SPECIFICATION.md" lines_changed="4" />
      </files_modified>
      <notes>Updated all 4 deface/FSL references: config field description, pydeface dependency table, FSL external tool notes, and known-limitations item. All now describe FSLDIR-based resolution with PATH fallback.</notes>
    </change>
    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="RUNBOOK.md" lines_changed="78" />
      </files_modified>
      <notes>Replaced GitHub URL placeholder with the repository owner username. Fixed stale dicom_pattern to dicom_template with updated variable names. Added new Section 7 (HPC Deployment) with subsections 7.1 Install, 7.2 Run, 7.3 How the pipeline handles module contamination. Renumbered Quick reference to Section 8 and added HPC variant code block.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>6</total_changes>
    <completed>6</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to design new tests for _resolve_flirt, _ensure_fsl_env, and the updated assert_deface_tools. The existing test suite (434 tests) covers the prior implementation but does not exercise the FSLDIR-based resolution paths or the _ensure_fsl_env PATH/FSLOUTPUTTYPE manipulation.</next_steps>
</implement_report>
