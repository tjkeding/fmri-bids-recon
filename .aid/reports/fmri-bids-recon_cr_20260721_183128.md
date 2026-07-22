<cr_report>
  <meta project="fmri-bids-recon" mode="cr" timestamp="2026-07-21T18:31:28Z" />
  <scope>
    Full independent critical review of the fmri-bids-recon DICOM-to-BIDS reconstruction pipeline
    in preparation for documentation and publication. Reviewed all 18 core modules
    (config.py, errors.py, sidecar.py, stage1_convert.py, stage2_classify.py, labels.py,
    runs.py, stage3_map.py, physio.py, stage4_assemble.py, stage5_render.py, stage6_validate.py,
    deface.py, report.py, tsv.py, versions.py, manifest.py, __main__.py), the test suite
    (conftest.py plus 12 test modules), environment.yml, config/study.example.yaml, and
    RUNBOOK.md. Grep scans performed for PHI values, local paths, project-specific markers,
    credentials, security-sensitive patterns (pickle, subprocess, fcntl), and TODO/FIXME markers.

    Review dimensions: validity (DICOM PS3.15 compliance, BIDS v1.9.0 format compliance),
    robustness (edge cases, error handling, format variations), reproducibility (determinism,
    serialization, environment pinning), scientific rigor (privacy protection, standard compliance),
    and publication readiness (PHI, local paths, project markers).
  </scope>

  <research_conducted>
    Three research topics were dispatched to independent research agents:

    R1 (DICOM PS3.15 Annex E Basic Profile completeness): Confirmed that Table E.1-1 enumerates
    several hundred attributes with action codes. Of the 12 candidate attributes queried, 11 are
    explicitly listed for removal (X, X/Z/D, or Z/D action codes): InstitutionName, InstitutionAddress,
    DeviceSerialNumber, InstitutionalDepartmentName, OperatorsName, PerformingPhysicianName,
    PhysiciansOfRecord, RequestingPhysician, ContentCreatorName, IssuerOfPatientID, OtherPatientIDs.
    StationName (0008,1010) is NOT in Table E.1-1 (only PerformedStationName (0040,0242) appears).
    Source: NEMA PS3.15, Table E.1-1 (https://dicom.nema.org/medical/dicom/current/output/chtml/part15/chapter_e.html).

    R2 (BIDS v1.9.0/1.11.x acq_time requirements): Confirmed that acq_time is OPTIONAL in both
    sessions.tsv and scans.tsv, but when present, BIDS requires identical ISO8601 format
    (YYYY-MM-DDThh:mm:ss[.000000][Z|+hh:mm|-hh:mm]) in both files, referenced via the
    common-principles Units section. BIDS RECOMMENDS random per-subject day-shifting with
    shifted dates flagged via a pre-1925 year.
    Source: BIDS Specification, Common Principles, Units
    (https://bids-specification.readthedocs.io/en/stable/common-principles.html).

    R3 (Re-identification risk from age + timestamp): Confirmed that HIPAA Safe Harbor
    (45 CFR 164.514(b)(2)(i)(C)) requires all ages over 89 aggregated to "90 or older,"
    and that BIDS enforces CheckAge89 (max(age) < 89). Peer-reviewed metadata-privacy analysis
    (arXiv:2509.15278, Imaging Neuroscience 2025) identifies age as a principal quasi-identifier
    for neuroimaging data. HHS guidance notes that residual combinations of quasi-identifying
    fields can reconstruct suppressed identifiers. Specifically: 4-decimal-place age
    (resolution ~53 minutes) combined with exact AcquisitionDateTime enables day-level
    reconstruction of the deny-listed PatientBirthDate.
  </research_conducted>

  <findings>

    <!-- ================================================================== -->
    <!-- CRITICAL                                                           -->
    <!-- ================================================================== -->

    <finding id="F1" severity="critical" category="validity">
      <location file="fmri_bids_recon/stage4_assemble.py" lines="30-45" />
      <description>
        The SIDECAR_DENY_LIST contains 14 fields but is substantially incomplete relative to
        DICOM PS3.15 Annex E Basic Application Level Confidentiality Profile (Table E.1-1).
        At least 11 additional attributes that PS3.15 marks for removal (action codes X, X/Z/D,
        or Z/D) are absent from the deny-list:

        - InstitutionName (0008,0080), action X/Z/D
        - InstitutionAddress (0008,0081), action X
        - DeviceSerialNumber (0018,1000), action X/Z/D
        - InstitutionalDepartmentName (0008,1040), action X
        - OperatorsName (0008,1070), action X/Z/D
        - PerformingPhysicianName (0008,1050), action X
        - PhysiciansOfRecord (0008,1048), action X
        - RequestingPhysician (0032,1032), action X
        - ContentCreatorName (0070,0084), action Z/D
        - IssuerOfPatientID (0010,0021), action X
        - OtherPatientIDs (0010,1000), action X

        A test comment at tests/test_assemble.py:71-73 documents this as a deliberate design
        decision: "Institutional identifiers (InstitutionName, DeviceSerialNumber, etc.) are
        deliberately retained: they are site-level metadata needed by downstream tools, not
        patient-level PHI." However, this reasoning does not align with PS3.15's classification
        of these attributes as requiring removal for de-identification, and the test fixture
        PHI_RAW (tests/conftest.py:469-470) proves that InstitutionName and DeviceSerialNumber
        flow through the sidecar path and survive scrubbing.

        Additionally, StationName (0008,1010) is NOT enumerated in PS3.15 Table E.1-1 itself
        (only PerformedStationName (0040,0242) appears), so including it would be a conservative
        extension beyond the standard. However, dcm2niix does emit StationName in JSON sidecars,
        and it can identify the specific scanner where data were acquired.

        The post-hoc scrub audit in report.py (lines 225-259) only checks against the same
        incomplete SIDECAR_DENY_LIST, meaning both the scrub and its verification share the
        same coverage gap.
      </description>
      <evidence>
        Current deny-list (14 items): AcquisitionDateTime, PatientAge, PatientBirthDate,
        PatientID, PatientName, PatientSex, PatientSize, PatientWeight, SeriesInstanceUID,
        StudyID, StudyInstanceUID, AccessionNumber, ReferringPhysicianName,
        PerformedProcedureStepDescription.

        Test fixture proves flow-through: conftest.py:469 InstitutionName="Somewhere Imaging
        Centre", conftest.py:470 DeviceSerialNumber="12345".

        Design intent documented: test_assemble.py:71-73.
      </evidence>
      <literature>
        NEMA PS3.15, Annex E, Table E.1-1 (Basic Application Level Confidentiality Profile).
        R1 research agent confirmed all 11 attributes carry X, X/Z/D, or Z/D action codes.
      </literature>
      <impact>
        For any dataset processed by this pipeline and subsequently shared (e.g., deposited to
        OpenNeuro), institutional identifiers surviving in BIDS JSON sidecars would constitute
        incomplete de-identification per DICOM PS3.15. Even for internally-retained datasets,
        the deviation from the standard should be explicitly documented and justified in the
        pipeline's data management plan. The compound vulnerability (deny-list + audit both
        incomplete) means no pipeline-internal mechanism will flag the retained fields.
      </impact>
      <recommendation>
        Two options, depending on the pipeline's data-sharing context:

        (A) If pipeline outputs will be shared externally: expand SIDECAR_DENY_LIST to include
        all 11 missing PS3.15 attributes plus StationName as a conservative extension. Update
        the scrub audit to verify against the expanded list. Update the test at
        test_assemble.py:69-76 to assert coverage of the expanded set.

        (B) If pipeline outputs are strictly internal and downstream tools require these fields:
        document the PS3.15 deviation explicitly in the pipeline's README and conversion report,
        with a rationale statement. Add a configurable de-identification profile level
        (e.g., "basic" vs. "full-ps315") so the user can select the appropriate level for their
        data-sharing context.

        In either case, the test comment at test_assemble.py:71-73 should be expanded to
        reference PS3.15 and state the specific justification for deviation.
      </recommendation>
    </finding>

    <!-- ================================================================== -->
    <!-- MAJOR                                                              -->
    <!-- ================================================================== -->

    <finding id="F2" severity="major" category="validity">
      <location file="fmri_bids_recon/stage4_assemble.py" lines="137-159, 513-516, 541" />
      <description>
        The _decimal_age function computes exact age to 4 decimal places from PatientBirthDate
        and AcquisitionDateTime (line 156: round(delta.days / 365.25, 4)). This value is written
        to sessions.tsv alongside the raw AcquisitionDateTime string (line 541). The combination
        enables reconstruction of PatientBirthDate, which is itself on the SIDECAR_DENY_LIST
        and removed from JSON sidecars, undermining the deny-list's intent.

        Calculation: 0.0001 years * 365.25 days/year = 0.036525 days, approximately 52.6 minutes.
        Combined with the exact AcquisitionDateTime (which provides the "study_dt" anchor), an
        adversary can compute birth_date = study_dt - (age_decimal * 365.25) to within approximately
        1 day, effectively reconstructing the removed PatientBirthDate.

        The BIDS specification enforces CheckAge89 (max(age) < 89) for the over-89 HIPAA Safe
        Harbor population, but provides no precision constraint for ages below 89. However,
        peer-reviewed metadata-privacy analysis (arXiv:2509.15278, Imaging Neuroscience 2025)
        identifies age as a principal quasi-identifier in shared neuroimaging datasets.
      </description>
      <evidence>
        _decimal_age at line 156: round(delta.days / 365.25, 4).
        age_val written to sessions.tsv at line 542 ("age": age_val).
        acq_time written to sessions.tsv at line 541 ("acq_time": acq_time_raw).
        PatientBirthDate on SIDECAR_DENY_LIST at line 33.
      </evidence>
      <literature>
        HIPAA Safe Harbor (45 CFR 164.514(b)(2)(i)(C)): ages over 89 must be aggregated.
        BIDS CheckAge89: max(age) < 89 (bids-standard/bids-specification#1633).
        HHS De-identification Guidance: residual quasi-identifier combinations can reconstruct
        suppressed identifiers.
        arXiv:2509.15278 (Imaging Neuroscience 2025): age identified as principal quasi-identifier
        for shared neuroimaging metadata.
      </literature>
      <impact>
        If the dataset is shared with both age (4 decimal places) and acq_time in sessions.tsv,
        PatientBirthDate can be reconstructed to within ~1 day, defeating the purpose of removing
        it from JSON sidecars. For participants with uncommon demographic profiles, this
        combination may enable re-identification.
      </impact>
      <recommendation>
        (1) Truncate age to integer years (consistent with ABCD Data Release conventions and most
        major neuroimaging data-sharing platforms). (2) If sub-year precision is scientifically
        required, use age-banding (e.g., 6-month bins) rather than exact decimal values.
        (3) Document the age precision policy in the pipeline's data management plan.
        (4) Consider implementing BIDS-recommended date-shifting for acq_time (see F4).
      </recommendation>
    </finding>

    <finding id="F3" severity="major" category="validity">
      <location file="fmri_bids_recon/stage4_assemble.py" lines="499, 541 vs. 292" />
      <description>
        The pipeline writes acq_time to sessions.tsv using the raw DICOM AcquisitionDateTime
        string (line 541: "acq_time": acq_time_raw), while scans.tsv uses _normalize_acq_time()
        (line 292 and similar), which parses and re-formats via datetime.isoformat(). This
        produces two distinct behaviors:

        (1) Format inconsistency: sessions.tsv may contain non-ISO8601 date strings
        (e.g., "20260115120000.000000" in DICOM format), while scans.tsv always contains
        ISO8601 ("2026-01-15T12:00:00").

        (2) BIDS format violation: the BIDS specification requires acq_time in both files to
        conform to the same ISO8601 format (YYYY-MM-DDThh:mm:ss[.000000][Z|+hh:mm|-hh:mm]),
        referenced from the Common Principles Units section. Raw DICOM datetime strings do
        not conform to this requirement.
      </description>
      <evidence>
        sessions.tsv: line 541 writes acq_time_raw (from first_raw.get("AcquisitionDateTime")).
        scans.tsv: line 292 writes _normalize_acq_time(series.raw), which calls
        _parse_acquisition_datetime(val).isoformat() at line 119.
        BIDS format requirement: "YYYY-MM-DDThh:mm:ss[.000000][Z|+hh:mm|-hh:mm]" per
        Common Principles Units section.
      </evidence>
      <literature>
        BIDS Specification, Common Principles, Units
        (https://bids-specification.readthedocs.io/en/stable/common-principles.html):
        "YYYY-MM-DDThh:mm:ss[.000000][Z|+hh:mm|-hh:mm]".
        R2 research: "format/privacy requirements for acq_time are identical across sessions.tsv
        and scans.tsv per the shared Units reference."
      </literature>
      <impact>
        (1) bids-validator may flag the non-ISO8601 sessions.tsv acq_time as a format error.
        (2) Downstream tools expecting ISO8601 timestamps may fail to parse the raw DICOM format.
        (3) The raw DICOM format may retain sub-second precision that ISO normalization would truncate.
      </impact>
      <recommendation>
        Apply _normalize_acq_time() (or an equivalent ISO8601 normalization) to the sessions.tsv
        acq_time value at line 541, consistent with the scans.tsv path. Replace
        "acq_time": acq_time_raw with "acq_time": _normalize_acq_time(first_raw).
      </recommendation>
    </finding>

    <finding id="F4" severity="major" category="scientific_rigor">
      <location file="fmri_bids_recon/stage4_assemble.py" lines="292, 541" />
      <description>
        The BIDS specification RECOMMENDS random per-subject day-shifting for acq_time values
        as a privacy anonymization mechanism, with shifted dates flagged by setting the year
        to 1925 or earlier. Neither the scans.tsv nor sessions.tsv acq_time values are shifted
        in the current pipeline. Combined with exact decimal age (F2), the unshifted timestamps
        represent a maximally informative temporal fingerprint.

        While date-shifting is a BIDS RECOMMENDATION (not a REQUIREMENT), the pipeline's stated
        purpose of preparing data for documentation and publication implies a context where
        date-shifting would be expected by reviewers and data-sharing platforms.
      </description>
      <evidence>
        scans.tsv writes ISO-normalized but unshifted acq_time at lines 292, 305, 323, 351, etc.
        sessions.tsv writes raw (unshifted) acq_time at line 541.
        BIDS Common Principles: "Dates can be shifted by a random number of days for privacy
        protection reasons. To distinguish real dates from shifted dates, it is RECOMMENDED to
        set shifted dates to the year 1925 or earlier."
      </evidence>
      <literature>
        BIDS Specification, Common Principles, Units (deidentification subsection).
        R2 research confirmed this is a documented BIDS RECOMMENDATION.
      </literature>
      <impact>
        Without date-shifting, exact acquisition timestamps are retained in BIDS metadata files.
        These timestamps, combined with other quasi-identifiers (age, sex, site), increase
        re-identification risk for shared datasets.
      </impact>
      <recommendation>
        Implement an optional date-shifting mechanism: (1) generate a random per-subject day offset
        (stored in a secure lookup table not included in shared data), (2) apply the offset to all
        acq_time values for that subject, (3) set the year to 1925 or earlier per BIDS convention
        to flag the shift. This should be configurable (opt-in for data sharing, opt-out for
        internal use).
      </recommendation>
    </finding>

    <finding id="F5" severity="major" category="reproducibility">
      <location file="tests/fmri-bids-recon_test_report_20260716.md" lines="1-375" />
      <description>
        A 375-line XA30 end-to-end test report is committed in the tests/ directory. This file
        contains protocol-specific references (ABCD protocol), platform-specific details
        (Siemens XA30, NumarisX), specific dataset characteristics (299 sidecar/NIfTI pairs,
        33 unique SeriesNumbers), series descriptions referencing real protocol names
        (e.g., ABCD_fMRI_rest_SBRef), and nine bug fixes specific to the XA30 platform.

        This is a project-specific artifact inappropriate for publication as part of the
        pipeline's source distribution. It reveals dataset characteristics, protocol names,
        and platform-specific implementation details that tie the pipeline to a specific
        deployment context.
      </description>
      <evidence>
        File: tests/fmri-bids-recon_test_report_20260716.md (14,208 bytes).
        Line 1: "fmri-bids-recon Pipeline Test Report: XA30 End-to-End Validation".
        Line 5: "ABCD protocol dataset acquired on Siemens XA30".
        Line 18: "299 sidecar/NIfTI pairs from a single session (33 unique SeriesNumbers)".
      </evidence>
      <literature>N/A</literature>
      <impact>
        If included in a public repository, this file discloses protocol and platform details
        that may be considered sensitive or that tie the pipeline to a specific dataset in a
        way that could compromise blinding or data provenance.
      </impact>
      <recommendation>
        Remove from tests/ before publication. If the report is needed for internal reference,
        move it to a non-distributed directory or add it to .gitignore (once version control
        is established).
      </recommendation>
    </finding>

    <finding id="F6" severity="major" category="robustness">
      <location file="fmri_bids_recon/__main__.py" lines="15, 235-237, 251-252" />
      <description>
        The pipeline uses Python's pickle module to serialize intermediate state between
        Phase 1 (convert) and Phase 3 (assemble). The intermediate dict contains Series
        objects (frozen dataclass with 22+ fields including numpy arrays for affine/voxel
        geometry), role assignments, label dictionaries, run indices, fieldmap mappings,
        physio pairs, and registry deltas.

        Pickle serialization has two concerns for a pipeline intended for publication:

        (1) Security: pickle.load() executes arbitrary code embedded in the serialized data.
        While the pipeline controls the write path (the pickle is written by Phase 1 and read
        by Phase 3 within the same invocation), if the staging directory is writable by other
        processes, a malicious pickle could be substituted.

        (2) Version brittleness: pickled objects encode the exact class layout at serialization
        time. Any change to the Series dataclass, role enum, or other serialized types between
        pipeline versions will cause deserialization failures with opaque error messages.
      </description>
      <evidence>
        pickle.dump at line 237: pickle.dump(intermediate, fh, protocol=pickle.HIGHEST_PROTOCOL).
        pickle.load at line 252: intermediate = pickle.load(fh).
        Intermediate dict structure at lines 225-234.
      </evidence>
      <literature>
        Python documentation: "Warning: The pickle module is not secure. Only unpickle data
        you trust." (https://docs.python.org/3/library/pickle.html).
      </literature>
      <impact>
        (1) Security: low practical risk in single-invocation mode, but increases if the pipeline
        is extended to support separate convert/assemble runs or if staging directories are shared.
        (2) Version brittleness: any structural change to serialized types between pipeline versions
        will break resume-from-intermediate workflows. Error messages from pickle deserialization
        failures are typically unhelpful for end users.
      </impact>
      <recommendation>
        Replace pickle with JSON serialization of a well-defined intermediate schema. This requires
        custom serialization for numpy arrays (e.g., base64-encoded or list-of-lists) and Path
        objects (str conversion), but provides version-stable, inspectable intermediate files and
        eliminates the arbitrary code execution surface.
      </recommendation>
    </finding>

    <finding id="F7" severity="major" category="robustness">
      <location file="fmri_bids_recon/tsv.py" lines="6, 44, 109" />
      <description>
        The tsv module uses fcntl.flock() for advisory file locking during atomic TSV upsert
        operations. fcntl is a POSIX-only module unavailable on Windows. While neuroimaging
        pipelines are predominantly deployed on POSIX systems (Linux clusters, macOS workstations),
        this creates an unconditional import-time failure on Windows and is an undocumented
        portability constraint.
      </description>
      <evidence>
        import fcntl at line 6.
        fcntl.flock(fh, fcntl.LOCK_EX) at line 44.
        fcntl.flock(fh, fcntl.LOCK_SH) at line 109.
      </evidence>
      <literature>N/A</literature>
      <impact>
        The pipeline cannot be imported on Windows (ImportError at module load time). This may
        limit adoption if published as a general-purpose BIDS reconstruction tool, though the
        practical impact is low given the neuroimaging field's POSIX ecosystem.
      </impact>
      <recommendation>
        Document the POSIX requirement in the README/RUNBOOK. Optionally, wrap fcntl usage in a
        platform-conditional import with a no-op fallback on Windows (acceptable since advisory
        locking is a race-condition mitigation, not a correctness requirement, for single-process
        pipeline execution).
      </recommendation>
    </finding>

    <!-- ================================================================== -->
    <!-- MINOR                                                              -->
    <!-- ================================================================== -->

    <finding id="F8" severity="minor" category="validity">
      <location file="fmri_bids_recon/report.py" lines="104" />
      <description>
        The conversion report writes the absolute config_path to the provenance section
        (line 104: f"- **Config path**: {config_path}"). This embeds the local filesystem path
        (e.g., /home/user/projects/study/config.yaml) in a report that may be committed to
        a repository or shared alongside the dataset. While not PHI, this constitutes a local
        path leak that may reveal directory structure, username, or project organization.
      </description>
      <evidence>
        report.py line 104: lines.append(f"- **Config path**: {config_path}")
      </evidence>
      <literature>N/A</literature>
      <impact>
        Low. Path information in conversion reports could reveal filesystem structure but is
        not a direct privacy risk. However, for publication-ready code, this is an unnecessary
        information disclosure.
      </impact>
      <recommendation>
        Write only the filename (config_path.name or Path(config_path).name) rather than the
        absolute path. Alternatively, make the provenance path configurable (absolute for
        internal use, basename-only for shared reports).
      </recommendation>
    </finding>

    <finding id="F9" severity="minor" category="validity">
      <location file="fmri_bids_recon/stage4_assemble.py" lines="156" />
      <description>
        The _decimal_age function computes age using delta.days / 365.25, which is a standard
        astronomical year approximation. This introduces a systematic error of up to ~12 hours
        (0.5 days) for specific date ranges due to the difference between the Gregorian calendar's
        actual leap-year distribution and the constant 365.25 divisor. For the pipeline's stated
        precision of 4 decimal places (0.0001 years ~ 53 minutes), this approximation error
        can exceed the reported precision.

        However, if F2's recommendation to truncate age to integer years is adopted, this finding
        becomes moot, as the approximation error is negligible at integer precision.
      </description>
      <evidence>
        line 156: return round(delta.days / 365.25, 4)
      </evidence>
      <literature>
        The Gregorian calendar has 97 leap years per 400-year cycle, giving an average year
        length of 365.2425 days, not 365.25. The difference (0.0075 days/year) accumulates
        to ~0.15 days over a 20-year age span.
      </literature>
      <impact>
        At 4 decimal places, the reported age may be off by up to ~0.0004 years (~3.5 hours)
        for a typical neuroimaging participant age range. This is below the threshold of
        scientific significance for any downstream analysis.
      </impact>
      <recommendation>
        If sub-year precision is retained (counter to F2's recommendation), replace
        delta.days / 365.25 with delta.days / 365.2425 or use dateutil.relativedelta for
        calendar-aware age computation. If integer-year truncation is adopted per F2, no
        change is needed.
      </recommendation>
    </finding>

    <finding id="F10" severity="minor" category="reproducibility">
      <location file="tests/test_physio.py" lines="19" />
      <description>
        The test_physio.py module docstring contains the phrase "action item" (line 19:
        "and it is routed as an action item"), which is a project-specific workflow marker.
        While this occurs in a docstring rather than executable code, it reads as an internal
        project management reference that would be out of place in published source code.
      </description>
      <evidence>
        test_physio.py line 19: "action item."
      </evidence>
      <literature>N/A</literature>
      <impact>
        Cosmetic. No functional impact, but may confuse readers of published code who are
        unfamiliar with the project's internal workflow terminology.
      </impact>
      <recommendation>
        Rephrase to a neutral statement, e.g., "is recommended as a future validation step"
        or "is deferred to integration testing against vendor data."
      </recommendation>
    </finding>

    <finding id="F11" severity="minor" category="reproducibility">
      <location file="tests/conftest.py" lines="464-471" />
      <description>
        The PHI_RAW test fixture dictionary uses placeholder values that stylistically resemble
        real PHI: "ZZTOP0001" (PatientID), "DOE^JANE" (PatientName), "Somewhere Imaging Centre"
        (InstitutionName), "12345" (DeviceSerialNumber). Additional PHI-like values appear in
        test_assemble.py ("QQBOTTOM9999" at line 339) and test_sidecar.py ("ABC123" at line 70).

        These are clearly synthetic test values and do not constitute actual PHI. However, for a
        pipeline intended for publication, the use of human-name-like patterns (DOE^JANE) in
        test fixtures may require a brief documentation note to preempt reviewer concerns.
      </description>
      <evidence>
        conftest.py:465 "PatientID": "ZZTOP0001"
        conftest.py:466 "PatientName": "DOE^JANE"
        test_assemble.py:339 "QQBOTTOM9999"
        test_sidecar.py:70 PatientID="ABC123"
      </evidence>
      <literature>N/A</literature>
      <impact>
        No functional impact. Cosmetic concern for publication readiness. The values are
        clearly synthetic and the pipeline correctly handles them (scrubbing PatientID and
        PatientName from sidecars, emitting only counts for PatientID cross-checks).
      </impact>
      <recommendation>
        Acceptable as-is for publication. Optionally, replace "DOE^JANE" with a more obviously
        synthetic pattern (e.g., "TEST^FIXTURE") if the publication venue's reviewers are
        expected to scrutinize test fixtures for PHI.
      </recommendation>
    </finding>

    <finding id="F12" severity="minor" category="reproducibility">
      <location file="tests/test_render.py" lines="88-101" />
      <description>
        test_render.py uses hardcoded absolute paths ("/data/bids/", "/staging/") as synthetic
        inputs for testing the _subject_relative_path helper. These are not real local paths
        (they are synthetic test fixtures), but they appear as hardcoded absolute paths in the
        test source and could be mistaken for environment-specific configuration.
      </description>
      <evidence>
        line 88: Path("/data/bids/sub-001/ses-01/func/...")
        line 90: _subject_relative_path(Path("/data/bids"), "001", nii)
        line 101: Path("/staging/sub-001/ses-01/...")
      </evidence>
      <literature>N/A</literature>
      <impact>
        No functional impact. The paths are synthetic and the tests are self-contained.
        Minor cosmetic concern for publication readiness.
      </impact>
      <recommendation>
        Acceptable as-is. The paths are clearly synthetic and follow a common testing pattern.
        If desired, replace with tmp_path fixtures, but this is not necessary for correctness
        or publication readiness.
      </recommendation>
    </finding>

    <finding id="F13" severity="minor" category="assumptions">
      <location file="fmri_bids_recon/stage4_assemble.py" lines="494-496" />
      <description>
        Demographic fields (PatientSex, PatientAge, PatientBirthDate, AcquisitionDateTime) are
        extracted from first_raw, which is defined as next(iter(series_map.values())).raw
        (line 496). series_map is a dict keyed by series number, and dict iteration order is
        insertion order in Python 3.7+. The selection of the "first" series for demographics is
        therefore deterministic but depends on the order in which series were processed during
        Phase 1 (convert).

        If different series within the same session carry different values for PatientSex or
        PatientAge (e.g., due to operator error or protocol differences), the pipeline will
        silently use whichever series was inserted first, without flagging the discrepancy.
        The PatientID cross-check (lines 564-575) flags multi-ID sessions but does not extend
        to PatientSex or PatientAge.
      </description>
      <evidence>
        line 496: first_raw = next(iter(series_map.values())).raw
        PatientID cross-check at lines 564-575 (counts only, correctly PHI-safe).
        No analogous cross-check for PatientSex or PatientAge.
      </evidence>
      <literature>N/A</literature>
      <impact>
        Low. Within-session demographic variation is rare in practice (it would indicate an
        operator error). The PatientID cross-check partially mitigates this by flagging
        multi-identity sessions.
      </impact>
      <recommendation>
        Consider extending the cross-check pattern to PatientSex (flag if more than one
        distinct value across series in a session). PatientAge variation is expected within
        a session (different series acquired at different times) and need not be checked.
      </recommendation>
    </finding>

    <finding id="F14" severity="minor" category="robustness">
      <location file="fmri_bids_recon/stage1_convert.py" lines="163-165" />
      <description>
        The DICOM indexing function uses source.rglob("*") to enumerate all files in the DICOM
        source directory, followed by is_file() filtering and pydicom.dcmread() with
        stop_before_pixels=True for each candidate. For large DICOM directories (e.g., multi-session
        acquisitions with thousands of files), this produces a complete in-memory file list before
        any filtering, and the subsequent pydicom header reads are I/O-bound and sequential.
      </description>
      <evidence>
        line 163: for path in source.rglob("*"):
        line 171: ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
      </evidence>
      <literature>N/A</literature>
      <impact>
        Performance concern only; no correctness impact. For typical neuroimaging session sizes
        (hundreds to low thousands of DICOM files), the performance is acceptable. For very large
        directories (e.g., multi-session bulk imports), memory and time costs scale linearly.
      </impact>
      <recommendation>
        Document the expected directory size in the RUNBOOK. No code change needed for typical
        use cases. If performance becomes a concern for large-scale deployments, consider
        generator-based processing (yield from rglob rather than list accumulation) and parallel
        pydicom header reads.
      </recommendation>
    </finding>

    <!-- ================================================================== -->
    <!-- NOTE                                                               -->
    <!-- ================================================================== -->

    <finding id="F15" severity="note" category="generalizability">
      <location file="fmri_bids_recon/config.py" lines="27-29" />
      <description>
        Geometry tolerance constants (GEOMETRY_POSITION_TOL_MM = 0.1, GEOMETRY_ORIENTATION_TOL
        = 1e-4, GEOMETRY_VOXEL_TOL_MM = 1e-3) are hardcoded module-level constants. The inline
        comment (lines 25-26) documents their rationale: "sized to absorb dcm2niix float jitter,
        NOT voxel-scaled; verified within-block delta 0.0mm, nearest block 2.53mm."

        These tolerances are appropriate for the Siemens XA30 platform verified during development,
        but may require adjustment for other scanner vendors or software versions where dcm2niix
        float precision characteristics differ.
      </description>
      <evidence>
        config.py:27 GEOMETRY_POSITION_TOL_MM = 0.1
        config.py:28 GEOMETRY_ORIENTATION_TOL = 1e-4
        config.py:29 GEOMETRY_VOXEL_TOL_MM = 1e-3
      </evidence>
      <literature>N/A</literature>
      <impact>
        Low. The tolerances are documented, empirically validated, and conservative. If the
        pipeline is applied to data from different platforms, the user should verify tolerance
        appropriateness, but the current values are reasonable defaults.
      </impact>
      <recommendation>
        Document the platform-specific validation in the RUNBOOK (already partially present).
        Consider making tolerances configurable via the study config YAML for multi-platform
        deployments, with the current values as defaults.
      </recommendation>
    </finding>

    <finding id="F16" severity="note" category="scientific_rigor">
      <location file="fmri_bids_recon/runs.py" lines="112-128" />
      <description>
        When the modal volume count is tied (two or more counts with equal frequency), the
        pipeline retains all runs without creating a registry entry, emitting a ReviewFlag.
        This is a conservative, defensible behavior that prioritizes data preservation over
        automated resolution.
      </description>
      <evidence>
        runs.py:117: if len(top) > 1 and top[0][1] == top[1][1]:
        Lines 118-125: ReviewFlag emitted, all runs retained.
      </evidence>
      <literature>N/A</literature>
      <impact>
        None. The behavior is correct and well-documented via the review flag. No data is lost
        or silently modified.
      </impact>
      <recommendation>
        No change needed. The conservative approach is appropriate for a pipeline that prioritizes
        data integrity.
      </recommendation>
    </finding>

    <finding id="F17" severity="note" category="assumptions">
      <location file="fmri_bids_recon/runs.py" lines="132-155" />
      <description>
        When a previously unknown task appears with a single run (n_runs == 1), the pipeline
        accepts the series, registers it in the task registry with volume_count = n_volumes,
        and emits a ReviewFlag noting "new task registered from single run." This is an implicit
        assumption that a single observation is sufficient to establish the expected volume count
        for future sessions.
      </description>
      <evidence>
        runs.py line 112+: single-run branch creates a registry entry.
        ReviewFlag documents the registration.
      </evidence>
      <literature>N/A</literature>
      <impact>
        Low. The review flag ensures the user is notified. If a subsequent session has a different
        volume count for the same task, the exact-match enforcement will flag the discrepancy.
        The single-run registration is a reasonable bootstrap mechanism.
      </impact>
      <recommendation>
        No change needed. The review flag provides adequate notification for manual review.
      </recommendation>
    </finding>

    <finding id="F18" severity="note" category="assumptions">
      <location file="fmri_bids_recon/physio.py" lines="485-504" />
      <description>
        The physio temporal association algorithm assumes a one-to-one correspondence between
        physio recordings and BOLD runs. When multiple physio recordings could be associated with
        the same BOLD run, the nearest-preceding heuristic resolves the ambiguity, but no warning
        is emitted for the discarded association(s). Conversely, if multiple BOLD runs fall within
        the temporal window of a single physio recording, only the nearest-preceding BOLD receives
        the association.
      </description>
      <evidence>
        physio.py:488-492: preceding = [...]; best_bold = max(preceding, key=lambda x: x[0])[1]
      </evidence>
      <literature>N/A</literature>
      <impact>
        Low for typical neuroimaging protocols where physio and BOLD acquisitions are 1:1.
        The heuristic may produce suboptimal associations for non-standard protocols with
        interleaved or overlapping physio recordings.
      </impact>
      <recommendation>
        Consider adding a ReviewFlag when the temporal association is ambiguous (multiple
        candidates within a configurable time window). No change to the default behavior needed.
      </recommendation>
    </finding>

  </findings>

  <summary>
    <critical_count>1</critical_count>
    <major_count>6</major_count>
    <minor_count>7</minor_count>
    <overall_assessment>conditionally_defensible</overall_assessment>

    The fmri-bids-recon pipeline demonstrates strong engineering discipline across its core conversion,
    classification, and assembly logic. The 14-guard validation system, geometry-based fieldmap
    association, atomic TSV writes, and post-hoc scrub audit reflect a mature approach to data
    integrity and error detection.

    The overall assessment is conditionally_defensible: the pipeline is scientifically sound and
    operationally robust for internal use, but requires targeted remediation in three areas before
    it is defensible for data sharing or publication:

    (1) PHI/de-identification: The SIDECAR_DENY_LIST (F1) is incomplete relative to DICOM PS3.15,
    and the combination of exact decimal age with unshifted AcquisitionDateTime (F2, F4) enables
    reconstruction of the deny-listed PatientBirthDate. These findings represent a compound
    privacy vulnerability that must be addressed before any pipeline-processed data is shared.

    (2) BIDS format compliance: The sessions.tsv acq_time format violation (F3) is a concrete
    spec noncompliance that should be straightforward to fix.

    (3) Publication readiness: The committed test report (F5), project markers (F10), and
    absolute path in conversion reports (F8) should be cleaned before the source code is
    published.

    The remaining findings (pickle serialization, fcntl portability, performance, and
    conservative design decisions) are either low-risk or represent defensible engineering
    tradeoffs that should be documented rather than changed.
  </summary>

  <action_items>
    <item priority="P0" target_mode="implement" finding_ref="F1"
          description="Expand SIDECAR_DENY_LIST to include all PS3.15 Basic Profile attributes identified in R1 research (11 additional fields). Update scrub audit and test_assemble.py coverage test. Add configurable de-identification profile level if institutional identifiers are needed for downstream tools." />
    <item priority="P0" target_mode="implement" finding_ref="F2"
          description="Truncate age to integer years in sessions.tsv (and participants.tsv if applicable). Remove 4-decimal-place precision from _decimal_age or change rounding to round(..., 0)." />
    <item priority="P0" target_mode="implement" finding_ref="F3"
          description="Apply _normalize_acq_time() to sessions.tsv acq_time value (line 541) to match scans.tsv normalization and BIDS ISO8601 format requirement." />
    <item priority="P1" target_mode="brainstorm" finding_ref="F4"
          description="Design and implement optional BIDS-recommended date-shifting for acq_time values. Requires discussion of shift-table storage, per-subject offset generation, and configuration interface." />
    <item priority="P1" target_mode="implement" finding_ref="F5"
          description="Remove tests/fmri-bids-recon_test_report_20260716.md from the source distribution before publication." />
    <item priority="P1" target_mode="brainstorm" finding_ref="F6"
          description="Evaluate replacing pickle intermediate serialization with JSON. Requires schema design for Series objects, numpy arrays, and Path objects." />
    <item priority="P2" target_mode="implement" finding_ref="F7"
          description="Document POSIX requirement in README/RUNBOOK. Optionally add platform-conditional fcntl import." />
    <item priority="P2" target_mode="implement" finding_ref="F8"
          description="Write only config filename (not absolute path) to conversion report provenance section." />
    <item priority="P2" target_mode="implement" finding_ref="F10"
          description="Rephrase 'action item' in test_physio.py docstring to publication-neutral language." />
  </action_items>

</cr_report>
