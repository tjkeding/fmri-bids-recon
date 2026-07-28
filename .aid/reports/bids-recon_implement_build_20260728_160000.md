<implement_report>
  <meta project="bids-recon" mode="implement" submodule="build" timestamp="2026-07-28T16:00:00-04:00" />
  <spec_ref>bids-recon_implement_plan_20260728_151500.md</spec_ref>
  <changes_applied>
    <change id="C1" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/sidecar.py" lines_changed="~20" />
      </files_modified>
      <notes>Added _PHYSIO_REQUIRED_FIELDS and _is_physio_sidecar(); load_series() now returns (list[Series], list[Path]) and skips NIfTI-companion resolution for sidecars carrying all three BIDS-required physio fields. No deviation from spec.</notes>
    </change>
    <change id="C2" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/physio.py" lines_changed="~250 (full rewrite)" />
      </files_modified>
      <notes>Retired the Siemens PMU byte-level parser (PhysioChannel, AcquisitionInfo, PhysioLog, parse_physio_dicom, _split_length_prefixed_blocks, _parse_data_block, _parse_acquisition_info_block, _seconds_since_midnight, _LOG_VERSION_REQUIRED, _TRIGGER_THRESHOLD, _CHANNEL_NAMES, associate_physio) entirely. Added NativePhysioChannel, _load_native_channel(), discover_native_physio(), _count_trigger_events(), _find_trigger_column(), associate_native_physio() (returns dict[int,int]; single-signal num_volumes guard, num_slices cross-check dropped per spec), and a rewritten write_physio(physio_series_number, staging_dir, run_prefix, bids_dir) that copies dcm2niix's native per-channel files verbatim. No deviation from spec. Sanity-checked post-build: module imports cleanly; all retired names confirmed absent; all new names confirmed present.</notes>
    </change>
    <change id="C3" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/stage1_convert.py" lines_changed="~90 (deletion)" />
      </files_modified>
      <notes>Removed DicomSeriesRecord, index_source_dicoms(), the dicom_index field/call, and the now-unused pydicom import. Updated module docstring. dcm2niix invocation, staging cleanup, and sidecar_paths collection unchanged. No deviation from spec.</notes>
    </change>
    <change id="C4" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/__main__.py" lines_changed="~15" />
      </files_modified>
      <notes>Import, load_series() unpacking, Phase 1 physio gate, and Phase 3 physio write gate all rewired to the new functions per spec. GuardError re-raise / warn-and-continue exception handling preserved unchanged. No deviation from spec.</notes>
    </change>
    <change id="C5" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/deface.py" lines_changed="~20" />
      </files_modified>
      <notes>_ensure_fsl_env() replaced with _build_fsl_env(), returning a scoped env dict instead of mutating os.environ globally. deface() computes it once per invocation and passes env=fsl_env to both subprocess.run() call sites (pydeface, afni_refacer). _resolve_flirt() and assert_deface_tools() unchanged. No deviation from spec.</notes>
    </change>
    <change id="C6" status="done" user_decision="n/a">
      <files_modified>
        <file path="fmri_bids_recon/json_intermediate.py" lines_changed="~5 (deletion)" />
      </files_modified>
      <notes>Removed the PhysioLog/PhysioChannel/AcquisitionInfo import and their entries in _DATACLASS_TYPES. Remaining six registrations (Series, FieldmapPair, Mapping, Excluded, RegistryDelta, TaskRegistryEntry) and all int_key_dict/encode/decode logic unchanged. No deviation from spec.</notes>
    </change>
    <change id="C7" status="done" user_decision="n/a">
      <files_modified>
        <file path="README.md" lines_changed="~16" />
      </files_modified>
      <notes>Guard System table replaced with the real 14-entry ALL_GUARD_NAMES list; the 7 stale guard names removed, the 7 real ones added. Clarifying sentence on ConversionError/PhysioAssociationError/PhysioParseError inserted immediately after the table. No other section modified. No deviation from spec.</notes>
    </change>
  </changes_applied>
  <summary>
    <total_changes>7</total_changes>
    <completed>7</completed>
    <skipped>0</skipped>
    <blocked>0</blocked>
  </summary>
  <post_build_verification>
    All six modified fmri_bids_recon modules (sidecar, physio, stage1_convert, deface, json_intermediate, __main__) were imported together via the bids-recon conda environment's Python interpreter after all seven changes landed: import succeeded with no errors. Confirmed programmatically: physio.py exposes discover_native_physio/associate_native_physio/write_physio/NativePhysioChannel and no longer exposes any retired name; stage1_convert.py no longer exposes index_source_dicoms or DicomSeriesRecord; deface.py exposes _build_fsl_env and no longer exposes _ensure_fsl_env; json_intermediate.py's _DATACLASS_TYPES contains exactly the six retained dataclasses. This is an import/consistency check only, not test execution.
  </post_build_verification>
  <next_steps>Recommended: run /test to validate all changes. In particular, C2's new logic needs synthetic-fixture coverage for discover_native_physio/associate_native_physio/write_physio, and a real-file golden test remains an open item (test_physio.py's retired suite never had one either, per its own docstring). C7's documentation fix should be checked against README's rendered form.</next_steps>
</implement_report>
