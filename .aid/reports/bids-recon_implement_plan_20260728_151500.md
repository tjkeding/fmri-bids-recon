<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-28T15:15:00-04:00" />
  <input_reports>
    <report path="(none — scope resolved via conversational discussion this session, no upstream brainstorm/cr report file)" mode="conversational" key_items="3" />
  </input_reports>

  <changes>

    <change id="C1" priority="P0" source_item="conversational: physio ingestion redesign, item 1 (classification layer)">
      <file path="fmri_bids_recon/sidecar.py" action="modify" />
      <description>
        Add spec-grounded classification distinguishing a physiological-recording JSON sidecar from an
        imaging sidecar, and change load_series() to skip NIfTI-companion resolution for the former.
        Replaces the filename-pattern approach originally considered; classification is based on the
        BIDS specification's three REQUIRED _physio.json fields (SamplingFrequency, StartTime, Columns —
        verified against BIDS spec v1.11.1, stable docs), which are vendor/converter/dcm2niix-version
        agnostic. Any sidecar NOT carrying all three fields is still required to resolve a NIfTI companion
        via the existing _find_nifti() hard-halt — this preserves the conversion-integrity guarantee for
        genuine imaging series; it must not be weakened into "any missing NIfTI is acceptable."
      </description>
      <spec>
        Add a module-level constant and a private helper, placed just above load_series():

        ```python
        _PHYSIO_REQUIRED_FIELDS = ("SamplingFrequency", "StartTime", "Columns")


        def _is_physio_sidecar(raw: dict) -> bool:
            """True if *raw* declares every BIDS-required _physio.json field.

            Per the BIDS specification (physiological recordings), SamplingFrequency,
            StartTime, and Columns are REQUIRED for any _physio.json sidecar,
            independent of scanner vendor or converter. This is the sole
            classification signal; filename conventions are deliberately not used,
            since they vary across dcm2niix versions and vendors.
            """
            return all(field in raw for field in _PHYSIO_REQUIRED_FIELDS)
        ```

        Modify load_series()'s signature and loop body:

        - Change the return type from `list[Series]` to `tuple[list[Series], list[Path]]`.
        - Initialize `physio_sidecars: list[Path] = []` alongside the existing `series_list`.
        - Inside the `for sidecar_path in sorted(staging.glob("*.json")):` loop, immediately after
          `raw: dict = json.load(fh)` is parsed: if `_is_physio_sidecar(raw)`, append `sidecar_path`
          to `physio_sidecars` and `continue` (skip `_find_nifti`, skip Series construction entirely
          for this sidecar).
        - At the end of the function, `return series_list, physio_sidecars` (series_list sorted by
          series_number as before; physio_sidecars in the glob's sorted order, no reordering needed).
        - Update the function's docstring: note the new return tuple, and that sidecars satisfying
          _is_physio_sidecar() are excluded from the NIfTI-companion requirement and returned separately
          for physio.py to consume.
      </spec>
      <dependencies>none</dependencies>
      <risk>medium - changes a public function's return signature; the sole call site (fmri_bids_recon/__main__.py:200) is updated in C4. No other internal or external call sites exist (verified: load_series is only imported/called in __main__.py).</risk>
      <rollback>git revert the commit touching this file; load_series() reverts to returning list[Series] only.</rollback>
    </change>

    <change id="C2" priority="P0" source_item="conversational: physio ingestion redesign, item 2 (retire custom parser, adopt dcm2niix native export)">
      <file path="fmri_bids_recon/physio.py" action="modify" />
      <description>
        Retire the custom Siemens PMU byte-level parser entirely and replace it with ingestion of
        dcm2niix's native per-channel BIDS physio export. Verified via direct byte-level inspection of a
        real ABCD/XA30 PhysioLog DICOM's private element (7fe1,1010) that the retired parser's assumed
        flat-ASCII-block format ("LogDataType: ...\nLogVersion: EJA_1\n...") does not match the real
        on-disk structure (a nested binary sub-record was found instead: an outer length-prefix framing
        the parser's model does match, but immediately followed by a second, unaccounted-for binary
        length field and an ASCII name token, not plain LogDataType text). dcm2niix's native decoder
        already produces correct output against this real data (verified: it wrote valid
        recording-cardiac/respiratory/external_trigger_physio .json/.tsv.gz triplets for all 6 PhysioLog
        series in the real dataset used for verification this session). This is a user-approved design
        decision to minimize scanner-specific implementation surface: dcm2niix already absorbs
        vendor-specific physio decoding (Siemens, GE, Philips) internally, so consuming its BIDS-standard
        output generalizes across scanners without this codebase carrying any vendor-specific parsing.
      </description>
      <spec>
        Remove entirely: `PhysioChannel`, `AcquisitionInfo`, `PhysioLog` dataclasses; `_LOG_VERSION_REQUIRED`,
        `_TRIGGER_THRESHOLD`, `_CHANNEL_NAMES` constants; `_parse_data_block()`, `_parse_acquisition_info_block()`,
        `_split_length_prefixed_blocks()`, `parse_physio_dicom()`, `_seconds_since_midnight()` (no longer
        needed — no absolute-clock alignment is performed against a native sidecar, which carries no
        AcquisitionDateTime field). Update the module docstring (currently describes Siemens PMU DICOM
        parsing) to describe the new native-export-ingestion responsibility.

        Add new dataclasses:

        ```python
        @dataclass
        class NativePhysioChannel:
            """One channel file from dcm2niix's native per-channel BIDS physio export.

            Parameters
            ----------
            label : str
                Channel identifier parsed from the filename token following
                '_recording-' (e.g. 'cardiac', 'respiratory', 'external_trigger').
            sampling_frequency : float
                SamplingFrequency from the channel's JSON sidecar, in Hz.
            start_time : float
                StartTime from the channel's JSON sidecar, in seconds.
            columns : tuple[str, ...]
                Columns from the channel's JSON sidecar, naming the TSV's fields
                in order. Read dynamically rather than assumed, since dcm2niix's
                per-channel column layout (e.g. a shared 'trigger' column
                alongside a stream-specific '<label>_trigger'/'external_trigger_peak'
                column) is not hardcoded by this codebase.
            data : dict[str, np.ndarray]
                Column name -> sample array, keyed exactly as declared in `columns`.
            json_path : Path
                Absolute path to the channel's JSON sidecar in the staging directory.
            tsv_path : Path
                Absolute path to the channel's .tsv.gz in the staging directory.
            """
            label: str
            sampling_frequency: float
            start_time: float
            columns: tuple[str, ...]
            data: dict[str, np.ndarray]
            json_path: Path
            tsv_path: Path
        ```

        Add discovery/loading:

        ```python
        def _load_native_channel(json_path: Path) -> NativePhysioChannel:
            """Load one dcm2niix-native _recording-<label>_physio.json/.tsv.gz pair.

            The label is parsed from the JSON filename (the token between
            '_recording-' and '_physio.json'). The companion TSV path is derived
            by replacing the '.json' suffix with '.tsv.gz'. The TSV is headerless
            (per BIDS convention for continuous recordings); columns are assigned
            by position from the JSON's `Columns` array — this must have as many
            entries as the TSV has tab-separated fields, else raise
            PhysioParseError (a malformed sidecar/TSV pairing, not a design
            ambiguity to guess through).
            """

        def discover_native_physio(
            physio_sidecar_paths: list[Path],
        ) -> dict[int, dict[str, NativePhysioChannel]]:
            """Group dcm2niix-native physio sidecars by SeriesNumber, then by channel label.

            *physio_sidecar_paths* is the list load_series() already classified via
            _is_physio_sidecar() and returned separately from imaging Series — this
            function does not re-classify by content, only groups the already-
            confirmed physio sidecars by filename structure (dcm2niix's own
            '{series_number}_..._recording-{label}_physio.json' naming convention,
            consistent with the '-f %s_%d' pattern stage1_convert.py already passes
            to dcm2niix). The series_number is parsed as the leading integer token
            before the first underscore. Returns {series_number: {label: NativePhysioChannel}}.
            """
        ```

        Add trigger-derived volume counting and association:

        ```python
        def _count_trigger_events(samples: np.ndarray) -> int:
            """Count discrete trigger pulses in *samples* via rising-edge detection.

            Threshold is the midpoint between the observed min and max sample
            value; a rising edge is any sample-to-sample transition from below
            to at-or-above that threshold. This is deliberately encoding-agnostic
            (works whether the channel is boolean 0/1 pulses or amplitude-coded
            events) rather than assuming a specific pulse height, since the exact
            numeric encoding of dcm2niix's native trigger channel has not been
            confirmed against a real file's full contents (only its JSON field
            names and TSV row count were confirmed this session, via the
            SOPClassUID/private-element checks — not the actual sample values).
            An incorrect edge-count here is caught downstream by the geometry
            guard in associate_native_physio() (mismatch against bold.n_volumes
            raises PhysioAssociationError), consistent with this pipeline's
            halt-on-uncertainty design principle: a wrong guess here fails loud,
            it does not silently propagate.
            """

        def _find_trigger_column(
            channels: dict[str, NativePhysioChannel],
        ) -> tuple[str, np.ndarray]:
            """Locate the BIDS-canonical shared trigger column across *channels*.

            Prefers an exact column name 'trigger' (the shared column dcm2niix
            reportedly duplicates across all three channel files); falls back to
            the first column name containing 'trigger' case-insensitively (e.g.
            'external_trigger_peak') if no exact match exists in any channel.
            Raises PhysioParseError if no candidate column is found in any channel
            — this is a hard failure, not a silent no-op, since num_volumes cannot
            be derived without it.
            """

        def associate_native_physio(
            recordings: dict[int, dict[str, NativePhysioChannel]],
            bolds: list[Series],
        ) -> dict[int, int]:
            """Associate each physio recording with a BOLD run.

            Algorithm shape is unchanged from the retired associate_physio(): for
            each recording, restrict to BOLD series whose series_number is <= the
            recording's series_number and take the one with the largest such
            series_number (nearest preceding); if none precede, fall back to the
            nearest by absolute |series_number difference|. SeriesNumber is
            substituted for the retired acquisition_datetime-based ordering
            because dcm2niix's native physio JSON carries no absolute-clock field
            — SeriesNumber is a standard DICOM field that increases monotonically
            with acquisition order in the same way acquisition_datetime did, so
            this is a like-for-like substitution of the ordering key, not a new
            algorithm.

            After selection, hard-guards the match: derives num_volumes via
            _find_trigger_column() + _count_trigger_events() and compares against
            the selected BOLD's n_volumes; raises PhysioAssociationError on
            mismatch (mirroring the retired function's num_volumes check).

            Note (disclosed, not silently dropped): the retired function's second
            geometry signal, num_slices (compared against bold.matrix[2]), is NOT
            reproduced. dcm2niix's native trigger channel exposes only per-volume
            timing, not slice-level timing, so no equivalent signal is available
            from this source. The guard is therefore single-signal
            (num_volumes) where it was previously two-signal
            (num_volumes + num_slices) — a real reduction in cross-check strength,
            surfaced here rather than silently absorbed.

            Returns {bold_series_number: physio_series_number}.
            """
        ```

        Rewrite `write_physio()`:

        ```python
        def write_physio(
            physio_series_number: int,
            staging_dir: Path,
            run_prefix: str,
            bids_dir: Path,
        ) -> list[Path]:
            """Copy dcm2niix's native per-channel physio export to the BIDS tree.

            Re-globs *staging_dir* for
            '{physio_series_number}_*_recording-*_physio.json' (and each JSON's
            companion .tsv.gz) directly — this is a fresh, minimal lookup for the
            one already-associated series, not a re-derivation of the association
            computed earlier in associate_native_physio(). For each channel found,
            copies (shutil.copy2, verbatim — no re-derivation or recombination)
            to bids_dir / f'{run_prefix}_recording-{label}_physio.tsv.gz' and the
            matching '.json'. dcm2niix's native output already satisfies the BIDS
            _physio.json contract (SamplingFrequency/StartTime/Columns), so no
            sidecar rewriting is performed.

            The retired write_physio()'s bespoke sourcedata/<run_prefix>_physio_raw.txt
            provenance dump is NOT reproduced: that dump existed to preserve the
            full unfiltered multi-channel log before the retired PULS+RESP-only
            2-column recombination discarded channels. Since this replacement
            copies dcm2niix's complete native per-channel output directly into
            func/ with no filtering step, there is no lossy transformation left to
            provide raw provenance against — the func/ output already is the
            complete data. (This is a scope simplification made possible by the
            redesign, not an oversight — flagged here for visibility since it
            removes a previously-existing output path.)

            Returns all paths written (2 files per channel found: .tsv.gz + .json).
            """
        ```

        Keep unchanged: `PhysioAssociationError`, `PhysioParseError` import from `.errors` (both classes
        stay as-is in errors.py; only their call sites move to the new functions above).
      </spec>
      <dependencies>none</dependencies>
      <risk>
        high - full rewrite of the physio ingestion layer. Two residual, explicitly disclosed
        uncertainties (both guard-protected, not silent): (1) the exact numeric encoding of dcm2niix's
        native trigger column was not confirmed against real sample values this session (only the JSON
        field names and outer container structure were confirmed) — _count_trigger_events()'s rising-edge
        heuristic is designed to be robust across plausible encodings, and a wrong count fails loud via
        the num_volumes geometry guard rather than silently producing misaligned physiological regressors;
        (2) the num_slices cross-check from the retired parser is dropped (not derivable from the native
        source), reducing the geometry guard from two signals to one. Recommend /test add both a synthetic
        fixture-driven suite (mirroring the retired parser's test structure) and flag the need for a
        real-file golden-test once a sample can be obtained, per test_physio.py's own pre-existing
        disclosed gap (it never had one either).
      </risk>
      <rollback>git revert the commit touching this file; physio.py reverts to the Siemens PMU parser. Note: since that parser was found not to match the real target platform's on-disk format, reverting restores non-functional (not just unmaintained) behavior against real ABCD/XA30 data — rollback is a code-state revert, not a return to a known-working state.</rollback>
    </change>

    <change id="C3" priority="P0" source_item="conversational: physio ingestion redesign, item 2 (retire PhysioLog-specific DICOM indexing)">
      <file path="fmri_bids_recon/stage1_convert.py" action="modify" />
      <description>
        Remove index_source_dicoms(), the DicomSeriesRecord dataclass, and the dicom_index field from
        StagingResult in their entirety. Verified via repo-wide grep that dicom_index/DicomSeriesRecord/
        index_source_dicoms are referenced nowhere except this file and the single physio call site in
        __main__.py:233 (updated in C4) — the whole mechanism existed solely to route around the
        (now-confirmed-false) assumption that dcm2niix silently skips PhysioLog series. With physio
        switching to consume dcm2niix's native output directly (C2), this indexing mechanism has no
        remaining purpose.
      </description>
      <spec>
        - Remove the `DicomSeriesRecord` dataclass (lines 23-32) and `index_source_dicoms()` function
          (lines 138-212) in full.
        - Remove the `dicom_index: dict[int, DicomSeriesRecord]` field from `StagingResult` and the
          corresponding `dicom_index=dicom_index` keyword in `convert_to_staging()`'s return construction.
        - Remove the `dicom_index = index_source_dicoms(source)` call inside `convert_to_staging()`.
        - Remove the `import pydicom` line (no longer used once index_source_dicoms is gone — confirm no
          other use of pydicom remains in this file before removing the import).
        - Update the module docstring (currently: "Also builds a DICOM index from the source files
          directly, which is the only channel through which PhysioLog series ... reach the engine,
          because dcm2niix silently skips them.") to remove this now-inaccurate claim; the module's
          responsibility is simply dcm2niix invocation and staging-directory management.
      </description>
      <dependencies>none</dependencies>
      <risk>low - deletion of dead code confirmed unused outside this file and the single call site C4 updates.</risk>
      <rollback>git revert the commit touching this file; index_source_dicoms()/DicomSeriesRecord/dicom_index are restored (dead but harmless).</rollback>
    </change>

    <change id="C4" priority="P0" source_item="conversational: physio ingestion redesign — call-site wiring">
      <file path="fmri_bids_recon/__main__.py" action="modify" />
      <description>
        Wire the new sidecar-classification (C1) and native-physio-ingestion (C2) functions into the
        Phase 1 (convert) and Phase 3 (assemble) loops, replacing the retired parse_physio_dicom/
        associate_physio/dicom_index-based flow. The intermediate JSON's `physio_pairs` value changes
        from `dict[int, PhysioLog]` (a rich dataclass round-tripped through json_intermediate.py's
        generic dataclass encoder) to `dict[int, int]` (bold_series_number -> physio_series_number) — a
        plain int-keyed, int-valued dict already handled natively by json_intermediate.py's existing
        `int_key_dict` codec, requiring no serialization changes there. Phase 3 re-derives the actual
        channel files fresh from staging_dir via write_physio()'s own minimal glob (staging is still
        present at Phase 3 time, before the next run's cleanup) rather than persisting loaded sample
        arrays through the intermediate file.
      </description>
      <spec>
        Import line 53 changes from:
        ```python
        from .physio import parse_physio_dicom, associate_physio, write_physio
        ```
        to:
        ```python
        from .physio import discover_native_physio, associate_native_physio, write_physio
        ```

        Line 200 changes from:
        ```python
        all_series = load_series(staging.staging_dir)
        ```
        to:
        ```python
        all_series, physio_sidecar_paths = load_series(staging.staging_dir)
        ```

        Lines 228-245 (the "Physio gate (convert phase)" block) change from the dicom_index/
        parse_physio_dicom/associate_physio flow to:
        ```python
        physio_pairs: dict = {}
        if config.physio:
            try:
                recordings = discover_native_physio(physio_sidecar_paths)
                bold_series = [series_map[sn] for sn, role in roles.items() if role == Role.BOLD]
                physio_pairs = associate_native_physio(recordings, bold_series)
            except Exception as physio_exc:
                if isinstance(physio_exc, GuardError):
                    raise
                logger.warning('Physio extraction skipped for sub=%s ses=%s: %s', sub, ses, physio_exc)
        elif not physio_disabled_logged:
            logger.info('Physio extraction disabled (config.physio=false); skipping.')
            physio_disabled_logged = True
        ```
        (unchanged: the GuardError re-raise / non-guard-error warn-and-continue pattern, since
        PhysioAssociationError and PhysioParseError remain GuardError subclasses per errors.py.)

        Line 266 (`'physio_pairs': physio_pairs,` inside the `intermediate` dict) is unchanged in
        structure — it now holds `dict[int, int]` instead of `dict[int, PhysioLog]`, requiring no
        change to the dump_intermediate() call itself.

        Lines 309-316 (the "Physio write gate" block in Phase 3) change from:
        ```python
        if config.physio:
            for bold_snum, log in physio_pairs.items():
                label = labels_dict[bold_snum]
                run_idx = run_indices[bold_snum]
                run_prefix = f'sub-{sub}_ses-{ses}_task-{label}_run-{run_idx:02d}'
                func_dir = bids_root / f'sub-{sub}' / f'ses-{ses}' / 'func'
                write_physio(log, run_prefix, func_dir, series_map[bold_snum])
        ```
        to:
        ```python
        if config.physio:
            for bold_snum, physio_snum in physio_pairs.items():
                label = labels_dict[bold_snum]
                run_idx = run_indices[bold_snum]
                run_prefix = f'sub-{sub}_ses-{ses}_task-{label}_run-{run_idx:02d}'
                func_dir = bids_root / f'sub-{sub}' / f'ses-{ses}' / 'func'
                write_physio(physio_snum, staging_dir, run_prefix, func_dir)
        ```
        (`staging_dir` is already in scope at this point in Phase 3 — defined at line 284 as
        `Path(config.staging_root) / f'sub-{sub}' / f'ses-{ses}'` — no new variable needed.)
      </spec>
      <dependencies>C1, C2, C3</dependencies>
      <risk>medium - call-site rewiring across two non-adjacent loops (Phase 1 convert, Phase 3 assemble) that must agree on the intermediate dict's new shape (dict[int,int]). Mitigated by the shape being simpler than before (plain int dict vs. a dataclass round-trip), reducing serialization risk relative to the current code.</risk>
      <rollback>git revert the commit touching this file; call sites revert to the retired parse_physio_dicom/associate_physio/dicom_index flow (compatible only with C2/C3 also being reverted together).</rollback>
    </change>

    <change id="C5" priority="P1" source_item="conversational: FSL environment-mutation fix (approved alongside physio work)">
      <file path="fmri_bids_recon/deface.py" action="modify" />
      <description>
        Fix _ensure_fsl_env(), confirmed via direct code read to mutate os.environ["PATH"] and
        os.environ["FSLOUTPUTTYPE"] globally and permanently with no scoping or restore. Change to a
        scoped, per-subprocess-call environment dict built from os.environ.copy(), passed explicitly to
        the subprocess.run() calls in deface(), eliminating blast-radius risk to unrelated later calls in
        the same process. The trusted-anchor-over-PATH resolution strategy (FSLDIR-based flirt
        resolution via _resolve_flirt()) is unchanged — only the mutation/scoping mechanism changes.
      </description>
      <spec>
        Replace `_ensure_fsl_env() -> None` with a function that returns a scoped env mapping instead of
        mutating globally:

        ```python
        def _build_fsl_env() -> dict[str, str]:
            """Return a per-call environment dict with FSL's bin directory reachable.

            Copies the current process environment and, when FSLDIR is set,
            appends $FSLDIR/bin to PATH (if not already present) so that
            pydeface's internal nipype calls can find flirt without requiring
            users to source fsl.sh. Also sets FSLOUTPUTTYPE to NIFTI_GZ if not
            already set. Unlike the prior _ensure_fsl_env(), this does NOT mutate
            os.environ — the returned dict is scoped to the specific
            subprocess.run() call it is passed to, with no effect on unrelated
            later calls in the same process.
            """
            env = os.environ.copy()
            fsl_dir = env.get("FSLDIR")
            if fsl_dir:
                fsl_bin = str(Path(fsl_dir) / "bin")
                current_path = env.get("PATH", "")
                if fsl_bin not in current_path.split(os.pathsep):
                    env["PATH"] = current_path + os.pathsep + fsl_bin
                    logger.info("Appended %s to PATH for FSL tool access (scoped to this call).", fsl_bin)
                if "FSLOUTPUTTYPE" not in env:
                    env["FSLOUTPUTTYPE"] = "NIFTI_GZ"
            return env
        ```

        In `deface()`:
        - Replace the single `_ensure_fsl_env()` call (currently at the top of the function, line 111)
          with `fsl_env = _build_fsl_env()` computed once per `deface()` invocation (not once per file —
          the environment does not vary across files within one call, so computing it once and passing
          it to each subprocess.run() call is sufficient and avoids redundant os.environ.copy() calls).
        - Add `env=fsl_env` as a keyword argument to both `subprocess.run()` call sites inside the
          `for input_path in nifti_files:` loop (the `pydeface` branch at line 144 and the
          `afni_refacer` branch at line 149).
      </spec>
      <dependencies>none</dependencies>
      <risk>low - narrow, mechanical change confined to one function and its two call sites within the same file; resolution strategy (FSLDIR trusted anchor) is unchanged, only the mutation scoping.</risk>
      <rollback>git revert the commit touching this file; _ensure_fsl_env() reverts to global os.environ mutation.</rollback>
    </change>

    <change id="C6" priority="P0" source_item="conversational: physio ingestion redesign — intermediate serialization cleanup">
      <file path="fmri_bids_recon/json_intermediate.py" action="modify" />
      <description>
        Remove the now-retired PhysioLog/PhysioChannel/AcquisitionInfo dataclasses from the generic
        dataclass encoder/decoder registry. No new registration is needed for the replacement types
        (NativePhysioChannel etc.) because, per C4, the intermediate's `physio_pairs` value is now a
        plain `dict[int, int]` (bold_series_number -> physio_series_number), already handled natively by
        the existing `int_key_dict` encode/decode branch — NativePhysioChannel/NativePhysioRecording data
        never crosses the intermediate-JSON boundary at all (Phase 3 re-derives channel files fresh from
        staging_dir via write_physio()'s own glob, per C2/C4).
      </description>
      <spec>
        - Change the import at line 23 from
          `from .physio import PhysioLog, PhysioChannel, AcquisitionInfo`
          — remove this import entirely (no replacement import needed, per the description above).
        - Remove `PhysioLog, PhysioChannel, AcquisitionInfo` from the `_DATACLASS_TYPES` tuple (lines 29-39).
      </spec>
      <dependencies>C2</dependencies>
      <risk>low - deletion of now-dead registry entries; the int_key_dict codec path already exists and is unchanged, so no new encode/decode logic is introduced.</risk>
      <rollback>git revert the commit touching this file; the import and dataclass registrations are restored (compatible only if C2 is also reverted, since PhysioLog/PhysioChannel/AcquisitionInfo would not otherwise exist).</rollback>
    </change>

    <change id="C7" priority="P2" source_item="conversational: README Guard System table accuracy (user-approved follow-up, surfaced as drift during this session)">
      <file path="README.md" action="modify" />
      <description>
        Correct the "Guard System" table, confirmed via direct comparison against
        fmri_bids_recon/stage6_validate.py's real ALL_GUARD_NAMES list to document 6 guard names that do
        not exist in code (fmap_phase_encoding_opposite, fmap_phase_encoding_label_match,
        fmap_geometry_match, fmap_coverage_complete, fmap_sbref_geometry_match, physio_association,
        conversion_success — 7 counted, see spec below for the precise mapping) while omitting 6 guard
        names that do (opposite_pe_within_pair, dir_label_pe_agreement, fieldmap_pairing_unambiguous,
        fieldmap_target_geometry_match, pe_axis_target_match, association_unambiguous, no_orphan_pairs).
        This is a pre-existing documentation-accuracy issue unrelated to the physio/FSL work in this
        plan, discovered as a side effect of tracing the guard system while designing C4's physio gate.
        The underlying guard system itself is not weaker than documented — if anything the real
        fieldmap-related guard set is more granular (7 named checks vs. README's 3) — this is a
        naming/documentation staleness fix, not a functional change.
      </description>
      <spec>
        Replace the "Guard System" table (README.md lines 178-196, the 14-row table between "The
        pipeline enforces 14 named guards:" and the "All guards initialize to False..." paragraph) with
        a table listing the real 14 entries from `ALL_GUARD_NAMES`, using descriptions grounded in the
        docstrings of the functions that set each guard (fmri_bids_recon/stage3_map.py's
        pair_fieldmaps() and map_fieldmaps() docstrings, and the existing descriptions for the 7 guards
        whose names are unchanged):

        | Guard | Description |
        |-------|-------------|
        | `dcm2niix_version_floor` | dcm2niix version meets the minimum verified floor. |
        | `anat_suffix_physics` | Physics-derived verdict agrees with the anatomical name token. |
        | `opposite_pe_within_pair` | Fieldmap pair members within a geometry group carry opposite phase-encoding directions. |
        | `dir_label_pe_agreement` | A fieldmap's _PA/_AP description token agrees with its physics-derived PE label. |
        | `fieldmap_pairing_unambiguous` | Every geometry group's fieldmap series split evenly into phase-encoding-opposite pairs (or no fieldmaps were present). |
        | `fieldmap_target_geometry_match` | A target series (BOLD/DWI/SBRef) has at least one geometry-compatible fieldmap pair available for assignment. |
        | `pe_axis_target_match` | The assigned fieldmap pair's phase-encoding axis matches the target's (implied by geometry compatibility). |
        | `association_unambiguous` | Multiple geometry-eligible fieldmap pairs for a target are disambiguated by nearest acquisition time without a tie. |
        | `no_orphan_pairs` | Every validated fieldmap pair is assigned to at least one target series. |
        | `label_injectivity` | No two distinct series descriptions resolve to the same BIDS label. |
        | `non_empty_labels` | No series description strips to an empty label. |
        | `no_label_drift` | A known description re-derives to the same label as previously recorded. |
        | `no_rename_collision` | No undeclared task rename detected via signature matching. |
        | `exact_volume_counts` | BOLD volume counts match the registered expected count. |

        Immediately following the table (before the existing "All guards initialize to False..."
        paragraph), add one clarifying sentence: "Two further invariants — dcm2niix conversion success
        and physio run association/geometry — are enforced via immediate exceptions
        (`ConversionError`, `PhysioAssociationError`, `PhysioParseError`, all `GuardError` subclasses)
        rather than the named meta-guard registry above, and so do not appear in `ALL_GUARD_NAMES`."
      </spec>
      <dependencies>none</dependencies>
      <risk>low - documentation-only change, no functional impact. Content grounded directly in stage3_map.py docstrings and stage6_validate.py's real ALL_GUARD_NAMES list (both read this session), not inferred.</risk>
      <rollback>git revert the commit touching this file; the stale table is restored.</rollback>
    </change>

  </changes>

  <execution_order>C1, C2, C3, C5, C7, C6, C4</execution_order>
</implement_plan>
