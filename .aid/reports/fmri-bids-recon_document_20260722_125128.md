<document_report>
  <meta project="fmri-bids-recon" mode="document" timestamp="2026-07-22T12:51:28Z" />

  <summary>
    Documentation was deferred at the user's request pending codebase changes
    (package rename to fmri-bids-recon, pyproject.toml creation). This report
    enumerates every change required before documentation can proceed, organized
    so that the action_items section can be passed directly to /implement plan.
  </summary>

  <files_updated>
    <file path="fmri_bids_recon/stage4_assemble.py" changes="Line 224: stale comment 'unscrubbed' changed to 'original'">
      <type>inline_comment</type>
    </file>
<file path="README.md" changes="Draft created; will need revision after package rename">
      <type>readme</type>
    </file>
  </files_updated>

  <aid_log>
    <status>not_applicable</status>
    <sections_modified>Deferred pending codebase changes</sections_modified>
  </aid_log>

  <coverage>
    <public_functions_documented>n/a (deferred)</public_functions_documented>
    <classes_documented>n/a (deferred)</classes_documented>
    <modules_with_docstrings>18/18</modules_with_docstrings>
  </coverage>

  <action_items>

    <!-- ================================================================= -->
    <!-- P0: FUNCTIONAL INFRASTRUCTURE (blocks all downstream work)        -->
    <!-- ================================================================= -->

    <item priority="P0" target_mode="implement" description="Create pyproject.toml for the fmri-bids-recon package. Required fields: (1) project name 'fmri-bids-recon', (2) package directory (currently fmri_bids_recon/, will become fmri_bids_recon/ after C2), (3) console entry point fmri-bids-recon mapping to the package __main__:main, (4) Python requires >=3.12, (5) dependencies mirroring environment.yml pip section (pydicom==3.0.1, nibabel==5.3.2, numpy==1.26.4, pyyaml==6.0.2, cubids==1.1.0, pydeface==2.1.0), (6) version read from __init__.__version__. Note: dcm2niix and bids-validator-deno are CLI tools installed via pip wheels but are runtime dependencies, not importable Python packages; they should be listed under project.dependencies (pip will install them) but may require special handling. environment.yml remains the canonical deployment spec for conda-based server installs; pyproject.toml enables pip install for development and GitHub-based distribution." />

    <item priority="P0" target_mode="implement" description="Rename Python package directory: fmri_bids_recon/ to fmri_bids_recon/. All internal imports use relative form (from .module import ...) and require NO changes. The following absolute references require updating (see P1 items below for specifics). The tests/ directory imports fmri_bids_recon by absolute name and will also need updating, but tests/ is not published; the user should decide whether to update tests now or defer." />

    <!-- ================================================================= -->
    <!-- P1: NAME ALIGNMENT (depends on P0 directory rename)               -->
    <!-- ================================================================= -->

    <!-- FUNCTIONAL CODE CHANGES (logic/output affected) -->

    <item priority="P1" target_mode="implement" description="__main__.py line 85: change prog='fmri_bids_recon' to the new package name. DECISION NEEDED: should prog be 'fmri_bids_recon' (matching the Python import) or 'fmri-bids-recon' (matching the repo/project name and console entry point)? The prog value appears in --help output and error messages." />

    <item priority="P1" target_mode="implement" description="__main__.py line 135 and report.py line 75: the BIDS derivatives directory is currently 'derivatives/fmri-bids-recon/'. DECISION NEEDED: should this become 'derivatives/fmri-bids-recon/' to match the new project name? Changing it affects the output BIDS tree structure and would be incompatible with datasets assembled under the old name. Options: (a) change to fmri-bids-recon for consistency, (b) keep fmri-bids-recon as the derivatives pipeline name since it's a BIDS convention identifier, not a Python package reference." />

    <item priority="P1" target_mode="implement" description="report.py line 93: the conversion report text says 'fmri-bids-recon engine version'. Update to match whatever derivatives-directory decision is made above." />

    <item priority="P1" target_mode="implement" description="tsv.py line 40: the lock file path uses f'bids_recon_{digest}.lock'. Update the prefix to the new package name (fmri_bids_recon)." />

    <!-- ENVIRONMENT / CONFIGURATION -->

    <item priority="P1" target_mode="implement" description="environment.yml: (1) line 1 comment says 'fmri-bids-recon DICOM-to-BIDS pipeline', update to 'fmri-bids-recon'. (2) line 7 name field is 'fmri-bids-recon'. DECISION NEEDED: should the conda environment name change to 'fmri-bids-recon'? Changing it means existing environments must be recreated. The environment name is referenced in the README and RUNBOOK." />

    <item priority="P1" target_mode="implement" description="config/study.example.yaml line 1: header comment says 'fmri-bids-recon study configuration template'. Update to 'fmri-bids-recon'." />

    <!-- TEST SUITE (NOT PUBLISHED, but functional) -->

    <item priority="P1" target_mode="implement" description="tests/ directory: 20 test files import from fmri_bids_recon by absolute name (e.g., 'from fmri_bids_recon.stage4_assemble import ...'). After the directory rename, every import must change to 'from fmri_bids_recon...'. conftest.py also imports from fmri_bids_recon. DECISION NEEDED: update tests now (recommended, keeps suite runnable) or defer?" />

    <!-- DOCUMENTATION-ONLY (handled by /document after rename) -->

    <item priority="P2" target_mode="document" description="Module docstrings: 13 modules contain 'for fmri-bids-recon' in their module-level docstring (config.py, deface.py, errors.py, json_intermediate.py, labels.py, manifest.py, physio.py, report.py, runs.py, sidecar.py, stage2_classify.py, stage4_assemble.py, versions.py). Three additional modules reference it differently: stage1_convert.py, stage3_map.py, stage5_render.py, stage6_validate.py, __main__.py. Update all to 'fmri-bids-recon' after rename." />

    <item priority="P2" target_mode="document" description="Sphinx-style cross-references: 4 occurrences of '~fmri_bids_recon.' in docstrings (manifest.py:98, labels.py:149, stage2_classify.py:3 and 141-149). Update to '~fmri_bids_recon.' after rename." />

    <item priority="P2" target_mode="document" description="README.md (already drafted): revise after rename to reflect final package name, entry point command, and conda environment name. Currently references 'python -m fmri_bids_recon' and 'conda activate fmri-bids-recon'." />

    <item priority="P2" target_mode="document" description=".gitignore (already created): review after rename; current rules reference 'fmri-bids-recon_*.md' pattern which is correct for the development report files." />

    <item priority="P2" target_mode="document" description="RUNBOOK.md line 149: stale reference 'scrubbed sidecars' (should be 'JSON sidecars'). RUNBOOK is internal only (not published) but should be corrected for accuracy. 15 total references to fmri-bids-recon/fmri_bids_recon in RUNBOOK that would need updating after rename." />

    <item priority="P2" target_mode="document" description="Create INPUT_SPECIFICATION.md, AID_LOG.md, and .aid/ directory structure (deferred from this session pending codebase changes)." />

  </action_items>

  <!-- ================================================================= -->
  <!-- OPEN DESIGN DECISIONS (must be resolved before /implement plan)    -->
  <!-- ================================================================= -->

  <open_decisions>
    <decision id="D1" description="Should the BIDS derivatives directory change from 'derivatives/fmri-bids-recon/' to 'derivatives/fmri-bids-recon/'? Affects backward compatibility with existing datasets." />
    <decision id="D2" description="Should the conda environment name change from 'fmri-bids-recon' to 'fmri-bids-recon'? Affects existing installations." />
    <decision id="D3" description="Should the argparse prog value be 'fmri_bids_recon' (Python import name) or 'fmri-bids-recon' (project/entry-point name)?" />
    <decision id="D4" description="Should tests/ imports be updated as part of this rename (recommended) or deferred?" />
  </open_decisions>

</document_report>
