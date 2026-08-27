<test_report>
  <meta project="bids-recon" mode="test" timestamp="2026-08-27T16:40:08Z" />
  <pre_design_run>
    <total>639</total>
    <passed>544</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct>null</coverage_pct>
    <failures></failures>
  </pre_design_run>
  <failing_test_dispositions>
    <!-- No failures in the pre-design run; the disposition ledger is empty. -->
  </failing_test_dispositions>
  <design_phase>
    <tests_created>2</tests_created>
    <tests_modified>0</tests_modified>
    <files_created>
      <file path="tests/test_tool_registry.py" test_count="1 (added; file total unchanged in count of new files)" coverage_target="Adds test_default_lockfile_path_is_colocated_with_the_module: asserts _default_lockfile_path().parent equals the tool_registry module's own parent directory, directly encoding the co-location contract introduced by the lockfile-path fix (implement build 2026-08-27T16:31:36Z, changes C1/C2)." />
      <file path="tests/test_packaging.py" test_count="1" coverage_target="New file. test_pyproject_declares_tools_lock_yaml_as_package_data: parses pyproject.toml via tomllib and asserts tools.lock.yaml is declared under [tool.setuptools.package-data].fmri_bids_recon, guarding the packaging-manifest half of the fix (change C3)." />
    </files_created>
    <design_rationale>
      The pre-design run was clean (0 failures), so this cycle is proactive coverage for the
      just-implemented lockfile-path fix rather than disposition-ledger remediation. The prior
      test suite had a real gap: test_default_lockfile_path_points_at_the_project_root only
      asserted path.name and path.exists(), which cannot distinguish "resolves correctly because
      it is package-relative" from "resolves correctly by incidental dev-checkout directory
      structure" -- exactly the ambiguity that let the original bug ship (the pre-fix
      .parent.parent offset also pointed at an existing file in the dev tree, since the project
      root contained tools.lock.yaml at the time). The new colocation test asserts the path
      directly against the module's own directory, which was verified to fail under the pre-fix
      code even when run from the source checkout. The second new test closes a second,
      independent gap: no test previously verified the pyproject.toml package-data declaration
      itself, so a future accidental removal of that declaration would only surface as a runtime
      failure on an installed system, not in the test suite. A stronger integration-level test
      (building an actual wheel and inspecting its contents) was considered but not implemented
      in this cycle, because it requires installing the `build` package, which is not currently
      present in the bids-recon environment and requires explicit per-invocation approval before
      installation.
    </design_rationale>
  </design_phase>
  <post_design_run>
    <total>641</total>
    <passed>546</passed>
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
    <item priority="P2" target_mode="implement" description="Optional follow-up: install the `build` package (with explicit per-invocation approval) and add a wheel-build-and-inspect test that verifies tools.lock.yaml is physically present in the built distribution, as a stronger guarantee beyond the manifest-declaration check added this cycle." />
  </action_items>
</test_report>
