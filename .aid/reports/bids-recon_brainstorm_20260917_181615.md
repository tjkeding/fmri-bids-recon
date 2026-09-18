<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-09-17T18:16:15+00:00" />
  <context_files>
    <file path="fmri_bids_recon/report.py" relevance="Current per-subject conversion report generator; defines the Markdown structure the group summary will parse" />
    <file path="fmri_bids_recon/pipeline.py" relevance="Pipeline run() function; the group summary generation phase will be added after Phase 7 (CUBIDS)" />
    <file path="fmri_bids_recon/warnings.py" relevance="Graded warning framework; defines severity taxonomy and accumulator used by all warning codes" />
    <file path="fmri_bids_recon/stage2_classify.py" relevance="Source of classification-stage warning codes (ANAT_CALIBRATION_DEMOTION, DUPLICATE_MODALITY, NAVIGATOR_CANDIDATE, etc.)" />
    <file path="fmri_bids_recon/runs.py" relevance="Source of volume-count warning codes (ABORTED_RUN_DETECTED, REGISTRY_VOLUME_MISMATCH, VOLUME_COUNT_DRIFT)" />
    <file path="fmri_bids_recon/labels.py" relevance="Source of label-resolution warning codes (LABEL_DRIFT_ADVISORY, TASK_RENAME_ADVISORY)" />
    <file path="fmri_bids_recon/stage3_map.py" relevance="Source of fieldmap-mapping warning codes (ABSENT_PE_DIRECTION, ODD_FIELDMAP_COUNT, FIELDMAP_COVERAGE_GAP, etc.)" />
    <file path="fmri_bids_recon/stage4_assemble.py" relevance="Source of assembly warning code (PATIENT_ID_MISMATCH)" />
    <file path="fmri_bids_recon/__main__.py" relevance="CLI entry point; defines exit code contract (0/1/2/3/4)" />
  </context_files>
  <topics>
    <topic id="T1" title="Generation mechanism">
      <summary>The group-level conversion summary is generated automatically at the end of every pipeline.run() invocation, not via a separate CLI command or optional flag. A new phase (after Phase 7/CUBIDS) reads all existing sub-*_ses-*_conversion_report.md files in derivatives/fmri-bids-recon/ and writes the group summary as a complete file. Every per-subject invocation regenerates the summary from whatever reports exist at that point. The last subject to finish in a batch produces the definitive version. Concurrency-safe because each process writes the complete file (not appending) and content is derived deterministically from per-subject reports already written atomically via Path.write_text().</summary>
      <research>None required; design grounded in codebase architecture analysis.</research>
      <approaches>
        <approach id="A1" label="Post-hoc CLI subcommand" feasibility="high" risk="low">
          <description>A separate --summarize flag or subcommand that reads all per-subject reports and generates the group summary.</description>
          <pros>Fully decoupled from pipeline execution; no impact on per-subject hot path.</pros>
          <cons>Requires an extra manual step after every run; user explicitly rejected this ("should be done every time fmri-bids-recon is run").</cons>
        </approach>
        <approach id="A2" label="Inline generation at end of run()" feasibility="high" risk="low">
          <description>New phase at end of pipeline.run() reads all existing per-subject conversion reports and writes the group summary. Runs on every invocation automatically.</description>
          <pros>No extra step required; always up to date; concurrency-safe (full rewrite, not append); deterministic output from existing reports.</pros>
          <cons>Adds a small amount of I/O at the end of each run (reading all existing reports). Negligible for realistic study sizes.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A2">User explicitly required automatic generation on every run, rejecting any flag or config gating.</decision>
    </topic>
    <topic id="T2" title="Content architecture">
      <summary>The group summary contains 7 sections in plain text (.txt) format: (1) Run Overview: compact table with one row per subject/session showing warning counts by severity and excluded-run status. (2) Action Required: all HIGH-severity findings grouped by subject/session with plain-language follow-up instructions. (3) Warnings for Review: all MEDIUM and LOW-severity findings with follow-up instructions. (4) Excluded Runs: table of every excluded run across all subjects. (5) Unclassified Series: table of every series that did not enter the BIDS tree. (6) Auto-Registered Tasks: table of all new task labels auto-registered during this batch. (7) Provenance: engine version, dcm2niix version, config path, list of aggregated per-subject reports.</summary>
      <research>None required; design grounded in existing per-subject report structure and user requirements.</research>
      <approaches>
        <approach id="A1" label="Markdown format" feasibility="high" risk="low">
          <description>Same .md format as per-subject reports.</description>
          <pros>Consistent with per-subject reports; renders well in GitHub/editors.</pros>
          <cons>User specified .txt or .json; Markdown was not requested.</cons>
        </approach>
        <approach id="A2" label="Plain text format" feasibility="high" risk="low">
          <description>.txt file with clear section headers, fixed-width tables, and indented blocks.</description>
          <pros>Maximally human-readable; no rendering dependencies; meets user requirement of "NOT cryptic" and "easily human readable."</pros>
          <cons>No rich formatting (bold, links); tables require fixed-width alignment.</cons>
        </approach>
        <approach id="A3" label="JSON format" feasibility="high" risk="low">
          <description>Structured JSON for machine parsing.</description>
          <pros>Machine-parseable; integrates with downstream tooling.</pros>
          <cons>Poor for human scanning; does not meet "easily human readable" requirement for a review document.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A2">User specified .txt or .json and approved plain text as the recommended format. 7-section layout approved as proposed.</decision>
    </topic>
    <topic id="T3" title="Follow-up instruction taxonomy">
      <summary>A static dictionary in the report module maps each (severity, code) pair to a plain-language follow-up instruction. The complete inventory of 21 warning codes was extracted from the codebase. HIGH-severity codes (13) appear in the "Action Required" section. MEDIUM-severity codes (8) and LOW-severity codes (2) appear in the "Warnings for Review" section. Each instruction tells the reviewer exactly what to check and where, grounded in what the warning code means mechanistically.</summary>
      <research>None required; warning codes extracted directly from codebase grep of all graded_warning() call sites.</research>
      <approaches>
        <approach id="A1" label="Static dictionary lookup" feasibility="high" risk="low">
          <description>A Python dictionary mapping (severity, code) to follow-up instruction string. Maintained alongside the warning code definitions.</description>
          <pros>Deterministic; every code gets a reviewed instruction; adding a new code requires adding a new instruction (good discipline).</pros>
          <cons>Requires manual update when new codes are added.</cons>
        </approach>
        <approach id="A2" label="Dynamic instruction generation from message text" feasibility="med" risk="med">
          <description>Parse the warning message text to generate follow-up instructions dynamically.</description>
          <pros>No maintenance when new codes are added.</pros>
          <cons>Fragile; depends on message format stability; cannot produce domain-specific follow-up guidance without understanding the code semantics.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Static dictionary with full code coverage. HIGH codes in Action Required section; MEDIUM and LOW codes in Warnings for Review section. Full taxonomy approved by user as presented.</decision>
    </topic>
    <topic id="T4" title="File location, naming, and lifecycle">
      <summary>The group summary is written to derivatives/fmri-bids-recon/group_conversion_summary_{YYYYMMDD_HHMMSS}.txt with a UTC timestamp. Each invocation creates a new timestamped file; previous summaries remain for historical reference, providing a timeline of the study's state as subjects are collected over time. The file is a derived artifact containing no information beyond what is in the per-subject reports, with added aggregation and follow-up instructions.</summary>
      <research>None required; design grounded in user workflow requirements.</research>
      <approaches>
        <approach id="A1" label="Fixed filename (overwrite)" feasibility="high" risk="low">
          <description>group_conversion_summary.txt, overwritten on every invocation.</description>
          <pros>Simple; always one file.</pros>
          <cons>No history; cannot compare state across collection waves. User explicitly rejected this in favor of timestamped files.</cons>
        </approach>
        <approach id="A2" label="Timestamped filename (accumulate)" feasibility="high" risk="low">
          <description>group_conversion_summary_{YYYYMMDD_HHMMSS}.txt, new file per invocation.</description>
          <pros>Full history; supports longitudinal data collection workflows where subjects are added over time; each file is a snapshot of the study state at that point.</pros>
          <cons>Directory accumulates files over time (manageable; one per pipeline invocation).</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A2">Timestamped filenames to support longitudinal collection workflows. User specified this requirement explicitly.</decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P0" target_mode="implement" description="Create group_report.py module with: (1) FOLLOWUP_INSTRUCTIONS dictionary mapping all 21 (severity, code) pairs to plain-language follow-up text, (2) parse_conversion_report() function to extract structured data from per-subject Markdown reports, (3) write_group_summary() function that globs all per-subject reports, aggregates them into the 7-section plain-text format, and writes group_conversion_summary_{timestamp}.txt. Add a new Phase 8 call to pipeline.run() after Phase 7 (CUBIDS) that invokes write_group_summary()." />
    <item priority="P0" target_mode="test" description="Test the group summary generator: (1) unit tests for parse_conversion_report() against representative per-subject report content covering all 7 sections (empty and populated variants), (2) unit tests for FOLLOWUP_INSTRUCTIONS completeness (every code emitted by graded_warning in the codebase has a corresponding entry), (3) integration test for write_group_summary() with 2+ parsed reports verifying all 7 output sections, (4) test that the follow-up instruction for each HIGH-severity code appears in the Action Required section and MEDIUM/LOW codes appear in Warnings for Review." />
  </action_items>
  <next_steps>Proceed to /implement to build the group_report.py module and integrate it into pipeline.run(). Follow with /test to validate the new functionality.</next_steps>
</brainstorm_report>
