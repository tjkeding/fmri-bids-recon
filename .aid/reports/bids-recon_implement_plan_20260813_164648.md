<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-13T16:46:48Z" />
  <input_reports>
    <report path="bids-recon_brainstorm_20260813_160653.md" mode="brainstorm" key_items="5" />
  </input_reports>
  <changes>
    <change id="C1" priority="P0" source_item="T3 (logging harmonization, graded_warning)">
      <file path="fmri_bids_recon/warnings.py" action="create" />
      <description>Create the graded_warning() structured warning framework, adopted verbatim from fmri-preproc. This is a leaf dependency with no upstream requirements.</description>
      <spec>
Create new file `fmri_bids_recon/warnings.py` with:

```python
from __future__ import annotations

import logging

SEVERITY_WARN = "warn"
SEVERITY_CRITICAL = "strong"

def graded_warning(
    logger: logging.Logger,
    severity: str,
    code: str,
    message: str,
    *,
    user_facing: bool = False,
) -> dict:
    level = logging.WARNING if user_facing else logging.INFO
    prefix = f"[{severity}:{code}]"
    full_message = f"{prefix} {message}"
    logger.log(level, full_message)
    return {
        "severity": severity,
        "code": code,
        "message": message,
    }
```

Signature, return schema, and log-line format match fmri-preproc's `preproc_utils.py:graded_warning()` exactly. The `user_facing` flag controls log level (WARNING vs INFO); severity is a record tag only, not a log-level controller.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - new file, no existing code affected</risk>
      <rollback>Delete fmri_bids_recon/warnings.py</rollback>
    </change>

    <change id="C2" priority="P0" source_item="T1 (version verification, ToolSuiteRegistry)">
      <file path="tools.lock.yaml" action="create" />
      <file path="fmri_bids_recon/tool_registry.py" action="create" />
      <file path="fmri_bids_recon/errors.py" action="modify" />
      <description>Create the tools.lock.yaml lockfile and the tool_registry module implementing preflight_tool_environments(). Add ToolVersionError to the exception hierarchy.</description>
      <spec>
**tools.lock.yaml** (project root):

```yaml
schema_version: "1.0.0"
tools:
  dcm2niix:
    pin_class: A
    version: "1.0.20260416"
    binary: dcm2niix
    version_flag: "--version"
  pydeface:
    pin_class: B
    version: "2.1.0"
    binary: pydeface
    version_flag: "--version"
    conditional: deface
  flirt:
    pin_class: A
    version: "6.0.7.15"
    binary: flirt
    version_flag: "-version"
    conditional: deface
    enforcement: declarative
```

`pin_class: A` = exact match required (in strict mode) or floor-check with warning (in lenient mode). `pin_class: B` = minimum floor always. `conditional: deface` = only checked when `config.deface is True`. `enforcement: declarative` = mismatch produces a warning, never an error (FSL version is session-global, bids-recon cannot control it).

**fmri_bids_recon/tool_registry.py**:

```python
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import StudyConfig
from .errors import ToolVersionError

logger = logging.getLogger(__name__)

@dataclass
class ToolStatus:
    name: str
    pinned_version: str
    found_version: str | None
    pin_class: str          # "A" or "B"
    status: str             # "ok", "warning", "error", "skipped"
    message: str

@dataclass
class ToolReport:
    tools: dict[str, ToolStatus] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(t.status == "error" for t in self.tools.values())
```

Internal helpers (private):
- `_default_lockfile_path() -> Path`: returns `Path(__file__).resolve().parent.parent / 'tools.lock.yaml'`
- `_load_lockfile(path: Path) -> dict`: reads and parses the YAML lockfile
- `_parse_version(text: str, tool_name: str) -> tuple[int, ...]`: extracts a version tuple from tool output. For dcm2niix: regex `r"v(\d+)\.(\d+)\.(\d+)"` (reuses the parsing logic from versions.py). For pydeface: regex `r"(\d+)\.(\d+)\.(\d+)"`. For flirt: regex `r"FLIRT version (\d+)\.(\d+)"` or similar.
- `_probe_tool(name: str, binary: str, version_flag: str) -> str | None`: runs `[binary, version_flag]` via subprocess, returns raw output or None on failure.
- `_resolve_binary(name: str, binary: str) -> str | None`: for flirt, checks `$FSLDIR/bin/flirt` first (reuses logic from deface.py:_resolve_flirt()), falls back to `shutil.which(binary)`. For other tools, uses `shutil.which(binary)`.
- `_compare_versions(found: tuple, pinned: tuple, pin_class: str, strict: bool) -> tuple[str, str]`: returns `(status, message)`. Class A + strict: exact match required. Class A + lenient: floor-check with warning if found > pinned. Class B: floor-check always.

