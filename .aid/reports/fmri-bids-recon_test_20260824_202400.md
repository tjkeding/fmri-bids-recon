<test_report>
  <meta project="bids-recon" mode="test" timestamp="2026-08-24T20:24:00Z" />
  <pre_design_run>
    <total>608</total>
    <passed>513</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct />
    <failures />
  </pre_design_run>
  <failing_test_dispositions>
    <!-- No failing tests in the pre-design run. Both product-bug tests from the prior
         cycle (test_a_single_volume_epi_preceding_a_matching_dwi_is_a_diffusion_sbref,
         and the renamed test_a_lone_single_volume_spin_echo_epi_is_a_functional_fieldmap)
         now pass following the context-aware Rule 5 fix applied in the implement build. -->
  </failing_test_dispositions>
  <design_phase>
    <tests_created>3</tests_created>
    <tests_modified>0</tests_modified>
    <files_created>
      <file path="tests/test_classify.py" test_count="3" coverage_target="Vendor-token coverage and look-ahead gating conditions for Rule 5's context-aware DWI look-ahead" />
    </files_created>
    <design_rationale>
      The implement build introduced a new DWI look-ahead inside Rule 5, with three gating
      conditions (same description stem, DIFFUSION modality token, .bval existence) and a
      vendor-agnostic default-to-FMAP_FUNC fallback. Pre-existing coverage exercised the
      positive DWI_SBREF path and the tok="FMRI" / tok="M" FMAP_FUNC defaults, but left two
      gaps: (1) no test exercised GE's tok="OTHER" token, which was the specific vendor case
      motivating the broadened gate; (2) the same_stem and bval_exists gating conditions
      inside the new look-ahead had no negative-case coverage proving they are load-bearing
      rather than vestigial. Three tests were added to close these gaps:
      test_a_lone_single_volume_spin_echo_epi_with_a_ge_style_token_is_a_functional_fieldmap,
      test_a_single_volume_epi_preceding_a_differently_named_dwi_is_still_a_functional_fieldmap,
      and test_a_single_volume_epi_preceding_a_bvalless_same_stem_diffusion_series_is_a_functional_fieldmap.
    </design_rationale>
  </design_phase>
  <post_design_run>
    <total>611</total>
    <passed>516</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct />
    <failures />
  </post_design_run>
  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>0</bugs_routed_to_implement>
    <recommendation>proceed_to_document</recommendation>
  </summary>
  <action_items />
</test_report>
