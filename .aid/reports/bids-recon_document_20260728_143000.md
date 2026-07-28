<document_report>
  <meta project="bids-recon" mode="document" timestamp="2026-07-28T14:30:00-04:00" />
  <files_updated>
    <file path="README.md" changes="Added 'Running on HPC Systems' section after Installation, before Configuration. Contains Install (one-time) and Run (each reconstruction) subsections with explicit module load ordering, -p flag variant for project-filesystem conda environments, and description of the two runtime guards (sys.path sanitization, FSLDIR-based tool resolution).">
      <type>readme</type>
    </file>
    <file path="INPUT_SPECIFICATION.md" changes="Added Section 3.5 'HPC Module-Based Environments' after Section 3.4, before Section 4. Documents two classes of contamination (install-time site-packages injection, run-time PATH shadowing), install and run sequences with code blocks, and a table of two runtime guards with Location and Mechanism columns.">
      <type>input_spec</type>
    </file>
  </files_updated>
  <aid_log>
    <status>unchanged</status>
    <sections_modified>none (AID_LOG.md was already current from the preceding /document invocation at 13:30:00)</sections_modified>
  </aid_log>
  <coverage>
    <public_functions_documented>all/all</public_functions_documented>
    <classes_documented>all/all</classes_documented>
    <modules_with_docstrings>all/all</modules_with_docstrings>
  </coverage>
  <security_gate>
    <agents_dispatched>5</agents_dispatched>
    <pii_findings>0</pii_findings>
    <tier1_findings>0</tier1_findings>
    <tier2_findings>0</tier2_findings>
  </security_gate>
  <summary>Added HPC deployment documentation to both user-facing files. README.md gained a new "Running on HPC Systems" section with explicit install and run sequences, the -p flag variant, and a description of the two runtime guards. INPUT_SPECIFICATION.md gained Section 3.5 documenting the two contamination classes, ordered module-load sequences, and a guard mechanism table. Security gate: 5 agents, 0 violations across all tiers. AID_LOG.md unchanged (already current from the v1.4.0 document pass).</summary>
</document_report>
