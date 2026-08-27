<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-27T17:18:45Z" />
  <input_reports>
    <report path="(conversation)" mode="bug-report" key_items="1" />
  </input_reports>
  <assumptions>
    <assumption id="A1">The _sanitize_sys_path() function body is relocated verbatim; no logic changes.</assumption>
    <assumption id="A2">The test import update is an import-path change only; existing assertions and fixtures remain untouched.</assumption>
  </assumptions>
  <changes>
    <change id="C1" priority="P0" source_item="production-bug: FSL sys.path contamination bypasses guard due to __init__.py import chain">
      <file path="fmri_bids_recon/__init__.py" action="modify" />
      <description>
        Move _sanitize_sys_path() and _STRIPPED_PATHS from __main__.py to the top of __init__.py,
        before any imports that can trigger the nibabel/numpy chain. This ensures the guard runs
        at package initialization time, before the entry point's `from fmri_bids_recon.__main__
        import main` triggers __init__.py's `from .pipeline import run, BidsReconResult`.
      </description>
      <spec>
        Insert at the very top of __init__.py (before __version__ and before from .config / from .pipeline):

        import os
        import re
        import sys

        _STRIPPED_PATHS: list[str] = []

        def _sanitize_sys_path() -> None:
            [verbatim function body from __main__.py lines 21-33]

        _sanitize_sys_path()

        Then the existing lines follow:
        __version__ = '1.0.0'
        from .config import load_and_validate
        from .pipeline import run, BidsReconResult
      </spec>
      <dependencies>none</dependencies>
      <risk>low - the function only uses re, os, sys (standard library, immune to contamination); the logic is unchanged</risk>
      <rollback>Revert __init__.py to its prior 4-line form</rollback>
    </change>
    <change id="C2" priority="P0" source_item="production-bug: complement to C1">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>
        Remove _STRIPPED_PATHS declaration, _sanitize_sys_path() definition, and _sanitize_sys_path()
        call from __main__.py. Add `from . import _STRIPPED_PATHS` to the existing import block so
        the logging code on lines 140-145 still has access to the list.
      </description>
      <spec>
        1. Remove line 17: `_STRIPPED_PATHS: list[str] = []`
        2. Remove lines 20-33: the entire _sanitize_sys_path() function definition
        3. Remove the blank line after the function and line 36: `_sanitize_sys_path()`
        4. On the existing `from . import __version__` line, change to:
           `from . import __version__, _STRIPPED_PATHS`

        The remaining code (logging on lines 140-145) references _STRIPPED_PATHS as a bare name,
        which will resolve to the imported package-level list (same object, since Python lists are
        mutable references).
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - removing code and adding one import; the reference semantics are unchanged</risk>
      <rollback>Restore the removed lines from git</rollback>
    </change>
    <change id="C3" priority="P0" source_item="test-import update for C1/C2 relocation">
      <file path="tests/test_sanitize_sys_path.py" action="modify" />
      <description>
        Update the test module's import to reference the new location of _sanitize_sys_path and
        _STRIPPED_PATHS (now on fmri_bids_recon, not fmri_bids_recon.__main__). This is an
        import-path change only; all test logic, assertions, and fixtures remain untouched.
      </description>
      <spec>
        1. Change line 20 from:
             `from fmri_bids_recon import __main__ as cli`
           to:
             `import fmri_bids_recon as pkg`
        2. Replace all occurrences of `cli._sanitize_sys_path` with `pkg._sanitize_sys_path`
        3. Replace all occurrences of `cli._STRIPPED_PATHS` with `pkg._STRIPPED_PATHS`

        No assertion logic changes. The fixture's save/restore of _STRIPPED_PATHS and sys.path
        continues to work identically because it operates on the same list object via the new
        import path.
      </spec>
      <dependencies>C1, C2</dependencies>
      <risk>low - import path change only; no test logic modifications</risk>
      <rollback>Revert the import and name references</rollback>
    </change>
  </changes>
  <execution_order>C1, C2, C3</execution_order>
</implement_plan>
