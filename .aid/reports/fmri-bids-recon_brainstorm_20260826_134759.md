<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-08-26T13:47:59Z" />
  <context_files>
    <file path="fmri_bids_recon/stage2_classify.py" relevance="Central to T1: contains classify(), modality_token(), _is_spin_echo(), _is_epi_bold_physics(), and all 10 classification rules" />
    <file path="fmri_bids_recon/sidecar.py" relevance="Series dataclass (vendor field addition D1, pe_direction_inferred D11), modality_token() (replaced by canonical_modality D4/D9), load_series()" />
    <file path="fmri_bids_recon/stage3_map.py" relevance="T2: pair_fieldmaps() even-count halt (D12 dual-mode), _geometry_check(), map_fieldmaps(); T6: GRE grouping (D16/D17)" />
    <file path="fmri_bids_recon/stage4_assemble.py" relevance="T7: GRE fieldmap assembly (D18), SE-EPI assembly (FieldmapUnit from D12)" />
    <file path="fmri_bids_recon/config.py" relevance="T4: TaskRegistryEntry prefix field (D14)" />
    <file path="fmri_bids_recon/labels.py" relevance="T4: derive_prefix(), derive_task_label(), drift guard (D14)" />
    <file path="fmri_bids_recon/runs.py" relevance="T4: check_volume_counts() uses TaskRegistryEntry" />
    <file path="fmri_bids_recon/errors.py" relevance="PhaseEncodingError halt replaced by graded_warning (D12)" />
    <file path="fmri_bids_recon/warnings.py" relevance="graded_warning framework used by D11, D12" />
    <file path="bids-recon_cr_20260825_164011.md" relevance="Source CR report: F2(A) fieldmap pairing, F2(B) GRE fieldmaps, F8 prefix drift" />
  </context_files>
  <research>
    <agent id="R7" topic="GE PulseSequenceName export and SE-EPI sequence naming">
      <finding>dcm2niix exports GE private tag (0019,109C) as 'PulseSequenceName'. 'epi_pepolar' is ABCD-study WIP-specific; standard GE product SE-EPI uses 'epi' or 'epiRT' (same as GRE-EPI, not discriminating).</finding>
    </agent>
    <agent id="R8" topic="DICOM Manufacturer string values across vendors">
      <finding>Siemens: 'SIEMENS', 'Siemens'. GE: 'GE MEDICAL SYSTEMS', 'GE Healthcare'. Philips: 'Philips Medical Systems', 'Philips', 'Philips Healthcare'. Case-insensitive substring matching to {siemens, ge, philips} is reliable.</finding>
    </agent>
    <agent id="R9" topic="Single-fieldmap SDC methods">
      <finding src="https://fsl.fmrib.ox.ac.uk/fsl/docs/diffusion/topup/users_guide/index.html">TOPUP requires two opposite-PE images; no single-PE mode exists.</finding>
      <finding src="https://fmriprep.org/en/1.1.4/_modules/fmriprep/workflows/fieldmap/pepolar.html">SDCFlows supports single SE-EPI fieldmap PEPOLAR: the single fieldmap supplies the opposite-PE half, the BOLD target supplies the matching-PE half. Requires the fieldmap's PE direction to be opposite to the BOLD's.</finding>
      <finding>ABCD-HCP pipeline does NOT implement single-fieldmap TOPUP. Requires valid opposite-PE pairs, falls back to GRE/FUGUE, then no SDC.</finding>
      <finding src="https://www.nipreps.org/sdcflows/master/methods.html">SyN-based SDC (EPI-to-T1w registration) is experimental and requires case-by-case scrutiny.</finding>
      <finding>FUGUE with GRE B0 field maps is the classical alternative to PEPOLAR/TOPUP when only one PE-direction SE-EPI exists but a separately-acquired GRE fieldmap is available.</finding>
    </agent>
    <empirical_verification dataset="dcm_qa (6 repos, 131 sidecars)">
      <finding>PhaseEncodingDirection: Siemens 8/8 (100%), GE 28/29 (97%), Philips 0/24 (0%). Philips exports PhaseEncodingAxis (axis without polarity) instead.</finding>
      <finding>ImageType[2] is vendor-specific per DICOM PS3.3 C.7.6.1.1.2: Siemens uses FMRI/DIFFUSION/M/P/ASL; GE uses EPI/OTHER; Philips uses T2/M/DIFFUSION/T1/PHASE MAP/PERFUSION.</finding>
      <finding>ScanningSequence EPI token: Siemens always includes EP; GE uses EP\GR (BOLD) and EP\SE (DWI); Philips never includes EP.</finding>
      <finding>Philips SE-EPI discrimination: SequenceName is the only signal (FEEPI for BOLD, DwiSE for DWI, GraSE for ASL). No EP in ScanningSequence, no PhaseEncodingDirection.</finding>
      <finding>Philips GRE fieldmap: dual-echo (TE=2.3ms/4.6ms), ScanningSequence=GR, SequenceName=T1FFE, PHASE in ImageType position 4+ for phase outputs. EchoNumber present (1 or 2). dcm2niix BidsGuess correctly identifies as fmap.</finding>
      <finding>GE PulseSequenceName absent from all 29 GE dcm_qa sidecars, invalidating PulseSequenceName-based SE-EPI detection for GE.</finding>
    </empirical_verification>
  </research>
  <topics>
    <topic id="T1" title="Vendor-aware SE-EPI classification design">
      <summary>The entire classification system (10 rules in stage2_classify.py) is effectively Siemens-only due to vendor-specific ImageType[2] tokens and ScanningSequence conventions. Redesign introduces a vendor gate, canonical_modality() dispatch, vendor-dispatched _is_epi() and _is_spin_echo(), and per-rule updates.</summary>
      <research>Empirical analysis of 131 dcm_qa reference sidecars across Siemens, GE, and Philips. Cross-validated against DICOM PS3.3 C.7.6.1.1.2 (ImageType semantics). GE PulseSequenceName absence verified (R7). Manufacturer string variations verified (R8).</research>
      <approaches>
        <approach id="A1" label="Vendor-aware infrastructure" feasibility="high" risk="low">
          <description>First-class vendor field on Series, canonical_modality() replacing modality_token(), vendor-dispatched _is_epi() and _is_spin_echo(), consolidated rule-by-rule redesign.</description>
          <pros>Empirically grounded in real vendor data. Extensible to new vendors. Preserves existing Siemens behavior while adding GE and Philips support.</pros>
          <cons>10 decisions required. Significant implementation scope (new functions, modified rules, new fields).</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        10 locked design decisions (D1-D10):
        D1: Vendor normalization in load_series() at construction time. Case-insensitive substring matching of Manufacturer to {siemens, ge, philips, None}.
        D2: Scope-wide vendor awareness across Rules 2, 3, 4, and 5.
        D3: Unknown vendor fallback: "SE" in ScanningSequence only for _is_spin_echo(); else False leading to UNCLASSIFIED.
        D4: Vendor-aware canonical_modality() function replacing modality_token().
        D5: Vendor-aware _is_epi() helper replacing raw "EP" in scanning_sequence checks.
        D6: Canonical token vocabulary: FMRI, DIFFUSION, MAGNITUDE, PHASE, ASL, EPI, DERIVED, OTHER.
        D7: _is_epi() per vendor: Siemens/GE: "EP" in scanning_sequence; Philips: SequenceName lookup (contains "EPI", starts with "Dwi", equals "GraSE"); Unknown: "EP" in scanning_sequence.
        D8: _is_spin_echo() per vendor: Siemens: "SE" in scanning_sequence OR "epse" in SequenceName OR "_se" in PulseSequenceDetails; GE/Philips/Unknown: "SE" in scanning_sequence.
        D9: canonical_modality() dispatch tables per vendor (Siemens: FMRI/DIFFUSION/ASL/M/P mapping; GE: EPI/OTHER with EP\SE refinement; Philips: SequenceName-based for T2/T1/M tokens; Unknown: raw token passthrough with M/P fallback).
        D10: Consolidated rule-by-rule redesign. Rules 1, 2, 10 unchanged. Rules 3, 4, 5 major rewrites. Rules 6, 7, 8, 9 moderate substitutions. GE dispatch table refined: EP\SE (not bare SE) for DIFFUSION.
      </decision>
    </topic>

    <topic id="T2" title="Fieldmap pairing relaxation">
      <summary>pair_fieldmaps() halts on odd-count geometry groups (PhaseEncodingError). This is too strict: single-fieldmap protocols (common on Philips) and odd-count groups from upstream exclusion are valid data scenarios, not errors. Philips structurally lacks PhaseEncodingDirection (0/24 sidecars), making PE-based pairing impossible without inference.</summary>
      <research>R9: TOPUP requires two opposite-PE images. SDCFlows supports single SE-EPI fieldmap where the fieldmap is opposite-PE and the BOLD supplies the matching-PE half. ABCD-HCP pipeline does not implement this, falls back to GRE/FUGUE then no SDC. Empirical: Philips has PhaseEncodingAxis (axis only, no polarity) but never PhaseEncodingDirection.</research>
      <approaches>
        <approach id="A2" label="Dual-mode association with PE inference" feasibility="high" risk="medium">
          <description>Support paired and single fieldmap association modes. Infer PE direction from description tokens + PhaseEncodingAxis for Philips. Three-tier fallback based on PE direction availability.</description>
          <pros>Handles all three vendor scenarios. Single fieldmaps reach fmap/ and are available for SDC. Graceful degradation when PE direction is unknown.</pros>
          <cons>Description-token inference is fragile for protocols without _AP/_PA naming. Unknown-PE fieldmaps cannot be associated (correctness constraint: same-PE fieldmap in TOPUP produces erroneous output).</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A2">
        3 locked design decisions (D11-D12 revised, plus GE dispatch refinement):
        D11: Description-token PE direction inference. When PhaseEncodingDirection absent: use PhaseEncodingAxis (physics-derived axis) + description token (_AP/_PA/_LR/_RL, case-insensitive) + affine rotation matrix to compute signed direction. Cross-validate token's anatomical axis against PhaseEncodingAxis alignment. Search SeriesDescription first, ProtocolName as fallback. New pe_direction_inferred boolean on Series. SEVERITY_MEDIUM graded_warning on inference.
        D12 (revised): Dual-mode fieldmap association. Mode 1 (paired): even-count groups with opposite PE, unchanged from current behavior. Mode 2 (single): direct geometry-based target association for unpaired fieldmaps. FieldmapPair generalized to FieldmapUnit (members: 1 or 2 Series; mode: "paired" or "single"). Three-tier PE verification fallback: (1) PE known on both fieldmap and BOLD, verify opposite, associate; (2) PE inferred from token, verify opposite, associate with warning; (3) PE unknown, cannot verify, route to sourcedata/unpaired_fmap with SEVERITY_HIGH warning. Critical constraint: same-PE fieldmap in TOPUP produces erroneous output, so unknown PE is a genuine blocker for single-mode association. Vendor-aware severity: Philips odd count = SEVERITY_MEDIUM (structurally expected); Siemens/GE odd count = SEVERITY_HIGH (unexpected).
      </decision>
    </topic>

    <topic id="T3" title="GRE fieldmap classification and assembly (scoping)">
      <summary>The pipeline handles only BIDS Case 4 (pepolar SE-EPI). Cases 1-3 (GRE-based, using FUGUE for SDC) are unclassified. GRE fieldmaps are the fallback SDC method when pepolar is unavailable. Scoping decision: full GRE support is in scope, detailed design deferred to T5-T7.</summary>
      <research>R9 confirmed FUGUE as the standard alternative SDC pathway. ABCD-HCP pipeline falls back to GRE/FUGUE when pepolar unavailable. Empirical: Philips dcm_qa has complete dual-echo GRE fieldmap data (8 files, 4 outputs x 2 DICOM formats).</research>
      <approaches>
        <approach id="A3" label="Full GRE support (Cases 1-3)" feasibility="high" risk="low">
          <description>Add classification, grouping, and assembly for GRE fieldmaps across all three BIDS cases, integrated with the vendor-aware infrastructure from T1.</description>
          <pros>Completes the pipeline's fieldmap coverage. GRE fieldmaps are common on all vendors, especially legacy protocols.</pros>
          <cons>Substantial implementation scope (new roles, new stage3 grouping, new stage4 assembly paths). Limited empirical data (Philips only in dcm_qa).</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A3">
        D13: GRE fieldmap support is in scope. Changes required at stage2 (classification), stage3 (grouping + target association), and stage4 (BIDS assembly). New Role enums: FMAP_GRE_PHASE, FMAP_GRE_MAG. Sessions may contain both SE-EPI and GRE fieldmaps; both are classified and assembled, downstream preprocessing selects SDC method.
      </decision>
    </topic>

    <topic id="T4" title="TaskRegistryEntry prefix storage">
      <summary>derive_prefix() computes the longest common leading token sequence from all retained descriptions in the current session. The drift guard re-derives labels using the current prefix, causing spurious LabelDriftError when session composition varies across timepoints (e.g., follow-up without structural scans).</summary>
      <research>Codebase analysis of labels.py derive_prefix() (line 43), derive_task_label() (line 83), and the drift guard (line 300). Verified that prefix is session-composition-dependent and not stored in the registry.</research>
      <approaches>
        <approach id="A4" label="Store prefix at registration time" feasibility="high" risk="low">
          <description>Add a prefix field to TaskRegistryEntry, populated at registration time. Drift guard uses the stored prefix instead of the current session's prefix.</description>
          <pros>Eliminates false-positive LabelDriftError from session-composition variation. Preserves drift guard intent (detecting code/config changes). Backward-compatible (None prefix falls back to current session's prefix).</pros>
          <cons>None identified.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A4">
        D14: Add prefix: Optional[tuple] = None to TaskRegistryEntry. At registration (labels.py line 321): store current prefix. At drift check (line 300): use stored prefix if available, else fall back to current session's prefix. Existing registry entries without prefix (loaded as None) use legacy behavior until re-registered.
      </decision>
    </topic>

    <topic id="T5" title="GRE fieldmap classification rules">
      <summary>GRE fieldmap outputs currently fall to UNCLASSIFIED because no classification rule identifies them. Phase images are reliably identified by canonical_modality() == PHASE (no false positives). Companion magnitudes cannot be distinguished from regular GRE anatomicals without cross-series context.</summary>
      <research>Empirical analysis of Philips dual-echo GRE fieldmap: 4 outputs (mag1, phase1, mag2, phase2). PHASE in ImageType position 4+ for phase outputs. EchoNumber present. canonical_modality() from D9 correctly maps to PHASE token for phase outputs and MAGNITUDE for magnitude outputs.</research>
      <approaches>
        <approach id="A5" label="Two-stage classification" feasibility="high" risk="low">
          <description>Stage 2: new rule before Rule 4 classifies PHASE + GR + not-EPI as FMAP_GRE_PHASE. Magnitude companions land at UNCLASSIFIED. Stage 3: new group_gre_fieldmaps() rescues companion magnitudes by SeriesNumber matching + geometry verification.</description>
          <pros>No cross-series context needed in per-series classifier. Magnitudes that fail grouping remain safely UNCLASSIFIED rather than misclassified.</pros>
          <cons>Two-pass approach adds a stage3 step. Magnitude classification depends on a companion PHASE series existing.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A5">
        D15: Two-stage GRE classification. Stage 2 rule (inserted before Rule 4): IF canonical_modality(s) == PHASE AND not _is_epi(s) AND "GR" in scanning_sequence -> FMAP_GRE_PHASE. Stage 3 function group_gre_fieldmaps(): collect FMAP_GRE_PHASE series, find UNCLASSIFIED companions with matching SeriesNumber + same geometry + ScanningSequence=GR, reclassify as FMAP_GRE_MAG, group into GREFieldmapSet dataclass (phase_series, magnitude_series, bids_case, run_index).
      </decision>
    </topic>

    <topic id="T6" title="GRE fieldmap grouping and target association">
      <summary>After classification, GRE outputs must be grouped into BIDS Case 1/2/3 fieldmap sets and associated with target BOLD/DWI series.</summary>
      <research>BIDS v1.9.0 Cases 1-3 definitions. dcm2niix sidecar fields: EchoTime1/EchoTime2 present for phasediff (Case 1), individual EchoTime for separate phases (Case 2), Units="Hz" for direct B0 maps (Case 3).</research>
      <approaches>
        <approach id="A6" label="Count-based case determination + relaxed geometry association" feasibility="high" risk="low">
          <description>BIDS case determined by phase output count and sidecar fields. Target association uses relaxed geometry check (position/orientation match, voxel size/matrix exempt). No PE direction constraint (FUGUE is direction-agnostic).</description>
          <pros>Robust case determination from sidecar metadata. Relaxed geometry accounts for GRE/EPI resolution differences.</pros>
          <cons>Relaxed geometry check needs careful tolerance tuning to avoid false associations.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A6">
        D16: BIDS case determination. 2 phase outputs -> Case 2. 1 phase with EchoTime1+EchoTime2 in sidecar -> Case 1 (phasediff). 1 phase with Units="Hz" -> Case 3 (direct B0). 1 phase otherwise -> Case 1 (default).
        D17: GRE target association. Relaxed geometry check: position and orientation must match (within tolerance), voxel size and matrix exempt. No PE direction constraint. Both SE-EPI and GRE fieldmaps classified and assembled if present; downstream preprocessing selects SDC method.
      </decision>
    </topic>

    <topic id="T7" title="GRE fieldmap BIDS assembly">
      <summary>Assembly stage needs new output paths for GRE fieldmaps. Each BIDS case has distinct suffixes and required sidecar metadata.</summary>
      <research>BIDS v1.9.0 fieldmap specification: Case 1 (_phasediff + _magnitude1/2), Case 2 (_phase1/2 + _magnitude1/2), Case 3 (_fieldmap + _magnitude). Required sidecar fields per case.</research>
      <approaches>
        <approach id="A7" label="GREFieldmapSet-driven assembly" feasibility="high" risk="low">
          <description>Assembly iterates over GREFieldmapSet objects. BIDS suffix determined by bids_case. No dir- or acq- entities (GRE fieldmaps are PE-agnostic and modality-agnostic). Coexists with SE-EPI _epi assembly path.</description>
          <pros>Clean separation from SE-EPI assembly. Set-based iteration avoids cross-series lookups in assembly.</pros>
          <cons>None identified.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A7">
        D18: GRE assembly path. Assembly operates on GREFieldmapSet (not individual series). Case 1: _phasediff (with EchoTime1/EchoTime2) + _magnitude1/2. Case 2: _phase1/_phase2 (each with EchoTime) + _magnitude1/2. Case 3: _fieldmap (with Units: "Hz") + _magnitude. All to fmap/ with run-{idx}. No dir- entity. No acq- entity. Mapping.bids_relative_paths populated for each GRE series. SE-EPI (_epi) and GRE paths coexist in the same session.
      </decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P0" target_mode="implement" description="Add vendor field to Series dataclass with Manufacturer normalization at load_series() construction time (D1)" />
    <item priority="P0" target_mode="implement" description="Implement canonical_modality() vendor-dispatched function replacing modality_token() (D4, D6, D9)" />
    <item priority="P0" target_mode="implement" description="Implement vendor-dispatched _is_epi() helper (D5, D7)" />
    <item priority="P0" target_mode="implement" description="Implement vendor-dispatched _is_spin_echo() (D8)" />
    <item priority="P0" target_mode="implement" description="Update all 10 classification rules per consolidated redesign (D10)" />
    <item priority="P0" target_mode="implement" description="Implement description-token PE direction inference with PhaseEncodingAxis cross-validation (D11)" />
    <item priority="P0" target_mode="implement" description="Generalize FieldmapPair to FieldmapUnit, implement dual-mode (paired/single) association with three-tier PE verification (D12)" />
    <item priority="P0" target_mode="implement" description="Replace PhaseEncodingError odd-count halt with vendor-aware graded_warning + sourcedata/unpaired_fmap routing (D12)" />
    <item priority="P1" target_mode="implement" description="Add FMAP_GRE_PHASE and FMAP_GRE_MAG to Role enum (D13, D15)" />
    <item priority="P1" target_mode="implement" description="Add GRE phase classification rule before Rule 4 (D15)" />
    <item priority="P1" target_mode="implement" description="Implement group_gre_fieldmaps() for companion magnitude identification and GREFieldmapSet assembly (D15, D16)" />
    <item priority="P1" target_mode="implement" description="Implement BIDS case determination logic (D16)" />
    <item priority="P1" target_mode="implement" description="Implement relaxed geometry check for GRE-to-EPI target association (D17)" />
    <item priority="P1" target_mode="implement" description="Add GRE fieldmap BIDS assembly path in stage4 (D18)" />
    <item priority="P1" target_mode="implement" description="Add prefix field to TaskRegistryEntry, update drift guard to use stored prefix (D14)" />
    <item priority="P1" target_mode="test" description="Design tests for vendor-aware classification against dcm_qa empirical sidecars (all vendors)" />
    <item priority="P1" target_mode="test" description="Design tests for dual-mode fieldmap association (paired, single, unknown-PE)" />
    <item priority="P1" target_mode="test" description="Design tests for GRE fieldmap classification, grouping, and assembly (Cases 1-3)" />
    <item priority="P1" target_mode="test" description="Design tests for TaskRegistryEntry prefix stability across varying session compositions" />
  </action_items>
  <next_steps>
    /implement for all action items (this brainstorm's decisions + CR direct-to-implement items F3, F4, F5, F7, F9, F10, F11). Recommend splitting into two /implement invocations: (1) P0 items (vendor-aware classification + fieldmap pairing) as a cohesive unit; (2) P1 items (GRE fieldmap support + prefix fix) as a second unit. Follow each with /test.
  </next_steps>
</brainstorm_report>
