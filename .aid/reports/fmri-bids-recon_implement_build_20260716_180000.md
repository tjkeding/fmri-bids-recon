<implement_report>
  <meta project="fmri-bids-recon" mode="implement" submodule="build" timestamp="2026-07-16T18:00:00Z" />
  <spec_ref>fmri-bids-recon_implement_plan_20260716_150000.md</spec_ref>
  <changes_applied>
    <change id="C8" status="done" user_decision="n/a">
      <files_modified>
        <file path="environment.yml" lines_changed="4" />
      </files_modified>
      <notes>Removed nodejs=20 from conda dependencies. Added bids-validator-deno==3.0.0 under pip. Rewrote header comment to reference conda env create as the sole setup step; removed references to hpc/setup_env.sh and npm.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/errors.py" lines_changed="12" />
      </files_modified>
      <notes>Deleted OrderingError and ValidationError classes. Added SpecFinding dataclass (severity, code, location, message) and ToolUnavailableError(BidsReconError). Added ConfigError(BidsReconError) for malformed configuration. Updated module docstring hierarchy to reflect the four-category taxonomy.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage6_validate.py" lines_changed="45" />
      </files_modified>
      <notes>Removed ordering_agreement and physio_geometry_agreement from ALL_GUARD_NAMES (12 entries remain). Rewrote run_bids_validator to invoke bids-validator-deno with JSON output to a temp file, return list[SpecFinding], and raise ToolUnavailableError on every failure mode (binary absent, no output, invalid JSON, missing issues key). Return code is ignored entirely. Updated module docstring to reflect the new return type.</notes>
    </change>
    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/physio.py" lines_changed="10" />
      </files_modified>
      <notes>Reverted two guard downgrades to fatal raises: PhysioAssociationError when log.acq_info is None in associate_physio, PhysioParseError when sample_time_ticks is None in write_physio. Removed function-local import logging as _logging occurrences.</notes>
    </change>
    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage4_assemble.py" lines_changed="30" />
      </files_modified>
      <notes>Four sub-changes: (a) removed InstitutionName, InstitutionAddress, InstitutionalDepartmentName, StationName, DeviceSerialNumber from SIDECAR_DENY_LIST; (b) added _normalize_acq_time helper using _parse_acquisition_datetime, replaced all 7 acq_time sites; (c) injected TaskName into func sidecars for both Role.BOLD and Role.SBREF; (d) added sessions.json sidecar write alongside sessions.tsv.</notes>
    </change>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/config.py" lines_changed="120" />
        <file path="config/study.example.yaml" lines_changed="71" />
      </files_modified>
      <notes>Reduced StudyConfig to seven primary fields (bids_root, staging_root, dicom_root, dicom_pattern, subjects, sessions, physio) with participants and task_registry as derived fields. Added @property for sourcedata_root and study_name. Rewrote load_config to expand subjects x sessions cross product with INFO-level skip for missing DICOM paths and ConfigError on empty result. Moved task_registry I/O to a sidecar .registry.yaml file. Rewrote the example YAML to match.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" lines_changed="345" />
      </files_modified>
      <notes>Complete rewrite. Deleted three subcommands and dispatch dict. Single positional config argument. Linear 7-phase pipeline: convert all, assert guards (before writes), assemble all, save registry, deface (hardcoded pydeface), validate, cubids. Structural reorder ensures guards check BEFORE any assembly output is written, and save_registry runs BEFORE the validator (fixing the silent registry loss on every historical run).</notes>
    </change>
    <change id="C7" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" lines_changed="0" />
      </files_modified>
      <notes>Included in the C2 rewrite. Manifest path relocated to bids_root/derivatives/fmri-bids-recon/manifest.tsv with migration helper that moves the old root-level manifest on first run.</notes>
    </change>
    <change id="C10" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" lines_changed="0" />
      </files_modified>
      <notes>Included in the C2 rewrite. Exit codes: 0 success, 1 GuardError, 2 ConfigError, 3 spec findings with errors, 4 ToolUnavailableError. Added _render_findings helper that groups findings by severity and code into a legible table. Never uses the word "Failed" for a completed validator check.</notes>
    </change>
    <change id="C11" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" lines_changed="0" />
      </files_modified>
      <notes>Included in the C2 rewrite. Physio extraction and association gated behind config.physio in both the convert loop and the assemble loop. Physio-disabled log emitted once via a flag to avoid per-participant noise.</notes>
    </change>
    <change id="C9" status="done" user_decision="proceed">
      <files_modified>
        <file path="hpc/convert_array.sbatch" lines_changed="0" />
        <file path="hpc/assemble.sbatch" lines_changed="0" />
        <file path="hpc/setup_env.sh" lines_changed="0" />
        <file path="hpc/Apptainer.def" lines_changed="0" />
        <file path="fmri-bids-recon.sh" lines_changed="0" />
        <file path="bids-heuristic-bw.py" lines_changed="0" />
        <file path="RUNBOOK.md" lines_changed="165" />
      </files_modified>
      <notes>Deleted the four hpc/ files, the hpc/ directory, fmri-bids-recon.sh, and bids-heuristic-bw.py. Per user direction, RUNBOOK.md was rewritten (not deleted) to reflect the redesigned single-command pipeline invocation, updated environment setup, new config format, exit code taxonomy, and output locations.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>11</total_changes>
    <completed>11</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate all changes. Tests will need updates: test_config.py references the old StudyConfig schema, test_cli_integration.py drives the deleted subcommands, and test_validate.py imports the deleted ValidationError. tests/bids_recon_patched/ is a stale copy that has diverged further.</next_steps>
</implement_report>