Public function:

```python
def preflight_tool_environments(
    config: StudyConfig,
    *,
    strict: bool = False,
    lockfile: Path | None = None,
) -> ToolReport:
```

Logic:
1. Load lockfile from `lockfile` parameter or `_default_lockfile_path()`.
2. For each tool entry in the lockfile:
   a. If `conditional` is set and the corresponding config attribute is False, set status="skipped" and continue.
   b. Resolve binary path via `_resolve_binary()`.
   c. If binary not found, set status="error" with message "not found on PATH".
   d. Probe version via `_probe_tool()`.
   e. Parse version via `_parse_version()`.
   f. Compare via `_compare_versions()` with the `strict` flag and the tool's `enforcement` field (declarative tools use warning, never error).
   g. Log result at INFO level.
3. If any tool has status="error", raise `ToolVersionError` with the full report.
4. Return `ToolReport`.

**fmri_bids_recon/errors.py** modification:

Add after `ToolUnavailableError`:

```python
class ToolVersionError(BidsReconError):
    """Installed tool version does not match the pinned version in tools.lock.yaml."""
```

Mark `VersionFloorError` with a deprecation note in its docstring (do not remove; test_versions.py still imports it):

```python
class VersionFloorError(GuardError):
    """dcm2niix version is below the verified minimum floor.

    Deprecated: replaced by ToolVersionError in tool_registry.py.
    Retained for backward compatibility with existing tests.
    """
```

Update the module docstring's exception tree to include ToolVersionError.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - new files plus a small additive change to errors.py</risk>
      <rollback>Delete tools.lock.yaml and fmri_bids_recon/tool_registry.py; revert errors.py</rollback>
    </change>

    <change id="C3" priority="P0" source_item="T4 (config schema versioning + 3-stage pipeline)">
      <file path="fmri_bids_recon/config.py" action="modify" />
      <description>Refactor the monolithic load_config() into a 3-stage private pipeline with load_and_validate() as the public API. Add schema_version and config_path fields to StudyConfig.</description>
      <spec>
**StudyConfig dataclass changes:**

Add two new fields after `deface`:

```python
schema_version: str = "1.0.0"
config_path: Path | None = None
```

`schema_version` defaults to "1.0.0" when absent from YAML (additive-growth policy). `config_path` stores the absolute path to the YAML file that was loaded; set by `_resolve_config()`, defaults to None for programmatic construction.

**Refactor load_config() into 3 private stages:**

`_load_raw(path: Path) -> dict`:
- Reads YAML file, returns raw dict.
- Raises `FileNotFoundError` if path does not exist.
- Body: lines 213-215 of current load_config (open + yaml.safe_load).

`_validate_raw(raw: dict) -> dict`:
- Schema validation, type checks, required field enforcement.
- Validates: bids_root, staging_root, dicom_root, dicom_template (placeholder checks), subjects (list or file path), sessions, physio, deface, schema_version.
- Calls `_validate_bids_label()`, `_validate_ses_label()`, duplicate-subject/session checks, staging-not-inside-bids guard.
- Returns the validated dict with all fields resolved to their correct Python types (but NOT yet converted to dataclass fields: paths are still strings, subjects is still a list, etc.).
- Body: lines 217-297 of current load_config.

`_resolve_config(validated: dict, *, subject: str | None = None, config_path: Path | None = None) -> StudyConfig`:
- Constructs the typed StudyConfig dataclass.
- Expands participants via subjects x sessions cross-product.
- When `subject` is not None, filters the subjects list to `[subject]` before expansion (single-subject mode for orchestrator use). If the provided subject is not in the original subjects list, raises `ConfigError`.
- Loads task_registry from sidecar file.
- Sets `config_path` on the returned StudyConfig.
- Body: lines 299-371 of current load_config.

