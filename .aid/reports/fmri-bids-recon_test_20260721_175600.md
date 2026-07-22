<test_report>
  <meta project="fmri-bids-recon" mode="test" timestamp="2026-07-21T13:56:00-04:00" />
  <pre_design_run>
    <total>390</total>
    <passed>388</passed>
    <failed>0</failed>
    <errors>0</errors>
    <skipped>2</skipped>
    <coverage_pct>n/a</coverage_pct>
    <failures />
    <receipt_verification>
      <nonce>F074DC7B-349D-4BC9-8DBC-48F695AB11F1</nonce>
      <all_checks_passed>true</all_checks_passed>
      <checks>freshness/nonce=match, freshness/clock=match, freshness/duration=match, freshness/summary=match, freshness/collect_total=match, freshness/receipt_file_mtime=match, freshness/receipt_file_nonce=match, freshness/receipt_file_summary=match</checks>
    </receipt_verification>
  </pre_design_run>
<failing_test_dispositions />
  <design_phase>
    <tests_created>0</tests_created>
    <tests_modified>0</tests_modified>
    <design_rationale>No design phase executed. Pre-design run showed 0 failures. The user's request targeted verification of the adversarial dataset (31/31 passed) and a baseline suite confirmation (388 passed, 2 documented skips). No new coverage gaps were identified.</design_rationale>
  </design_phase>
  <post_design_run>
    <note>Skipped (no design changes made; post-design run would be identical to pre-design).</note>
  </post_design_run>
  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>0</bugs_routed_to_implement>
    <pipeline_test_result>388 passed, 2 skipped, 0 failed (390 collected)</pipeline_test_result>
<recommendation>proceed_to_implement (resolve pydeface dependency gap in environment.yml)</recommendation>
  </summary>
  <action_items>
    <item priority="P1" target_mode="implement" description="Add pydeface to environment.yml. The pipeline invokes pydeface unconditionally at Phase 5 (deface.py line 82), but pydeface is not declared in environment.yml and is absent from the conda environment. This will cause a runtime failure on the first real-data run." />
    <item priority="P2" target_mode="test" description="Add test assertions for the candidate_pairs key in FieldmapCoverageError.context to exercise the per-criterion geometry-mismatch diagnostic content (already implemented in stage3_map.py lines 473-495, but not tested at the assertion level)." />
  </action_items>
</test_report>
