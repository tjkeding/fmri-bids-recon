<document_report>
  <meta project="bids-recon" mode="document" timestamp="2026-09-17T19:05:00Z" />
  <files_updated>
    <file path="README.md" changes="Added Phase 8 (group summary) to the Pipeline Stages table; added a Group Conversion Summary section describing the automatic, timestamped, non-blocking aggregation of per-subject reports; documented the 7 new optional config fields (scout_keywords, calibration_keywords, norm_tokens, expected_anat_count, registry_mode, label_freeze_mode, rename_detection); added advisory-mode notes to the no_label_drift, no_rename_collision, and exact_volume_counts guard rows; noted the group summary file in Output Structure.">
      <type>readme</type>
    </file>
    <file path="INPUT_SPECIFICATION.md" changes="Added 7 rows to the Optional Fields table (Section 1.2) with types, defaults, and full behavioral descriptions; split the calibration exclusion prose into fieldmap-calibration and anatomical-calibration subsections and added a NORM/ND twin resolution subsection (Section 2.2); added Section 6.1 (Group-Level Conversion Summary) documenting the 7-section .txt format, timestamped non-overwriting filenames, non-blocking behavior, and the FOLLOWUP_INSTRUCTIONS fallback; added two Known Limitations entries (lexicographic subject/session sort order; advisory-mode registry enforcement order-dependence in shared-registry batch runs); expanded the calibration keyword note in the existing Siemens-only limitation.">
      <type>input_spec</type>
    </file>
    <file path="RUNBOOK.md" changes="Added step 8 (group summary) to the pipeline run sequence; added the group conversion summary path to Output locations; added a pointer to INPUT_SPECIFICATION.md Section 1.2 for the new optional config fields in the config-preparation section.">
      <type>runbook</type>
    </file>
    <file path="config/study.example.yaml" changes="Added a new 'Classification and guard tuning' section with commented-out templates and inline documentation for all 7 new optional config fields, matching the file's existing comment style.">
      <type>config_template</type>
    </file>
    <file path="fmri_bids_recon/config.py" changes="Extended the StudyConfig docstring's Attributes section to document the 7 new fields (scout_keywords, calibration_keywords, norm_tokens, expected_anat_count, registry_mode, label_freeze_mode, rename_detection), including their downstream consumers and mode semantics. No functional code changed.">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/labels.py" changes="Extended the resolve_labels() docstring to document the label_freeze_mode and rename_detection keyword-only parameters and their frozen/re-derive and strict/warn/off behaviors. No functional code changed.">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/runs.py" changes="Extended the check_volume_counts() docstring to document the registry_mode keyword-only parameter and its strict/advisory behavior. No functional code changed.">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/stage2_classify.py" changes="Extended the classify() docstring to document the two-key anatomical calibration gate (expected_anat_count-driven) as distinct from the existing PE-axis fieldmap calibration pass, and to document the scout_keywords, calibration_keywords, norm_tokens, and expected_anat_count keyword-only parameters. No functional code changed.">
      <type>docstring</type>
    </file>
    <file path="fmri_bids_recon/stage4_assemble.py" changes="Added an inline comment above the excluded_sns guard explaining it is a defense-in-depth check independent of pipeline.py's upstream roles-dict deletion, not redundant dead code. No functional code changed.">
      <type>inline_comment</type>
    </file>
    <file path="fmri_bids_recon/pipeline.py" changes="Added an inline comment above the excluded_sns roles-dict deletion (Phase 1) explaining why it runs before Stage 3 and its relationship to stage4_assemble.py's independent guard. No functional code changed.">
      <type>inline_comment</type>
    </file>
    <file path="bids-recon_run-local_20260917_173400.md" changes="Security-gate remediation: replaced two repo-internal absolute paths (sandbox_path, run_directory) with repo-relative equivalents, and two conda tool-resolution paths with a &lt;conda_env&gt; placeholder preserving the env-relative remainder. Re-scanned clean after remediation.">
      <type>inline_comment</type>
    </file>
  </files_updated>
  <aid_log>
    <status>unchanged</status>
    <sections_modified></sections_modified>
  </aid_log>
  <security_gate>
    <dispatch_count>5</dispatch_count>
    <completed_after_retry>5</completed_after_retry>
    <retry_note>SG-2 through SG-5 initially failed on a session-level API rate limit (protocol failure, not a negative verdict); re-dispatched with identical payloads after the limit reset per the Agent Return Validation Gate doctrine's retry-same recovery path. All 5 completed on retry.</retry_note>
    <violations_found>4</violations_found>
    <violations_remediated>4</violations_remediated>
    <detail>
      All 4 violations were PII-tier, all confined to bids-recon_run-local_20260917_173400.md: 2 repo-internal absolute paths (sandbox_path, run_directory; found by all 5 agents) and 2 conda tool-resolution paths (found by 1 of 5 agents; retained per union-with-dedup). All 4 remediated per the CONVENTIONS.md remediation table (repo-relative equivalents for the absolute paths, &lt;conda_env&gt; placeholder for the conda paths) and re-scanned clean via a targeted orchestrator grep pass.
    </detail>
    <llm_attribution_findings>0</llm_attribution_findings>
  </security_gate>
  <coverage>
    <public_functions_documented>4/4 (resolve_labels, check_volume_counts, classify, StudyConfig)</public_functions_documented>
    <classes_documented>1/1 (StudyConfig)</classes_documented>
    <modules_with_docstrings>7/7 (config.py, labels.py, runs.py, stage2_classify.py, stage4_assemble.py, pipeline.py, group_report.py -- group_report.py required no changes, docstrings already complete from its implement:build pass)</modules_with_docstrings>
  </coverage>
  <summary>Documentation now reflects two previously undocumented, tested, uncommitted feature sets: (1) the config-schema generalizability work (7 new optional config fields; vendor-agnostic NORM/PURE/SCIC/CLEAR reconstruction-variant detection; expanded cross-vendor scout/calibration keyword vocabularies; the two-layer anatomical calibration demotion gate; advisory-mode toggles for the volume-count, label-drift, and rename-collision guards), and (2) the automatic, timestamped, non-blocking group-level conversion summary (Phase 8). README, INPUT_SPECIFICATION, RUNBOOK, and the example config template are all updated and cross-consistent; code docstrings and comments were extended (no functional code touched); the mandatory security gate found and remediated 4 PII violations confined to one run-local report, with zero LLM-attribution violations across all 29 scanned files.</summary>
</document_report>
