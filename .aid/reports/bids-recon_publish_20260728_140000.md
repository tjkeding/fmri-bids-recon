<publish_report>
  <meta project="bids-recon" mode="publish" timestamp="2026-07-28T14:00:00-04:00" />
  <preflight>
    <tests_passing>true</tests_passing>
    <docs_current>true</docs_current>
    <sensitive_files_found>none</sensitive_files_found>
    <gitignore_adequate>true</gitignore_adequate>
    <aid_log_present>true</aid_log_present>
  </preflight>
  <aid>
    <reports_synced>5</reports_synced>
    <pii_check_passed>true</pii_check_passed>
    <aid_log_updated>false</aid_log_updated>
    <files_added>
      .aid/reports/bids-recon_publish_20260726_160000.md
      .aid/reports/bids-recon_implement_plan_20260728_091500.md
      .aid/reports/bids-recon_implement_build_20260728_130500.md
      .aid/reports/bids-recon_test_20260728_130800.md
      .aid/reports/bids-recon_document_20260728_133000.md
    </files_added>
  </aid>
  <security_gate>
    <agents_dispatched>5</agents_dispatched>
    <pii_findings>6</pii_findings>
    <tier1_findings>0</tier1_findings>
    <tier2_findings>0</tier2_findings>
    <pii_remediations>
      <remediation file=".aid/reports/bids-recon_document_20260728_133000.md" line="7" category="hostname" action="Replaced quoted HPC cluster names in remediation description with generic phrasing" />
      <remediation file=".aid/reports/bids-recon_document_20260728_133000.md" line="7" category="absolute_path" action="Replaced quoted institution-specific HPC path in remediation description with generic phrasing" />
      <remediation file=".aid/reports/bids-recon_document_20260728_133000.md" line="7" category="username" action="Replaced quoted bare username in remediation description with generic descriptor" />
      <remediation file=".aid/reports/bids-recon_document_20260728_133000.md" line="10" category="username" action="Replaced quoted bare username in remediation description with generic descriptor" />
      <remediation file=".aid/reports/bids-recon_publish_20260726_160000.md" line="27" category="conda_path" action="Replaced conda prefix path variable reference with generic phrasing" />
      <remediation file=".aid/reports/bids-recon_publish_20260726_160000.md" line="28" category="absolute_path" action="Replaced home-directory example path with generic phrasing" />
    </pii_remediations>
    <rescan_passed>true</rescan_passed>
  </security_gate>
  <git_operations>
    <operation type="add" status="success">
      <details>Staged 6 modified tracked files and force-added 5 new .aid/reports/ files</details>
    </operation>
    <operation type="commit" status="success">
      <details>5c70d21 FSLDIR-based FSL tool resolution: eliminate circular PATH dependency on HPC clusters</details>
    </operation>
    <operation type="push" status="success">
      <details>3e6fad4..5c70d21 main -> main</details>
    </operation>
    <operation type="tag" status="success">
      <details>v1.4.0 -> v1.4.0</details>
    </operation>
  </git_operations>
  <github>
    <repo_url>https://github.com/tjkeding/fmri-bids-recon</repo_url>
    <visibility>public</visibility>
    <issues_created>0</issues_created>
  </github>
  <summary>Published v1.4.0 to GitHub. 11 files committed: 5 codebase changes (deface.py FSLDIR resolution, config.py docstring, .gitignore root-only pattern, README.md and INPUT_SPECIFICATION.md FSL references), 1 documentation update (AID_LOG.md v1.4.0 entry), 5 new AID reports synced (61 total). Security gate: 5 agents, 0 Tier 1, 0 Tier 2, 6 PII findings remediated (recursive meta-references in AID report remediation descriptions) and re-verified clean.</summary>
</publish_report>
