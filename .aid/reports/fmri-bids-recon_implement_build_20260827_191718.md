<implement_report>
  <meta project="fmri-bids-recon" mode="implement" submodule="build" timestamp="2026-08-27T19:17:18Z" />
  <spec_ref>fmri-bids-recon_implement_plan_20260827_191254.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="1" />
      </files_modified>
      <notes>Added DROP_CALIBRATION = "drop_calibration" to Role enum after DROP_ANAT_ND_T2W, before UNCLASSIFIED.</notes>
    </change>
    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="5" />
      </files_modified>
      <notes>Updated module docstring and classify() function docstring to document the calibration sequence exclusion pass.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="34" />
      </files_modified>
      <notes>Inserted modality-scoped PE axis validation pass after the NORM/ND twin resolution pass. FMAP_FUNC checked against BOLD PE axes, FMAP_DWI against DWI PE axes, with empty-target bypass and graded_warning at medium severity on demotion.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="28" />
      </files_modified>
      <notes>Added _CALIBRATION_KEYWORDS constant and compound keyword guard pass. Requires keyword match AND single-volume AND description stem mismatch vs target modality. Series already demoted by the PE axis pass are skipped.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage4_assemble.py" lines_changed="2" />
      </files_modified>
      <notes>Updated the DROP_* comment to explicitly list DROP_CALIBRATION alongside DROP_DERIVED, DROP_SCOUT, and DROP_NAVIGATOR.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>5</total_changes>
    <completed>5</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate the calibration exclusion guard against the vNav setter scenario, empty-target bypass, matching PE axis pass-through, and compound keyword guard edge cases.</next_steps>
</implement_report>
