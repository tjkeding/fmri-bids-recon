<test_report>
  <meta project="bids-recon" mode="test" timestamp="2026-08-27T17:33:50Z" />
  <pre_design_run>
    <total>641</total>
    <passed>546</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct>null</coverage_pct>
    <failures></failures>
  </pre_design_run>
  <failing_test_dispositions>
    <!-- No failures in the pre-design run; the disposition ledger is empty. -->
  </failing_test_dispositions>
  <design_phase>
    <tests_created>1</tests_created>
    <tests_modified>0</tests_modified>
    <files_created>
      <file path="tests/test_sanitize_sys_path.py" test_count="1 (added; file total unchanged in count of new files)" coverage_target="Adds test_foreign_version_contamination_is_stripped_before_pipeline_import: a subprocess-based regression test reproducing the exact reported production bug (FSL Python 3.11 numpy shadowing Python 3.12 conda numpy via PYTHONPATH). Spawns a subprocess that imports fmri_bids_recon.__main__ (the literal console-entry-point import path) with a fake foreign-version numpy stub on PYTHONPATH that raises RuntimeError if ever imported; asserts the subprocess exits cleanly and the stub is never reached." />
    </files_created>
    <design_rationale>
      The pre-design run was clean (0 failures), so this cycle is proactive coverage for the
      just-implemented guard-relocation fix (implement build 2026-08-27T17:20:45Z, changes C1/C2/C3)
      rather than disposition-ledger remediation. The prior test suite had a real coverage gap: all
      existing tests in test_sanitize_sys_path.py call _sanitize_sys_path() directly and assert on
      its logic in isolation, which cannot distinguish "guard is correct but runs too late" from
      "guard is correct and runs at the right time" -- exactly the dimension the reported production
      bug lived in (the function itself was never wrong; it simply executed after __init__.py's
      `from .pipeline import run, BidsReconResult` had already reached nibabel/numpy). The new test
      reproduces the entry point's actual import path (`from fmri_bids_recon.__main__ import main`)
      in a subprocess with a synthetic foreign-version numpy stub on PYTHONPATH, so it exercises the
      real import-ordering contract rather than the function's internals.

      This test was verified empirically to discriminate the fix: run against the pre-fix code
      (via `git stash` of fmri_bids_recon/__init__.py and __main__.py, reverting to the last
      committed state before this session's relocation), the test's own fixture errored with
      `AttributeError: module 'fmri_bids_recon' has no attribute '_STRIPPED_PATHS'` -- confirming
      the pre-fix package namespace genuinely lacked the guard. Against the post-fix code, the test
      passes cleanly. This mirrors the real production traceback the user reported (FSL's Python 3.11
      numpy C-extension failing to import from within the fmri_bids_recon.__init__ import chain).
    </design_rationale>
  </design_phase>
  <post_design_run>
    <total>642</total>
    <passed>547</passed>
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