**New public API function:**

```python
def load_and_validate(
    config_path: str | Path,
    *,
    subject: str | None = None,
) -> StudyConfig:
    path = Path(config_path)
    raw = _load_raw(path)
    validated = _validate_raw(raw)
    return _resolve_config(validated, subject=subject, config_path=path)
```

**Backward compatibility:**

Keep `load_config()` as a thin wrapper:

```python
def load_config(path: str | Path) -> StudyConfig:
    return load_and_validate(path)
```

This preserves backward compatibility for existing callers (tests, internal code). It will be removed in a future cleanup pass.

**Import updates:**

`__main__.py` currently imports `load_config` from config. No change needed yet; C6 will switch to `load_and_validate`.
      </spec>
      <dependencies>none</dependencies>
      <risk>medium - refactoring a 190-line function with many validation paths; thorough testing recommended after build</risk>
      <rollback>Revert config.py to prior state (single load_config function, no schema_version/config_path fields)</rollback>
    </change>

    <change id="C4" priority="P0" source_item="T3 (logging harmonization, ReviewFlag migration)">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <file path="fmri_bids_recon/runs.py" action="modify" />
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <file path="fmri_bids_recon/json_intermediate.py" action="modify" />
      <file path="fmri_bids_recon/report.py" action="modify" />
      <file path="fmri_bids_recon/errors.py" action="modify" />
      <description>Migrate all ReviewFlag usage to graded_warning() dicts. Retire the ReviewFlag class from errors.py. Update the JSON serialization layer and report consumer.</description>
      <spec>
**stage2_classify.py:**

- Replace import: `from .errors import AnatSuffixError, NavigatorDropError, ReviewFlag` becomes `from .errors import AnatSuffixError, NavigatorDropError` plus `from .warnings import graded_warning, SEVERITY_WARN`.
- Add `import logging` and `logger = logging.getLogger(__name__)` at module level.
- Change `classify()` return type annotation: `list[ReviewFlag]` becomes `list[dict]`.
- Line 324-334: replace `ReviewFlag(message, context={...})` with `graded_warning(logger, SEVERITY_WARN, "UNCLASSIFIED_SERIES", message)`. The context dict contents are folded into the message string (series_number, description, suffix are already in the message text).
- Line 348-360: same pattern, code `"NAVIGATOR_CANDIDATE"`.
- Line 373-385: same pattern, code `"AMBIGUOUS_CLASSIFICATION"`.
- All three sites use `user_facing=False` (INFO level; these are classification details, not operator-actionable warnings).

**runs.py:**

- Replace import: `from .errors import ReviewFlag` becomes `from .warnings import graded_warning, SEVERITY_WARN`.
- Add `import logging` and `logger = logging.getLogger(__name__)` at module level.
- Change `check_volume_counts()` return type: `list[ReviewFlag]` becomes `list[dict]`.
- Line 118-125: replace `ReviewFlag(message, {"code": "ambiguous_volume_mode"})` with `graded_warning(logger, SEVERITY_WARN, "VOLUME_COUNT_MISMATCH", message, user_facing=True)`. This is user-facing (WARNING level) because ambiguous volume counts require operator attention.
- Line 176-189: replace `ReviewFlag(message, {"task_label": ...})` with `graded_warning(logger, SEVERITY_WARN, "VOLUME_COUNT_DRIFT", message, user_facing=True)`.

**stage4_assemble.py:**

- Replace import: `from .errors import ReviewFlag, PhaseEncodingError` becomes `from .errors import PhaseEncodingError` plus `from .warnings import graded_warning, SEVERITY_WARN, SEVERITY_CRITICAL`.
- Add `import logging` and `logger = logging.getLogger(__name__)` at module level (if not already present).
- Change `AssembleResult.review_flags` type annotation: `list[ReviewFlag]` becomes `list[dict]`. Update the field docstring.
- Line 183: `review_flags: list[ReviewFlag] = []` becomes `review_flags: list[dict] = []`.
- Line 380-384: replace `ReviewFlag(message, {"code": "unpaired_fieldmap"})` with `graded_warning(logger, SEVERITY_WARN, "UNPAIRED_FIELDMAP", message, user_facing=True)`.
- Note: The brainstorm identified `PATIENT_ID_WARNING` at severity `"strong"`, but looking at the code, patient_id_warnings are handled via a separate `patient_id_warnings: list[str]` field on AssembleResult (line 53), not via ReviewFlag. So the `"strong"` severity applies to the patient_id_warnings rendering in the report, not to a ReviewFlag migration. The actual ReviewFlag site in assemble.py is the unpaired fieldmap warning at line 380.

