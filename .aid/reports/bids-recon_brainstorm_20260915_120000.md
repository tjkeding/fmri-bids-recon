<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-09-15T12:00:00Z" />
  <context_files>
    <file path="fmri_bids_recon/stage2_classify.py" relevance="Classification rules: Rule 5 DWI_SBREF look-ahead (lines 338-364), Rule 9 DWI_SBREF look-ahead (lines 394-408), _has_nonzero_bval helper (lines 176-186)" />
    <file path="fmri_bids_recon/stage4_assemble.py" relevance="DWI run-index assignment (lines 254-258), BOLD SBRef pairing pattern (lines 294-313), fieldmap acq-entity (line 384), excluded series routing (lines 409-413)" />
    <file path="fmri_bids_recon/runs.py" relevance="check_volume_counts within-session mode reasoning (lines 117-133), tied-mode GuardError (lines 122-123)" />
    <file path="fmri_bids_recon/pipeline.py" relevance="BOLD collection and check_volume_counts invocation (lines 181-182)" />
    <file path="fmri_bids_recon/labels.py" relevance="Task label derivation from SeriesDescription (derive_task_label)" />
  </context_files>
  <research>
    <note>No new research dispatches this session. T2/T1/T3 were fully researched in the prior session (R1: BIDS SBRef suffix scope, consensus; R2: BIDS acq entity semantics, consensus; R3: dcm2niix vNav handling, emerging). T5 is a code-level design question resolved by codebase analysis and fMRI protocol physics reasoning.</note>
  </research>
  <topics>
    <topic id="T2" title="DistortionMap SBRef disposition">
      <summary>Rule 5 (stage2_classify.py:338-364) and Rule 9 (lines 394-408) classify DistortionMap SBRefs as DWI_SBREF because their next chronological series (a b=0-only fieldmap EPI) has DIFFUSION modality and a .bval file. The check uses _bval_exists but not _has_nonzero_bval, so b=0-only fieldmap EPIs match. This produces orphaned SBRefs in dwi/ that inflate the run counter and confuse QSIPrep. R1 research (prior session, consensus) confirmed BIDS has no valid suffix for SBRefs in fmap/ and no downstream tool consumes them.</summary>
      <research>R1 (prior session): BIDS spec scopes sbref suffix to dwi/func/perf only. fMRIPrep SBRef consumption scoped to BOLD reference images. QSIPrep has no fieldmap SBRef concept.</research>
      <approaches>
        <approach id="A1" label="Add _has_nonzero_bval guard, route to UNCLASSIFIED" feasibility="high" risk="low">
          <description>Add _has_nonzero_bval(nxt) to the DWI_SBREF look-ahead condition in both Rule 5 (line 359) and Rule 9 (line 405). When the next series is DIFFUSION/SE_EPI with .bval but all b-values are zero (a fieldmap EPI, not a real DWI), explicitly route the SBRef to UNCLASSIFIED instead of falling through to Rule 5's default FMAP_FUNC (which would also be incorrect). The series ends up in sourcedata/unclassified/, preserving the data for manual review without corrupting the BIDS tree.</description>
          <pros>Clean fix at the classification level. Uses existing _has_nonzero_bval helper. Prevents both the DWI_SBREF misclassification and the FMAP_FUNC misclassification. Consistent with pipeline conventions for ambiguous ancillary series.</pros>
          <cons>None identified.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Add _has_nonzero_bval guard to Rule 5/Rule 9 DWI_SBREF branches. Route unmatched SBRef to UNCLASSIFIED. Eliminates orphaned DWI SBRefs and resolves the root cause of T1's run-counter inflation.</decision>
    </topic>
    <topic id="T1" title="DWI run-index assignment and SBRef pairing">
      <summary>stage4_assemble.py lines 254-258 pool all Role.DWI and Role.DWI_SBREF series into one flat sorted list and assign global sequential indices, regardless of dir- entity or acquisition relationship. This produces non-consecutive per-entity-combination indices and breaks SBRef-to-DWI run-index pairing for QSIPrep. The BOLD SBRef logic (lines 294-313) correctly pairs each SBRef to its parent BOLD by task label and temporal proximity; no analogous pairing exists for DWI. With T2 locked, the DWI_SBREF pool is clean (only genuine DWI SBRefs remain).</summary>
      <research>Codebase-only analysis. BIDS run-entity semantics: repeated instances of the same acquisition within the same entity combination. The fix mirrors the existing BOLD SBRef pairing pattern.</research>
      <approaches>
        <approach id="A1" label="Mirror BOLD SBRef pairing logic" feasibility="high" risk="low">
          <description>Group DWI series by dir- entity. Within each group, assign run indices sequentially (1, 2, ...) in acquisition order. Pair each DWI_SBREF to its parent DWI by temporal proximity (next DWI series chronologically with matching dir- entity), then inherit the parent's run index. Analogous to the validated BOLD SBRef pairing at lines 294-313.</description>
          <pros>Mirrors an already-validated pattern. Produces correct run-index semantics for QSIPrep. Per-entity-combination indices are consecutive.</pros>
          <cons>None identified (T2 fix ensures clean input).</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Mirror BOLD SBRef pairing: group DWI by dir- entity, assign per-group run indices, pair DWI_SBREF to parent DWI by temporal proximity and matching dir- entity.</decision>
    </topic>
    <topic id="T3" title="Fieldmap acq-entity task-specific labeling">
      <summary>stage4_assemble.py line 384 assigns acq-func/acq-dwi for fieldmaps. R2 research (prior session, consensus) established that the acq entity is free-form per BIDS, the canonical SE-EPI example uses only the dir entity, and fieldmap-to-target association is via B0FieldIdentifier/B0FieldSource. No downstream tool parses acq to infer target scope.</summary>
      <research>R2 (prior session): BIDS acq entity is free-form. Canonical examples omit acq for SE-EPI. B0FieldSource is the machine-readable association mechanism. Current naming is spec-consistent.</research>
      <approaches>
        <approach id="A1" label="No action" feasibility="high" risk="low">
          <description>Retain current acq-func/acq-dwi naming. BIDS-consistent per R2 consensus. No functional impact from any change.</description>
          <pros>Already implemented. No churn.</pros>
          <cons>Human readability is marginally less informative (cosmetic).</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Closed as no-action. Current naming is BIDS-consistent per R2 consensus. No functional benefit from modification.</decision>
    </topic>
    <topic id="T5" title="exact_volume_counts guard crash on 2-run tie with aborted acquisition">
      <summary>External user hit fatal GuardError on task '<task>' with volume counts [19, 409] (2 runs). check_volume_counts (runs.py:117-133) uses within-session mode reasoning for unknown tasks. With exactly 2 runs of different lengths, each count has frequency 1, producing a tied mode. The function raises GuardError (fatal, exit code 1). The session context (2 T1w, 3 T2w duplicates, PE axis calibration demotions) indicates multiple scanner restarts. 19 volumes (~15 seconds at typical TRs) is an unambiguous aborted acquisition.</summary>
      <research>Code-level analysis plus fMRI protocol physics reasoning: standard fMRI protocols prescribe a fixed number of volumes per run. Over-acquisition does not occur (the scanner stops at the prescribed count). Therefore, when two runs of the same task within the same session have different volume counts, the shorter run is always truncated and the longer run is the complete (or closest to complete) acquisition.</research>
      <approaches>
        <approach id="A1" label="Accept longer run (2-run tie)" feasibility="high" risk="low">
          <description>When n_runs == 2 and the mode is tied (two runs with different volume counts), accept the run with max(counts), exclude the run with min(counts), and register max as expected_volumes. Emit SEVERITY_HIGH user_facing graded_warning documenting the decision. Preserve current GuardError for n_runs > 2 tied modes (genuine multi-cluster ambiguity). The excluded run is preserved in sourcedata/excluded/ for manual review.</description>
          <pros>Correct by protocol physics. Handles the common aborted-run scenario. Cross-session registry catches the edge case where both runs are truncated (a future session establishes the true expected count). Minimal scope: only the n_runs==2 tied-mode branch changes. Excluded data preserved in sourcedata/excluded/.</pros>
          <cons>If both runs are truncated at different points, the longer one is registered as expected. Cross-session registry catches this on the next session.</cons>
        </approach>
        <approach id="A2" label="Ratio threshold" feasibility="med" risk="med">
          <description>Accept the longer run only when min/max is below a threshold (e.g., 0.5). Raise GuardError when ratio >= 0.5.</description>
          <pros>More conservative for near-equal counts.</pros>
          <cons>Arbitrary threshold. A [350, 409] pair is still truncation by protocol physics but would crash under a 0.5 threshold. Over-acquisition does not occur, so the ratio adds no discriminative power.</cons>
        </approach>
        <approach id="A3" label="Accept both, flag" feasibility="low" risk="high">
          <description>Accept both runs without establishing expected_volumes.</description>
          <pros>Preserves all data.</pros>
          <cons>Allows a truncated run (~15 seconds of data) into the BIDS tree. Downstream tools receive scientifically unusable data.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Accept the longer run for 2-run ties. Preserve GuardError for n_runs > 2 tied modes. SEVERITY_HIGH user_facing warning with full volume-count details. Excluded run preserved in sourcedata/excluded/.</decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P0" target_mode="implement" description="T5: In runs.py check_volume_counts (lines 122-133), add n_runs==2 tied-mode branch: accept max(counts), exclude min(counts), register max as expected_volumes, emit SEVERITY_HIGH user_facing graded_warning. Preserve GuardError for n_runs > 2 ties." />
    <item priority="P1" target_mode="implement" description="T2: In stage2_classify.py, add _has_nonzero_bval(nxt) guard to Rule 5 DWI_SBREF branch (line 359) and Rule 9 DWI_SBREF branch (line 405). When the next series is b=0-only, explicitly route the SBRef to UNCLASSIFIED (do not fall through to FMAP_FUNC)." />
    <item priority="P1" target_mode="implement" description="T1: In stage4_assemble.py (lines 254-258), replace global DWI run-index with per-dir-entity grouping. Add DWI_SBREF-to-parent-DWI pairing by temporal proximity and matching dir- entity, mirroring the BOLD SBRef pairing at lines 294-313." />
  </action_items>
  <next_steps>Proceed to /implement for T5 (P0, external user blocker), T2 (P1), and T1 (P1). T2 must be implemented before T1 (T1's clean input depends on T2's fix). T3 is closed. The platform-agnostic classifier redesign and pydeface three-layer defense (T4 from prior session) remain in the implementation backlog.</next_steps>
</brainstorm_report>
