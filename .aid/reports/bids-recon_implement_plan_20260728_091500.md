<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-28T09:15:00-04:00" />
  <input_reports>
    <report path="(session discussion: FSL PATH circular dependency debugging)" mode="session" key_items="5" />
    <report path="(session resume: P2 items from 2026-07-26 session memory)" mode="resume" key_items="4" />
  </input_reports>
  <assumptions>
    <assumption>The repository owner username in repository URLs is not PII. The user confirmed this was a false positive from prior security gates: the username is required for users to install the package from its public repository.</assumption>
    <assumption>nipype's FSLCommand interface resolves flirt via PATH lookup at subprocess execution time. The _ensure_fsl_env() strategy of appending $FSLDIR/bin to PATH is therefore sufficient to make flirt reachable to pydeface's internal nipype calls, regardless of nipype version.</assumption>
    <assumption>FSLOUTPUTTYPE=NIFTI_GZ is the correct default for pydeface/nipype when the variable is unset. This matches nipype's own internal default.</assumption>
  </assumptions>
  <changes>
    <change id="C1" priority="P0" source_item="session discussion: FSL PATH circular dependency">
      <file path="fmri_bids_recon/deface.py" action="modify" />
      <description>Resolve FSL flirt via $FSLDIR environment variable instead of PATH-only lookup. Eliminates the circular PATH ordering problem between conda and FSL on HPC clusters.</description>
      <spec>
        1. Add `import os` to the import block.

        2. Add helper `_resolve_flirt() -> str | None`:
           - Read `os.environ.get("FSLDIR")`
           - If set, check `Path(fsl_dir) / "bin" / "flirt"` exists (`.is_file()`)
           - If that file exists, return its string path
           - Otherwise fall back to `shutil.which("flirt")`
           - Return None if neither resolution succeeds

        3. Rewrite `assert_deface_tools()`:
           - Check pydeface via `shutil.which("pydeface")` (unchanged)
           - Check flirt via `_resolve_flirt()` (replaces `shutil.which("flirt")`)
           - Build missing list from both checks
           - If "flirt" is in missing, append an FSLDIR-specific hint to the error message:
             " Set the FSLDIR environment variable (e.g. via 'module load FSL') or add FSL's bin directory to PATH."
           - Update docstring to describe FSLDIR resolution order
           - Return type remains None; signature unchanged

        4. Add helper `_ensure_fsl_env() -> None`:
           - Read `os.environ.get("FSLDIR")`; return immediately if not set
           - Compute `fsl_bin = str(Path(fsl_dir) / "bin")`
           - If `fsl_bin` not in `os.environ.get("PATH", "").split(os.pathsep)`:
             - APPEND (not prepend) `fsl_bin` to PATH: `os.environ["PATH"] = current + os.pathsep + fsl_bin`
             - Log: `logger.info("Appended %s to PATH for FSL tool access.", fsl_bin)`
           - If `"FSLOUTPUTTYPE" not in os.environ`:
             - Set `os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"`
           - Docstring: explain purpose (ensure pydeface/nipype can find flirt without requiring users to source fsl.sh)

        5. In `deface()`: add `_ensure_fsl_env()` call immediately after the tool validation check (after `if tool not in ...` block, before the `output_paths` initialization).
      </spec>
      <dependencies>none</dependencies>
      <risk>low - backward compatible; if FSLDIR is unset, behavior is identical to current. Appending (not prepending) to PATH avoids shadowing conda's dcm2niix.</risk>
      <rollback>Revert deface.py to prior version (git checkout).</rollback>
    </change>

    <change id="C2" priority="P1" source_item="session discussion: stale 'on PATH' docstring">
      <file path="fmri_bids_recon/config.py" action="modify" />
      <description>Update the deface field docstring to describe FSLDIR-based resolution instead of "on PATH".</description>
      <spec>
        Lines 106-108, replace:
          ```
          deface : bool
              Whether to run the defacing stage.  Defaults to False.  Requires
              ``pydeface`` and FSL ``flirt`` on PATH; the pipeline verifies both
              at startup when this flag is True.
          ```
        With:
          ```
          deface : bool
              Whether to run the defacing stage.  Defaults to False.  Requires
              ``pydeface`` (installed via pip) and FSL ``flirt``; the pipeline
              resolves ``flirt`` via the ``FSLDIR`` environment variable (falling
              back to PATH lookup) and verifies both tools at startup when this
              flag is True.
          ```
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - docstring only, no behavior change</risk>
      <rollback>Revert config.py docstring.</rollback>
    </change>

    <change id="C3" priority="P2" source_item="P2 from 2026-07-26 session: .gitignore pattern too broad">
      <file path=".gitignore" action="modify" />
      <description>Fix .gitignore pattern from `bids-recon_*.md` (matches anywhere in tree, catches .aid/reports/) to `/bids-recon_*.md` (root-only match).</description>
      <spec>
        Line 15, replace:
          `bids-recon_*.md`
        With:
          `/bids-recon_*.md`
      </spec>
      <dependencies>none</dependencies>
      <risk>low - only narrows the ignore scope; .aid/reports/ files will no longer require `git add -f`</risk>
      <rollback>Revert .gitignore line.</rollback>
    </change>

    <change id="C4" priority="P1" source_item="session discussion: README GitHub URLs are placeholders, FSL description stale">
      <file path="README.md" action="modify" />
      <description>Fix GitHub URL placeholders from &lt;org&gt; to the repository owner username. Update FSL prerequisite and dependency table to describe FSLDIR resolution.</description>
      <spec>
        1. Line 33, replace:
             `- **FSL** (any version): required only if the \`deface\` stage is enabled (\`deface: true\` in the study config). Specifically, \`flirt\` must be on PATH. FSL must be installed separately; it is not included in the conda environment.`
           With:
             `- **FSL** (any version): required only if the \`deface\` stage is enabled (\`deface: true\` in the study config). The pipeline resolves \`flirt\` via the \`FSLDIR\` environment variable (e.g., set by \`module load FSL\` on HPC clusters), falling back to PATH lookup. FSL must be installed separately; it is not included in the conda environment.`

        2. Line 43, replace:
             `pip install git+https://github.com/&lt;org&gt;/fmri-bids-recon.git`
           With:
             `pip install git+https://github.com/tjkeding/fmri-bids-recon.git`

        3. Line 49, replace:
             `git clone https://github.com/&lt;org&gt;/fmri-bids-recon.git`
           With:
             `git clone https://github.com/tjkeding/fmri-bids-recon.git`

        4. Line 172, replace:
             `| pydeface | 2.1.0 | Anatomical defacing (requires FSL \`flirt\` on PATH) |`
           With:
             `| pydeface | 2.1.0 | Anatomical defacing (requires FSL \`flirt\` via \`FSLDIR\` or PATH) |`
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - text only</risk>
      <rollback>Revert README.md edits.</rollback>
    </change>

    <change id="C5" priority="P1" source_item="session discussion: INPUT_SPECIFICATION FSL description stale">
      <file path="INPUT_SPECIFICATION.md" action="modify" />
      <description>Update all deface/FSL references to describe FSLDIR-based resolution instead of PATH-only.</description>
      <spec>
        1. Line 27, replace:
             `| \`deface\` | boolean | \`false\` | Enable anatomical defacing via pydeface. When true, the pipeline verifies that both \`pydeface\` and FSL \`flirt\` are on PATH at startup (pre-flight check) and halts immediately if either is absent. Defaced copies are written to \`derivatives/defaced/\`; the analysis \`anat/\` directories are never modified. |`
           With:
             `| \`deface\` | boolean | \`false\` | Enable anatomical defacing via pydeface. When true, the pipeline resolves \`flirt\` via the \`FSLDIR\` environment variable (falling back to PATH lookup) and verifies both \`pydeface\` and \`flirt\` at startup. Halts immediately if either is absent. Defaced copies are written to \`derivatives/defaced/\`; the analysis \`anat/\` directories are never modified. |`

        2. Line 125, replace:
             `| pydeface | 2.1.0 | Anatomical defacing (requires FSL \`flirt\` at runtime) |`
           With:
             `| pydeface | 2.1.0 | Anatomical defacing (requires FSL \`flirt\` via \`FSLDIR\` or PATH) |`

        3. Line 135, replace:
             `| FSL \`flirt\` | any | Hard when \`deface: true\` (pre-flight check halts pipeline); stage skipped when \`deface: false\` (default). | Required only when the deface stage is enabled. Must be installed separately. |`
           With:
             `| FSL \`flirt\` | any | Hard when \`deface: true\` (pre-flight check halts pipeline); stage skipped when \`deface: false\` (default). | Required only when the deface stage is enabled. Must be installed separately. Resolved via the \`FSLDIR\` environment variable (e.g., \`module load FSL\`), with PATH fallback. |`

        4. Line 204, replace:
             `4. **Defacing requires FSL**: the \`pydeface\` package is a Python wrapper around FSL's \`flirt\`. When \`deface: true\` is set in the study config, the pipeline verifies that both \`pydeface\` and \`flirt\` are on PATH at startup and halts immediately if either is absent.`
           With:
             `4. **Defacing requires FSL**: the \`pydeface\` package is a Python wrapper around FSL's \`flirt\`. When \`deface: true\` is set in the study config, the pipeline resolves \`flirt\` via the \`FSLDIR\` environment variable (falling back to PATH lookup) and verifies both tools at startup. On HPC clusters using environment modules, \`module load FSL\` sets \`FSLDIR\`; no additional PATH manipulation or \`source fsl.sh\` is required.`
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - text only</risk>
      <rollback>Revert INPUT_SPECIFICATION.md edits.</rollback>
    </change>

    <change id="C6" priority="P0" source_item="P2 items from 2026-07-26 (stale reference, HPC guidance) + session debugging + GitHub URL placeholder">
      <file path="RUNBOOK.md" action="modify" />
      <description>Fix stale dicom_pattern reference, fix GitHub URL placeholder, and add comprehensive HPC deployment section documenting the install/run separation, FSLDIR resolution, and contamination guards. This section codifies the debugging workflow from this session so trainees do not repeat it.</description>
      <spec>
        1. Line 39, replace:
             `git clone https://github.com/&lt;org&gt;/fmri-bids-recon.git &lt;CODE_DIR&gt;`
           With:
             `git clone https://github.com/tjkeding/fmri-bids-recon.git &lt;CODE_DIR&gt;`

        2. Line 103, replace:
             `dicom_pattern: '{sub}/{ses}'                      # path pattern under dicom_root`
           With:
             `dicom_template: '{subject}/{session}'             # path template under dicom_root`

        3. After Section 6 ("First-run caveat") and before the Quick Reference, insert a new Section 7: "HPC Deployment (Module-Based Environments)". Content:

           ## 7. HPC Deployment (Module-Based Environments)

           On HPC clusters where software is provided via environment modules (e.g.,
           &lt;cluster-name&gt;), the install and run sequences must be separated to
           avoid PATH and PYTHONPATH contamination between the conda environment and
           FSL's bundled Python packages.

           ### 7.1 Install (once)

           Do NOT load FSL during installation. The FSL module adds its own Python 3.11
           site-packages to the environment, which causes pip to either (a) fail with
           permission errors when upgrading FSL-owned packages, or (b) silently skip
           installation of Python 3.12 wheels for packages FSL already provides (numpy,
           scipy, pandas), resulting in ABI-incompatible C extensions at runtime.

           ```bash
           module load miniconda
           conda create -n fmri-bids-recon python=3.12 -y
           conda activate fmri-bids-recon
           pip install git+https://github.com/tjkeding/fmri-bids-recon.git
           ```

           If your home directory quota is insufficient for the conda environment, create
           it on a project or scratch filesystem using the `-p` flag instead of `-n`:

           ```bash
           conda create -p /path/to/project/<group>/<user>/envs/fmri-bids-recon python=3.12 -y
           conda activate /path/to/project/<group>/<user>/envs/fmri-bids-recon
           pip install git+https://github.com/tjkeding/fmri-bids-recon.git
           ```

           ### 7.2 Run

           Load FSL before activating the conda environment. The pipeline uses the
           `FSLDIR` environment variable (set by `module load FSL`) to locate `flirt`;
           you do NOT need to run `source $FSLDIR/etc/fslconf/fsl.sh`.

           ```bash
           module load FSL
           conda activate fmri-bids-recon
           fmri-bids-recon <CONFIG>
           ```

           The `conda activate` step must come AFTER `module load FSL` so that the conda
           environment's `bin/` directory takes priority on PATH. This ensures the
           pipeline uses the pip-installed `dcm2niix` (version >= 1.0.20260416) rather
           than any older system copy.

           ### 7.3 How the pipeline handles module contamination

           Two guards protect against HPC module contamination at runtime:

           1. **sys.path sanitization** (`_sanitize_sys_path()` in `__main__.py`): at
              startup, strips foreign-version Python site-packages entries (e.g., FSL's
              Python 3.11 paths injected into a Python 3.12 environment) from `sys.path`
              and `PYTHONPATH` before scientific library imports. Version-aware and
              generalizes to any module that injects foreign-version paths. Complete no-op
              in clean environments.

           2. **FSLDIR-based tool resolution** (`deface.py`): resolves `flirt` via
              `$FSLDIR/bin/flirt` rather than PATH lookup, avoiding the circular PATH
              conflicts that arise when conda and FSL bin directories shadow each
              other's binaries. At deface time, appends `$FSLDIR/bin` to PATH so that
              pydeface's internal nipype calls can also find `flirt`.

           These guards mean that a simple `module load FSL` followed by
           `conda activate` is sufficient. No manual PATH manipulation, environment
           variable exports, or FSL shell configuration scripts are required.

        4. Renumber the current "Quick reference" section from (unnumbered / implicit 7) to Section 8.

        5. In the Quick Reference section, add an HPC variant block after the existing commands:

           ```bash
           # HPC clusters (module-based FSL):
           module load miniconda
           conda create -n fmri-bids-recon python=3.12 -y
           conda activate fmri-bids-recon
           pip install git+https://github.com/tjkeding/fmri-bids-recon.git

           # Per reconstruction (HPC):
           module load FSL
           conda activate fmri-bids-recon
           fmri-bids-recon <CONFIG>
           ```
      </spec>
      <dependencies>C1 (FSLDIR resolution must be implemented before documenting it)</dependencies>
      <risk>low - documentation only; the stale dicom_pattern reference is a text fix</risk>
      <rollback>Revert RUNBOOK.md edits.</rollback>
    </change>
  </changes>
  <execution_order>C1, C3, C2, C4, C5, C6</execution_order>
  <notes>
    - C1 is the core code change; all documentation changes (C2, C4, C5, C6) depend on it being implemented first so that documentation describes actual behavior.
    - C3 (.gitignore) is independent and can execute at any point.
    - Existing deface tests in tests/test_deface.py monkeypatch shutil.which and will need new test cases for the FSLDIR resolution path (_resolve_flirt, _ensure_fsl_env). Recommend /test after build to design and run those tests.
    - The 20 stale session-bound grants (P2 #4 from the prior session) are an infrastructure cleanup item, not a codebase change; they should be handled via /end-session grant review rather than /implement.
  </notes>
</implement_plan>
