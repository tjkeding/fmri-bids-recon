<test_report>
  <meta project="fmri-bids-recon" mode="test" timestamp="2026-07-15T19:42:10Z" submodule="run_suite" />
  <pre_design_run>
    <total>368</total>
    <passed>366</passed>
    <failed>0</failed>
    <errors>0</errors>
    <skipped>2</skipped>
    <coverage_pct>not measured (run_suite regression check; coverage instrumentation not requested)</coverage_pct>
    <failures />
    <verification>
      <return_schema>ok</return_schema>
      <receipt_freshness>all 8 checks match: nonce, clock, duration, summary, collect_total, receipt_file_mtime, receipt_file_nonce, receipt_file_summary</receipt_freshness>
      <collect_only_oracle>368 tests collected (independent --collect-only), matches receipt summary 366 passed + 2 skipped</collect_only_oracle>
      <interpreter>conda env fmri-bids-recon, Python 3.12.13, pytest 9.1.1</interpreter>
    </verification>
  </pre_design_run>
  <failing_test_dispositions />
  <design_phase>
    <tests_created>0</tests_created>
    <tests_modified>0</tests_modified>
    <files_created />
    <design_rationale>Not run. The user invoked /test with the run_suite submodule only ("run_suite to ensure no regressions"), scoping this invocation to a baseline regression check of the existing suite. No test authoring or modification was performed.</design_rationale>
  </design_phase>
  <post_design_run>
    <total>not run (run_suite-only invocation)</total>
    <passed>n/a</passed>
    <failed>n/a</failed>
    <errors>n/a</errors>
    <coverage_pct>n/a</coverage_pct>
    <failures />
  </post_design_run>
  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>0</bugs_routed_to_implement>
    <recommendation>proceed_to_document</recommendation>
    <regression_verdict>No regressions. The suite is identical to the pre-deployment baseline (366 passed, 2 skipped, 0 failed, 0 errors). This is the expected outcome: the five deployment changes (environment.yml, hpc/setup_env.sh, the two rewritten sbatch scripts, and the Apptainer.def integrity fix) are server-side configuration and shell artifacts that do not import or exercise the fmri_bids_recon package, so they are outside the pytest suite's scope by construction.</regression_verdict>
    <scope_note>The two principled skips are unchanged from baseline. The deployment path (live dcm2niix and bids-validator binaries) remains unexercised by this suite, as both external boundaries are stubbed in tests; that verification can only occur on the server against live data.</scope_note>
  </summary>
  <action_items />
</test_report>
