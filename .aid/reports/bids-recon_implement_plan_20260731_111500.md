<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-31T16:40:00-04:00" />
  <input_reports>
    <report path="MODS_NEEDED.md" mode="external (fmri-preproc integration testing)" key_items="3" />
  </input_reports>
  <assumptions>
    <assumption id="A1">Intensity rescaling preserves the existing inter-tissue contrast ratios (relative ordering per modality) rather than re-deriving contrasts from MRI physics equations. Rationale: the existing ratios were designed during the 2026-07-30 tissue synthesis brainstorm; the blocking issue is absolute scale (~1000x too low), not relative contrast.</assumption>
    <assumption id="A2">The per-modality scale factors (~920x for T1w, ~1000x for T2w/T2*/DWI) are chosen to place the brightest tissue class in the 700-950 AU range, consistent with typical 3T Siemens Prisma int16 output after dcm2niix conversion.</assumption>
    <assumption id="A3">SNR targets (SNR_T1W=40, SNR_BOLD=25, etc.) are not modified. The Rician noise model computes sigma = mean_signal / target_snr, so absolute noise levels auto-scale with the rescaled intensities. These SNR values are within reasonable 3T ranges for their respective sequences.</assumption>
    <assumption id="A4">Full regeneration of both datasets (~3h) is required because the intensity lookup tables are consumed during synthesis (Phase 1), not post-generation. Targeted re-application of adversaries alone (the prior C4 approach) is insufficient.</assumption>
  </assumptions>
  <changes>
    <change id="C1" priority="P1" source_item="A16 section of MODS_NEEDED.md">
      <file path="tools/simulated_bids/adversaries.py" action="modify" />
      <description>Retarget A16 from T1w anat to BOLD func. The current implementation modifies pixdim4 on T1w files only, which is invisible to fmri-preproc (BOLD pipeline). Retarget to all BOLD func files in the affected session: set NIfTI pixdim4=0.0 and JSON sidecar RepetitionTime=2.5.</description>
      <spec>
1. ADVERSARY_MATRIX entry for sub-005 A16: change target from "t1w_pixdim4_mismatch" to "bold_pixdim4_tr_mismatch". Details unchanged: {"pixdim4": 0.0, "json_tr": 2.5}.

2. Rewrite apply_A16:
   - For each session in spec["sessions"]:
     - Glob func_dir for *_bold.nii.gz
     - For each BOLD NIfTI: load, set header["pixdim"][4] = spec["details"]["pixdim4"], save
     - For each corresponding JSON sidecar (.json with same stem): load, set RepetitionTime = spec["details"]["json_tr"], save
   - Note: SBRef files are excluded (they share the same TR in clean baseline; the adversary targets BOLD only per the MODS_NEEDED spec)
      </spec>
      <dependencies>none</dependencies>
      <risk>low - post-generation mutation, no upstream dependencies</risk>
      <rollback>Revert the two ADVERSARY_MATRIX + apply_A16 code blocks to their prior state</rollback>
    </change>
    <change id="C2" priority="P1" source_item="A18 section of MODS_NEEDED.md">
      <file path="tools/simulated_bids/adversaries.py" action="modify" />
      <description>Redesign A18 from scl_slope=NaN (indistinguishable from nibabel int16 default) to direct NaN voxel injection in BOLD data. Injects NaN into a contiguous spatial slice across all volumes of rest run-01, exercising fmri-preproc's NONFINITE_BOLD detector (F3).</description>
      <spec>
1. ADVERSARY_MATRIX entry for sub-009 A18: change target from "dwi_scl_slope_nan" to "bold_nan_injection". Add details: {"task": "rest", "run": 1, "nan_slice_idx": 30} (axial slice 30 of 60, roughly mid-brain).

