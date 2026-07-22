<brainstorm_report>
  <meta project="fmri-bids-recon" mode="brainstorm" timestamp="2026-07-17T12:30:03-04:00" />

  <context_files>
    <file path="fmri-bids-recon_cr_20260717_113514.md" relevance="Source CR; findings F1-F9 on the fieldmap pairing path. This brainstorm adjudicates the pipeline (brainstorm-first) findings." />
    <file path="fmri_bids_recon/stage3_map.py" relevance="Current pair_fieldmaps + map_fieldmaps (nearest-preceding-strict); the association logic being redesigned." />
    <file path="fmri_bids_recon/stage5_render.py" relevance="Emits IntendedFor + B0FieldIdentifier + B0FieldSource; confirms both metadata forms are already written." />
    <file path="fmri_bids_recon/sidecar.py" relevance="Series model; loads matrix from NIfTI shape but NOT the affine/position, which the redesign requires." />
    <file path="fmri_bids_recon/__main__.py" relevance="Guard-log construction (line 199, hardcoded all-True) and target list (line 176, BOLD/DWI only)." />
</context_files>

  <topics>

    <topic id="T1" title="Fieldmap-to-target association basis">
      <summary>
        The CR (F1) found the pipeline associates fieldmaps to targets by acquisition order alone
        (nearest-preceding-strict), which the field uses only as a tiebreaker. The user reframed the
        question from "what order does ABCD use" to "how do we know which fieldmap belongs to which
      </summary>
      <research>
        partitions the session into exactly three geometric blocks, each containing one fieldmap
        pair and its target runs, with NO order information used:
          block 0 pos=(-108.0,-135.55,-73.57): func-fmap PA/AP (SN10,12) + enback-1,2 (SN15,19)
          block 1 pos=(-108.0,-136.35,-71.17): func-fmap PA/AP (SN22,24) + rest-1..4 (SN27,31,35,39)
          block 2 pos=(-120.0,-149.15,-69.17): dwi-fmap PA/AP (SN42-45) + dwi (SN47)
        Every member of a block shares the EXACT ImagePositionPatient; the three blocks differ. The
        scanner re-prescribed the stack between blocks (~0.8mm Y, ~2.4mm Z between the two func
        blocks). Protocol name CANNOT disambiguate (both func pairs are "ABCD_fMRI_DistortionMap
        PA/AP"); Siemens shim is ABSENT from these XA30 sidecars (no CSA group 0021 shim keyword);
        all EPI is PE=COLUMN. Geometry is the only reliable, order-independent discriminator present.

        Literature (from the source CR's research, lit_state=consensus): heudiconv
        populate_intended_for matches on ImagingVolume (position/orientation/voxel/matrix) or Shims as
        PRIMARY, temporal proximity as TIEBREAKER; BIDS 1.7 B0FieldIdentifier recommended derived from
        Protocol/Sequence Name; SDCFlows requires PE-axis identity (epi_pe[0]==pe_dir[0]).
      </research>
      <approaches>
        <approach id="A1" label="Geometry-primary + global-optimal time tiebreaker + halt-on-uncertainty" feasibility="high" risk="low">
          <description>
            (1) Partition all EPI series (fieldmaps + BOLD/DWI targets) into distortion groups by
            shared slice prescription: ImageOrientationPatient + ImagePositionPatient + voxel size +
            matrix + PE-axis, compared within a tolerance. (2) Within a group, assign targets to the
            fieldmap pair; when geometry does NOT separate two blocks (a subject not re-prescribed
            between blocks, yielding identical positions), disambiguate among the geometry-valid
            candidates by a GLOBAL optimal assignment minimizing total time-distance (scan-to-fieldmap),
            not greedy nearest-preceding. (3) HALT on any association uncertainty (a target with no
            geometry-compatible fieldmap, an invalid/non-opposite-PE pair, an unresolvable tie, or an
            orphaned fieldmap): fail-loud, write nothing for that subject.
          </description>
          <pros>
            Order-independent primary signal, verified on the target data. Resolves F1 (order
            dependence), F3 (a corrupt re-acquired fieldmap at a different prescription lands in a
            different group and cannot mis-pair; at the same prescription it produces an ambiguous
            group that halts), F4 (PE-axis is part of the gate), F5 (tolerance replaces exact float
            equality), F6 (closest-in-time replaces strict-preceding). Degrades gracefully: order is
            consulted only to break geometry ties among physically-valid candidates.
          </pros>
          <cons>
            Requires extending the Series model to carry the affine/position (currently only matrix is
            loaded). Depends on slice geometry surviving dcm2niix conversion into a readable form
            (verification gate, below). Global-optimal assignment adds modest complexity, though per-group
            cardinalities are tiny.
          </cons>
          <statistical_considerations>
            Geometry uniqueness is not guaranteed: it discriminates here because the subject was
            re-prescribed between blocks. The tiebreaker is the designed fallback for the
            no-re-prescription case. TOLERANCE SIZING (corrected during the pre-report audit): the
            tolerance should be SMALL, sized only to absorb dcm2niix floating-point jitter (order
            0.01-0.1mm), NOT voxel-scaled. Rationale: within a block a fieldmap and its targets
            share position EXACTLY (both func-block-0 members read -135.55), so a tiny tolerance
            never risks splitting a fieldmap from its own target; between blocks, any real
            prescription difference however small should be preserved so geometry discriminates,
            with the temporal tiebreaker engaging only when the prescription is truly identical
            (a subject who held still, zero separation). A voxel-scaled tolerance (e.g. half-voxel
            1.2mm) would over-merge blocks that geometry could have separated and lean on the
            tiebreaker unnecessarily. Note the observed func-block separation is 2.53mm Euclidean
            (dY=0.80mm, dZ=2.40mm), so half-voxel would NOT merge THIS subject's blocks; but the
            smallest single-axis separation (0.80mm in Y) shows voxel-scaled tolerances are far
            too coarse in general, since inter-block separation has no guaranteed lower bound.
          </statistical_considerations>
        </approach>
        <approach id="A2" label="Keep temporal-primary, add geometry as a gate only" feasibility="high" risk="med">
          <description>Retain nearest-preceding-strict; add a geometry+PE-axis compatibility guard rejecting an assignment whose fieldmap prescription does not match the target.</description>
          <pros>Smallest change; catches the mismatch cases.</pros>
          <cons>Does not fix the root ordering dependence; order remains the primary key. Rejected by user.</cons>
        </approach>
        <approach id="A3" label="Geometry-only, halt on any ambiguity (no temporal fallback)" feasibility="high" risk="med">
          <description>Partition by geometry; require exactly one fieldmap pair per group; halt if a group is geometrically ambiguous.</description>
          <pros>Fully order-free.</pros>
          <cons>Halts on the held-still subject (identical block positions) rather than resolving automatically. User chose to resolve such cases via the tiebreaker, so A3's no-fallback stance was not selected; however, the user's separate halt-on-uncertainty decision means a tie the tiebreaker cannot break DOES halt.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        User-locked, one decision at a time: (1) association basis = geometry-primary (matching each
        fieldmap to the scans that share its slice prescription); (2) tiebreaker = global optimal
        assignment minimizing total time-distance among geometry-compatible candidates; (3) geometry
        match = within a tolerance (not exact float equality); (4) behavior on any association
        uncertainty = HALT (strictest guarantee against silent mismatch). The user's rationale for the
        temporal tiebreaker: a fieldmap is by definition the close-in-time accounting of scanner field,
        so proximity is a physically-justified secondary signal; but it must be competition-aware so a
        fieldmap is not spent on a scan that already has a closer one.
      </decision>
    </topic>

    <topic id="T2" title="Meta-guard (CR F2): inoperative guard-execution certification">
      <summary>
        __main__.py:199 constructs the guard log as {name: True for name in ALL_GUARD_NAMES}
        unconditionally; no guard records its own execution; assert_guards_executed therefore cannot
        fail and certifies nothing. The docstring names the exact failure mode it does not prevent.
      </summary>
      <research>Not applicable (internal defensive-verification concern). Confirmed by grep: zero per-key guard_log assignments anywhere in fmri_bids_recon/; guard names appear only in ALL_GUARD_NAMES.</research>
      <approaches>
        <approach id="A1" label="Make it real" feasibility="high" risk="low">
          <description>Initialize the guard log to all-False; each guard flips its own entry True at the point it executes; assert_guards_executed verifies genuine execution records. The redesigned association adds new guards (geometry match, PE-axis, pair validity, no-ambiguity) that this then certifies.</description>
          <pros>Turns a decorative check into a real safety net; certifies the new association guards.</pros>
          <cons>Requires threading the guard log through the guard call sites.</cons>
        </approach>
        <approach id="A2" label="Remove it" feasibility="high" risk="low">
          <description>Delete the meta-guard rather than present false assurance.</description>
          <cons>Abandons the intended defense against a silently-skipped guard. Not chosen.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        Make the meta-guard real: per-guard execution instrumentation, log initialized False, each
        guard sets its own entry at execution. Motivated further by the new association guards, which
        deserve genuine certification.
      </decision>
    </topic>

    <topic id="T3" title="SBRef association and metadata format (CR F7)">
      <summary>
        SBRef currently excluded from fieldmap targets (__main__.py:176). The pipeline is
        downstream-agnostic and should emit BIDS metadata that satisfies any consumer.
      </summary>
      <research>
        CR research R2: BIDS is permissive on SBRef association ("MAY be linked"); no harm in including
        SBRefs even for tools that ignore them (SDCFlows). The user clarified they do NOT use fMRIPrep;
        downstream is mostly an in-house custom pipeline, and the reconstruction must be agnostic to the
        consumer. stage5_render already emits BOTH IntendedFor and B0FieldIdentifier/B0FieldSource,
        matching the BIDS recommendation to provide both for compatibility.
      </research>
      <approaches>
        <approach id="A1" label="Associate SBRef; emit both metadata forms" feasibility="high" risk="low">
          <description>Include SBRef (and DWI_SBREF) in its block's fieldmap association under the geometry grouping; continue emitting both IntendedFor and B0FieldIdentifier/B0FieldSource.</description>
          <pros>Complete for any downstream tool that corrects the reference; harmless for those that do not; maximally compatible. Nearly free under geometry grouping (SBRef shares its block's prescription).</pros>
          <cons>Implies the simulated clean dataset should also associate SBRef, for consistency (harmonization item).</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        Associate SBRef with its block's fieldmap; keep emitting both metadata forms. Grounds: the
        downstream-agnostic-completeness principle the user stated. The earlier premise (fMRIPrep
        corrects the reference regardless) was withdrawn when the user clarified fMRIPrep is not used.
      </decision>
    </topic>

    <topic id="T4" title="Residual CR minors under the redesign">
      <summary>How the remaining CR findings fare once T1-T3 are adopted.</summary>
      <research>Determined by the redesign, not external research.</research>
      <approaches>
        <approach id="A1" label="Resolve-by-redesign or route-mechanical" feasibility="high" risk="low">
          <description>
            F3 (corrupt-rerun mis-pair): resolved by T1 (halts as ambiguous/orphaned group).
            F4 (PE-axis unchecked): resolved by T1 (PE-axis in the gate; register a PE-axis guard in
              ALL_GUARD_NAMES).
            F5 (exact EES float equality): resolved by T1's tolerance philosophy applied to all
              geometry/parameter comparisons.
            F6 (strict pair_dt < target_dt): resolved by T1 (closest-in-time replaces strict-preceding).
            F8 (missing AcquisitionDateTime crashes load_series, inconsistent with stage4's tolerant
              handling): mechanical; adopt one consistent policy (typed contextual error naming the
              series, or degrade-with-flag). Lower criticality now that time is a tiebreaker, but a
              missing timestamp needed to break a tie must halt under the halt-on-uncertainty rule.
            F9 (run_bids_validator nested parsed['issues']['issues'] unguarded): mechanical; guard the
              nested access so a validator schema drift yields ToolUnavailableError, not a crash.
          </description>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        F3/F4/F5/F6 fold into the T1 redesign. F8 and F9 are independent mechanical fixes routed to
        implement.
      </decision>
    </topic>

    <topic id="T5" title="Pending verification gate (mandatory audit item)">
      <summary>
        The redesign assumes slice geometry survives dcm2niix conversion into a form the pipeline can
        read (NIfTI affine translation + ImageOrientationPatientDICOM). Verified present in the raw
        DICOMs; NOT verified to survive conversion, because brainstorm is read-only and confirming it
        requires running dcm2niix (a write operation).
      </summary>
      <research>Deferred: could not run dcm2niix under the brainstorm read-only constraint.</research>
      <approaches>
        <approach id="A1" label="Record as a plan-time verification gate" feasibility="high" risk="low">
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        Recorded as a required verification gate the plan must clear before build. The tolerance
        decision de-risks sub-millimeter conversion jitter, but geometry readability post-conversion
        must be confirmed on real converted output.
      </decision>
    </topic>

  </topics>

  <action_items>
    <item priority="P0" target_mode="implement" description="Redesign fieldmap-to-target association in stage3_map.py: partition EPI series into distortion groups by slice prescription (ImageOrientationPatient + ImagePositionPatient + voxel size + matrix + PE-axis) compared within a tolerance; assign targets to their group's fieldmap pair; disambiguate geometry-degenerate groups by a global-optimal assignment minimizing total scan-to-fieldmap time-distance; HALT on any association uncertainty (no compatible fieldmap, invalid pair, unresolvable tie, orphaned fieldmap)." />
    <item priority="P0" target_mode="implement" description="Extend the Series model (sidecar.py) to carry slice geometry: the NIfTI affine (position from its translation) and ImageOrientationPatientDICOM, plus a PE-axis accessor (first char of PhaseEncodingDirection). Currently only matrix (NIfTI shape) is loaded." />
    <item priority="P0" target_mode="implement" description="Add guards to ALL_GUARD_NAMES and instrument them: geometry-compatibility, PE-axis-identity, opposite-PE-pair-validity, association-no-ambiguity. Make the meta-guard real: initialize guard_log to all-False and have each guard set its own entry True at execution (replace __main__.py:199 hardcoded all-True)." />
    <item priority="P1" target_mode="implement" description="Include SBRef and DWI_SBREF in the fieldmap association target set (currently __main__.py:176 admits only BOLD and DWI). Continue emitting both IntendedFor and B0FieldIdentifier/B0FieldSource (already implemented in stage5_render)." />
    <item priority="P2" target_mode="implement" description="F8: adopt one consistent missing-AcquisitionDateTime policy across load_series and stage4._acq_sort_key (typed contextual error naming the series, or degrade-with-flag); a missing timestamp required to break a geometry tie must halt under the halt-on-uncertainty rule." />
    <item priority="P2" target_mode="implement" description="F9: guard the nested parsed['issues']['issues'] access in run_bids_validator so a validator schema change yields ToolUnavailableError (dataset UNCHECKED) rather than an uncaught crash." />
    <item priority="P2" target_mode="implement" description="HARMONIZATION (simulated dataset, separate plan): the clean dataset generator should associate SBRef in its fieldmap IntendedFor to remain a faithful representation of the redesigned pipeline's output. Under geometry-based association, existing fieldmap adversaries change meaning: fieldmap-geometry-mismatch now makes the target have no compatible fieldmap (expected pipeline behavior = HALT); PE-flip is a same-axis polarity error not caught by an axis-only gate (still a silent defect, correctly); voxel-drift drifts a whole session-block together so per-session association still succeeds (cross-session defect, uncaught by per-session association). Optionally add a fieldmap-position-mismatch adversary to directly exercise the new primary signal. These are recorded for the dataset plan; the pipeline redesign does not depend on them." />
  </action_items>

  <next_steps>
    /implement plan on this report to produce the pipeline redesign spec (fmri_bids_recon). Route and build
    separately from the simulated-dataset plan, per the user's instruction. Clear the T5 verification
    gate (dcm2niix geometry survival) before the build. The dataset-plan harmonization (SBRef
    association; adversary-meaning notes) is handled by editing the existing dataset implement:plan
    separately, as the user authorized.
  </next_steps>
</brainstorm_report>
