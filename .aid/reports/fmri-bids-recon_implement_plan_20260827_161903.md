<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-27T16:19:03Z" />
  <input_reports>
    <report path="(conversation)" mode="bug_report" key_items="1" />
  </input_reports>
  <assumptions>
    <assumption>No external tooling or user workflow depends on tools.lock.yaml living at the project root. The file is consumed exclusively by tool_registry._default_lockfile_path() and by tests that pass explicit fixture paths.</assumption>
    <assumption>The test function name test_default_lockfile_path_points_at_the_project_root does not need renaming, because the assertions (path.name == "tools.lock.yaml" and path.exists()) are invariant to the file's parent directory. The function name is cosmetically inaccurate after this change, but renaming test functions is a test-mode concern, not a production bug fix.</assumption>
  </assumptions>
  <changes>
    <change id="C1" priority="P0" source_item="production bug: FileNotFoundError on pip-installed lockfile">
      <file path="tools.lock.yaml" action="delete" />
      <file path="fmri_bids_recon/tools.lock.yaml" action="create" />
      <description>Move tools.lock.yaml from the project root into the fmri_bids_recon package directory. The file is a runtime dependency of tool_registry.preflight_tool_environments(), so it must be co-located with the package code to survive pip installation. The file content is unchanged; only its location moves.</description>
      <spec>
        mv tools.lock.yaml fmri_bids_recon/tools.lock.yaml

        Git will track this as a rename. No content changes.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - file move only, no content change. All tests that use the lockfile either call _default_lockfile_path() (which is fixed in C2) or pass an explicit tmp_path fixture.</risk>
      <rollback>mv fmri_bids_recon/tools.lock.yaml tools.lock.yaml</rollback>
    </change>
    <change id="C2" priority="P0" source_item="production bug: _default_lockfile_path resolves to site-packages parent">
      <file path="fmri_bids_recon/tool_registry.py" action="modify" />
      <description>Fix _default_lockfile_path() to resolve the lockfile relative to the package directory (Path(__file__).parent) instead of the project root (Path(__file__).parent.parent). After C1 moves the lockfile into the package directory, .parent is the correct resolution in both development (repo checkout) and installed (site-packages) contexts.</description>
      <spec>
        Line 46, change:
          return Path(__file__).resolve().parent.parent / "tools.lock.yaml"
        to:
          return Path(__file__).resolve().parent / "tools.lock.yaml"

        Single token change: remove one ".parent" from the chain.
      </spec>
      <dependencies>C1 (the lockfile must be in the package directory before this path change takes effect)</dependencies>
      <risk>low - one-token change to a path resolution function. Both development and installed contexts resolve correctly because the lockfile will be in the same directory as tool_registry.py in both cases.</risk>
      <rollback>Restore ".parent.parent" in the path chain (but only meaningful if C1 is also rolled back).</rollback>
    </change>
    <change id="C3" priority="P0" source_item="production bug: lockfile not included in pip distribution">
      <file path="pyproject.toml" action="modify" />
      <description>Declare tools.lock.yaml as package data so setuptools includes it in the distribution. Without this, pip install copies only .py files from fmri_bids_recon/, and the lockfile would still be absent in site-packages even after C1 moves it into the package directory.</description>
      <spec>
        Add the following section after [tool.setuptools.packages.find]:

        [tool.setuptools.package-data]
        fmri_bids_recon = ["tools.lock.yaml"]

        This tells setuptools to include the specific YAML file when building the distribution.
      </spec>
      <dependencies>C1 (the file must exist in fmri_bids_recon/ for the package-data declaration to match)</dependencies>
      <risk>low - additive pyproject.toml section. Does not alter any existing build behavior. Only adds one non-Python file to the distribution.</risk>
      <rollback>Remove the [tool.setuptools.package-data] section from pyproject.toml.</rollback>
    </change>
  </changes>
  <execution_order>C1, C2, C3 (C2 and C3 both depend on C1; C2 and C3 are independent of each other and could execute in parallel)</execution_order>
</implement_plan>
