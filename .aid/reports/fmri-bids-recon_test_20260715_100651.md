<test_report>
  <meta project="fmri-bids-recon" mode="test" timestamp="2026-07-15T10:06:51" input="fmri-bids-recon_implement_build_20260715_083741.md" sequence="run_suite -> design -> run_suite" />

  <!-- =============================================================== -->
  <!-- Stage 1: run_suite (pre-design baseline)                        -->
  <!-- =============================================================== -->
  <run_suite phase="pre-design">
    <summary>
      Baseline established before any design-phase edit. The suite was already
      green with tracked strict-xfails: the carried-forward defect ledger
      (render IntendedFor rendering, cross-session rename guard) was present from
      the prior test cycle. No unexpected failures or errors at baseline. The
      pre-design run confirmed the codebase-under-test was in the state described
      by the implement build report, with the known product defects captured as
      strict-xfails rather than red failures.
    </summary>
  </run_suite>

  <!-- =============================================================== -->
  <!-- Stage 2: design                                                 -->
  <!-- =============================================================== -->
  <design>
    <scope>
      Coverage was extended against the implement build report and against
      uncovered code paths surfaced while reading the engine. Design work in this
      cycle touched seven test files: test_cli_integration.py, test_physio.py,
      test_classify.py, test_sidecar.py, test_convert.py, test_manifest.py, and
      test_assemble.py. Two files (test_render.py, test_labels.py) carry defect
      xfails authored in a prior test cycle and were left unmodified; their
      defects remain routed to /implement below.
    </scope>

    <!-- Per-failure / per-gap disposition ledger -->
    <disposition_ledger>

      <!-- ===== Net-new positive coverage (disposition: aligned) ===== -->
      <entry id="D1" disposition="aligned" area="physio write guards">
        <intended_contract>write_physio must refuse a physio log whose channel
          sampling cannot be trusted: no channel reporting a positive SampleTime,
          disagreeing PULS/RESP sample times, or a recovered acquisition window
          that cannot be reconciled with n_volumes*TR. physio.py lines 588-627.</intended_contract>
        <current_test_claim>No coverage existed for the three write_physio guard
          branches.</current_test_claim>
        <evidence>physio.py raises PhysioParseError on each branch; no test
          exercised the raise paths.</evidence>
        <action>Authored three tests in test_physio.py asserting PhysioParseError
          on (a) no channel with positive SampleTime, (b) PULS/RESP SampleTime
          disagreement, (c) window vs n_volumes*TR mismatch beyond
          max(0.05*expected_s, TR). Positive coverage of implemented behavior;
          all three pass.</action>
      </entry>

      <entry id="D2" disposition="aligned" area="classifier: navigator fail-loud">
        <intended_contract>A multi-volume EPI series whose modality token is
          neither FMRI nor DIFFUSION must halt the session (NavigatorDropError)
          rather than be silently dropped as a navigator, because silently
          dropping a real multi-volume acquisition would leave an undetectable
          hole in the dataset. stage2_classify.py lines 138-146.</intended_contract>
        <current_test_claim>Only the silent-drop limb was covered
          (test_multivolume_series_outside_fmri_and_diffusion_is_a_navigator);
          the fail-loud EPI limb was uncovered.</current_test_claim>
        <evidence>Rule 3 raises NavigatorDropError with context
          {series_number, image_type, software_versions} when n_volumes > 1 and
          "EP" in scanning_sequence and the token is unrecognised.</evidence>
        <action>Authored a fail-loud test asserting NavigatorDropError and its
          context payload. An initial duplicate of the existing silent-drop test
          was self-caught and removed. Positive coverage; passes.</action>
      </entry>

      <entry id="D3" disposition="aligned" area="classifier: DWI single-band reference">
        <intended_contract>A single-volume magnitude EPI series immediately
          preceding a matching-stem diffusion run is a diffusion single-band
          reference (Role.DWI_SBREF); a lone such reference with no following DWI
          is unclassified. stage2_classify.py line 251.</intended_contract>
        <current_test_claim>No coverage for the DWI_SBREF classification rule.</current_test_claim>
        <evidence>Rule 9b keys on tok == "M", n_volumes == 1, "EP" in
          scanning_sequence, with a subsequent same-stem DIFFUSION+bval series.</evidence>
        <action>Authored two classification tests (matched pair -> DWI_SBREF+DWI;
          lone reference -> UNCLASSIFIED). Positive coverage; both pass.</action>
      </entry>

      <entry id="D4" disposition="aligned" area="sidecar: software_versions capture">
        <intended_contract>load_series must capture SoftwareVersions as a typed
          Series field (software_versions), and an absent key must read back as
          None, not empty string, so downstream 'is None' guards hold and the
          navigator fail-loud context can surface it. sidecar.py line 252.</intended_contract>
        <current_test_claim>No coverage for the software_versions field.</current_test_claim>
        <evidence>load_series sets software_versions=raw.get("SoftwareVersions").</evidence>
        <action>Authored two tests (present -> captured value; absent -> None).
          Positive coverage; both pass.</action>
      </entry>

      <entry id="D5" disposition="aligned" area="convert: stale staging cleanup">
        <intended_contract>A SLURM array re-uses one staging leaf per
          (subject, session); a partial prior run can leave NIfTIs and sidecars
          behind. convert_to_staging must empty the leaf before conversion, or a
          stale sidecar would be rglob'd and assembled as if it belonged to this
          conversion, silently mixing subjects. stage1_convert.py lines 80-89.</intended_contract>
        <current_test_claim>ConversionError-on-nonzero and stderr retention were
          covered; the clearing of stale contents was uncovered.</current_test_claim>
        <evidence>convert iterates children, rmtree on dirs / unlink on files,
          then mkdir.</evidence>
        <action>Authored a test seeding stale top-level files plus a nested stale
          subdirectory, asserting removal and that no "leftover" sidecar survives
          into result.sidecar_paths. Positive coverage; passes.</action>
      </entry>

      <entry id="D6" disposition="aligned" area="manifest: status vocabulary enforcement">
        <intended_contract>A status outside VALID_STATUSES must be refused at the
          write boundary (ValidationError) with no partial file write, so
          should_skip and downstream readers never branch on an unrecognised
          value.</intended_contract>
        <current_test_claim>Only the vocabulary constant was asserted; write-time
          enforcement was uncovered.</current_test_claim>
        <evidence>update_manifest validates status before writing.</evidence>
        <action>Authored a test asserting ValidationError with context["status"]
          and that the manifest file is not created. Positive coverage; passes.</action>
      </entry>

      <entry id="D7" disposition="aligned" area="assemble: DWI_SBREF placement">
        <intended_contract>A Role.DWI_SBREF series must land under dwi/ with the
          _sbref suffix and the correct dir- entity. stage4_assemble.py.</intended_contract>
        <current_test_claim>No coverage for DWI_SBREF assembly placement.</current_test_claim>
        <evidence>assemble routes DWI_SBREF to the dwi/ directory with sbref
          suffix and dir- label from PE_DIRECTION_TO_LABEL.</evidence>
        <action>Authored a test asserting the emitted .nii.gz and .json land at
          dwi/sub-001_ses-01_dir-AP_run-01_sbref.*. Positive coverage; passes.</action>
      </entry>

      <!-- ===== Obsolete-test re-expression (strengthened) ===== -->
      <entry id="D8" disposition="obsolete-test" area="integration: T1w run entity">
        <intended_contract>Per the locked decision to always emit the run- entity,
          the anat T1w output is sub-001_ses-01_run-01_T1w.nii.gz.</intended_contract>
        <current_test_claim>The integration assertion expected a T1w path without
          the run- entity.</current_test_claim>
        <evidence>Locked design decision "always emit run-".</evidence>
        <action>Re-expressed the integration assertion to require the run-01
          entity. This STRENGTHENS the postcondition (the assertion now requires a
          more specific path); it is not a weakening. The assertion lives inside
          the assemble integration test, which remains strict-xfail under the
          assemble command defect (D10) until /implement fixes the call sites.</action>
      </entry>

      <!-- ===== Product-bug dispositions (routed to /implement) ===== -->
      <entry id="D9" disposition="product-bug" area="cli: physio wiring" route="PB-09/PB-10">
        <intended_contract>A physio log present in the source directory must reach
          the intermediate: _cmd_convert must select Raw Data Storage records from
          staging.dicom_index, parse each file, and associate against BOLD survivors.</intended_contract>
        <current_test_claim>Strict-xfail test authored this cycle
          (test_a_physio_log_in_the_source_directory_reaches_the_intermediate,
          test_cli_integration.py) asserting physio_pairs is non-empty.</current_test_claim>
        <evidence>_cmd_convert calls parse_physio_dicom(staging.staging_dir)
          (__main__ line 143), but parse_physio_dicom takes a single DICOM FILE,
          raising IsADirectoryError swallowed by the physio except block; physio is
          silently never produced. Two latent defects behind it: associate_physio
          receives all series rather than BOLD survivors, and its dict return is
          iterated as pairs.</evidence>
        <action>NO assertion edit. Routed to /implement (see action_items).</action>
      </entry>

      <entry id="D10" disposition="product-bug" area="cli: assemble command call sites" route="PB-05/03/04/06/07/08">
        <intended_contract>A converted session must assemble into a BIDS tree:
          the assemble command's call sites must match the real stage signatures.</intended_contract>
        <current_test_claim>Strict-xfail integration test authored this cycle
          (test_a_converted_session_assembles_into_a_bids_tree,
          test_cli_integration.py) asserting the anat/func/fmap outputs exist.</current_test_claim>
        <evidence>_cmd_assemble dies at __main__ line 264
          merged_registry.update(registry_delta): registry_delta is the
          RegistryDelta dataclass, not a mapping. Five further defects sit on the
          same path (assemble/render signatures do not exist; write_conversion_report
          and generate_cubids_report called with wrong arity; save_registry handed a
          dict where a YAML path is expected). The pipeline has never produced a
          BIDS dataset.</evidence>
        <action>NO assertion edit. Routed to /implement as one change (rewrite the
          assemble command call sites against the real stage signatures).</action>
      </entry>

      <entry id="D11" disposition="product-bug" area="assemble: unresolvable DWI phase-encoding direction" route="PB-25">
        <intended_contract>A diffusion (DWI or DWI_SBREF) series whose
          phase-encoding direction cannot be resolved to a BIDS label must be
          refused with a blocking GuardError, not written as dir-UNK.</intended_contract>
        <current_test_claim>Strict-xfail test authored this cycle
          (test_assemble.py, PB-25) asserting refusal on an unresolvable PE
          direction. This is the locked "fail loud on unknown PE" decision.</current_test_claim>
        <evidence>assemble computes PE_DIRECTION_TO_LABEL.get(pe or '', 'UNK') for
          both Role.DWI and Role.DWI_SBREF (stage4_assemble.py lines 349, 371) and
          emits dir-UNK. dir-UNK silently disables the susceptibility distortion
          correction the dir- entity exists to specify and is indistinguishable
          from a correctly labelled acquisition; the dir_label_pe_agreement guard
          treats an unresolvable direction as a blocking condition.</evidence>
        <action>NO assertion edit. Routed to /implement (raise a blocking
          GuardError when a DWI/DWI_SBREF PE direction does not map to a known label).</action>
      </entry>

      <entry id="D12" disposition="product-bug" area="render: IntendedFor / B0Field rendering" route="PB-01/PB-02" provenance="carried-forward">
        <intended_contract>render() must write IntendedFor, B0FieldIdentifier, and
          B0FieldSource into the assembled BIDS sidecars for every session carrying
          a fieldmap pair, preserving the physics already in the sidecar and never
          reintroducing identifiers into the tree.</intended_contract>
        <current_test_claim>Four strict-xfail tests in test_render.py (prior cycle)
          asserting the IntendedFor targets, the dual-rendering agreement, physics
          preservation, and no-PHI-reintroduction.</current_test_claim>
        <evidence>render() reads target.nii_path / member.nii_path (stage5_render
          lines 146, 152, 162) but the sidecar.Series attribute is nifti_path, so
          every fieldmap session dies with AttributeError. Renaming is insufficient:
          nifti_path points into the STAGING tree, so _subject_relative_path's
          relative_to(bids_root/'sub-XXX') then raises ValueError, and the sidecars
          render would edit are staging sidecars, not assembled BIDS ones.
          AssemblyResult exposes no series_number -> BIDS path map. No dataset this
          pipeline produces carries IntendedFor/B0FieldIdentifier/B0FieldSource, so
          fMRIPrep runs with no susceptibility distortion correction.</evidence>
        <action>NO assertion edit. Routed to /implement (interface change: assemble
          must return the emitted BIDS path per series; render must consume it).</action>
      </entry>

      <entry id="D13" disposition="product-bug" area="labels: cross-session rename guard" route="PB-14" provenance="carried-forward">
        <intended_contract>The no_rename_collision guard must detect a genuine
          cross-session protocol rename (e.g. STUDY_faces_bold -> STUDY_emotion_bold
          with identical physics).</intended_contract>
        <current_test_claim>Strict-xfail test in test_labels.py (prior cycle)
          asserting a cross-session rename is detected.</current_test_claim>
        <evidence>resolve_labels builds all_sig_by_desc only from series present in
          the CURRENT session, then looks up the old registry description in that
          same map. In a genuine rename the old description is absent from the
          session, so old_sigs is always empty and the intersection can never fire.
          TaskRegistryEntry(label, expected_volumes, first_seen) carries no
          acquisition signature, so the registry cannot supply one either. The guard
          is structurally unfireable.</evidence>
        <action>NO assertion edit. Routed to /implement (persist the acquisition
          signature in TaskRegistryEntry at first registration; compare against the
          STORED signature).</action>
      </entry>

      <entry id="D14" disposition="product-bug" area="tsv: sessions lock persistence" route="TSV-lock">
        <intended_contract>The sessions.tsv write path must serialise concurrent
          upserts under a persistent advisory lock. The locked decision is to
          remove the lock-file unlink and persist the lock, so a concurrent writer
          cannot acquire a freshly-recreated lock and race the read-modify-write.</intended_contract>
        <current_test_claim>test_tsv.py covers the flock/atomic-write happy path
          (test_concurrent_upserts_do_not_lose_rows), which passes under the current
          code. The unlink/persist race is a robustness defect not deterministically
          triggered by the existing test.</current_test_claim>
        <evidence>Locked decision "remove unlink, persist lock", routed as a code
          change during design discussion.</evidence>
        <action>NO assertion edit. Routed to /implement as a code fix. Coverage
          note below (see open_items): this route currently has no dedicated
          regression test because a deterministic trigger for the unlink/persist
          race would be inherently flaky.</action>
      </entry>

    </disposition_ledger>

    <success_metrics>
      <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
      <assertions_note>No assertion was removed, weakened, replaced with a
        tautology, suppressed via try/except, or reduced in specificity. The single
        re-expressed assertion (D8, T1w run entity) was STRENGTHENED to require the
        run-01 entity. Every other design-phase edit added new assertions.</assertions_note>
      <bugs_routed_to_implement>6</bugs_routed_to_implement>
      <bugs_routed_note>Six product-defect clusters routed via action_items: four
        captured/decided this cycle (physio wiring PB-09/10, assemble command call
        sites PB-05/03/04/06/07/08, unresolvable DWI PE PB-25, sessions-lock
        persistence), and two carried forward from the prior cycle (render
        IntendedFor PB-01/02, cross-session rename PB-14). A non-zero count is a
        positive design outcome: correctly identified product defects, not test
        failures.</bugs_routed_note>
      <net_new_tests>11 positive-coverage tests authored across six files (D1-D7),
        all passing; plus the PB-25 strict-xfail and the D8 assertion strengthening.</net_new_tests>
    </success_metrics>
  </design>

  <!-- =============================================================== -->
  <!-- Stage 3: run_suite (post-design, delegated + receipt-verified)  -->
  <!-- =============================================================== -->
  <run_suite phase="post-design" dispatch="execution-agent-sonnet-medium" task_id="postdesign-suite-full">
    <results total="368" passed="358" skipped="2" xfailed="8" failed="0" errors="0" xpassed="0" duration_s="5.76" />
    <verification>
      <return_schema_revalidation dispatch_site="test:run_suite" ok="true" />
      <receipt_verifier ok="true">
        All eight anti-fabrication checks matched: nonce present, clock within
        [T0,T1], duration consistent, receipt summary matches returned counts,
        collect_total matches the independent --collect-only oracle (368), tee'd
        receipt-file mtime within [T0,T1], receipt-file nonce present, receipt-file
        summary line matches returned pass/fail counts.
      </receipt_verifier>
      <collect_only_oracle>368</collect_only_oracle>
    </verification>
    <interpretation>
      The suite is green with tracked strict-xfails. All 8 xfails are product
      defects with citable reasons recorded inline in the test files (D9-D13; D14
      is a code-route without an xfail). There are zero unexpected failures, zero
      errors, and zero XPASSes, so no captured defect has silently resolved and no
      new regression was introduced. The 2 skips are pre-existing conditional
      skips (a **kwargs-splat signature that cannot be introspected in
      test_cli_integration.py; the exact_volume_counts exclude-rather-than-raise
      behavior in test_guard_coverage.py), not design-phase additions.
    </interpretation>
  </run_suite>

  <!-- =============================================================== -->
  <!-- Action items: product defects routed to /implement              -->
  <!-- =============================================================== -->
  <action_items>
    <item priority="P0" target_mode="implement" ref="D10 / PB-05+03+04+06+07+08"
      description="Rewrite the assemble command (_cmd_assemble) call sites against the real stage signatures: merge registry_delta.new_entries (not the RegistryDelta dataclass), merge the pickled vol_updates, fix the assemble/render call signatures, pass write_conversion_report and generate_cubids_report their full argument lists, and hand save_registry a YAML path rather than a dict. This is the first fault on the pipeline's main path; the pipeline has never produced a BIDS dataset until it is fixed. Flips test_a_converted_session_assembles_into_a_bids_tree from xfail to pass." />
    <item priority="P0" target_mode="implement" ref="D9 / PB-09+PB-10"
      description="Wire physio: in _cmd_convert, select Raw Data Storage records from staging.dicom_index (not staging.staging_dir), parse each PMU file, and pass associate_physio the BOLD survivors rather than all series, consuming its dict[int, PhysioLog] return correctly. Flips test_a_physio_log_in_the_source_directory_reaches_the_intermediate from xfail to pass." />
    <item priority="P0" target_mode="implement" ref="D12 / PB-01+PB-02"
      description="Fix render() fieldmap association: assemble must return a series_number -> emitted BIDS path map (interface change on AssemblyResult), and render must consume that map instead of reading Series.nifti_path (which points into staging). Without this no dataset carries IntendedFor/B0FieldIdentifier/B0FieldSource and fMRIPrep runs with no susceptibility distortion correction. Flips the four test_render.py xfails to pass." />
    <item priority="P1" target_mode="implement" ref="D11 / PB-25"
      description="Raise a blocking GuardError when a Role.DWI or Role.DWI_SBREF phase-encoding direction does not map to a known BIDS label (stage4_assemble.py lines 349, 371), rather than emitting dir-UNK. Flips the PB-25 strict-xfail in test_assemble.py to pass." />
    <item priority="P1" target_mode="implement" ref="D13 / PB-14"
      description="Make the cross-session rename guard fireable: persist the acquisition signature in TaskRegistryEntry at first registration and compare a session's series against the STORED signature (not against signatures rebuilt only from the current session). Flips the cross-session rename xfail in test_labels.py to pass." />
    <item priority="P1" target_mode="implement" ref="D14 / TSV-lock"
      description="In the sessions.tsv write path, remove the lock-file unlink and persist the advisory lock so a concurrent writer cannot acquire a freshly-recreated lock and race the read-modify-write." />
    <item priority="P2" target_mode="test" ref="D14 coverage gap"
      description="After /implement applies the sessions-lock persistence fix, add a targeted regression test IF a deterministic (non-flaky) trigger for the unlink/persist race can be constructed; otherwise document why the flock happy-path test is the strongest defensible guard." />
  </action_items>

  <open_items>
    <item>The sessions-lock persistence route (D14) is the only product defect
      routed without a strict-xfail guard, because a deterministic regression test
      for the unlink/persist race would be inherently flaky. Surfaced here rather
      than silently omitted; the P2 test action item above records the follow-up.</item>
  </open_items>

  <next_steps>
    Recommended: run /implement on this report to fix the six routed product
    defects (three P0 on the pipeline's main path: assemble command call sites,
    physio wiring, render fieldmap association; then the P1 items). After the fix,
    re-run /test: the completion criterion for this effort is a green suite with
    zero xfails and zero xpasses, which is reachable only once /implement flips the
    eight tracked strict-xfails to true passes. This /test cycle's post-design
    suite is green-with-tracked-xfails and receipt-verified; it is a correct
    intermediate state, not the terminal one.
  </next_steps>
</test_report>
