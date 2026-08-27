<test_report>
  <meta project="bids-recon" mode="test" timestamp="2026-08-25T11:43:28Z" />
  <pre_design_run>
    <total>593</total>
    <passed>497</passed>
    <failed>1</failed>
    <errors>0</errors>
    <coverage_pct></coverage_pct>
    <failures>
      <failure test="test_a_guard_violation_is_blocking[dcm2niix_version_floor]" file="tests/test_guard_coverage.py" line="206">
        <error_type>AssertionError</error_type>
        <message>assert False where False = issubclass(ToolVersionError, GuardError)</message>
        <traceback>AssertionError: assert False
 +  where False = issubclass(&lt;class 'fmri_bids_recon.errors.ToolVersionError'&gt;, GuardError)
 +    where &lt;class 'fmri_bids_recon.errors.ToolVersionError'&gt; = Guard(engine_module='tool_registry', error=&lt;class 'fmri_bids_recon.errors.ToolVersionError'&gt;, ...).error
/Users/tjkeding/bids-recon/tests/test_guard_coverage.py:206: AssertionError: assert False</traceback>
      </failure>
    </failures>
  </pre_design_run>
  <failing_test_dispositions>
    <disposition test="test_a_guard_violation_is_blocking[dcm2niix_version_floor]" file="tests/test_guard_coverage.py" classification="obsolete-test">
      <intended_contract>A guard's violation must be BLOCKING: the exception must be one that __main__.py maps to a non-zero exit rather than letting the session silently proceed. The test's original mechanism for checking this (issubclass(guard.error, GuardError)) was written when GuardError was the only halting exception category in the codebase.</intended_contract>
      <current_test_claim>assert issubclass(guard.error, GuardError) — for dcm2niix_version_floor, guard.error is ToolVersionError, which errors.py places as a sibling of GuardError under BidsReconError, not a subclass.</current_test_claim>
      <evidence>fmri_bids_recon/__main__.py:120-130 documents a 5-way exit-code contract; lines 160-177 show GuardError -> exit 1 and ToolVersionError -> exit 4 as two independent, deliberate except clauses, both non-zero and neither falling through to the generic Exception handler. The dcm2niix_version_floor guard was repointed from the deprecated VersionFloorError(GuardError) to the production ToolVersionError(BidsReconError) earlier in this harmonization round, which is what exposed the gap between the test's literal check and the codebase's actual (broader) definition of "blocking".</evidence>
      <action>re-express: widened the assertion for this guard from issubclass(guard.error, GuardError) to issubclass(guard.error, (GuardError, ToolVersionError)), naming the second legitimate halting category explicitly rather than loosening to a generic BidsReconError check (which would also admit ConfigError, a genuinely different, non-blocking-in-the-same-sense failure mode). User explicitly approved this disposition over the alternative (making ToolVersionError inherit from GuardError, which would have silently changed __main__.py's exit code for tool-version failures from 4 to 1 via except-clause ordering, a production behavior change out of scope for a test fix).</action>
    </disposition>
  </failing_test_dispositions>
  <design_phase>
    <tests_created>1</tests_created>
    <tests_modified>1</tests_modified>
    <files_created>
      <file path="tests/test_tool_registry.py" test_count="1" coverage_target="Missing-flirt error message includes the FSLDIR/module-load hint" />
    </files_created>
    <design_rationale>Two edits, both scoped to the implement/build report's C8 (guard repoint) and C9 (deface->tool_registry FSLDIR hint migration) changes. The guard-coverage assertion was re-expressed per the disposition above. The FSLDIR-hint test closes a coverage gap: test_deface.py's test_assert_deface_tools_error_message_hints_at_fsldir_when_flirt_is_missing was deleted along with assert_deface_tools() in C9, but the hint text itself moved into tool_registry.py's preflight_tool_environments() without a replacement test following it. The pipeline.py hasattr-removal (C10) was checked and found not to need new coverage: resolve_labels() always returns a RegistryDelta instance by its own type signature, so the removed dict-branch was unreachable dead code, not a behavior change.</design_rationale>
  </design_phase>
  <post_design_run>
    <total>594</total>
    <passed>499</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct></coverage_pct>
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
