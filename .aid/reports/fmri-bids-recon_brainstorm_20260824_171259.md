<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-08-24T17:12:59Z" source_project="fmri-proc-orchestrator" source_report="fmri-proc-orchestrator_brainstorm_20260824_140104.md" />
  <context_files>
    <file path="fmri_bids_recon/warnings.py" relevance="T3/T4: graded_warning return dict and accumulator implementation site" />
    <file path="fmri_bids_recon/pipeline.py" relevance="T4/T6: warning accumulation consumer, fieldmap target filtering, no-fieldmap early-out" />
    <file path="fmri_bids_recon/stage2_classify.py" relevance="T5: all 10 classification rules, vendor-agnostic broadening" />
    <file path="fmri_bids_recon/stage1_convert.py" relevance="T5/C8: dcm2niix invocation flags" />
    <file path="fmri_bids_recon/stage3_map.py" relevance="T6: FieldmapCoverageError raise sites, Mapping class, map_fieldmaps" />
    <file path="fmri_bids_recon/sidecar.py" relevance="T5: modality_token() and Series dataclass fields" />
    <file path="fmri_bids_recon/runs.py" relevance="T6: check_volume_counts exclusion list, task_registry contamination analysis" />
    <file path="fmri_bids_recon/errors.py" relevance="T6: FieldmapCoverageError as GuardError subclass" />
    <file path="fmri_bids_recon/stage4_assemble.py" relevance="T4: PATIENT_ID_MISMATCH graded_warning visibility confirmation" />
    <file path="fmri-bids-recon_brainstorm_20260824_140104.md" relevance="Input: orchestrator-generated harmonization report (T3, T4)" />
  </context_files>
  <topics>
    <topic id="T3" title="graded_warning return dict: add user_facing to four-key schema">
      <summary>The cross-pipeline contract for graded_warning return dicts standardizes four keys: {severity, code, message, user_facing}. bids-recon's warnings.py returns only three keys (missing user_facing). The user_facing parameter already exists in the function signature; only the return dict needs updating.</summary>
      <research>No external research required. The four-key schema is defined by the fmri-proc-orchestrator harmonization audit. The user_facing parameter is already in the graded_warning signature (warnings.py:22, default False); the return dict at line 33 omits it.</research>
      <approaches>
        <approach id="A1" label="Add user_facing to return dict" feasibility="high" risk="low">
          <description>Add "user_facing": user_facing to the return dict in warnings.py graded_warning(). Single-line change.</description>
          <pros>Completes the four-key contract. Zero risk of breaking existing consumers (they use dict access, and adding a key is backward-compatible).</pros>
          <cons>None.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Straightforward contract completion. The parameter already exists; only the return statement needs the fourth key.</decision>
    </topic>

    <topic id="T4" title="Warning accumulation: add module-level _WARNING_ACCUMULATOR">
      <summary>The cross-pipeline contract standardizes warning accumulation via a module-level _WARNING_ACCUMULATOR list with get_warnings()/clear_warnings() API. bids-recon's pipeline.py currently collects warnings manually via all_review_flags (lines 135, 203, 298, 323). The accumulator pattern must be adopted for plumbing consistency across sister modules.</summary>
      <research>No external research required. Verified that the PATIENT_ID_MISMATCH graded_warning in stage4_assemble.py (lines 533-549) is fire-and-forget before a GuardError raise, so the accumulator append is harmless (the GuardError path never reaches get_warnings()). No warning visibility is lost.</research>
      <approaches>
        <approach id="A1" label="Module-level accumulator, pipeline consumer" feasibility="high" risk="low">
          <description>Add _WARNING_ACCUMULATOR (list[dict]), get_warnings() -> list[dict], and clear_warnings() -> None to warnings.py. Have graded_warning() auto-append each return dict to the accumulator. Update pipeline.py: import get_warnings and clear_warnings; call clear_warnings() at pipeline entry; replace all_review_flags with get_warnings() at status determination (line 323). Leave classify() and check_volume_counts() return signatures intact (Option A from discussion).</description>
          <pros>Minimal invasion. Classify/check_volume_counts continue returning their own review_flags lists for intermediate serialization. The accumulator captures all warnings regardless of source, including future call sites.</pros>
          <cons>Dual accumulation paths exist temporarily (accumulator + intermediate JSON review_flags). Acceptable because the intermediate is a serialization concern, not a semantic one.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Option A preserves existing return signatures while adopting the cross-pipeline accumulator contract. The dual-path concern is cosmetic and does not affect correctness.</decision>
    </topic>

    <topic id="T5" title="Vendor-agnostic classifier: physics-based BOLD inference for Siemens/GE/Philips">
      <summary>The classifier depends on ImageType[2] == "FMRI" (a Siemens XA vendor extension) in Rules 3, 5, 8, and 9, making it XA30-only. Siemens pre-XA (E11/VB/VD/VE) uses "M", GE uses "OTHER", and Philips uses "M". An end-user reported NavigatorDropError on Siemens E11 data (Series 12, ImageType[2]='M') because Rule 3 drops multi-volume EPI when tok is not "FMRI" or "DIFFUSION". The pipeline must support Siemens (all platforms), GE, and Philips scanners without error or inappropriate warning when the input is a complete, reconstruction-ready set of DICOMs.</summary>
      <research>
        Five research agents dispatched to investigate:
        (1) Siemens pre-XA DICOM conventions: ImageType[2] = "M" for magnitude images across VB/VD/VE/E11 platforms. No "FMRI" token outside XA.
        (2) GE DICOM conventions: ImageType[2] = "OTHER" for EPI BOLD. MRAcquisitionType = "2D", ScanningSequence includes "EP". No NORM/ND dual-reconstruction equivalent.
        (3) Philips DICOM conventions: ImageType[2] = "M" for magnitude. Dual reconstructions exist (real/imaginary/phase/magnitude) but are NOT equivalent to Siemens NORM/ND. MRAcquisitionType = "2D", ScanningSequence includes "EP" for EPI sequences.
        (4) dcm2niix -i y flag safety: Confirmed safe for BOLD fMRI. Only skips truly single-slice 2D images (xyzDim[3] < 2 AND mosaicSlices < 2), plus derived and localizer images. Multi-slice BOLD (mosaic or multi-band) is never affected.
        (5) Philips dual-reconstruction patterns: Real/imaginary/phase/magnitude splits. Not equivalent to Siemens NORM/ND. The NORM/ND pass should be guarded by Siemens-specific detection.
      </research>
      <approaches>
        <approach id="A1" label="Physics-based BOLD inference with 8 coordinated changes" feasibility="high" risk="medium">
          <description>Replace ImageType[2]-dependent classification with physics-based inference using DICOM-standard fields (MRAcquisitionType, ScanningSequence, n_volumes, .bval presence). Eight changes across 3 files cover the full vendor-agnostic surface.</description>
          <pros>Supports Siemens (all platforms), GE, and Philips without vendor-specific branching in the core classification path. Uses only DICOM-standard fields. Downstream guards (check_volume_counts, fieldmap mapping) remain as safety nets.</pros>
          <cons>n_volumes >= 10 threshold is a heuristic (could theoretically exclude a very short legitimate BOLD, though no known protocol produces fewer than 10 volumes). The NORM/ND pass guard and duplicate modality guard add conditional logic.</cons>
          <statistical_considerations>The n_volumes >= 10 threshold closes a task_registry contamination vector: without it, a 2-3 volume calibration EPI scan could be classified as BOLD, register expected_volumes=3, and cause all subsequent subjects' real BOLD runs (e.g., 362 volumes) to be excluded by check_volume_counts. The threshold is conservative: the shortest known research BOLD protocols are 20+ volumes.</statistical_considerations>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        Physics-based classification with 8 changes:

        C1. New helper `_is_epi_bold_physics(s: Series) -> bool`:
            `s.mr_acquisition_type == "2D" and "EP" in s.scanning_sequence and s.n_volumes >= 10 and not _bval_exists(s)`.
            The n_volumes >= 10 floor prevents task_registry contamination from calibration EPI scans (typically 1-5 volumes). File: stage2_classify.py.

        C2. Rule 3 (NavigatorDropError, lines 183-194): Add physics pass-through. When _is_epi_bold_physics(s) matches, pass through instead of raising NavigatorDropError. Continue to drop when tok is not "FMRI"/"DIFFUSION" AND physics does not match (preserves navigator-drop safety for genuinely aberrant series). File: stage2_classify.py.

        C3. Rule 5 (FMAP_FUNC assignment, lines 230-238): Broaden from `tok == "FMRI"` to `tok != "DIFFUSION" and "EP" in scanning_sequence`. This identifies functional fieldmaps by their EPI acquisition and single-volume character, vendor-agnostically. File: stage2_classify.py.

        C4. Rule 8 (BOLD assignment, lines 260-263): Broaden from `tok == "FMRI" and s.n_volumes > 1` to `(tok == "FMRI" or _is_epi_bold_physics(s)) and s.n_volumes > 1`. File: stage2_classify.py.

        C5. Rules 9/9b (SBRef, lines 265-306): Merge into a single vendor-agnostic SBRef rule. Use EPI + single-volume detection. Look-ahead determines SBREF vs DWI_SBREF based on the immediately following series' role. File: stage2_classify.py.

        C6. Rule 2 (scout/localizer, lines 174-181): Add multi-signal detection: "LOCALIZER" in image_type OR (description keyword match for scout/localizer/survey AND physics confirmation). Prevents GE/Philips scout scans from reaching downstream rules. File: stage2_classify.py.

        C7. NORM/ND pass (lines 311-377): Guard with Siemens-specific detection (check whether any series in the session has NORM-bearing ImageType tokens). Skip entirely for non-Siemens data. Add a duplicate modality guard for T1W/T2W: if the same modality appears more than once after all classification and NORM/ND filtering, emit a graded_warning (medium severity, DUPLICATE_MODALITY). This catches Philips/GE dual-reconstruction artifacts that the NORM/ND pass is not designed to handle. File: stage2_classify.py.

        C8. dcm2niix -i y flag: Add to the dcm2niix invocation in stage1_convert.py (lines 86-94, alongside existing -ba n -b y -z y -f '%s_%d'). Skips truly single-slice 2D images, derived images, and localizer images at the conversion stage. Safe for all multi-slice BOLD data (mosaic and multi-band). File: stage1_convert.py.
      </decision>
    </topic>

    <topic id="T6" title="FieldmapCoverageError: filter excluded targets, soften to graded_warning">
      <summary>An end-user reported FieldmapCoverageError for Series 35 (ABCD_fMRI_task_Emotional_n-back) on a subject where the emotional n-back task was never started (only T1w and 2 rest runs completed). Root cause is two-fold: (a) pipeline.py:178 builds fieldmap targets from ALL classified roles, not just surviving ones from check_volume_counts, so a calibration/auto-align scan excluded by volume-count checking still appears as a target demanding fieldmap coverage; (b) FieldmapCoverageError (a GuardError) is too rigid for protocols that legitimately lack fieldmaps for some or all targets.</summary>
      <research>
        Verified against codebase:
        - pipeline.py:178 uses all roles.items() with no exclusion filter, confirming the false-positive vector.
        - check_volume_counts (runs.py:80-193) returns an excluded list with series_number entries.
        - map_fieldmaps (stage3_map.py:407-546) raises FieldmapCoverageError at three sites: line 485 (per-target gap), line 533 (orphan pair), and line 598 (uncovered targets).
        - pair_fieldmaps returns [] when fmaps is empty (line 267-269).
        - Mapping dataclass (line 80) has pairs and pair_to_targets fields; an empty Mapping can be constructed as Mapping(pairs=[], pair_to_targets={}).
        - FieldmapCoverageError is a GuardError subclass (errors.py:68), so it triggers exit code 1 via __main__.py:160.
      </research>
      <approaches>
        <approach id="A1" label="Four-change defense-in-depth" feasibility="high" risk="low">
          <description>Four coordinated changes: (C1) filter fieldmap targets by volume-count exclusion list, (C2) no-fieldmaps early-out with graded_warning, (C3) soften per-target coverage gap, (C4) soften orphan pair check. Each layer independently prevents the reported false-positive; together they provide defense-in-depth for incomplete scan sessions.</description>
          <pros>No false-positive halts for incomplete sessions. Fieldmap issues become visible warnings rather than silent passes. Defense-in-depth: any single change would fix the reported bug, but all four together handle the full space of partial-session scenarios.</pros>
          <cons>Softening FieldmapCoverageError means a genuine fieldmap configuration error (e.g., missing fieldmap in a complete session) produces a warning rather than a halt. The high-severity graded_warning and exit code 3 (via status="warning") ensure visibility, but the pipeline no longer stops.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        Defense-in-depth with 4 changes:

        C1. Filter fieldmap targets (pipeline.py:178): Build a set of excluded series_numbers from check_volume_counts. Filter the targets list comprehension to exclude any series whose series_number is in the excluded set. This prevents volume-count-excluded calibration/auto-align scans from appearing as fieldmap targets. File: pipeline.py.

        C2. No-fieldmaps early-out (pipeline.py, after pairs = pair_fieldmaps(...)): When pairs is empty (no fieldmap series classified or all fieldmaps excluded), skip map_fieldmaps entirely. Construct an empty Mapping(pairs=[], pair_to_targets={}). Emit graded_warning(logger, "medium", "NO_FIELDMAP_SERIES", "No fieldmap series found; proceeding without fieldmap correction."). File: pipeline.py.

        C3. Soften per-target coverage gap (stage3_map.py:485): Replace FieldmapCoverageError raise with graded_warning(logger, "high", "FIELDMAP_COVERAGE_GAP", ...). The function continues processing remaining targets instead of halting. File: stage3_map.py.

        C4. Soften orphan pair check (stage3_map.py:533): Replace FieldmapCoverageError raise with graded_warning(logger, "medium", "ORPHAN_FIELDMAP_PAIR", ...). An orphan fieldmap pair (no targets assigned) is a configuration anomaly, not a fatal error. File: stage3_map.py.
      </decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P1" target_mode="implement" description="T3: Add user_facing to graded_warning return dict in warnings.py (line 33)" />
    <item priority="P1" target_mode="implement" description="T4: Add _WARNING_ACCUMULATOR, get_warnings(), clear_warnings() to warnings.py; update pipeline.py to call clear_warnings() at entry and get_warnings() at status determination" />
    <item priority="P1" target_mode="implement" description="T5/C1: Add _is_epi_bold_physics(s) helper to stage2_classify.py (mr_acquisition_type==2D, EP in scanning_sequence, n_volumes>=10, no bval)" />
    <item priority="P1" target_mode="implement" description="T5/C2: Rule 3 physics pass-through in stage2_classify.py (lines 183-194)" />
    <item priority="P1" target_mode="implement" description="T5/C3: Rule 5 broadened from tok==FMRI to tok!=DIFFUSION + EP in stage2_classify.py (lines 230-238)" />
    <item priority="P1" target_mode="implement" description="T5/C4: Rule 8 broadened with _is_epi_bold_physics fallback in stage2_classify.py (lines 260-263)" />
    <item priority="P1" target_mode="implement" description="T5/C5: Merge Rules 9/9b into single vendor-agnostic SBRef rule in stage2_classify.py (lines 265-306)" />
    <item priority="P1" target_mode="implement" description="T5/C6: Rule 2 multi-signal scout detection in stage2_classify.py (lines 174-181)" />
    <item priority="P1" target_mode="implement" description="T5/C7: NORM/ND pass Siemens guard + duplicate modality guard for T1W/T2W in stage2_classify.py (lines 311-377)" />
    <item priority="P1" target_mode="implement" description="T5/C8: Add -i y flag to dcm2niix invocation in stage1_convert.py (lines 86-94)" />
    <item priority="P1" target_mode="implement" description="T6/C1: Filter fieldmap targets by volume-count exclusion set in pipeline.py (line 178)" />
    <item priority="P1" target_mode="implement" description="T6/C2: No-fieldmaps early-out with empty Mapping and graded_warning in pipeline.py (after pair_fieldmaps)" />
    <item priority="P1" target_mode="implement" description="T6/C3: Soften per-target FieldmapCoverageError to graded_warning(high, FIELDMAP_COVERAGE_GAP) in stage3_map.py (line 485)" />
    <item priority="P1" target_mode="implement" description="T6/C4: Soften orphan FieldmapCoverageError to graded_warning(medium, ORPHAN_FIELDMAP_PAIR) in stage3_map.py (line 533)" />
  </action_items>
  <next_steps>Invoke /implement to execute all 14 action items. T3 and T4 are prerequisite (warnings.py changes must land before T5/T6 consume graded_warning). Recommended implementation order: T3 -> T4 -> T5 (C1 first, then C2-C8) -> T6 (C1-C4). Follow with /test to validate the full change set.</next_steps>
</brainstorm_report>
