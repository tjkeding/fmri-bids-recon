<document_report>
  <meta project="fmri-bids-recon" mode="document" timestamp="2026-07-22T14:40:46Z" />

  <files_updated>
    <file path="fmri_bids_recon/__main__.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/json_intermediate.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/errors.py" changes="Module docstring and BidsReconError class docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/deface.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/config.py" changes="Module docstring and StudyConfig class docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/labels.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'; Sphinx cross-ref: ~fmri_bids_recon.config.TaskRegistryEntry to ~fmri_bids_recon.config.TaskRegistryEntry">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/report.py" changes="Module docstring and engine_version parameter docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/physio.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/stage2_classify.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'; 3 Sphinx cross-refs: ~fmri_bids_recon.sidecar.Series, ~fmri_bids_recon.sidecar.load_series, ~fmri_bids_recon.errors.ReviewFlag to ~fmri_bids_recon equivalents">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/manifest.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'; Sphinx cross-ref: ~fmri_bids_recon.tsv.upsert_tsv to ~fmri_bids_recon.tsv.upsert_tsv">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/runs.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/stage3_map.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/stage4_assemble.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/stage5_render.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/stage6_validate.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/sidecar.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/versions.py" changes="Module docstring: 'fmri-bids-recon' to 'fmri-bids-recon'">
      <type>docstring</type>
    </file>
    <file path="README.md" changes="Revised Installation (pip install from GitHub + local editable), Usage (entry point instead of PYTHONPATH), conda env name (fmri-bids-recon), derivatives path (fmri-bids-recon)">
      <type>readme</type>
    </file>
    <file path="RUNBOOK.md" changes="Title, package directory refs, deployment instructions (pip install -e . + entry point), derivatives paths, conda env name, quick reference, line 149 'scrubbed sidecars' to 'JSON sidecars'">
      <type>readme</type>
    </file>
    <file path="INPUT_SPECIFICATION.md" changes="Created. Exhaustive input schema: config YAML fields, validation rules, DICOM requirements, environment deps, geometry tolerances, exit codes, output structure, known limitations.">
      <type>input_spec</type>
    </file>
    <file path="AID_LOG.md" changes="Created from AID Framework template (Weaver, 2025). Sections 1, 3, 6, 7 from template; Sections 2, 4, 5 project-specific.">
      <type>aid_log</type>
    </file>
    <file path=".aid/project_claude.md" changes="Created. Sanitized extract of project-relevant AI development directives (no local paths, usernames, or environment identifiers).">
      <type>aid_log</type>
    </file>
    <file path=".aid/reports/" changes="Directory created (empty; populated by archiving development reports).">
      <type>aid_log</type>
    </file>
  </files_updated>

  <aid_log>
    <status>created</status>
    <sections_modified>All sections (1-7) authored from template; Version History section omitted (managed by /publish).</sections_modified>
  </aid_log>

  <coverage>
    <public_functions_documented>All public functions have docstrings (pre-existing; no new functions added this invocation)</public_functions_documented>
    <classes_documented>All classes have docstrings (pre-existing; updated name references)</classes_documented>
    <modules_with_docstrings>18/18</modules_with_docstrings>
  </coverage>

  <pii_screening>
    <status>passed</status>
    <files_scanned>AID_LOG.md, INPUT_SPECIFICATION.md, .aid/project_claude.md, README.md, RUNBOOK.md, all 17 modified source files</files_scanned>
    <hits>1 false positive: RUNBOOK.md line 23 references 'miniconda' as a generic module-load example (instructional, not a local path). No remediation needed.</hits>
  </pii_screening>

  <llm_attribution_scrub>
    <status>passed</status>
    <files_scanned>AID_LOG.md, INPUT_SPECIFICATION.md, .aid/project_claude.md, README.md, RUNBOOK.md</files_scanned>
    <hits>1 false positive: INPUT_SPECIFICATION.md line 87 'written by dcm2niix' describes software tool output behavior, not authorship attribution. No remediation needed.</hits>
  </llm_attribution_scrub>

  <summary>Documentation is now complete for GitHub publication. All 18 module docstrings and 5 Sphinx cross-references updated from fmri-bids-recon/fmri_bids_recon to fmri-bids-recon/fmri_bids_recon. README.md revised for pip-installable distribution (entry point invocation, conda env name). RUNBOOK.md updated with all name references and stale 'scrubbed sidecars' fix. INPUT_SPECIFICATION.md created with exhaustive input schema. AID_LOG.md created per the AID Framework (Weaver, 2025). .aid/ directory structure created with sanitized project_claude.md. PII Screening Gate and LLM-Attribution Scrub Gate both passed.</summary>

</document_report>
