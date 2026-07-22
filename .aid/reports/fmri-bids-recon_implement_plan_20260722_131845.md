<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-22T13:18:45Z" />
  <input_reports>
    <report path="fmri-bids-recon_document_20260722_125128.md" mode="document" key_items="8" />
  </input_reports>

  <!-- Only P0 and P1 items with target_mode="implement" are in scope.
       P2 items with target_mode="document" are deferred to /document. -->

  <changes>

    <!-- ================================================================= -->
    <!-- C1: Create pyproject.toml                                         -->
    <!-- ================================================================= -->
    <change id="C1" priority="P0" source_item="P0 item 1 (pyproject.toml creation)">
      <file path="pyproject.toml" action="create" />
      <description>Create a PEP 621-compliant pyproject.toml that enables pip-installable distribution and provides a console entry point. The environment.yml remains the canonical deployment spec for conda-based server installs; pyproject.toml enables `pip install -e .` for development and GitHub-based distribution.</description>
      <spec>
Create pyproject.toml at the project root with the following content:

```toml
[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"

[project]
name = "fmri-bids-recon"
dynamic = ["version"]
description = "DICOM-to-BIDS reconstruction pipeline"
requires-python = ">=3.12"
dependencies = [
    "pydicom>=3.0.1",
    "nibabel>=5.3.2",
    "numpy>=1.26.4",
    "pyyaml>=6.0.2",
    "cubids>=1.1.0",
    "pydeface>=2.1.0",
    "dcm2niix>=1.0.20260416",
    "bids-validator-deno>=3.0.0",
]

[project.scripts]
fmri-bids-recon = "fmri_bids_recon.__main__:main"

[tool.setuptools.dynamic]
version = {attr = "fmri_bids_recon.__version__"}

[tool.setuptools.packages.find]
include = ["fmri_bids_recon*"]
```

Notes:
- `dynamic = ["version"]` reads `__version__` from `fmri_bids_recon/__init__.py` (currently `'0.1.0'`).
- `[project.scripts]` creates a console entry point `fmri-bids-recon` that invokes `fmri_bids_recon.__main__:main`.
- `dcm2niix` and `bids-validator-deno` are CLI tools distributed as pip wheels; listing them under `dependencies` ensures `pip install` fetches them.
- Version specifiers use `>=` (minimum compatible) rather than `==` (pinned). The `environment.yml` pins exact versions for reproducible conda deployments; pyproject.toml declares the floor for pip-based installs.
- `[tool.setuptools.packages.find]` includes only `fmri_bids_recon*` to exclude `tests/`, `tools/`, etc.
      </spec>
      <dependencies>none</dependencies>
      <risk>low — new file creation; no existing state affected</risk>
      <rollback>Delete pyproject.toml</rollback>
    </change>

    <!-- ================================================================= -->
    <!-- C2: Rename package directory                                      -->
    <!-- ================================================================= -->
    <change id="C2" priority="P0" source_item="P0 item 2 (directory rename)">
      <file path="fmri_bids_recon/" action="modify" />
      <description>Rename the Python package directory from fmri_bids_recon/ to fmri_bids_recon/. All internal imports use relative form (from .module import ...) and require no changes. This change blocks all subsequent edits to files within the package (C3, C4, C5) because their paths change.</description>
      <spec>
Execute: `mv fmri_bids_recon fmri_bids_recon`

Verify: `ls fmri_bids_recon/__init__.py` returns successfully.

The __pycache__/ directory inside the renamed package will contain stale .pyc files keyed to the old module path. These are harmless (Python will regenerate them on next import) but can be cleaned: `find fmri_bids_recon/__pycache__ -name "*.pyc" -delete 2>/dev/null; true`
      </spec>
      <dependencies>none</dependencies>
      <risk>medium — renames the primary package directory; all absolute imports break until C8 updates them. Rollback is a single mv command.</risk>
      <rollback>mv fmri_bids_recon fmri_bids_recon</rollback>
    </change>

    <!-- ================================================================= -->
    <!-- C3: Update __main__.py functional references                      -->
    <!-- ================================================================= -->
    <change id="C3" priority="P1" source_item="P1 items 1-2 (__main__.py prog and derivatives path)">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>Update the argparse prog value and the BIDS derivatives directory path in __main__.py.</description>
      <spec>
Two edits in fmri_bids_recon/__main__.py:

1. Line 85: change `prog="fmri_bids_recon"` to `prog="fmri-bids-recon"` (hyphenated, matching the console entry point).

2. Line 135: change `bids_root / 'derivatives' / 'fmri-bids-recon' / 'manifest.tsv'` to `bids_root / 'derivatives' / 'fmri-bids-recon' / 'manifest.tsv'`.
      </spec>
      <dependencies>C2</dependencies>
      <risk>low — two string literal edits; no logic change</risk>
      <rollback>Revert strings to 'fmri_bids_recon' and 'fmri-bids-recon'</rollback>
    </change>

    <!-- ================================================================= -->
    <!-- C4: Update report.py functional references                        -->
    <!-- ================================================================= -->
    <change id="C4" priority="P1" source_item="P1 items 2-3 (report.py derivatives path and engine version)">
      <file path="fmri_bids_recon/report.py" action="modify" />
      <description>Update the BIDS derivatives directory path and the engine version label in report.py.</description>
      <spec>
Two edits in fmri_bids_recon/report.py:

1. Line 75: change `bids_root / "derivatives" / "fmri-bids-recon"` to `bids_root / "derivatives" / "fmri-bids-recon"`.

