<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-08-27T17:20:45Z" />
  <spec_ref>fmri-bids-recon_implement_plan_20260827_171845.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__init__.py" lines_changed="25" />
      </files_modified>
      <notes>Inserted _sanitize_sys_path() and _STRIPPED_PATHS at the top of __init__.py, before __version__ and all package imports. The guard now runs at package initialization time, before the from .pipeline import triggers the nibabel/numpy import chain.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" lines_changed="20" />
      </files_modified>
      <notes>Removed _STRIPPED_PATHS declaration, _sanitize_sys_path() definition, and _sanitize_sys_path() call. Added _STRIPPED_PATHS to the existing `from . import __version__` line. The `import re` was also removed since __main__.py no longer uses the re module.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="tests/test_sanitize_sys_path.py" lines_changed="22" />
      </files_modified>
      <notes>Changed import from `from fmri_bids_recon import __main__ as cli` to `import fmri_bids_recon as pkg`. All references to `cli._sanitize_sys_path` and `cli._STRIPPED_PATHS` updated to `pkg._sanitize_sys_path` and `pkg._STRIPPED_PATHS`. No test logic or assertion changes.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>3</total_changes>
    <completed>3</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate all changes.</next_steps>
</implement_report>