**json_intermediate.py:**

- Remove import: `from .errors import ReviewFlag` (line 22).
- Remove ReviewFlag from the encoder (lines 40-48): delete the `isinstance(obj, ReviewFlag)` block. After migration, review_flags in the intermediate dict are plain dicts, which pass through the general dict encoding path natively.
- Remove ReviewFlag from the decoder (lines 132-134): delete the `tag == "ReviewFlag"` block.
- Note: Existing intermediate JSON files on disk with `__type__: "ReviewFlag"` tags will not decode correctly after this change. This is acceptable because intermediate files are ephemeral (per-run scratch) and are not persisted across pipeline invocations.

**report.py:**

- No import changes needed (ReviewFlag is not imported).
- Update `review_flags` parameter type hint from `list` to `list[dict]` (line 30).
- Update the docstring (line 58): "Collection of ReviewFlag instances" becomes "Collection of graded warning dicts with keys: severity, code, message."
- Update rendering logic (lines 162-163): replace `f"- {flag}"` with `f"- [{flag['severity']}:{flag['code']}] {flag['message']}"`.

**errors.py:**

- Mark `ReviewFlag` class as deprecated (add deprecation note to docstring). Do NOT delete the class yet; tests may still reference it. The class remains importable but is no longer instantiated by any production code.
      </spec>
      <dependencies>C1 (warnings.py must exist before graded_warning can be imported)</dependencies>
      <risk>medium - touches 6 files with 10 instantiation sites; type annotation changes propagate through function signatures</risk>
      <rollback>Revert all 6 files to prior state</rollback>
    </change>

    <change id="C5" priority="P0" source_item="T5 (Python API: BidsReconResult + run())">
      <file path="fmri_bids_recon/pipeline.py" action="create" />
      <description>Create the pipeline module containing BidsReconResult and run(). Extracts the core pipeline logic from __main__.py:main() into a programmatic API function that returns a typed result without calling sys.exit() or setting up logging.</description>
      <spec>
**fmri_bids_recon/pipeline.py:**

Imports (migrated from __main__.py):

```python
from __future__ import annotations

import datetime
import logging
import shutil
from collections import defaultdict
from pathlib import Path
from dataclasses import dataclass, field

from .config import StudyConfig, save_registry, load_and_validate
from .tool_registry import preflight_tool_environments, ToolReport
from .stage1_convert import convert_to_staging
from .sidecar import load_series
from .stage2_classify import classify, Role
from .labels import resolve_labels
from .runs import check_volume_counts, assign_run_indices
from .stage3_map import order_series, pair_fieldmaps, map_fieldmaps
from .physio import discover_native_physio, associate_native_physio, write_physio
from .stage4_assemble import assemble
from .stage5_render import render
from .stage6_validate import (
    assert_guards_executed, run_bids_validator, generate_cubids_report, ALL_GUARD_NAMES,
)
from .report import write_conversion_report
from .manifest import read_manifest, update_manifest, should_skip, ManifestEntry
from .deface import deface
from .json_intermediate import dump_intermediate, load_intermediate
from .errors import GuardError
```

**BidsReconResult dataclass:**

```python
@dataclass
class BidsReconResult:
    status: str                       # "success" | "warning" | "error"
    manifest_path: Path
    warnings: list[dict] = field(default_factory=list)
    participants_processed: list[str] = field(default_factory=list)
    bids_validation_errors: int = 0
    bids_validation_warnings: int = 0
    tool_report: ToolReport | None = None
```

**Helper functions** (migrated from __main__.py, made private):

- `_render_findings(findings) -> tuple[int, int]`: same as current `_render_findings()` but returns `(error_count, warning_count)` instead of None.
- `_migrate_manifest(bids_root, new_manifest_path)`: unchanged from current.

**run() function:**

```python
def run(
    config: StudyConfig,
    *,
    strict_versions: bool = False,
    config_path: Path | None = None,
) -> BidsReconResult:
```

