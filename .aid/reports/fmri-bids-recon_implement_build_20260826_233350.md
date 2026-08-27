<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-08-26T23:33:50Z" />
  <spec_ref>bids-recon_implement_plan_20260826_225753.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/config.py" lines_changed="8" />
        <file path="fmri_bids_recon/runs.py" lines_changed="4" />
      </files_modified>
      <notes>
        save_registry() now serializes prefix as a list when non-None,
        parallel to the existing signature block. _resolve_config() reads
        prefix from the sidecar, converts list to tuple, and passes it to
        TaskRegistryEntry. check_volume_counts() now carries both prefix
        and signature from the pre-existing registry entry (via the
        already-scoped prior variable) at both the multi-run and
        single-run construction sites, so the volume-count merge no
        longer strips drift-guard state. No deviation from spec.
      </notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/pipeline.py" lines_changed="2" />
      </files_modified>
      <notes>
        Added `from . import __version__` after the GuardError import and
        changed the write_conversion_report call to pass
        engine_version=__version__ while dcm2niix_version retains
        version_str_i. No deviation from spec.
      </notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/deface.py" lines_changed="18" />
      </files_modified>
      <notes>
        Wrapped the pydeface/afni_refacer subprocess.run calls in a
        try/except block. CalledProcessError and FileNotFoundError are
        both re-raised as ToolUnavailableError with a context dict and a
        chained traceback (`from exc`), so main() now correctly maps
        defacing-tool failures to exit code 4 instead of falling through
        to the catch-all exit 1. The success path and the
        output_path.exists() check are unchanged. No deviation from spec.
      </notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage4_assemble.py" lines_changed="112" />
      </files_modified>
      <notes>
        Defined the _emit_series(series, subdir, stem, *, json_data=None,
        companions=()) nested helper inside assemble(), immediately after
        the unpaired_sns set. _write_gre_output is now a thin wrapper
        calling _emit_series. All seven role branches (T1W, T2W, BOLD,
        SBREF, DWI, DWI_SBREF, FMAP paired) were rewritten to call
        _emit_series, collapsing eight parallel emission sites into one.
        Each branch's pre-emission guards (DWI/DWI_SBREF PhaseEncodingError,
        FMAP unit-lookup and single-mode routing) remain unchanged before
        the _emit_series call. BOLD/SBREF TaskName injection uses the
        json_data parameter; DWI's .bval/.bvec companion copy uses the
        companions parameter. No deviation from spec.
      </notes>
    </change>
    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/warnings.py" lines_changed="6" />
        <file path="fmri_bids_recon/pipeline.py" lines_changed="8" />
      </files_modified>
      <notes>
        Documentation-only change, applied after the engine_version fix
        to avoid a merge conflict on pipeline.py. warnings.py's module
        docstring now states the accumulator is process-global and not
        thread-safe, and that the pipeline must be parallelized at the
        process level. pipeline.py's run() docstring gained a Notes
        section stating the function is not reentrant and explaining why.
        No executable code path was modified in either file. No deviation
        from spec.
      </notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>5</total_changes>
    <completed>5</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <next_steps>Recommended: run /test to validate all changes.</next_steps>
</implement_report>
