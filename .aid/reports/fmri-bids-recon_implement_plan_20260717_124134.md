<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-17T12:41:34-04:00" />

  <input_reports>
    <report path="fmri-bids-recon_brainstorm_20260717_123003.md" mode="brainstorm" key_items="8" />
  </input_reports>

  <scope_note>
    Implements ONLY the action items of the specified brainstorm report: the pipeline (fmri_bids_recon)
    fieldmap-association redesign and the associated guard/meta-guard, SBRef, and mechanical fixes.
    The simulated-dataset harmonization (SBRef in the clean generator) is explicitly DEFERRED by user
    decision until the pipeline is built and is NOT in this plan. Test-suite updates (six files listed
    below) are routed to /test, not built here (/implement does not run or author tests).
  </scope_note>

  <verification_gate_cleared>
    The brainstorm recorded one required pre-build gate: confirm slice geometry survives dcm2niix
    conversion into a readable form. CLEARED during this plan's environment pre-flight (implement mode
    converted to a scratch directory and inspected:
      - The NIfTI affine translation partitions the session into the SAME three blocks as the raw
        DICOM analysis: block0 trans=(108.0,-78.05,-73.57) = func-fmap(10,12)+enback(15,19);
        block1 trans=(108.0,-77.25,-71.17) = func-fmap(22,24)+rest(27,31,35,39);
        block2 trans=(120.0,-89.14,-69.17) = dwi-fmap(43,45)+dwi(47).
      - Within-block position delta (fieldmap vs its own targets) = EXACTLY 0.0 mm after conversion.
      - Between-block delta (enback vs rest) = 2.53 mm.
      - ImageOrientationPatientDICOM present in every sidecar; PhaseEncodingDirection converted to
        BIDS j / j-.
      - dcm2niix transforms the coordinate convention (raw IPP sign/values differ from the affine
        translation), so the AFFINE TRANSLATION, not raw ImagePositionPatient, is the comparison key
        the pipeline must use. The partitioning is preserved exactly under that key.
    Consequence for the tolerance decision: within-block delta is 0.0, so a small jitter tolerance
    (order 0.01-0.1 mm) cleanly groups within-block members and separates the 2.53-mm-apart blocks.
  </verification_gate_cleared>

  <changes>

    <change id="C1" priority="P0" source_item="Extend Series with slice geometry">
      <file path="fmri_bids_recon/sidecar.py" action="modify" />
      <description>
        The association gate needs each series' slice prescription. The Series model currently loads
        only `matrix` (NIfTI shape). Add the affine-derived position, the affine itself (for
        orientation), voxel sizes, and a PE-axis accessor. load_series already opens the NIfTI via
        nibabel, so the affine is in hand.
      </description>
      <spec>
        Add fields to the frozen Series dataclass (after `matrix`, before `n_volumes` is fine; append
        to preserve positional-arg call sites is safer — see note). Store hashable types only (Series
        is frozen and must remain hashable):

            affine: tuple[tuple[float, ...], ...] | None = None
            image_position: tuple[float, float, float] | None = None
            voxel_sizes: tuple[float, float, float] | None = None

        Add a property:

            @property
            def pe_axis(self) -> str | None:
                \"\"\"Phase-encoding AXIS (first char of PhaseEncodingDirection), polarity-stripped.

                'j' and 'j-' both return 'j'. A fieldmap pair shares its targets' PE axis; the
                opposite polarities distinguish the pair members, not the axis.
                \"\"\"
                if not self.phase_encoding_direction:
                    return None
                return self.phase_encoding_direction[0]

        In load_series, after `img = nib.load(...)` and the existing shape/matrix computation, populate:

            aff = img.affine
            affine = tuple(tuple(float(v) for v in row) for row in aff)
            image_position = (float(aff[0, 3]), float(aff[1, 3]), float(aff[2, 3]))
            zooms = img.header.get_zooms()
            voxel_sizes = (float(zooms[0]), float(zooms[1]), float(zooms[2]))

        Pass affine, image_position, voxel_sizes to the Series(...) constructor.

        POSITIONAL-ARG NOTE: Series currently has `software_versions` as the only defaulted field
        (last). Adding three new defaulted fields AFTER software_versions preserves every existing
        positional constructor call. Verify load_series is the only construction site with positional
        args; test fixtures (tests/conftest.py) construct Series and will need the new fields, but that
        is a test change routed to /test, not built here.
      </spec>
      <dependencies>none</dependencies>
      <risk>
        low - Additive fields with defaults; the affine is already available. The only consumers that
        must change are the new geometry code (C2) and test fixtures (routed to /test).
      </risk>
      <rollback>Restore sidecar.py from the pre-build backup.</rollback>
      <acceptance>
        After load_series, every Series has a 4x4 affine tuple, an image_position equal to the affine
        translation, voxel_sizes from the header, and pe_axis returning the polarity-stripped first
        character of PhaseEncodingDirection (None when absent).
      </acceptance>
    </change>

    <change id="C2" priority="P0" source_item="Geometry-based association redesign">
      <file path="fmri_bids_recon/stage3_map.py" action="modify" />
      <file path="fmri_bids_recon/config.py" action="modify" />
      <description>
        Replace the nearest-preceding-strict association with a geometry-primary design: partition EPI
        series into distortion groups by shared prescription (affine position + orientation + voxel +
        matrix + PE-axis, within a tolerance); pair fieldmaps and assign targets WITHIN each group;
        use a global-optimal closest-in-time tiebreaker only when a geometry group contains more than
        one fieldmap pair; and HALT on any association uncertainty. The Mapping output interface
        (pairs, pair_to_targets, bids_relative_paths) is preserved so stage4/stage5 are unchanged.
      </description>
      <spec>
        In fmri_bids_recon/config.py (or a module constant at the top of stage3_map.py; prefer config.py
        for a single tunable point), add:

            # Geometry-match tolerance for fieldmap-to-target association. Sized to absorb
            # within-block affine-translation delta is exactly 0.0 mm; nearest distinct block is
            # 2.53 mm away, so any value in [~1e-3, ~1.0] mm separates blocks. 0.1 mm is a safe,
            # jitter-absorbing default well below the smallest plausible inter-block separation.
            GEOMETRY_POSITION_TOL_MM = 0.1
            GEOMETRY_ORIENTATION_TOL = 1e-4   # cosine components are unitless; jitter-sized
            GEOMETRY_VOXEL_TOL_MM = 1e-3

        Geometry key + compatibility helper (new, in stage3_map.py):

            def _geometry_compatible(a: Series, b: Series) -> bool:
                \"\"\"True if two series share a slice prescription within tolerance.

                Compared: affine translation (position) within GEOMETRY_POSITION_TOL_MM;
                affine rotation direction cosines within GEOMETRY_ORIENTATION_TOL; voxel sizes
                within GEOMETRY_VOXEL_TOL_MM; identical matrix; identical PE axis. The PE AXIS
                (not signed direction) is compared, so a fieldmap pair's opposite polarities do
                not split it from its targets.
                \"\"\"
                # position
                if a.image_position is None or b.image_position is None:
                    return False
                if any(abs(pa - pb) > GEOMETRY_POSITION_TOL_MM
                       for pa, pb in zip(a.image_position, b.image_position)):
                    return False
                # orientation: compare the 3x3 rotation cosines of the affines
                if a.affine is None or b.affine is None:
                    return False
                for i in range(3):
                    for j in range(3):
                        if abs(a.affine[i][j] - b.affine[i][j]) > (
                                GEOMETRY_ORIENTATION_TOL
                                + GEOMETRY_POSITION_TOL_MM * (j == 3)):
                            # (translation column handled by the position check above;
                            #  restrict this loop to the 3x3 rotation block — see note)
                            pass
                # NOTE: implement the rotation comparison over the 3x3 block only
                # (rows 0-2, cols 0-2); the translation column is covered by image_position.
                # voxel size
                if a.voxel_sizes is None or b.voxel_sizes is None:
                    return False
                if any(abs(va - vb) > GEOMETRY_VOXEL_TOL_MM
                       for va, vb in zip(a.voxel_sizes, b.voxel_sizes)):
                    return False
                # matrix + PE axis
                if a.matrix != b.matrix:
                    return False
                if a.pe_axis is None or b.pe_axis is None or a.pe_axis != b.pe_axis:
                    return False
                return True

        (Build note: the rotation-comparison loop above is sketched; implement it cleanly over the
        3x3 rotation block of the affine, e.g. compare a.affine[i][j] vs b.affine[i][j] for i in
        0..2, j in 0..2 within GEOMETRY_ORIENTATION_TOL. The pseudocode's inline (j==3) hack is NOT
        to be carried into the implementation.)

        Redesigned pair_fieldmaps (geometry-grouped, replaces consecutive-by-time pairing):

            def pair_fieldmaps(fmaps, ordered, guard_log) -> list[FieldmapPair]:
                # 1. Partition fmaps into geometry groups via _geometry_compatible
                #    (transitive grouping: a series joins a group if compatible with any member).
                # 2. Within each geometry group:
                #    - There must be exactly two opposite-PE members forming one pair, OR a set that
                #      cleanly splits into opposite-PE pairs (2, 4, ... members balanced by polarity).
                #    - Validate opposite PE (existing GUARD 1 logic) -> guard_log['opposite_pe_within_pair']=True
                #    - Validate _PA/_AP name-token vs physics label (existing GUARD 4) ->
                #      guard_log['dir_label_pe_agreement']=True
                #    - An ODD member count, or members that cannot be balanced into opposite-PE pairs,
                #      raises PhaseEncodingError (halt): the geometry group is ambiguous.
                #      This REPLACES the silent range(0, n-1, 2) drop (CR F3).
                # 3. Build FieldmapPair objects, recording each pair's geometry (via one member) and
                #    modality/run_index as before. run_index enumerated per modality in acquisition order.
                # Set guard_log['fieldmap_pairing_unambiguous']=True after the group loop completes.

        Redesigned map_fieldmaps (geometry-primary assignment, global-optimal time tiebreaker):

            def map_fieldmaps(pairs, targets, ordered, guard_log) -> Mapping:
                pair_to_targets = {i: [] for i in range(len(pairs))}
                for s, role in targets_sorted_by_time:
                    # eligible pairs = geometry+PE-axis compatible with this target
                    eligible = [i for i, p in enumerate(pairs)
                                if _geometry_compatible(p.member_a, s)]
                    guard_log['fieldmap_target_geometry_match'] = True
                    guard_log['pe_axis_target_match'] = True   # pe_axis is part of _geometry_compatible
                    if not eligible:
                        raise FieldmapCoverageError(
                            f\"Series {s.series_number} has no geometry-compatible fieldmap pair.\",
                            context={...})
                    if len(eligible) == 1:
                        chosen = eligible[0]
                    else:
                        # global-optimal closest-in-time among geometry-compatible pairs.
                        # Each target independently takes its closest compatible pair (separable
                        # objective => the global optimum for one-to-many assignment). A TIE
                        # (two pairs equidistant in time) is genuine ambiguity -> HALT.
                        def pair_time(i):
                            p = pairs[i]
                            return max(p.member_a.acquisition_datetime,
                                       p.member_b.acquisition_datetime)
                        dists = sorted(((abs((s.acquisition_datetime - pair_time(i)).total_seconds()), i)
                                        for i in eligible))
                        if len(dists) > 1 and dists[0][0] == dists[1][0]:
                            raise FieldmapCoverageError(
                                f\"Series {s.series_number} is equidistant in time from two \"
                                f\"geometry-compatible fieldmap pairs; association ambiguous.\",
                                context={...})
                        chosen = dists[0][1]
                    pair_to_targets[chosen].append(s)
                guard_log['association_unambiguous'] = True
                # Orphan check (halt on ANY uncertainty, per user decision): every pair must serve >=1 target.
                for i, p in enumerate(pairs):
                    if not pair_to_targets[i]:
                        raise FieldmapCoverageError(
                            f\"Fieldmap pair (run_index={p.run_index}, modality={p.modality}) \"
                            f\"serves no target.\", context={...})
                guard_log['no_orphan_pairs'] = True
                return Mapping(pairs=pairs, pair_to_targets=pair_to_targets)

        REMOVED behaviors: the nearest-preceding-strict policy (lines 234-345), the strict
        pair_dt < target_dt eligibility (CR F6), the exact-EES geometry guard (CR F5, superseded by the
        tolerance-based _geometry_compatible), and the consecutive-by-time / odd-drop pairing (CR F3).
        The EES/TotalReadoutTime fields remain in Series and sidecars (BIDS-required) but are no longer
        the association gate.

        PRESERVED: Mapping / FieldmapPair dataclasses and their fields; order_series (still used for
        run_index enumeration and the time tiebreaker).

        43,45 = DIFFUSION token). The classifier assigns FMAP_DWI only to the DIFFUSION-token members
        (43,45), which form the opposite-PE pair; the M-token members are classified elsewhere and do
        not enter fmaps. The geometry grouping operates on whatever the classifier labels FMAP_*, so
        this is handled upstream; no special-casing here.
      </spec>
      <dependencies>C1 (Series geometry fields), C3 (guard_log threading + guard names)</dependencies>
      <risk>
        high - The core redesign; replaces the entire association algorithm. Mitigations: the Mapping
        output interface is preserved so stage4/stage5 are untouched; every failure path raises a
        GuardError (halt) rather than degrading; the geometry gate is verified on real converted data
        (within-block 0.0 mm, between-block 2.53 mm). The existing test_map.py encodes the OLD behavior
        and WILL fail; updating it is a /test task, not a regression.
      </risk>
      <rollback>Restore stage3_map.py and config.py from the pre-build backup.</rollback>
      <acceptance>
        func-fmap pair at block0, every rest target to the func-fmap pair at block1, and the dwi target
        to the dwi-fmap pair at block2, using no acquisition-order information (the two func pairs are
        distinguished by geometry alone). A target with no geometry-compatible pair, an ambiguous
        (odd/unbalanced) fieldmap group, a time tie among eligible pairs, or an orphan pair each raises
        a GuardError.
      </acceptance>
    </change>

    <change id="C3" priority="P0" source_item="Real meta-guard + new association guards">
      <file path="fmri_bids_recon/stage6_validate.py" action="modify" />
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>
        Make the meta-guard genuine: initialize the guard log to all-False and have each guard record
        its own execution, replacing the hardcoded all-True construction (CR F2). Update the guard-name
        registry for the redesigned association guards.
      </description>
      <spec>
        In stage6_validate.py, update ALL_GUARD_NAMES to reflect the redesign. Remove the obsolete
        fieldmap_geometry_ees_match and target_pair_coverage; add the new association guards. Resulting
        fieldmap-related entries:

            \"opposite_pe_within_pair\",          # retained (pair validity)
            \"dir_label_pe_agreement\",           # retained (name-token vs physics)
            \"fieldmap_pairing_unambiguous\",     # new (geometry group forms clean opposite-PE pairs)
            \"fieldmap_target_geometry_match\",   # new (target has a geometry-compatible pair)
            \"pe_axis_target_match\",             # new (fieldmap PE axis == target PE axis)
            \"association_unambiguous\",           # new (no time tie among eligible pairs)
            \"no_orphan_pairs\",                  # retained (every pair serves >=1 target)

        Keep the non-fieldmap guard names unchanged (dcm2niix_version_floor, anat_suffix_physics,
        label_injectivity, non_empty_labels, no_label_drift, no_rename_collision, exact_volume_counts).

        In __main__.py, REPLACE line 199 (`guard_log = {name: True for name in ALL_GUARD_NAMES}`) with:

            guard_log = {name: False for name in ALL_GUARD_NAMES}

        Thread this guard_log into pair_fieldmaps(...) and map_fieldmaps(...) (C2 signatures take it),
        so each guard sets its own entry True at execution. The guards owned by other stages
        (classify, labels, volume counts) must ALSO set their entries at their execution points rather
        than being assumed; for stages not being edited in this plan, set their guard_log entries True
        at the existing call site in __main__ immediately AFTER the stage returns successfully (a
        minimal honest signal that the stage ran), and record in the build report which guards are
        call-site-recorded vs self-recorded. The fieldmap guards (this plan's focus) are self-recorded
        inside stage3_map. assert_guards_executed(combined_guard_log) at line 232 is unchanged; it now
        checks a genuinely-populated log.

        SCOPE SURFACE (build must halt-and-ask if this expands): fully self-recording every non-fieldmap
        guard would require editing classify/labels/volume-count stages beyond this plan's fieldmap
        scope. The plan's directive is: self-record the fieldmap guards inside stage3_map; call-site
        record the rest in __main__ after each stage returns. If the build agent finds a guard that
        cannot be honestly recorded either way, halt and surface it rather than defaulting it True.
      </spec>
      <dependencies>none (but C2 consumes the guard_log it threads)</dependencies>
      <risk>
        medium - The meta-guard becoming real means a guard that genuinely does not run will now HALT
        the batch (its entry stays False). That is the intended behavior, but it can surface
        latent gaps where a guard was never actually wired. The call-site recording for non-fieldmap
        stages is a deliberate, documented interim honest signal, not a hardcode.
      </risk>
      <rollback>Restore stage6_validate.py and __main__.py from the pre-build backup.</rollback>
      <acceptance>
        guard_log initializes all-False; after a successful subject, every entry in ALL_GUARD_NAMES is
        True by genuine record (fieldmap guards set inside stage3_map, others set at their __main__
        call site post-return). Forcing any single fieldmap guard not to run leaves its entry False and
        assert_guards_executed raises GuardError naming it.
      </acceptance>
    </change>

    <change id="C4" priority="P1" source_item="SBRef in association targets">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>
        Include SBRef and DWI_SBREF in the fieldmap association target set so they inherit their block's
        fieldmap (B0FieldSource) and appear in its IntendedFor, per the downstream-agnostic completeness
        decision. stage5_render already emits both IntendedFor and B0FieldIdentifier/B0FieldSource for
        whatever targets the Mapping contains, so no render change is needed.
      </description>
      <spec>
        In __main__.py, change the targets construction (currently line 176):

            targets = [(series_map[sn], role) for sn, role in roles.items()
                       if role in (Role.BOLD, Role.DWI)]

        to include the reference roles:

            targets = [(series_map[sn], role) for sn, role in roles.items()
                       if role in (Role.BOLD, Role.DWI, Role.SBREF, Role.DWI_SBREF)]

        The geometry gate (C2) will place each SBRef in its block (an SBRef shares its BOLD run's
        prescription), so it associates with the same fieldmap pair as its BOLD. No SBRef-specific
        logic is required. Confirm stage4_assemble writes B0FieldSource onto SBRef sidecars via the
        existing target loop (stage5_render.py:167-176 iterates mapping targets uniformly).
      </spec>
      <dependencies>C2 (SBRef must flow through the geometry assignment)</dependencies>
      <risk>
        low - One filter widened. SBRefs share their BOLD's geometry so they group cleanly; verified in
        the converted data that SBRef series (e.g. SN26,30 rest SBRef) share the rest block's affine.
      </risk>
      <rollback>Restore __main__.py from the pre-build backup.</rollback>
      <acceptance>
        Each SBRef and DWI_SBREF appears in its block's fieldmap IntendedFor and carries a B0FieldSource
        equal to that pair's identifier.
      </acceptance>
    </change>

    <change id="C5" priority="P2" source_item="CR F8 (missing AcquisitionDateTime policy)">
      <file path="fmri_bids_recon/sidecar.py" action="modify" />
      <description>
        _parse_acquisition_datetime("") currently raises a bare ValueError (via fromisoformat) that
        crashes load_series, while stage4._acq_sort_key tolerates the same absence. Adopt one
        consistent, contextual policy. Since the association tiebreaker (C2) needs time only to break a
        geometry tie, and the pipeline now halts on any association uncertainty, a missing timestamp
        that would be needed for a tie must halt with a clear, named error rather than an opaque
        ValueError.
      </description>
      <spec>
        Wrap the parse in load_series so a missing/unparseable AcquisitionDateTime raises a typed,
        contextual GuardError naming the offending series and sidecar path, e.g.:

            try:
                acquisition_datetime = _parse_acquisition_datetime(acq_dt_raw)
            except (ValueError, TypeError) as exc:
                raise ConversionError(
                    f\"Series sidecar {sidecar_path.name} has missing or unparseable \"
                    f\"AcquisitionDateTime ({acq_dt_raw!r}); cannot order or associate it.\",
                    context={\"sidecar\": str(sidecar_path), \"raw\": acq_dt_raw}) from exc

        (ConversionError is an existing GuardError subclass; if a more specific type is preferred, add a
        MetadataError(GuardError) in errors.py — but reusing ConversionError avoids widening the
        exception surface. Build may choose either; state the choice in the report.)
        Leave stage4._acq_sort_key's tolerant handling as-is: by the time assembly runs, load_series has
        already halted on any unparseable timestamp, so _acq_sort_key's fallback is unreachable dead-safe
        code, not an inconsistency.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - Converts an opaque crash into a typed, contextual halt. Behavior change only on already-broken input.</risk>
      <rollback>Restore sidecar.py from the pre-build backup.</rollback>
      <acceptance>A sidecar with absent AcquisitionDateTime raises a GuardError naming the series/sidecar, not a bare ValueError.</acceptance>
    </change>

    <change id="C6" priority="P2" source_item="CR F9 (validator nested-key access)">
      <file path="fmri_bids_recon/stage6_validate.py" action="modify" />
      <description>
        run_bids_validator guards only the outer "issues" key then accesses parsed["issues"]["issues"]
        and parsed["issues"]["codeMessages"], so a validator output-schema change raises KeyError/
        TypeError instead of the intended ToolUnavailableError (dataset UNCHECKED).
      </description>
      <spec>
        Replace the direct nested access (lines ~145-146) with a guarded extraction:

            issues_block = parsed.get(\"issues\")
            if not isinstance(issues_block, dict) or \"issues\" not in issues_block:
                raise ToolUnavailableError(
                    \"bids-validator-deno output has an unexpected 'issues' shape; dataset is UNCHECKED.\",
                    context={\"issues_type\": type(issues_block).__name__})
            issues_list = issues_block[\"issues\"]
            code_messages = issues_block.get(\"codeMessages\", {})

        Keep the existing outer `if \"issues\" not in parsed` check (line 139) or fold it into the above;
        either way every schema deviation must raise ToolUnavailableError, never a bare KeyError.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - Defensive parsing only; no behavior change on well-formed validator output.</risk>
      <rollback>Restore stage6_validate.py from the pre-build backup.</rollback>
      <acceptance>A validator JSON whose "issues" is a list (or lacks the inner "issues" key) yields ToolUnavailableError, not an uncaught exception.</acceptance>
    </change>

  </changes>

  <execution_order>
    C1, C3, C2, C4, C5, C6

    Rationale. C1 first: the Series geometry fields underpin C2's gate. C3 before C2: C3 defines the
    guard-name registry and the all-False guard_log that C2's functions record into, and updates the
    __main__ construction; landing it first means C2's guard_log threading matches an existing shape.
    C2 next: the core redesign, consuming C1's fields and C3's guard_log. C4 after C2: SBRef must flow
    through the finished geometry assignment. C5 and C6 last: isolated mechanical fixes (sidecar.py and
    stage6_validate.py respectively), independent of the association logic.

    File partitioning for dispatch: C1+C5 = sidecar.py (sequential, same file); C3 spans
    stage6_validate.py + __main__.py; C2 spans stage3_map.py + config.py; C4 = __main__.py; C6 =
    stage6_validate.py. Because C3, C4 both touch __main__.py and C3, C6 both touch stage6_validate.py,
    the __main__.py edits (C3 then C4) and the stage6_validate.py edits (C3 then C6) must be sequential
    within their files. Safe dispatch: C1 -> C3 -> C2 -> C4 -> C5 -> C6, sequential, halting at the
    first failure (per the no-git per-file rollback granularity below).
  </execution_order>

  <rollback_strategy>
    This project is NOT a git repository (verified earlier this session). Rollback is file-backup based
    and MUST be taken before the first edit. Before C1, copy the five target files to a timestamped
    backup:

        mkdir -p sandbox/backups/pre_implement_20260717_124134
        cp fmri_bids_recon/sidecar.py fmri_bids_recon/stage3_map.py fmri_bids_recon/config.py \
           fmri_bids_recon/stage6_validate.py fmri_bids_recon/__main__.py \
           sandbox/backups/pre_implement_20260717_124134/

    Record SHA-256 of each original in the build report. Restoring is an overwrite (destructive-policy:
    explicit per-invocation user approval; the build surfaces the request, never restores unilaterally).
    Granularity is per-file; several changes touch __main__.py and stage6_validate.py, so restoring
    either reverts all of its changes. Dispatch sequentially and halt at first failure so at most one
    change is in flight. Use ONLY this backup directory; earlier backups predate this session's builds.
  </rollback_strategy>

  <post_build>
    Not part of this plan; recorded so nothing is silently dropped.
    1. TESTS: test_map.py, test_assemble.py, test_render.py, test_guard_coverage.py, test_report.py,
       and tests/conftest.py encode the OLD nearest-preceding behavior and the old Series constructor.
       They WILL fail after this build and require redesign under /test (per the design-vs-obsolete
       disposition rules of /test). This build runs no tests.
    2. The dcm2niix geometry verification gate is already CLEARED (see verification_gate_cleared);
       no further gate blocks the build.
    3. Deferred by user: simulated-dataset harmonization (SBRef association in the clean generator;
       adversary-meaning notes) against fmri-bids-recon_implement_plan_20260717_101506.md, to be actioned
       after this pipeline build.
    4. The scratch conversion at scratchpad/dcm2niix_probe/ is a throwaway verification artifact; it
       may be removed (destructive; requires approval) at end-session.
  </post_build>
</implement_plan>