`config_path` parameter: used for conversion report provenance. If None, falls back to `config.config_path` (set by `load_and_validate()`). If both are None, the report omits the config path.

Logic (extracted from __main__.py:main() lines 156-367):
1. Call `preflight_tool_environments(config, strict=strict_versions)`. Store as `tool_report`.
2. Set up manifest path: `bids_root / 'derivatives' / 'fmri-bids-recon' / 'manifest.tsv'`. Call `_migrate_manifest()`.
3. Phase 1-7 processing loop (identical to current main(), but collecting warnings as `list[dict]` instead of `list[ReviewFlag]`, and NOT calling `sys.exit()`).
4. Construct and return `BidsReconResult`:
   - `status`: "success" if no BIDS validation errors, "warning" if errors found, "error" never returned (errors raise exceptions).
   - `manifest_path`: absolute path to manifest.tsv.
   - `warnings`: all graded_warning dicts collected during processing.
   - `participants_processed`: list of `f"sub-{sub}_ses-{ses}"` strings for each participant that was processed (not skipped).
   - `bids_validation_errors`, `bids_validation_warnings`: counts from `_render_findings()`.
   - `tool_report`: the ToolReport from preflight.

**Exception behavior**: `run()` does NOT catch exceptions. `GuardError`, `ToolUnavailableError`, `ConfigError`, and `BidsReconError` propagate to the caller. `main()` catches them and maps to exit codes. The orchestrator catches them and maps to its own error handling.

**Key differences from current main():**
- No `logging.basicConfig()` call.
- No `argparse` usage.
- No `sys.exit()` calls.
- Returns `BidsReconResult` instead of exiting.
- `assert_dcm2niix_version()` replaced by `preflight_tool_environments()`.
- `assert_deface_tools()` replaced by the deface-conditional entries in `preflight_tool_environments()`.
- `version_str` (previously returned by `assert_dcm2niix_version()`) is now obtained from `tool_report.tools["dcm2niix"].found_version`.
      </spec>
      <dependencies>C2 (tool_registry.py for preflight and ToolReport), C3 (config.py for load_and_validate and config_path), C4 (ReviewFlag migration complete so warnings are list[dict])</dependencies>
      <risk>high - largest single change; extracts ~220 lines from main() into a new module with new return semantics</risk>
      <rollback>Delete fmri_bids_recon/pipeline.py</rollback>
    </change>

    <change id="C6" priority="P0" source_item="T5 (Python API: CLI refactoring), T3 (logging factory, --log-file)">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>Refactor main() into a thin CLI wrapper that calls load_and_validate() and run(). Add _setup_logging(), new CLI arguments (--config, --subject, --log-file, --strict-versions), and exit code documentation.</description>
      <spec>
**Imports** (replace current heavy import block):

```python
from __future__ import annotations

import os
import re
import sys

_STRIPPED_PATHS: list[str] = []

def _sanitize_sys_path() -> None:
    # unchanged from current

_sanitize_sys_path()

import argparse
import logging
from pathlib import Path

from .config import load_and_validate
from .pipeline import run
from .errors import GuardError, ConfigError, ToolUnavailableError, BidsReconError
from . import __version__

logger = logging.getLogger(__name__)
```

All stage-specific imports are removed (they live in pipeline.py now).

**_setup_logging() function:**

```python
def _setup_logging(log_file: Path | None = None) -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # idempotent guard

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file is not None:
        file_handler = logging.FileHandler(str(log_file))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    root.setLevel(logging.DEBUG)
```

**_build_parser() function** (rewritten):

```python
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fmri-bids-recon",
        description="DICOM-to-BIDS reconstruction pipeline (v{})".format(__version__),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {}".format(__version__),
    )
    parser.add_argument(
        "config_positional",
        nargs="?",
        default=None,
        metavar="CONFIG",
        help="Path to the study configuration YAML file (positional form).",
    )
    parser.add_argument(
        "--config",
        dest="config_named",
        default=None,
        metavar="PATH",
        help="Path to the study configuration YAML file (named form).",
    )
    parser.add_argument(
        "--subject",
        default=None,
        metavar="ID",
        help="Process only this subject (filters the config subjects list).",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        type=Path,
        metavar="PATH",
        help="Write DEBUG-level logs to this file (INFO to console).",
    )
    parser.add_argument(
        "--strict-versions",
        action="store_true",
        default=False,
        help="Enforce exact version matches for Class A tool pins.",
    )
    return parser
```

