<cr_report>
  <meta project="fmri-bids-recon" mode="cr" timestamp="2026-07-17T11:35:14-04:00" />

  <scope>
    Fieldmap-to-target pairing path in the fmri_bids_recon pipeline (user-designated focus), plus a
    sweep of the stages that feed and police it. Files read in full this session:
    fmri_bids_recon/stage2_classify.py (387 L), stage3_map.py (363 L), stage4_assemble.py fieldmap
    branch and acq-sort (590 L, relevant sections), stage5_render.py (176 L), stage6_validate.py
    (226 L), sidecar.py (276 L), __main__.py orchestration (345 L). NOT reviewed: stage1_convert,
    deface, physio, report, tsv, runs, versions, labels beyond their interaction with pairing.
    This review is READ-ONLY; no code was modified.
  </scope>

  <research_conducted>
    Two research agents dispatched under the Topic Approval Gate (user reframed the primary
    question from "what acquisition order does ABCD use" to "how should association be determined
    WITHOUT relying on order"). Both returned lit_state=consensus.

    R1 (order-independent fieldmap-to-target association):
      - BIDS 1.7 introduced B0FieldIdentifier / B0FieldSource as the recommended order-independent
        association mechanism, superseding IntendedFor; association is by shared string label, not
        file order or timestamp. The spec RECOMMENDS deriving the identifier from DICOM Protocol
        Name (0018,1030) or Sequence Name (0018,0024).
        [bids-specification.readthedocs.io MRI data page; BIDS PR #622]
      - heudiconv populate_intended_for matches on ShimSetting ("Shims") or ImagingVolume
        (position, orientation, voxel size, matrix) as PRIMARY signals; temporal proximity
        ("Closest") is only a TIEBREAKER. [heudiconv.readthedocs.io v1.4.0]
      - SDCFlows keys on B0FieldIdentifier, falling back to IntendedFor path grouping; it checks
        neither shim nor geometry itself, trusting the converter's association.
        [nipreps.org/sdcflows methods]
      - Missing/incorrect association metadata causes fMRIPrep and QSIPrep to SILENTLY skip
        distortion correction (no validation error). [Cieslak et al. 2022, NeuroImage; PMC9981813]

    R2 (SBRef association requirement; PE-axis matching requirement):
      - BIDS states fieldmaps "MAY be linked" via IntendedFor (permissive); no SBRef-specific
        mandate. fMRIPrep applies SDC to whatever reference it uses regardless of SBRef presence
        in IntendedFor. [BIDS v1.6.0 Section 8.9; Neurostars 4276]
      - PE-axis identity between fieldmap and target is a HARD computational requirement in
        SDCFlows: init_pepolar_unwarp_wf compares epi_pe[0] == pe_dir[0] and excludes fieldmaps
        whose PE axis differs. Distortion is confined to the PE axis, so an orthogonal-axis
        fieldmap physically cannot correct the target. [nipreps/sdcflows pepolar.py commit 5b4cc23;
        fMRIPrep SDC docs v1.0.3]
  </research_conducted>

  <findings>

    <finding id="F1" severity="major" category="scientific_rigor">
      <location file="fmri_bids_recon/stage3_map.py" lines="234-345" />
      <description>
        The fieldmap-to-target association is computed by map_fieldmaps using a
        NEAREST-PRECEDING-STRICT policy: each BOLD/DWI target is assigned to the pair whose later
        member has the most recent acquisition_datetime that still strictly precedes the target
        (lines 291-301, 345). Acquisition order is thus the PRIMARY and SOLE association signal.
        The established tools invert this: they associate on order-independent metadata (shim
        settings, imaging geometry, or a Protocol/Sequence-Name-derived B0FieldIdentifier) and use
        temporal proximity only as a tiebreaker. The current policy silently encodes an assumption
        about acquisition order (each fieldmap immediately precedes exactly the runs it covers,
        with no later same-modality pair intervening). When that assumption does not hold, the
        policy either mis-assigns silently or raises a spurious FieldmapCoverageError.
      </description>
      <evidence>
        stage3_map.py:294-301 selects best_pair by max member datetime strictly preceding the
        target; :345 appends the target to that single pair; :303-314 raises FieldmapCoverageError
        if no preceding pair exists. No shim, geometry, PE-axis, or identifier signal participates
        in the assignment. Contrast heudiconv POPULATE_INTENDED_FOR_OPTS (Shims / ImagingVolume
        primary, Closest-in-time as tiebreaker) and BIDS 1.7 B0FieldIdentifier.
      </evidence>
      <literature>
        BIDS 1.7 B0FieldIdentifier/B0FieldSource (bids-specification, PR #622); heudiconv
        populate_intended_for matching_parameters (Shims/ImagingVolume); SDCFlows association
        (nipreps.org); Cieslak et al. 2022 (PMC9981813) on silent SDC skip when association is
        wrong or absent.
      </literature>
      <impact>
        A protocol where fieldmaps are grouped (e.g., all acquired at session start) rather than
        interleaved immediately before their targets will either (a) assign every functional run
        to the last preceding pair, orphaning the earlier pair and raising a coverage error on a
        valid dataset, or (b) where an intervening pair exists, associate a run with a fieldmap
        that was not acquired for it. Downstream, an incorrect association does not error: fMRIPrep
        applies the wrong warp or skips SDC silently. This is the central scan-fieldmap-mismatch
        risk.
      </impact>
      <recommendation>
        Redesign the association basis: primary match on shim settings and/or imaging geometry
        (ImageOrientationPatient, ImagePositionPatient, voxel size, matrix), and ideally emit a
        B0FieldIdentifier derived from Protocol Name / Sequence Name, with temporal proximity
        demoted to a tiebreaker only. This is design work with real options (shim-only vs
        geometry-only vs identifier-first vs a layered combination) and belongs in /brainstorm per
        the user's routing decision, not a point patch.
      </recommendation>
    </finding>

    <finding id="F2" severity="major" category="reproducibility">
      <location file="fmri_bids_recon/__main__.py" lines="199-232" />
      <description>
        The Layer-1 meta-guard (stage6_validate.assert_guards_executed) exists to ensure every
        named guard actually ran, on the stated principle that "a guard that never ran is
        indistinguishable from a guard that does not work." But the guard log it checks is
        constructed unconditionally as all-True: guard_log = {name: True for name in
        ALL_GUARD_NAMES} (line 199), per participant, before assembly. No per-guard status is set
        anywhere in the codebase, and the guard names (opposite_pe_within_pair,
        fieldmap_geometry_ees_match, target_pair_coverage, no_orphan_pairs, dir_label_pe_agreement)
        are referenced at NO execution point outside the ALL_GUARD_NAMES list. The meta-guard
        therefore cannot fail.
      </description>
      <evidence>
        grep across fmri_bids_recon/ finds zero per-key assignments to guard_log; the five pairing
        guard names appear only in stage6_validate.py:28-41. __main__.py:199 hardcodes all-True;
        :232 asserts against it. The actual guards in stage3_map.py DO raise real exceptions
        (PhaseEncodingError, FieldmapGeometryError, FieldmapCoverageError), so guard EXECUTION is
        real; only the CERTIFICATION that they executed is inoperative.
      </evidence>
      <literature>
        The pattern the meta-guard intends to enforce is standard defensive verification (guard
        that the guard ran). The docstring at stage6_validate.py:4-6 states the exact failure mode
        the current implementation does not prevent.
      </literature>
      <impact>
        The pipeline advertises a validation layer that provides no assurance. A future refactor
        that caused pair_fieldmaps or map_fieldmaps to skip a guard (e.g., an early return on an
        empty fieldmap list) would pass the meta-guard silently. On a run with zero fieldmaps, all
        five pairing guards are recorded as executed though none of their code ran.
      </impact>
      <recommendation>
        Either wire genuine per-guard instrumentation (each guard sets its own log entry True at
        the point it executes, initialised False), or remove the meta-guard rather than present
        false assurance. The choice (real instrumentation vs removal vs a redesigned verification)
        is a design decision for /brainstorm.
      </recommendation>
    </finding>

    <finding id="F3" severity="major" category="robustness">
      <location file="fmri_bids_recon/stage3_map.py" lines="155-231" />
      <description>
        pair_fieldmaps sorts each modality's fieldmaps by acquisition_datetime and pairs
        consecutive members: for i in range(0, len(members) - 1, 2) (line 158). With an ODD count,
        the last member is not paired. More importantly, the pairing is purely positional: it
        assumes the first two chronologically are an intended AP/PA pair. In the human-centric
        scenario of a corrupt fieldmap followed by a re-acquisition (three members), the code pairs
        members 0 and 1 and sets member 2 aside. If the re-run produced a same-axis image (e.g.
        AP, AP, PA in time order), GUARD 1 (opposite-PE) catches it. But if the order is
        AP(bad), PA, AP(good-rerun), the pair (AP-bad, PA) has opposite PE and passes, and the good
        re-acquisition is set aside.
      </description>
      <evidence>
        stage3_map.py:158 loop step 2 leaves the last of an odd count unpaired. The dropped member
        is routed by stage4_assemble.py:416-426 to sourcedata/unpaired_fmap/ with a ReviewFlag
        code "unpaired_fieldmap". That flag names the SET-ASIDE series and does not warn that the
        FORMED pair (member 0 + member 1) may itself be the wrong pairing. The opposite-PE guard
        (stage3_map.py:167-192) filters only same-axis pairs, not wrong-partner pairs of opposite
        axis.
      </evidence>
      <literature>
        Order-independent association (F1 literature) would remove the positional assumption
        entirely: a re-acquired fieldmap sharing shim/geometry with its target would be selectable
        on merit rather than discarded by position.
      </literature>
      <impact>
        A corrupt fieldmap paired with a valid opposite-PE partner passes all pairing guards; the
        valid re-acquisition is diverted to sourcedata and the corrupt one is applied to every
        target the pair covers. The review flag points the human reviewer at the innocent series,
        making the actual mis-pair easy to wave through. This is the exact class of silent
        scan-fieldmap mismatch the review was commissioned to find.
      </impact>
      <recommendation>
        Resolve jointly with F1: once association is metadata-based, pairing should select the
        AP/PA members that share shim/geometry with each other AND with their target, rather than
        pairing by chronological adjacency. Interim hardening: when a modality has an odd fieldmap
        count or more members than expected pairs, raise or flag the PAIRING as ambiguous (naming
        the formed pair), not merely the leftover member.
      </recommendation>
    </finding>

    <finding id="F4" severity="major" category="validity">
      <location file="fmri_bids_recon/stage3_map.py" lines="318-343" />
      <description>
        GUARD 2 validates that the assigned pair's effective_echo_spacing and matrix match the
        target's, but does NOT check that the fieldmap pair's phase-encoding AXIS matches the
        target's PE axis. Research (R2) establishes PE-axis identity as a HARD computational
        requirement for pepolar SDC: SDCFlows compares epi_pe[0] == pe_dir[0] and excludes
        non-matching-axis fieldmaps, because susceptibility distortion is confined to the PE axis
        and an orthogonal fieldmap cannot estimate or correct it. A fieldmap with matching matrix
        and EES but an orthogonal PE axis (e.g. fieldmap j/j-, target i) passes the current guard
        and is assigned to a target it physically cannot correct.
      </description>
      <evidence>
        stage3_map.py:319-343 checks member.effective_echo_spacing and member.matrix only. The
        Series model carries phase_encoding_direction (sidecar.py:75) but map_fieldmaps never
        compares the pair's PE axis to the target's. ALL_GUARD_NAMES (stage6_validate.py:28-41)
        contains no PE-axis-vs-target guard. SDCFlows pepolar.py enforces epi_pe[0] == pe_dir[0].
      </evidence>
      <literature>
        nipreps/sdcflows pepolar.py (commit 5b4cc23): "different phase encoding dimension in the
        target file and the '_epi' file(s) (for example 'i' and 'j') is not supported"; fMRIPrep
        SDC docs v1.0.3 on PE-confined distortion.
      </literature>
      <impact>
        An axis-mismatched assignment yields an invalid or absent correction downstream with no
        error at curation time. Rare in a single-protocol ABCD dataset (all EPIs typically j), but
        exactly the kind of cross-protocol or mis-labelled-PE case a curation pipeline should catch
        rather than pass.
      </impact>
      <recommendation>
        Add a PE-axis-compatibility guard: the assigned pair's axis (first character of
        PhaseEncodingDirection) must equal the target's. Register it in ALL_GUARD_NAMES. Sequence
        with F1/F2 in /brainstorm since it is part of the same association-correctness surface.
      </recommendation>
    </finding>

    <finding id="F5" severity="minor" category="validity">
      <location file="fmri_bids_recon/stage3_map.py" lines="320-331" />
      <description>
        GUARD 2 compares effective_echo_spacing with exact inequality
        (member.effective_echo_spacing != s.effective_echo_spacing). EES is a float parsed
        independently from each sidecar; if the fieldmap and target sidecars carry EES computed or
        rounded differently (different dcm2niix runs, manual edits), an exact-equality test raises
        FieldmapGeometryError on a physically-compatible pair.
      </description>
      <evidence>stage3_map.py:320 uses !=; no tolerance. The matrix comparison (:332) is integer-tuple equality, which is safe; only the EES float comparison is brittle.</evidence>
      <literature>Standard floating-point comparison guidance: compare within a relative/absolute tolerance, not exact equality, for physically-derived quantities.</literature>
      <impact>False-positive geometry error halting an otherwise valid association; low frequency within a single homogeneous protocol.</impact>
      <recommendation>Compare EES within a small relative tolerance (e.g. math.isclose with rel_tol ~1e-6). Keep matrix as exact integer equality.</recommendation>
    </finding>

    <finding id="F6" severity="minor" category="robustness">
      <location file="fmri_bids_recon/stage3_map.py" lines="298" />
      <description>
        Eligibility uses strict inequality pair_dt &lt; target_dt. If a target shares the exact
        acquisition_datetime of its fieldmap's later member (possible with second-precision
        timestamps on rapid back-to-back series), that pair becomes ineligible and the target is
        assigned to an earlier pair or raises a coverage error.
      </description>
      <evidence>stage3_map.py:298 `if pair_dt &lt; target_dt`. acquisition_datetime precision depends on the sidecar's AcquisitionDateTime string; strptime formats at :133-138 include second-only forms.</evidence>
      <literature>Interacts with F1: an order-independent association removes the dependence on strict temporal ordering entirely.</literature>
      <impact>Edge-case mis-assignment or spurious coverage error when timestamps collide; subsumed if F1 demotes time to a tiebreaker.</impact>
      <recommendation>Subsume under the F1 redesign. If temporal proximity is retained as a tiebreaker, use &lt;= with a deterministic secondary key, and document the tie policy.</recommendation>
    </finding>

    <finding id="F7" severity="note" category="validity">
      <location file="fmri_bids_recon/__main__.py" lines="176" />
      <description>
        The target list for fieldmap association admits only Role.BOLD and Role.DWI; SBRef and
        DWI_SBREF are excluded, so single-band references receive no B0FieldSource and appear in no
        fieldmap IntendedFor. Research (R2) confirms this is permissive-compliant: BIDS does not
        mandate SBRef association and fMRIPrep corrects the reference regardless.
      </description>
      <evidence>__main__.py:176 filters roles to BOLD, DWI. stage3_map.py:280-282 silently continues on any unmapped role.</evidence>
      <literature>BIDS v1.6.0 Section 8.9 ("MAY be linked"); Neurostars 4276 (fMRIPrep core dev: "more BIDS-correct" to include SBRef, but not required).</literature>
      <impact>None operationally. Documented so the design choice is explicit rather than incidental, and so the same choice in the simulated-dataset generator (SBRef omitted from fieldmap IntendedFor) is confirmed correct.</impact>
      <recommendation>Optional: include SBRef in the covering fieldmap's IntendedFor for stricter BIDS-correctness. Not required. Decide during the F1 brainstorm if the association is being reworked anyway.</recommendation>
    </finding>

    <finding id="F8" severity="note" category="robustness">
      <location file="fmri_bids_recon/sidecar.py" lines="117-145, 222-223" />
      <description>
        The entire pairing path depends on acquisition_datetime, parsed in load_series. A sidecar
        lacking AcquisitionDateTime yields "" (line 222), which fails all four strptime formats and
        then datetime.fromisoformat("") raises ValueError, crashing load_series and the whole run.
        The pipeline fails hard rather than degrading or flagging.
      </description>
      <evidence>sidecar.py:222 `raw.get("AcquisitionDateTime", "")`; :133-145 the parse chain ending in fromisoformat, which raises on "". Note stage4_assemble._acq_sort_key (stage4:240-246) DOES guard with try/except and a None fallback, so the two acq-time consumers handle absence inconsistently.</evidence>
      <literature>Interacts with F1: reducing the criticality of acquisition_datetime in association reduces the blast radius of a missing timestamp.</literature>
      <impact>A single sidecar missing AcquisitionDateTime aborts the batch. Fail-loud is defensible, but the inconsistency with stage4's tolerant handling suggests the crash is unintended rather than a deliberate gate.</impact>
      <recommendation>Decide a single policy for missing AcquisitionDateTime (raise a typed, contextual error naming the offending series, or degrade with a review flag) and apply it consistently across load_series and _acq_sort_key.</recommendation>
    </finding>

    <finding id="F9" severity="minor" category="robustness">
      <location file="fmri_bids_recon/stage6_validate.py" lines="139-146" />
      <description>
        run_bids_validator guards only `if "issues" not in parsed` (line 139), then accesses the
        nested parsed["issues"]["issues"] and parsed["issues"].get("codeMessages", ...) (lines
        145-146). If the validator's output schema changes such that parsed["issues"] is a list or
        lacks an inner "issues" key, this raises KeyError/TypeError instead of the intended graceful
        ToolUnavailableError, so a schema drift is reported as an uncaught crash rather than
        "dataset UNCHECKED".
      </description>
      <evidence>stage6_validate.py:139 checks only the outer key; :145 assumes parsed["issues"] is a dict with an "issues" key. The surrounding design (lines 118-143) otherwise converts every tool-level failure into ToolUnavailableError.</evidence>
      <literature>Not applicable (defensive-parsing concern, not methodological).</literature>
      <impact>Tangential to fieldmap pairing. A bids-validator-deno version whose JSON shape differs would crash the validation stage instead of signalling UNCHECKED. Low likelihood, contained blast radius.</impact>
      <recommendation>Wrap the nested access in the same ToolUnavailableError guard used for the other schema expectations, checking that parsed["issues"] is a dict containing "issues".</recommendation>
    </finding>

  </findings>

  <summary>
    <critical_count>0</critical_count>
    <major_count>4</major_count>
    <minor_count>3</minor_count>
    <overall_assessment>needs_revision</overall_assessment>
  </summary>

  <action_items>
    <item priority="P0" target_mode="brainstorm" finding_ref="F1" description="Redesign fieldmap-to-target association onto order-independent metadata (shim settings and/or imaging geometry, and ideally a Protocol/Sequence-Name-derived B0FieldIdentifier), demoting acquisition order to a tiebreaker. Real design options to weigh; do not patch nearest-preceding-strict in place." />
    <item priority="P0" target_mode="brainstorm" finding_ref="F2" description="Repair or remove the inoperative meta-guard: either instrument each guard to record its own execution (initialised False), or drop assert_guards_executed rather than present false assurance. Decide the verification model." />
    <item priority="P1" target_mode="brainstorm" finding_ref="F3" description="Replace positional (chronological-adjacency) pairing with merit-based AP/PA selection sharing shim/geometry with each other and the target; harden the odd-count / extra-member case to flag the FORMED pair as ambiguous, not only the leftover member. Sequence with F1." />
    <item priority="P1" target_mode="brainstorm" finding_ref="F4" description="Add a PE-axis-compatibility guard (assigned pair axis must equal target PE axis) and register it in ALL_GUARD_NAMES. Part of the same association-correctness surface as F1/F2." />
    <item priority="P2" target_mode="implement" finding_ref="F5" description="Compare EffectiveEchoSpacing within a relative tolerance (math.isclose) rather than exact float inequality; keep matrix as exact integer equality. Mechanical; no design needed." />
    <item priority="P2" target_mode="brainstorm" finding_ref="F6" description="Subsume the strict-timestamp eligibility (pair_dt < target_dt) under the F1 redesign; if temporal proximity is kept as a tiebreaker, define the tie policy explicitly." />
    <item priority="P2" target_mode="brainstorm" finding_ref="F7" description="Optional BIDS-correctness: decide whether SBRef should be included in the covering fieldmap's IntendedFor. Not required; fold into the F1 brainstorm. Confirms the simulated-dataset generator's existing SBRef-omission choice is correct." />
    <item priority="P2" target_mode="implement" finding_ref="F8" description="Adopt a single, consistent policy for missing AcquisitionDateTime across load_series and stage4._acq_sort_key (typed contextual error naming the series, or degrade-with-flag). Mechanical once the policy is chosen." />
    <item priority="P2" target_mode="implement" finding_ref="F9" description="Guard the nested parsed['issues']['issues'] access in run_bids_validator so a validator schema drift yields ToolUnavailableError (dataset UNCHECKED) rather than an uncaught crash. Mechanical; tangential to pairing." />
  </action_items>
</cr_report>