2. Rewrite apply_A18:
   - For each session in spec["sessions"]:
     - Build path: func_dir / f"{sub}_{ses}_task-{task}_run-{run:02d}_bold.nii.gz"
     - Load with nibabel, get float32 data via get_fdata(dtype=np.float32)
     - Set data[:, :, nan_slice_idx, :] = np.nan (one axial slice, all volumes)
     - Re-save as float32 via _save_nifti(..., dtype=np.float32)
   - NaN requires float32 storage (int16 cannot represent NaN). This dtype change is intentional and mirrors A19's float32 cast pattern.
   - NaN fraction: 1 slice / 60 slices = ~1.7% of voxels, well above the report's 0.1% floor.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - post-generation mutation, float32 save uses existing _save_nifti path (proven by A19)</risk>
      <rollback>Revert the two ADVERSARY_MATRIX + apply_A18 code blocks to their prior state</rollback>
    </change>
    <change id="C3" priority="P1" source_item="all three sections of MODS_NEEDED.md">
      <file path="sandbox/verify_dataset.py" action="modify" />
      <description>Update verification checks for A16 and A18 to match the redesigned adversaries, and add an intensity floor check that catches regression to normalized [0, 1] values.</description>
      <spec>
1. A16 check (lines 137-142): change from T1w anat to BOLD func.
   - Target: sub-005/ses-02/func/*task-rest_run-01_bold.nii.gz and corresponding .json
   - Assert pixdim4 == 0.0 (was: pixdim4 != jtr)
   - Assert JSON RepetitionTime == 2.5
   - Combined check: both conditions must hold

2. A18 check (lines 153-156): change from DWI scl_slope to BOLD NaN voxels.
   - Target: sub-009/ses-02/func/*task-rest_run-01_bold.nii.gz
   - Load with get_fdata(), assert np.isnan(data).any()
   - Report NaN fraction for diagnostic clarity

3. Add intensity floor check (new, appended after all adversary checks):
   - Sample one T1w NIfTI from sub-001/ses-01 (clean subject in adversarial dataset, or any subject in clean dataset)
   - Load with get_fdata(), compute non-background mean: d[d > 10].mean()
   - Assert non-background mean > 100 AU (catches regression to [0, 1] normalized range)
   - Assert max intensity > 50 AU
   - Print per-modality intensity summary for diagnostic visibility
      </spec>
      <dependencies>C1, C2, C4 (verify checks must match the redesigned adversaries and rescaled intensities)</dependencies>
      <risk>low - read-only verification script</risk>
      <rollback>Revert the modified and added check blocks</rollback>
    </change>
    <change id="C4" priority="P1" source_item="Intensity Rescaling section of MODS_NEEDED.md">
      <file path="tools/simulated_bids/config.py" action="modify" />
      <description>Rescale per-tissue-class intensity lookup tables from normalized [0, 1] to realistic 3T Siemens Prisma arbitrary units. The current tables produce voxel intensities ~1000x lower than real scanner output, causing degenerate results in downstream binary tools (FastSurfer, TOPUP, ANTs). Each table is multiplied by a per-modality scale factor that brings the maximum tissue intensity into the 700-950 AU range while preserving the existing inter-tissue contrast ratios.</description>
      <spec>
1. Update section comment (line 137) from "normalized 0-1 per tissue class" to "3T Siemens Prisma arbitrary units per tissue class".

2. Replace T1W_INTENSITIES (lines 139-141, scale factor ~920, preserving T1w MPRAGE contrast: WM > GM > CSF):
   T1W_INTENSITIES: dict[int, float] = {
       0: 0.0, 1: 140.0, 2: 600.0, 3: 780.0, 4: 830.0,
       5: 510.0, 6: 510.0, 7: 185.0, 8: 320.0, 9: 370.0,
   }

3. Replace T2W_INTENSITIES (lines 144-146, scale factor ~1000, preserving T2w SPC contrast: CSF > GM > WM):
   T2W_INTENSITIES: dict[int, float] = {
       0: 0.0, 1: 950.0, 2: 700.0, 3: 450.0, 4: 800.0,
       5: 400.0, 6: 400.0, 7: 100.0, 8: 600.0, 9: 300.0,
   }

4. Replace T2STAR_INTENSITIES (lines 150-152, physics-derived combined T1/T2* signal equation at ABCD BOLD parameters TR=0.8s, TE=30ms, FA=52 deg; contrast ordering changes from pure-T2* CSF > GM > WM to T1-dominated WM > CSF > GM):
   T2STAR_INTENSITIES: dict[int, float] = {
       0: 0.0, 1: 587.0, 2: 474.0, 3: 700.0, 4: 350.0,
       5: 250.0, 6: 250.0, 7: 50.0, 8: 300.0, 9: 200.0,
   }
   Physics basis: S = sin(FA) * (1 - exp(-TR/T1)) / (1 - cos(FA)*exp(-TR/T1)) * exp(-TE/T2*).
   At TR=0.8s, T1 recovery is incomplete (WM~62%, GM~46%, CSF~18%), and this T1 weighting
   dominates the T2* decay at TE=30ms, yielding WM > CSF > GM. Non-parenchymal classes
   retain their proportional relationship to the maximum (scaled 1000x from current values)
   since they do not materially affect FastSurfer/TOPUP/ANTs processing.

5. Replace DWI_S0_INTENSITIES (lines 156-158, scale factor ~1000, preserving T2-weighted DWI b=0 contrast: CSF > GM > WM):
   DWI_S0_INTENSITIES: dict[int, float] = {
       0: 0.0, 1: 900.0, 2: 650.0, 3: 500.0, 4: 750.0,
       5: 350.0, 6: 350.0, 7: 80.0, 8: 550.0, 9: 250.0,
   }

6. NOT modified:
   - DWI_ADC: physical ADC coefficients in mm^2/s (not arbitrary intensity units)
   - SNR targets: auto-scale via sigma = mean_signal / target_snr
   - All other config constants: B1_AMPLITUDE, DRIFT_AMPLITUDE, FC_AMPLITUDE, SPIKE_MAGNITUDE are fractional or SD-relative, so they auto-scale correctly
   - _save_nifti in modalities.py: int16 quantization with scl_slope/scl_inter auto-adapts to the new data range (slope = (dmax - dmin) / 4095)

Note: the existing tests/simulated_bids/ suite (87 tests) may contain assertions calibrated to [0, 1] intensity ranges. After this change, run /test to identify and update any affected assertions.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - numeric constant change only; all downstream computations auto-scale</risk>
      <rollback>Revert the four intensity dictionaries and section comment to their prior values</rollback>
    </change>
    <change id="C5" priority="P1" source_item="Intensity Rescaling section of MODS_NEEDED.md (both datasets)">
      <file path="~/simulated-bids/{adversarial,clean}/" action="regenerate (full, both datasets)" />
      <description>Regenerate both adversarial and clean datasets from scratch via /run-local. The intensity rescaling (C4) modifies the synthesis step, requiring full regeneration rather than targeted adversary re-application. The fixed adversaries (C1, C2) are automatically applied during the generator's Phase 3 (adversarial profile only). Both datasets share the same intensity lookup tables and must both be regenerated.</description>
      <spec>
1. Execute via /run-local for both profiles:
   - Adversarial: 13 subjects x 3 sessions, seed=42, ~128 min estimated
   - Clean: 4 subjects x 3 sessions, seed=1729, ~38 min estimated
   - Output to ~/simulated-bids/{adversarial,clean}/ (overwrite in place)

2. The generator's Phase 3 automatically applies all 31 adversaries (adversarial profile only) using the fixed A16 (C1) and A18 (C2) code.

3. Post-generation verification (both datasets):
   - Run verify_dataset.py (updated by C3) against adversarial: all 31 adversaries must PASS
   - Run intensity floor check (added by C3) against both datasets: non-background mean > 100 AU for all sampled NIfTI files
   - Spot-check T1w and BOLD intensity distributions to confirm realistic 3T range

4. Expected dataset characteristics:
   - Sizes: ~40 GB adversarial, ~13 GB clean (unchanged order of magnitude; int16 quantization to 4095 levels is independent of absolute scale)
   - T1w WM intensity: ~780 AU (was ~0.85)
   - BOLD WM intensity: ~700 AU (was ~0.40; now brightest due to T1-dominated contrast at TR=0.8s)
   - Wall-clock: ~3 hours total (sequential adversarial + clean)
      </spec>
      <dependencies>C1, C2, C3, C4 (all code changes must be in place before regeneration)</dependencies>
      <risk>medium - overwrites existing datasets (~53 GB total); datasets are fully regenerable from code</risk>
      <rollback>Regenerate datasets with original config.py intensity tables (~3 hours)</rollback>
    </change>
  </changes>
  <execution_order>C1, C2, C4 (parallelizable: independent files), C3, C5</execution_order>
</implement_plan>
