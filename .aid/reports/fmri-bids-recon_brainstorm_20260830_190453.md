<brainstorm_report>
  <meta project="fmri-bids-recon" mode="brainstorm" timestamp="2026-08-30T19:04:53Z" />
  <status>partial: T4 locked, T2/T1/T3 deferred to next session</status>
  <context_files>
    <file path="bids-recon_run-local_20260828_003115.md" relevance="Run-local report with anomalies A1 (DWI run numbering), A2 (DistortionMap SBRef classification), A3 (fmap func naming)" />
    <file path="fmri_bids_recon/stage2_classify.py" relevance="Classification rules: Rule 3 (DROP_NAVIGATOR), Rule 4 (T1W/T2W), Rule 5 (FMAP_FUNC/DWI_SBREF), Rule 9 (SBREF); NORM/ND twin resolution; calibration exclusion" />
    <file path="fmri_bids_recon/stage4_assemble.py" relevance="DWI run-index assignment (lines 254-258), BOLD SBRef pairing (lines 294-313), fieldmap acq-label (line 384)" />
    <file path="fmri_bids_recon/stage3_map.py" relevance="FieldmapUnit grouping and run_index assignment, map_fieldmaps target association" />
    <file path="fmri_bids_recon/deface.py" relevance="Defacing workflow: no dimensionality validation before pydeface invocation (lines 93-115)" />
    <file path="fmri_bids_recon/runs.py" relevance="BOLD run-index assignment (assign_run_indices), groups by task_label" />
  </context_files>
  <research>
    <agent id="R1" question="BIDS-standard disposition for SBRefs of SE-EPI fieldmap acquisitions" lit_state="consensus">
      <finding>BIDS specification scopes the sbref suffix exclusively to dwi/, func/, and perf/ datatypes. No valid suffix exists for SBRefs in fmap/. (src: BIDS Specification, MRI data, Echo-Planar Imaging and B0 mapping section)</finding>
      <finding>fMRIPrep SBRef consumption is scoped to BOLD (func/) reference-image selection only. SDCFlows has no concept of a fieldmap-associated SBRef. (src: fMRIPrep documentation, BOLD preprocessing workflows)</finding>
      <finding>QSIPrep documentation contains no mention of SBRef in any fieldmap context. (src: QSIPrep preprocessing.html, absence-of-evidence)</finding>
    </agent>
    <agent id="R2" question="BIDS convention for encoding fieldmap-to-target association in acq entity" lit_state="consensus">
      <finding>The acq entity is a free-form, user-chosen label for distinguishing different acquisition parameter sets. No normative requirement to encode task name. (src: BIDS Specification, Appendices: Entities)</finding>
      <finding>BIDS canonical example for SE-EPI fieldmap pairs uses only the dir entity (no acq entity), confirming acq is optional. (src: BIDS Specification, Case 4: PEpolar)</finding>
      <finding>Fieldmap-to-target association is encoded via B0FieldIdentifier/B0FieldSource (or legacy IntendedFor), not filename entities. fMRIPrep SDCFlows prioritizes B0FieldIdentifier/B0FieldSource. Downstream tools do not parse acq to infer target scope. (src: fMRIPrep documentation, SDCFlows)</finding>
      <finding>The run entity is for repeated instances of the same acquisition, not for encoding which task a fieldmap targets. Using run-01/run-02 for successive identical-parameter fieldmap pairs is spec-consistent. (src: BIDS Specification, Appendices: Entities)</finding>
    </agent>
    <agent id="R3" question="Siemens vNav navigator handling in BIDS conversion and pydeface behavior on multi-volume input" lit_state="emerging">
      <finding>dcm2niix does not reliably split vNav navigators from the parent anatomical on XA30/ABCD exports. Navigators can be merged into 4D NIfTIs with shapes like 192x192x1x2 or 192x192x2x1. (src: rordenlab/dcm2niix GitHub issue #716)</finding>
      <finding>No dcm2niix flag exists to force pure 3D output and suppress intelligent merging of vNav navigator instances. (src: rordenlab/dcm2niix GitHub issue #481)</finding>
      <finding>No peer BIDS conversion tool (HeuDiConv, Dcm2Bids, BIDScoin) has documented navigator detection guards. (src: nipy/heudiconv issues, UNFmontreal/Dcm2Bids issues, BIDScoin ReadTheDocs)</finding>
      <finding>pydeface has no dimensionality check gating 3D-only input. Its failure mode on 4D input is either an uncaught ValueError (broadcast failure) or silent output corruption when the first axis size equals the volume count. (src: poldracklab/pydeface GitHub PR #84, Aug 2026)</finding>
      <finding>No peer tool implements a pre-deface dimensionality check. A project-side guard would be novel. (src: aggregate of surveyed GitHub issue trackers)</finding>
    </agent>
  </research>
  <topics>
    <topic id="T4" title="pydeface crash on multi-volume T2w (vNav navigator misclassification)">
      <summary>Production-halting bug on the institutional HPC cluster: pydeface crashes with ValueError on a T2w NIfTI with shape (192,192,1,2). Root cause is a three-layer failure: (1) dcm2niix version-dependent vNav navigator handling emits navigators with anomalous geometry (2,192,192) that bypasses the NORM/ND twin resolution pass, (2) no fallback navigator detection in stage2_classify.py (Rule 3 does not fire because n_volumes=1 for a 3D volume with 2 slices; Rule 4 classifies as T2W; NAVIGATOR_CANDIDATE flag is purely informational), (3) deface.py passes all T1w/T2w NIfTIs to pydeface without volume-count or dimensionality validation. pydeface PR #84 documents a silent corruption path that is strictly worse than the crash.</summary>
      <research>R3 findings: dcm2niix GitHub #716 and #481 document the vNav merging behavior. No peer BIDS conversion tool implements navigator detection guards or pre-deface dimensionality checks. pydeface has no ndim check; its failure on 4D input is either ValueError or silent corruption (PR #84).</research>
      <approaches>
        <approach id="A1" label="L1a: Min-slice geometry guard" feasibility="high" risk="low">
          <description>In stage2_classify.py NORM/ND twin resolution pass, when NAVIGATOR_CANDIDATE fires, apply geometry heuristic: if min(series.matrix) less than 16 while max(series.matrix) >= 64, demote to DROP_NAVIGATOR instead of emitting SEVERITY_LOW warning.</description>
          <pros>Catches the reported production failure mode (separate 3D navigator with 2 slices). Threshold of 16 provides wide margin against false positives.</pros>
          <cons>Does not catch the complementary merged-navigator case (4D, n_volumes=2).</cons>
        </approach>
        <approach id="A2" label="L1b: Anatomical volume-count guard" feasibility="high" risk="low">
          <description>After Rule 4 in stage2_classify.py, if a newly-classified T1W/T2W series has n_volumes greater than 1, demote to DROP_NAVIGATOR with SEVERITY_MEDIUM warning.</description>
          <pros>Catches the merged-navigator case where dcm2niix produces a 4D anatomical NIfTI.</pros>
          <cons>Does not catch the separate-navigator case (3D, 2 slices, n_volumes=1).</cons>
        </approach>
        <approach id="A3" label="L2: Pre-deface ndim + volume check" feasibility="high" risk="low">
          <description>In deface.py, before calling pydeface, load the NIfTI header via nibabel and verify ndim == 3 and shape has no 4th dimension greater than 1. If violated, skip with SEVERITY_HIGH graded_warning and continue to next file.</description>
          <pros>Defense-in-depth against any multi-volume anatomical reaching deface stage. Prevents both the crash and the silent corruption path documented in pydeface PR #84.</pros>
          <cons>Does not fix the root-cause misclassification; the navigator-as-T2W still enters the BIDS tree.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1+A2+A3">Implement all three layers: L1a (min-slice geometry guard, threshold 16) catches the separate-navigator case, L1b (volume-count guard) catches the merged-navigator case, L2 (pre-deface ndim check) provides defense-in-depth. The layered approach is necessary because dcm2niix's navigator handling varies across versions and platform configurations.</decision>
    </topic>
    <topic id="T2" title="DistortionMap SBRef disposition">
      <summary>stage2_classify.py Rule 9 classifies DistortionMap SBRefs (e.g., ABCD_dMRI_DistortionMap_PA_SBRef) as DWI_SBREF because the next series chronologically is a DIFFUSION-modality fieldmap EPI with the same description stem. These are reference scans for the fieldmap EPIs (correctly placed in fmap/ as FMAP_DWI), not for any DWI acquisition. Their presence in dwi/ creates orphaned SBRefs and inflates the run counter, directly contributing to A1.</summary>
      <research>R1 findings (consensus): BIDS spec scopes sbref suffix exclusively to dwi/func/perf. No valid suffix for fmap/. fMRIPrep SBRef consumption scoped to BOLD reference-image selection only. QSIPrep has no mention of fieldmap SBRefs.</research>
      <approaches>
        <approach id="A1" label="Route to sourcedata/dropped" feasibility="high" risk="low">
          <description>Refine Rule 9 DWI_SBREF branch: before assigning DWI_SBREF, verify the next series is classified as Role.DWI (multi-volume diffusion with non-zero bvals), not Role.FMAP_DWI (single-volume b=0 fieldmap). If next series is FMAP_DWI, the SBRef is ancillary to the fieldmap and should be dropped. Consistent with existing handling of vNav navigators and ND twins.</description>
          <pros>Clean solution. No BIDS suffix invention. Consistent with pipeline conventions. Removes the root cause of DWI run-counter inflation.</pros>
          <cons>None identified.</cons>
        </approach>
        <approach id="A2" label="Route to fmap/ as ancillary" feasibility="low" risk="high">
          <description>Invent a non-standard convention for fieldmap SBRefs in fmap/.</description>
          <pros>Preserves the data in the BIDS tree.</pros>
          <cons>No BIDS suffix exists. Would create a non-standard convention. No downstream tool consumes them.</cons>
        </approach>
        <approach id="A3" label="Keep in dwi/ with run-index fix" feasibility="med" risk="med">
          <description>Preserve DWI_SBREF classification but fix the run-index logic to handle orphaned SBRefs.</description>
          <pros>Minimal classification change.</pros>
          <cons>Preserves the misclassification. Complicates T1's run-index fix. Files remain orphaned in dwi/.</cons>
        </approach>
      </approaches>
      <decision status="open" chosen="none">Recommendation: Option A1 (route to sourcedata/dropped via Rule 9 refinement). Presented to user but not yet locked. Deferred to next session.</decision>
    </topic>
    <topic id="T1" title="DWI run-index assignment and SBRef pairing">
      <summary>stage4_assemble.py lines 254-258 pool all Role.DWI and Role.DWI_SBREF series into one sorted list and assign global sequential indices, regardless of dir- entity or acquisition relationship. The BOLD SBRef logic (lines 294-313) correctly pairs each SBRef to its parent BOLD by task label and temporal proximity; no analogous pairing exists for DWI. This produces non-consecutive per-entity-combination indices and breaks SBRef-to-DWI run-index pairing for downstream tools (QSIPrep).</summary>
      <research>Codebase-only analysis. BIDS run-entity semantics are unambiguous: repeated instances of the same acquisition within the same entity combination. The fix mirrors the existing BOLD SBRef pairing pattern.</research>
      <approaches>
        <approach id="A1" label="Mirror BOLD SBRef pairing logic" feasibility="high" risk="low">
          <description>Pair each DWI_SBREF to its parent DWI by temporal proximity (next DWI series chronologically with matching dir- entity), then assign run indices per entity combination (dir + suffix). Analogous to the BOLD SBRef logic at lines 294-313.</description>
          <pros>Mirrors an already-validated pattern. Produces correct run-index semantics for QSIPrep.</pros>
          <cons>Depends on T2 resolution (the correct set of DWI-classified series determines the input).</cons>
        </approach>
      </approaches>
      <decision status="open" chosen="none">Not yet discussed. Depends on T2 resolution. Deferred to next session.</decision>
    </topic>
    <topic id="T3" title="Fieldmap acq-entity task-specific labeling">
      <summary>stage4_assemble.py line 384 hardcodes acq="func" for func fieldmaps. The run entity distinguishes fieldmaps serving different task blocks. Initially assessed as anomalous (A3), but R2 research findings significantly downgrade the severity.</summary>
      <research>R2 findings (consensus): acq is a free-form label for acquisition parameter distinction, not task-target encoding. BIDS canonical example uses only dir entity for SE-EPI fieldmaps. Fieldmap-to-target association is encoded via B0FieldIdentifier/B0FieldSource, not filename entities. Downstream tools do not parse acq to infer target scope. Using run for successive identical-parameter fieldmap pairs is spec-consistent.</research>
      <approaches>
        <approach id="A1" label="Keep current naming (acq-func + run index)" feasibility="high" risk="low">
          <description>Retain the current acq-func/acq-dwi naming with run indices. The R2 research establishes that the current scheme is BIDS-consistent: acq encodes the modality parameter distinction, run indexes repeated identical-parameter acquisitions, and the machine-readable association is via B0FieldSource.</description>
          <pros>Already implemented. BIDS-consistent per R2. No downstream tool impact. Avoids unnecessary churn.</pros>
          <cons>Human readability: a reader cannot tell from the filename alone which task a fieldmap pair serves.</cons>
        </approach>
        <approach id="A2" label="Task-specific acq labels" feasibility="med" risk="low">
          <description>When all B0FieldSource targets share a single task label, use that label as the acq entity (e.g., acq-emotionalnback). Fall back to acq-func when targets span multiple tasks.</description>
          <pros>Improved human readability. Eliminates run entity for the non-repetition case.</pros>
          <cons>More complex logic. Marginal benefit given that B0FieldSource is the authoritative association mechanism.</cons>
        </approach>
      </approaches>
      <decision status="open" chosen="none">Not yet discussed. R2 findings suggest the current naming may be acceptable (downgraded from anomalous to cosmetic preference). Deferred to next session.</decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P0" target_mode="implement" description="T4: Implement L1a (min-slice geometry guard in NAVIGATOR_CANDIDATE, threshold 16), L1b (anatomical volume-count guard post-Rule-4), and L2 (pre-deface ndim+volume check in deface.py). Three-layer defense against vNav navigator misclassification and pydeface crash/silent corruption." />
    <item priority="P1" target_mode="brainstorm" description="T2: Resolve DistortionMap SBRef disposition (recommendation: Option A1, route to sourcedata/dropped via Rule 9 refinement). Must be locked before T1 can proceed." />
    <item priority="P1" target_mode="brainstorm" description="T1: Resolve DWI run-index assignment (recommendation: mirror BOLD SBRef pairing logic). Depends on T2 resolution." />
    <item priority="P2" target_mode="brainstorm" description="T3: Resolve fieldmap acq-entity naming (recommendation: Option A1, keep current naming per R2 consensus). May be downgraded to no-action." />
  </action_items>
  <next_steps>Next session: resume brainstorm to lock T2, T1, T3, then proceed to /implement for T4 (P0) and any additional locked items. T4 is implementation-ready.</next_steps>
</brainstorm_report>
