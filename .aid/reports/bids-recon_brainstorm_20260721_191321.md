<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-07-21T19:13:21Z" />
  <context_files>
    <file path="bids-recon_cr_20260721_183128.md" relevance="Source CR report; findings F1-F18, research R1-R3" />
    <file path="bids_recon/stage4_assemble.py" relevance="Contains SIDECAR_DENY_LIST, scrub(), 7 scrub call sites, acq_time handling, _decimal_age" />
    <file path="bids_recon/report.py" relevance="Contains scrub audit (Section 8), SIDECAR_DENY_LIST import, GuardError raise" />
    <file path="bids_recon/__main__.py" relevance="Pickle intermediate serialization (lines 235-237, 251-252); pipeline entry point" />
    <file path="bids_recon/sidecar.py" relevance="Series dataclass (frozen, 22 fields including Path, datetime, tuples)" />
    <file path="bids_recon/tsv.py" relevance="fcntl POSIX-only file locking (lines 6, 44, 109)" />
    <file path="tools/simulated_bids/config.py" relevance="SCANNER dict (missing patient-level fields), DEMOGRAPHICS, modality params" />
    <file path="tools/simulated_bids/modalities.py" relevance="_base_sidecar() merges SCANNER with modality params; 7 modality generators" />
    <file path="tools/simulated_bids/scaffold.py" relevance="participants.tsv, sessions.tsv, scans.tsv generation" />
  </context_files>

  <topics>

    <topic id="T1" title="Remove scrub infrastructure from the production pipeline">
      <summary>
        The pipeline's SIDECAR_DENY_LIST and scrub() function were implemented for
        handling raw DICOM examples during development. They are not intended features
        of the production pipeline. The pipeline is a faithful DICOM-to-BIDS
        reconstruction tool: if information is in the DICOMs, it belongs in the output.
        The pipeline does not restrict what downstream users see of their own data.
        De-identification, if needed, is a downstream responsibility.

        The scrub infrastructure is integrated into the production assembly path at
        7 call sites across all modalities, plus a post-hoc scrub audit in report.py
        that raises a GuardError if any deny-listed fields survive. This must be
        removed entirely.
      </summary>
      <research>
        CR research R1 (DICOM PS3.15) and R3 (re-identification risk) are no longer
        applicable to the pipeline's design: these findings were premised on the
        pipeline being a de-identification tool, which it is not.
        CR research R2 (BIDS acq_time format) remains applicable to the sessions.tsv
        format compliance fix (see T1/C3 below).
      </research>
      <approaches>
        <approach id="A1" label="Remove scrub infrastructure" feasibility="high" risk="low">
          <description>
            Remove SIDECAR_DENY_LIST, scrub(), all call sites, and the scrub audit.
            Replace scrub() calls with direct series.raw passthrough (or dict copy
            where subsequent field additions require it). Keep sourcedata/ provenance
            copies (they preserve raw dcm2niix output before pipeline field additions
            like IntendedFor, B0FieldIdentifier, TaskName).
          </description>
          <pros>Aligns pipeline with its stated purpose. Eliminates information loss. Simple removal.</pros>
          <cons>Tests that assert scrubbing behavior will fail and need separate updates.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        User approved. The pipeline is a faithful reconstruction tool. Scrub
        infrastructure is removed. sourcedata/ provenance copies are retained
        because they preserve the raw dcm2niix sidecar before BIDS-specific
        field additions (IntendedFor, B0FieldIdentifier, B0FieldSource, TaskName).
      </decision>
    </topic>

    <topic id="T2" title="Age precision and calendar approximation">
      <summary>
        CR finding F2 (age re-identification risk) was premised on the pipeline being
        a de-identification tool. Under the faithful-reconstruction philosophy, the
        pipeline should compute age as accurately as possible. The 4-decimal-place
        precision is retained.

        The separate correctness concern (F9) remains: _decimal_age uses 365.25
        days/year instead of the Gregorian average 365.2425, introducing a systematic
        error of up to ~0.0004 years (~3.5 hours) for typical participant ages.
      </summary>
      <research>N/A (correctness, not design)</research>
      <approaches>
        <approach id="A1" label="Fix approximation constant" feasibility="high" risk="low">
          <description>Replace 365.25 with 365.2425 at stage4_assemble.py line 156.</description>
          <pros>More accurate. Trivial change.</pros>
          <cons>None.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        User approved collapse. Keep 4 decimal places. Fix the approximation constant.
      </decision>
    </topic>

    <topic id="T3" title="Date-shifting mechanism">
      <summary>
        CR finding F4 proposed BIDS-recommended date-shifting as a pipeline feature.
        Under the faithful-reconstruction philosophy, de-identification (including
        date-shifting) is a downstream responsibility, not a pipeline feature.
      </summary>
      <research>N/A</research>
      <approaches />
      <decision status="decided" chosen="none">
        Collapsed. Date-shifting is not a pipeline responsibility. No implementation.
      </decision>
    </topic>

    <topic id="T4" title="BIDS generator: add patient-level fields to simulated sidecars">
      <summary>
        The BIDS generator at tools/simulated_bids/ produces JSON sidecars that
        include institutional/scanner fields (InstitutionName, DeviceSerialNumber,
        StationName, etc.) but omit all patient-level DICOM fields that dcm2niix
        normally outputs. The generator's SCANNER dict in config.py has 17
        scanner-level fields; no patient-level fields are present.

        With the pipeline no longer scrubbing sidecars, the simulated datasets
        must include these fields to accurately represent what dcm2niix produces
        from real DICOMs and to test the pipeline's handling of complete sidecars.

        14 fields need to be added (matching the fields dcm2niix outputs from
        Siemens XA30 DICOMs, consistent with the raw DICOM examples the pipeline
        was developed against):

        Per-subject fields (derived from DEMOGRAPHICS):
          - PatientID: derived from participant_id (e.g., "sub-001" -> "SIM001")
          - PatientName: fabricated (e.g., "SIMULATED^SUBJECTnnn")
          - PatientSex: from DEMOGRAPHICS[].sex
          - PatientBirthDate: computed from age_ses01 and a simulated study date
            (YYYYMMDD format, e.g., "20170315")
          - PatientAge: computed from age at session (e.g., "011Y")
          - PatientSize: simulated height in meters (e.g., 1.45)
          - PatientWeight: simulated weight in kg (e.g., 38.0)

        Per-session fields:
          - AcquisitionDateTime: simulated ISO datetime per session
            (e.g., "2026-01-15T10:30:00.000000")

        Per-series fields:
          - SeriesInstanceUID: fabricated unique UID per series
            (e.g., "1.2.826.0.1.3680043.8.498.SIM.{sub}.{ses}.{series_num}")
          - StudyInstanceUID: fabricated unique UID per study/session
            (e.g., "1.2.826.0.1.3680043.8.498.SIM.{sub}.{ses}")

        Per-study fields (constant or semi-constant):
          - StudyID: simulated (e.g., "SIM_STUDY_001")
          - AccessionNumber: simulated (e.g., "SIM_ACC_{sub}_{ses}")
          - ReferringPhysicianName: simulated (e.g., "SIMULATED^PHYSICIAN")
          - PerformedProcedureStepDescription: from SeriesDescription or
            ProtocolName (e.g., "ABCD_T1w_MPR_vNav")

        Implementation approach: add a per-subject/session patient_fields dict
        computed from DEMOGRAPHICS, pass it to _base_sidecar(), and merge it
        into every sidecar. UIDs are generated deterministically from subject,
        session, and series number using the generator's seeded RNG to ensure
        reproducibility.
      </summary>
      <research>N/A (implementation specification)</research>
      <approaches>
        <approach id="A1" label="Inject patient fields via _base_sidecar" feasibility="high" risk="low">
          <description>
            Extend _base_sidecar(params, series_num) to accept a patient_fields dict.
            Compute patient_fields per subject/session in the main generation loop.
            Merge into every sidecar alongside SCANNER and modality params.
          </description>
          <pros>Minimal generator restructuring. All fields centralized in one dict per subject/session.</pros>
          <cons>_base_sidecar signature changes; all callers must be updated.</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        User directed: generator must include simulated values for all fields
        present in the raw DICOM example. The 14 fields listed above cover the
        patient-level and identifier fields that dcm2niix outputs from Siemens
        XA30 DICOMs.
      </decision>
    </topic>

    <topic id="T5" title="Regenerate simulated datasets">
      <summary>
        After the generator is updated with patient-level fields (T4), both
        simulated datasets must be regenerated:
        - adversarial: 13 subjects, 3 sessions each (previously complete, but
          with missing patient-level fields)
        - clean: 4 subjects, 3 sessions each (previously incomplete; generation
          crashed during sub-104/ses-03)

        Both datasets reside at ~/simulated-bids/ (adversarial/ and clean/).
      </summary>
      <research>N/A</research>
      <approaches>
        <approach id="A1" label="Full regeneration of both datasets" feasibility="high" risk="low">
          <description>
            Delete existing adversarial/ and clean/ directories. Regenerate both
            using the updated generator. The generator uses deterministic seeding
            (adversarial: seed=42, clean: seed=1729) so output is reproducible.
          </description>
          <pros>Clean state. No partial artifacts. Reproducible.</pros>
          <cons>Requires deletion of existing datasets (user approval needed at execution time).</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        Full regeneration. Both datasets must be regenerated with the updated
        generator to include patient-level fields in all sidecars.
      </decision>
    </topic>

    <topic id="T6" title="Replace pickle intermediate serialization with JSON">
      <summary>
        CR finding F6 flagged that __main__.py uses pickle.dump() (line 235) and
        pickle.load() (line 251) to serialize the Phase 1 (convert) output and
        deserialize it at Phase 3 (assemble). Two concerns: (1) pickle.load()
        executes arbitrary Python during deserialization, and (2) pickled objects
        are coupled to exact class definitions, making them version-brittle.

        The intermediate dict (lines 220-234) contains 12 keys whose values
        span several custom dataclasses (Series, FieldmapPair, Mapping,
        RegistryDelta, TaskRegistryEntry), stdlib types requiring conversion
        (Path, datetime, tuples used as frozen sequences, StrEnum), and
        plain dicts/lists/strings/ints/bools. A JSON replacement requires
        custom encode/decode for: Series (22 fields, frozen dataclass with
        Path, datetime, tuple fields), FieldmapPair (contains two Series),
        Mapping (contains list of FieldmapPair and dict mapping int to
        list of Series), RegistryDelta (contains dict of TaskRegistryEntry),
        ReviewFlag (Exception subclass), Role (StrEnum), and int dict keys
        (JSON requires string keys).
      </summary>
      <research>N/A (robustness, not design)</research>
      <approaches>
        <approach id="A1" label="Replace with JSON via custom encoder/decoder" feasibility="medium" risk="low">
          <description>
            Add a json_intermediate.py module with dump_intermediate(data, path)
            and load_intermediate(path) functions. Implement _to_dict/_from_dict
            round-trip methods for Series, FieldmapPair, Mapping, RegistryDelta,
            TaskRegistryEntry, and ReviewFlag. Handle Path (str conversion),
            datetime (isoformat), tuples (tagged lists or positional convention),
            StrEnum (string value), and int dict keys (str conversion with int
            restoration on load). Replace pickle.dump/pickle.load in __main__.py
            lines 235-237 and 251-252. Change file extension from .pkl to .json.
          </description>
          <pros>Eliminates arbitrary code execution risk. Human-readable intermediates. Version-resilient (field additions are forward-compatible). Aligns with the pipeline's existing JSON-centric data model.</pros>
          <cons>Non-trivial implementation: Series alone has 22 fields. Requires careful round-trip testing. Slightly larger intermediate files and slower serialization (negligible relative to dcm2niix runtime).</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        User directed: replace pickle with JSON. Implementation via a dedicated
        json_intermediate.py module with custom encode/decode for the pipeline's
        dataclass hierarchy.
      </decision>
    </topic>

    <topic id="T7" title="fcntl POSIX-only file locking">
      <summary>
        CR finding F7 flagged that bids_recon/tsv.py uses fcntl.flock()
        (imported at line 6, called at lines 44 and 109), which is a
        POSIX-only module unavailable on Windows.

        The pipeline's operational environment is exclusively POSIX: its core
        external dependencies (dcm2niix, pydeface/AFNI, FreeSurfer) have no
        Windows builds. There is no realistic Windows deployment scenario.
        Adding a cross-platform fallback (msvcrt or the filelock package) would
        produce dead code on every real deployment.
      </summary>
      <research>N/A</research>
      <approaches>
        <approach id="A1" label="Document POSIX requirement, no code change" feasibility="high" risk="low">
          <description>
            Document the POSIX-only requirement in the pipeline's documentation.
            No code change.
          </description>
          <pros>Honest about operational reality. No dead code.</pros>
          <cons>Windows users get ImportError without inline context (mitigated by documentation).</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        User approved. Documentation-only item routed to /document, not /implement.
        No code change.
      </decision>
    </topic>

    <topic id="T8" title="Absolute config_path in pipeline reports">
      <summary>
        CR finding F8 flagged that report.py line 104 writes the absolute
        filesystem path of the user's configuration file into the pipeline's
        output report. Under the faithful-reconstruction philosophy, this is
        operational provenance (which configuration file produced this BIDS
        reconstruction), analogous to dcm2niix writing ConversionSoftwareVersion
        into sidecars. The user who ran the pipeline already knows the path;
        it is their data on their system.
      </summary>
      <research>N/A</research>
      <approaches />
      <decision status="decided" chosen="none">
        Non-finding under the faithful-reconstruction philosophy. The config
        path is user-provided input metadata, not embedded developer state.
        No change.
      </decision>
    </topic>

  </topics>

  <action_items>
    <item priority="P0" target_mode="implement" description="C1: Remove SIDECAR_DENY_LIST (lines 26-45) and scrub() function (lines 48-65) from bids_recon/stage4_assemble.py. Replace 7 scrub() call sites: lines 287, 302 (anat) pass series.raw directly; lines 318, 346 (BOLD/SBRef) replace scrub(series.raw) with dict(series.raw) to allow TaskName addition; lines 375, 408 (DWI/DWI_SBREF) pass series.raw directly; line 440 (fieldmap) pass series.raw directly. Update the module docstring at line 4 to remove 'scrubbed' reference. Keep sourcedata/ provenance copies unchanged." />
    <item priority="P0" target_mode="implement" description="C2: Remove scrub audit infrastructure from bids_recon/report.py. Remove the SIDECAR_DENY_LIST import (line 17) and the GuardError import (line 18; only used for scrub audit). Remove Section 8 'SIDECAR SCRUB AUDIT' (lines 216-260). Update the module docstring (line 4) to remove 'PHI-scrub audit'. Update the function docstring (lines 42-45) to remove scrub audit reference and the Raises GuardError block (lines 79-83). The report becomes a 7-section document." />
    <item priority="P0" target_mode="implement" description="C3: Fix sessions.tsv acq_time format compliance. In bids_recon/stage4_assemble.py line 541, replace 'acq_time': acq_time_raw with 'acq_time': _normalize_acq_time(first_raw) to match scans.tsv normalization and BIDS ISO8601 format requirement (YYYY-MM-DDThh:mm:ss)." />
    <item priority="P0" target_mode="implement" description="C4: Fix calendar approximation in _decimal_age. In bids_recon/stage4_assemble.py line 156, replace 365.25 with 365.2425 (Gregorian mean year length)." />
    <item priority="P0" target_mode="implement" description="C5: Add 14 patient-level fields to the BIDS generator. In tools/simulated_bids/config.py, add a PATIENT_FIELDS_TEMPLATE dict or equivalent structure. In tools/simulated_bids/modalities.py, extend _base_sidecar() to accept and merge a patient_fields dict. Update all 7 modality generators (generate_t1w, generate_t2w, generate_bold, generate_dwi, generate_fmap_epi, and their SBRef variants) to pass patient_fields. Compute per-subject fields from DEMOGRAPHICS: PatientID derived from participant_id, PatientName fabricated, PatientSex from demographics, PatientBirthDate computed from age and simulated study date, PatientAge formatted as NNNy, PatientSize and PatientWeight simulated. Compute per-session fields: AcquisitionDateTime as a simulated ISO datetime. Compute per-series fields: SeriesInstanceUID and StudyInstanceUID as deterministic fabricated UIDs. Set per-study fields: StudyID, AccessionNumber, ReferringPhysicianName, PerformedProcedureStepDescription." />
    <item priority="P0" target_mode="implement" description="C6: Regenerate both simulated datasets at ~/simulated-bids/ using the updated generator. Delete existing adversarial/ and clean/ directories (requires explicit user permission at execution time). Run the generator for both profiles: adversarial (13 subjects, seed=42) and clean (4 subjects, seed=1729). Verify all output sidecars contain the 14 new patient-level fields." />
    <item priority="P0" target_mode="implement" description="C7: Replace pickle intermediate serialization with JSON in bids_recon/__main__.py. Create a new module bids_recon/json_intermediate.py with dump_intermediate(data, path) and load_intermediate(path) functions. Implement custom encode/decode for the intermediate dict's type graph: Series (22-field frozen dataclass with Path, datetime, tuple fields), FieldmapPair (contains two Series, plus str/int fields), Mapping (list of FieldmapPair, dict[int, list[Series]], dict[int, str]), RegistryDelta (dict[str, TaskRegistryEntry], list[str]), TaskRegistryEntry (str, int|None, str, tuple|None), ReviewFlag (Exception subclass; serialize as {category, message, context}), Role (StrEnum; serialize as string value). Handle Path (str), datetime (isoformat), tuples (list with positional convention or tagged), int dict keys (str with int restoration on load). In __main__.py: replace 'import pickle' (line 15) with 'from .json_intermediate import dump_intermediate, load_intermediate'; replace pickle.dump (lines 235-237) with dump_intermediate(intermediate, json_path); replace pickle.load (lines 251-252) with load_intermediate(json_path); change file extension from .pkl to .json (lines 235, 247)." />
    <item priority="P1" target_mode="document" description="C8: Document the POSIX-only requirement for the pipeline. The fcntl module (bids_recon/tsv.py lines 6, 44, 109) and external tool dependencies (dcm2niix, pydeface/AFNI, FreeSurfer) restrict the pipeline to POSIX systems (Linux, macOS). No code change." />
  </action_items>

  <next_steps>
    Pass this report to /implement for tech spec generation and build execution.
    Execution order: C1 and C2 (pipeline scrub removal) first, then C3 and C4
    (pipeline correctness fixes), then C7 (pickle-to-JSON replacement), then
    C5 (generator update), then C6 (dataset regeneration). C1/C2 can be
    parallelized. C3/C4 can be parallelized. C5 must precede C6. C7 is
    independent of C1-C4 but should precede C5/C6 to ensure intermediates
    are JSON before regeneration.

    C8 (POSIX documentation) is routed to /document, not /implement.

    Note: removing scrub infrastructure (C1/C2) will cause test failures in
    tests/test_assemble.py (imports SIDECAR_DENY_LIST, scrub; tests scrub behavior)
    and tests/test_report.py (tests scrub audit). These test updates are not included
    in this implement plan per user direction that tests/ changes are out of scope
    for this pass.

    CR findings disposition (complete reconciliation against F1-F18):
    - F1 (deny-list): reframed as T1 (remove scrub). C1/C2.
    - F2 (age re-id): collapsed under faithful-reconstruction. Non-finding.
    - F3 (acq_time format): C3.
    - F4 (date-shifting): collapsed (T3). Not pipeline responsibility.
    - F5 (ABCD test report): collapsed. tests/ not published.
    - F6 (pickle): T6. C7.
    - F7 (fcntl POSIX): T7. C8 (documentation only).
    - F8 (config_path): T8. Non-finding under faithful-reconstruction.
    - F9 (365.25): C4.
    - F10 ("action item" marker): collapsed. tests/ not published.
    - F11 (PHI-like fixtures): collapsed. Expected for PHI-processing pipeline.
    - F12 (hardcoded test paths): collapsed. tests/ not published.
    - F13 (first_raw selection): CR recommendation informational. No action.
    - F14 (rglob performance): CR recommendation documentation-only. No action.
    - F15-F18 (notes): CR recommended no changes. No action.
  </next_steps>

</brainstorm_report>
