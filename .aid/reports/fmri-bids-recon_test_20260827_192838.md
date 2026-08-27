<test_report>
  <meta project="fmri-bids-recon" mode="test" timestamp="2026-08-27T19:28:38Z" />
  <pre_design_run>
    <total>642</total>
    <passed>547</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct>null</coverage_pct>
    <failures></failures>
  </pre_design_run>
  <failing_test_dispositions>
  </failing_test_dispositions>
  <design_phase>
    <tests_created>12</tests_created>
    <tests_modified>0</tests_modified>
    <files_created>
      <file path="tests/test_classify.py" test_count="12" coverage_target="Calibration sequence exclusion guard: PE axis validation pass (modality-scoped matching, opposite-polarity tolerance, empty-target bypass) and description keyword guard (defense-in-depth, compound-match stem requirement), including a direct regression fixture modeling the reported Siemens vNav setter production bug." />
    </files_created>
    <design_rationale>
      Pre-design baseline showed zero failures, so no failing-test dispositions were needed;
      the design phase added coverage for the calibration sequence exclusion guard built in
      this session's /implement pass (5 changes across stage2_classify.py and
      stage4_assemble.py, per fmri-bids-recon_implement_plan_20260827_191254.md). The new
      tests follow the existing test_classify.py convention of pinning each classification
      rule to the physics it discriminates on and testing each modality path (functional vs.
      diffusion fieldmap) independently, matching the density of coverage given to the
      adjacent NORM/ND twin-resolution pass. Coverage spans: the core PE-axis-mismatch
      demotion path, opposite-polarity tolerance (the normal fieldmap/target relationship),
      modality-scoped axis checking (FMAP_FUNC checked only against BOLD axes, FMAP_DWI only
      against DWI axes, proven by constructing sessions where the wrong-modality axis would
      produce a false pass if scoping were broken), the empty-target bypass for both
      modalities, the description-keyword defense-in-depth layer for both modalities, the
      compound-match stem-mismatch requirement that prevents the keyword guard from
      overreaching, and a direct regression fixture modeling the reported production bug
      (two sagittal single-volume SE-EPI calibration candidates alongside a differently-axed
      BOLD run). No assembly-level (test_assemble.py) test was added for DROP_CALIBRATION's
      silent-discard routing, matching the existing convention that DROP_NAVIGATOR,
      DROP_SCOUT, and DROP_DERIVED also have no dedicated assembly-level tests (their
      silent discard is a structural consequence of assemble()'s role-dispatch loop).
    </design_rationale>
  </design_phase>
  <post_design_run>
    <total>654</total>
    <passed>559</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct>null</coverage_pct>
    <failures></failures>
  </post_design_run>
  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>0</bugs_routed_to_implement>
    <recommendation>proceed_to_document</recommendation>
  </summary>
  <action_items>
  </action_items>
</test_report>
