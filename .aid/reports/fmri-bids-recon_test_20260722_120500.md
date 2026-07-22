<test_report>
  <meta project="fmri-bids-recon" mode="test" timestamp="2026-07-22T12:05:00Z" />

  <pre_design_run>
    <note>
      The first dispatch of this run used the default pytest invocation and
      was blocked entirely: a collection error in test_assemble.py (an import
      of the removed SIDECAR_DENY_LIST/scrub symbols) interrupted the whole
      pytest session before any of the other ~358 tests could execute. This
      is pytest's default behavior on a collection error and is not specific
      to this codebase. The run was re-dispatched with
      --continue-on-collection-errors so the rest of the suite could report
      its true state; the counts below are from that corrected dispatch.
    </note>
    <total>359</total>
    <passed>350</passed>
    <failed>7</failed>
    <errors>1</errors>
    <coverage_pct />
    <failures>
      <failure test="test_rendering_does_not_reintroduce_identifiers_into_the_tree" file="tests/test_render.py" line="163">
        <error_type>AssertionError</error_type>
        <message>assert 'PatientID' not in fmap</message>
        <traceback>Asserted a removed identifier is absent from a fieldmap sidecar; identifiers are now intentionally present.</traceback>
      </failure>
      <failure test="test_every_section_of_the_report_is_present" file="tests/test_report.py" line="103">
        <error_type>AssertionError</error_type>
        <message>assert '## 8. SIDECAR SCRUB AUDIT' in report text</message>
        <traceback>Report is now seven sections, not eight; Section 8 was removed with the scrub audit.</traceback>
      </failure>
      <failure test="test_a_clean_tree_passes_the_scrub_audit" file="tests/test_report.py" line="158">
        <error_type>AssertionError</error_type>
        <message>assert 'All sidecars clean' in report text</message>
        <traceback>No audit exists to report a clean verdict from.</traceback>
      </failure>
      <failure test="test_a_surviving_identifier_in_a_bids_sidecar_stops_the_pipeline" file="tests/test_report.py" line="168">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE GuardError</message>
        <traceback>report.py no longer imports GuardError or performs the audit that raised it.</traceback>
      </failure>
      <failure test="test_the_audit_names_the_surviving_key_but_never_its_value" file="tests/test_report.py" line="182">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE GuardError</message>
        <traceback>Same removed audit mechanism.</traceback>
      </failure>
      <failure test="test_the_failing_report_is_on_disk_before_the_guard_raises" file="tests/test_report.py" line="198">
        <error_type>Failed</error_type>
        <message>DID NOT RAISE GuardError</message>
        <traceback>Same removed audit mechanism.</traceback>
      </failure>
      <failure test="test_the_unscrubbed_provenance_copies_do_not_trip_the_audit" file="tests/test_report.py" line="212">
        <error_type>AssertionError</error_type>
        <message>assert 'All sidecars clean' in report text</message>
        <traceback>Same removed audit mechanism.</traceback>
      </failure>
      <failure test="tests/test_assemble.py (collection)" file="tests/test_assemble.py" line="22">
        <error_type>ImportError</error_type>
        <message>cannot import name 'SIDECAR_DENY_LIST' from 'fmri_bids_recon.stage4_assemble'</message>
        <traceback>Blocked collection of the entire file (32 test functions), not just the scrub-specific ones.</traceback>
      </failure>
    </failures>
  </pre_design_run>

  <failing_test_dispositions>
    <disposition test="test_scrub_removes_every_deny_listed_key, test_scrub_is_a_deny_list_not_an_allow_list, test_scrub_does_not_mutate_its_input, test_the_deny_list_covers_the_direct_identifiers" file="tests/test_assemble.py" classification="obsolete-test">
      <intended_contract>Verify the scrub() function and its SIDECAR_DENY_LIST deny-list behave correctly.</intended_contract>
      <current_test_claim>scrub() strips deny-listed keys, preserves unknown keys, does not mutate its input, and the deny-list covers direct identifiers.</current_test_claim>
      <evidence>fmri_bids_recon/stage4_assemble.py no longer defines SIDECAR_DENY_LIST or scrub(); removed per the implement build (change C1) on explicit user direction that the pipeline is a faithful reconstruction tool with no information filtering.</evidence>
      <action>remove — the function under test no longer exists; there is no contract left to re-express against</action>
    </disposition>

    <disposition test="test_sidecars_written_into_the_bids_tree_are_scrubbed" file="tests/test_assemble.py" classification="obsolete-test">
      <intended_contract>No deny-listed key survives into a sidecar written to the BIDS tree.</intended_contract>
      <current_test_claim>SIDECAR_DENY_LIST &amp; set(data) is empty for every sidecar under sub-001/ses-01.</current_test_claim>
      <evidence>The corrected contract is the inverse: faithful reconstruction requires these fields to survive. Independently confirmed: all patient-level fields are now present in every sidecar, cross-modality consistent.</evidence>
      <action>remove — assertion is now false by design, not by regression</action>
    </disposition>

    <disposition test="test_every_section_of_the_report_is_present" file="tests/test_report.py" classification="obsolete-test">
      <intended_contract>Every section the conversion report is supposed to emit is present in its output.</intended_contract>
      <current_test_claim>Eight named headings, including "## 8. SIDECAR SCRUB AUDIT", are all present.</current_test_claim>
      <evidence>fmri_bids_recon/report.py's Section 8 was removed (implement build change C2); the module docstring now says "seven sections ending at the PatientID cross-check".</evidence>
      <action>re-express — drop the removed heading from the expected tuple, keep the other seven; strengthens nothing but preserves the contract's intent (every actual section is checked)</action>
    </disposition>

    <disposition test="test_a_clean_tree_passes_the_scrub_audit, test_a_surviving_identifier_in_a_bids_sidecar_stops_the_pipeline, test_the_audit_names_the_surviving_key_but_never_its_value, test_the_failing_report_is_on_disk_before_the_guard_raises, test_the_unscrubbed_provenance_copies_do_not_trip_the_audit" file="tests/test_report.py" classification="obsolete-test">
      <intended_contract>The Section 8 scrub audit fires correctly: passes clean sidecars, raises GuardError on a surviving identifier, names the leaked key without its value, writes the report before raising, and does not sweep the intentionally-retained provenance copies.</intended_contract>
      <current_test_claim>Various assertions on report text and pytest.raises(GuardError) around calls that no longer raise.</current_test_claim>
      <evidence>report.py no longer imports GuardError or performs any audit (implement build change C2, confirmed by grep: zero remaining references).</evidence>
      <action>remove — the audited feature no longer exists</action>
    </disposition>

    <disposition test="test_rendering_does_not_reintroduce_identifiers_into_the_tree" file="tests/test_render.py" classification="obsolete-test">
      <intended_contract>render() must not corrupt or reintroduce data it does not itself understand into a sidecar.</intended_contract>
      <current_test_claim>PatientID and PatientName are absent from the rendered fmap sidecar.</current_test_claim>
      <evidence>render() (stage5) is untouched by the build; its own module docstring already states "anything stage 4 put there ... must come back out unchanged" (sibling test test_rendering_preserves_the_physics_already_in_the_sidecar). The rendered fixture stages fields via PHI_RAW, so a faithful round-trip now correctly carries PatientID/PatientName through.</evidence>
      <action>re-express — invert the assertion to check preservation rather than absence, which exercises the real, still-load-bearing contract (render() does not drop fields) under the corrected data model; renamed to test_rendering_preserves_patient_level_fields_already_in_the_sidecar</action>
    </disposition>

    <disposition test="test_sessions_tsv_records_the_wave_and_a_decimal_age, test_the_demographics_summary_carries_no_direct_identifier" file="tests/test_assemble.py" classification="obsolete-test">
      <intended_contract>Age is computed as an exact decimal value from PatientBirthDate against the study datetime.</intended_contract>
      <current_test_claim>float(row["age"]) == 20.0, and demographics["age"] == "20.0".</current_test_claim>
      <evidence>Discovered mid-design, not in the original pre-design failure list: test_assemble.py's collection error had masked these two failures along with the rest of the file. Once the import was fixed, running the file directly showed both failing. The fixture's 7305-day span (2006-01-15 to 2026-01-15, 5 leap days) is exactly 20.0 years under the Julian approximation (365.25, 7305/365.25 = 20.0 exactly) but not under the Gregorian mean year (365.2425) the corrected _decimal_age divides by (7305/365.2425 = 20.0004). Verified numerically: conda run -n fmri-bids-recon python confirms _decimal_age("20060115", 2026-01-15T09:02:00) == 20.0004. The fixture's apparent "pass" before this build was a coincidence of the old, less accurate constant, not evidence the test was discriminating correctly.</evidence>
      <action>re-express — pin the exact Gregorian-correct value (round(7305/365.2425, 4)) rather than the coincidentally round one; this strengthens the test since it now would fail if the constant regressed to 365.25</action>
    </disposition>

    <disposition test="(orchestrator self-correction, not a disposition) import of GuardError in tests/test_assemble.py" file="tests/test_assemble.py" classification="n/a">
      <intended_contract>n/a</intended_contract>
      <current_test_claim>n/a</current_test_claim>
      <evidence>While removing the scrub import, GuardError was dropped from the same import line along with SIDECAR_DENY_LIST/scrub, but GuardError is independently used by test_a_diffusion_series_with_an_unresolvable_pe_direction_is_refused (an unrelated PE-direction-refusal test, section "Product defects routed to /implement"). Caught by running the file directly; corrected before the design phase concluded.</evidence>
      <action>self-corrected within the design phase; noted here for traceability, not counted as a disposition</action>
    </disposition>
  </failing_test_dispositions>

  <design_phase>
    <tests_created>29</tests_created>
    <tests_modified>4</tests_modified>
    <files_created>
      <file path="tests/test_json_intermediate.py" test_count="27" coverage_target="Round-trip encode/decode of the JSON intermediate serialization that replaced pickle: all 9 dataclasses carried in the intermediate dict (Series, FieldmapPair, Mapping, Excluded, RegistryDelta, TaskRegistryEntry, PhysioLog, PhysioChannel, AcquisitionInfo), the ReviewFlag exception subclass, Path, datetime, tuple (including nested tuple-of-tuples via Series.affine and TaskRegistryEntry.signature), frozenset, the Role StrEnum, integer-keyed dicts, unknown-tag forward-compatibility passthrough, and a full dump_intermediate/load_intermediate file round-trip." />
    </files_created>
    <files_modified>
      <file path="tests/test_assemble.py" description="Removed the scrub import and 5 obsolete scrub/deny-list tests plus their section header; fixed a self-introduced GuardError import regression; re-expressed the two age-precision assertions to the Gregorian-correct value; added 2 new tests closing coverage gaps for the age-constant and acq_time-normalization fixes (_decimal_age, _normalize_acq_time), neither of which had any prior direct coverage." />
      <file path="tests/test_report.py" description="Removed the GuardError import and 5 obsolete scrub-audit tests plus their section header and the now-unused _sidecar helper and json import; re-expressed the section-count test to 7 headings; updated the module docstring to drop the PHI-scrub-audit framing while preserving the still-valid PatientID cross-check contract." />
      <file path="tests/test_render.py" description="Re-expressed the identifier test to assert preservation instead of absence, renamed to reflect the new contract; added the PHI_RAW import needed by the re-expressed assertion." />
    </files_modified>
    <design_rationale>
      Every change traces to a specific implement-build change (C1 scrub removal, C2 audit removal, C3 acq_time normalization, C4 Gregorian year length, C5 pickle-to-JSON) or to a coverage gap those changes left behind. No test was weakened: removals target tests whose subject no longer exists, re-expressions pin the new correct value at the same precision as before, and the two new test_assemble.py tests plus the full test_json_intermediate.py file close gaps that had zero prior coverage (sessions.tsv acq_time had no dedicated assertion at all; the JSON intermediate serialization was entirely new code from this build with no tests).
    </design_rationale>
  </design_phase>

  <post_design_run>
    <total>409</total>
    <passed>407</passed>
    <failed>0</failed>
    <errors>0</errors>
    <coverage_pct />
    <failures />
  </post_design_run>

  <summary>
    <assertions_preserved_or_strengthened>true</assertions_preserved_or_strengthened>
    <bugs_routed_to_implement>0</bugs_routed_to_implement>
    <recommendation>proceed_to_document</recommendation>
  </summary>

  <action_items>
    <item priority="P2" target_mode="implement" description="fmri_bids_recon/stage4_assemble.py: the assemble() function's own docstring (around line 140) still reads 'writes scrubbed JSON sidecars'. The module-level docstring at the top of the file was correctly updated to 'writes JSON sidecars' during the implement build, but this function-level docstring was missed. Outside /test's write scope (tests/ only)." />
  </action_items>
</test_report>
