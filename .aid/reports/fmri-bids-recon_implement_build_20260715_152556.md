<implement_report>
  <meta project="fmri-bids-recon" mode="implement" submodule="build" timestamp="2026-07-15T19:25:56Z" />
  <spec_ref>fmri-bids-recon_implement_plan_20260715_151850.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="environment.yml" lines_changed="24" />
      </files_modified>
      <notes>New conda environment spec created verbatim: conda-forge Python 3.12 and Node.js 20; pip-pinned pydicom, nibabel, numpy, pyyaml, cubids, and dcm2niix==1.0.20260416. No deviations.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="hpc/setup_env.sh" lines_changed="41" />
      </files_modified>
      <notes>New setup script created verbatim: creates or updates the conda env from environment.yml, then installs bids-validator@1.14.13 into that env via conda run npm. Passes bash -n. No deviations.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="hpc/convert_array.sbatch" lines_changed="61" />
      </files_modified>
      <notes>Full-file overwrite replacing the apptainer invocation with conda activation. Adds CODE_DIR and optional ENV_NAME positional args, validates the fmri_bids_recon package directory, parses the participant with the env's Python via heredoc, and runs the module with CODE_DIR on PYTHONPATH. Passes bash -n; no apptainer references remain.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="hpc/assemble.sbatch" lines_changed="42" />
      </files_modified>
      <notes>Full-file overwrite replacing the apptainer invocation with conda activation. Adds CODE_DIR and optional ENV_NAME positional args, validates the package directory, preserves the "ONLY process that touches the BIDS root" comment, and runs the assemble subcommand with CODE_DIR on PYTHONPATH. Passes bash -n; no apptainer references remain.</notes>
    </change>
    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="hpc/Apptainer.def" lines_changed="3" />
      </files_modified>
      <notes>Three targeted edits: repinned DCM2NIIX_VERSION to v1.0.20260416 (verified real release at the code's version floor), set DCM2NIIX_SHA256 to the verified 64-hex digest, and inserted a sha256sum -c integrity check between the wget and unzip lines in the x86_64 branch (confirmed at lines 96-98). All other lines unchanged.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>5</total_changes>
    <completed>5</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate all changes. The five deliverables are configuration and shell artifacts consumed only on the server (environment.yml, setup_env.sh, the two sbatch scripts, and the container recipe); none touch the fmri_bids_recon package or the existing pytest suite. Static checks performed inline: all three shell scripts pass bash -n, and the sbatch scripts contain no residual apptainer references.</next_steps>
</implement_report>
