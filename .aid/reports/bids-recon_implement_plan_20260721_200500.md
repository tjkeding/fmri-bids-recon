<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-21T20:05:00Z" />
  <input_reports>
    <report path="bids-recon_brainstorm_20260721_191321.md" mode="brainstorm" key_items="7" />
  </input_reports>

  <changes>

    <change id="C1" priority="P0" source_item="brainstorm C1">
      <file path="bids_recon/stage4_assemble.py" action="modify" />
      <description>
        Remove the SIDECAR_DENY_LIST frozenset (lines 26-45) and scrub() function
        (lines 48-65) from stage4_assemble.py. Replace all 7 scrub() call sites
        with direct series.raw passthrough or dict(series.raw) where downstream
        mutation is required. Update the module docstring (line 4) to remove
        "scrubbed JSON sidecars" language.
      </description>
      <spec>
        1. Delete module docstring reference: line 4, replace "writes scrubbed JSON
           sidecars" with "writes JSON sidecars".

        2. Delete lines 26-65 entirely (the PHI deny-list comment block,
           SIDECAR_DENY_LIST frozenset, and the scrub() function).

        3. Replace 7 call sites:
           - Line 287: `_write_json(anat_dir / f"{stem}.json", scrub(series.raw))`
             Replace with: `_write_json(anat_dir / f"{stem}.json", series.raw)`

           - Line 302: `_write_json(anat_dir / f"{stem}.json", scrub(series.raw))`
             Replace with: `_write_json(anat_dir / f"{stem}.json", series.raw)`

           - Lines 318-320:
             ```
             data = scrub(series.raw)
             data["TaskName"] = labels[snum]
             ```
             Replace with:
             ```
             data = dict(series.raw)
             data["TaskName"] = labels[snum]
             ```
             (dict copy needed because series.raw is shared and TaskName is added)

           - Lines 346-348:
             ```
             data = scrub(series.raw)
             data["TaskName"] = labels[snum]
             ```
             Replace with:
             ```
             data = dict(series.raw)
             data["TaskName"] = labels[snum]
             ```

           - Line 375: `_write_json(dwi_dir / f"{stem}.json", scrub(series.raw))`
             Replace with: `_write_json(dwi_dir / f"{stem}.json", series.raw)`

           - Line 408: `_write_json(dwi_dir / f"{stem}.json", scrub(series.raw))`
             Replace with: `_write_json(dwi_dir / f"{stem}.json", series.raw)`

           - Line 440: `_write_json(fmap_dir / f"{stem}.json", scrub(series.raw))`
             Replace with: `_write_json(fmap_dir / f"{stem}.json", series.raw)`
      </spec>
      <dependencies>none</dependencies>
      <risk>low - pure removal; call site replacements are mechanical</risk>
      <rollback>Restore SIDECAR_DENY_LIST, scrub(), and all 7 call sites from backup</rollback>
    </change>

    <change id="C2" priority="P0" source_item="brainstorm C2">
      <file path="bids_recon/report.py" action="modify" />
      <description>
        Remove scrub audit infrastructure from report.py. Remove Section 8
        (SIDECAR SCRUB AUDIT), the SIDECAR_DENY_LIST import, the GuardError
        import (only used for scrub audit), and update docstrings.
      </description>
      <spec>
        1. Line 4: module docstring, replace "and PHI-scrub audit" with nothing
           (delete the phrase). Result: "Writes a human-readable Markdown report
           summarising the provenance, exclusions, unclassified series, fieldmap
           mapping, and PatientID cross-check for a single subject/session
           conversion."

        2. Line 17: delete `from .stage4_assemble import SIDECAR_DENY_LIST`

        3. Line 18: delete `from .errors import GuardError`

        4. Lines 42-44: update function docstring. Replace "The report covers
           eight sections: provenance, excluded runs, unclassified series,
           auto-registered tasks, review flags, fieldmap mapping, PatientID
           cross-check, and a sidecar scrub audit." with "The report covers
           seven sections: provenance, excluded runs, unclassified series,
           auto-registered tasks, review flags, fieldmap mapping, and PatientID
           cross-check."

        5. Delete "The report contains NO PHI values\n    under any circumstance.\n"
           from the docstring (line 44-45). The pipeline no longer restricts
           information; this claim is no longer accurate.

        6. Lines 79-83: delete the `Raises` block:
           ```
           Raises
           ------
           GuardError
               If any key from SIDECAR_DENY_LIST is found in a BIDS sidecar during
               the scrub audit (Section 8).
           ```

        7. Delete lines 216-260 entirely (Section 8: SIDECAR SCRUB AUDIT).
           This removes the comment block, the session_dir scan, the
           surviving_keys dict, the audit logic, the GuardError raise, and
           the "All sidecars clean" else branch.

        8. The report now ends after Section 7 (PatientID CROSS-CHECK) at
           the existing "Write report" block.
      </spec>
      <dependencies>C1 (SIDECAR_DENY_LIST must be removed from stage4_assemble.py
        before this import removal; otherwise execution order does not matter
        since both changes land before any test run)</dependencies>
      <risk>low - pure removal of dead code after C1 removes the symbol</risk>
      <rollback>Restore imports, Section 8, and docstrings from backup</rollback>
    </change>

    <change id="C3" priority="P0" source_item="brainstorm C3">
      <file path="bids_recon/stage4_assemble.py" action="modify" />
      <description>
        Fix sessions.tsv acq_time to use ISO8601-normalized format instead of
        raw DICOM string, consistent with scans.tsv normalization.
      </description>
      <spec>
        Line 541: replace
          `"acq_time": acq_time_raw,`
        with
          `"acq_time": _normalize_acq_time(first_raw),`

        _normalize_acq_time (lines 113-121) already exists and is used for
        scans.tsv rows throughout the file. It parses the raw DICOM
        AcquisitionDateTime string and re-formats it via .isoformat(),
        returning 'n/a' on parse failure.
      </spec>
      <dependencies>none (independent of C1/C2; same file as C1 but
        non-overlapping lines)</dependencies>
      <risk>low - uses existing helper already proven across all scans.tsv rows</risk>
      <rollback>Revert line 541 to `"acq_time": acq_time_raw,`</rollback>
    </change>

    <change id="C4" priority="P0" source_item="brainstorm C4">
      <file path="bids_recon/stage4_assemble.py" action="modify" />
      <description>
        Fix calendar approximation in _decimal_age from Julian year (365.25)
        to Gregorian mean year (365.2425).
      </description>
      <spec>
        Line 156: replace
          `return round(delta.days / 365.25, 4)`
        with
          `return round(delta.days / 365.2425, 4)`
      </spec>
      <dependencies>none (independent; same file as C1/C3 but
        non-overlapping lines)</dependencies>
      <risk>low - single constant change; existing test coverage for
        _decimal_age will catch regressions</risk>
      <rollback>Revert 365.2425 to 365.25</rollback>
    </change>

    <change id="C5" priority="P0" source_item="brainstorm C7">
      <file path="bids_recon/json_intermediate.py" action="create" />
      <file path="bids_recon/__main__.py" action="modify" />
      <description>
        Replace pickle intermediate serialization with JSON. Create a new
        module json_intermediate.py with custom encode/decode for the
        pipeline's dataclass hierarchy. Update __main__.py to use it.
      </description>
      <spec>
        **New file: bids_recon/json_intermediate.py**

        Two public functions:
        - dump_intermediate(data: dict, path: Path) -> None
        - load_intermediate(path: Path) -> dict

        Custom encoder (json.JSONEncoder subclass or standalone _encode/_decode):

        Type encoding rules (each tagged with a "__type__" key for round-trip):
        - Path: {"__type__": "Path", "value": str(path)}
        - datetime: {"__type__": "datetime", "value": dt.isoformat()}
        - tuple: {"__type__": "tuple", "value": list(items)}
          (tuples are significant: Series fields like image_type, image_type_text,
          scanning_sequence, slice_timing, matrix, affine, image_position,
          voxel_sizes are typed as tuples, and frozenness matters for the
          frozen dataclass)
        - frozenset: {"__type__": "frozenset", "value": sorted(list(items))}
        - Role (StrEnum): {"__type__": "Role", "value": role.value}
          (Role.BOLD -> "bold", etc.)

        Dataclass encoding (recursive, via dataclasses.asdict is NOT usable
        because it recursively converts nested dataclasses to dicts without
        type tags; use explicit field iteration instead):
        - Series: {"__type__": "Series", "fields": {field.name: encode(getattr(obj, field.name)) for field in dataclasses.fields(obj)}}
        - FieldmapPair: same pattern
        - Mapping: {"__type__": "Mapping", "fields": {"pairs": [...], "pair_to_targets": {...}, "bids_relative_paths": {...}}}
          Note: pair_to_targets has int keys -> convert to str keys on dump,
          restore to int on load. Same for bids_relative_paths.
        - RegistryDelta: {"__type__": "RegistryDelta", "fields": {"new_entries": {desc: encode(entry)}, "warnings": [...]}}
        - TaskRegistryEntry: {"__type__": "TaskRegistryEntry", "fields": {"label": str, "expected_volumes": int|null, "first_seen": str, "signature": tuple|null}}
        - Excluded: {"__type__": "Excluded", "fields": {"series": encode(series), "task_label": str, "observed_volumes": int, "expected_volumes": int}}
        - ReviewFlag: {"__type__": "ReviewFlag", "fields": {"message": str(flag), "context": flag.context}}
        - PhysioLog: {"__type__": "PhysioLog", "fields": {"channels": {name: encode(channel)}, "acq_info": encode(info)|null, "series_number": int, "acquisition_datetime": str|null}}
        - PhysioChannel: {"__type__": "PhysioChannel", "fields": {"name": str, "sample_time": int, "data": list[int]}}
        - AcquisitionInfo: {"__type__": "AcquisitionInfo", "fields": {"num_volumes": int, "num_slices": int, "num_echoes": int, "first_time": int, "last_time": int, "volume_table": list[dict]}}

        Int dict keys (roles, labels_dict, run_indices, series_map,
        physio_pairs, pair_to_targets, bids_relative_paths):
        - On dump: convert int keys to str via {"__int_keys__": true, "items": {str(k): encode(v)}}
        - On load: restore str keys to int

        Top-level intermediate dict keys and their types (for reference,
        verified from __main__.py lines 220-234):
          roles: dict[int, Role]
          labels_dict: dict[int, str]
          run_indices: dict[int, int]
          mapping: Mapping
          excluded: list[Excluded]
          review_flags: list[ReviewFlag]
          physio_pairs: dict[int, PhysioLog]
          registry_delta: RegistryDelta
          vol_updates: dict[str, TaskRegistryEntry]
          guard_log: dict[str, bool]
          version_str: str
          series_map: dict[int, Series]
          unclassified: list[Series]

        Imports needed:
          import dataclasses, json, datetime, pathlib
          from .sidecar import Series
          from .stage2_classify import Role
          from .stage3_map import Mapping, FieldmapPair
          from .runs import Excluded
          from .labels import RegistryDelta
          from .config import TaskRegistryEntry
          from .errors import ReviewFlag
          from .physio import PhysioLog, PhysioChannel, AcquisitionInfo

        **Modifications to bids_recon/__main__.py:**

        1. Line 15: replace `import pickle` with
           `from .json_intermediate import dump_intermediate, load_intermediate`

        2. Lines 235-237: replace
           ```
           pkl_path = staging.staging_dir / f'{sub}_{ses}_intermediate.pkl'
           with open(pkl_path, 'wb') as fh:
               pickle.dump(intermediate, fh, protocol=pickle.HIGHEST_PROTOCOL)
           ```
           with
           ```
           json_path = staging.staging_dir / f'{sub}_{ses}_intermediate.json'
           dump_intermediate(intermediate, json_path)
           ```

        3. Lines 247-252: replace
           ```
           pkl_path = staging_dir / f'{sub}_{ses}_intermediate.pkl'
           if not pkl_path.exists():
               continue

           with open(pkl_path, 'rb') as fh:
               intermediate = pickle.load(fh)
           ```
           with
           ```
           json_path = staging_dir / f'{sub}_{ses}_intermediate.json'
           if not json_path.exists():
               continue

           intermediate = load_intermediate(json_path)
           ```
      </spec>
      <dependencies>none (independent of C1-C4; touches __main__.py which
        C1-C4 do not touch, and creates a new file)</dependencies>
      <risk>medium - custom serialization/deserialization for 10+ types with
        nested dataclasses. Round-trip correctness is critical. Existing tests
        that exercise full pipeline flow will validate end-to-end. Dedicated
        round-trip tests recommended via /test.</risk>
      <rollback>Delete json_intermediate.py; restore pickle import and
        dump/load calls in __main__.py</rollback>
    </change>

    <change id="C6" priority="P0" source_item="brainstorm C5">
      <file path="tools/simulated_bids/config.py" action="modify" />
      <file path="tools/simulated_bids/modalities.py" action="modify" />
      <file path="tools/simulated_bids/scaffold.py" action="modify" />
      <description>
        Add 14 patient-level fields to the BIDS generator so simulated
        sidecars match what dcm2niix outputs from real Siemens XA30 DICOMs.
        Update _base_sidecar() to accept and merge patient_fields.
        Update scaffold.py to write acq_time from the new per-session
        AcquisitionDateTime values instead of "n/a".
      </description>
      <spec>
        **tools/simulated_bids/config.py:**

        1. Add a new function `compute_patient_fields(demographics_entry, ses_index,
           series_num, rng)` that returns a dict with all 14 fields:

           Per-subject (derived from demographics_entry):
           - "PatientID": demographics_entry["participant_id"].replace("sub-", "SIM")
             (e.g., "sub-001" -> "SIM001")
           - "PatientName": f"SIMULATED^SUBJECT{demographics_entry['participant_id'][-3:]}"
           - "PatientSex": demographics_entry["sex"]
           - "PatientBirthDate": computed as YYYYMMDD string. Use a fixed
             reference study date of "2026-01-15" for ses-01, offset by
             SESSION_INTERVAL_YEARS per session. Subtract age_at_session years
             from the study date to get birth date. Format as YYYYMMDD (no dashes).
           - "PatientAge": formatted as f"{int(round(age_at_session(base_age, ses_index)))}Y"
             (e.g., "009Y", "011Y", "013Y")
           - "PatientSize": simulated height in meters. Use a simple age-based
             linear model: 1.10 + 0.05 * age (clamped to [1.10, 1.85]).
             Round to 2 decimal places.
           - "PatientWeight": simulated weight in kg. Use: 25.0 + 2.5 * (age - 9.0).
             Clamped to [20.0, 90.0]. Round to 1 decimal place.

           Per-session:
           - "AcquisitionDateTime": ISO datetime string. Base: "2026-01-15T10:30:00.000000"
             for ses-01. Add SESSION_INTERVAL_YEARS per session index. Vary the
             time-of-day slightly using series_num to distinguish series within
             a session: add series_num * 300 seconds (5 minutes per series).

           Per-series (deterministic from subject/session/series_num):
           - "SeriesInstanceUID": f"1.2.826.0.1.3680043.8.498.SIM.{sub_num}.{ses_index+1}.{series_num}"
             where sub_num is the numeric part of participant_id.
           - "StudyInstanceUID": f"1.2.826.0.1.3680043.8.498.SIM.{sub_num}.{ses_index+1}"

           Per-study (constant or semi-constant):
           - "StudyID": "SIM_STUDY_001"
           - "AccessionNumber": f"SIM_ACC_{sub_num}_{ses_index+1}"
           - "ReferringPhysicianName": "SIMULATED^PHYSICIAN"
           - "PerformedProcedureStepDescription": will be set per-series from
             the modality's SeriesDescription or ProtocolName in the caller.
             Return a placeholder that the caller overrides after _base_sidecar
             merges. Or: accept a series_description parameter and set it here.
             Decision: accept series_description as a parameter, set
             "PerformedProcedureStepDescription": series_description.

           Function signature:
           ```python
           def compute_patient_fields(
               demo: dict,
               ses_index: int,
               series_num: int,
               series_description: str,
           ) -> dict:
           ```

           No RNG parameter needed: all fields are deterministic from the inputs.

        **tools/simulated_bids/modalities.py:**

        2. Update _base_sidecar signature:
           ```python
           def _base_sidecar(params: dict, series_num: int = 1,
                             patient_fields: dict | None = None) -> dict:
           ```
           After the existing SCANNER + params merge, add:
           ```python
           if patient_fields is not None:
               sc.update(patient_fields)
           ```

        3. Update all generator functions to accept and pass patient_fields:
           - generate_t1w: add patient_fields parameter, pass to _base_sidecar
           - generate_t2w: same
           - generate_bold: same (note: sc already gets TaskName added after
             _base_sidecar; patient_fields merge happens in _base_sidecar before
             TaskName addition, so no conflict)
           - generate_dwi: same (main DWI + 3 SBRef files; each SBRef call to
             _base_sidecar must also pass patient_fields)
           - generate_fmap_pair: same (both PA and AP members)

           Each generator's signature gains `patient_fields: dict | None = None`
           as the last parameter before rng.

        **tools/simulated_bids/scaffold.py:**

        4. Update write_scans_tsv to accept an optional acq_times dict:
           ```python
           def write_scans_tsv(out_dir: Path, sub: str, ses: str,
                               nifti_paths: list[Path],
                               acq_times: dict[str, str] | None = None) -> None:
           ```
           Line 83: replace `lines.append(f"{rel}\tn/a")` with:
           ```python
           acq = acq_times.get(str(rel), "n/a") if acq_times else "n/a"
           lines.append(f"{rel}\t{acq}")
           ```

        **tools/simulated_bids/__main__.py (generator orchestrator):**

        5. Update generate_clean_session() signature to accept demo and ses_index:
           ```python
           def generate_clean_session(out_dir: Path, sub: str, ses: str,
                                      demo: dict, ses_index: int,
                                      rng: np.random.Generator) -> tuple[list[Path], dict[str, str]]:
           ```
           Returns (nifti_paths, acq_times) where acq_times maps
           relative NIfTI path -> AcquisitionDateTime string.

        6. Inside generate_clean_session, use a series_counter starting at 1.
           Before each modality generator call, compute:
           ```python
           pf = compute_patient_fields(demo, ses_index, series_counter,
                                       series_description)
           ```
           Pass patient_fields=pf to each generator. Increment series_counter
           after each call (for multi-file generators like generate_bold which
           produce BOLD + SBRef, increment by 2; for generate_dwi which
           produces DWI + 3 SBRef, increment by 4; for generate_fmap_pair
           which produces 2 files, increment by 2).

           Collect acq_times from each pf["AcquisitionDateTime"] keyed by
           the relative path of the NIfTI file (relative to ses_dir).

        7. Update the main() loop (lines 107-115):
           - Pass demo and ses_index (enumerate SESSIONS) to
             generate_clean_session.
           - Pass the returned acq_times to write_scans_tsv.
           ```python
           for sub in roster:
               demo = demo_by_id[sub]
               sub_rng = np.random.default_rng(rng.integers(0, 2**31))
               for ses_index, ses in enumerate(SESSIONS):
                   print(f"  {sub}/{ses}...", end=" ", flush=True)
                   paths, acq_times = generate_clean_session(
                       out, sub, ses, demo, ses_index, sub_rng)
                   write_scans_tsv(out, sub, ses, paths, acq_times=acq_times)
                   print(f"{len(paths)} files")
               write_sessions_tsv(out, sub, demo["age_ses01"])
           ```

        8. Add import: `from .config import compute_patient_fields`
      </spec>
      <dependencies>none (generator is independent of pipeline code)</dependencies>
      <risk>medium - 14 new fields across 7+ generator functions; must ensure
        correct per-subject/session/series differentiation. Round-trip
        verification against pipeline consumption validates correctness.</risk>
      <rollback>Revert config.py, modalities.py, scaffold.py to pre-change state</rollback>
    </change>

    <change id="C7" priority="P0" source_item="brainstorm C6">
      <description>
        Regenerate both simulated datasets at ~/simulated-bids/ using the
        updated generator.
      </description>
      <spec>
        1. Delete existing ~/simulated-bids/adversarial/ directory
           (requires explicit user permission at execution time).
        2. Delete existing ~/simulated-bids/clean/ directory
           (requires explicit user permission at execution time).
        3. Run the generator for the adversarial profile:
           `conda run -n bids-recon python -m tools.simulated_bids adversarial`
           (or equivalent invocation; verify the generator's CLI entry point).
        4. Run the generator for the clean profile:
           `conda run -n bids-recon python -m tools.simulated_bids clean`
        5. Verify: spot-check 3 output sidecars (one per modality category:
           anat, func, dwi) to confirm all 14 patient-level fields are present.
      </spec>
      <dependencies>C6 (generator must be updated before regeneration)</dependencies>
      <risk>low - deterministic seeded generation; deletion requires user permission</risk>
      <rollback>Re-run generator with pre-C6 code (restore from backup)</rollback>
    </change>

  </changes>

  <execution_order>
    Phase 1 (parallel, pipeline scrub removal): C1, C2
    Phase 2 (parallel, pipeline correctness): C3, C4
    Phase 3 (pickle replacement): C5
    Phase 4 (generator update): C6
    Phase 5 (dataset regeneration): C7

    C1 and C2 touch different files (stage4_assemble.py and report.py) and
    can execute in parallel. C3 and C4 touch the same file as C1
    (stage4_assemble.py) but non-overlapping lines, so they can execute in
    parallel with each other but must follow C1 (C1 deletes lines 26-65,
    shifting all subsequent line numbers). C5 touches __main__.py and creates
    json_intermediate.py, independent of C1-C4. C6 touches only tools/
    files. C7 depends on C6.

    Revised execution order accounting for line-shift dependencies:
    Group 1: C1 + C2 (parallel)
    Group 2: C3 + C4 (parallel, after C1 completes since same file)
    Group 3: C5 (independent, can run in parallel with Group 1 or 2)
    Group 4: C6 (after Groups 1-3 complete, since generator should reflect
              the final pipeline state for validation alignment)
    Group 5: C7 (after C6)
  </execution_order>

  <notes>
    Test impact: C1/C2 will break tests that import SIDECAR_DENY_LIST or scrub
    (tests/test_assemble.py lines 22, 41-76, 153-180) and tests that assert
    scrub audit behavior (tests/test_report.py). These test updates are out of
    scope for this implement pass per user direction. Recommend /test after build
    to design and apply test updates.

    C5 (pickle-to-JSON) should have dedicated round-trip tests added via /test
    to verify serialization/deserialization fidelity for all types in the
    intermediate dict.

    C8 (POSIX documentation for fcntl) is routed to /document per brainstorm
    decision and is not included in this implement plan.
  </notes>

</implement_plan>
