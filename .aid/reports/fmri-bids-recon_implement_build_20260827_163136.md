<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-08-27T16:31:36Z" />
  <spec_ref>fmri-bids-recon_implement_plan_20260827_161903.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="tools.lock.yaml" lines_changed="0 (moved, not deleted)" />
        <file path="fmri_bids_recon/tools.lock.yaml" lines_changed="0 (moved, content unchanged)" />
      </files_modified>
      <notes>Moved via `mv`. Content verified unchanged (437 bytes, lockfile_version 1.0.0, three binaries: dcm2niix, pydeface, flirt).</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/tool_registry.py" lines_changed="1" />
      </files_modified>
      <notes>Removed one ".parent" from the path chain in _default_lockfile_path(). Verified by direct import: _default_lockfile_path() now resolves to fmri_bids_recon/tools.lock.yaml and the file loads successfully with the expected lockfile_version and binary keys.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="pyproject.toml" lines_changed="3" />
      </files_modified>
      <notes>Added [tool.setuptools.package-data] section declaring fmri_bids_recon = ["tools.lock.yaml"], placed immediately after [tool.setuptools.packages.find].</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>3</total_changes>
    <completed>3</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate all changes, including a pip-install-context regression check for the lockfile resolution path.</next_steps>
</implement_report>
