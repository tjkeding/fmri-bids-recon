<cr_report>
  <meta project="bids-recon" mode="cr" timestamp="2026-08-25T16:40:11Z" />
  <scope>
    Full adversarial review of the fmri-bids-recon pipeline. Files reviewed:
    fmri_bids_recon/stage2_classify.py, fmri_bids_recon/stage3_map.py,
    fmri_bids_recon/stage4_assemble.py, fmri_bids_recon/sidecar.py,
    fmri_bids_recon/pipeline.py, fmri_bids_recon/physio.py,
    fmri_bids_recon/labels.py, fmri_bids_recon/deface.py,
    fmri_bids_recon/warnings.py, fmri_bids_recon/report.py,
    fmri_bids_recon/errors.py, fmri_bids_recon/config.py,
    fmri_bids_recon/__main__.py, fmri_bids_recon/runs.py.
    Cross-module harmonization against fmri-preproc, fmri-first-level-proc,
    and fmri-proc-orchestrator (exit code contracts, error class hierarchies,
    warning accumulator specification).
    Focus areas: (1) guards that should be proactive pipeline logic rather than
    defensive halts, (2) code efficiency, (3) cross-module harmonization.
  </scope>
  <research_conducted>
    R7: dcm2niix JSON key mapping for GE private tag PulseSequenceName (0019,109C).
    Confirmed dcm2niix exports as "PulseSequenceName". GE ABCD WIP sequence
    "epi_pepolar" is site-specific; standard GE product SE-EPI uses "epi" or
    "epiRT" (indistinguishable from GRE-EPI by PulseSequenceName alone).

    R8: DICOM Manufacturer string (0008,0070) variations across Siemens, GE,
    Philips scanner product lines over the past 10 years. Confirmed
    case-insensitive substring matching on {"siemens", "ge", "philips"} covers
    all known production variants: "SIEMENS", "Siemens", "GE MEDICAL SYSTEMS",
    "GE Healthcare", "Philips Medical Systems", "Philips Healthcare", etc.

    PV-1/PV-2/PV-3: Independent proposal verification (N=3) of the vendor-aware
    SE-EPI classification recommendation. Majority verified (2/3) with minority
    concerns. All concerns addressed by evidence (GE product sequence
    indistinguishability acknowledged as residual risk with safe failure mode:
    unclassified, not misclassified).
  </research_conducted>
  <findings>
    <finding id="F1" severity="major" category="validity">
      <location file="fmri_bids_recon/stage2_classify.py" lines="67-88, 245-265" />
      <location file="fmri_bids_recon/sidecar.py" lines="20-92, 290-315" />
      <description>
        The _is_spin_echo() function uses a three-signal vendor-agnostic approach
        to detect SE-EPI sequences. Signal 3 (absence of "SS" in SequenceVariant,
        lines 79-87) is empirically falsified: GRE-BOLD sequences on Siemens Prisma
        also lack "SS", producing false-positive SE-EPI classification that routes
        GRE-EPI SBRef to FMAP_FUNC. No vendor-agnostic physics-based discriminator
        exists for SE-EPI vs GRE-EPI; all production BIDS tools use vendor-specific
        heuristics.
      </description>
      <evidence>
        Signal 3 checks `not any(v in seq_var for v in ("SS",))` but Siemens
        GRE-BOLD SequenceVariant is typically ["SK", "SP"] (no "SS"), making this
        signal vacuously true for GRE-BOLD. Signal 2 (line 76-77) checks "_se" in
        PulseSequenceDetails but misses "epse" (Siemens CMRR variant).
      </evidence>
      <literature>
        No published vendor-agnostic SE-EPI discriminator exists. HeuDiConv,
        ReproIn, and BIDScoin all use vendor-specific string matching. dcm2niix
        exports Manufacturer as "SIEMENS", "GE MEDICAL SYSTEMS", or "Philips
        Medical Systems" (R8 findings). GE exports PulseSequenceName (0019,109C)
        as "PulseSequenceName" in JSON (R7 findings).
      </literature>
      <impact>
        GRE-EPI SBRef misclassified as SE-EPI fieldmap on Siemens data. Pipeline
        routes the SBRef to fmap/ instead of func/, producing an incorrect BIDS
        dataset. Downstream TOPUP distortion correction uses a GRE image as if it
        were SE, producing incorrect susceptibility field estimates.
      </impact>
      <recommendation>
        (1) Add a first-class `vendor: str | None` field to the Series dataclass,
        normalized at construction time from `raw.get("Manufacturer", "")` via
        case-insensitive substring matching to {"siemens", "ge", "philips", None}.
        (2) Remove signal 3 (SS-absence heuristic).
        (3) Replace _is_spin_echo() with a vendor-dispatched implementation:
        Siemens: "SE" in ScanningSequence OR "_se"/"epse" in PulseSequenceDetails.
        GE: "SE" in ScanningSequence OR "epi_pepolar" in PulseSequenceName.
        Philips: "SE" in ScanningSequence OR "epse" in SequenceName.
        Unknown vendor: "SE" in ScanningSequence only; else False (series
        classified as UNCLASSIFIED, not misclassified).
        Independently verified (PV 2/3 verified, 1/3 concerns addressed).
      </recommendation>
    </finding>

    <finding id="F2" severity="major" category="validity">
      <location file="fmri_bids_recon/stage3_map.py" lines="230-405" />
      <location file="fmri_bids_recon/stage2_classify.py" lines="245-265" />
      <description>
        Two pipeline failures in fieldmap handling:
        (A) Pairing logic is too strict. pair_fieldmaps() requires even member
        count per geometry group (odd-count halt at lines 322-332), requires
        non-None PE direction (halt), and cannot handle a single reverse-PE
        fieldmap used for all runs in a session.
        (B) GRE fieldmaps (BIDS Cases 1-3: phasediff+magnitude, two-phase+magnitude,
        direct B0 map) are not classified. The pipeline only handles Case 4
        (pepolar SE-EPI pairs). GRE fieldmaps are valid, common, and should be
        classified and processed.
      </description>
      <evidence>
        pair_fieldmaps() raises PhaseEncodingError on odd member count (line 326).
        Classification rules 1-10 in stage2_classify.py have no rule for GRE
        fieldmap detection (phasediff, phase1/phase2, fieldmap suffixes).
      </evidence>
      <literature>
        BIDS specification v1.9.0 defines four fieldmap cases. Cases 1-3 (GRE-based)
        are common on Siemens and GE scanners, particularly for legacy protocols
        and structural-only sessions. Single reverse-PE fieldmaps are valid on
        Philips systems where only one PE direction is acquired for distortion
        correction via SyNDistortionCorrection (ANTs).
      </literature>
      <impact>
        Sessions with GRE fieldmaps: fieldmaps classified as UNCLASSIFIED, routed
        to sourcedata/unclassified, and unavailable for distortion correction.
        Sessions with odd-count SE-EPI fieldmaps: pipeline halts with
        PhaseEncodingError. Both are pipeline failures for valid data.
      </impact>
      <recommendation>
        (A) Relax pairing: allow single reverse-PE fieldmaps (emit medium-severity
        graded_warning, associate without pairing). Handle odd-count groups by
        warning rather than halting.
        (B) Add GRE fieldmap classification rules and BIDS assembly paths for
        Cases 1-3. This requires /brainstorm for design (classification heuristics,
        assembly file naming, IntendedFor population) then /implement.
      </recommendation>
    </finding>

    <finding id="F3" severity="major" category="robustness">
      <location file="fmri_bids_recon/pipeline.py" lines="158" />
      <description>
        The dict comprehension `series_map = {s.series_number: s for s in
        all_series}` silently overwrites duplicate SeriesNumbers. On Siemens XA30
        with vNav-enabled sequences, the navigator reconstruction produces a twin
        series with the same SeriesNumber as the parent anatomical. This is valid
        scanner behavior, not corrupted data.
      </description>
      <evidence>
        pipeline.py line 158. vNav twin series share SeriesNumber with the parent
        T1w/T2w. Current DROP_NAVIGATOR classification (Rule 2) drops navigators,
        but the drop happens after load_series(), and the dict comprehension
        in pipeline.py runs on all_series before classification applies.
      </evidence>
      <literature>
        Siemens XA30 vNav (volumetric navigators, Tisdall et al. 2012) produces
        navigator volumes with identical SeriesNumber to the parent structural
        scan. This is documented in the Siemens DICOM Conformance Statement.
      </literature>
      <impact>
        If the navigator twin overwrites the parent anatomical in series_map,
        the pipeline processes the navigator instead of the T1w/T2w. The
        navigator is a low-resolution motion-tracking volume, not a diagnostic
        structural scan.
      </impact>
      <recommendation>
        Resolve vNav twins upstream of series_map construction: identify
        navigator/parent pairs by SeriesNumber collision + ImageType[2]
        discrimination ("ND" navigators vs "NORM"/"DIS2D" parent), retain the
        parent, and drop the navigator. Only genuinely unresolvable duplicates
        (same SeriesNumber, same ImageType, different content) should be guarded.
      </recommendation>
    </finding>

    <finding id="F4" severity="minor" category="robustness">
      <location file="fmri_bids_recon/physio.py" lines="194-216, 263-315" />
      <description>
        The physio trigger-event counter uses a fixed midpoint threshold for
        rising-edge detection, and the physio association logic hard-halts
        (PhysioAssociationError) on trigger volume count mismatch instead of
        degrading gracefully. The association attempts only a single BOLD
        candidate rather than trying all eligible candidates.
      </description>
      <evidence>
        _count_trigger_events() at line 207 uses `threshold = (max_val +
        min_val) / 2`. associate_native_physio() at lines 300-311 raises
        PhysioAssociationError on mismatch.
      </evidence>
      <literature>
        Otsu's method (1979) provides a data-adaptive threshold that maximizes
        inter-class variance, more robust than a fixed midpoint for bimodal
        trigger signals with variable baseline or amplitude.
      </literature>
      <impact>
        Fixed midpoint threshold: miscounts trigger events when the trigger
        signal has a non-zero baseline or asymmetric amplitude distribution.
        Hard halt: a single BOLD with a physio timing mismatch (e.g., aborted
        run, partial recording) halts the entire session, losing physio data
        for all other BOLDs.
      </impact>
      <recommendation>
        (1) Replace midpoint threshold with Otsu's method.
        (2) Try all BOLD candidates (sorted by temporal proximity) rather than
        a single candidate.
        (3) Convert the hard halt to a medium-severity graded_warning on
        mismatch (physio association is valuable but not load-bearing for
        downstream preprocessing).
        (4) Add +/-1 volume tolerance for trigger count matching (accounts for
        dummy scans and partial trigger recordings).
      </recommendation>
    </finding>

    <finding id="F5" severity="minor" category="harmonization">
      <location file="fmri_bids_recon/pipeline.py" lines="280-286" />
      <location file="fmri_bids_recon/warnings.py" lines="1-30" />
      <location file="fmri_bids_recon/report.py" lines="189-201" />
      <description>
        The conversion report receives review_flags directly but does not
        include warnings from _WARNING_ACCUMULATOR. Two parallel warning
        channels exist: review_flags (per-session, report-only) and
        _WARNING_ACCUMULATOR (module-level, cross-pipeline specification for
        the orchestrator). The report does not reflect the full warning state.
      </description>
      <evidence>
        pipeline.py line 284 passes review_flags to write_conversion_report()
        but does not pass get_warnings(). report.py Section 5 renders
        review_flags only. _WARNING_ACCUMULATOR is read by __main__.py for
        exit code determination but not by the report.
      </evidence>
      <literature>
        The _WARNING_ACCUMULATOR is a cross-pipeline specification shared
        with fmri-preproc and fmri-first-level-proc via the orchestrator's
        graded_warning() contract.
      </literature>
      <impact>
        The conversion report omits pipeline-level warnings that affect the
        exit code and orchestrator routing. A reviewer reading only the report
        would miss warnings that caused exit code 3.
      </impact>
      <recommendation>
        Route all warnings (including review_flags) through graded_warning()
        into _WARNING_ACCUMULATOR as the single source of truth. The report
        reads from get_warnings(). Call clear_warnings() at session boundaries.
        This preserves the orchestrator contract while unifying the report's
        warning view.
      </recommendation>
    </finding>

    <finding id="F6" severity="note" category="harmonization">
      <location file="fmri_bids_recon/__main__.py" lines="123-177" />
      <description>
        Cross-module exit code harmonization: CONFIRMED ALIGNED. All four
        modules (bids-recon, fmri-preproc, fmri-first-level-proc,
        fmri-proc-orchestrator) share a 6-code contract with consistent
        semantics for codes 0-4. Exit code 5 is appropriately scoped:
        reserved in bids-recon and fmri-preproc (no model fitting), used
        as ModelError in fmri-first-level-proc (GLM singularity, insufficient
        DOF). The orchestrator correctly consumes all exit codes from each
        child module.
      </description>
      <evidence>
        Orchestrator __main__.py line 35: "Model error (propagated from
        first-level)". Orchestrator pipeline.py:166-181: exit 3 handled as
        graded_warning + status='warning' + proceed; exit 1/2/4/5 mapped to
        specific exception classes. Orchestrator pipeline.py:189: raw exit_code
        recorded in ledger.
      </evidence>
      <literature>N/A</literature>
      <impact>None. The harmonization is correct and complete.</impact>
      <recommendation>No changes needed.</recommendation>
    </finding>

    <finding id="F7" severity="minor" category="validity">
      <location file="fmri_bids_recon/stage3_map.py" lines="427-434" />
      <description>
        _select_pair() uses exact float equality (`d0 == d1`) to detect
        time-distance ties. While numerically safe for Python datetime
        arithmetic (microsecond precision, simple subtraction), the semantic
        concern is that a sub-second timing artifact (scanner clock jitter,
        reconstruction timestamp granularity) can silently determine pair
        selection when two pairs are nearly equidistant (e.g., 300.001s vs
        299.999s). True ties fire correctly; near-ties resolve silently.
      </description>
      <evidence>
        stage3_map.py line 429: `if d0 == d1:` where d0, d1 are float values
        from `abs((s.acquisition_datetime - pair_dt).total_seconds())`.
      </evidence>
      <literature>N/A (numerical precision analysis, not literature-dependent)</literature>
      <impact>
        Low. Genuine near-ties require two fieldmap pairs approximately
        equidistant from a target on opposite temporal sides, an unusual
        session layout. The selected pair is geometry-compatible regardless,
        so downstream TOPUP remains valid.
      </impact>
      <recommendation>
        Add a configurable near-tie epsilon (e.g., 1.0 second). When
        `abs(d0 - d1) < epsilon` but `d0 != d1`, emit a medium-severity
        graded_warning noting that pair selection is fragile with respect to
        timing perturbations, then proceed with the closer pair.
      </recommendation>
    </finding>

    <finding id="F8" severity="minor" category="robustness">
      <location file="fmri_bids_recon/labels.py" lines="258, 300-301" />
      <description>
        The drift guard re-derives task labels using the current session's
        common prefix (computed from all retained series descriptions).
        The prefix is session-composition-dependent: if the set of retained
        series changes between sessions (e.g., abbreviated session without
        structural scans), the prefix can lengthen, consuming more tokens
        than the original derivation. This produces spurious LabelDriftError
        or EmptyLabelError halts.
      </description>
      <evidence>
        labels.py line 258: `prefix = derive_prefix(retained_descriptions)`
        computed from ALL retained series in the current session.
        labels.py line 300: `re_derived = derive_task_label(desc, prefix)`
        uses current prefix, not the prefix that was active when the label
        was first registered.
      </evidence>
      <literature>N/A (pipeline logic analysis)</literature>
      <impact>
        Spurious pipeline halts in longitudinal studies where session
        composition varies across timepoints (e.g., structural scans
        collected only at baseline). The pipeline is correct for identical
        session compositions but fragile across varying compositions.
      </impact>
      <recommendation>
        Store the prefix used at registration time in TaskRegistryEntry
        (e.g., a `derive_prefix` field). During drift checks, use the
        stored prefix rather than the current session's prefix. This
        preserves the drift guard's intent (detecting code/config changes)
        while eliminating the false-positive pathway from session-composition
        variation.
      </recommendation>
    </finding>

    <finding id="F9" severity="minor" category="harmonization">
      <location file="fmri_bids_recon/deface.py" lines="107-113" />
      <location file="fmri_bids_recon/pipeline.py" lines="303" />
      <location file="fmri_bids_recon/errors.py" lines="100-107" />
      <description>
        Both subprocess.run() calls in deface.py use check=True, raising
        CalledProcessError on failure. pipeline.py:303 calls deface(config)
        without try/except. CalledProcessError falls through to the
        except Exception catch-all in __main__.py, logged as "Unexpected
        error" with exit code 1. This misclassifies tool execution failures
        as GuardError (exit 1) instead of tool failures (exit 4).
        Additionally, bids-recon lacks ToolExecutionError, which is present
        in all three sister modules (fmri-preproc, fmri-first-level-proc,
        fmri-proc-orchestrator).
      </description>
      <evidence>
        Cross-module Tool* error class inventory:
        ToolUnavailableError: present in all 4 modules.
        ToolVersionError: present in bids-recon + orchestrator, absent in
        preproc + first-level.
        ToolExecutionError: absent in bids-recon, present in other 3.
        Orchestrator _EXCEPTION_NAME_MAP (pipeline.py:122) and
        _exception_to_exit_code (pipeline.py:111) already handle
        ToolExecutionError -> exit 4.
      </evidence>
      <literature>N/A (cross-module harmonization analysis)</literature>
      <impact>
        Orchestrator misclassifies deface failures as GuardError (exit 1)
        instead of tool failures (exit 4). Affects ledger error taxonomy
        and downstream triage.
      </impact>
      <recommendation>
        (1) Add ToolExecutionError(BidsReconError) to errors.py.
        (2) Wrap CalledProcessError in deface.py with ToolExecutionError,
        including returncode and stderr in context.
        (3) Add except ToolExecutionError to __main__.py mapped to exit 4.
      </recommendation>
    </finding>

    <finding id="F10" severity="note" category="scientific_rigor">
      <location file="fmri_bids_recon/config.py" lines="27-29" />
      <location file="fmri_bids_recon/stage3_map.py" lines="120-200, 340-360" />
      <description>
        Two items under geometry check adequacy:
        (A) The three geometry tolerance constants (GEOMETRY_POSITION_TOL_MM=0.1,
        GEOMETRY_ORIENTATION_TOL=1e-4, GEOMETRY_VOXEL_TOL_MM=1e-3) are
        empirically calibrated, not literature-derived. No published standard
        establishes geometry matching tolerances for fieldmap association.
        The values are conservative (tight), erring toward rejection of
        borderline pairs. This is appropriate but undocumented.
        (B) Total readout time agreement is not checked within fieldmap pairs.
        The pipeline parses TotalReadoutTime into every Series (sidecar.py:80)
        but never validates that paired fieldmaps share the same value.
        TOPUP assumes identical readout times within a pair; a mismatch
        produces systematic bias in the estimated susceptibility field.
        SDCFlows (fMRIPrep) checks total readout time agreement.
      </description>
      <evidence>
        config.py lines 27-29: tolerance constants with no inline rationale.
        _geometry_check() checks 5 criteria (position, orientation, voxel
        size, matrix, PE axis) but not total readout time.
        Series.total_readout_time is parsed at sidecar.py:303 but unused
        in stage3_map.py.
      </evidence>
      <literature>
        FSL TOPUP (Andersson et al. 2003) assumes matched readout times
        within input pairs. SDCFlows checks total readout time agreement
        via get_trt(). No published standard for geometry matching tolerances.
      </literature>
      <impact>
        (A) Low. Conservative tolerances produce false rejections (visible,
        debuggable) rather than false acceptances (silent, incorrect).
        (B) Moderate. Mismatched readout times within a pair produce
        incorrect TOPUP field estimates without any QC signal.
      </impact>
      <recommendation>
        (A) P2: Add inline comment at config.py:27-29 documenting the
        empirical calibration rationale.
        (B) P1: Add total-readout-time agreement check in pair_fieldmaps()
        after the PE-direction check. Verify member_a.total_readout_time
        and member_b.total_readout_time are both non-None and agree within
        1e-6 seconds. On mismatch: raise PhaseEncodingError. On None:
        emit medium-severity graded_warning (older dcm2niix may omit the
        field).
      </recommendation>
    </finding>

    <finding id="F11" severity="note" category="robustness">
      <location file="fmri_bids_recon/pipeline.py" lines="148-165" />
      <description>
        The pipeline processes all series within a given sub/ses directory
        as belonging to a single scanning session but never validates that
        all series' AcquisitionDateTime values fall within a plausible
        single-session window. The existing PatientID cross-check
        (stage4_assemble.py:516-538) catches cross-patient contamination
        but not same-patient cross-session contamination.
      </description>
      <evidence>
        pipeline.py processes all series loaded from the staging directory
        without temporal coherence validation. AcquisitionDateTime is parsed
        for every series (sidecar.py:295) and used for ordering/association
        but not for session-boundary detection.
      </evidence>
      <literature>N/A (defensive QC check)</literature>
      <impact>
        Low probability (requires data management error) but high
        consequence: silent incorrect fieldmap associations across sessions
        with no QC signal.
      </impact>
      <recommendation>
        After loading all series, compute the AcquisitionDateTime span
        (max minus min). If the span exceeds a configurable threshold
        (e.g., 6 hours), emit a medium-severity graded_warning noting the
        span and earliest/latest series numbers. Do not halt (very long
        sessions are rare but valid).
      </recommendation>
    </finding>
  </findings>
  <summary>
    <critical_count>0</critical_count>
    <major_count>3</major_count>
    <minor_count>5</minor_count>
    <note_count>3</note_count>
    <overall_assessment>conditionally_defensible</overall_assessment>
  </summary>
  <action_items>
    <item priority="P0" target_mode="brainstorm" finding_ref="F1" description="Design vendor-aware SE-EPI classification: vendor gate implementation, per-vendor _is_spin_echo() branches, GE product sequence coverage strategy" />
    <item priority="P0" target_mode="brainstorm" finding_ref="F2" description="Design fieldmap handling overhaul: (A) relaxed pairing logic for single reverse-PE and odd-count groups, (B) GRE fieldmap classification rules and BIDS assembly for Cases 1-3" />
    <item priority="P0" target_mode="implement" finding_ref="F3" description="Resolve vNav twin SeriesNumber collisions upstream of series_map construction via ImageType[2] discrimination" />
    <item priority="P1" target_mode="implement" finding_ref="F4" description="Adaptive physio trigger threshold (Otsu), try-all-candidates association, convert halt to warning, +/-1 volume tolerance" />
    <item priority="P1" target_mode="implement" finding_ref="F5" description="Route all warnings through graded_warning() into _WARNING_ACCUMULATOR; report reads from get_warnings(); clear_warnings() per session" />
    <item priority="P1" target_mode="brainstorm" finding_ref="F8" description="Design TaskRegistryEntry schema change to store derive_prefix at registration time for drift-check stability" />
    <item priority="P1" target_mode="implement" finding_ref="F9" description="Add ToolExecutionError to errors.py, wrap CalledProcessError in deface.py, add exit-code-4 handler in __main__.py" />
    <item priority="P1" target_mode="implement" finding_ref="F10" description="Add total-readout-time agreement check in pair_fieldmaps() after PE-direction check; guard for None with medium-severity warning" />
    <item priority="P2" target_mode="implement" finding_ref="F7" description="Add configurable near-tie epsilon in _select_pair() with medium-severity graded_warning on fragile selection" />
    <item priority="P2" target_mode="implement" finding_ref="F10" description="Add inline calibration-rationale comment at geometry tolerance declarations in config.py" />
    <item priority="P2" target_mode="implement" finding_ref="F11" description="Add AcquisitionDateTime span check after series loading with configurable threshold and medium-severity warning" />
  </action_items>
</cr_report>
