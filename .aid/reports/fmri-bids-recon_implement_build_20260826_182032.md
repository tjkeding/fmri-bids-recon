<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-08-26T18:20:32Z" />
  <spec_ref>bids-recon_implement_plan_20260826_152436.md</spec_ref>
  <changes_applied>

    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/sidecar.py" lines_changed="~30" />
      </files_modified>
      <notes>Added _normalize_vendor() helper and four new Series fields (vendor, echo_number, phase_encoding_axis, sequence_name), populated in load_series(). No deviation from spec.</notes>
    </change>

    <change id="C7" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/config.py" lines_changed="1" />
        <file path="fmri_bids_recon/labels.py" lines_changed="~4" />
      </files_modified>
      <notes>Added prefix field to TaskRegistryEntry; drift guard now uses the stored prefix when available. No deviation from spec.</notes>
    </change>

    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="~120" />
      </files_modified>
      <notes>Implemented canonical_modality() with vendor dispatch (Siemens/GE/Philips/fallback maps), context-gated GE EP\SE handling (SE_EPI token), layered Philips _is_epi(), and vendor-dispatched _is_spin_echo(). No deviation from spec.</notes>
    </change>

    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage2_classify.py" lines_changed="~60" />
      </files_modified>
      <notes>Classification rules 2-9 updated to use canonical_modality()/_is_epi() in place of raw ImageType/ScanningSequence checks; added Rule 3.5 for FMAP_GRE_PHASE; added SE_EPI context gates. No deviation from spec.</notes>
    </change>

    <change id="C4" status="done" user_decision="proceed" deviation_approved="true">
      <files_modified>
        <file path="fmri_bids_recon/stage3_map.py" lines_changed="~250" />
        <file path="fmri_bids_recon/pipeline.py" lines_changed="~15" />
        <file path="fmri_bids_recon/json_intermediate.py" lines_changed="2" />
        <file path="fmri_bids_recon/stage5_render.py" lines_changed="~15" />
        <file path="fmri_bids_recon/report.py" lines_changed="~15" />
      </files_modified>
      <notes>
        Core spec implemented as written: FieldmapPair replaced by FieldmapUnit (paired/single modes), pair_fieldmaps() rewritten as group_fieldmaps() with absent-PE detection (high-severity graded_warning, routed to unpaired_fmaps) and odd-count handling (high-severity graded_warning replacing the PhaseEncodingError raise, remainder routed to unpaired_fmaps), Mapping dataclass updated (units, unit_to_targets, unpaired_fmaps), _select_pair renamed to _select_unit, map_fieldmaps() adapted to FieldmapUnit.

        Deviation from spec (flagged mid-build, user approved before proceeding): the tech spec's C4 scope covered only stage3_map.py, but the FieldmapPair-to-FieldmapUnit rename has four downstream callers not named in any change in the plan: pipeline.py (import, group_fieldmaps() call, empty-Mapping construction), json_intermediate.py (dataclass round-trip registry), stage5_render.py (B0Field identifier/IntendedFor rendering, iterates pair.member_a/member_b), and report.py (fieldmap mapping table section). Left unmodified, the codebase would fail at import or at runtime. All four were updated as a mechanical, no-logic-change consequence of the C4 rename, per explicit user approval. stage5_render.py's dir-label display now converts stored voxel-space PE labels back to anatomical labels via PE_DIRECTION_TO_LABEL for the B0Field identifier pattern (unchanged output format); report.py's fieldmap table does the same for its "dir-PA/dir-AP" display and additionally now lists unpaired fieldmaps routed to sourcedata.
      </notes>
    </change>

    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage3_map.py" lines_changed="~330" />
      </files_modified>
      <notes>
        Added GREFieldmapSet dataclass, group_gre_fieldmaps() (geometry-primary magnitude rescue, explicit BIDS Case 1/2/3/indeterminate determination), _relaxed_geometry_check() (position/orientation only, for GRE-to-target association), and map_gre_fieldmaps().

        Two implementation choices made where the spec's prose left the exact mechanism underspecified, both consistent with the spec's explicit statements: (1) the spec's magnitude-rescue geometry check explicitly enumerates "position, orientation, voxel size, matrix" as the criteria, omitting pe_axis; since GRE magnitude reconstructions frequently lack a populated PhaseEncodingDirection despite sharing the other four criteria with their phase companion, _geometry_check() was given an additive check_pe_axis: bool = True parameter (default preserves all four existing call sites' behavior unchanged) rather than duplicating ~50 lines of geometry-comparison logic in a new function. (2) Phase series sharing geometry (BIDS Case 2's two phase outputs from one acquisition) are clustered via the same transitive-closure union-find algorithm used elsewhere in this file, with per-phase-series rescued magnitudes merged and deduplicated into the resulting GREFieldmapSet.
      </notes>
    </change>

    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage4_assemble.py" lines_changed="~90" />
        <file path="fmri_bids_recon/pipeline.py" lines_changed="~10" />
        <file path="fmri_bids_recon/json_intermediate.py" lines_changed="2" />
      </files_modified>
      <notes>
        assemble() signature extended with gre_sets and unpaired_fmaps parameters. SE-EPI fieldmap assembly rewritten against FieldmapUnit (fmap_unit_lookup keyed by member index); a fieldmap series with no unit match is now silently skipped in the per-series loop and instead picked up by a dedicated unpaired_fmaps-to-sourcedata loop, replacing the prior GuardError raise. Added a GRE fieldmap assembly block covering BIDS Cases 1 (phasediff + magnitude1/2), 2 (phase1/phase2 + magnitude1/2), and 3 (fieldmap + magnitude), with indeterminate sets (bids_case=0) routed to sourcedata/unclassified.

        Per the tech spec's own note ("pipeline.py orchestrator... wiring change... included in C6's scope"), pipeline.py was updated to call group_gre_fieldmaps()/map_gre_fieldmaps() after fieldmap mapping and before the unclassified-series list is computed (ordering matters: group_gre_fieldmaps mutates the roles dict, reclassifying rescued magnitude series from UNCLASSIFIED to FMAP_GRE_MAG, and the unclassified list must reflect that reclassification). gre_sets is persisted through the phase1/phase3 JSON intermediate file; this required registering GREFieldmapSet in json_intermediate.py's dataclass round-trip registry (the same category of mechanical, no-logic-change addition as C4's deviation, applied to a class this change newly wires into the intermediate file).
      </notes>
    </change>

  </changes_applied>
  <summary>
    <total_changes>7</total_changes>
    <completed>7</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <verification_performed>
    AST syntax validation and package-level import checks on all ten modified files (sidecar.py, config.py, labels.py, stage2_classify.py, stage3_map.py, stage4_assemble.py, pipeline.py, json_intermediate.py, stage5_render.py, report.py); confirmed via grep that no stale references to the pre-refactor API (FieldmapPair, pair_fieldmaps, _select_pair, .pairs, pair_to_targets, member_a/member_b) remain anywhere in the package. No pytest execution performed, per this skill's no-testing constraint.
  </verification_performed>
  <next_steps>Recommended: run /test to validate all changes, including the new vendor-dispatch classification paths, FieldmapUnit pairing/absent-PE/odd-count routing, and GRE Case 1/2/3 assembly.</next_steps>
</implement_report>
