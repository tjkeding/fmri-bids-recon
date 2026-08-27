<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-08-26T22:57:53Z" />
  <input_reports>
    <report path="bids-recon_clean_20260826_225214.md" mode="clean" key_items="5" />
  </input_reports>
  <changes>

    <change id="C1" priority="P1" source_item="F1">
      <file path="fmri_bids_recon/config.py" action="modify" />
      <file path="fmri_bids_recon/runs.py" action="modify" />
      <description>
        Persist and reload TaskRegistryEntry.prefix across save/reload cycles,
        and carry prefix+signature through the volume-count merge, closing three
        gaps that defeat the D14 drift guard across sessions.
      </description>
      <spec>
        THREE SITES, all structurally parallel to existing `signature` handling:

        (a) config.py save_registry() (lines 466-479): after the signature
        serialization block, add prefix serialization. prefix is a tuple (or
        None), so persist as a list (mirroring the matrix inner-tuple treatment)
        and gate on `entry.prefix is not None`:

            if entry.prefix is not None:
                entry_dict["prefix"] = list(entry.prefix)

        Insert this block immediately after the existing signature block
        (after line 479, before the `serialised_registry[label] = entry_dict`
        assignment on the current line 479).

        (b) config.py _resolve_config() (lines 349-367): after the signature
        deserialization block, add prefix deserialization. Read `trec.get("prefix")`,
        and if non-None, convert from list to tuple:

            pfx_raw = trec.get("prefix")
            prefix = tuple(pfx_raw) if pfx_raw is not None else None

        Then pass `prefix=prefix` to the TaskRegistryEntry constructor at
        line 358-367. The constructor call becomes:

            task_registry[label] = TaskRegistryEntry(
                label=str(trec["label"]),
                expected_volumes=(
                    int(trec["expected_volumes"])
                    if trec.get("expected_volumes") is not None
                    else None
                ),
                first_seen=str(trec["first_seen"]),
                signature=signature,
                prefix=prefix,
            )

        (c) runs.py check_volume_counts() (lines 142-153, 169-179): at both
        sites where a new TaskRegistryEntry is constructed (n_runs >= 2 branch
        at line 149, and n_runs == 1 branch at line 175), carry prefix and
        signature from the pre-existing registry entry. Replace bare
        construction:

            new_registry_entries[series.description] = TaskRegistryEntry(
                label=tlabel,
                expected_volumes=mode_count,    # or series.n_volumes
                first_seen=first_seen,
            )

        with:

            prior = registry.get(series.description)
            new_registry_entries[series.description] = TaskRegistryEntry(
                label=tlabel,
                expected_volumes=mode_count,    # or series.n_volumes
                first_seen=first_seen,
                signature=prior.signature if prior is not None else None,
                prefix=prior.prefix if prior is not None else None,
            )

        NOTE: the n_runs >= 2 branch already computes `prior` at line 144
        (used for first_seen); reuse that same `prior` variable. The n_runs == 1
        branch also already computes `prior` at line 169; reuse that as well.
        Both sites already have the `prior` variable in scope, so no new
        variable is needed, only the two additional keyword arguments.
      </spec>
      <dependencies>none</dependencies>
      <risk>medium - touches serialization/deserialization on a correctness-critical path (drift guard); structurally parallel to existing signature handling reduces novelty risk; 35 existing registry tests bound regression surface</risk>
      <rollback>Revert the three edit sites to their prior state (drop prefix serialization, drop prefix parameter from TaskRegistryEntry constructor in _resolve_config, drop the two keyword args from check_volume_counts construction sites)</rollback>
    </change>

    <change id="C2" priority="P1" source_item="F2">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <description>
        Pass the package version (not the dcm2niix version) as engine_version
        to write_conversion_report, correcting the report provenance field.
      </description>
      <spec>
        (a) Add an import at the top of pipeline.py, after the existing
        `from .errors import GuardError` import (line 38):

            from . import __version__

        (b) In the Phase 3 assemble loop, change the write_conversion_report
        call (pipeline.py:296-298) from:

            dcm2niix_version=version_str_i, engine_version=version_str_i,

        to:

            dcm2niix_version=version_str_i, engine_version=__version__,

        One import, one argument change. No data-path impact; the
        engine_version field is purely informational in the report.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - single import, single argument substitution; no data-path or control-flow impact</risk>
      <rollback>Remove the import and revert the argument to version_str_i</rollback>
    </change>

    <change id="C3" priority="P1" source_item="F3">
      <file path="fmri_bids_recon/deface.py" action="modify" />
      <description>
        Wrap defacing subprocess calls and re-raise CalledProcessError and
        FileNotFoundError as ToolUnavailableError so main() maps them to
        exit 4, preserving fail-loud semantics for the de-identification step.
      </description>
      <spec>
        In deface() (deface.py), wrap the tool invocation block (lines 106-122,
        the `if tool == "pydeface": ... elif tool == "afni_refacer": ...` block)
        inside a try/except that catches the two failure modes:

            try:
                if tool == "pydeface":
                    subprocess.run(
                        ["pydeface", str(input_path), "--outfile", str(output_path)],
                        check=True,
                        env=fsl_env,
                    )
                elif tool == "afni_refacer":
                    subprocess.run(
                        [
                            "@afni_refacer_run",
                            "-input", str(input_path),
                            "-mode_deface",
                            "-prefix", str(output_path),
                        ],
                        check=True,
                        env=fsl_env,
                    )
            except subprocess.CalledProcessError as exc:
                raise ToolUnavailableError(
                    f"Defacing tool '{tool}' failed on {input_path.name}: "
                    f"exit code {exc.returncode}",
                    context={
                        "tool": tool,
                        "input_path": str(input_path),
                        "returncode": exc.returncode,
                    },
                ) from exc
            except FileNotFoundError as exc:
                raise ToolUnavailableError(
                    f"Defacing tool '{tool}' binary not found: {exc}",
                    context={
                        "tool": tool,
                        "input_path": str(input_path),
                    },
                ) from exc

        ToolUnavailableError is already imported (deface.py:16). The `from exc`
        chain preserves the original traceback. main() already catches
        ToolUnavailableError and maps it to exit 4 (__main__.py:163-164).
      </spec>
      <dependencies>none</dependencies>
      <risk>low - wrapping existing calls in try/except with re-raise; no behavioral change to the success path; ToolUnavailableError import already present</risk>
      <rollback>Remove the try/except wrapping, restoring the bare subprocess.run calls</rollback>
    </change>

    <change id="C4" priority="P2" source_item="F4">
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>
        Extract a _emit_series nested helper inside assemble() and route all
        eight file-emission sites through it, eliminating the duplicated
        mkdir/copy/write/append/scans epilogue.
      </description>
      <spec>
        (a) Define `_emit_series` as a nested function inside assemble(), placed
        immediately after the existing `unpaired_sns` set (line 197), replacing
        the current `_write_gre_output` definition (lines 199-211):

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
                mapping.bids_relative_paths[series.series_number] = (
                    dest.relative_to(sub_dir).as_posix()
                )
                scans_rows.append({
                    "filename": str(dest.relative_to(ses_dir)),
                    "acq_time": _normalize_acq_time(series.raw),
                })

            def _write_gre_output(series, suffix, run_idx):
                _emit_series(series, ses_dir / "fmap",
                             f"sub-{sub}_ses-{ses}_run-{run_idx:02d}_{suffix}")

        (b) Rewrite each of the seven role branches to call _emit_series:

        T1W (replace lines 256-269):
            if role == Role.T1W:
                run_idx = anat_run_index[snum]
                _emit_series(series, ses_dir / "anat",
                             f"sub-{sub}_ses-{ses}_run-{run_idx:02d}_T1w")

        T2W (replace lines 271-284):
            elif role == Role.T2W:
                run_idx = anat_run_index[snum]
                _emit_series(series, ses_dir / "anat",
                             f"sub-{sub}_ses-{ses}_run-{run_idx:02d}_T2w")

        BOLD (replace lines 286-302):
            elif role == Role.BOLD:
                task_label = labels[snum]
                run_idx = run_indices[snum]
                data = dict(series.raw)
                data["TaskName"] = labels[snum]
                _emit_series(series, ses_dir / "func",
                             f"sub-{sub}_ses-{ses}_task-{task_label}_run-{run_idx:02d}_bold",
                             json_data=data)

        SBREF (replace lines 304-330, preserving the parent-BOLD derivation):
            elif role == Role.SBREF:
                task_label = labels[snum]
                sbref_key = _acq_sort_key(snum)
                bold_snums_same_task = sorted(
                    [sn for sn, r in roles.items()
                     if r == Role.BOLD and labels.get(sn) == task_label],
                    key=_acq_sort_key,
                )
                parent_bold_snum = next(
                    (sn for sn in bold_snums_same_task
                     if _acq_sort_key(sn) > sbref_key),
                    bold_snums_same_task[0] if bold_snums_same_task else None,
                )
                run_idx = (run_indices[parent_bold_snum]
                           if parent_bold_snum is not None else 1)
                data = dict(series.raw)
                data["TaskName"] = labels[snum]
                _emit_series(series, ses_dir / "func",
                             f"sub-{sub}_ses-{ses}_task-{task_label}_run-{run_idx:02d}_sbref",
                             json_data=data)

        DWI (replace lines 332-363, preserving the PhaseEncodingError guard):
            elif role == Role.DWI:
                dir_label = PE_DIRECTION_TO_LABEL.get(
                    series.phase_encoding_direction or "")
                if dir_label is None:
                    raise PhaseEncodingError(
                        f"Diffusion series {snum} has phase-encoding direction "
                        f"{series.phase_encoding_direction!r}, which does not "
                        f"map to a known BIDS dir- label; refusing to emit "
                        f"dir-UNK.",
                        context={
                            "series_number": snum,
                            "phase_encoding_direction":
                                series.phase_encoding_direction,
                            "role": role.name,
                        },
                    )
                run_idx = dwi_run_index[snum]
                _emit_series(
                    series, ses_dir / "dwi",
                    f"sub-{sub}_ses-{ses}_dir-{dir_label}_run-{run_idx:02d}_dwi",
                    companions=(".bval", ".bvec"),
                )

        DWI_SBREF (replace lines 365-390, preserving the PhaseEncodingError guard):
            elif role == Role.DWI_SBREF:
                dir_label = PE_DIRECTION_TO_LABEL.get(
                    series.phase_encoding_direction or "")
                if dir_label is None:
                    raise PhaseEncodingError(
                        f"Diffusion series {snum} has phase-encoding direction "
                        f"{series.phase_encoding_direction!r}, which does not "
                        f"map to a known BIDS dir- label; refusing to emit "
                        f"dir-UNK.",
                        context={
                            "series_number": snum,
                            "phase_encoding_direction":
                                series.phase_encoding_direction,
                            "role": role.name,
                        },
                    )
                run_idx = dwi_run_index.get(snum, 1)
                _emit_series(
                    series, ses_dir / "dwi",
                    f"sub-{sub}_ses-{ses}_dir-{dir_label}_run-{run_idx:02d}_sbref",
                )

        FMAP paired (replace lines 417-434, preserving the unit-lookup and
        single-mode routing that precede it):
            # After the unit-lookup, single-mode routing, and fmap_dir setup:
            fmap_dir = ses_dir / "fmap"
            acq = "func" if role == Role.FMAP_FUNC else "dwi"
            dir_label = PE_DIRECTION_TO_LABEL[unit.dir_labels[member_idx]]
            run_idx = unit.run_index
            _emit_series(
                series, fmap_dir,
                f"sub-{sub}_ses-{ses}_acq-{acq}_dir-{dir_label}"
                f"_run-{run_idx:02d}_epi",
            )

        (c) nifti_stem is already imported (stage4_assemble.py:19). shutil is
        already imported (stage4_assemble.py:7). No new imports needed.

        (d) INVARIANTS PRESERVED:
        - DWI PhaseEncodingError guards remain in the DWI/DWI_SBREF branches
          (executed before _emit_series is called).
        - FMAP unit-lookup, unpaired_sns routing, and single-mode sourcedata
          routing remain in the FMAP branch (executed before _emit_series).
        - BOLD/SBREF TaskName injection uses the json_data parameter.
        - DWI companion .bval/.bvec copy uses the companions parameter.
        - _write_gre_output remains as a thin wrapper (used by GRE assembly).
      </spec>
      <dependencies>none</dependencies>
      <risk>medium - refactors 8 emission sites in a safety-critical module; the 35-test assembly suite and role-specific structural tests bound regression risk; all pre-emission guards are preserved in their branches</risk>
      <rollback>Revert stage4_assemble.py to its pre-change state (restore inline emission blocks and the original _write_gre_output)</rollback>
    </change>

    <change id="C5" priority="P2" source_item="F5">
      <file path="fmri_bids_recon/pipeline.py" action="modify" />
      <file path="fmri_bids_recon/warnings.py" action="modify" />
      <description>
        Document the process-level parallelism / non-reentrancy invariant for
        the global warning accumulator. No code-path change.
      </description>
      <spec>
        (a) warnings.py: add a module-level docstring note. Replace the existing
        module docstring (lines 1-5) with an expanded version that includes
        the invariant. Append after the existing docstring content:

        After the line "the fmri-proc-orchestrator." add:

            The accumulator is process-global and not thread-safe. Concurrent
            in-process run() calls would interleave on the shared list, making
            session status and exit code nondeterministic. The pipeline must be
            parallelized at the process level (one run() per process, as in the
            SLURM deployment model).

        (b) pipeline.py run() docstring (lines 95-123): add a note after the
        existing Raises section. After the last line of the docstring
        ("On other pipeline errors."), add:

            Notes
            -----
            This function is not reentrant. The warning framework uses a
            process-global accumulator (``warnings._WARNING_ACCUMULATOR``)
            that is cleared on entry and snapshotted on exit. Concurrent
            in-process calls would interleave on the accumulator, producing
            nondeterministic session status and exit codes. Parallelize at
            the process level (one ``run()`` per process).
      </spec>
      <dependencies>C2 (both touch pipeline.py; C5 must apply after C2 to avoid merge conflicts on the same file)</dependencies>
      <risk>low - documentation-only change; no behavior impact</risk>
      <rollback>Remove the added docstring text</rollback>
    </change>

  </changes>
  <execution_order>C1, C2, C3, C4, C5 (C1/C2/C3/C4 are mutually independent; C5 depends on C2 completing first due to shared pipeline.py edits)</execution_order>
</implement_plan>
