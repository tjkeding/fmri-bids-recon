<test_report>
  <meta project="bids-recon" mode="test" timestamp="2026-08-26T19:01:36Z" />

  <pre_design_run>
    <total>0</total>
    <passed>0</passed>
    <failed>0</failed>
    <errors>5</errors>
    <coverage_pct />
    <failures>
      <failure test="collection" file="tests/test_map.py" line="19">
        <error_type>ImportError</error_type>
        <message>cannot import name 'pair_fieldmaps' from 'fmri_bids_recon.stage3_map'</message>
        <traceback>ImportError while importing test module; pair_fieldmaps was renamed to group_fieldmaps in the C4 refactor</traceback>
      </failure>
      <failure test="collection" file="tests/test_render.py" line="22">
        <error_type>ImportError</error_type>
        <message>cannot import name 'pair_fieldmaps' from 'fmri_bids_recon.stage3_map'</message>
        <traceback>ImportError while importing test module</traceback>
      </failure>
      <failure test="collection" file="tests/test_report.py" line="18">
        <error_type>ImportError</error_type>
        <message>cannot import name 'pair_fieldmaps' from 'fmri_bids_recon.stage3_map'</message>
        <traceback>ImportError while importing test module</traceback>
      </failure>
      <failure test="collection" file="tests/test_assemble.py" line="21">
        <error_type>ImportError</error_type>
        <message>cannot import name 'FieldmapPair' from 'fmri_bids_recon.stage3_map'</message>
        <traceback>ImportError while importing test module; FieldmapPair was renamed to FieldmapUnit</traceback>
      </failure>
      <failure test="collection" file="tests/test_json_intermediate.py" line="18">
        <error_type>ImportError</error_type>
        <message>cannot import name 'FieldmapPair' from 'fmri_bids_recon.stage3_map'</message>
        <traceback>ImportError while importing test module</traceback>
      </failure>
    </failures>
  </pre_design_run>

  <failing_test_dispositions>

    <disposition test="collection (whole file)" file="tests/test_map.py" classification="obsolete-test">
      <intended_contract>Fieldmap pairing (group_fieldmaps), coverage mapping (map_fieldmaps), and the physics-to-filename dir- label contract.</intended_contract>
      <current_test_claim>Called the removed pair_fieldmaps() API; accessed FieldmapPair.member_a/member_b/dir_a/dir_b and mapping.pair_to_targets, all removed in the C4 refactor.</current_test_claim>
      <evidence>fmri_bids_recon/stage3_map.py: pair_fieldmaps renamed to group_fieldmaps (returns (units, unpaired_fmaps)); FieldmapPair renamed to FieldmapUnit (members: list, dir_labels: list, mode field added); Mapping.pairs/pair_to_targets renamed to units/unit_to_targets; ORPHAN_FIELDMAP_PAIR renamed to ORPHAN_FIELDMAP_UNIT (user-approved during design).</evidence>
      <action>Re-expressed to the new API throughout (mechanical). Additionally, three tests asserting PhaseEncodingError for absent-PE and odd-count scenarios were re-expressed to their new, deliberately-changed CR F3/F7 contract: routed to unpaired_fmaps with a graded_warning instead of raising. Verified against the real implementation before finalizing: all re-expressed assertions pass.</action>
    </disposition>

    <disposition test="collection (whole file)" file="tests/test_assemble.py" classification="obsolete-test">
      <intended_contract>BIDS assembly of every classified series, including fieldmap members, into the correct directory/filename, with nothing silently destroyed.</intended_contract>
      <current_test_claim>Called pair_fieldmaps(); assemble() call sites lacked the new required gre_sets/unpaired_fmaps parameters.</current_test_claim>
      <evidence>stage4_assemble.assemble() signature extended (C6) with gre_sets: list[GREFieldmapSet] and unpaired_fmaps: list[Series]; conftest.py's build_session()/session_kwargs already updated to supply both.</evidence>
      <action>Re-expressed API surface. test_an_unpaired_fieldmap_halts_the_session_as_ambiguous re-expressed to its new CR F7 contract (renamed test_a_repeated_fieldmap_is_paired_where_possible_and_the_remainder_routed): odd count degrades gracefully instead of halting. test_a_fieldmap_role_absent_from_the_pairing_output_halts_assembly kept UNCHANGED (see product-bug finding below).</action>
    </disposition>

    <disposition test="collection (whole file)" file="tests/test_json_intermediate.py" classification="obsolete-test">
      <intended_contract>Every dataclass appearing in the phase-1-to-phase-3 intermediate JSON round-trips field-by-field through encode/decode.</intended_contract>
      <current_test_claim>Constructed FieldmapPair(member_a=..., member_b=..., dir_a=..., dir_b=...) and Mapping(pairs=..., pair_to_targets=...), both removed.</current_test_claim>
      <evidence>Same stage3_map.py rename as above; json_intermediate.py's _DATACLASS_TYPES registry updated (C4/C6 deviation) to FieldmapUnit and the newly-introduced GREFieldmapSet.</evidence>
      <action>Re-expressed the two existing tests to FieldmapUnit/Mapping's new shape. Added new coverage: GREFieldmapSet round-trips with nested Series lists (previously untested; C6 now serializes it through the same intermediate file).</action>
    </disposition>

    <disposition test="collection (whole file)" file="tests/test_render.py" classification="obsolete-test">
      <intended_contract>B0FieldIdentifier/B0FieldSource/IntendedFor rendering derives from the same Mapping object so the two BIDS conventions cannot disagree.</intended_contract>
      <current_test_claim>Called pair_fieldmaps() and imported _pair_identifier, both removed/renamed.</current_test_claim>
      <evidence>stage5_render._pair_identifier renamed to _unit_identifier (C4 deviation); same stage3_map rename.</evidence>
      <action>Re-expressed API surface only; identifier-generation logic itself is unchanged, so no behavioral re-express was needed.</action>
    </disposition>

    <disposition test="collection (whole file)" file="tests/test_report.py" classification="obsolete-test">
      <intended_contract>The human-facing conversion report names every decision the pipeline made, including which fieldmap unit corrects which run.</intended_contract>
      <current_test_claim>Called pair_fieldmaps()/map_fieldmaps() with the removed API.</current_test_claim>
      <evidence>Same stage3_map rename.</evidence>
      <action>Re-expressed API surface. The fieldmap-mapping-table assertion (dir-PA/dir-AP format) was left UNCHANGED (see product-bug finding below). Added new coverage for the "Unpaired fieldmaps (routed to sourcedata)" section (a genuinely new report.py section added during the C4 deviation).</action>
    </disposition>

    <disposition test="test_a_guard_violation_exits_one" file="tests/test_cli_integration.py" classification="obsolete-test">
      <intended_contract>A GuardError-raising pipeline invariant violation exits the CLI with code 1, distinct from operational/config/tool-version errors.</intended_contract>
      <current_test_claim>Used a single odd-count functional fieldmap as the guard-violation fixture.</current_test_claim>
      <evidence>CR F7 deliberately converted odd-count fieldmap groups from a hard halt to a graceful-degradation warning; this fixture no longer raises anything, so the test as written no longer exercises exit code 1 at all.</evidence>
      <action>Re-expressed the fixture to two same-direction functional fieldmaps (opposite_pe_within_pair violation), which still genuinely halts. This test did not fail during collection (it collected fine); the disposition is recorded here because it would have silently stopped testing anything once CR F7 landed, without ever failing.</action>
    </disposition>

    <disposition test="roster entry: fieldmap_pairing_unambiguous" file="tests/test_guard_coverage.py" classification="product-bug">
      <intended_contract>Every guard in ALL_GUARD_NAMES has an independently-triggerable violation path, proven by its own dedicated test (not shared with another guard's exception).</intended_contract>
      <current_test_claim>fieldmap_pairing_unambiguous's proof test was test_a_fieldmap_with_no_phase_encoding_direction_raises.</current_test_claim>
      <evidence>Traced group_fieldmaps(): its only two remaining PhaseEncodingError raise sites are opposite_pe_within_pair and dir_label_pe_agreement. Absent-PE and odd-count (this guard's historical violation modes) are now deliberately non-halting per CR F3/F7. fieldmap_pairing_unambiguous therefore always succeeds whenever those two other guards succeed -- it has no independent violation path left.</evidence>
      <action>User chose (explicit adjudication during design) to design a new, genuinely independent halt condition rather than reclassify the guard as non-halting: a timestamp tie between two fieldmap members within the same modality sub-group makes their consecutive-pairing order arbitrary. Added test_a_pairing_time_tie_within_a_modality_subgroup_raises in test_map.py and repointed the roster entry at it. EXPECTED TO FAIL until routed through /implement (group_fieldmaps() does not yet detect this case).</action>
    </disposition>

  </failing_test_dispositions>

  <design_phase>
    <tests_created>39</tests_created>
    <tests_modified>28</tests_modified>
    <files_created>
      <file path="tests/test_map.py" test_count="40" coverage_target="group_fieldmaps/map_fieldmaps re-express (CR F3/F7 graceful degradation) plus new group_gre_fieldmaps/_relaxed_geometry_check/map_gre_fieldmaps coverage (CR F5/F8) and the new fieldmap_pairing_unambiguous timestamp-tie test" />
      <file path="tests/test_assemble.py" test_count="35" coverage_target="assemble() re-express plus new GRE Case 1/2/3/indeterminate assembly coverage (CR F5) and the odd-count graceful-degradation path" />
      <file path="tests/test_json_intermediate.py" test_count="24" coverage_target="FieldmapUnit re-express plus new GREFieldmapSet round-trip coverage" />
      <file path="tests/test_render.py" test_count="11" coverage_target="_unit_identifier re-express (mechanical only)" />
      <file path="tests/test_report.py" test_count="10" coverage_target="group_fieldmaps re-express plus new unpaired-fieldmaps-section coverage" />
      <file path="tests/test_cli_integration.py" test_count="32" coverage_target="guard-violation fixture swap (mechanical contract preservation)" />
      <file path="tests/test_guard_coverage.py" test_count="47" coverage_target="roster proof-test repoint for fieldmap_pairing_unambiguous and the unit-vs-pair renames" />
      <file path="tests/test_classify.py" test_count="63" coverage_target="new: canonical_modality vendor dispatch (Siemens/GE/Philips/fallback), layered _is_epi (CR F4), vendor-dispatched _is_spin_echo (D8), DIS2D negative guard (CR F2), rule 3.5 GRE phase classification, GE SE_EPI context gate (CR F1); plus a pre-existing test's fixture fixed (see below)" />
      <file path="tests/test_labels.py" test_count="27" coverage_target="new: TaskRegistryEntry.prefix persistence and the stored-prefix drift-guard fix (D14/C7)" />
      <file path="tests/conftest.py" test_count="0" coverage_target="build_session() rewired to group_fieldmaps/gre_sets/unpaired_fmaps; _series() factory extended to expose vendor/echo_number/phase_encoding_axis/sequence_name/software_versions, which it silently defaulted to None for every test series before this fix (a fixture gap, not a product bug -- it blocked all vendor-dispatch coverage from being written at all)" />
    </files_created>
    <design_rationale>
      Two categories of work. (1) Re-express: eight files broke or would silently stop testing anything due to the C1-C7 refactor's API renames (pair_fieldmaps to group_fieldmaps, FieldmapPair to FieldmapUnit, dir_a/dir_b to dir_labels, ORPHAN_FIELDMAP_PAIR to ORPHAN_FIELDMAP_UNIT) and deliberately-changed contracts (CR F3/F7 halt-to-warning conversions). Every re-expressed assertion was verified directly against the real implementation before being finalized, not just hand-derived. (2) New coverage: C1-C3, C5-C7 added substantial new pipeline behavior (vendor-aware classification, GRE fieldmap grouping and assembly, task-registry prefix persistence) with zero prior test coverage; this pass designed and verified first-class coverage for all of it. A conftest.py fixture gap (the four new Series fields were unreachable from any test factory) was found and fixed as a precondition for the vendor-dispatch coverage. One test-authoring error of my own (an incorrect assumption about the Philips EPI-detection fallback's branch structure) was caught by running the test against the real implementation and corrected before finalizing.
    </design_rationale>
  </design_phase>

  <post_design_run>
    <total>636</total>
    <passed>538</passed>
    <failed>3</failed>
    <errors>0</errors>
    <coverage_pct />
    <failures>
      <failure test="test_a_fieldmap_role_absent_from_the_pairing_output_halts_assembly" file="tests/test_assemble.py" line="554">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE GuardError</message>
        <traceback>Failed: DID NOT RAISE GuardError</traceback>
        <likely_cause>Product bug in stage4_assemble.assemble(): the per-series loop now `continue`s past any fieldmap-role series absent from fmap_unit_lookup without checking whether it is also absent from unpaired_fmaps. A series that never entered group_fieldmaps() at all (a genuine wiring defect, as opposed to a CR F3/F7 legitimate degradation) is silently dropped -- no BIDS file, no sourcedata copy, no error -- instead of raising GuardError(guard="fieldmap_pair_complete").</likely_cause>
      </failure>
      <failure test="test_a_pairing_time_tie_within_a_modality_subgroup_raises" file="tests/test_map.py" line="214">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE PhaseEncodingError</message>
        <traceback>Failed: DID NOT RAISE PhaseEncodingError</traceback>
        <likely_cause>Missing feature in stage3_map.group_fieldmaps(): two same-geometry, opposite-PE fieldmap members sharing an identical AcquisitionDateTime have no principled consecutive-pairing order, but nothing currently detects this. This is the new, independent halt condition the user explicitly chose to add for the fieldmap_pairing_unambiguous guard (see the product-bug disposition above) rather than reclassifying the guard as non-halting.</likely_cause>
      </failure>
      <failure test="test_the_fieldmap_mapping_section_records_which_pair_corrects_which_run" file="tests/test_report.py" line="137">
        <error_type>AssertionError</error_type>
        <message>assert 'dir-PA/dir-AP, run-01' in report output</message>
        <traceback>AssertionError: assert 'dir-PA/dir-AP, run-01' in report text</traceback>
        <likely_cause>Formatting regression in report.py's fieldmap-mapping-table row: produces "dir-PA/AP, run-01" (joining anatomical_labels with a single leading dir- prefix) instead of the original "dir-PA/dir-AP, run-01" (each direction independently dir--prefixed).</likely_cause>
      </failure>
    </failures>
  </post_design_run>

  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>3</bugs_routed_to_implement>
    <recommendation>implement_fixes</recommendation>
  </summary>

  <action_items>
    <item priority="P0" target_mode="implement" description="stage4_assemble.py per-series fieldmap loop: when a FMAP_FUNC/FMAP_DWI series is absent from fmap_unit_lookup, raise GuardError(guard='fieldmap_pair_complete') unless it is also present in the unpaired_fmaps parameter (the legitimate CR F3/F7 degradation case); currently it is silently dropped in both cases. Proof test: tests/test_assemble.py::test_a_fieldmap_role_absent_from_the_pairing_output_halts_assembly." />
    <item priority="P1" target_mode="implement" description="stage3_map.py report.py: fix the fieldmap-mapping-table row format to independently dir--prefix each direction label ('dir-PA/dir-AP') instead of joining them under one shared prefix ('dir-PA/AP'). Proof test: tests/test_report.py::test_the_fieldmap_mapping_section_records_which_pair_corrects_which_run." />
    <item priority="P1" target_mode="implement" description="stage3_map.py group_fieldmaps(): add a timestamp-tie detection within each modality sub-group (after the odd-count check, before consecutive pairing) -- if two members share an identical acquisition_datetime, raise PhaseEncodingError, since their pairing order is otherwise arbitrary. This restores fieldmap_pairing_unambiguous as an independently-triggerable guard, per explicit user adjudication during /test design (chosen over reclassifying it as non-halting). Proof test: tests/test_map.py::test_a_pairing_time_tie_within_a_modality_subgroup_raises." />
  </action_items>
</test_report>
