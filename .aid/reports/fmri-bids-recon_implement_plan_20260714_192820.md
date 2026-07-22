<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-14T23:28:20Z" />

  <input_reports>
    <report path="fmri-bids-recon_test_20260714_175742.md" mode="test" key_items="30" />
    <report path="follow-up discussion (this session)" mode="brainstorm-adjudication" key_items="6" />
  </input_reports>

  <scope_note>
    Source items: the twenty-four product defects PB-01..PB-24 (each pinned by a strict xfail;
    the twenty-five strict xfails are the executable acceptance suite, green = complete), the
    report.py:105 datetime.utcnow deprecation, the demographics dead-key removal, and the six
    locked adjudications from the follow-up discussion:
      (i)   A1 physio: fail-loud PhysioParseError on SampleTime &lt;= 0, plus a TR-versus-acquisition-window
            agreement guard and a PULS/RESP rate-agreement guard.
      (ii)  A2 staging: clean the per-session staging leaf at the start of convert_to_staging,
            scoped strictly to the single sub-{sub}/ses-{ses} directory, and logged.
      (iii) A3 manifest: update_manifest raises ValidationError on a status outside VALID_STATUSES.
      (iv)  A4 classifier fail-loud: raise a new blocking NavigatorDropError when an EPI-physics
            multi-volume series would be silently dropped as a navigator (Rule 3); load
            SoftwareVersions onto Series for the error context.
      (v)   Diffusion single-band reference: recognise the diffusion SBRef signature and route it
            to dwi/ with a _sbref suffix (new Role).
      (vi)  Demographics: delete the always-None getattr and its dead pickle key (does NOT add
            demographics to participants.tsv).
    Adjudications (i) TR-window/rate guards, (ii), (iii), (iv), and (v) are NOT pinned by any
    existing test. Each carries a mandatory /test follow-up. All new physio guards and the
    NavigatorDropError guard are specified against header fields that the minimal fixtures already
    satisfy, so they do not regress the current 356-test green baseline. The golden-file PMU/DICOM
    test is target_mode=test and is OUT OF SCOPE here.
  </scope_note>

  <changes>

    <!-- ============================================================ -->
    <!-- FOUNDATION: new error classes -->
    <!-- ============================================================ -->
    <change id="C1" priority="P0" source_item="PB-19, A1, A4">
      <file path="fmri_bids_recon/errors.py" action="modify" />
      <description>
        Add three new blocking error classes so downstream fail-loud changes have a target. All
        subclass GuardError (BLOCKING; exit code 1 via the existing __main__ GuardError handler),
        matching the established taxonomy.
      </description>
      <spec>
        Define, alongside the existing GuardError subclasses:
          class ConversionError(GuardError): """dcm2niix returned a non-zero exit status."""
          class PhysioParseError(GuardError): """A PMU physio log carried no usable sampling rate."""
          class NavigatorDropError(GuardError): """An EPI-physics multi-volume series would be dropped as a navigator."""
        Follow the existing subclass pattern exactly (same __init__/context signature the sibling
        GuardError subclasses use). No change to exit-code mapping is needed: GuardError already maps
        to exit code 1 in _cmd_convert / _cmd_assemble.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive; no existing symbol is altered.</risk>
      <rollback>Delete the three class definitions.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- IntendedFor path repair (PB-01, PB-02) -->
    <!-- ============================================================ -->
    <change id="C2" priority="P0" source_item="PB-01, PB-02">
      <file path="fmri_bids_recon/stage3_map.py" action="modify" />
      <description>
        Enrich the mutable Mapping dataclass with a series-number to BIDS-relative-path index. This
        is the channel by which assemble (which knows each series' final on-disk BIDS path) informs
        render (which currently reconstructs the path from a staging path and fails). render's
        4-argument signature is FROZEN by test_render, so the fix flows through the shared Mapping
        object rather than through render's parameters.
      </description>
      <spec>
        Add to the Mapping dataclass:
          bids_relative_paths: dict[int, str] = field(default_factory=dict)
        Keyed by series_number; value is the session-subject-relative POSIX path of the emitted
        NIfTI (e.g. "ses-01/func/sub-001_ses-01_task-rest_run-01_bold.nii.gz"). Populated by C3,
        consumed by C7. field/default_factory import already present.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive field with a default; existing Mapping construction is unaffected.</risk>
      <rollback>Remove the field.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- Role enum extension for the diffusion SBRef (adjudication v) -->
    <!-- ============================================================ -->
    <change id="C3" priority="P1" source_item="adjudication (v) diffusion-SBRef">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>
        Add a Role enum member for the diffusion single-band reference so the classifier can assign
        it a positive role and assemble can route it to dwi/.
      </description>
      <spec>
        In the Role enum add: DWI_SBREF = "dwi_sbref". Placed adjacent to DWI for readability.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive enum member.</risk>
      <rollback>Remove the member (requires reverting C10 and C11 which reference it).</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- Series carries SoftwareVersions (adjudication iv context) -->
    <!-- ============================================================ -->
    <change id="C4" priority="P1" source_item="adjudication (iv) A4">
      <file path="fmri_bids_recon/sidecar.py" action="modify" />
      <description>
        Load the Siemens software line onto Series so NavigatorDropError can name the platform in its
        context. Added as the LAST Series field with a default so existing positional/keyword
        constructions (including test fixtures) are unaffected.
      </description>
      <spec>
        In the frozen Series dataclass, append as the final field:
          software_versions: str | None = None
        In load_series, populate it: software_versions=raw.get("SoftwareVersions"). The conftest
        _series factory and make_series need no change because the field defaults to None (a /test
        follow-up may add a fixture that sets it).
      </spec>
      <dependencies>none</dependencies>
      <risk>low - trailing defaulted field on a frozen dataclass; no existing constructor breaks.</risk>
      <rollback>Remove the field and the loader line.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- assemble: BIDS path population + entity disambiguation cluster -->
    <!-- ============================================================ -->
    <change id="C5" priority="P0" source_item="PB-01, PB-02, PB-12, PB-13, PB-16, PB-17, adjudication (v)">
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>
        Six edits to the per-series assembly loop and return, all in one file (execute as one
        serialized edit group). (a) PB-01/02: every emitting branch records its BIDS-relative path
        into mapping.bids_relative_paths[snum]. (b) PB-13: T1W and T2W gain a run- entity so two
        same-suffix anatomicals at different geometries do not overwrite. (c) PB-12: SBREF derives
        its run index from its parent BOLD, not from run_indices[snum] (a KeyError today). (d) PB-17:
        DWI gains dir-/run- entities so two diffusion acquisitions do not overwrite. (e) PB-16: an
        orphan fieldmap (snum not in fmap_pair_lookup) is copied to sourcedata and raises a
        ReviewFlag instead of being silently dropped. (f) adjudication (v): a new Role.DWI_SBREF
        branch writes to dwi/ with a _sbref suffix.
      </description>
      <spec>
        Preamble: the assemble signature is
          assemble(roles, series_map, labels, run_indices, mapping, excluded, unclassified, config,
                   participant, staging_dir) -> AssemblyResult
        sub = participant.sub; ses = participant.ses; sub_dir = bids_root/f"sub-{sub}";
        ses_dir = sub_dir/f"ses-{ses}". The subject-relative emitted path is dest.relative_to(sub_dir).

        (a) PB-01/02 path recording. In EACH branch that writes a NIfTI to `dest` (T1W, T2W, BOLD,
            SBREF, DWI, DWI_SBREF, FMAP_FUNC, FMAP_DWI), after `bids_files.append(dest)` add:
              mapping.bids_relative_paths[snum] = dest.relative_to(sub_dir).as_posix()

        (b) PB-13 anat run-. Replace the fixed stems
              f"sub-{sub}_ses-{ses}_T1w"  and  f"sub-{sub}_ses-{ses}_T2w"
            with a run-disambiguated stem. Compute a per-suffix run index by acquisition order:
            before the loop, build ordered lists of the T1W series-numbers and T2W series-numbers
            (sorted by series AcquisitionDateTime, falling back to series_number), and a
            anat_run_index: dict[int,int] assigning 1-based positions. In the T1W branch:
              run_idx = anat_run_index[snum]
              stem = f"sub-{sub}_ses-{ses}_run-{run_idx:02d}_T1w"
            and symmetrically for T2W. Test only requires two distinct files; run- is the BIDS-
            sanctioned disambiguator (test_two_anatomicals_at_different_geometries_do_not_overwrite_each_other).

        (c) PB-12 sbref run-index. In the SBREF branch, replace `run_idx = run_indices[snum]` with a
            lookup via the parent BOLD. The parent is the next chronological same-stem BOLD (the same
            adjacency Rule 9 in classify used to label it SBREF). Resolve it as: find the BOLD series
            whose task label equals labels[snum] and whose run is the one this SBRef shares; concretely,
            locate the BOLD survivor that is the chronological successor of this SBRef with a matching
            description stem and read run_indices[bold_snum]. Assign that run index to the SBRef stem:
              stem = f"sub-{sub}_ses-{ses}_task-{labels[snum]}_run-{run_idx:02d}_sbref"
            (test_an_sbref_inherits_the_run_index_of_its_bold expects
             sub-001_ses-01_task-rest_run-01_sbref.nii.gz).

        (d) PB-17 dwi dir-/run-. Replace the fixed stem f"sub-{sub}_ses-{ses}_dwi" with dir-/run-
            entities. dir- comes from the signed phase_encoding_direction of the series (map "j"->"PA",
            "j-"->"AP", "i"->"LR", "i-"->"RL", consistent with the fmap dir_label convention already in
            stage3_map; reuse that helper if one exists, else add a local _pe_to_dir(series)). run-
            comes from acquisition order among the DWI series (build a dwi_run_index dict analogous to
            anat_run_index). stem = f"sub-{sub}_ses-{ses}_dir-{dir_label}_run-{run_idx:02d}_dwi".
            Companion .bval/.bvec copy logic is retained, keyed off the new stem
            (test_two_diffusion_series_do_not_overwrite_each_other expects two files).

        (e) PB-16 orphan fieldmap. In the FMAP_FUNC/FMAP_DWI branch, replace the current
              if snum not in fmap_pair_lookup:
                  continue
            with:
              if snum not in fmap_pair_lookup:
                  sd_dest = sd_base / "unpaired_fmap" / series.nifti_path.name
                  sd_dest.parent.mkdir(parents=True, exist_ok=True)
                  shutil.copy2(series.nifti_path, sd_dest)
                  sourcedata_files.append(sd_dest)
                  review_flags.append(ReviewFlag(
                      code="unpaired_fieldmap",
                      message=f"sub-{sub} ses-{ses}: fieldmap series {snum} has no validated pair; "
                              f"preserved under sourcedata/unpaired_fmap and not placed in fmap/.",
                  ))
                  continue
            (match the existing ReviewFlag constructor fields used elsewhere in this module).
            test_an_unpaired_fieldmap_is_not_silently_destroyed asserts the file appears in
            result.sourcedata_files OR result.review_flags is non-empty.

        (f) adjudication (v) DWI_SBREF branch. Add a branch:
              elif role == Role.DWI_SBREF:
                  dwi_dir = ses_dir / "dwi"; dwi_dir.mkdir(parents=True, exist_ok=True)
                  # inherit dir-/run- of the associated DWI run (same resolution as PB-17)
                  dir_label = _pe_to_dir(series)
                  run_idx = dwi_run_index.get(snum, 1)
                  stem = f"sub-{sub}_ses-{ses}_dir-{dir_label}_run-{run_idx:02d}_sbref"
                  dest = dwi_dir / f"{stem}.nii.gz"
                  _copy_nifti(series, dest); _write_json(dwi_dir/f"{stem}.json", scrub(series.raw))
                  bids_files.append(dest)
                  mapping.bids_relative_paths[snum] = dest.relative_to(sub_dir).as_posix()
                  scans_rows.append({"filename": str(dest.relative_to(ses_dir)),
                                     "acq_time": series.raw.get("AcquisitionDateTime","n/a")})
            NOTE: this branch is unpinned; a /test follow-up authors its fixture. Include the
            DWI_SBREF series numbers in dwi_run_index construction alongside DWI.
      </description>
      <spec>See the description; each lettered item is a discrete, independently reversible edit.</spec>
      <dependencies>C1, C2, C3</dependencies>
      <risk>medium - six edits to one hot loop. (a)-(e) are pinned by xfails and invert to green.
        (f) is unpinned and adds a new branch; guarded by the new Role so no existing series reaches it.</risk>
      <rollback>Revert each lettered edit independently; (f) is fully removable with C3/C10.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- render consumes the BIDS path index (PB-01, PB-02) -->
    <!-- ============================================================ -->
    <change id="C6" priority="P0" source_item="PB-01, PB-02">
      <file path="fmri_bids_recon/stage5_render.py" action="modify" />
      <description>
        render must read each target's final BIDS path from mapping.bids_relative_paths rather than
        from Series.nii_path (which does not exist; the attribute is nifti_path, PB-01) and rather
        than relative_to a staging path (which raises ValueError, PB-02). The 4-argument signature
        render(mapping, bids_root, sub, ses) is unchanged.
      </description>
      <spec>
        In the per-pair loop, for each target Series:
          rel = mapping.bids_relative_paths.get(target.series_number)
          if rel is None:  # target was not emitted (e.g. excluded); skip its IntendedFor entry
              continue
          bids_nii = sub_dir / rel        # sub_dir = bids_root / f"sub-{sub}"
        Replace the current `target_nii = Path(target.nii_path)` (PB-01 AttributeError) with bids_nii.
        Compute the IntendedFor value via the existing helper _subject_relative_path(bids_root, sub,
        bids_nii) (which now receives a real in-tree path, resolving PB-02). Compute the sidecar path
        via _sidecar_path(bids_nii). Retain _subject_relative_path and _pair_identifier unchanged
        (they carry their own unit tests). render is already invoked after assemble, so
        bids_relative_paths is populated by the time render runs.
      </spec>
      <dependencies>C2, C5</dependencies>
      <risk>low-medium - the IntendedFor writer is the module's core; the change is a source swap for
        the path, and test_render pins the resulting sidecar content.</risk>
      <rollback>Restore the prior target_nii derivation.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- classify: navigator fail-loud + diffusion SBRef rule (adj iv, v) -->
    <!-- ============================================================ -->
    <change id="C7" priority="P1" source_item="adjudication (iv) A4, adjudication (v) diffusion-SBRef">
      <file path="fmri_bids_recon/stage2_classify.py" action="modify" />
      <description>
        (a) A4: before Rule 3 assigns DROP_NAVIGATOR, raise NavigatorDropError when the to-be-dropped
        series carries EPI physics (a real BOLD/EPI run must never be discarded silently). (b) Add a
        diffusion-SBRef rule mirroring Rule 9 (chronological same-stem adjacency), placed before the
        Rule 10 UNCLASSIFIED fallthrough.
      </description>
      <spec>
        (a) In Rule 3, replace:
              if s.n_volumes > 1 and tok not in {"FMRI", "DIFFUSION"}:
                  roles[s.series_number] = Role.DROP_NAVIGATOR
                  continue
            with:
              if s.n_volumes > 1 and tok not in {"FMRI", "DIFFUSION"}:
                  if "EP" in s.scanning_sequence:
                      raise NavigatorDropError(
                          f"Series {s.series_number} is multi-volume EPI physics "
                          f"(ImageType[2]={tok!r}, SoftwareVersions={s.software_versions!r}) "
                          f"and would be dropped as a navigator; halting for adjudication.",
                          context={"series_number": s.series_number,
                                   "image_type": list(s.image_type),
                                   "software_versions": s.software_versions})
                  roles[s.series_number] = Role.DROP_NAVIGATOR
                  continue
            Import NavigatorDropError from .errors. This does NOT fire on the current cohort or on the
            existing navigator fixture (test_multivolume_series_outside_fmri_and_diffusion_is_a_navigator
            uses the default scanning_sequence=("GR",), which contains no "EP").

        (b) After Rule 9 (SBREF) and before Rule 10 (UNCLASSIFIED), add Rule 9b:
              # Rule 9b: diffusion single-band reference. A single-volume magnitude EPI whose next
              # chronological same-stem series is a DWI (DIFFUSION + b-values).
              if tok == "M" and s.n_volumes == 1 and "EP" in s.scanning_sequence:
                  pos = next((i for i, t in enumerate(by_time)
                              if t.series_number == s.series_number), None)
                  if pos is not None and pos + 1 < len(by_time):
                      nxt = by_time[pos + 1]
                      same_stem = (nxt.description.lower().strip() == s.description.lower().strip()
                                   or nxt.description.lower().startswith(
                                          s.description.lower().rstrip("_- ")))
                      if same_stem and modality_token(nxt) == "DIFFUSION" and _bval_exists(nxt):
                          roles[s.series_number] = Role.DWI_SBREF
                          continue
            This is unpinned; a /test follow-up authors its fixture. It cannot fire on existing
            fixtures unless one presents a single-volume "M" EPI immediately preceding a DWI.
      </spec>
      <dependencies>C1, C3, C4</dependencies>
      <risk>medium - both edits add positive behavior on paths that currently fall through. Verified
        non-regressing against the current classify fixtures; both are unpinned and require /test.</risk>
      <rollback>Remove the raise block (a) and the Rule 9b block (b) independently.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- __main__ convert: physio wiring, guard log, intermediate, staging, demographics -->
    <!-- ============================================================ -->
    <change id="C8" priority="P0" source_item="PB-09, PB-10, PB-11, PB-19, A2, demographics, PB-03(pickle)">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>
        Repairs to _cmd_convert: (a) PB-09 physio parsed per-file from the DICOM index, not by
        passing a directory to a single-file parser; (b) PB-10 associate against BOLD survivors and
        carry a keyed dict; (c) PB-11 guard_log records all fourteen guard names; (d) demographics
        dead-key removal; (e) PB-03 pickle extension: add series_map and unclassified so assemble can
        receive them. PB-19 and A2 live in stage1_convert (C13) but are triggered here.
      </description>
      <spec>
        (a) PB-09. Replace:
              physio_dicoms = parse_physio_dicom(staging.staging_dir)
            with an iteration over the source DICOM index (the only channel physio reaches, since
            dcm2niix skips Raw Data Storage):
              physio_logs = []
              for rec in staging.dicom_index.values():
                  if rec.sop_class_uid == "1.2.840.10008.5.1.4.1.1.66":
                      for fp in rec.file_paths:
                          physio_logs.append(parse_physio_dicom(fp))
            (parse_physio_dicom takes a single file Path.)

        (b) PB-10. Replace associate_physio(physio_dicoms, all_series) with association against the
            BOLD survivors:
              bold_series = [series_map[sn] for sn, role in roles.items() if role == Role.BOLD]
              physio_pairs = associate_physio(physio_logs, bold_series)
            physio_pairs is dict[int, PhysioLog] keyed by BOLD series_number. Keep the try/except, but
            it MUST NOT swallow PhysioAssociationError / PhysioParseError (both GuardError): narrow the
            except to the genuinely-optional case (physio absent), i.e. catch and warn only when no
            physio DICOM was found; let GuardError subclasses propagate to the outer GuardError handler.
            Concretely: run the parse/associate outside the broad `except Exception`, or re-raise if
            isinstance(physio_exc, GuardError).

        (c) PB-11. Replace the hard-coded guard_log:
              guard_log = {"dcm2niix_version_floor": True}
            with a dict populated with every name in stage6_validate.ALL_GUARD_NAMES set True as its
            guard executes without error. On a clean session (no physio), physio_geometry_agreement
            records vacuously True. Import ALL_GUARD_NAMES; build
              guard_log = {name: True for name in ALL_GUARD_NAMES}
            after all guards in this stage have run without raising (the guards themselves raise
            GuardError on failure, which aborts before this line). test_the_converted_session_records_
            every_guard_that_ran asserts sorted(guard_log) == sorted(ALL_GUARD_NAMES).

        (d) demographics removal. Delete:
              demographics = getattr(participant, "demographics", None)   (line ~154)
            and the "demographics": demographics entry in the intermediate dict (line ~170). Does NOT
            add demographics to participants.tsv (assemble's own sex/age/wave summary is unaffected).

        (e) PB-03 pickle extension. Add to the intermediate dict:
              "series_map": series_map,
              "unclassified": [series_map[sn] for sn, role in roles.items()
                               if role == Role.UNCLASSIFIED],
            so C9 can pass series_map and unclassified into assemble.
      </spec>
      <dependencies>C1, C7(Role.DWI_SBREF unaffected here), C13</dependencies>
      <risk>medium - convert is the pipeline entry; physio wiring and guard_log are pinned by
        integration tests.</risk>
      <rollback>Revert each lettered edit; the pickle keys are additive.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- __main__ assemble: call sites, registry merge/persist, report, cubids -->
    <!-- ============================================================ -->
    <change id="C9" priority="P0" source_item="PB-03, PB-04, PB-05, PB-06, PB-07, PB-08">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>
        Repairs to _cmd_assemble: PB-05 registry merge; PB-03 assemble call; PB-04 render call; PB-07
        per-session conversion report capturing patient_id_warnings; PB-06 registry persistence;
        PB-08 cubids two-argument call.
      </description>
      <spec>
        Unpickle additions (after the existing unpickle block ~line 260):
          series_map   = intermediate["series_map"]
          unclassified = intermediate["unclassified"]
          excluded     = intermediate.get("excluded", [])
          vol_updates  = intermediate.get("vol_updates", {})

        (PB-05) Replace `merged_registry.update(registry_delta)` (RegistryDelta is a dataclass, not a
          mapping; this raises TypeError) with:
            merged_registry.update(registry_delta.new_entries)
            merged_registry.update(vol_updates)

        (PB-03) Replace the assemble(...) call with the correct signature and capture the result:
            result = assemble(
                roles=roles,
                series_map=series_map,
                labels=labels_dict,
                run_indices=run_indices,
                mapping=mapping,
                excluded=excluded,
                unclassified=unclassified,
                config=config,
                participant=participant,
                staging_dir=staging_dir,
            )
          (Drop the demographics kwarg; assemble has no such parameter.) The param is named `labels`,
          not labels_dict.

        (PB-04) Replace the render(...) call with the frozen 4-argument form:
            render(mapping, Path(config.bids_root), sub, ses)

        (PB-07) Move write_conversion_report INTO the per-participant loop (it is a per-session
          report) and pass the full signature, using result.patient_id_warnings:
            write_conversion_report(
                bids_root=Path(config.bids_root), sub=sub, ses=ses,
                excluded=excluded, unclassified=unclassified,
                new_tasks={desc: e.label for desc, e in registry_delta.new_entries.items()},
                review_flags=review_flags, mapping=mapping,
                patient_id_warnings=result.patient_id_warnings,
                dcm2niix_version=version_str, engine_version=version_str,
                config_path=Path(args.config),
            )
          Remove the batch-level 2-argument call at ~line 315.

        (PB-06) Persist the merged registry. save_registry(config, path) serialises
          config.task_registry (NOT a passed dict), so update the config's registry in place first:
            config.task_registry.clear()
            config.task_registry.update(merged_registry)   # dict[str, TaskRegistryEntry]
            save_registry(config, args.config)
          (Mutating the dict contents works even if StudyConfig is frozen.) This persistence is a
          runtime precondition for PB-14 (C11).

        (PB-08) Replace generate_cubids_report(Path(config.bids_root)) with the 2-argument form:
            generate_cubids_report(Path(config.bids_root), Path(config.bids_root) / "code" / "cubids")
          (or the module's documented output_dir convention; any writable path satisfies the arity fix).
      </spec>
      <dependencies>C1, C5, C6, C8</dependencies>
      <risk>medium-high - the assemble/render/report call sites are the end-to-end assemble driver
        that the chained xfail covers; all are pinned.</risk>
      <rollback>Revert each call-site edit; unpickle additions are additive.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- __main__ physio write loop (PB-10 write side, PB-12 run index) -->
    <!-- ============================================================ -->
    <change id="C10" priority="P1" source_item="PB-10, PB-12">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>
        Fix the physio write loop: physio_pairs is a dict keyed by BOLD series_number, and
        write_physio has signature write_physio(log, run_prefix, bids_dir, bold). The current loop
        iterates the dict (yielding keys) and passes wrong kwargs.
      </description>
      <spec>
        Replace:
          for physio_pair in physio_pairs:
              write_physio(physio_pair, sub=sub, ses=ses, bids_root=Path(config.bids_root))
        with:
          for bold_snum, log in physio_pairs.items():
              label = labels_dict[bold_snum]
              run_idx = run_indices[bold_snum]
              run_prefix = f"sub-{sub}_ses-{ses}_task-{label}_run-{run_idx:02d}"
              func_dir = Path(config.bids_root) / f"sub-{sub}" / f"ses-{ses}" / "func"
              write_physio(log, run_prefix, func_dir, series_map[bold_snum])
        (The written-fixture contract pins bids_dir = the func directory and run_prefix =
        sub-...-task-...-run-... ; bold is the matched BOLD Series.)
      </spec>
      <dependencies>C8, C9</dependencies>
      <risk>low-medium - pinned by the physio integration path.</risk>
      <rollback>Restore the prior loop.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- labels: rename guard against the persisted registry (PB-14) -->
    <!-- ============================================================ -->
    <change id="C11" priority="P1" source_item="PB-14">
      <file path="fmri_bids_recon/labels.py" action="modify" />
      <description>
        The task-rename guard currently compares only within the current session's descriptions, so a
        label drift relative to the PERSISTED registry is not caught. Compare against the persisted
        registry (now written by C9/PB-06).
      </description>
      <spec>
        In resolve_labels, the rename-guard set
          old_registry_descs = set(registry.keys()) - current_bs_descs
        must be evaluated against the persisted registry passed in via config.task_registry (which C9
        now updates and save_registry persists), so a description present in the persisted registry
        under a different label than the incoming session triggers TaskRenameError. Concretely, retain
        the existing comparison but ensure `registry` is the persisted registry (config.task_registry),
        not a session-local delta; raise TaskRenameError when a persisted description maps to a
        changed label. Runtime dependency: PB-06 (C9) must persist the registry for the guard to have
        cross-session state on the next run.
      </spec>
      <dependencies>C9 (runtime: persisted registry)</dependencies>
      <risk>medium - guard semantics; pinned by the rename xfail.</risk>
      <rollback>Restore the within-session comparison.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- runs: volume-count tie handling (PB-15) -->
    <!-- ============================================================ -->
    <change id="C12" priority="P1" source_item="PB-15">
      <file path="fmri_bids_recon/runs.py" action="modify" />
      <description>
        Counter.most_common(1) breaks ties by insertion order, silently anointing an arbitrary volume
        count as the mode. On a tie, register nothing and raise a ReviewFlag instead.
      </description>
      <spec>
        Replace the unconditional mode selection at the top of check_volume_counts:
          mode_count = Counter(counts).most_common(1)[0][0]
        with tie detection:
          counter = Counter(counts)
          top = counter.most_common()
          if len(top) > 1 and top[0][1] == top[1][1]:
              # Ambiguous mode: do not register a new expected-volumes entry; flag for review.
              review_flags.append(ReviewFlag(
                  code="ambiguous_volume_mode",
                  message=f"Task {label!r}: no unique modal volume count among {sorted(set(counts))}; "
                          f"no registry entry created, all runs retained pending review."))
              # skip new_registry_entries assignment for this task; retain all bolds
          else:
              mode_count = top[0][0]
              ... existing exclusion / registration logic ...
        (Match the exact ReviewFlag fields and the surrounding surviving/excluded bookkeeping used in
        the current function.)
      </spec>
      <dependencies>none</dependencies>
      <risk>medium - alters exclusion logic; pinned by the tie xfail.</risk>
      <rollback>Restore the most_common(1) selection.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- stage1_convert: dcm2niix returncode + clean staging leaf (PB-19, A2) -->
    <!-- ============================================================ -->
    <change id="C13" priority="P1" source_item="PB-19, adjudication (ii) A2">
      <file path="fmri_bids_recon/stage1_convert.py" action="modify" />
      <description>
        (a) PB-19: inspect the dcm2niix return code and raise ConversionError on failure instead of
        proceeding over a partial conversion. (b) A2: at the start of convert_to_staging, clean the
        single per-session staging leaf so a re-run is a pure function of its current source DICOMs
        and cannot adopt stale sidecars from a prior attempt.
      </description>
      <spec>
        (b) A2 clean leaf (first, before invoking dcm2niix). The staging leaf is the passed `staging`
        directory (already sub-{sub}/ses-{ses}, built by __main__:93). Guard the scope strictly:
          if staging.exists():
              # scoped strictly to this one session leaf; never a parent
              for child in staging.iterdir():
                  if child.is_dir(): shutil.rmtree(child)
                  else: child.unlink()
              logger.info("Cleaned stale staging leaf for reproducible conversion: %s", staging)
          staging.mkdir(parents=True, exist_ok=True)
        (Do NOT rmtree the leaf itself and recreate across a parent; only its contents, so the caller's
        path handle stays valid. Log every clean.)

        (a) PB-19 returncode. Replace the unchecked
          subprocess.run(cmd, ...)
        with capture + inspection:
          proc = subprocess.run(cmd, capture_output=True, text=True)
          if proc.returncode != 0:
              raise ConversionError(
                  f"dcm2niix exited {proc.returncode} for staging {staging}.",
                  context={"returncode": proc.returncode, "stderr": proc.stderr[-2000:]})
        Import ConversionError from .errors. Preserve the existing stderr_output capture on
        StagingResult.
      </spec>
      <dependencies>C1</dependencies>
      <risk>medium - the clean step is destructive; scoped strictly to the session leaf's contents and
        logged. PB-19 is pinned; A2 is unpinned (/test follow-up).</risk>
      <rollback>Remove the returncode raise and the leaf-clean block.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- physio: association + StartTime + A1 guards (PB-20, PB-21, PB-23, A1) -->
    <!-- ============================================================ -->
    <change id="C14" priority="P1" source_item="PB-20, PB-21, PB-23, adjudication (i) A1">
      <file path="fmri_bids_recon/physio.py" action="modify" />
      <description>
        Four edits: PB-20 nearest-preceding association; PB-21 fail-loud when acq_info is absent;
        PB-23 StartTime recomputed on the PMU clock; A1 PhysioParseError on SampleTime &lt;= 0 plus a
        TR-versus-acquisition-window guard and a PULS/RESP rate-agreement guard.
      </description>
      <spec>
        (PB-20) In associate_physio, the current
            delta = abs((log_time - bold_time).total_seconds())
          picks the globally nearest run, which can be a run that STARTED AFTER the log. Restrict to
          runs that precede (or coincide with) the log and take the latest such:
            candidates = [b for b in bolds if bold_time(b) <= log_time]
            chosen = max(candidates, key=bold_time) if candidates else
                     min(bolds, key=lambda b: abs((log_time - bold_time(b)).total_seconds()))
          Return dict[int, PhysioLog] keyed by chosen BOLD series_number. (Test: log at minutes=16
          binds to run1 at minutes=11, not run2 at minutes=20.)

        (PB-21) In associate_physio, before using acq_info for the geometry/agreement checks, replace
          the current permissive `if log.acq_info is not None:` guard so that a MISSING acq_info is a
          hard failure, not a silent skip:
            if log.acq_info is None:
                raise PhysioAssociationError(
                    f"Physio log {log!r} has no ACQUISITION_INFO block; cannot verify run geometry.",
                    context={...})
          (Test with_acq_info=False expects PhysioAssociationError.) PhysioAssociationError already
          exists in the taxonomy.

        (PB-23) In write_physio, StartTime must be the offset between the physio recording start and
          the first volume, both on the PMU clock (tics since midnight x 2.5e-3 s). Replace the
          current
            start_time = dt_offset - physio_start_secs
          with a PMU-clock-only computation:
            first_volume_tics = log.acq_info.volume_table[0]["acq_start_tics"]   # first volume, PMU clock
            first_volume_secs = first_volume_tics * 2.5e-3
            rec = _seconds_since_midnight(log.acquisition_datetime)              # PMU recording open
            start_time = rec - first_volume_secs
          where _seconds_since_midnight parses the log's DICOM AcquisitionDateTime to seconds since
          midnight (hh*3600 + mm*60 + ss + frac). Because both terms share the tics-since-midnight
          reference, the reference cancels and the offset is exact. (Test: recording opens at 09:11:00,
          first volume 1 s later -> StartTime == approx(-1.0), abs &lt; 60.0.) If acq_info was absent,
          PB-21 has already raised.

        (A1) In write_physio, replace the fallback:
            sample_time_ticks = 1  # fallback
            for ch in (puls_channel, resp_channel):
                if ch is not None and ch.sample_time > 0:
                    sample_time_ticks = ch.sample_time
          with a fail-loud + agreement guards:
            sample_time_ticks = None
            for ch in (puls_channel, resp_channel):
                if ch is not None and ch.sample_time > 0:
                    sample_time_ticks = ch.sample_time; break
            if sample_time_ticks is None:
                raise PhysioParseError(
                    f"No channel in {run_prefix} reports a positive SampleTime; cannot derive "
                    f"SamplingFrequency.", context={"channels": list(log.channels)})
            # PULS/RESP rate-agreement guard
            rates = {name: ch.sample_time for name, ch in log.channels.items()
                     if name in ("PULS", "RESP") and ch is not None and ch.sample_time > 0}
            if len(set(rates.values())) > 1:
                raise PhysioParseError(
                    f"PULS/RESP sample rates disagree in {run_prefix}: {rates}.", context={"rates": rates})
            # TR-versus-acquisition-window agreement guard
            window_s = (log.acq_info.volume_table[-1]["acq_start_tics"]
                        - log.acq_info.volume_table[0]["acq_start_tics"] + 320) * 2.5e-3
            expected_s = bold.n_volumes * bold.repetition_time
            if abs(window_s - expected_s) > max(0.05 * expected_s, bold.repetition_time):
                raise PhysioParseError(
                    f"Acquisition window {window_s:.1f}s disagrees with n_volumes*TR "
                    f"{expected_s:.1f}s for {run_prefix}.",
                    context={"window_s": window_s, "expected_s": expected_s})
          Import PhysioParseError from .errors. The minimal fixtures satisfy all three guards
          (sample_time=20 &gt; 0; PULS and RESP both 20; window == n_volumes*TR by construction), so
          the current green tests do not regress. All three A1 guards are unpinned -> /test follow-up.
          Tune the exact window arithmetic and tolerance to the volume_table field names actually
          present on AcquisitionInfo (FirstTime/LastTime/volume_table with acq_start_tics).
      </spec>
      <dependencies>C1</dependencies>
      <risk>medium - four edits to the physio writer/associator. PB-20/21/23 are pinned; the A1 guards
        are unpinned and are specified to be satisfied by the minimal fixtures.</risk>
      <rollback>Revert each edit independently; the A1 guards are a self-contained block.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- manifest: enforce VALID_STATUSES (report A3) -->
    <!-- ============================================================ -->
    <change id="C15" priority="P1" source_item="adjudication (iii) A3">
      <file path="fmri_bids_recon/manifest.py" action="modify" />
      <description>
        update_manifest accepts any status string; a typo silently disables idempotency. Enforce
        VALID_STATUSES fail-loud (locked: raise ValidationError).
      </description>
      <spec>
        At the top of update_manifest, before any write:
          if entry.status not in VALID_STATUSES:
              raise ValidationError(
                  f"Manifest status {entry.status!r} is not one of {VALID_STATUSES}.",
                  context={"sub": entry.sub, "ses": entry.ses, "status": entry.status})
        Import ValidationError from .errors (already used elsewhere). Unpinned -> /test follow-up.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive guard at the function entry.</risk>
      <rollback>Remove the guard.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- deface: only record produced outputs (PB-22) -->
    <!-- ============================================================ -->
    <change id="C16" priority="P1" source_item="PB-22">
      <file path="fmri_bids_recon/deface.py" action="modify" />
      <description>
        The output path is appended unconditionally even when the defacing tool produced no file, so
        a missing output is reported as success. Append only if the output exists.
      </description>
      <spec>
        Replace the unconditional:
          output_paths.append(output_path)
        with:
          if output_path.exists():
              output_paths.append(output_path)
          else:
              logger.warning("Defacing produced no output for %s; not recorded.", output_path)
        (Match the module's existing logger usage.)
      </spec>
      <dependencies>none</dependencies>
      <risk>low - guards one append; pinned by the deface xfail.</risk>
      <rollback>Restore the unconditional append.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- tsv: lockfile outside the BIDS tree (PB-18) -->
    <!-- ============================================================ -->
    <change id="C17" priority="P1" source_item="PB-18">
      <file path="fmri_bids_recon/tsv.py" action="modify" />
      <description>
        upsert_tsv writes its lockfile as a sibling inside the BIDS tree, which bids-validator rejects,
        failing the pipeline's own output. Relocate the lockfile outside the tree.
      </description>
      <spec>
        Replace:
          lock_path = Path(str(path) + ".lock")
        with a lock outside the BIDS root, uniquely derived from the target's resolved path:
          import hashlib, tempfile
          digest = hashlib.sha1(str(Path(path).resolve()).encode()).hexdigest()[:16]
          lock_path = Path(tempfile.gettempdir()) / f"bids_recon_{digest}.lock"
        Retain the existing lock acquire/release semantics; ensure the lock is removed in the finally
        block (so no stray temp lock persists). test_assembly_leaves_no_non_bids_artefacts_in_the_tree
        asserts no *.lock remains anywhere under the BIDS root.
      </spec>
      <dependencies>none</dependencies>
      <risk>low-medium - concurrency-sensitive; the hash keeps per-target lock identity. Pinned.</risk>
      <rollback>Restore the in-tree lock path.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- stage6_validate: bids-validator absence (PB-24) -->
    <!-- ============================================================ -->
    <change id="C18" priority="P1" source_item="PB-24">
      <file path="fmri_bids_recon/stage6_validate.py" action="modify" />
      <description>
        run_bids_validator invokes the validator with no FileNotFoundError handler, so a missing
        binary surfaces as an opaque OSError rather than a domain error. Catch it and raise
        ValidationError (BLOCKING).
      </description>
      <spec>
        Wrap the subprocess.run(["bids-validator", ...]) call:
          try:
              proc = subprocess.run([...], capture_output=True, text=True)
          except FileNotFoundError as exc:
              raise ValidationError(
                  "bids-validator executable not found on PATH; cannot validate the BIDS tree.",
                  context={"error": str(exc)}) from exc
        Retain the existing non-zero-exit handling that already raises ValidationError. Import
        ValidationError if not already imported.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive exception mapping; pinned by the validator xfail.</risk>
      <rollback>Remove the try/except.</rollback>
    </change>

    <!-- ============================================================ -->
    <!-- report: timezone-aware timestamp (datetime.utcnow deprecation) -->
    <!-- ============================================================ -->
    <change id="C19" priority="P2" source_item="report.py:105 datetime.utcnow deprecation">
      <file path="fmri_bids_recon/report.py" action="modify" />
      <description>
        datetime.utcnow() is deprecated. Use a timezone-aware UTC timestamp.
      </description>
      <spec>
        At line 105 replace:
          datetime.utcnow().isoformat(timespec='seconds')
        with:
          datetime.now(datetime.UTC).isoformat(timespec='seconds')
        (Or datetime.now(timezone.utc) matching the module's existing import style; __main__ already
        uses datetime.datetime.now(datetime.timezone.utc).) Emits no DeprecationWarning; the trailing
        'Z' suffix in the format string is retained.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - one expression; removes 13 test-suite DeprecationWarnings.</risk>
      <rollback>Restore datetime.utcnow().</rollback>
    </change>

  </changes>

  <execution_order>
    C1; C2; C3; C4;                     <!-- foundations: errors, Mapping field, Role, Series field -->
    C13; C14; C12; C15; C16; C17; C18; C19;  <!-- leaf-module defect fixes (independent files) -->
    C7;                                 <!-- classify: navigator raise + diffusion-SBRef rule -->
    C5; C6;                             <!-- assemble populate/disambiguate, then render consume -->
    C8; C9; C10;                        <!-- __main__ convert then assemble then physio write loop -->
    C11                                 <!-- labels rename guard (runtime-depends on C9 persistence) -->
  </execution_order>

  <post_build_followups>
    The following require /test after the build (each behavior is currently UNPINNED by any test):
      - A1 TR-versus-acquisition-window guard and PULS/RESP rate-agreement guard (C14).
      - A2 clean-staging-leaf idempotency (C13).
      - A3 manifest VALID_STATUSES enforcement (C15).
      - A4 NavigatorDropError fail-loud on droppable EPI (C7a).
      - Diffusion single-band reference recognition and dwi/_sbref emission (C3, C5f, C7b).
    The golden-file PMU/DICOM regression test remains a separate /test design item (out of scope here).
    Per the test report, completion is a green suite with zero xfails and zero xpasses; run /test to
    confirm each strict xfail inverts to a pass and no new regression appears.
  </post_build_followups>
</implement_plan>
