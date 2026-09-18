<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-09-17T00:00:00Z" />
  <context_files>
    <file path="fmri_bids_recon/stage2_classify.py" relevance="Classification rules 1-10, NORM/ND twin resolution pass, calibration PE axis pass, calibration keyword guard pass, _is_spin_echo PSD check" />
    <file path="fmri_bids_recon/stage4_assemble.py" relevance="Per-series BIDS assembly loop (lines 314-355): BOLD branch KeyError on excluded series, SBRef branch secondary crash vector" />
    <file path="fmri_bids_recon/pipeline.py" relevance="Phase 1 CONVERT (roles/run_indices save to intermediate JSON), Phase 3 ASSEMBLE (load and dispatch), Phase 4 registry save, merged_registry accumulation" />
    <file path="fmri_bids_recon/runs.py" relevance="check_volume_counts: known-series exact-match enforcement (lines 101-114), within-session reasoning (lines 116-213), new_registry_entries accumulation" />
    <file path="fmri_bids_recon/labels.py" relevance="resolve_labels: registry lookup, RegistryDelta construction, no in-place mutation of registry" />
    <file path="fmri_bids_recon/config.py" relevance="Registry YAML loading (lines 349-376), save_registry (line 447+), registry persistence across pipeline invocations" />
    <file path="sandbox/runs/run_20260916_143000/staging/sub-1/ses-01/1_01_intermediate.json" relevance="SUBJ_1 (XA30): image_type_text populated with NORM, NORM/ND pass works, rest=383, 0 excluded" />
    <file path="sandbox/runs/run_20260916_143000/staging/sub-2/ses-01/2_01_intermediate.json" relevance="SUBJ_2 (E11): image_type_text empty, NORM/ND pass skipped, 2 T1W + 3 T2W, 1 excluded BOLD (115 vs 409), T2w setter leak" />
    <file path="sandbox/runs/run_20260916_143000/staging/sub-3/ses-01/3_01_intermediate.json" relevance="SUBJ_3 (E11): rest excluded (540 vs 383) via cross-run registry contamination, same NORM/ND and setter issues as SUBJ_2" />
    <file path="sandbox/runs/run_20260916_143000/staging/sub-4/ses-01/4_01_intermediate.json" relevance="SUBJ_4 (E11): identical classification pattern to SUBJ_2, 1 excluded BOLD (19 vs 409)" />
  </context_files>
  <topics>
    <topic id="T1" title="Excluded-series crash in assemble">
      <summary>The roles dict saved to intermediate JSON at pipeline.py:258 includes all classified series, including BOLDs later excluded by the volume checker. run_indices (pipeline.py:204) only contains surviving BOLDs. assemble() at stage4_assemble.py:314 iterates roles.items() and hits run_indices[snum] at line 329 for any excluded BOLD, causing a KeyError crash. A secondary crash vector exists in the SBRef branch (line 349), which can select an excluded BOLD as its parent. This is the root cause of all three E11 subject failures (SUBJ_2, SUBJ_3, SUBJ_4).</summary>
      <research>Code-verified against intermediate JSON: SUBJ_2 Series 18 (BOLD, 115 volumes) is in roles but not in run_indices. SUBJ_4 Series 18 (BOLD, 19 volumes) exhibits the same pattern. SUBJ_3 Series 18 (rest, 540 volumes) was falsely excluded by cross-run registry contamination and exhibits the same roles/run_indices mismatch.</research>
      <approaches>
        <approach id="A1" label="Filter roles upstream" feasibility="high" risk="low">
          <description>Remove excluded series from roles before saving to intermediate JSON (pipeline.py:258). Downstream consumers never see excluded series.</description>
          <pros>Single source of truth; no defensive check needed in assemble.</pros>
          <cons>Intermediate JSON loses the record of what was classified before exclusion, reducing debugging/audit visibility (mitigated by the excluded list which preserves this information).</cons>
        </approach>
        <approach id="A2" label="Skip excluded in assemble" feasibility="high" risk="medium">
          <description>Add an excluded-series guard at the top of the assemble loop (stage4_assemble.py:314).</description>
          <pros>Minimal change; explicit about what it skips.</pros>
          <cons>Every downstream consumer of roles must independently filter excluded series; fragile if new consumers are added.</cons>
        </approach>
        <approach id="A3" label="Both upstream filter and downstream guard" feasibility="high" risk="low">
          <description>A1 + A2: filter roles before saving AND add guard in assemble.</description>
          <pros>Defense in depth; intermediate JSON accurately reflects only surviving series AND assemble is self-protective.</pros>
          <cons>Two changes instead of one; minimal additional complexity.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A3">Defense in depth: filter excluded series from roles before saving to intermediate JSON (pipeline.py:258), and add a skip-excluded guard at the top of the assemble loop (stage4_assemble.py:314). The excluded list in the intermediate JSON preserves audit information about what was removed and why.</decision>
    </topic>
    <topic id="T2" title="NORM/ND twin resolution is XA30-only">
      <summary>The NORM/ND twin resolution pass at stage2_classify.py:428 gates on "NORM" in s.image_type_text, which is a Siemens enhanced-DICOM private tag populated only in XA-line software (XA20, XA30, XA50). For E11 classic DICOM, image_type_text is empty (verified: all SUBJ_2/3/4 series have image_type_text=()). The NORM token for E11 resides in the standard image_type field (position [4] or [5]). Critically, XA30 image_type does NOT contain NORM (both NORM and ND variants have identical image_type tuples with 'NONE' at position [3]). The two platforms carry the NORM/ND distinction in mutually exclusive fields.</summary>
      <research>Code-verified against intermediate JSON. XA30 (SUBJ_1): image_type_text carries NORM, image_type does not. E11 (SUBJ_2/3/4): image_type carries NORM, image_type_text is empty. The NORM/ND pass works for XA30 (Series 4 demoted to DROP_ANAT_ND_T1W, Series 5 retained as T1W) but is entirely skipped for E11 (has_norm evaluates False), producing 2 T1W and 3 T2W instead of 1 each.</research>
      <approaches>
        <approach id="A1" label="Check image_type only" feasibility="low" risk="high">
          <description>Replace image_type_text checks with image_type checks.</description>
          <pros>Simplest change.</pros>
          <cons>Breaks XA30, where image_type does NOT contain NORM. Both NORM and ND variants have identical image_type tuples.</cons>
        </approach>
        <approach id="A2" label="Check both via helper" feasibility="high" risk="low">
          <description>Define _has_norm_token(s) returning "NORM" in s.image_type_text or "NORM" in s.image_type. Replace all bare image_type_text NORM checks in the pass with this helper.</description>
          <pros>Covers both platforms without version detection; XA30 path unchanged (image_type_text fires first); E11 gains coverage via image_type fallback.</pros>
          <cons>Dual-path complexity (minimal: single helper function).</cons>
        </approach>
        <approach id="A3" label="Vendor-dispatched check" feasibility="medium" risk="medium">
          <description>Branch on software_versions to select the appropriate field.</description>
          <pros>Most precise.</pros>
          <cons>Version-string parsing is fragile; adds maintenance burden for new Siemens platforms; no correctness benefit over A2.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A2">Define a helper _has_norm_token(s: Series) -> bool that checks "NORM" in s.image_type_text or "NORM" in s.image_type. Replace all bare "NORM" in s.image_type_text checks in the NORM/ND twin resolution pass (the has_norm guard, norm_members/nd_members partitions, and warning conditions) with calls to this helper. A1 is ruled out because it would break XA30.</decision>
    </topic>
    <topic id="T3" title="Calibration sequence classification gaps">
      <summary>Two related defects in vNav setter classification on E11. (a) T2w MOSAIC setter leak: the T2w setter's MOSAIC split (scanning_seq=('SE',), 3D, nvol=1) enters Rule 4 and is classified as T2W. The calibration keyword guard only inspects FMAP_FUNC/FMAP_DWI roles, so T2W escapes. The setter becomes an extra T2w anatomical. (b) _is_spin_echo false positive: the non-MOSAIC EP split has PSD "%CustomerSeq%\ep_moco_nav_set_ABCD". The check "_se" in psd.lower() at line 123 matches "_se" as a substring of "nav_set", falsely detecting spin-echo. This routes the series through Rule 5 to FMAP_FUNC, where the keyword guard correctly demotes it to DROP_CALIBRATION. The end result is accidentally correct, but the intermediate classification is wrong and poses a latent risk.</summary>
      <research>Code-verified against SUBJ_2 intermediate. Series 13 (T2w MOSAIC setter): scanning_seq=('SE',), classified T2W by Rule 4, keyword guard skips (not FMAP_FUNC/FMAP_DWI). Series 8 (T1w non-MOSAIC setter): PSD contains "nav_set", "_se" in psd.lower() matches inside "set", classified FMAP_FUNC by Rule 5, then keyword guard demotes to DROP_CALIBRATION. description_stem verified: "abcd_t2w_spc_vnav_setter" differs from "abcd_t2w_spc_vnav", confirming the expanded guard would correctly distinguish setters from genuine anatomicals.</research>
      <approaches>
        <approach id="A1" label="Expand keyword guard to T1W/T2W" feasibility="high" risk="low">
          <description>Add T1W and T2W to the roles inspected by the keyword guard.</description>
          <pros>Handles the T2w setter leak.</pros>
          <cons>Does not fix the _is_spin_echo false positive (latent risk remains).</cons>
        </approach>
        <approach id="A2" label="Pre-Rule-4 calibration check" feasibility="medium" risk="medium">
          <description>Insert a new rule before Rule 4 that demotes 3D single-volume series with calibration keywords and small matrices.</description>
          <pros>Catches setters before Rule 4.</pros>
          <cons>Matrix-size threshold is heuristic; does not fix _is_spin_echo.</cons>
        </approach>
        <approach id="A3" label="Fix _is_spin_echo + expand guard" feasibility="high" risk="low">
          <description>Two independent fixes: (1) replace "_se" in psd.lower() with token-based "se" in psd.lower().split("_"); (2) expand keyword guard to T1W/T2W with target stems built from non-calibration-keyword anatomicals.</description>
          <pros>Fixes both defects independently; token-based PSD check eliminates the latent false-positive risk; expanded guard catches the T2w setter leak.</pros>
          <cons>Two changes (both targeted and low-risk).</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A3">Two independent fixes. (1) _is_spin_echo PSD check (line 123): replace "_se" in psd.lower() with "se" in psd.lower().split("_") for token-based matching. (2) Expand calibration keyword guard (lines 561-583): add T1W/T2W arm that builds target stems from non-calibration-keyword anatomicals of the same type; for T1W/T2W with calibration keyword and nvol==1, check stem against target set; demote to DROP_CALIBRATION if target set is non-empty and no match; skip if target set is empty.</decision>
    </topic>
    <topic id="T4" title="Task registry cross-subject contamination">
      <summary>The task registry (config.registry.yaml) persists expected volume counts across pipeline invocations. When subjects with different rest-state volume counts (SUBJ_1/2: rest=383, SUBJ_3: rest=540) share a config, the registry carries forward volume expectations from prior runs. SUBJ_3's rest (540 volumes) was excluded because the registry contained expected_volumes=383 from SUBJ_1/2's prior run. The contamination is across pipeline invocations (the registry YAML persists), not within a single run (config.task_registry is not mutated during the per-participant loop).</summary>
      <research>Code-verified: config.task_registry is loaded from YAML at startup (config.py:349-376) and not mutated during the Phase 1 loop (pipeline.py:161-256 uses merged_registry as a separate accumulator). The registry is saved only at Phase 4 (pipeline.py:348-351), after all phases complete. SUBJ_3's intermediate confirms: Series 18 (rest, 540 vols) excluded with expected=383. SUBJ_1 rest=383 (4 runs), SUBJ_2 rest=383 (2 runs). Within-session reasoning for SUBJ_3 (1 rest run at 540) would have accepted the run, but the registry's "known series" enforcement (lines 101-114) excluded it first.</research>
      <approaches>
        <approach id="A1" label="Per-subject registry isolation" feasibility="high" risk="low">
          <description>Each subject gets an independent registry namespace.</description>
          <pros>Eliminates cross-contamination entirely.</pros>
          <cons>Loses cross-subject volume validation for genuinely same-protocol subjects.</cons>
        </approach>
        <approach id="A2" label="Registry as advisory" feasibility="high" risk="low">
          <description>Registry-based volume mismatches produce a high-severity warning instead of exclusion. Within-session reasoning remains the enforcement mechanism.</description>
          <pros>Preserves cross-subject drift detection as information; never silently drops data; within-session reasoning is the robust enforcement layer.</pros>
          <cons>Single-run aborted acquisitions that previously would have been caught by registry now survive with a warning (acceptable: downstream QC catches volume anomalies).</cons>
        </approach>
        <approach id="A3" label="Registry scoped by acquisition signature" feasibility="medium" risk="medium">
          <description>Volume enforcement only applies when series signature matches registry entry signature.</description>
          <pros>Cross-subject enforcement when protocols truly match.</pros>
          <cons>Signatures vary across scanners even for the "same" protocol; calibration is difficult.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A2">Registry-based volume mismatches become advisory (high-severity warning) rather than enforcement (exclusion). The "known series" branch in check_volume_counts (runs.py lines 101-114) changes from adding to excluded_list on mismatch to appending a high-severity warning and adding to surviving_bolds. Within-session reasoning (mode-based, 2-run tie resolution) remains the enforcement mechanism. Rationale: false exclusions (lost data requiring re-run) are worse than false inclusions (caught by downstream QC); within-session reasoning is the robust layer.</decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P0" target_mode="implement" description="T1: Filter excluded series from roles dict before saving to intermediate JSON (pipeline.py:258) AND add skip-excluded guard at top of assemble loop (stage4_assemble.py:314). Defense in depth." />
    <item priority="P1" target_mode="implement" description="T2: Define _has_norm_token(s) helper checking both image_type_text and image_type for NORM. Replace all bare image_type_text NORM checks in the NORM/ND twin resolution pass (stage2_classify.py:428-504) with the helper." />
    <item priority="P1" target_mode="implement" description="T3a: Fix _is_spin_echo PSD false positive (stage2_classify.py:123): replace substring check with token-based 'se' in psd.lower().split('_')." />
    <item priority="P1" target_mode="implement" description="T3b: Expand calibration keyword guard (stage2_classify.py:561-583) to inspect T1W/T2W roles. Build target stems from non-calibration-keyword anatomicals; demote to DROP_CALIBRATION if target set non-empty and no match; skip if empty." />
    <item priority="P2" target_mode="implement" description="T4: Change registry-based volume enforcement to advisory in check_volume_counts (runs.py:101-114). Registry mismatch produces high-severity warning instead of exclusion. Within-session reasoning remains enforcement." />
  </action_items>
  <next_steps>Proceed to /implement for all action items. Recommended order: P0 (T1) first as it is the crash blocker, then P1 items (T2, T3a, T3b) as a group, then P2 (T4). Follow with /test to verify all fixes against the 4 test subjects.</next_steps>
</brainstorm_report>
