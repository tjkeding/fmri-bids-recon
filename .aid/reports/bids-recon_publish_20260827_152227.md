<publish_report>
  <meta project="bids-recon" mode="publish" timestamp="2026-08-27T15:22:27Z" />
  <preflight>
    <tests_passing>true</tests_passing>
    <docs_current>true</docs_current>
    <sensitive_files_found>none</sensitive_files_found>
    <gitignore_adequate>true (updated this session: added /fmri-bids-recon_*.md, /HARMONIZE_*.md, /cftsi-*.yaml, dcm_qa_*/)</gitignore_adequate>
    <aid_log_present>true</aid_log_present>
  </preflight>
  <aid>
    <reports_synced>39 (38 from history directories + 1 document report)</reports_synced>
    <pii_check_passed>true</pii_check_passed>
    <aid_log_updated>true (v1.6.0 entry expanded to cover rounds 2-5, report count updated to 132)</aid_log_updated>
    <files_added>63 new .aid/reports/ files (39 synced this publish + 24 synced by prior /document)</files_added>
  </aid>
  <security_gate>
    <agents_dispatched>5</agents_dispatched>
    <agents_returned>5</agents_returned>
    <tier1_violations>0</tier1_violations>
    <tier2_violations>0 (1 borderline flag from SG-2 in AID_LOG.md Section 2 adjudicated as false positive: tool-framing language, not authorship attribution; 4/5 agents found clean)</tier2_violations>
    <pii_violations>0</pii_violations>
  </security_gate>
  <git_operations>
    <operation type="add" status="success">
      <details>87 files staged (18 modified source, 3 new source, 1 deleted source, 2 docs, 1 config, 63 AID reports, .gitignore)</details>
    </operation>
    <operation type="commit" status="success">
      <details>1c02d2e Multi-vendor classification, GRE fieldmaps, cross-module harmonization (87 files, +14559 -1119)</details>
    </operation>
    <operation type="commit" status="success">
      <details>5e445b7 Bump package version to 1.0.0</details>
    </operation>
    <operation type="push" status="success">
      <details>git push origin main (9ff4fd1..5e445b7)</details>
    </operation>
  </git_operations>
  <github>
    <repo_url>https://github.com/tjkeding/fmri-bids-recon.git</repo_url>
    <visibility>public</visibility>
    <issues_created>0</issues_created>
  </github>
  <summary>Published fmri-bids-recon v1.0.0 (package version) / AID v1.6.0 to origin/main. Two commits: the main payload (multi-vendor classification, GRE fieldmaps, cross-module harmonization rounds 2-5, 132 AID reports, .gitignore update) and a version bump to 1.0.0. Security gate passed (5/5 agents, 0 violations; 1 borderline Tier 2 adjudicated as false positive). Pre-flight clean: tests passing (639/544/0/95), docs current, no sensitive files.</summary>
</publish_report>
