<clean_report>
  <meta project="bids-recon" mode="clean" timestamp="2026-08-26T22:52:14Z" />
  <scope>
    Full production codebase: all 22 modules under fmri_bids_recon/ (6,193 LOC).
    Focus per invocation: project-specific markers, code efficiency (dead code,
    unused paths, redundancy), and reorganization for comprehensibility and
    resource use. Test suite (tests/) read for context but out of review scope.
    Every finding was adjudicated with the user and locked before this report
    was written.
  </scope>
  <research_conducted>
    None. All five findings derive from direct codebase analysis (control-flow
    tracing across pipeline.py, config.py, runs.py, labels.py, deface.py,
    __main__.py, stage4_assemble.py, warnings.py); no external performance or
    framework claims required literature verification, so no research agents were
    dispatched.
  </research_conducted>
  <metrics>
    <loc>6193</loc>
    <files>22</files>
    <avg_complexity>Not profiled with radon; by inspection the two largest modules (stage3_map.py 983 LOC, stage4_assemble.py 633 LOC) carry the highest branching density, concentrated in group_fieldmaps() and the assemble() per-role dispatch.</avg_complexity>
  </metrics>
  <findings>

    <finding id="F1" severity="major" category="correctness">
      <location file="fmri_bids_recon/config.py" lines="59, 358-367, 466-479" />
      <location file="fmri_bids_recon/runs.py" lines="149-153, 175-179" />
      <location file="fmri_bids_recon/pipeline.py" lines="226-227" />
      <description>
        The D14/C7 fix added TaskRegistryEntry.prefix so the no_label_drift guard
        re-derives a registered label against the prefix in force at registration
        time, not the current session's prefix. The field is exercised only
        within a single session by the test suite; three gaps break it across a
        save/reload cycle and across the volume-count merge.
      </description>
      <current>
        (1) save_registry() (config.py:466-479) serialises label,
        expected_volumes, first_seen, and conditionally signature, but never
        prefix. (2) _resolve_config() (config.py:358-367) reconstructs
        TaskRegistryEntry without passing prefix, so it defaults to None on
        reload. (3) check_volume_counts() (runs.py:149-153, 175-179) constructs
        bare TaskRegistryEntry(label, expected_volumes, first_seen) with neither
        prefix nor signature; pipeline.py:227 (merged_registry.update(vol_updates))
        then overwrites the prefix-bearing entry that resolve_labels() built
        (labels.py:322-328), stripping both fields from the merged result.
      </description>
      <proposed>
        (a) Add prefix serialization in save_registry() and deserialization in
        _resolve_config(), parallel to the existing signature handling (prefix is
        a tuple, so persist as a list and re-tuple on load, mirroring the matrix
        inner-tuple treatment). (b) In check_volume_counts(), carry prefix and
        signature from the pre-existing registry entry (registry.get(description))
        into the new TaskRegistryEntry rather than constructing a bare one, so the
        volume-count merge does not discard drift-guard state.
      </proposed>
      <literature>None required.</literature>
      <impact>
        After any save/reload, registry[desc].prefix is None and the drift guard
        (labels.py:300) silently falls back to the current session's prefix,
        reintroducing exactly the cross-wave false-drift / missed-drift failure
        D14 was designed to prevent. This is a reproducibility/defensibility
        defect in the longitudinal task-label contract.
      </impact>
    </finding>

    <finding id="F2" severity="major" category="correctness">
      <location file="fmri_bids_recon/pipeline.py" lines="128-129, 240, 268, 296-298" />
      <location file="fmri_bids_recon/report.py" lines="91-92" />
      <description>
        The conversion report's engine_version provenance field is populated with
        the dcm2niix version string instead of the fmri-bids-recon engine version.
      </description>
      <current>
        version_str is the dcm2niix version (pipeline.py:128-129), stored in the
        intermediate (line 240), read back as version_str_i (line 268), and passed
        to BOTH dcm2niix_version and engine_version of write_conversion_report
        (pipeline.py:296-298). report.py:91-92 renders them as two distinct
        provenance lines, so both show the dcm2niix version; the true engine
        version (fmri_bids_recon.__version__ = '0.1.0') never appears.
      </current>
      <proposed>
        Import __version__ in pipeline.py (already imported in __main__.py:45) and
        pass engine_version=__version__ while keeping dcm2niix_version=version_str_i.
        One import, one argument; no data-path impact.
      </proposed>
      <literature>None required.</literature>
      <impact>
        Every conversion report misidentifies the software that produced the
        dataset. An auditor reconstructing the pipeline from provenance cannot
        recover the engine version. Direct reproducibility defect.
      </impact>
    </finding>

    <finding id="F3" severity="major" category="correctness">
      <location file="fmri_bids_recon/deface.py" lines="107-122" />
      <location file="fmri_bids_recon/pipeline.py" lines="314-315" />
      <location file="fmri_bids_recon/__main__.py" lines="160-177" />
      <description>
        Defacing subprocess failures are not mapped to the documented tool-error
        exit code (4); they fall through main()'s catch-all and exit 1
        (pipeline invariant violation), misclassifying an environment/tool failure
        as a pipeline-logic failure and misdirecting the orchestrator's retry policy.
      </description>
      <current>
        deface() invokes pydeface/afni_refacer with subprocess.run(..., check=True)
        (deface.py:107-122). CalledProcessError (non-zero exit) and FileNotFoundError
        (absent binary; afni_refacer is not covered by the tool preflight) are not
        BidsReconError subclasses. The Phase 5 call site (pipeline.py:314-315) is
        unguarded, unlike physio (caught/skipped, pipeline.py:216-219) and cubids
        (caught/warned, pipeline.py:340-343). The exception reaches
        __main__.py's `except Exception` and exits 1, though the exit contract
        (__main__.py:123-129) reserves 4 for external-tool/environment failures.
      </current>
      <proposed>
        LOCKED RESOLUTION (option a, blocking, fail-loud): wrap the subprocess
        calls in deface() (or the Phase 5 call site) and re-raise pydeface/
        afni_refacer/flirt failures as ToolUnavailableError, which main() already
        maps to exit 4. This corrects the exit-code classification and preserves
        fail-loud semantics appropriate to a de-identification step: an incomplete
        derivatives/defaced/ tree halts the session visibly rather than being
        surfaced as a soft warning, protecting against distribution of
        insufficiently de-identified data.
      </proposed>
      <literature>None required.</literature>
      <impact>
        Exit 1 tells the orchestrator "pipeline invariant violation, do not retry";
        the correct signal for a defacing-tool failure is exit 4 "environment
        issue" (potentially retryable after fixing the environment). Additionally,
        the de-identification failure mode (partial defaced tree) warrants explicit
        halting on PHI-safety grounds.
      </impact>
    </finding>

    <finding id="F4" severity="minor" category="redundancy">
      <location file="fmri_bids_recon/stage4_assemble.py" lines="197-209, 254-422" />
      <description>
        The seven per-role assembly branches plus _write_gre_output each repeat an
        identical six-line file-emission epilogue and a near-identical
        mkdir/copy/write prologue, differing only by target subdirectory, stem,
        JSON payload (BOLD/SBREF inject TaskName), and companion files (DWI copies
        .bval/.bvec).
      </description>
      <current>
        The block
          bids_files.append(dest)
          mapping.bids_relative_paths[snum] = dest.relative_to(sub_dir).as_posix()
          scans_rows.append({"filename": ..., "acq_time": _normalize_acq_time(series.raw)})
        recurs verbatim at lines 262-267, 277-282, 295-300, 323-328, 356-361,
        383-388, 417-422, and 204-209 (eight sites; inline branches use snum, the
        helper uses series.series_number, which are equal). The mkdir + _copy_nifti
        + _write_json prologue is duplicated to the same degree.
      </current>
      <proposed>
        LOCKED RESOLUTION (fuller _emit_series helper):
          def _emit_series(series, subdir, stem, *, json_data=None, companions=()):
              subdir.mkdir(parents=True, exist_ok=True)
              dest = subdir / f"{stem}.nii.gz"
              _copy_nifti(series, dest)
              _write_json(subdir / f"{stem}.json",
                          json_data if json_data is not None else series.raw)
              for ext in companions:
                  src = series.nifti_path.parent / (nifti_stem(series.nifti_path) + ext)
                  if src.exists():
                      shutil.copy2(src, subdir / (stem + ext))
              bids_files.append(dest)
              mapping.bids_relative_paths[series.series_number] = dest.relative_to(sub_dir).as_posix()
              scans_rows.append({"filename": str(dest.relative_to(ses_dir)),
                                 "acq_time": _normalize_acq_time(series.raw)})
        Each role branch reduces to computing its stem and calling _emit_series
        (BOLD/SBREF pass json_data with TaskName; DWI passes companions=(".bval",
        ".bvec")); _write_gre_output becomes a thin wrapper. The DWI dir-label
        PhaseEncodingError guard and the FMAP unit-lookup / single-mode routing
        remain in their branches, unchanged, before the _emit_series call.
        nifti_stem is already imported (stage4_assemble.py:19).
      </proposed>
      <literature>None required.</literature>
      <impact>
        Converts eight parallel emission sites into one. This is the exact
        failure mode that produced F1 and F2 (a field dropped or mislabelled in
        one of N parallel construction sites); consolidation removes the
        recurrence surface. The 35-test assembly suite bounds regression risk on
        this safety-critical module.
      </impact>
    </finding>

    <finding id="F5" severity="minor" category="correctness">
      <location file="fmri_bids_recon/warnings.py" lines="16, 20-24, 45" />
      <location file="fmri_bids_recon/pipeline.py" lines="125, 345-346" />
      <description>
        The warning framework accumulates into a single process-global list,
        making the documented public run() API non-reentrant and thread-unsafe.
        Latent: not triggered by the SLURM/process-level parallelism the system
        actually uses.
      </description>
      <current>
        _WARNING_ACCUMULATOR (warnings.py:16) is a module-global list appended by
        graded_warning() (line 45), emptied by clear_warnings() (line 24), and
        snapshotted by get_warnings() (line 20). run() brackets a session with
        clear_warnings()/get_warnings() (pipeline.py:125, 345) and derives status
        (and thus exit code 3) from the accumulated set (line 346). No lock,
        threading.local, or contextvars isolation exists.
      </current>
      <proposed>
        LOCKED RESOLUTION (option a, document the invariant): add an explicit note
        to run()'s docstring and to warnings.py stating that the pipeline is not
        reentrant / not thread-safe and must be parallelized at the process level
        (the SLURM deployment model). No data-path change. The process-level
        parallelism model makes the global safe in practice; documenting the
        invariant is proportionate to a hazard the deployment does not exercise.
        (Options b/contextvars and c/explicit-threading were considered and
        declined as disproportionate.)
      </proposed>
      <literature>None required.</literature>
      <impact>
        Two concurrent in-process run() calls would interleave on the accumulator:
        one call's clear_warnings() wipes the other's warnings and each
        get_warnings() returns a blend, making session status and exit code 3
        nondeterministic. Single-threaded sequential calls and the per-participant
        loop within one run() are unaffected. Fix is documentary because the
        deployment parallelizes at the process level.
      </impact>
    </finding>

  </findings>
  <summary>
    <critical_count>0</critical_count>
    <major_count>3</major_count>
    <minor_count>2</minor_count>
    <total_findings>5</total_findings>
    <overall_assessment>needs_minor_work</overall_assessment>
  </summary>
  <action_items>
    <item priority="P1" target_mode="implement" finding_ref="F1" description="Persist and reload TaskRegistryEntry.prefix in save_registry()/_resolve_config() (parallel to signature); and in check_volume_counts() carry prefix+signature from the existing registry entry into the new entry instead of constructing a bare one, so pipeline.py's vol_updates merge does not strip drift-guard state." />
    <item priority="P1" target_mode="implement" finding_ref="F2" description="Import __version__ in pipeline.py and pass engine_version=__version__ to write_conversion_report (keep dcm2niix_version=version_str_i)." />
    <item priority="P1" target_mode="implement" finding_ref="F3" description="Wrap deface() subprocess.run(check=True) calls and re-raise pydeface/afni_refacer/flirt failures (CalledProcessError, FileNotFoundError) as ToolUnavailableError so main() maps them to exit 4; keep the step fail-loud so an incomplete derivatives/defaced/ tree halts the session." />
    <item priority="P2" target_mode="implement" finding_ref="F4" description="Extract the _emit_series(series, subdir, stem, *, json_data=None, companions=()) helper in stage4_assemble.py and route all eight emission sites (seven role branches plus _write_gre_output) through it, preserving each branch's pre-emission guards (DWI dir-label PhaseEncodingError, FMAP unit-lookup/single-mode routing)." />
    <item priority="P2" target_mode="implement" finding_ref="F5" description="Document in run()'s docstring and warnings.py that the pipeline is not reentrant/thread-safe and must be parallelized at the process level (SLURM); no code-path change to the accumulator." />
  </action_items>
</clean_report>
