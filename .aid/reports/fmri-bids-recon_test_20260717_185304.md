<test_report>
  <meta project="fmri-bids-recon" mode="test" timestamp="2026-07-17T18:53:04Z" />
  <input_reports>
    <report path="fmri-bids-recon_implement_build_20260717_130057.md" mode="implement" />
  </input_reports>

  <pre_design_run>
    <total>370</total>
    <passed>296</passed>
    <failed>55</failed>
    <errors>17</errors>
    <skipped>2</skipped>
    <coverage_pct>null</coverage_pct>
    <failures>
      <failure test="test_anatomical_lands_under_anat_with_the_t1w_suffix" file="tests/test_assemble.py" />
      <failure test="test_bold_runs_carry_task_and_run_entities" file="tests/test_assemble.py" />
      <failure test="test_fieldmap_members_carry_the_direction_from_the_pair" file="tests/test_assemble.py" />
      <failure test="test_the_session_entity_is_always_emitted" file="tests/test_assemble.py" />
      <failure test="test_diffusion_carries_its_gradient_tables" file="tests/test_assemble.py" />
      <failure test="test_a_diffusion_sbref_lands_under_dwi_with_the_sbref_suffix" file="tests/test_assemble.py" />
      <failure test="test_sidecars_written_into_the_bids_tree_are_scrubbed" file="tests/test_assemble.py" />
      <failure test="test_scrubbed_sidecars_retain_the_acquisition_physics" file="tests/test_assemble.py" />
      <failure test="test_the_unscrubbed_sidecar_is_preserved_under_sourcedata" file="tests/test_assemble.py" />
      <failure test="test_volume_count_exclusions_are_preserved_under_sourcedata" file="tests/test_assemble.py" />
      <failure test="test_unclassified_series_are_preserved_under_sourcedata" file="tests/test_assemble.py" />
      <failure test="test_the_nd_anatomical_twin_is_preserved_under_sourcedata" file="tests/test_assemble.py" />
      <failure test="test_participants_tsv_records_the_subject" file="tests/test_assemble.py" />
      <failure test="test_sessions_tsv_records_the_wave_and_a_decimal_age" file="tests/test_assemble.py" />
      <failure test="test_age_falls_back_to_patient_age_when_no_birth_date_is_present" file="tests/test_assemble.py" />
      <failure test="test_scans_tsv_lists_every_emitted_file_with_its_acquisition_time" file="tests/test_assemble.py" />
      <failure test="test_dataset_description_is_created_once_and_never_overwritten" file="tests/test_assemble.py" />
      <failure test="test_dataset_description_is_written_when_absent" file="tests/test_assemble.py" />
      <failure test="test_inconsistent_patient_ids_raise_a_warning_that_carries_no_identifier" file="tests/test_assemble.py" />
      <failure test="test_a_consistent_patient_id_raises_no_warning" file="tests/test_assemble.py" />
      <failure test="test_the_demographics_summary_carries_no_direct_identifier" file="tests/test_assemble.py" />
      <failure test="test_an_sbref_inherits_the_run_index_of_its_bold" file="tests/test_assemble.py" />
      <failure test="test_two_anatomicals_at_different_geometries_do_not_overwrite_each_other" file="tests/test_assemble.py" />
      <failure test="test_two_diffusion_series_do_not_overwrite_each_other" file="tests/test_assemble.py" />
      <failure test="test_an_unpaired_fieldmap_is_not_silently_destroyed" file="tests/test_assemble.py" />
      <failure test="test_assembly_leaves_no_non_bids_artefacts_in_the_tree" file="tests/test_assemble.py" />
      <failure test="test_a_diffusion_series_with_an_unresolvable_pe_direction_is_refused" file="tests/test_assemble.py" />
      <failure test="test_a_guard_violation_exits_one" file="tests/test_cli_integration.py" />
      <failure test="test_every_guard_on_the_roster_has_a_test_that_fires_it" file="tests/test_guard_coverage.py" />
      <failure test="test_the_engine_module_named_for_a_guard_still_raises_its_error[fieldmap_geometry_ees_match]" file="tests/test_guard_coverage.py" />
      <failure test="test_consecutive_fieldmaps_are_paired_and_labelled_from_the_physics" file="tests/test_map.py" />
      <failure test="test_pairs_are_ordered_by_acquisition_time_not_input_order" file="tests/test_map.py" />
      <failure test="test_run_indices_restart_at_one_for_each_fieldmap_modality" file="tests/test_map.py" />
      <failure test="test_a_pair_with_the_same_phase_encoding_direction_raises" file="tests/test_map.py" />
      <failure test="test_a_pair_with_orthogonal_phase_encoding_directions_raises" file="tests/test_map.py" />
      <failure test="test_a_fieldmap_with_no_phase_encoding_direction_raises" file="tests/test_map.py" />
      <failure test="test_a_description_direction_token_contradicting_the_physics_raises" file="tests/test_map.py" />
      <failure test="test_a_description_direction_token_agreeing_with_the_physics_is_accepted" file="tests/test_map.py" />
      <failure test="test_descriptions_without_a_direction_token_are_left_to_the_physics" file="tests/test_map.py" />
      <failure test="test_a_target_is_assigned_to_the_pair_that_precedes_it" file="tests/test_map.py" />
      <failure test="test_a_target_is_assigned_to_the_nearest_preceding_pair_not_the_first" file="tests/test_map.py" />
      <failure test="test_several_targets_can_share_one_preceding_pair" file="tests/test_map.py" />
      <failure test="test_a_target_preceding_every_pair_raises" file="tests/test_map.py" />
      <failure test="test_the_preceding_relation_is_strict" file="tests/test_map.py" />
      <failure test="test_a_func_pair_cannot_cover_a_diffusion_target" file="tests/test_map.py" />
      <failure test="test_a_diffusion_pair_covers_a_diffusion_target" file="tests/test_map.py" />
      <failure test="test_a_pair_covering_nothing_raises" file="tests/test_map.py" />
      <failure test="test_an_sbref_does_not_count_as_coverage" file="tests/test_map.py" />
      <failure test="test_an_echo_spacing_mismatch_between_pair_and_target_raises" file="tests/test_map.py" />
      <failure test="test_a_matrix_mismatch_between_pair_and_target_raises" file="tests/test_map.py" />
      <failure test="test_the_geometry_guard_checks_both_pair_members" file="tests/test_map.py" />
      <failure test="test_the_identifier_encodes_the_modality_and_the_run" file="tests/test_render.py" />
      <failure test="test_the_identifier_separates_func_from_dwi" file="tests/test_render.py" />
      <failure test="test_the_identifier_is_zero_padded_and_distinct_per_run" file="tests/test_render.py" />
      <failure test="test_the_guard_roster_is_exactly_the_twelve_named_guards" file="tests/test_validate.py" />
      <failure test="test_each_fieldmap_member_declares_the_runs_it_is_intended_for" file="tests/test_render.py" type="ERROR" />
      <failure test="test_the_two_renderings_of_the_same_association_agree" file="tests/test_render.py" type="ERROR" />
      <failure test="test_rendering_preserves_the_physics_already_in_the_sidecar" file="tests/test_render.py" type="ERROR" />
      <failure test="test_rendering_does_not_reintroduce_identifiers_into_the_tree" file="tests/test_render.py" type="ERROR" />
      <failure test="test_the_report_lands_in_the_derivatives_tree" file="tests/test_report.py" type="ERROR" />
      <failure test="test_every_section_of_the_report_is_present" file="tests/test_report.py" type="ERROR" />
      <failure test="test_the_provenance_section_names_the_binary_that_did_the_conversion" file="tests/test_report.py" type="ERROR" />
      <failure test="test_an_excluded_run_is_reported_with_both_volume_counts" file="tests/test_report.py" type="ERROR" />
      <failure test="test_an_unclassified_series_is_reported_as_not_having_entered_the_tree" file="tests/test_report.py" type="ERROR" />
      <failure test="test_the_fieldmap_mapping_section_records_which_pair_corrects_which_run" file="tests/test_report.py" type="ERROR" />
      <failure test="test_auto_registered_tasks_are_reported_with_the_label_they_received" file="tests/test_report.py" type="ERROR" />
      <failure test="test_a_clean_tree_passes_the_scrub_audit" file="tests/test_report.py" type="ERROR" />
      <failure test="test_a_surviving_identifier_in_a_bids_sidecar_stops_the_pipeline" file="tests/test_report.py" type="ERROR" />
      <failure test="test_the_audit_names_the_surviving_key_but_never_its_value" file="tests/test_report.py" type="ERROR" />
      <failure test="test_the_failing_report_is_on_disk_before_the_guard_raises" file="tests/test_report.py" type="ERROR" />
      <failure test="test_the_unscrubbed_provenance_copies_do_not_trip_the_audit" file="tests/test_report.py" type="ERROR" />
      <failure test="test_the_patient_id_cross_check_reports_the_warning_and_not_the_identifier" file="tests/test_report.py" type="ERROR" />
    </failures>
  </pre_design_run>

  <failing_test_dispositions>

    <disposition test="26 tests in tests/test_assemble.py (all listed pre_design_run failures for this file except test_an_unpaired_fieldmap_is_not_silently_destroyed); all 13 tests in tests/test_report.py; all 7 tests in tests/test_render.py (3 FAILED + 4 ERROR)" file="tests/conftest.py" classification="obsolete-test">
      <intended_contract>The shared `build_session`/`materialise`-style fixtures in conftest.py construct synthetic DICOM-derived series records for assemble/render/report-stage tests. Their contract is to hand each test a session whose series carry realistic geometry (image_position, affine, voxel_sizes, pe_axis) and to thread a `guard_log` collector through the mapping call chain, since the redesigned `pair_fieldmaps`/association path now requires both.</intended_contract>
      <current_test_claim>Verbatim, all 46 affected tests asserted on downstream BIDS-tree, sidecar, TSV, PHI-scrubbing, IntendedFor, or report-structure content; none asserted anything about fixture call signatures directly. All 46 failed/errored with `TypeError` at fixture construction or at the `order_series`/`pair_fieldmaps` call site inside conftest.py, before any test-body assertion executed.</current_test_claim>
      <evidence>conftest.py's `build_session` left fmap/dwi geometry fields at their pre-redesign None defaults and called `pair_fieldmaps`/`order_series` with the pre-redesign 2-argument signature; the redesigned stage3_map.py functions require populated geometry fields and a `guard_log` argument per the locked plan. The TypeError originates in conftest.py, not in the 46 tests' own bodies.</evidence>
      <action>Re-expressed conftest.py only: populated realistic geometry fields (image_position, affine, voxel_sizes, pe_axis) on `fmap_func`/`fmap_dwi`/`dwi`/anatomical fixture builders, and updated the `order_series`/`pair_fieldmaps` call site to thread `guard_log`. Zero edits were made to the 46 dependent tests' own bodies or assertions; all 46 passed once the fixture defect was corrected, confirming their original assertions were already contract-aligned and merely blocked by the fixture regression. No postcondition was touched for these 46 tests.</action>
    </disposition>

    <disposition test="test_an_unpaired_fieldmap_is_not_silently_destroyed" file="tests/test_assemble.py" classification="obsolete-test">
      <intended_contract>Prior contract: an unpaired (odd-count) fieldmap series must not be silently dropped from the pipeline's accounting. Redesigned contract per the locked plan (`fmri-bids-recon_implement_plan_20260717_124134.md`, geometry-association section): odd-count or otherwise unbalanceable geometry groups raise a blocking `GuardError` rather than being silently degraded, warned, or routed around.</intended_contract>
      <current_test_claim>The pre-redesign assertion checked that the unpaired fieldmap surfaced via a non-blocking pathway (consistent with the old nearest-preceding policy's permissive handling of coverage gaps). Under the redesigned code this now raises `PhaseEncodingError` from `stage3_map.py:277` ("Geometry group contains an odd number (3) of 'func' fieldmap series; cannot form balanced opposite-PE pairs.") before reaching the old assertion point.</current_test_claim>
      <evidence>Locked plan: unbalanceable geometry groups are a deliberate, explicit halt case, not a silent-degradation case. Observed behavior in both the design-phase local sanity check and the final post-design dispatch confirms `PhaseEncodingError` is raised deterministically for the 3-member odd-count group fixture.</evidence>
      <action>Re-expressed to assert that `PhaseEncodingError` (a `GuardError` subclass) is raised for the odd-count group, replacing the old silent-non-destruction assertion. This is a postcondition STRENGTHENING, not a weakening: the new assertion requires the pipeline to halt loudly on this condition, where the old assertion only required it not be silently dropped. Import of `GuardError` was added to the test file's import block to support the `pytest.raises` context.</action>
    </disposition>

    <disposition test="test_a_guard_violation_exits_one" file="tests/test_cli_integration.py" classification="obsolete-test">
      <intended_contract>The CLI must exit with status 1 whenever any guard raises during a pipeline run, regardless of which specific guard fires.</intended_contract>
      <current_test_claim>The original scenario was engineered to deterministically trip the old strict nearest-preceding-pair temporal guard (`pair_dt &lt; target_dt`), which the locked plan deliberately removed (plan lines 231-235). Under the redesigned code the original fixture scenario no longer trips any guard and the pipeline completes normally, so the test failed on an assertion that exit code equaled 1.</current_test_claim>
      <evidence>Locked plan explicitly removes the strict-preceding eligibility check (CR finding F6) as part of the geometry-based redesign. The scenario's guard trigger was coupled to that removed check, not to the CLI exit-code contract itself.</evidence>
      <action>Re-expressed the fixture scenario to trip a currently-active guard from the 14-name `ALL_GUARD_NAMES` roster (a geometry-incompatible fieldmap/target pairing, raising `FieldmapCoverageError`) while preserving the original postcondition unchanged: CLI exit code must equal 1 on any guard violation. No weakening of the exit-code assertion occurred.</action>
    </disposition>

    <disposition test="test_every_guard_on_the_roster_has_a_test_that_fires_it; test_the_engine_module_named_for_a_guard_still_raises_its_error[fieldmap_geometry_ees_match]" file="tests/test_guard_coverage.py" classification="obsolete-test">
      <intended_contract>Every guard defined in `fmri_bids_recon/stage6_validate.py`'s `ALL_GUARD_NAMES` roster must have a corresponding test that fires it; the roster itself must match the authoritative guard set in the codebase.</intended_contract>
      <current_test_claim>The roster table hard-coded a 12-name legacy list that included `fieldmap_geometry_ees_match` and `target_pair_coverage`, both of which the locked plan (C3, lines 274-284) deliberately removed. `ALL_GUARD_NAMES` in `stage6_validate.py` was confirmed via direct grep to now contain 14 names, replacing the two removed guards with `fieldmap_target_geometry_match` and `association_unambiguous`.</current_test_claim>
      <evidence>Direct grep confirmation of `ALL_GUARD_NAMES` in `fmri_bids_recon/stage6_validate.py`: 14-entry ordered list (`dcm2niix_version_floor`, `anat_suffix_physics`, `opposite_pe_within_pair`, `dir_label_pe_agreement`, `fieldmap_pairing_unambiguous`, `fieldmap_target_geometry_match`, `pe_axis_target_match`, `association_unambiguous`, `no_orphan_pairs`, `label_injectivity`, `non_empty_labels`, `no_label_drift`, `no_rename_collision`, `exact_volume_counts`).</evidence>
      <action>Updated the test file's guard-to-error import list and roster table to the confirmed 14-name/14-Guard-tuple set, removing the parametrized case for the deleted `fieldmap_geometry_ees_match` name and adding cases for `fieldmap_target_geometry_match` and `association_unambiguous`. The coverage postcondition (every roster guard has a firing test) is preserved at full strength against the new, correct roster.</action>
    </disposition>

    <disposition test="test_the_guard_roster_is_exactly_the_twelve_named_guards" file="tests/test_validate.py" classification="obsolete-test">
      <intended_contract>`ALL_GUARD_NAMES` is pinned to an exact, explicit set so that any future addition or removal of a guard is caught by this test.</intended_contract>
      <current_test_claim>Asserted the roster equals a specific 12-name set, which no longer matches the redesigned 14-name roster.</current_test_claim>
      <evidence>Same `ALL_GUARD_NAMES` grep confirmation as above.</evidence>
      <action>Renamed to `test_the_guard_roster_is_exactly_the_fourteen_named_guards` and updated the pinned set to the confirmed 14 names. The pinning postcondition itself (exact-set equality, not subset/superset) is preserved unweakened.</action>
    </disposition>

    <disposition test="test_consecutive_fieldmaps_are_paired_and_labelled_from_the_physics; test_pairs_are_ordered_by_acquisition_time_not_input_order; test_run_indices_restart_at_one_for_each_fieldmap_modality; test_a_pair_with_the_same_phase_encoding_direction_raises; test_a_pair_with_orthogonal_phase_encoding_directions_raises; test_a_fieldmap_with_no_phase_encoding_direction_raises; test_a_description_direction_token_contradicting_the_physics_raises; test_a_description_direction_token_agreeing_with_the_physics_is_accepted; test_descriptions_without_a_direction_token_are_left_to_the_physics" file="tests/test_map.py" classification="obsolete-test">
      <intended_contract>Fieldmap pairs are formed by physics (opposite phase-encoding direction), ordered by acquisition time within a pair, given per-modality run indices starting at 1, and validated against optional description direction tokens. This contract is UNCHANGED by the geometry-based association redesign, which governs target-to-pair association, not intra-pair physics validation.</intended_contract>
      <current_test_claim>Same physics/ordering/labelling/direction-token assertions as before; all failed with `TypeError` because `pair_fieldmaps` now requires a `guard_log` argument the test call sites did not supply.</current_test_claim>
      <evidence>The redesign's diff scope (per the locked plan) is limited to target-to-pair association logic; `pair_fieldmaps`'s opposite-PE and direction-token validation logic is untouched, confirmed by these 9 tests passing unmodified in content once the call site is corrected.</evidence>
      <action>Updated call sites (within the full-file rewrite of test_map.py) to pass `guard_log`. No assertion content was changed for any of these 9 tests.</action>
    </disposition>

    <disposition test="test_a_target_is_assigned_to_the_pair_that_precedes_it; test_a_target_is_assigned_to_the_nearest_preceding_pair_not_the_first; test_several_targets_can_share_one_preceding_pair; test_a_target_preceding_every_pair_raises; test_the_preceding_relation_is_strict" file="tests/test_map.py" classification="obsolete-test">
      <intended_contract>Prior contract: a target is associated with the nearest STRICTLY PRECEDING pair in acquisition time (`pair_dt &lt; target_dt`); a target preceding every pair is an error. Redesigned contract per the locked plan: targets are associated with the geometry-compatible pair nearest in time (no directional "preceding" requirement); a target with no geometry-compatible pair, or a tie among equally-near compatible pairs, raises a blocking `GuardError`.</intended_contract>
      <current_test_claim>Original assertions were written directly against the strict-preceding-in-time policy (`pair_dt &lt; target_dt`), which the locked plan explicitly and deliberately removes (plan lines 231-235, CR finding F6 resolution).</evidence>
      <evidence>Locked plan section on geometry-based fieldmap association explicitly replaces the nearest-preceding-strict temporal policy with geometry-group membership plus nearest-in-time-among-compatible-candidates; ties and no-compatible-pair cases are explicit, deliberate `GuardError` halts (a strengthening relative to the old silent-first-match behavior implied by "preceding").</evidence>
      <action>Re-expressed all 5 tests against the geometry-compatible-nearest-in-time policy: association still requires temporal proximity, but eligibility is now geometry-compatibility rather than strict precedence; the tie and no-compatible-pair cases now assert `GuardError` is raised (a strengthening from the old test's implicit permissiveness). No assertion was weakened; the halt-on-ambiguity behavior is strictly more restrictive than the prior "share one preceding pair" degenerate-success case it replaces.</action>
    </disposition>

    <disposition test="test_a_func_pair_cannot_cover_a_diffusion_target; test_a_diffusion_pair_covers_a_diffusion_target; test_a_pair_covering_nothing_raises; test_an_sbref_does_not_count_as_coverage" file="tests/test_map.py" classification="obsolete-test">
      <intended_contract>Modality-scoped coverage: a func fieldmap pair may only cover func targets, a diffusion pair only diffusion targets; a pair covering no eligible target is an orphan and raises; an SBRef series must never itself satisfy orphan/coverage accounting (the "passenger, not justifier" contract).</intended_contract>
      <current_test_claim>Same modality-scoping and orphan-detection assertions as before; failed with `TypeError` from the same `guard_log`/call-signature cascade as the physics-pairing cluster above, not from any change to the coverage contract itself.</current_test_claim>
      <evidence>The geometry-based redesign does not alter modality-scoping of coverage or the SBRef-exclusion rule; both remain intact requirements per the locked plan's fieldmap-association section.</evidence>
      <action>Updated call sites only (within the full-file rewrite of test_map.py). No assertion content was changed for any of these 4 tests; `test_an_sbref_does_not_count_as_coverage`'s postcondition (SBRef series must not count toward orphan/coverage resolution) was left fully intact, distinct from the new passenger-metadata test described below.</action>
    </disposition>

    <disposition test="test_an_echo_spacing_mismatch_between_pair_and_target_raises; test_a_matrix_mismatch_between_pair_and_target_raises; test_the_geometry_guard_checks_both_pair_members" file="tests/test_map.py" classification="obsolete-test">
      <intended_contract>Prior contract: a pair/target combination with mismatched EffectiveEchoSpacing (EES) or acquisition matrix is rejected via an EXACT-equality guard (CR finding F5's `fieldmap_geometry_ees_match`). Redesigned contract per the locked plan (C3, lines 274-284): the exact-EES/matrix guard is deliberately removed and replaced by the TOLERANCE-based `fieldmap_target_geometry_match` guard, which compares image_position/affine/voxel_sizes/pe_axis within a defined tolerance.</intended_contract>
      <current_test_claim>Original assertions checked for rejection on exact EES/matrix inequality via the now-removed guard path; that code path no longer exists.</current_test_claim>
      <evidence>Locked plan C3 explicitly and deliberately removes the exact-EES geometry guard as part of the redesign; `ALL_GUARD_NAMES` grep confirms `fieldmap_geometry_ees_match` is absent from the current 14-name roster and `fieldmap_target_geometry_match` is present in its place.</evidence>
      <action>Re-expressed all 3 tests against the tolerance-based `fieldmap_target_geometry_match` guard: fixtures now construct geometry that differs beyond the defined tolerance (rather than differing in EES/matrix alone), and the assertion still requires a `GuardError` to be raised on mismatch. The "mismatch is blocking" postcondition is preserved; only the specific geometric criterion being violated changed, per the locked, user-approved redesign.</action>
    </disposition>

  </failing_test_dispositions>

  <design_phase>
    <tests_created>1</tests_created>
    <tests_modified>26</tests_modified>
    <tests_restored_via_fixture_fix_only>46</tests_restored_via_fixture_fix_only>
    <files_edited>
      <file path="tests/conftest.py" reason="populated real geometry fields on fmap_func/fmap_dwi/dwi/anatomical fixture builders; threaded guard_log through the order_series/pair_fieldmaps call site" />
      <file path="tests/test_assemble.py" reason="added GuardError import; re-expressed test_an_unpaired_fieldmap_is_not_silently_destroyed against the odd-count halt contract" />
      <file path="tests/test_report.py" reason="call-site fix mirroring the conftest.py signature change; no assertion changes" />
      <file path="tests/test_render.py" reason="call-site fixes mirroring the conftest.py signature change across three fmap-pair helper functions; no assertion changes" />
      <file path="tests/test_map.py" reason="full-file rewrite (Write, not Edit): re-expressed 21 pre-existing failing tests across four root-cause clusters (call-signature only, preceding-to-geometry policy change, coverage call-signature only, exact-to-tolerance geometry guard change); added 1 new test, test_an_sbref_geometry_compatible_with_a_pair_receives_its_b0fieldsource, to pin the SBRef passenger contract" />
      <file path="tests/test_guard_coverage.py" reason="updated guard-to-error import list and roster table from 12 to 14 guards, removing fieldmap_geometry_ees_match and target_pair_coverage, adding fieldmap_target_geometry_match and association_unambiguous" />
      <file path="tests/test_validate.py" reason="renamed and updated the roster-pinning test from twelve to fourteen named guards" />
      <file path="tests/test_cli_integration.py" reason="re-expressed test_a_guard_violation_exits_one to trip an active guard (FieldmapCoverageError via geometry-incompatible pairing) instead of the removed strict-preceding guard" />
    </files_edited>
    <files_deleted>
      <file path="tests/bids_recon_patched/" reason="stale, superseded parallel package confirmed via grep to have zero active imports from any test or codebase file; removed with explicit user approval (rm -rf) as housekeeping unrelated to any specific failing test" />
    </files_deleted>
    <production_files_edited_under_session_bound_grant>
      <file path="fmri_bids_recon/stage3_map.py" reason="removed a dead ped_a/ped_b None-check made unreachable by the redesign's mandatory-geometry precondition; narrow, per-file, session-bound Edit grant obtained from the user before editing (Test Mode's default write scope is tests/ only)" />
      <file path="fmri_bids_recon/errors.py" reason="removed the now-unused FieldmapGeometryError class (dead code following removal of the exact-EES geometry guard per locked plan C3) and updated the module docstring's exception-hierarchy listing; narrow, per-file, session-bound Edit grant obtained from the user before editing" />
    </production_files_edited_under_session_bound_grant>
    <design_rationale>
      The design phase resolved 71 of 72 pre-design failures as obsolete-test dispositions and 1 as a product-bug. Of the 71 obsolete-test dispositions, 46 (test_assemble.py's 26 non-redesign-specific tests, test_report.py's 13, test_render.py's 7) required zero change to their own bodies once the shared conftest.py fixture defect (missing geometry population, missing guard_log threading) was corrected; their original assertions were already contract-aligned. The remaining 26 required direct re-expression: 9 test_map.py pairing/physics tests and 4 test_map.py coverage tests needed only a call-signature fix with no assertion change; 5 test_map.py "preceding" tests were re-expressed against the locked plan's geometry-based nearest-in-time association policy (a strengthening, since ambiguous/incompatible cases now halt via GuardError rather than degrading silently); 3 test_map.py exact-geometry-guard tests were re-expressed against the locked plan's tolerance-based fieldmap_target_geometry_match guard (replacing the deliberately-removed exact-EES guard, CR F5); test_assemble.py's odd-count-fieldmap test was re-expressed as a strengthened halt-on-imbalance assertion; test_guard_coverage.py and test_validate.py were updated from the stale 12-guard roster to the confirmed 14-guard roster; test_cli_integration.py's engineered scenario was re-pointed at a currently-active guard. No assertion was removed, weakened, reduced in specificity, wrapped in a suppressing try/except, or skipped/xfailed without citable reason at any point in this phase. One new test was added to pin the SBRef "passenger, not justifier" contract; its initial run surfaced the one remaining product-bug, routed below via action_items rather than fixed in Test Mode.
    </design_rationale>
  </design_phase>

  <post_design_run>
    <total>377</total>
    <passed>374</passed>
    <failed>1</failed>
    <errors>0</errors>
    <skipped>2</skipped>
    <coverage_pct>null</coverage_pct>
    <failures>
      <failure test="test_an_sbref_geometry_compatible_with_a_pair_receives_its_b0fieldsource" file="tests/test_map.py" line="470" type="AssertionError" likely_cause="fmri_bids_recon/stage3_map.py's _ROLE_TO_MODALITY gate (or equivalent role-dispatch logic) excludes SBRef/DWI_SBREF series when populating B0FieldSource metadata during fieldmap-to-target rendering. The test asserts B0FieldSource == ['pepolarfunc01'] for an SBRef series that is geometry-compatible with a func fieldmap pair; the pipeline currently returns None for that field on the SBRef series, meaning SBRef series receive no B0FieldSource metadata at all under the redesigned association path, even when geometry-eligible. This is a product-bug disposition: the test correctly encodes the locked plan's SBRef 'passenger, not justifier' contract (SBRef series MUST receive B0FieldSource metadata as a passenger, but MUST NOT themselves count toward orphan/coverage resolution as a justifier); test_an_sbref_does_not_count_as_coverage (the justifier half of the same contract) passes, confirming only the passenger half is unimplemented." />
    </failures>
  </post_design_run>

  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>1</bugs_routed_to_implement>
    <recommendation>Route the single remaining failure to /implement as a product-bug fix (the SBRef passenger-metadata gap); do not re-loop design/run_suite within this invocation per the skill's Single-Pass Discipline. Once the fix lands, a follow-up /test run_suite should confirm 375/375 non-skipped tests pass with the SBRef passenger contract intact on both halves (passenger and justifier).</recommendation>
  </summary>

  <action_items>
    <item priority="P0" target_mode="implement" description="Fix the SBRef/DWI_SBREF B0FieldSource passenger gap in fmri_bids_recon/stage3_map.py: when an SBRef series is geometry-compatible with a fieldmap pair, it must receive B0FieldSource metadata identifying that pair, exactly as a corresponding BOLD/DWI series would. This fix MUST NOT alter SBRef's exclusion from orphan/coverage justification: test_an_sbref_does_not_count_as_coverage's postcondition (an SBRef-only-eligible pair must still raise FieldmapCoverageError as an orphan) must remain intact and passing after the fix. Evidence: tests/test_map.py:470 (test_an_sbref_geometry_compatible_with_a_pair_receives_its_b0fieldsource), post-design run_suite failure, receipt-verified." />
    <item priority="P2" target_mode="implement" description="Enhancement, not a routed test failure: restore per-criterion geometry-mismatch diagnostics on FieldmapCoverageError (e.g., which of image_position/affine/voxel_sizes/pe_axis failed tolerance, and against which candidate pair) so that operators debugging a geometry-association halt see an actionable reason rather than a bare orphan/no-match message. This was identified during design-phase reasoning about the tolerance-based fieldmap_target_geometry_match guard, not discovered via a failing test, and is intentionally excluded from the bugs_routed_to_implement count above. Two open design questions were identified and are unresolved: (1) when zero candidate pairs are geometry-eligible for a target, which single candidate's mismatch (if any) should be cited in the error, given there may be several equally-disqualified candidates; (2) whether fmri_bids_recon/stage3_map.py's _geometry_compatible check needs a separate diagnostic-reason-returning variant, or whether the existing boolean-returning check can be extended in place without disturbing its call sites. This item requires user adjudication of those two questions before an /implement plan can be written." />
  </action_items>

</test_report>
