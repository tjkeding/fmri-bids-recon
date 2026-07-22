<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-15T10:57:45Z" />
  <input_reports>
    <report path="fmri-bids-recon_test_20260715_100651.md" mode="test" key_items="6" />
  </input_reports>

  <preamble>
    This specification covers four of the six items the input test report routed to
    /implement. During plan-phase code reading it was established that the report's
    reason constants describe first-faults that a prior build already fixed, and that
    the current on-disk state of each routed item is:

      - Rewrite _cmd_assemble call sites: ALREADY IMPLEMENTED (no change needed).
        __main__.py line 270 uses registry_delta.new_entries; line 271 merges
        vol_updates; every downstream call site (assemble, render,
        write_conversion_report, save_registry, generate_cubids_report) uses the real
        full signature; the AST-bind tests in test_cli_integration.py pass.

      - Wire physio in _cmd_convert: ALREADY IMPLEMENTED at the convert level
        (__main__.py lines 142-149 iterate staging.dicom_index, select Raw Data
        Storage records, parse each file, and associate against BOLD survivors only).
        The physio integration test still xfails for a cause that could not be
        confirmed by static reading; it is DEFERRED to /test --runxfail for a runtime
        traceback and is intentionally NOT specified here.

      - Render fieldmap-association interface: HALF IMPLEMENTED. Change C1 below.

      - dir-UNK refusal (DWI phase encoding): UNFIXED. Change C2 below.

      - Acquisition-signature persistence in TaskRegistryEntry: UNFIXED. Change C3 below.

      - sessions.tsv lock-file unlink: UNFIXED. Change C4 below.

    STRICT-XFAIL HANDOFF (applies to C1, C2, C3). The tests guarding these three
    changes are marked @pytest.mark.xfail(strict=True). Applying the product fix will
    make each guarded test PASS, which pytest reports as XPASS(strict) = FAILED until
    the xfail marker is removed. Marker removal is a /test-lane operation, not part of
    this build. Consequently, the post-build suite is EXPECTED to show strict-XPASS
    failures on the fixed tests; the subsequent /test run confirms the fix and removes
    the now-obsolete markers to reach the green, zero-xfail, zero-xpass state. C4 has
    no guarding test and will not change suite counts.
  </preamble>

  <changes>

    <change id="C1" priority="P0" source_item="RENDER_DEFECT (test_render.py); ASSEMBLE_DEFECT integration failure (test_cli_integration.py)">
      <file path="fmri_bids_recon/stage5_render.py" action="modify" />
      <description>
        render() addresses each fieldmap member's sidecar via member.nii_path
        (line 155). sidecar.Series exposes no nii_path attribute (the attribute is
        nifti_path), so any session carrying a fieldmap pair raises AttributeError;
        and nifti_path, even if renamed, points into the staging tree rather than the
        assembled BIDS tree. The target side of render() was already migrated to
        resolve BIDS-relative paths via mapping.bids_relative_paths (lines 146, 165).
        This change makes the fieldmap-member side symmetric with the target side.
        assemble() records mapping.bids_relative_paths[snum] for every emitted paired
        fieldmap member (stage4_assemble.py line 410), keyed by series_number, so the
        member's BIDS sidecar is resolvable the same way targets are.
      </description>
      <spec>
        In render() (fmri_bids_recon/stage5_render.py), sub_dir is already defined at the
        top of the function as `sub_dir = bids_root / f"sub-{sub}"`.

        Replace the fieldmap-member loop body (currently lines 154-161):

            for member in (pair.member_a, pair.member_b):
                fmap_nii = Path(member.nii_path)
                fmap_sidecar = _sidecar_path(fmap_nii)

                data = _read_sidecar(fmap_sidecar)
                data["IntendedFor"] = intended_for
                data["B0FieldIdentifier"] = [identifier]
                _write_sidecar(fmap_sidecar, data)

        with:

            for member in (pair.member_a, pair.member_b):
                member_rel = mapping.bids_relative_paths.get(member.series_number)
                if member_rel is None:      # member not emitted into the BIDS tree; nothing to annotate
                    continue
                fmap_nii = sub_dir / member_rel
                fmap_sidecar = _sidecar_path(fmap_nii)

                data = _read_sidecar(fmap_sidecar)
                data["IntendedFor"] = intended_for
                data["B0FieldIdentifier"] = [identifier]
                _write_sidecar(fmap_sidecar, data)

        member is a sidecar.Series (stage3_map.FieldmapPair.member_a/member_b are both
        typed Series); Series.series_number is present. bids_relative_paths is
        dict[int, str] keyed by series_number. No import change is required: `Path`
        remains used by _sidecar_path and the module's other helpers; `sub_dir /
        member_rel` yields a Path directly.

        Do NOT rename Series.nii_path to nifti_path anywhere; the fix removes the
        attribute access entirely rather than repointing it, which also eliminates the
        staging-vs-BIDS tree defect the reason constant describes.
      </spec>
      <dependencies>none (mapping.bids_relative_paths population by stage4 is already present)</dependencies>
      <risk>low - the target side already uses this exact pattern; the member side becomes symmetric. Only paired fieldmap members reach this loop (unpaired fmaps are diverted to sourcedata earlier and never appear in a pair), so member_rel is populated in the normal path; the None guard is defensive.</risk>
      <rollback>Restore the prior loop body using Path(member.nii_path).</rollback>
    </change>

    <change id="C2" priority="P1" source_item="PB-25 (test_assemble.py)">
      <file path="fmri_bids_recon/stage4_assemble.py" action="modify" />
      <description>
        For Role.DWI (line 349) and Role.DWI_SBREF (line 371), an unresolvable
        phase_encoding_direction is silently labelled dir-UNK. 'UNK' is not a
        phase-encoding direction; QSIPrep and fMRIPrep read the dir- entity together
        with PhaseEncodingDirection to orient the readout and drive susceptibility
        distortion correction, so a dir-UNK diffusion file disables the correction the
        entity exists to specify and is indistinguishable in the tree from a correctly
        labelled acquisition. Replace the 'UNK' fallback with a blocking
        PhaseEncodingError so an unresolvable direction refuses the session.
      </description>
      <spec>
        1. Extend the errors import at line 23 from:

               from .errors import ReviewFlag

           to:

               from .errors import ReviewFlag, PhaseEncodingError

           (PhaseEncodingError is a GuardError subclass in fmri_bids_recon/errors.py, so a
           raised PhaseEncodingError is caught by _cmd_assemble's GuardError handling
           and yields exit code 1, and satisfies the test's pytest.raises(GuardError).)

        2. At the Role.DWI branch, replace line 349:

               dir_label = PE_DIRECTION_TO_LABEL.get(series.phase_encoding_direction or "", "UNK")

           with:

               dir_label = PE_DIRECTION_TO_LABEL.get(series.phase_encoding_direction or "")
               if dir_label is None:
                   raise PhaseEncodingError(
                       f"Diffusion series {snum} has phase-encoding direction "
                       f"{series.phase_encoding_direction!r}, which does not map to a "
                       f"known BIDS dir- label; refusing to emit dir-UNK.",
                       context={
                           "series_number": snum,
                           "phase_encoding_direction": series.phase_encoding_direction,
                           "role": role.name,
                       },
                   )

        3. Apply the identical replacement at the Role.DWI_SBREF branch, line 371
           (same three-line get + None-check + raise block). The context role.name
           distinguishes DWI from DWI_SBREF in the raised error.

        PE_DIRECTION_TO_LABEL.get(key) with no default returns None when the key is
        absent; the empty string produced by `... or ""` is not a key in
        PE_DIRECTION_TO_LABEL, so an unresolvable direction triggers the raise while a
        resolvable direction ('j', 'j-', etc.) returns its PA/AP label unchanged.
      </spec>
      <dependencies>none</dependencies>
      <risk>medium - behavior change: a session with an unresolvable DWI or DWI_SBREF phase-encoding direction now fails with exit 1 (GuardError) instead of emitting dir-UNK. This is the intended blocking behavior. Sessions with resolvable directions are unaffected. No existing passing test asserts dir-UNK emission; the only test exercising this path expects the raise.</risk>
      <rollback>Restore the `.get(..., "UNK")` default at both branches and remove the PhaseEncodingError import addition.</rollback>
    </change>

    <change id="C3" priority="P1" source_item="PB-14 (test_labels.py)">
      <file path="fmri_bids_recon/config.py" action="modify" />
      <file path="fmri_bids_recon/labels.py" action="modify" />
      <description>
        The no_rename_collision guard in resolve_labels cannot fire on a genuine
        cross-session rename. It builds old_sigs from all_sig_by_desc, which is keyed
        only on descriptions present in the CURRENT session; in a real rename the old
        description is absent, so old_sigs is always empty and sig_match can never be
        true, while label_match cannot fire because a rename changes the label.
        TaskRegistryEntry carries no acquisition signature, so the registry cannot
        supply one either. Persist the acquisition signature at first registration and
        compare a new description's signature against the STORED signature of an absent
        old description.
      </description>
      <spec>
        config.py:

        (a) TaskRegistryEntry dataclass (currently label / expected_volumes /
            first_seen): add a trailing optional field so all existing keyword
            constructions remain valid and legacy YAML entries default to None:

                signature: Optional[tuple] = None

            Update the docstring to document signature as the persisted acquisition
            fingerprint tuple (repetition_time, effective_echo_spacing,
            multiband_factor, matrix), or None for entries registered before signature
            persistence.

        (b) load_config task_registry parsing (lines 218-227): read an optional
            "signature" key. PyYAML stores it as a list [tr, ees, mb, [m0, m1, m2]];
            reconstruct as a tuple with the matrix as an inner tuple so equality holds
            against acquisition_signature() output (which uses Series.matrix, a tuple):

                sig_raw = trec.get("signature")
                signature = None
                if sig_raw is not None:
                    tr_v, ees_v, mb_v, matrix_v = sig_raw
                    signature = (
                        tr_v, ees_v, mb_v,
                        tuple(matrix_v) if matrix_v is not None else None,
                    )
                task_registry[label] = TaskRegistryEntry(
                    label=str(trec["label"]),
                    expected_volumes=(
                        int(trec["expected_volumes"])
                        if trec.get("expected_volumes") is not None
                        else None
                    ),
                    first_seen=str(trec["first_seen"]),
                    signature=signature,
                )

        (c) save_registry serialization (lines 261-266): PyYAML safe_dump cannot
            represent Python tuples, so serialize signature as a list (matrix inner
            tuple -> list), and omit the key entirely when signature is None:

                entry_dict = {
                    "label": entry.label,
                    "expected_volumes": entry.expected_volumes,
                    "first_seen": entry.first_seen,
                }
                if entry.signature is not None:
                    tr_v, ees_v, mb_v, matrix_v = entry.signature
                    entry_dict["signature"] = [
                        tr_v, ees_v, mb_v,
                        list(matrix_v) if matrix_v is not None else None,
                    ]
                serialised_registry[label] = entry_dict

        labels.py:

        (d) resolve_labels new-entry registration (lines 321-325): populate signature
            from the new description's acquisition signature. new_sigs is already
            computed at the guard as all_sig_by_desc.get(desc, set()); compute the same
            here (or hoist it above the registration). A description's BOLD/SBREF series
            share physics, so the set is effectively singleton:

                new_sigs = all_sig_by_desc.get(desc, set())
                delta.new_entries[desc] = TaskRegistryEntry(
                    label=new_label,
                    expected_volumes=None,
                    first_seen=date.today().isoformat(),
                    signature=next(iter(new_sigs)) if new_sigs else None,
                )

        (e) resolve_labels rename guard (lines 340-360): augment old_sigs with the
            STORED registry signature so an absent old_desc still contributes its
            fingerprint. Change only the old_sigs construction; the raise block is
            unchanged:

                new_sigs = all_sig_by_desc.get(desc, set())
                for old_desc in old_registry_descs:
                    old_label = registry[old_desc].label
                    old_sigs = set(all_sig_by_desc.get(old_desc, set()))
                    stored_sig = getattr(registry[old_desc], "signature", None)
                    if stored_sig is not None:
                        old_sigs.add(stored_sig)
                    sig_match = bool(new_sigs & old_sigs)
                    label_match = (new_label == old_label)
                    if sig_match or label_match:
                        raise TaskRenameError( ... unchanged ... )

            Equality note: new_sigs elements are acquisition_signature() tuples with
            matrix as a tuple; stored_sig (from load_config reconstruction or from an
            in-memory registration merged into config.task_registry) also carries matrix
            as a tuple, so set intersection matches correctly.
      </spec>
      <dependencies>none among the four changes; parts (a)-(e) within C3 must all land together</dependencies>
      <risk>medium - touches the YAML round-trip and the rename guard. Backward-compatible: legacy entries without a stored signature default to None and the guard falls back to label_match (prior behavior). The existing passing rename test (test_labels.py line 250) has the old description present in-session as a DROP_DERIVED twin, so all_sig_by_desc supplies old_sigs independent of the stored signature; that test is unaffected.</risk>
      <rollback>Remove the signature field from TaskRegistryEntry, revert load_config and save_registry, and revert the resolve_labels registration and guard changes.</rollback>
    </change>

    <change id="C4" priority="P1" source_item="TSV-lock (test report D14)">
      <file path="fmri_bids_recon/tsv.py" action="modify" />
      <description>
        upsert_tsv unlinks the flock lockfile in its finally block (line 112).
        Unlinking a file whose inode is held under flock defeats mutual exclusion: a
        second process opens a newly created lockfile at the same path (a different
        inode) and its LOCK_EX succeeds immediately, admitting two processes into the
        read-modify-write critical section concurrently. Persist the lockfile so all
        contending processes lock the same inode.
      </description>
      <spec>
        In upsert_tsv, change the finally block (lines 108-114) from:

            finally:
                fcntl.flock(lock_fh, fcntl.LOCK_UN)
                lock_fh.close()
                try:
                    lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

        to:

            finally:
                fcntl.flock(lock_fh, fcntl.LOCK_UN)
                lock_fh.close()

        The lockfile lives under tempfile.gettempdir() with a name derived
        deterministically from the target path digest (line 40), so it is reused across
        processes and never appears in the BIDS tree; test_assemble.py's
        no-non-BIDS-artefact assertion (line 420) remains satisfied.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - the persistent zero-byte lockfile in the system temp directory is the correct flock idiom. No test currently guards this path, so suite pass/fail counts are unchanged by this change.</risk>
      <rollback>Restore the try/except lock_path.unlink(missing_ok=True) block.</rollback>
    </change>

  </changes>

  <execution_order>C1, C2, C3, C4</execution_order>

  <downstream_test_handoff>
    The following are /test-lane operations required to reach the green, zero-xfail,
    zero-xpass goal, and are intentionally OUT OF SCOPE for this /implement build:

    1. After C1/C2/C3 land, the strict-xfail markers on the now-passing tests must be
       removed: test_render.py (4 markers, RENDER_DEFECT), test_cli_integration.py
       line 328 (ASSEMBLE_DEFECT, which passes once render() no longer dies inside
       _cmd_assemble), test_assemble.py line 432 (PB-25), test_labels.py line 276
       (PB-14, conditional on item 2 below).

    2. PB-14 test dependency: test_a_cross_session_rename_is_detected supplies its
       registry entry via the conftest registry_entry fixture, which does not set a
       signature. For that xfail to flip to pass after C3, the fixture must construct
       the entry with a stored signature matching the renamed series' acquisition
       signature. This fixture change is a /test operation; C3 delivers the product
       capability but does not, on its own, flip this test.

    3. Physio: test_a_physio_log_in_the_source_directory_reaches_the_intermediate
       (test_cli_integration.py line 287) still xfails despite the convert-level physio
       wiring being present. Its cause could not be confirmed by static reading (the
       fixture BOLD geometry matches the payload, and index_source_dicoms ingests Raw
       Data Storage objects, which by static analysis should make the test XPASS). It
       requires a runtime traceback (pytest --runxfail) to determine whether the
       remaining fault is a convert-time BOLD geometry timing issue (a product defect)
       or a fixture inconsistency (a test defect) before any fix can be responsibly
       specified.

    4. C4 has no guarding test. Recommend /test add a concurrency regression test for
       upsert_tsv's flock mutual exclusion.
  </downstream_test_handoff>
</implement_plan>