**main() function** (rewritten as thin wrapper):

```python
def main() -> None:
    """DICOM-to-BIDS reconstruction pipeline entry point.

    Exit codes (orchestrator contract):
        0 = Success (proceed to next stage)
        1 = Pipeline invariant violation / GuardError (stop, do not retry)
        2 = Config / input validation error (stop, user must fix config)
        3 = Completed with warnings (proceed, flag for QC review)
        4 = External tool unavailable or crashed (stop, environment issue)
    """
    parser = _build_parser()
    args = parser.parse_args()

    config_path = args.config_named or args.config_positional
    if config_path is None:
        parser.error("config path required (positional or --config)")

    _setup_logging(args.log_file)

    if _STRIPPED_PATHS:
        logger.info(
            "Sanitized sys.path: stripped %d foreign-version entr%s.",
            len(_STRIPPED_PATHS),
            "y" if len(_STRIPPED_PATHS) == 1 else "ies",
        )

    strict = args.strict_versions or os.environ.get(
        "FMRI_BIDS_RECON_STRICT_VERSIONS", ""
    ).lower() in ("1", "true", "yes")

    try:
        config = load_and_validate(config_path, subject=args.subject)
        result = run(config, strict_versions=strict)
        if result.status == "warning":
            sys.exit(3)
        sys.exit(0)
    except GuardError as exc:
        logger.error("Pipeline invariant violated: %s", exc, exc_info=True)
        sys.exit(1)
    except ToolUnavailableError as exc:
        logger.error("Tool unavailable, dataset is UNCHECKED: %s", exc)
        sys.exit(4)
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(2)
    except BidsReconError as exc:
        logger.error("Pipeline error: %s", exc)
        sys.exit(2)
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        sys.exit(2)
```

Note: `ToolVersionError` (from C2) is a subclass of `BidsReconError`, so it falls through to the `BidsReconError` handler (exit code 2). If the orchestrator needs a distinct exit code for version mismatches in the future, a new handler can be added.

The `strict` flag checks both the CLI argument and the `FMRI_BIDS_RECON_STRICT_VERSIONS` environment variable (either-one-true semantics).

**Removed from __main__.py:**
- `_render_findings()` (moved to pipeline.py)
- `_migrate_manifest()` (moved to pipeline.py)
- All stage-specific imports (moved to pipeline.py)
- All pipeline logic from the current main() (moved to run() in pipeline.py)
- Import of `assert_dcm2niix_version` from versions
- Import of `assert_deface_tools` from deface
      </spec>
      <dependencies>C3 (load_and_validate in config.py), C5 (run() in pipeline.py)</dependencies>
      <risk>high - complete rewrite of main(); dual-form CLI argument parsing adds complexity</risk>
      <rollback>Revert __main__.py to prior state; requires reverting C5 as well</rollback>
    </change>

    <change id="C7" priority="P0" source_item="T5 (public API exports), T2 (exit code documentation)">
      <file path="fmri_bids_recon/__init__.py" action="modify" />
      <description>Update __init__.py to export the public API functions and types. Exit code documentation is embedded in main()'s docstring (C6).</description>
      <spec>
**fmri_bids_recon/__init__.py** (rewritten):

```python
__version__ = '0.1.0'

from .config import load_and_validate
from .pipeline import run, BidsReconResult
```

This makes the public API importable as:
- `from fmri_bids_recon import load_and_validate, run, BidsReconResult`
- `from fmri_bids_recon.config import load_and_validate`
- `from fmri_bids_recon.pipeline import run, BidsReconResult`

The exit code documentation is handled in C6 (main()'s docstring).
      </spec>
      <dependencies>C3 (load_and_validate exists), C5 (run and BidsReconResult exist), C6 (main() docstring written)</dependencies>
      <risk>low - small additive change</risk>
      <rollback>Revert __init__.py to prior state (__version__ only)</rollback>
    </change>
  </changes>
  <execution_order>C1, C2, C3, C4, C5, C6, C7</execution_order>
</implement_plan>
