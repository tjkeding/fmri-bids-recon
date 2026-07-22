<test_report>
  <meta project="fmri-bids-recon" mode="test" timestamp="2026-07-14T21:57:42Z" />

  <pre_design_run>
    <total>0</total>
    <passed>0</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct>0</coverage_pct>
    <failures />
    <note>
      The `tests/` directory was empty at design entry. The engine had been written by
      `/implement build` and had never been executed against an assertion of any kind.
      The formal pre-design failure ledger is therefore EMPTY, and the disposition ledger
      below is not a record of pre-existing test failures: it is the record of defects
      discovered by the design phase itself, each of which is dispositioned under the same
      discipline (`product-bug` routes to `/implement`; assertions are never weakened to
      accommodate the defect).
    </note>
  </pre_design_run>

  <failing_test_dispositions>

    <!-- ================================================================
         Every entry below is disposition `product-bug`: the test correctly
         encodes the intended contract and the implementation is wrong.
         NO assertion was edited, weakened, tautologised, or suppressed.
         Each is pinned by a `@pytest.mark.xfail(strict=True)` carrying the
         verbatim reason text, so the marker inverts to a hard FAILURE the
         moment the defect is fixed. Twenty-five strict xfails cover the
         twenty-four defects (the end-to-end assemble drive covers a chain).
         ================================================================ -->

    <disposition test="test_each_fieldmap_member_declares_the_runs_it_is_intended_for" file="tests/test_render.py" classification="product-bug">
      <intended_contract>`render()` writes the fieldmap-to-target association into the BIDS sidecars, as `IntendedFor` (and/or `B0FieldIdentifier`/`B0FieldSource`), so that fMRIPrep can perform susceptibility distortion correction.</intended_contract>
      <current_test_claim>Each rendered fieldmap sidecar declares the runs it is intended for.</current_test_claim>
      <evidence>`fmri_bids_recon/stage5_render.py` dereferences `.nii_path` on a `Series`; the attribute defined in `fmri_bids_recon/sidecar.py` is `nifti_path`. The call raises `AttributeError` before any sidecar is written.</evidence>
      <action>route-to-implement (PB-01). Rename the attribute access to `nifti_path`.</action>
    </disposition>

    <disposition test="test_the_two_renderings_of_the_same_association_agree" file="tests/test_render.py" classification="product-bug">
      <intended_contract>The fieldmap association is rendered consistently across the `IntendedFor` and `B0FieldIdentifier`/`B0FieldSource` mechanisms, and `IntendedFor` paths are subject-relative per the BIDS specification.</intended_contract>
      <current_test_claim>The two renderings of the same association agree, and the rendered path is subject-relative.</current_test_claim>
      <evidence>Even with PB-01 corrected, `Series.nifti_path` still points into the STAGING tree, not the BIDS tree, so `_subject_relative_path` cannot compute a subject-relative path and raises (`fmri_bids_recon/stage5_render.py:147-167`, which the coverage run confirms never executes).</evidence>
      <action>route-to-implement (PB-02). This is the highest-consequence defect in the catalog: no dataset this pipeline produces carries any fieldmap association, so every fMRIPrep run downstream would silently proceed with NO susceptibility distortion correction. Render must resolve paths against the assembled BIDS tree, not staging.</action>
    </disposition>

    <disposition test="test_the_cli_can_call_the_stage_function_it_imports[assemble]" file="tests/test_cli_integration.py" classification="product-bug">
      <intended_contract>The CLI's call to `assemble()` binds to that function's signature.</intended_contract>
      <current_test_claim>The call site at `fmri_bids_recon/__main__.py:267` binds against `inspect.signature(assemble)`.</current_test_claim>
      <evidence>AST extraction of the call site plus `Signature.bind` raises `TypeError`. The CLI passes arguments that the callee does not declare.</evidence>
      <action>route-to-implement (PB-03). Reconcile the call site with the signature.</action>
    </disposition>

    <disposition test="test_the_cli_can_call_the_stage_function_it_imports[render]" file="tests/test_cli_integration.py" classification="product-bug">
      <intended_contract>The CLI's call to `render()` binds to that function's signature.</intended_contract>
      <current_test_claim>The call site at `fmri_bids_recon/__main__.py:280` binds against `inspect.signature(render)`.</current_test_claim>
      <evidence>`Signature.bind` raises `TypeError` on the extracted call site.</evidence>
      <action>route-to-implement (PB-04).</action>
    </disposition>

    <disposition test="test_a_converted_session_assembles_into_a_bids_tree" file="tests/test_cli_integration.py" classification="product-bug">
      <intended_contract>A session that converted cleanly assembles into a valid BIDS tree.</intended_contract>
      <current_test_claim>`cli._cmd_assemble` over a real converted intermediate exits 0 and produces a BIDS tree.</current_test_claim>
      <evidence>`fmri_bids_recon/__main__.py:264` calls `merged_registry.update(registry_delta)`, but `resolve_labels()` returns `tuple[dict[int, str], RegistryDelta]` and `RegistryDelta` is a dataclass, not a mapping. `dict.update()` raises `TypeError`. This fires BEFORE `assemble()` at line 267, so it is the FIRST fault on the assemble path; PB-03, PB-04, PB-07, PB-08 and PB-06 sit behind it.</evidence>
      <action>route-to-implement (PB-05). Merge the `RegistryDelta` through its own accessor, and merge `vol_updates` (currently placed on the intermediate at line 172 and never consumed).</action>
    </disposition>

    <disposition test="test_a_converted_session_assembles_into_a_bids_tree" file="tests/test_cli_integration.py" classification="product-bug">
      <intended_contract>`save_registry` persists the task registry updated by this session.</intended_contract>
      <current_test_claim>Covered by the same end-to-end assemble drive.</current_test_claim>
      <evidence>`fmri_bids_recon/__main__.py:320` calls `save_registry(config, merged_registry)`, passing a dict where a path is expected; the function then serialises `config.task_registry` regardless, so the merged registry is discarded even if the call succeeded.</evidence>
      <action>route-to-implement (PB-06). A task label learned this session would be lost, and the `no_label_drift` guard would then have nothing to compare against next session.</action>
    </disposition>

    <disposition test="test_the_cli_can_call_the_stage_function_it_imports[write_conversion_report]" file="tests/test_cli_integration.py" classification="product-bug">
      <intended_contract>The CLI calls `write_conversion_report()` with the twelve arguments it declares.</intended_contract>
      <current_test_claim>The call site at `fmri_bids_recon/__main__.py:315` binds against the signature.</current_test_claim>
      <evidence>`Signature.bind` raises `TypeError`: the CLI supplies 2 of 12 required arguments.</evidence>
      <action>route-to-implement (PB-07). This is PHI-relevant: `write_conversion_report()` is the function that performs the Section 8 sidecar PHI scrub audit. As called, the audit never runs, so a surviving identifier key in a BIDS sidecar would never be detected.</action>
    </disposition>

    <disposition test="test_the_cli_can_call_the_stage_function_it_imports[generate_cubids_report]" file="tests/test_cli_integration.py" classification="product-bug">
      <intended_contract>The CLI calls `generate_cubids_report()` with the arguments it declares.</intended_contract>
      <current_test_claim>The call site at `fmri_bids_recon/__main__.py:343` binds against the signature.</current_test_claim>
      <evidence>`Signature.bind` raises `TypeError`: 1 of 2 required arguments supplied.</evidence>
      <action>route-to-implement (PB-08).</action>
    </disposition>

    <disposition test="test_a_physio_log_in_the_source_directory_reaches_the_intermediate" file="tests/test_cli_integration.py" classification="product-bug">
      <intended_contract>A Siemens PMU physio log present in the source DICOM directory reaches the conversion intermediate as a physio pair.</intended_contract>
      <current_test_claim>Driving `cli._cmd_convert` over a source tree containing a PMU DICOM yields a non-empty `physio_pairs` on the intermediate.</current_test_claim>
      <evidence>`fmri_bids_recon/__main__.py:143` calls `parse_physio_dicom(staging.staging_dir)`, passing a DIRECTORY to a function that takes a FILE. The physio DICOM is Raw Data Storage (SOPClassUID `1.2.840.10008.5.1.4.1.1.66`), which dcm2niix skips, so it is never in the staging tree at all. The data it needs is already on the same local variable: `StagingResult.dicom_index`, built by `convert_to_staging()` and left unused.</evidence>
      <action>route-to-implement (PB-09). Read `staging.dicom_index`, which is the only channel through which a physio log can reach the engine.</action>
    </disposition>

    <disposition test="test_the_cli_can_call_the_stage_function_it_imports[write_physio]" file="tests/test_cli_integration.py" classification="product-bug">
      <intended_contract>The CLI calls `associate_physio()` and `write_physio()` with the arguments they declare, and consumes `associate_physio`'s return in its declared shape.</intended_contract>
      <current_test_claim>The call sites at `fmri_bids_recon/__main__.py:144` and `:292` bind against their signatures.</current_test_claim>
      <evidence>`associate_physio` is passed ALL series rather than the BOLD subset, and its dict return is iterated as though it were a list; `write_physio`'s keyword arguments do not bind.</evidence>
      <action>route-to-implement (PB-10).</action>
    </disposition>

    <disposition test="test_the_converted_session_records_every_guard_that_ran" file="tests/test_cli_integration.py" classification="product-bug">
      <intended_contract>`guard_log` records which of the fourteen named guards executed, so that `assert_guards_executed()` can detect a guard that was silently skipped.</intended_contract>
      <current_test_claim>After a clean conversion, `guard_log` contains an entry for every guard that actually ran.</current_test_claim>
      <evidence>`fmri_bids_recon/__main__.py:157` hard-codes the dict with `dcm2niix_version_floor` alone. Thirteen guards that DID run are recorded as not having run.</evidence>
      <action>route-to-implement (PB-11). The meta-guard is thereby inverted: it would report thirteen skipped guards on a session where all fourteen fired, which trains the operator to ignore it. That is worse than not having the meta-guard at all.</action>
    </disposition>

    <disposition test="test_an_sbref_inherits_the_run_index_of_its_bold" file="tests/test_assemble.py" classification="product-bug">
      <intended_contract>An SBRef carries the run index of the BOLD series it precedes.</intended_contract>
      <current_test_claim>An SBRef assembled alongside its BOLD receives that BOLD's run index.</current_test_claim>
      <evidence>`fmri_bids_recon/stage4_assemble.py` indexes `run_indices[snum]` with the SBRef's own series number, which is not a key in the mapping (run indices are assigned to BOLDs). Raises `KeyError` on any session containing an SBRef.</evidence>
      <action>route-to-implement (PB-12).</action>
    </disposition>

    <disposition test="test_two_anatomicals_at_different_geometries_do_not_overwrite_each_other" file="tests/test_assemble.py" classification="product-bug">
      <intended_contract>Two anatomicals of the same suffix are distinguished in the filename so that neither is lost.</intended_contract>
      <current_test_claim>Two T1w series at different geometries produce two distinct files.</current_test_claim>
      <evidence>The T1w/T2w filename is built with no `acq-` and no `run-` entity, so the second write silently overwrites the first. Data loss, no error, no log line.</evidence>
      <action>route-to-implement (PB-13). A repeated structural (the standard response to subject motion) destroys the first acquisition.</action>
    </disposition>

    <disposition test="test_a_cross_session_rename_is_detected" file="tests/test_labels.py" classification="product-bug">
      <intended_contract>The `no_rename_collision` guard detects a task that was renamed between sessions while keeping the same acquisition signature.</intended_contract>
      <current_test_claim>A new description sharing a registered description's acquisition signature raises `TaskRenameError`.</current_test_claim>
      <evidence>The guard compares only within the current session's series, so a rename that occurred BETWEEN sessions (the only way a rename can actually occur) is structurally unfireable.</evidence>
      <action>route-to-implement (PB-14). The guard must compare against the persisted task registry, which makes it dependent on PB-06 being fixed first.</action>
    </disposition>

    <disposition test="test_a_two_run_tie_does_not_silently_promote_the_first_listed_count" file="tests/test_runs.py" classification="product-bug">
      <intended_contract>An ambiguous volume-count majority is resolved deterministically, or flagged, rather than by an accident of list order.</intended_contract>
      <current_test_claim>A two-way tie in observed volume counts does not silently adopt whichever count appears first.</current_test_claim>
      <evidence>`fmri_bids_recon/runs.py` resolves the tie by list order. The resulting count is then written into the registry as the expected volume count and enforced against every future session.</evidence>
      <action>route-to-implement (PB-15). A coin-flip at registry-seeding time becomes a hard guard for the remainder of the study.</action>
    </disposition>

    <disposition test="test_an_unpaired_fieldmap_is_not_silently_destroyed" file="tests/test_assemble.py" classification="product-bug">
      <intended_contract>A fieldmap that could not be paired is either reported or preserved, not discarded.</intended_contract>
      <current_test_claim>An unpaired fieldmap survives assembly or is reported as excluded.</current_test_claim>
      <evidence>`fmri_bids_recon/stage4_assemble.py` drops it with no `Excluded` record and no `ReviewFlag`.</evidence>
      <action>route-to-implement (PB-16).</action>
    </disposition>

    <disposition test="test_two_diffusion_series_do_not_overwrite_each_other" file="tests/test_assemble.py" classification="product-bug">
      <intended_contract>Multiple DWI series are distinguished in the filename.</intended_contract>
      <current_test_claim>Two DWI series produce two distinct files.</current_test_claim>
      <evidence>The DWI filename carries neither `run-` nor `dir-`, so the second series silently overwrites the first. Same class of defect as PB-13, different modality.</evidence>
      <action>route-to-implement (PB-17).</action>
    </disposition>

    <disposition test="test_assembly_leaves_no_non_bids_artefacts_in_the_tree" file="tests/test_assemble.py" classification="product-bug">
      <intended_contract>Assembly leaves only BIDS-legal files in the BIDS tree.</intended_contract>
      <current_test_claim>After assembly, the tree contains no non-BIDS artefacts.</current_test_claim>
      <evidence>`fmri_bids_recon/tsv.py::upsert_tsv` leaves `.lock` files inside the BIDS tree. The BIDS validator flags these, so the `validated` status is unreachable.</evidence>
      <action>route-to-implement (PB-18). Place the lock outside the tree, or remove it in a `finally`.</action>
    </disposition>

    <disposition test="test_a_failed_conversion_stops_the_subject" file="tests/test_convert.py" classification="product-bug">
      <intended_contract>A dcm2niix invocation that fails stops the session rather than proceeding with a partial staging tree.</intended_contract>
      <current_test_claim>A non-zero dcm2niix exit raises rather than returning a `StagingResult`.</current_test_claim>
      <evidence>`fmri_bids_recon/stage1_convert.py:97` calls `subprocess.run` without `check=True` and never inspects `result.returncode`. A failed conversion yields an empty or partial staging tree that the downstream stages then treat as authoritative. The error taxonomy in `fmri_bids_recon/errors.py` has NO conversion error class, which corroborates that this path was never designed.</evidence>
      <action>route-to-implement (PB-19). Add a conversion error class to the taxonomy and check the return code.</action>
    </disposition>

    <disposition test="test_a_log_binds_to_the_run_it_followed_not_to_the_one_it_preceded" file="tests/test_physio.py" classification="product-bug">
      <intended_contract>A physio log is associated with the run it followed. The codebase's established temporal doctrine is nearest-preceding-strict (`pair_dt &lt; target_dt`), which `fmri_bids_recon/stage3_map.py` applies to fieldmap-to-target mapping.</intended_contract>
      <current_test_claim>A log acquired after run 1 and before run 2 binds to run 1.</current_test_claim>
      <evidence>`fmri_bids_recon/physio.py::associate_physio` scores candidates by ABSOLUTE temporal proximity, so a log that closely precedes the next run is bound to that next run instead of the one it recorded. This contradicts both the function's own docstring and the nearest-preceding-strict rule used everywhere else in the engine.</evidence>
      <action>route-to-implement (PB-20). Physio traces would be attached to the wrong BOLD run, which is a silent, systematic misattribution of the cardiac/respiratory regressors.</action>
    </disposition>

    <disposition test="test_a_log_that_cannot_be_geometry_checked_is_not_silently_accepted" file="tests/test_physio.py" classification="product-bug">
      <intended_contract>The `physio_geometry_agreement` guard verifies that a log's volume count agrees with its target's.</intended_contract>
      <current_test_claim>A log carrying no ACQUISITION_INFO block is not associated without a geometry check.</current_test_claim>
      <evidence>A log with no ACQUISITION_INFO is associated with NO geometry check performed, while the guard is still recorded in `guard_log` as having executed. The guard reports success on a check it did not perform.</evidence>
      <action>route-to-implement (PB-21). Either fail the association or record the guard as skipped; do not report a check that did not run.</action>
    </disposition>

    <disposition test="test_a_tool_that_writes_nothing_is_not_reported_as_a_successful_defacing" file="tests/test_deface.py" classification="product-bug">
      <intended_contract>`deface()`'s docstring promises "absolute paths to all defaced output files that were successfully created".</intended_contract>
      <current_test_claim>A defacing tool that exits zero without writing its output yields no output paths.</current_test_claim>
      <evidence>`fmri_bids_recon/deface.py:103` appends `output_path` unconditionally after the subprocess returns, never checking `output_path.exists()`. pydeface silently no-ops on an unreadable input, and `@afni_refacer_run` appends its own suffixes to `-prefix` rather than writing the literal path given.</evidence>
      <action>route-to-implement (PB-22). The error runs in the PHI-unsafe direction: the failure mode is "reported as defaced but is not", so an operator could publish an identifiable anatomical believing it had been defaced.</action>
    </disposition>

    <disposition test="test_the_start_time_is_the_offset_between_the_trace_and_the_first_volume" file="tests/test_physio.py" classification="product-bug">
      <intended_contract>BIDS `StartTime` is the offset, in seconds, between the start of the physio trace and the first volume of the associated run.</intended_contract>
      <current_test_claim>`StartTime` is a small offset (seconds), not a wall-clock difference.</current_test_claim>
      <evidence>`fmri_bids_recon/physio.py::write_physio` subtracts the PMU clock from the DICOM wall clock, yielding `StartTime == -33061.0` seconds on the fixture. These are two different clocks and the difference is meaningless.</evidence>
      <action>route-to-implement (PB-23). Downstream physio regressors would be aligned to a point roughly nine hours from the run.</action>
    </disposition>

    <disposition test="test_a_missing_validator_binary_is_reported_as_a_validation_failure" file="tests/test_validate.py" classification="product-bug">
      <intended_contract>An absent BIDS validator binary is reported as a validation failure, not as a crash.</intended_contract>
      <current_test_claim>A missing validator binary produces a validation failure rather than an unhandled `FileNotFoundError`.</current_test_claim>
      <evidence>`fmri_bids_recon/stage6_validate.py:102` calls `subprocess.run` with no `FileNotFoundError` handler, while the OPTIONAL cubids layer in the same file (lines 156-161) does catch it. The blocking layer is less careful than the optional one, so the whole session exits 2 (unexpected error) instead of reporting a validation failure.</evidence>
      <action>route-to-implement (PB-24).</action>
    </disposition>

    <!-- ================================================================
         AMBIGUOUS: design phase HALTED on these per the discipline.
         The intended contract cannot be determined from the available
         evidence. NO assertion was written, NO routing performed. These
         require explicit user adjudication before they become tests.
         ================================================================ -->

    <disposition test="(none written)" file="fmri_bids_recon/physio.py::write_physio" classification="ambiguous">
      <intended_contract>Undetermined.</intended_contract>
      <current_test_claim>No test written.</current_test_claim>
      <evidence>When the sample-time tick interval is absent, `write_physio` falls back to `sample_time_ticks = 1`, which fabricates a 400 Hz `SamplingFrequency` and writes it into the sidecar as though it were measured. The current behaviour is clearly wrong (a fabricated sampling rate is worse than a missing one), but the correct remedy is a design choice: raise, omit the key, or emit a `ReviewFlag`.</evidence>
      <action>halt-for-user. Requires adjudication.</action>
    </disposition>

    <disposition test="(none written)" file="fmri_bids_recon/stage1_convert.py::convert_to_staging" classification="ambiguous">
      <intended_contract>Undetermined.</intended_contract>
      <current_test_claim>No test written.</current_test_claim>
      <evidence>The staging directory is created with `exist_ok=True` and sidecars are harvested via `sorted(staging.rglob("*.json"))`, so a stale sidecar left by a previous conversion of a DIFFERENT session is silently adopted into the current one. The docstring describes the current behaviour rather than an intent, so it is not possible to tell whether the non-idempotency is deliberate (resumable staging) or an oversight.</evidence>
      <action>halt-for-user. Requires adjudication.</action>
    </disposition>

    <disposition test="(none written)" file="fmri_bids_recon/manifest.py::VALID_STATUSES" classification="ambiguous">
      <intended_contract>Undetermined.</intended_contract>
      <current_test_claim>`test_manifest.py` pins the vocabulary's CONTENT (the five documented states) but asserts nothing about its ENFORCEMENT, because the intended enforcement point is unknown.</current_test_claim>
      <evidence>`VALID_STATUSES` is declared and never referenced anywhere in the engine; `update_manifest` accepts any string. The blast radius is bounded (a typo'd status disables idempotency, causing re-processing rather than skipping, which is the safe direction), and the remedy is a design choice: raise, warn, or leave validation to callers.</evidence>
      <action>halt-for-user. Requires adjudication.</action>
    </disposition>

  </failing_test_dispositions>

  <design_phase>
    <tests_created>356</tests_created>
    <tests_modified>0</tests_modified>
    <files_created>
      <file path="tests/conftest.py" test_count="0" coverage_target="Shared fixtures. Constructs physics-faithful dcm2niix sidecars (`_series`) and materialises them to a staging tree that round-trips byte-exactly through `load_series()`." />
      <file path="tests/test_versions.py" test_count="8" coverage_target="dcm2niix version parsing and the version floor guard." />
      <file path="tests/test_sidecar.py" test_count="15" coverage_target="Sidecar load/parse; the Series model; the engine-owned deny-list scrub." />
      <file path="tests/test_classify.py" test_count="30" coverage_target="The ten ordered first-match-wins classification rules and the NORM/ND anatomical twin resolution pass. Physics only; never substring matching." />
      <file path="tests/test_labels.py" test_count="25" coverage_target="Label derivation; injectivity, non-emptiness, drift, and rename-collision guards." />
      <file path="tests/test_runs.py" test_count="16" coverage_target="Run indexing and the exact-volume-count guard (the one guard that excludes rather than halts)." />
      <file path="tests/test_map.py" test_count="26" coverage_target="Fieldmap-to-target mapping: nearest-preceding-strict temporal rule; the six mapping guards." />
      <file path="tests/test_tsv.py" test_count="9" coverage_target="TSV upsert semantics and concurrency behaviour." />
      <file path="tests/test_assemble.py" test_count="29" coverage_target="BIDS filename entity construction and the assembled tree's integrity." />
      <file path="tests/test_render.py" test_count="11" coverage_target="IntendedFor / B0FieldIdentifier rendering: the susceptibility distortion correction contract." />
      <file path="tests/test_physio.py" test_count="24" coverage_target="Siemens PMU parsing, temporal association, and geometry agreement." />
      <file path="tests/test_validate.py" test_count="14" coverage_target="BIDS validator and cubids invocation; the guard-executed meta-guard." />
      <file path="tests/test_convert.py" test_count="15" coverage_target="dcm2niix invocation, the staging tree, and the source DICOM index." />
      <file path="tests/test_report.py" test_count="13" coverage_target="All eight report sections, and the Section 8 sidecar PHI scrub audit from both sides (a surviving identifier raises; key NAMES are reported and VALUES never are; sourcedata/ is exempt)." />
      <file path="tests/test_config.py" test_count="22" coverage_target="Registry parse/validate/save: the staging-inside-bids concurrency hazard, BIDS label legality, round-trip fidelity." />
      <file path="tests/test_manifest.py" test_count="18" coverage_target="The idempotency contract. `should_skip` is True for `validated` alone; `assembled` is the dangerous case and is re-processed." />
      <file path="tests/test_deface.py" test_count="15" coverage_target="Exact argv per tool; the analysis anat/ tree is read-only; the returned paths mean what they say." />
      <file path="tests/test_guard_coverage.py" test_count="45" coverage_target="Structural meta-test: one entry per name in ALL_GUARD_NAMES, each naming the engine module that raises AND the distinct test that drives the guard to its violation. Proves the referents exist." />
      <file path="tests/test_cli_integration.py" test_count="21" coverage_target="Call-site binding harness over `__main__` (AST + inspect.signature), plus end-to-end drives of the convert and assemble commands stubbing only the dcm2niix boundary." />
    </files_created>
    <design_rationale>
      The suite was designed against the engine's own stated contracts (docstrings, signatures, the guard roster, the error taxonomy) rather than against its observed behaviour, which is the only way a test can find a defect rather than ratify one.

      Three structural decisions carry most of the diagnostic weight.

      First, `test_guard_coverage.py` closes a gap the engine's own meta-guard cannot close. `assert_guards_executed()` checks that every guard RAN; nothing checked that every guard WORKS. A guard that records itself as executed and then never raises is exactly as invisible as a guard that was never invoked, and it defeats the meta-guard while appearing to satisfy it. The coverage table names, for each of the fourteen guards, both the engine module that raises and the distinct test that drives it to its violation, and asserts that those referents exist. Requiring the proof tests to be pairwise distinct is what prevents one test from appearing to discharge two guards that share an exception class (`opposite_pe_within_pair` and `dir_label_pe_agreement` both raise `PhaseEncodingError`). All fourteen guards are proven to fire.

      Second, `test_cli_integration.py` binds the CLI's call sites to the callees' signatures by AST extraction plus `inspect.signature(...).bind(...)`. Six of the nine defects on the assemble path are call-signature mismatches that no unit test of either side could ever see: each function is correct in isolation, and the seam between them is where the engine is broken. This is the class of defect that a suite organised strictly by module would have missed entirely.

      Third, the fixtures build physics-faithful sidecars and materialise them to a real staging tree that round-trips through the real `load_series()`. This was not free: the first end-to-end drive surfaced that `conftest._series` omitted six keys the loader reads, so a materialised fieldmap lost the very physics the classifier discriminates on and re-loaded as something else. That was a FIXTURE gap, not a product bug, and it was fixed by making the fixture MORE faithful (never by relaxing an assertion). It is recorded here because it is the one place where a weaker fixture would have silently produced a green suite that tested a different series than the one it constructed.

      Every defect found is pinned by a `strict=True` xfail carrying its verbatim reason. Strictness is the load-bearing choice: a non-strict xfail would stay green after the defect is fixed, so the marker would rot into a permanent excuse. As written, each of the twenty-five inverts to a hard FAILURE the moment `/implement` corrects the underlying defect, which makes the xfail set an executable acceptance suite for the repair work rather than a list of apologies.
    </design_rationale>
  </design_phase>

  <post_design_run>
    <total>356</total>
    <passed>329</passed>
    <failed>0</failed>
    <errors>0</errors>
    <skipped>2</skipped>
    <xfailed>25</xfailed>
    <xpassed>0</xpassed>
    <coverage_pct>89</coverage_pct>
    <failures />
    <verification>
      Dispatched to `execution-agent-sonnet-medium` under the nonce+wrapper receipt protocol.
      `validate_io.py return --dispatch-site test:run_suite` returned `ok=true`.
      `verify_receipts.py` returned `ok=true` with all eight anti-fabrication checks matching:
      nonce, clock-in-window, duration, summary counts, the independent `--collect-only`
      oracle (356), and the tee'd receipt file's mtime, nonce, and summary line.
    </verification>
    <coverage_note>
      Statement coverage is 89% of 1598 statements. The deficit is concentrated in exactly
      two modules, and it is a symptom of the defects rather than a gap in the suite:
      `fmri_bids_recon/__main__.py` (63%) and `fmri_bids_recon/stage5_render.py` (57%). The assemble
      path dies at `__main__.py:264` (PB-05), so lines 267-348 are unreachable; render dies
      on the attribute error (PB-01), so lines 147-167 are unreachable. Those lines cannot
      be covered until the defects behind them are fixed. Re-measuring coverage after
      `/implement` is the correct check that the repair is complete.
    </coverage_note>
  </post_design_run>

  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>24</bugs_routed_to_implement>
    <recommendation>implement_fixes</recommendation>
    <rationale>
      Zero assertions were weakened, removed, tautologised, or wrapped in a suppressing
      try/except. The only edit to a pre-existing file made a fixture strictly MORE faithful
      to the loader it feeds. Every one of the twenty-five xfail markers carries an explicit,
      citable recorded reason and is `strict=True`.

      A `bugs_routed_to_implement` count of 24 is the positive outcome of this design phase,
      not a failure of it. The engine as built cannot complete an assemble, cannot write a
      fieldmap association, and never runs the PHI scrub audit. None of that was visible
      before this suite existed.
    </rationale>
  </summary>

  <action_items>

    <item priority="P0" target_mode="implement" description="PB-02 (with PB-01): render() cannot write any fieldmap association. Fix the .nii_path/.nifti_path attribute error, then resolve rendered paths against the assembled BIDS tree rather than the staging tree so _subject_relative_path can produce a subject-relative IntendedFor. Without this, every dataset the pipeline produces drives fMRIPrep with NO susceptibility distortion correction, silently. This is the defect with the largest scientific blast radius." />

    <item priority="P0" target_mode="implement" description="PB-07: write_conversion_report() is called with 2 of its 12 required arguments, so the Section 8 sidecar PHI scrub audit never executes. A surviving identifier key in a BIDS sidecar would reach the shared dataset undetected. Reconcile the call site." />

    <item priority="P0" target_mode="implement" description="PB-05: __main__.py:264 calls dict.update() on a RegistryDelta dataclass, raising TypeError. This is the FIRST fault on the assemble path; PB-03, PB-04, PB-06, PB-07 and PB-08 sit behind it and cannot be observed until it is fixed. Also merge vol_updates, which is placed on the intermediate and never consumed." />

    <item priority="P0" target_mode="implement" description="PB-03, PB-04, PB-08, PB-09, PB-10: five further call-signature mismatches between __main__ and the stage functions it imports (assemble, render, generate_cubids_report, parse_physio_dicom/associate_physio, write_physio). For PB-09 specifically: read staging.dicom_index, which convert_to_staging already builds and returns, rather than passing the staging directory to a function that takes a file. The physio DICOM is Raw Data Storage and is never in the staging tree at all." />

    <item priority="P0" target_mode="implement" description="PB-22: deface() appends its output path unconditionally without checking that the file exists, so a tool that exits zero without writing is reported as a successful defacing. The error runs in the PHI-unsafe direction: an operator could publish an identifiable anatomical believing it was defaced. Check output_path.exists() and either raise or omit the path." />

    <item priority="P0" target_mode="implement" description="PB-19: convert_to_staging() never checks dcm2niix's return code (stage1_convert.py:97), so a failed conversion yields a partial staging tree that downstream stages treat as authoritative. The error taxonomy in errors.py has no conversion error class at all, which corroborates that this path was never designed. Add the class and check the code." />

    <item priority="P1" target_mode="implement" description="PB-13 and PB-17: anatomical (T1w/T2w) and diffusion filenames carry no distinguishing entity (no acq-/run- for anat, no run-/dir- for DWI), so a second series of the same type silently overwrites the first. A repeated structural is the standard response to subject motion, which makes PB-13 a routine data-loss path, not an edge case." />

    <item priority="P1" target_mode="implement" description="PB-20: associate_physio() scores by absolute temporal proximity rather than the nearest-preceding-strict rule its own docstring states and stage3_map applies everywhere else in the engine. Physio traces bind to the wrong BOLD run, silently and systematically." />

    <item priority="P1" target_mode="implement" description="PB-23: write_physio() computes StartTime by subtracting the PMU clock from the DICOM wall clock (two different clocks), yielding -33061.0 s on the fixture. Physio regressors would be aligned to a point roughly nine hours from the run." />

    <item priority="P1" target_mode="implement" description="PB-11 and PB-21: the guard_log is hard-coded to a single guard, so the meta-guard reports thirteen guards as skipped on a session where all fourteen fired; and a physio log with no ACQUISITION_INFO is associated with no geometry check while its guard is still recorded as executed. A guard that reports a check it did not perform is worse than no guard, because it trains the operator to ignore the signal." />

    <item priority="P1" target_mode="implement" description="PB-14 and PB-06: the no_rename_collision guard compares only within the current session, so a cross-session rename (the only kind that can occur) is structurally unfireable; and save_registry() discards the merged registry, so a task label learned this session is lost. These are coupled: fixing the guard requires the persisted registry to actually persist." />

    <item priority="P1" target_mode="implement" description="PB-24: run_bids_validator() does not catch FileNotFoundError (stage6_validate.py:102), while the OPTIONAL cubids layer in the same file does (lines 156-161). A missing validator binary exits 2 (unexpected error) instead of reporting a validation failure." />

    <item priority="P2" target_mode="implement" description="PB-12, PB-15, PB-16, PB-18: an SBRef raises KeyError on run_indices lookup; a volume-count tie is resolved by list order and then frozen into the registry as a hard guard for the rest of the study; an unpaired fieldmap is discarded with no Excluded record and no ReviewFlag; and upsert_tsv leaves .lock files inside the BIDS tree, which the validator flags, making the validated status unreachable." />

    <item priority="P1" target_mode="test" description="Golden-file physio test against one real Siemens PMU DICOM. The current physio fixtures are self-referential: they are constructed to the vendor format the parser ASSUMES, so they would ratify a parser that misreads a real file. This is the single largest remaining gap in the suite and it cannot be closed without one real (de-identified) PMU DICOM. Required before the physio path is trusted." />

    <item priority="P2" target_mode="implement" description="report.py:105 uses the deprecated datetime.utcnow(), emitting a DeprecationWarning on every report write (13 in the current run). Replace with datetime.now(datetime.UTC)." />

    <item priority="P2" target_mode="implement" description="ParticipantEntry has no demographics field, so __main__.py:154's getattr(participant, 'demographics', None) is always None and the corresponding pickle key (line 170) is dead. Either add the field or remove the key." />

  </action_items>

  <items_requiring_user_adjudication>
    <note>
      Surfaced rather than resolved. Under the Test Design Discipline, an `ambiguous`
      disposition HALTS and is escalated; it is never silently encoded as a test.
    </note>
    <item id="A1" description="write_physio's sample_time_ticks = 1 fallback fabricates a 400 Hz SamplingFrequency and writes it to the sidecar as though measured. Current behaviour is wrong; the remedy (raise / omit the key / emit a ReviewFlag) is a design choice." />
    <item id="A2" description="convert_to_staging harvests sorted(staging.rglob('*.json')) from a directory created with exist_ok=True, so a stale sidecar from a previous conversion is silently adopted. The docstring describes the behaviour rather than an intent, so it cannot be determined whether the non-idempotency is deliberate (resumable staging) or an oversight." />
    <item id="A3" description="manifest.VALID_STATUSES is declared and never enforced; update_manifest accepts any status string. Blast radius is bounded and runs in the safe direction (a typo causes re-processing, not skipping). Remedy (raise / warn / leave to callers) is a design choice." />
    <item id="A4" description="The classifier keys fieldmap-vs-BOLD discrimination on XA/NumarisX ImageType[2] tokens. A VE11-era BOLD series would be dropped as DROP_NAVIGATOR. If this study includes any VE11 data, the classifier is platform-coupled in a way that silently discards functional runs. Confirm the scanner software baseline." />
  </items_requiring_user_adjudication>

  <process_observation>
    The `/implement build` report's `&lt;deviations&gt;` section flagged exactly ONE call-signature
    mismatch (`write_conversion_report`). The true count is six, and the build report therefore
    materially understates the defect surface it delivered. This is recorded because it bears on
    how much weight a build report's self-assessment can carry: it was produced without executing
    the code, and no assertion had ever been run against the engine at that point.
  </process_observation>

  <next_steps>
    Run `/implement` against this report. The twenty-five strict xfails constitute an executable
    acceptance suite for the repair: each inverts to a hard failure the moment its defect is fixed,
    so a green suite with zero xfails and zero xpasses is the completion criterion. Re-measure
    coverage afterwards; `__main__.py` and `stage5_render.py` should rise sharply, because their
    current uncovered lines are unreachable rather than untested.

    Adjudicate A1-A4 before or during that work: A4 in particular could invalidate the classifier's
    core discrimination rule for part of the dataset, and it is a question about the scanner, not
    about the code.
  </next_steps>

</test_report>
