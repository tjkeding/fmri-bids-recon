<test_report>
  <meta project="fmri-bids-recon" mode="test" submodule="run_suite" timestamp="2026-07-17T19:45:52Z" />
  <scope>Explicit run_suite-only invocation (no submodule argument omitted; design was not requested and was not run). Input report: fmri-bids-recon_implement_build_20260717_195412.md (the geometry-diagnostics refactor and SBRef passenger-pass build).</scope>
  <pre_design_run>
    <total>377</total>
    <passed>375</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct>null</coverage_pct>
    <skipped>2</skipped>
    <failures />
  </pre_design_run>
  <failing_test_dispositions>
    <!-- No failing tests; no dispositions required. -->
  </failing_test_dispositions>
  <design_phase>
    <invoked>false</invoked>
    <tests_created>0</tests_created>
    <tests_modified>0</tests_modified>
    <design_rationale>Not run. This invocation explicitly specified the run_suite submodule only; per the skill's submodule-scoping convention, the design phase is not auto-entered.</design_rationale>
  </design_phase>
  <post_design_run>
    <invoked>false</invoked>
  </post_design_run>
  <verification>
    <receipt_verified>true</receipt_verified>
    <verification_method>verify_receipts.py anti-fabrication cross-check (nonce, clock window, duration, summary-line match, tee'd receipt file mtime/nonce/summary, independent --collect-only oracle match)</verification_method>
    <collect_only_oracle>377</collect_only_oracle>
    <oracle_agrees_with_receipt>true</oracle_agrees_with_receipt>
  </verification>
  <summary>
    <assertions_preserved_or_strengthened>n/a</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>0</bugs_routed_to_implement>
    <recommendation>proceed</recommendation>
  </summary>
  <action_items>
    <!-- None. All 375 non-skipped tests pass, including the SBRef passenger-pass test targeted by the preceding build. -->
  </action_items>
</test_report>
