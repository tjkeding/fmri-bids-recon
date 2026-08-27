<test_report>
  <meta project="bids-recon" mode="test" timestamp="2026-08-24T19:21:20Z" />
  <pre_design_run>
    <total>597</total>
    <passed>493</passed>
    <failed>15</failed>
    <errors>0</errors>
    <coverage_pct></coverage_pct>
    <failures>
      <failure test="test_a_multivolume_epi_navigator_halts_rather_than_dropping_silently" file="tests/test_classify.py" line="101">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE NavigatorDropError</message>
        <traceback>Series classified as BOLD via the new physics pass-through instead of halting; n_volumes=12 clears the n_volumes&gt;=10 BOLD-physics floor.</traceback>
      </failure>
      <failure test="test_a_single_volume_epi_preceding_a_matching_dwi_is_a_diffusion_sbref" file="tests/test_classify.py" line="294">
        <error_type>AssertionError</error_type>
        <message>assert Role.FMAP_FUNC == Role.DWI_SBREF</message>
        <traceback>Broadened Rule 5 now intercepts the single-volume spin-echo EPI fixture before Rule 9's look-ahead runs.</traceback>
      </failure>
      <failure test="test_a_single_volume_epi_with_no_following_dwi_is_unclassified" file="tests/test_classify.py" line="308">
        <error_type>AssertionError</error_type>
        <message>assert Role.FMAP_FUNC == Role.UNCLASSIFIED</message>
        <traceback>Same Rule 5/Rule 9 interaction as above.</traceback>
      </failure>
      <failure test="test_a_lone_anatomical_without_norm_is_flagged_for_review" file="tests/test_classify.py" line="389">
        <error_type>AssertionError</error_type>
        <message>assert 0 == 1 (flags)</message>
        <traceback>New has_norm Siemens-detection guard skips the NORM/ND pass entirely when no series in the dataset carries a NORM token.</traceback>
      </failure>
      <failure test="test_a_paired_group_with_no_norm_member_flags_every_member" file="tests/test_classify.py" line="407">
        <error_type>AssertionError</error_type>
        <message>assert 1 == 2 (flags)</message>
        <traceback>Same has_norm guard as above; only the new unconditional DUPLICATE_MODALITY flag fired.</traceback>
      </failure>
      <failure test="test_status_reflects_any_high_severity_warning_not_just_bids_errors" file="tests/test_cli_integration.py" line="305">
        <error_type>unknown</error_type>
        <message>injected raw dict flag not reflected in status</message>
        <traceback>pipeline.run() now determines status from get_warnings(), not from classify()'s returned flag list.</traceback>
      </failure>
      <failure test="test_the_conversion_argv_is_exactly_the_documented_command" file="tests/test_convert.py" line="72">
        <error_type>unknown</error_type>
        <message>argv mismatch</message>
        <traceback>dcm2niix invocation now includes -i y.</traceback>
      </failure>
      <failure test="test_a_target_with_no_geometry_compatible_pair_raises" file="tests/test_map.py" line="285">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE FieldmapCoverageError</message>
        <traceback>Per-target coverage gap softened to a graded_warning (FIELDMAP_COVERAGE_GAP, high) plus continue.</traceback>
      </failure>
      <failure test="test_a_func_pair_cannot_cover_a_diffusion_target" file="tests/test_map.py" line="308">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE FieldmapCoverageError</message>
        <traceback>Same coverage-gap softening as above.</traceback>
      </failure>
      <failure test="test_a_pair_covering_nothing_raises" file="tests/test_map.py" line="342">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE FieldmapCoverageError</message>
        <traceback>Orphan pair check softened to a graded_warning (ORPHAN_FIELDMAP_PAIR, medium).</traceback>
      </failure>
      <failure test="test_an_sbref_does_not_count_as_coverage" file="tests/test_map.py" line="358">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE FieldmapCoverageError</message>
        <traceback>Same orphan-pair softening as above.</traceback>
      </failure>
      <failure test="test_a_phase_encoding_axis_mismatch_between_pair_and_target_raises" file="tests/test_map.py" line="376">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE FieldmapCoverageError</message>
        <traceback>Same coverage-gap softening as above.</traceback>
      </failure>
      <failure test="test_a_matrix_mismatch_between_pair_and_target_raises" file="tests/test_map.py" line="397">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE FieldmapCoverageError</message>
        <traceback>Same coverage-gap softening as above.</traceback>
      </failure>
      <failure test="test_the_returned_record_has_exactly_the_three_documented_keys" file="tests/test_warnings.py" line="56">
        <error_type>AssertionError</error_type>
        <message>extra key 'user_facing' in returned dict</message>
        <traceback>graded_warning() now returns a 4-key schema.</traceback>
      </failure>
      <failure test="test_the_returned_record_carries_the_inputs_verbatim" file="tests/test_warnings.py" line="62">
        <error_type>AssertionError</error_type>
        <message>left has extra 'user_facing' key</message>
        <traceback>Same 4-key schema change as above.</traceback>
      </failure>
    </failures>
  </pre_design_run>
  <failing_test_dispositions>
    <disposition test="test_the_returned_record_has_exactly_the_three_documented_keys" file="tests/test_warnings.py" classification="obsolete-test">
      <intended_contract>graded_warning() returns severity/code/message/user_facing (4-key schema) per the implement build's C1 change.</intended_contract>
      <current_test_claim>Return dict has exactly 3 keys: severity, code, message.</current_test_claim>
      <evidence>fmri_bids_recon/warnings.py:39-44 constructs a 4-key result dict including user_facing.</evidence>
      <action>Re-express: renamed to test_the_returned_record_has_exactly_the_four_documented_keys, assertion updated to the 4-key set.</action>
    </disposition>
    <disposition test="test_the_returned_record_carries_the_inputs_verbatim" file="tests/test_warnings.py" classification="obsolete-test">
      <intended_contract>Same as above.</intended_contract>
      <current_test_claim>Returned dict equals a 3-key literal.</current_test_claim>
      <evidence>fmri_bids_recon/warnings.py:39-44.</evidence>
      <action>Re-express: expected literal now includes "user_facing": False.</action>
    </disposition>
    <disposition test="test_the_conversion_argv_is_exactly_the_documented_command" file="tests/test_convert.py" classification="obsolete-test">
      <intended_contract>dcm2niix invocation includes -i y per the implement build's C10 change.</intended_contract>
      <current_test_claim>Expected argv omits -i y.</current_test_claim>
      <evidence>fmri_bids_recon/stage1_convert.py:87-96 cmd list includes "-i", "y".</evidence>
      <action>Re-express: expected argv literal updated to include -i y between -ba n and -b y.</action>
    </disposition>
    <disposition test="test_a_target_with_no_geometry_compatible_pair_raises" file="tests/test_map.py" classification="obsolete-test">
      <intended_contract>A target with no geometry-compatible fieldmap pair emits a FIELDMAP_COVERAGE_GAP graded_warning (high severity) and is left unmapped, per the implement build's C14 change.</intended_contract>
      <current_test_claim>map_fieldmaps() raises FieldmapCoverageError for this case.</current_test_claim>
      <evidence>fmri_bids_recon/stage3_map.py:486-492 replaced the raise with graded_warning + continue.</evidence>
      <action>Re-express: renamed to test_a_target_with_no_geometry_compatible_pair_emits_a_coverage_gap_warning; asserts get_warnings() and empty pair_to_targets instead of pytest.raises.</action>
    </disposition>
    <disposition test="test_a_func_pair_cannot_cover_a_diffusion_target" file="tests/test_map.py" classification="obsolete-test">
      <intended_contract>Same coverage-gap softening as above, applied to the func/dwi modality-separation case.</intended_contract>
      <current_test_claim>Raises FieldmapCoverageError.</current_test_claim>
      <evidence>fmri_bids_recon/stage3_map.py:486-492.</evidence>
      <action>Re-express: asserts FIELDMAP_COVERAGE_GAP warning content (modality='dwi', image_position failure substring) instead of pytest.raises.</action>
    </disposition>
    <disposition test="test_a_pair_covering_nothing_raises" file="tests/test_map.py" classification="obsolete-test">
      <intended_contract>An orphan fieldmap pair emits an ORPHAN_FIELDMAP_PAIR graded_warning (medium severity), per the implement build's C15 change.</intended_contract>
      <current_test_claim>Raises FieldmapCoverageError.</current_test_claim>
      <evidence>fmri_bids_recon/stage3_map.py:528-537 replaced the raise with graded_warning.</evidence>
      <action>Re-express: renamed to test_a_pair_covering_nothing_emits_an_orphan_pair_warning; asserts warning content instead of pytest.raises. Downstream ripple: repointed test_guard_coverage.py's no_orphan_pairs proof-test reference and remodeled its error field to None (see below).</action>
    </disposition>
    <disposition test="test_an_sbref_does_not_count_as_coverage" file="tests/test_map.py" classification="obsolete-test">
      <intended_contract>An SBRef-only target (modality lookup returns None, skipped by the main coverage pass) leaves its pair orphaned, which now emits ORPHAN_FIELDMAP_PAIR rather than raising, even though the passenger pass later attaches the SBRef to that pair for B0FieldSource metadata.</intended_contract>
      <current_test_claim>Raises FieldmapCoverageError.</current_test_claim>
      <evidence>Verified empirically: map_fieldmaps() with only an SBRef target produces exactly one ORPHAN_FIELDMAP_PAIR warning and a populated pair_to_targets (from the later passenger pass).</evidence>
      <action>Re-express: asserts exactly one ORPHAN_FIELDMAP_PAIR warning instead of pytest.raises.</action>
    </disposition>
    <disposition test="test_a_phase_encoding_axis_mismatch_between_pair_and_target_raises" file="tests/test_map.py" classification="obsolete-test">
      <intended_contract>Same coverage-gap softening as the geometry-mismatch case, applied to the pe_axis criterion.</intended_contract>
      <current_test_claim>Raises FieldmapCoverageError.</current_test_claim>
      <evidence>fmri_bids_recon/stage3_map.py:486-492.</evidence>
      <action>Re-express: renamed to test_a_phase_encoding_axis_mismatch_between_pair_and_target_emits_a_warning; asserts warning content (pe_axis failure substring). Downstream ripple: repointed test_guard_coverage.py's pe_axis_target_match proof-test reference and remodeled its error field to None (see below).</action>
    </disposition>
    <disposition test="test_a_matrix_mismatch_between_pair_and_target_raises" file="tests/test_map.py" classification="obsolete-test">
      <intended_contract>Same coverage-gap softening as above, applied to the matrix criterion.</intended_contract>
      <current_test_claim>Raises FieldmapCoverageError.</current_test_claim>
      <evidence>fmri_bids_recon/stage3_map.py:486-492.</evidence>
      <action>Re-express: renamed to test_a_matrix_mismatch_between_pair_and_target_emits_a_warning; asserts warning content (matrix failure substring). Downstream ripple: repointed test_guard_coverage.py's fieldmap_target_geometry_match proof-test reference and remodeled its error field to None (see below).</action>
    </disposition>
    <disposition test="test_a_multivolume_epi_navigator_halts_rather_than_dropping_silently" file="tests/test_classify.py" classification="obsolete-test">
      <intended_contract>A multi-volume EPI navigator halts only when it does NOT clear the physics-BOLD floor (n_volumes &gt;= 10); above the floor it passes through as BOLD, per the implement build's C5 change.</intended_contract>
      <current_test_claim>n_volumes=12 halts with NavigatorDropError.</current_test_claim>
      <evidence>fmri_bids_recon/stage2_classify.py:131-137 (_is_epi_bold_physics, n_volumes &gt;= 10 threshold) and :208-223 (Rule 3 physics pass-through).</evidence>
      <action>Re-express: fixture's n_volumes reduced from 12 to 3 (below the floor) so the halt is still exercised. Added a new complementary test (test_a_multivolume_epi_navigator_clearing_the_bold_physics_floor_passes_through) proving the pass-through branch with n_volumes=200.</action>
    </disposition>
    <disposition test="test_a_single_volume_epi_preceding_a_matching_dwi_is_a_diffusion_sbref" file="tests/test_classify.py" classification="product-bug">
      <intended_contract>A single-volume magnitude EPI immediately preceding a same-stem bval-bearing DWI is classified as DWI_SBREF via Rule 9's look-ahead.</intended_contract>
      <current_test_claim>roles[29] == Role.DWI_SBREF for a single-volume EP+SE fixture followed by a matching DWI.</current_test_claim>
      <evidence>Verified empirically: the broadened Rule 5 (fmri_bids_recon/stage2_classify.py:259-268, C6) unconditionally matches any single-volume, spin-echo, non-DIFFUSION-token EPI as FMAP_FUNC before Rule 9 (C8, merged SBRef rule) ever runs its look-ahead. Since real diffusion SBrefs are spin-echo (matching the dwi() fixture's own physics), Rule 5 now intercepts every physically realistic diffusion SBref. Confirmed with a direct classify() call: a single-volume EP+SE series followed by a matching bval-bearing DWI classifies as FMAP_FUNC, never reaching DWI_SBREF.</evidence>
      <action>Route to implement. No assertion edit; test left in its pre-existing form and continues to fail, correctly documenting the regression. User-approved disposition: full remodel deferred to /implement, not resolved in this /test pass.</action>
    </disposition>
    <disposition test="test_a_single_volume_epi_with_no_following_dwi_is_unclassified" file="tests/test_classify.py" classification="product-bug">
      <intended_contract>A single-volume magnitude EPI with no qualifying subsequent series falls through to UNCLASSIFIED.</intended_contract>
      <current_test_claim>roles[29] == Role.UNCLASSIFIED for a lone single-volume EP+SE fixture.</current_test_claim>
      <evidence>Same Rule 5/Rule 9 shadowing as above; the fixture is intercepted by Rule 5 as FMAP_FUNC before it can reach the UNCLASSIFIED fallback via Rule 9's failed look-ahead.</evidence>
      <action>Route to implement. No assertion edit; test left in its pre-existing form and continues to fail.</action>
    </disposition>
    <disposition test="test_a_lone_anatomical_without_norm_is_flagged_for_review" file="tests/test_classify.py" classification="obsolete-test">
      <intended_contract>The NORM/ND resolution pass only runs when the dataset carries a NORM token somewhere (Siemens-detection guard), per the implement build's C9 change.</intended_contract>
      <current_test_claim>A single T1w without NORM, alone in the dataset, is flagged.</current_test_claim>
      <evidence>fmri_bids_recon/stage2_classify.py:319-320 (has_norm guard).</evidence>
      <action>Re-express: added a NORM-bearing sibling series (t2w with norm=True) to the fixture set, establishing has_norm=True without changing the anatomical under test. Verified empirically that the original 1-flag assertion still holds with this fixture.</action>
    </disposition>
    <disposition test="test_a_paired_group_with_no_norm_member_flags_every_member" file="tests/test_classify.py" classification="obsolete-test">
      <intended_contract>Same has_norm guard as above; additionally, the new unconditional duplicate-modality guard (C9) now also fires for any T1W/T2W role with more than one survivor.</intended_contract>
      <current_test_claim>Two paired T1w series without NORM produce exactly 2 flags.</current_test_claim>
      <evidence>fmri_bids_recon/stage2_classify.py:319-320 (has_norm guard) and :385-395 (unconditional duplicate-modality guard).</evidence>
      <action>Re-express: added a NORM-bearing sibling to establish has_norm=True. Assertions split by code: 2 AMBIGUOUS_CLASSIFICATION flags (original intent, unweakened) plus 1 new DUPLICATE_MODALITY flag, verified empirically.</action>
    </disposition>
    <disposition test="test_status_reflects_any_high_severity_warning_not_just_bids_errors" file="tests/test_cli_integration.py" classification="obsolete-test">
      <intended_contract>BidsReconResult.status is determined from the module-level warning accumulator (get_warnings()), not from classify()'s returned flag list, per the implement build's C11 change.</intended_contract>
      <current_test_claim>A raw dict appended to classify()'s returned flags list is reflected in result.warnings and drives status="warning".</current_test_claim>
      <evidence>fmri_bids_recon/pipeline.py:339-340 (all_warnings = get_warnings(); status determined from it).</evidence>
      <action>Re-express: the injected warning is now produced via an actual graded_warning() call inside the monkeypatched classify() wrapper, so it flows through the accumulator exactly as a real high-severity pipeline warning would. Assertion strengthened to check the warning is present by code rather than exact dict identity.</action>
    </disposition>
  </failing_test_dispositions>
  <design_phase>
    <tests_created>9</tests_created>
    <tests_modified>13</tests_modified>
    <files_created>
      <file path="tests/test_warnings.py" test_count="3" coverage_target="module-level warning accumulator: get_warnings()/clear_warnings() API, append-on-call behavior, copy semantics" />
      <file path="tests/test_classify.py" test_count="6" coverage_target="physics-BOLD pass-through floor, vendor-agnostic LOCALIZER/description-keyword scout signals, has_norm guard skip on norm-free datasets, duplicate-modality guard independent of has_norm" />
    </files_created>
    <design_rationale>
      Every pre-design failure was dispositioned per the mandatory per-failure ledger before any edit. 13 of 15 were obsolete-test (the implement build's approved contract changes were correctly reflected in the engine but not yet in the tests); all 13 were re-expressed with assertions verified empirically against the actual post-build runtime behavior before being written, never assumed. 2 were product-bug (a genuine regression: the broadened vendor-agnostic FMAP_FUNC rule now shadows the diffusion-SBref look-ahead rule for any physically realistic, spin-echo diffusion SBref) and were left unedited per explicit user decision, routed to implement rather than patched around.

      Mid-design-phase, renaming 3 tests in test_map.py surfaced a downstream architectural conflict in test_guard_coverage.py: that module's roster asserted exactly one guard (exact_volume_counts) may exclude/warn rather than halt, an invariant the implement build's fieldmap-coverage softening (C14/C15) had already violated for three more guards without the roster being updated. Per explicit user decision, this was fully remodeled rather than patched: the three guards (fieldmap_target_geometry_match, pe_axis_target_match, no_orphan_pairs) now correctly declare error=None, the "exactly one" invariant was re-expressed as "exactly these four" with an expanded rationale, and the two per-guard skip-reason messages plus the loophole-closing raise-path test were generalized to the four-guard model without weakening their original intent.

      New coverage added beyond the disposition ledger: the accumulator API itself (get_warnings/clear_warnings) had no direct tests prior to this pass; the three new vendor-agnostic scout-detection signals (LOCALIZER token, description-keyword with physics guard) and the standalone duplicate-modality guard (independent of has_norm) were untested prior to this build and are now covered.
    </design_rationale>
  </design_phase>
  <post_design_run>
    <total>608</total>
    <passed>511</passed>
    <failed>2</failed>
    <errors>0</errors>
    <coverage_pct></coverage_pct>
    <failures>
      <failure test="test_a_single_volume_epi_preceding_a_matching_dwi_is_a_diffusion_sbref" file="tests/test_classify.py" line="359">
        <error_type>AssertionError</error_type>
        <message>assert Role.FMAP_FUNC == Role.DWI_SBREF</message>
        <traceback>- dwi_sbref
+ fmap_func</traceback>
        <likely_cause>Confirmed product-bug: Rule 5's broadening (C6) shadows Rule 9's diffusion-SBref look-ahead (C8) for any physically realistic spin-echo single-volume EPI. See disposition ledger and action_items.</likely_cause>
      </failure>
      <failure test="test_a_single_volume_epi_with_no_following_dwi_is_unclassified" file="tests/test_classify.py" line="372">
        <error_type>AssertionError</error_type>
        <message>assert Role.FMAP_FUNC == Role.UNCLASSIFIED</message>
        <traceback>- unclassified
+ fmap_func</traceback>
        <likely_cause>Same root cause as above.</likely_cause>
      </failure>
    </failures>
  </post_design_run>
  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>2</bugs_routed_to_implement>
    <recommendation>implement_fixes</recommendation>
  </summary>
  <action_items>
    <item priority="P0" target_mode="implement" description="Resolve the Rule 5/Rule 9 ordering conflict in fmri_bids_recon/stage2_classify.py: the broadened Rule 5 (FMAP_FUNC, vendor-agnostic, matches any single-volume spin-echo EPI with a non-DIFFUSION token) unconditionally intercepts single-volume series before Rule 9's diffusion-SBref look-ahead ever runs, making the DWI_SBREF branch unreachable for any physically realistic (spin-echo) diffusion single-band reference. Candidate approaches: give Rule 5 a look-ahead exception mirroring Rule 9's (skip FMAP_FUNC classification when the next same-stem series is a bval-bearing DIFFUSION-token series), or reorder so Rule 9's diffusion-SBref look-ahead runs before Rule 5 commits for single-volume, non-DIFFUSION-token series. Failing tests: tests/test_classify.py::test_a_single_volume_epi_preceding_a_matching_dwi_is_a_diffusion_sbref, tests/test_classify.py::test_a_single_volume_epi_with_no_following_dwi_is_unclassified." />
  </action_items>
</test_report>
