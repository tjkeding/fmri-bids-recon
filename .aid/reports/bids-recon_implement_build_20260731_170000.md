<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-07-31T17:00:00-04:00" />
  <spec_ref>bids-recon_implement_plan_20260731_111500.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/adversaries.py" lines_changed="12" />
      </files_modified>
      <notes>Retargeted the ADVERSARY_MATRIX entry from "t1w_pixdim4_mismatch" to "bold_pixdim4_tr_mismatch". Rewrote the apply function to glob BOLD func NIfTI files, set pixdim4=0.0, and update the corresponding JSON sidecar RepetitionTime=2.5. Uses .with_suffix("").with_suffix(".json") to locate sidecars by stem.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/adversaries.py" lines_changed="12" />
      </files_modified>
      <notes>Redesigned the ADVERSARY_MATRIX entry from "dwi_scl_slope_nan" to "bold_nan_injection" with details for task, run, and slice index. Rewrote the apply function to load BOLD data as float32, inject NaN into axial slice 30 across all volumes, and re-save via _save_nifti with dtype=np.float32 (matching the existing float32 pattern used by the mixed-dtype adversary).</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="sandbox/verify_dataset.py" lines_changed="20" />
      </files_modified>
      <notes>Updated the verification check to target BOLD func (not T1w anat), asserting pixdim4==0.0 and JSON RepetitionTime==2.5. Updated the verification check to target BOLD func NaN voxels (not DWI scl_slope), with fraction reporting. Added an intensity floor check sampling sub-001/ses-01 T1w, asserting non-background mean > 100 AU and max > 50 AU.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools/simulated_bids/config.py" lines_changed="9" />
      </files_modified>
      <notes>Rescaled all four intensity lookup tables to 3T Siemens Prisma arbitrary units. T1w: ~920x (WM=780, GM=600, CSF=140). T2w: ~1000x (CSF=950, GM=700, WM=450). T2*: physics-derived combined T1/T2* signal (WM=700, CSF=587, GM=474; ordering changed from CSF>GM>WM to WM>CSF>GM per TR=0.8s T1 saturation). DWI S0: ~1000x (CSF=900, GM=650, WM=500). Updated section comment from "normalized 0-1" to "3T Siemens Prisma arbitrary units". DWI_ADC and SNR targets unchanged (auto-scale).</notes>
    </change>
    <change id="C5" status="skipped" user_decision="defer">
      <files_modified />
      <notes>Dataset regeneration is an operational step designated by the spec as a /run-local task. Both adversarial (13 subjects x 3 sessions, ~128 min) and clean (4 subjects x 3 sessions, ~38 min) datasets require full regeneration because the intensity lookup tables are consumed during synthesis (Phase 1). Deferred to /run-local invocation after /test validates the code changes.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>5</total_changes>
    <completed>4</completed>
    <skipped>1</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>
    1. Run /test to validate all code changes (the 87 tests in tests/simulated_bids/ may have assertions calibrated to the old [0, 1] intensity range that need updating).
    2. Run /run-local to regenerate both datasets with the rescaled intensities and fixed adversaries.
    3. After regeneration, run verify_dataset.py against both datasets to confirm all 31 adversaries PASS and intensity floor check passes.
  </next_steps>
</implement_report>
