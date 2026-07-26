<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-24T16:00:00-04:00" />
  <input_reports>
    <report path="(conversation)" mode="discussion" key_items="1" />
  </input_reports>
  <assumptions_and_decisions>
    - The sanitization targets `sys.path` entries containing `pythonX.Y` where X.Y differs from the running interpreter. This is version-aware, not FSL-specific, and generalizes to any HPC module that contaminates PYTHONPATH.
    - In a clean environment (no contamination), the function finds nothing to strip and is a no-op.
    - `os.environ['PYTHONPATH']` is also sanitized so that subprocesses (e.g., pydeface invoking flirt) do not inherit foreign-version entries.
    - A module-level list captures stripped paths for deferred logging inside `main()`, after `logging.basicConfig()` has been called.
    - The sanitization is placed inline in `__main__.py` (not a separate module), since it is tightly coupled to the CLI entry point and adding a new file for 15 lines of code is unnecessary.
    - The walrus operator (`:=`) is used; this requires Python 3.8+, well within the `requires-python >= 3.12` floor.
    - The stale `dicom_pattern` reference in RUNBOOK.md (line 103) was observed during diagnosis but is out of scope for this plan. It should be addressed separately (e.g., via `/document`).
  </assumptions_and_decisions>
  <changes>
    <change id="C1" priority="P0" source_item="conversation: FSL PYTHONPATH contamination fix">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>Add _sanitize_sys_path() to strip foreign-version site-packages from sys.path and PYTHONPATH before any scientific library imports. Log stripped entries inside main() after logging is configured.</description>
      <spec>
        1. After `from __future__ import annotations` (line 10) and before the existing `import argparse` (line 12), insert:
           - `import os`
           - `import re`
           - `import sys`
           - A module-level `_STRIPPED_PATHS: list[str] = []`
           - Function `_sanitize_sys_path() -> None`:
             - Compile pattern `r'python(\d+\.\d+)'`
             - Build `current = f"{sys.version_info.major}.{sys.version_info.minor}"`
             - Collect `foreign`: entries in `sys.path` where pattern matches and captured version != current
             - Remove each foreign entry from `sys.path`, append to `_STRIPPED_PATHS`
             - If foreign entries were found AND `PYTHONPATH` is in `os.environ`: filter `PYTHONPATH` the same way; if all entries are foreign, `del os.environ["PYTHONPATH"]`; otherwise reassign with clean entries
           - Call `_sanitize_sys_path()` at module level (runs at import time, before any subsequent imports)

        2. Remove the duplicate `import sys` from the later import block (currently line 17), since `sys` is now imported at the top.

        3. Inside `main()`, immediately after `logging.basicConfig(...)` (line 111), insert:
           ```python
           if _STRIPPED_PATHS:
               logger.info(
                   'Sanitized sys.path: stripped %d foreign-version entr%s.',
                   len(_STRIPPED_PATHS),
                   'y' if len(_STRIPPED_PATHS) == 1 else 'ies',
               )
           ```
      </spec>
      <dependencies>none</dependencies>
      <risk>low - no-op in clean environments; only strips paths that would cause C-extension crashes anyway</risk>
      <rollback>Revert the three insertion sites in __main__.py and restore `import sys` to its original position.</rollback>
    </change>
  </changes>
  <execution_order>C1</execution_order>
  <observations>
    <observation>RUNBOOK.md line 103 still references `dicom_pattern` with `{sub}/{ses}` placeholders, which was renamed to `dicom_template` with `{subject}/{session}` in v1.1.0 (commit 44d1fea). This is a separate documentation issue, not addressed in this plan.</observation>
  </observations>
  <next_steps>Recommended: run /test to validate the change (unit tests for _sanitize_sys_path covering contaminated, clean, and PYTHONPATH-only scenarios).</next_steps>
</implement_plan>