2. Line 93: change `"- **fmri-bids-recon engine version**: {engine_version}"` to `"- **fmri-bids-recon engine version**: {engine_version}"`.
      </spec>
      <dependencies>C2</dependencies>
      <risk>low — two string literal edits; no logic change</risk>
      <rollback>Revert strings to 'fmri-bids-recon'</rollback>
    </change>

    <!-- ================================================================= -->
    <!-- C5: Update tsv.py lock file prefix                                -->
    <!-- ================================================================= -->
    <change id="C5" priority="P1" source_item="P1 item 4 (tsv.py lock file)">
      <file path="fmri_bids_recon/tsv.py" action="modify" />
      <description>Update the lock file name prefix from fmri_bids_recon to fmri_bids_recon.</description>
      <spec>
One edit in fmri_bids_recon/tsv.py:

Line 40: change `f"bids_recon_{digest}.lock"` to `f"fmri_bids_recon_{digest}.lock"`.
      </spec>
      <dependencies>C2</dependencies>
      <risk>low — string literal edit in lock file name; no logic change</risk>
      <rollback>Revert string to 'fmri_bids_recon'</rollback>
    </change>

    <!-- ================================================================= -->
    <!-- C6: Update environment.yml                                        -->
    <!-- ================================================================= -->
    <change id="C6" priority="P1" source_item="P1 item 5 (environment.yml)">
      <file path="environment.yml" action="modify" />
      <description>Update the conda environment name and header comment to use fmri-bids-recon.</description>
      <spec>
Two edits in environment.yml:

1. Line 1: change `# Conda environment for the fmri-bids-recon DICOM-to-BIDS pipeline.` to `# Conda environment for the fmri-bids-recon DICOM-to-BIDS pipeline.`

2. Line 7: change `name: fmri-bids-recon` to `name: fmri-bids-recon`.
      </spec>
      <dependencies>none</dependencies>
      <risk>low — two string edits in a configuration file; no logic change. Existing fmri-bids-recon conda environments on the server will need to be recreated as fmri-bids-recon.</risk>
      <rollback>Revert strings to 'fmri-bids-recon'</rollback>
    </change>

    <!-- ================================================================= -->
    <!-- C7: Update config/study.example.yaml                              -->
    <!-- ================================================================= -->
    <change id="C7" priority="P1" source_item="P1 item 6 (config template)">
      <file path="config/study.example.yaml" action="modify" />
      <description>Update the header comment to use fmri-bids-recon.</description>
      <spec>
One edit in config/study.example.yaml:

Line 1: change `# study.example.yaml — fmri-bids-recon study configuration template` to `# study.example.yaml — fmri-bids-recon study configuration template`.
      </spec>
      <dependencies>none</dependencies>
      <risk>low — comment-only edit</risk>
      <rollback>Revert string to 'fmri-bids-recon'</rollback>
    </change>

    <!-- ================================================================= -->
    <!-- C8: Update test imports                                           -->
    <!-- ================================================================= -->
    <change id="C8" priority="P1" source_item="P1 item 7 (test imports)">
      <file path="tests/" action="modify" />
      <description>Update all absolute imports across 20 test files and conftest.py from fmri_bids_recon to fmri_bids_recon. Also update the sys.path comment in conftest.py that directly describes the import being changed.</description>
      <spec>
Bulk find-and-replace across all files in tests/:

1. Replace all `from fmri_bids_recon.` with `from fmri_bids_recon.` (import statements).
2. Replace all `from fmri_bids_recon import` with `from fmri_bids_recon import` (import statements).
3. Replace all `import bids_recon` with `import fmri_bids_recon` (bare imports, e.g., test_validate.py:28).

Files affected (21 total):
  tests/conftest.py (lines 29, 32, 33, 481, 482, 483)
  tests/test_classify.py (lines 18, 19)
  tests/test_sidecar.py (line 17)
  tests/test_convert.py (lines 28, 29)
  tests/test_tsv.py (lines 17, 139)
  tests/test_manifest.py (line 19)
  tests/test_report.py (lines 15, 16, 17, 18)
  tests/test_versions.py (lines 16, 17)
  tests/test_physio.py (lines 35, 36)
  tests/test_config.py (lines 18, 19)
  tests/test_labels.py (lines 14, 20, 26)
  tests/test_cli_integration.py (lines 26, 27, 28, 29, 30, 31, 32, 33, 34)
  tests/test_render.py (lines 21, 22, 23, 24)
  tests/test_validate.py (lines 28, 29, 30)
  tests/test_map.py (lines 17, 18, 19, 25, 454, 455)
  tests/test_assemble.py (lines 19, 20, 21, 22, 23)
  tests/test_runs.py (line 14)
  tests/test_guard_coverage.py (lines 27, 38)
  tests/test_deface.py (lines 25, 26)
  tests/test_json_intermediate.py (lines 18, 19, 20, 26, 27, 28, 29, 30, 31)

Additionally in conftest.py:
  Line 29 comment: change `# Allow \`import bids_recon\`` to `# Allow \`import fmri_bids_recon\``
      </spec>
      <dependencies>C2</dependencies>
      <risk>medium — touches 21 files; but every edit is a mechanical string replacement with no logic change. Risk is mitigated by the fact that any missed or incorrect replacement will produce an ImportError on test execution, making failures immediately detectable via /test.</risk>
      <rollback>Reverse the find-and-replace (fmri_bids_recon → fmri_bids_recon)</rollback>
    </change>

  </changes>

  <execution_order>
    Phase 1 (independent): C1, C2, C6, C7
    Phase 2 (depends on C2): C3, C4, C5, C8
  </execution_order>

</implement_plan>
