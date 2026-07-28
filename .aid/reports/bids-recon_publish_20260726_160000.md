<publish_report>
  <meta project="bids-recon" mode="publish" timestamp="2026-07-26T16:00:00-04:00" />
  <preflight>
    <tests_passing>true</tests_passing>
    <docs_current>true</docs_current>
    <sensitive_files_found>none</sensitive_files_found>
    <gitignore_adequate>true</gitignore_adequate>
    <aid_log_present>true</aid_log_present>
  </preflight>
  <aid>
    <reports_synced>4</reports_synced>
    <pii_check_passed>true</pii_check_passed>
    <aid_log_updated>true</aid_log_updated>
    <files_added>
      .aid/reports/bids-recon_implement_plan_20260724_160000.md
      .aid/reports/bids-recon_implement_build_20260724_160500.md
      .aid/reports/bids-recon_test_20260724_160500.md
      .aid/reports/bids-recon_document_20260724_161500.md
    </files_added>
  </aid>
  <security_gate>
    <agents_dispatched>5</agents_dispatched>
    <pii_findings>5</pii_findings>
    <tier1_findings>0</tier1_findings>
    <tier2_findings>0</tier2_findings>
    <pii_remediations>
      <remediation file=".aid/reports/fmri-bids-recon_implement_plan_20260714_150852.md" line="104" category="conda_path" action="Removed conda prefix path reference, retained tool name and version only" />
      <remediation file=".aid/reports/fmri-bids-recon_cr_20260721_183128.md" line="380" category="absolute_path" action="Replaced home-directory example path with generic placeholder" />
      <remediation file=".aid/reports/fmri-bids-recon_implement_plan_20260715_151850.md" line="303" category="absolute_path" action="Replaced /tmp/ path with temp_dir placeholder" />
      <remediation file=".aid/reports/fmri-bids-recon_test_20260721_180900.md" line="12" category="uuid" action="Redacted receipt-verification nonce" />
      <remediation file=".aid/reports/fmri-bids-recon_test_20260721_175600.md" line="12" category="uuid" action="Redacted receipt-verification nonce" />
    </pii_remediations>
    <rescan_passed>true</rescan_passed>
  </security_gate>
  <git_operations>
    <operation type="add" status="success">
      <details>Staged 7 modified files and force-added 4 new .aid/reports/ files (gitignored by bids-recon_*.md pattern)</details>
    </operation>
    <operation type="commit" status="success">
      <details>3e6fad4 HPC environment sanitization: sys.path guard for foreign-version Python contamination</details>
    </operation>
    <operation type="push" status="success">
      <details>7a96295..3e6fad4 main -> main</details>
    </operation>
    <operation type="tag" status="success">
      <details>v1.3.0 -> v1.3.0</details>
    </operation>
  </git_operations>
  <github>
    <repo_url>https://github.com/tjkeding/fmri-bids-recon</repo_url>
    <visibility>public</visibility>
    <issues_created>0</issues_created>
  </github>
  <observations>
    <observation scope="deferred">.gitignore pattern `bids-recon_*.md` (line 16) is too broad: matches .aid/reports/bids-recon_*.md files in addition to root-level working copies. Recommend changing to `/bids-recon_*.md` (root-only match) via /implement in a future session.</observation>
  </observations>
  <summary>Published v1.3.0 to GitHub. 11 files committed: 1 codebase change (_sanitize_sys_path guard in __main__.py), 1 documentation update (AID_LOG.md v1.3.0 entry), 4 new AID reports synced (56 total), 5 pre-existing AID reports remediated for PII (conda path, absolute paths, UUID nonces). Security gate: 5 agents, 0 Tier 1, 0 Tier 2, 5 PII findings remediated and re-verified clean.</summary>
</publish_report>
