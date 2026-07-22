<test_report>
  <meta project="fmri-bids-recon" mode="test" sequence="run_suite -> design -> run_suite" timestamp="2026-07-15T17:14:10Z" />
  <spec_ref>fmri-bids-recon_implement_build_20260715_123948.md</spec_ref>

  <objective>
    Reconcile the failing test suite to the code state produced by the prior
    implement build, reaching a green suite with zero xfail and zero xpass, without
    weakening any assertion. Test-file edits only; product defects (if any new ones
    were found) route to /implement; ambiguous or environment-blocked cases are
    surfaced for adjudication rather than resolved unilaterally.
  </objective>

  <run_suite phase="pre_design">
    <collected>368</collected>
    <derivation>
      The baseline suite carried eight marker-guarded anomalies. Five strict-xfail
      tests had begun passing after the prior implement build, so pytest reported
      them as failures under XPASS(strict); three xfail tests were still failing as
      expected and were reported as xfailed. Two tests were skipped (see skipped
      section). The residual clean-passing count was therefore 358.
    </derivation>
    <summary>358 passed, 5 failed (XPASS strict), 3 xfailed, 2 skipped</summary>
    <interpretation>
      None of the five "failures" were genuine assertion failures: each was a
      strict-xfail tripwire firing because the product defect its marker documented
      had already been fixed. The three xfailed tests were the deferred-fix cases
      whose residual cause had to be diagnosed before the marker could be removed.
    </interpretation>
  </run_suite>

  <design phase="design">
    <discipline>
      Per-failure disposition ledger recorded before any edit. Write scope was
      restricted to tests/. No assertion was removed, replaced with a tautology,
      wrapped in failure-suppressing try/except, or reduced in specificity. Every
      disposition below is supported by product-code or prior-build evidence, and
      the one case whose resolution required a design decision (the external BIDS
      validator boundary) was surfaced and adjudicated by the user before editing.
    </discipline>

    <ledger>
      <entry id="L1-L4" tests="test_render.py::test_each_fieldmap_member_declares_the_runs_it_is_intended_for, test_the_two_renderings_of_the_same_association_agree, test_rendering_preserves_the_physics_already_in_the_sidecar, test_rendering_does_not_reintroduce_identifiers_into_the_tree">
        <intended_contract>render() writes IntendedFor and the B0FieldIdentifier/B0FieldSource pair to each resolved fieldmap-member sidecar in the assembled BIDS tree, preserves physics keys already present (RepetitionTime, EffectiveEchoSpacing, PhaseEncodingDirection), and does not reintroduce identifiers into the shareable tree.</intended_contract>
        <current_test_claim>Exact IntendedFor arrays; B0FieldIdentifier == B0FieldSource and both name the pair; RepetitionTime == 0.8, EffectiveEchoSpacing == 0.00051, PhaseEncodingDirection == "j-"; PatientID and PatientName absent.</current_test_claim>
        <disposition>obsolete-marker</disposition>
        <evidence>The prior implement build rewrote the fieldmap-member loop in stage5_render.py to resolve each member's BIDS sidecar via mapping.bids_relative_paths, eliminating the staging-tree attribute error the RENDER_DEFECT marker documented. With the defect fixed, all four tests pass, so the strict markers reported XPASS(strict).</evidence>
        <action>Removed the four strict-xfail markers and the now-orphaned RENDER_DEFECT constant. Assertions unchanged.</action>
        <assertion_change>preserved</assertion_change>
      </entry>

      <entry id="L5" tests="test_assemble.py::test_a_diffusion_series_with_an_unresolvable_pe_direction_is_refused">
        <intended_contract>A diffusion (DWI or DWI single-band-reference) series whose phase-encoding direction does not map to a BIDS dir- label must be refused with a blocking GuardError, not emitted as dir-UNK.</intended_contract>
        <current_test_claim>pytest.raises(GuardError) when assembling a DWI with phase_encoding_direction=None.</current_test_claim>
        <disposition>obsolete-marker</disposition>
        <evidence>The prior implement build added PhaseEncodingError (a GuardError subclass) to both diffusion branches of stage4_assemble.py, replacing the dir-UNK fallback. The test now raises as specified, so the strict marker reported XPASS(strict).</evidence>
        <action>Removed the strict-xfail marker and its inline reason. Assertion unchanged.</action>
        <assertion_change>preserved</assertion_change>
      </entry>

      <entry id="L6" tests="test_cli_integration.py::test_a_physio_log_in_the_source_directory_reaches_the_intermediate">
        <intended_contract>A PhysioLog (Raw Data Storage object) present in the source directory is indexed, parsed, associated with a BOLD run, and surfaces as a non-empty physio_pairs in the pickled intermediate.</intended_contract>
        <current_test_claim>assert _intermediate(session)["physio_pairs"] (truthy).</current_test_claim>
        <disposition>obsolete-marker plus fixture defect</disposition>
        <evidence>The marker's wiring-defect narrative was already remediated by the prior build. The residual failure was isolated to the test fixture: _write_pmu_dicom set only the file-meta MediaStorageSOPClassUID (0002,0002) and never the dataset-level SOPClassUID (0008,0016), which is the tag index_source_dicoms reads to select Raw Data Storage series. The end-to-end product path was traced: index_source_dicoms records the SOP class, the CLI physio loop filters on it, parse_physio_dicom performs a full read of the private acquisition-info element, and associate_physio matches the log to a BOLD by geometry (num_volumes 200, num_slices 20), both matching the default bold() fixture. The correct fixture pattern is corroborated by test_convert.py, whose DICOM writer sets ds.SOPClassUID and whose index assertion passes.</evidence>
        <action>Removed the xfail marker and the orphaned PHYSIO_WIRING_DEFECT constant; added ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.66" to _write_pmu_dicom with a comment recording the (0008,0016) vs (0002,0002) distinction. Assertion preserved.</action>
        <assertion_change>preserved</assertion_change>
      </entry>

      <entry id="L7" tests="test_labels.py::test_a_cross_session_rename_is_detected">
        <intended_contract>A cross-session task rename, where the old description is absent from the current session, is detected via the acquisition signature persisted in the registry at first registration.</intended_contract>
        <current_test_claim>pytest.raises(TaskRenameError).</current_test_claim>
        <disposition>obsolete-marker plus fixture enrichment</disposition>
        <evidence>The prior build added a persisted signature field to TaskRegistryEntry and made the rename guard augment the old-description signature set with the stored registry signature, matching by signature intersection across the new-by-old description cross-product (labels.py:342-350). The residual failure was that the registry_entry fixture supplied no signature, so the guard's old_sigs stayed empty and the intersection could never be non-empty. The signature the fixture must supply is constructed exactly as the product constructs it, so the tuple comparison holds.</evidence>
        <action>Added an optional signature parameter to the registry_entry fixture (default None, backward-compatible with the existing in-session collision test); passed acquisition_signature(bold(11, "STUDY_faces_bold")) in the rename test; removed the xfail marker. Assertion preserved.</action>
        <assertion_change>preserved</assertion_change>
      </entry>

      <entry id="L8" tests="test_cli_integration.py::test_a_converted_session_assembles_into_a_bids_tree">
        <intended_contract>A converted session assembles into a valid BIDS tree (T1w, two BOLD runs, a PA fieldmap), and the produced tree is submitted to the BIDS validator before the run is declared clean.</intended_contract>
        <current_test_claim>_convert == 0; _assemble == 0; four file-existence assertions over the emitted tree.</current_test_claim>
        <disposition>obsolete-marker plus test-environment issue (user-adjudicated)</disposition>
        <evidence>The marker's assemble-call-site narrative was remediated by the prior build. A faithful reproduction drove the real _cmd_convert and _cmd_assemble to a well-formed tree; the only residual failure was the blocking run_bids_validator guard, which shells to bids-validator v1.5.3. That binary crashes on load under Node v25.7.0 (dumps its esm shim, empty stdout, exit 1) regardless of input, confirmed by an identical crash on a known-valid minimal BIDS dataset. The failure is therefore a broken external tool in the local environment, not a malformed tree.</evidence>
        <decision surfaced="true" resolved_by="user">
          Stubbing a blocking scientific-integrity guard has defensibility implications, so the resolution was surfaced with three options (stub the validator boundary in the test; fix the local environment; leave one xfail). The user selected stubbing the boundary, conditioned on the real validator still running on the deployment server. That condition is satisfied by construction: the stub lives only in the test, and the product's run_bids_validator continues to shell out to the real binary unchanged.
        </decision>
        <action>Removed the xfail marker and the orphaned ASSEMBLE_DEFECT constant; stubbed the external bids-validator boundary in the test via monkeypatch (record-and-noop, mirroring the existing dcm2niix stub) and strengthened the test by asserting run_bids_validator is invoked exactly once with the configured bids_root. Product code untouched.</action>
        <assertion_change>strengthened</assertion_change>
      </entry>
    </ledger>

    <files_edited scope="tests/">
      <file path="tests/conftest.py" change="registry_entry fixture gained an optional, backward-compatible signature parameter" />
      <file path="tests/test_physio.py" change="_write_pmu_dicom now sets the dataset-level SOPClassUID (0008,0016)" />
      <file path="tests/test_render.py" change="removed four strict-xfail markers and the RENDER_DEFECT constant" />
      <file path="tests/test_assemble.py" change="removed the diffusion PE-direction strict-xfail marker" />
      <file path="tests/test_labels.py" change="removed the rename xfail marker; passed the persisted signature in the rename test" />
      <file path="tests/test_cli_integration.py" change="removed the physio and assemble xfail markers and their constants; stubbed the bids-validator boundary and added a validator-wiring assertion in the assemble test" />
    </files_edited>
  </design>

  <run_suite phase="post_design" verified="true">
    <collected>368</collected>
    <summary>366 passed, 0 failed, 0 errors, 2 skipped, 0 xfailed, 0 xpassed</summary>
    <verification>
      Dispatched to execution-agent-sonnet-medium under the nonce plus tee'd-receipt
      protocol. All eight receipt checks matched (nonce, wall clock, duration,
      summary counts, independent collect-only oracle of 368, receipt-file mtime,
      receipt-file nonce, receipt-file summary). The override-schema return validated
      ok. The run is confirmed genuine.
    </verification>
  </run_suite>

  <skipped count="2">
    <note>
      Both skips are in test_guard_coverage.py and are principled, pre-existing
      conditional skips documenting that the exact_volume_counts guard excludes a
      series rather than raising, with an explicit cross-reference to the test that
      covers that behavior (test_the_volume_count_guard_is_the_only_one_that_excludes).
      They are neither xfail nor suppressed failures and are outside the scope of the
      zero-xfail/zero-xpass objective. No action taken.
    </note>
  </skipped>

  <success_metrics>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>0</bugs_routed_to_implement>
    <bugs_routed_note>
      No new product defects were found. Every failing test resolved to an obsolete
      strict-xfail tripwire (the product fix having already been applied by the prior
      implement build), a test-fixture defect, or one broken external tool. The
      product changes that these tests now confirm were made in the prior build, not
      in this cycle.
    </bugs_routed_note>
    <objective_met>true</objective_met>
  </success_metrics>

  <deployment_dependency>
    The assemble integration test stubs the external bids-validator boundary; the
    product's run_bids_validator is unchanged and still invokes the real binary via
    subprocess. Consequently, BIDS-compliance verification of the pipeline's output
    is exercised only on the deployment server, and only if a working bids-validator
    is present on PATH there. The local environment's validator (v1.5.3) is
    incompatible with the installed Node runtime (v25.7.0) and cannot serve as that
    check. Recommended before production use: install a compatible validator on the
    server (a current Deno-based validator, or a Node version compatible with the
    installed validator) and confirm the pipeline's tree passes against the intended
    BIDS version.
  </deployment_dependency>

  <next_steps>
    The suite is green with zero xfail and zero xpass. Two follow-ups remain
    recommendations rather than blockers, for the user to schedule: (1) a concurrency
    regression test for the upsert_tsv lockfile-persistence change made in the prior
    build, which currently has no guarding test; (2) provisioning and validating a
    working bids-validator on the deployment server per the deployment dependency
    above. Neither is required to close this /test cycle.
  </next_steps>
</test_report>
