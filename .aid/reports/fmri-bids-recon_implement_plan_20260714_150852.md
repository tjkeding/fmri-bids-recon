<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-14T19:08:52Z" />

  <assumptions>
    Per standing directive, this plan opens with every decision taken WITHOUT explicit user approval, plus every
    decision taken WITH approval during this planning session that is not recorded in the input report. Nothing below
    is a gate: all are resolved directives. They are listed so the resolution is reviewable rather than buried.

    A. RESOLVED DURING THIS PLANNING SESSION (explicit user approval; supersedes or extends the input report)

    A1. PHI BOUNDARY. The project's PHI rule scopes to the collaboration surface, not to pipeline outputs. The pipeline
        runs on a secure PHI-cleared server to which the assistant has no access. The engine may therefore READ
        PatientBirthDate, PatientID, PatientSex and study date, and may WRITE derived covariates into the BIDS
        demographics TSVs. Two constraints survive without exception: (i) no PHI VALUE may appear in any report, plan,
        commit message, engine log message template, or source comment authored during this collaboration (field names
        only); (ii) the sidecar scrub is still applied, on propagation and consolidation grounds (below), not as a
        privacy concession.

    A2. SIDECAR SCRUB MECHANISM. This SUPERSEDES the input report's T10 directive of "dcm2niix -ba y PLUS an explicit
        residual-key scrub". Empirical verification against dcm2niix v1.0.20260416 established that `-ba y` (which is
        the DEFAULT) suppresses exactly these sidecar keys:
            AcquisitionDateTime, PatientAge, PatientBirthDate, PatientID, PatientName, PatientSex, PatientSize,
            PatientWeight, SeriesInstanceUID, StudyID, StudyInstanceUID
        That set includes the very keys the engine now requires (A3, A4). `-ba y` is therefore NOT USABLE. The engine
        MUST convert with `-ba n` into a private staging area, harvest what it needs there, and apply its OWN
        deny-list at BIDS-tree assembly time. Net sidecar content in the BIDS tree equals what `-ba y` would have
        produced, but the engine obtains its inputs first and the scrub is explicit and auditable rather than
        delegated to a flag. This also satisfies T10's "do not trust the flag alone."
        RATIONALE for scrubbing at all, given the secure server: sidecar contents are copied verbatim by downstream
        tools (fMRIPrep, MRIQC) into derivatives and HTML reports, and MRIQC's IQM records are built for export, so
        identifiers left in the sidecars propagate into every downstream artifact; and promoting the analytically
        useful identifiers to participants.tsv / sessions.tsv confines the redaction surface to two auditable files
        instead of several hundred.
        NOTE, correcting an earlier misstatement made during planning: AcquisitionTime (time-of-day) SURVIVES `-ba y`.
        Only AcquisitionDateTime (full date) is suppressed. Within-session temporal ordering was therefore never at
        risk from the flag.

    A3. sessions.tsv PROVENANCE. acq_time is DERIVED from AcquisitionDateTime. age is DERIVED as exact decimal years
        from PatientBirthDate and the study date, falling back to PatientAge only when PatientBirthDate is absent.
        wave (the human-readable timepoint name) is SUPPLIED by the study config, not derived.

    A4. PatientID CROSS-CHECK. Implemented as WARN-ONLY and non-fatal. The engine builds a PatientID <-> subject-label
        map across the run and warns when one PatientID maps to multiple sub- labels, or one sub- label carries
        multiple PatientIDs. PatientID is never a naming source and never reaches the BIDS tree. This closes the item
        the input report explicitly left open ("surfaced to the user, not assumed", T6).

    A5. LEGACY SCRIPTS. bids-heuristic-bw.py and fmri-bids-recon.sh REMAIN IN PLACE, unmodified and unreferenced. The new
        engine does not import, call, or extend them. No file is moved or deleted by this plan.

    A6. UNCLASSIFIED-SERIES FALLTHROUGH. The input report's T3 rule table specifies no behaviour for a series matching
        no rule. Resolved: an unmatched series is converted, written to sourcedata/unclassified/, recorded in the
        conversion report, and the session COMPLETES. Rationale: preserves the T7 principle that unattended HPC
        batches are not blocked and that nothing acquired is destroyed. The accepted risk is explicit: a genuinely new
        BOLD variant unrecognised by the rule table would be omitted from func/ rather than halting the run, so the
        conversion report must be read after each batch.

    B. ASSUMPTIONS TAKEN WITHOUT EXPLICIT APPROVAL (each justified by a lock already in the input report)

    B1. NAVIGATOR RULE, PARAMETER-FREE. The input report writes the navigator rule as "navigator geometry (32x32),
        high frame count". Both are free parameters and 32x32 is a constant lifted from the example session. This
        collides with two higher-priority locks in the same report: T2/T6's "engine contains NO study-specific
        vocabulary / no study-specific assumptions anywhere", and T7's explicit doctrine that a rule with no free
        parameter is the defensible one. RESOLVED BY PRECEDENCE: the rule is implemented as "a 4D series (dim4 > 1)
        whose ImageType modality token is neither FMRI nor DIFFUSION has no BIDS role". This selects exactly the same
        series in the example session and introduces no constants. Such series are preserved to sourcedata/, not
        deleted.

    B2. T1w VERSUS T2w IS RESOLVED BY PHYSICS, CROSS-CHECKED BY NAME. The input report's T3 rule table collapses both
        anatomicals into a single `anat` row and never states how the BIDS suffix is chosen; their ImageType values
        are byte-identical (recorded in the report's own empirical findings). The report's dominant and repeatedly
        locked pattern is "derive from physics, cross-check against the name token, hard-error on disagreement" (used
        for dir- in T3/T4). That pattern is applied here: InversionTime present AND ScanningSequence containing GR ->
        T1w; ScanningSequence containing SE AND InversionTime absent -> T2w; neither -> unclassified (A6). If the
        series name carries a BIDS anatomical suffix token that disagrees with the physics verdict, HARD ERROR. The
        rule is presence/absence based and carries no thresholds.

    B3. TEMPORAL ORDERING KEY. The engine orders series by AcquisitionDateTime (available because of A2), not by
        AcquisitionTime, which eliminates the midnight-crossing failure mode in which a session spanning 00:00 would
        sort catastrophically wrong. Monotonic agreement between the AcquisitionDateTime ordering and the SeriesNumber
        ordering is asserted; disagreement is a HARD ERROR. Justified by the report's own guard pattern: an
        independent witness confirming a derived ordering, failing loudly rather than guessing.

    B4. VOLUME COUNT AND dim4 ARE READ FROM THE NIfTI, NOT THE SIDECAR. dcm2niix does not reliably emit a 4D length in
        the sidecar. nibabel is used to read the converted image header (shape[3], or 1 when ndim == 3). This is a
        mechanical sourcing decision required by T3 (bold vs sbref) and T7 (exact volume-count match).

    B5. PHYSIO SERIES ARE DISCOVERED FROM THE DICOMs, NOT THE SIDECARS. The input report records that dcm2niix
        silently SKIPS the PhysioLog series, so they produce no sidecar and are invisible to a sidecar-driven
        classifier. Stage 1 therefore additionally builds a pydicom-based index of the source DICOMs (SeriesNumber,
        SOPClassUID, AcquisitionDateTime, file paths) so Raw Data Storage series remain discoverable for T11.

    B6. PACKAGE NAME AND LAYOUT. The engine is a new Python package `fmri_bids_recon/` at the project root, with a
        `python -m bids_recon` CLI. Greenfield: no existing package, module, or import contract constrains the choice.
  </assumptions>

  <input_reports>
    <report path="fmri-bids-recon_brainstorm_20260714_142126.md" mode="brainstorm" key_items="7" />
  </input_reports>

  <environment>
    Verified at plan time on the development machine. The build must not assume these hold on the cluster; T9's runtime
    version assertion (C15) is what enforces them where it matters.
      conda env `fmri-bids-recon`: python 3.12.13, pydicom 3.0.2, nibabel 5.4.2, numpy 2.5.1
      dcm2niix v1.0.20260416 at $CONDA_PREFIX/bin/dcm2niix  (EXACTLY the T9 version floor)
      bids-validator on PATH
    BUILD PREREQUISITE, NOT YET INSTALLED: PyYAML (required by C2, the study config loader). Per the Environment
    Pre-Flight contract the orchestrator installs this only on explicit per-invocation user approval, before any
    execution agent is dispatched. It is not a design decision and not a plan gate.
    NOT PRESENT AND NOT NEEDED LOCALLY: CuBIDS and Apptainer are cluster-side concerns (C16, C17); the local build
    does not exercise them.
  </environment>

  <changes>

    <change id="C1" priority="P0" source_item="T2 (engine skeleton)">
      <file path="fmri_bids_recon/__init__.py" action="create" />
      <file path="fmri_bids_recon/errors.py" action="create" />
      <description>
        Package root and the exception hierarchy. The exception hierarchy is created FIRST and as its own change
        because it is the load-bearing element of the entire refactor: the input report's central finding (T1, T8) is
        that the legacy pipeline failed silently, and that every guard must therefore be a hard failure rather than a
        warning. Every guard in C4-C11 raises a member of this hierarchy. A guard that cannot raise is a guard that
        does not exist.
      </description>
      <spec>
        errors.py defines:
          class BidsReconError(Exception)                 # base; carries .context: dict for structured logging
          class GuardError(BidsReconError)                # base for all BLOCKING assertion failures
            class VersionFloorError(GuardError)           # dcm2niix below the verified floor            (T9)
            class OrderingError(GuardError)               # AcquisitionDateTime / SeriesNumber disagree  (B3)
            class AnatSuffixError(GuardError)             # physics verdict disagrees with name token    (B2)
            class PhaseEncodingError(GuardError)          # pair members not opposite; dir- disagrees
                                                          #   with the _PA/_AP name token                (T3, T4)
            class FieldmapGeometryError(GuardError)       # pair EES/geometry != target's               (T4)
            class FieldmapCoverageError(GuardError)       # orphan pair, or a run preceding all pairs   (T4)
            class LabelCollisionError(GuardError)         # two distinct descriptions -> one label       (T6)
            class EmptyLabelError(GuardError)             # a label strips to nothing                    (T6)
            class LabelDriftError(GuardError)             # a known description re-derives differently   (T6)
            class TaskRenameError(GuardError)             # old absent + new present, matching signature (T6)
            class PhysioAssociationError(GuardError)      # physio geometry != its candidate run's       (T11)
            class ValidationError(GuardError)             # bids-validator returned non-zero             (T8)
          class ReviewFlag(BidsReconError)                # NON-blocking; collected, never raised

        Each GuardError subclass docstring names the report topic it enforces. GuardError.__init__ requires a
        `context` dict; the message template must never interpolate a PHI value (only field names, series numbers,
        counts, and derived labels).

        __init__.py exports __version__ = "0.1.0" and the public entry points; it contains no logic.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - pure declarations, no behaviour.</risk>
      <rollback>Delete fmri_bids_recon/.</rollback>
    </change>

    <change id="C2" priority="P0" source_item="T6 (per-study config), T5 (wave), A3">
      <file path="fmri_bids_recon/config.py" action="create" />
      <file path="config/study.example.yaml" action="create" />
      <description>
        The declarative per-study config: the ONLY per-study artifact in the system. Engine code is never edited per
        project (T2, T6). The config also carries the auto-maintained task registry, which is read at start of run and
        written back at end of run.
      </description>
      <spec>
        Schema (PyYAML load, validated by hand against a dataclass; no jsonschema dependency):

          study_name: str                       # user-supplied. NOT StudyDescription.
          bids_root: path
          sourcedata_root: path                 # default: {bids_root}/sourcedata
          staging_root: path                    # private per-task staging; NEVER inside bids_root
          participants:
            - source: path                      # DICOM directory for one (subject, session)
              sub: str                          # user-supplied label. NOT PatientID.
              ses: str                          # zero-padded ordinal, e.g. "01"                       (T5)
              wave: str                         # human-readable timepoint name -> sessions.tsv        (A3)
          task_registry:                        # AUTO-DERIVED and AUTO-MAINTAINED. Hand-edited only to
                                                #   resolve a TaskRenameError.
            "<SeriesDescription>":
              label: str                        # frozen task label; never re-derived once written    (T6)
              expected_volumes: int | null      # null until first complete observation                (T7)
              first_seen: str                   # ISO date, for audit

        Dataclasses: StudyConfig, ParticipantEntry, TaskRegistryEntry.

        Functions:
          load_config(path) -> StudyConfig
              Validates: sub/ses are BIDS-legal alphanumerics; ses matches ^[0-9]{2,}$ (T5 zero-padding);
              every `source` exists; staging_root is NOT a subpath of bids_root (prevents the legacy
              per-subject-BIDS-root hazard of T1/T9); sub+ses pairs are unique.
          save_registry(config, path) -> None
              Atomic rewrite (write to tempfile in the same directory, os.replace). Preserves comments is NOT
              required; the registry is machine-owned.

        config/study.example.yaml is a fully-commented template using placeholder values only. It contains NO value
        drawn from the example session: no protocol prefix, no task name, no site, no participant label.
      </spec>
      <dependencies>C1</dependencies>
      <risk>medium - the staging_root-not-inside-bids_root assertion is the structural fix for the legacy concurrency
        hazard (T1, T9). If it is omitted the whole isolate-then-merge design silently degrades back to the legacy
        failure mode.</risk>
      <rollback>Delete config.py and config/study.example.yaml.</rollback>
    </change>

    <change id="C3" priority="P0" source_item="T9 (version pinning is a scientific dependency)">
      <file path="fmri_bids_recon/versions.py" action="create" />
      <description>
        Runtime assertion of the dcm2niix version floor. The report is explicit that this is a SCIENTIFIC dependency,
        not an environment detail: the entire fieldmap design rests on dcm2niix recovering signed
        PhaseEncodingDirection from XA enhanced DICOM with no CSA headers, a capability verified on v1.0.20260416 and
        known to have evolved across releases. An older binary emits no PhaseEncodingDirection and every fieldmap
        association the engine builds would be unfounded.
      </description>
      <spec>
        DCM2NIIX_VERSION_FLOOR = "1.0.20260416"     # verified; see input report T9

        parse_dcm2niix_version(text: str) -> tuple[int, int, int]
            Extracts the vX.Y.ZZZZZZZZ token from `dcm2niix --version` output. The third component is a date-like
            integer and is compared numerically, not lexically.
        assert_dcm2niix_version(binary: str = "dcm2niix") -> str
            Runs `{binary} --version`, parses, and raises VersionFloorError if BELOW the floor. Returns the version
            string for the provenance record. Called unconditionally at the top of every run (C13), regardless of how
            the environment was provisioned.
      </spec>
      <dependencies>C1</dependencies>
      <risk>low - but it is the guard that makes every other guard trustworthy, so it must run before any conversion.</risk>
      <rollback>Delete versions.py; remove the call site in C13.</rollback>
    </change>

    <change id="C4" priority="P0" source_item="T2 stage 1, A2, B5">
      <file path="fmri_bids_recon/stage1_convert.py" action="create" />
      <description>
        Stage 1. Converts one (subject, session) DICOM directory into a PRIVATE staging directory with `-ba n`, and
        builds a pydicom index of the source DICOMs so that the physio series (which dcm2niix silently skips) remain
        discoverable. Staging is per-array-task and shares no state, which is the architectural fix for the legacy
        concurrency hazard (T1, T9).
      </description>
      <spec>
        convert_to_staging(source: Path, staging: Path, dcm2niix: str) -> StagingResult

          Invokes, with no series filter:
              dcm2niix -ba n -b y -z y -f "%s_%d" -o {staging} {source}
          `-ba n` is REQUIRED (A2): the default `-ba y` suppresses AcquisitionDateTime, PatientBirthDate, PatientSex
          and PatientID, which are exactly the keys stages 3, 4 and the cross-check consume. The staging directory is
          PRIVATE and lives on the secure server; it is never merged into the BIDS tree as-is.

          `-f "%s_%d"` prefixes every output with the zero-padded SeriesNumber, which is what joins a sidecar back to
          its DICOM series and to the pydicom index.

        index_source_dicoms(source: Path) -> dict[int, DicomSeriesRecord]
          One pydicom read per SERIES (first file only; stop_before_pixels=True) plus a file listing. Records:
          SeriesNumber, SOPClassUID, Modality, SeriesDescription, AcquisitionDateTime, and the file list. This index
          is the ONLY channel through which the physio series (Raw Data Storage, SOPClassUID
          1.2.840.10008.5.1.4.1.1.66) reach the engine, because they produce no sidecar (B5).

        StagingResult carries: staging dir, the list of emitted sidecar paths, the DICOM index, the dcm2niix version
        string, and captured stderr (the report notes dcm2niix emits an Issue870 warning on the diffusion series;
        it is CAPTURED to the provenance record, never parsed for control flow).

        No scrub happens here. Staging sidecars are deliberately FULL. The scrub is applied at assembly (C10).
      </spec>
      <dependencies>C1, C2, C3</dependencies>
      <risk>medium - `-ba n` deliberately writes identifiers into staging. This is correct and safe under A1 (the
        staging area is on the PHI-cleared server), but the code must never copy a staging sidecar into the BIDS tree
        without passing it through the C10 deny-list. That invariant is enforced by making C10 the single writer of
        BIDS-tree sidecars.</risk>
      <rollback>Delete stage1_convert.py.</rollback>
    </change>

    <change id="C5" priority="P0" source_item="T3 (rule table), B1, B2, B4, A6">
      <file path="fmri_bids_recon/sidecar.py" action="create" />
      <file path="fmri_bids_recon/stage2_classify.py" action="create" />
      <description>
        Stage 2. The physics-driven rule table. This change replaces the legacy heuristic's substring matching
        outright: SUBSTRING MATCHING ON SeriesDescription IS BANNED FROM THE CLASSIFIER (T3). Every discriminator is
        an acquisition property. The series name is used only as a CROSS-CHECK that fails loudly on disagreement,
        never as a source of truth.
      </description>
      <spec>
        sidecar.py:
          @dataclass(frozen=True) Series
              series_number: int
              description: str                  # retained for cross-checks and label derivation ONLY
              image_type: tuple[str, ...]       # DICOM standard: ORIGINAL/DERIVED, ..., FMRI/DIFFUSION/M/OTHER
              image_type_text: tuple[str, ...]  # Siemens: ND / NORM / MB / DIS2D
              acquisition_datetime: datetime    # ordering key (B3)
              repetition_time, echo_time, inversion_time: float | None
              scanning_sequence: tuple[str, ...]
              mr_acquisition_type: str | None   # "2D" | "3D"
              phase_encoding_direction: str | None   # signed: "j" | "j-" | ...
              effective_echo_spacing: float | None
              total_readout_time: float | None
              multiband_factor: int | None
              slice_timing: tuple[float, ...] | None
              matrix: tuple[int, int, int]      # from the NIfTI header
              n_volumes: int                    # NIfTI shape[3], else 1                            (B4)
              nifti_path, sidecar_path: Path
              raw: dict                         # the full staging sidecar, incl. identifiers. NEVER
                                                #   written to the BIDS tree except through C10.

          load_series(staging: Path) -> list[Series]
              Reads each sidecar; opens the matching NIfTI with nibabel for matrix and n_volumes (B4).
              modality_token(s) -> str  helper: image_type[2] if present else "OTHER".

        stage2_classify.py:
          class Role(StrEnum):
              BOLD, SBREF, FMAP_FUNC, FMAP_DWI, DWI, T1W, T2W,
              DROP_DERIVED, DROP_SCOUT, DROP_NAVIGATOR, UNCLASSIFIED

          classify(series: list[Series]) -> dict[int, Role]

          RULE TABLE, evaluated in this order (first match wins; every rule is an acquisition property):

            1. DROP_DERIVED     image_type[0] == "DERIVED"
            2. DROP_SCOUT       "DIS2D" in image_type_text and mr_acquisition_type == "2D"
                                and multiband_factor is None
            3. DROP_NAVIGATOR   n_volumes > 1 and modality_token not in {"FMRI", "DIFFUSION"}      (B1)
                                # parameter-free replacement for the report's "(32x32), high frame count";
                                # a 4D non-functional, non-diffusion series has no BIDS role.
            4. T1W / T2W        mr_acquisition_type == "3D" and modality_token == "M"
                                and "EP" not in scanning_sequence
                                Suffix by PHYSICS (B2):
                                  inversion_time is not None and "GR" in scanning_sequence  -> T1W
                                  "SE" in scanning_sequence and inversion_time is None      -> T2W
                                  otherwise                                                 -> UNCLASSIFIED
                                CROSS-CHECK: if the description carries a BIDS anatomical suffix token
                                (case-insensitive "t1w" / "t2w") that DISAGREES with the physics verdict,
                                raise AnatSuffixError.
            5. FMAP_FUNC        modality_token == "FMRI" and spin-echo ("SE" in scanning_sequence,
                                "GR" not in scanning_sequence) and n_volumes == 1
            6. FMAP_DWI         modality_token == "DIFFUSION" and spin-echo and has NO b-vector file
            7. DWI              modality_token == "DIFFUSION" and image_type[0] == "ORIGINAL"
                                and a .bval/.bvec pair exists
            8. BOLD             modality_token == "FMRI" and n_volumes > 1
            9. SBREF            modality_token == "FMRI" and n_volumes == 1 and the NEXT series in
                                AcquisitionDateTime order with the same description-stem is a BOLD
           10. UNCLASSIFIED     no rule matched                                                     (A6)

          Rules 5 and 9 both admit a single-volume FMRI series; rule 5 is reached first and is distinguished by the
          spin-echo test (an SBRef is a gradient-echo image acquired with the BOLD readout; a PEPOLAR fieldmap is a
          spin-echo EPI). This ordering is deliberate and must not be permuted.

          UNCLASSIFIED is NOT an error (A6): it is preserved to sourcedata/unclassified/ by C10 and reported by C14.

          ANATOMICAL VARIANT SELECTION (T3, the hard downstream constraint): among series classified T1W (resp. T2W),
          the one whose image_type_text contains "NORM" goes to anat/; its ND twin goes to sourcedata/. This is a
          PHYSICAL SEPARATION, not a .bidsignore entry and not a rec- entity: the downstream consumer reaches the file
          with a raw glob on anat/*_T1w.nii.gz that ignores .bidsignore, and both _rec-norm_ and _rec-nonorm_ would
          match that glob. An in-tree ND twin, however labelled, would trigger the downstream fail-closed exit.
          If no NORM variant exists, the sole reconstruction is used and a ReviewFlag is recorded.
      </spec>
      <dependencies>C1, C4</dependencies>
      <risk>high - this is the module whose legacy equivalent caused every misclassification in T1. The rule ORDER is
        load-bearing (rules 5/9). The anatomical NORM/ND separation is the one place where a wrong choice silently
        breaks the downstream pipeline rather than erroring.</risk>
      <rollback>Delete sidecar.py and stage2_classify.py. Nothing else imports Role until C6.</rollback>
    </change>

    <change id="C6" priority="P0" source_item="T6 (derived-prefix + BIDS stop-list, registry growth policy)">
      <file path="fmri_bids_recon/labels.py" action="create" />
      <description>
        Task-label derivation and the registry growth policy. The engine contains NO study vocabulary: the protocol
        prefix is DERIVED at runtime, never listed, and the stop-list contains only words defined by the BIDS spec or
        by MRI physics.
      </description>
      <spec>
        derive_prefix(descriptions: Iterable[str]) -> tuple[str, ...]
            The longest common LEADING TOKEN SEQUENCE across the descriptions of the series RETAINED AFTER
            CLASSIFICATION (which excludes the scout, the navigators and the derived maps: this is why classification
            must precede labelling, since the scout carries no protocol prefix and would collapse the prefix to
            nothing). Tokens are split on [_\-\s]. Returns () when there is no common prefix.
            The zero-entropy argument: a token present in EVERY retained series carries no discriminative information
            and therefore cannot belong to a label whose purpose is to discriminate.

        BIDS_STOP_WORDS: frozenset  -- every entry is defined OUTSIDE any particular study:
            entity keywords:      task run dir acq rec echo part chunk ses sub
            suffix / modality:    fmri bold epi sbref dwi dmri t1w t2w mprage spc tse flair
            directions:           ap pa lr rl is si
            vendor recon tokens:  nd norm mb dis2d setter vnav distortionmap physiolog

        derive_task_label(description, prefix) -> str
            strip the derived prefix -> drop BIDS_STOP_WORDS -> sanitise to [a-z0-9] -> join.
            Raise EmptyLabelError if the result is empty. Never fall back to a guess.

        resolve_labels(series, roles, registry) -> tuple[dict[int, str], RegistryDelta]
            Per T6's growth policy:
              KNOWN description                  -> use the FROZEN registry label. Never re-derived, so it cannot
                                                    drift with a changing series inventory.
              KNOWN description, re-derivation
                would now differ                 -> LabelDriftError (HARD). The drift guard.
              UNKNOWN description, prior tasks
                still present                    -> AUTO-DERIVE, auto-register, log prominently. NON-BLOCKING.
                                                    This is the "new task added after the first N subjects" case and
                                                    it must keep working.
              old name ABSENT + new name present
                with MATCHING acquisition
                signature                        -> TaskRenameError (HARD). Requires an explicit config resolution.
              a session that BOTH drops a task
                and adds one                     -> TaskRenameError (HARD). The ambiguous case resolves to the loud
                                                    stop: a false positive costs one config line, a false negative
                                                    silently forks one task into two labels across a longitudinal
                                                    dataset.
              two DISTINCT descriptions -> one
                label                            -> LabelCollisionError (HARD). Injectivity.
            NOTE, from the report's empirical findings: the two fMRI paradigms in the example session are PHYSICALLY
            IDENTICAL acquisitions differing only in run length. An acquisition signature therefore CANNOT by itself
            distinguish a rename from an addition, which is exactly why the rename discriminator is keyed on the
            PRESENCE OR ABSENCE of the old description, not on the signature alone. The signature is a corroborating
            witness, not the discriminator.

        Acquisition signature (for the rename test only): the tuple
        (repetition_time, effective_echo_spacing, multiband_factor, matrix), rounded; run length DELIBERATELY EXCLUDED.
      </spec>
      <dependencies>C1, C2, C5</dependencies>
      <risk>high - the rename guard is a hard error on a heuristic. A false positive blocks a batch until a config
        line is added; the report accepts that cost explicitly and the asymmetry argument is recorded above.</risk>
      <rollback>Delete labels.py.</rollback>
    </change>

    <change id="C7" priority="P0" source_item="T7 (aborted-run detection)">
      <file path="fmri_bids_recon/runs.py" action="create" />
      <description>
        Exact-match volume-count detection of aborted/incomplete runs, and run-index assignment over the SURVIVORS.
        The failure mode the legacy `checkdir` logic reached for and never executed.
      </description>
      <spec>
        check_volume_counts(bolds, labels, registry) -> tuple[list[Series], list[Excluded]]
            For each task label, the expected volume count is a REGISTRY property, auto-populated from the first
            complete observation. A run whose n_volumes DEVIATES BY ANY AMOUNT from the registered count is EXCLUDED.
            EXACT MATCH, no threshold. The report's rationale is explicit and is preserved verbatim in the module
            docstring: for a fixed stimulus paradigm the volume count is deterministic, so any threshold is an
            arbitrary free parameter with irreversible downstream consequences (a "90% of expected" rule would admit a
            345-of-383-volume run as complete), and the defensible rule is the one with NO free parameter.

            First observation of a NEW task (no registered count):
              >= 2 runs in this session -> the within-session MODE establishes the count; it is registered.
              exactly 1 run             -> ACCEPTED, registered, and a ReviewFlag is recorded. There is nothing to
                                           compare against, and this residual gap is stated rather than papered over.

        Excluded runs are: NOT written to func/; PRESERVED (NIfTI + sidecar) under sourcedata/; recorded in scans.tsv
        and in the conversion report WITH BOTH COUNTS. Conversion COMPLETES, so unattended HPC batches are not blocked.

        assign_run_indices(surviving, order) -> dict[int, int]
            run- indices are assigned over the SURVIVING runs only, in AcquisitionDateTime order, per task label,
            starting at 1. run- is ALWAYS emitted, even for a singleton run (T6), so the tree stays uniform across
            sessions and a later session acquiring a second run does not create an inconsistent naming pattern or a
            spurious CuBIDS variant group.
      </spec>
      <dependencies>C1, C2, C5, C6</dependencies>
      <risk>medium - an exclusion is a silent-by-design omission from func/. It is made auditable by three independent
        records (scans.tsv, the conversion report, and the preserved sourcedata copy).</risk>
      <rollback>Delete runs.py.</rollback>
    </change>

    <change id="C8" priority="P0" source_item="T4 (temporal mapping and its four guards), B3">
      <file path="fmri_bids_recon/stage3_map.py" action="create" />
      <description>
        Stage 3. The temporal fieldmap-to-target mapping. This is the user's presenting problem, and the report's
        decisive finding is that it is NOT a string problem: the two functional PEPOLAR pairs share an IDENTICAL
        SeriesDescription, so no string in any header distinguishes them. The association exists ONLY in acquisition
        order. The legacy design's acq-rest / acq-enback labels were not merely buggy, they were UNIMPLEMENTABLE AS
        SPECIFIED. The mapping is built here as a first-class data structure, entirely separately from how it is later
        rendered (C11).
      </description>
      <spec>
        order_series(series) -> list[Series]
            Sort by acquisition_datetime (B3). Assert that this ordering agrees monotonically with the SeriesNumber
            ordering; raise OrderingError on disagreement. Two independent witnesses to one ordering, failing loudly.

        pair_fieldmaps(fmaps) -> list[FieldmapPair]
            Consecutive same-modality fieldmap series are paired. GUARD 1: the two members MUST have OPPOSITE
            phase_encoding_direction ("j" vs "j-"); otherwise PhaseEncodingError.
            GUARD 4: the dir- label DERIVED from the signed phase_encoding_direction MUST agree with the PA/AP token
            in the series name; disagreement is PhaseEncodingError. The name is the cross-check, never the source.

        map_fieldmaps(pairs, targets) -> Mapping
            POLICY: nearest-preceding pair of MATCHING MODALITY, STRICT. Each pair owns every subsequent run of its
            modality until the next pair of that modality appears. A run that precedes ALL pairs of its modality is a
            HARD ERROR (FieldmapCoverageError), never a guess.

            GUARD 2 (the guard that makes cross-modality mismapping impossible): the pair's effective_echo_spacing and
            matrix geometry MUST EQUAL its targets'. A fieldmap that does not share readout geometry with its target
            cannot correct it. Violation -> FieldmapGeometryError.
            GUARD 3: every target owns exactly ONE pair, and every pair has at least one target. An orphan pair
            usually means an aborted block and must stop the run rather than be quietly ignored ->
            FieldmapCoverageError.

        Mapping is an explicit dataclass: pair -> list[target Series], plus the derived dir- labels and the pair's
        run- index. It is the SINGLE source of truth from which BOTH IntendedFor and B0Field* are generated in C11,
        which is what makes it structurally impossible for the two renderings to contradict each other.

        SIMPLIFICATION THAT FALLS OUT (T4): the legacy acq-rest / acq-enback fieldmap labels are unnecessary as well
        as unimplementable. BIDS distinguishes the two pairs with run-, and the association is carried by metadata,
        not by the filename.
      </spec>
      <dependencies>C1, C5, C7</dependencies>
      <risk>high - this module IS the refactor. All four guards must be able to fire; a guard that never fires in a
        test is indistinguishable from a guard that does not work (recorded for /test).</risk>
      <rollback>Delete stage3_map.py.</rollback>
    </change>

    <change id="C9" priority="P1" source_item="T11 (physiological recordings)">
      <file path="fmri_bids_recon/physio.py" action="create" />
      <description>
        The CMRR physio parser. Six PhysioLog series (one per functional run) are silently skipped by dcm2niix and are
        therefore currently discarded outright. The format was VERIFIED EMPIRICALLY on this scanner generation before
        being specified: the payload is plain ASCII CMRR logs, LogVersion = EJA_1, and XA30 did not change the
        encoding. This is a parser for a documented ASCII format, not vendor reverse-engineering.
      </description>
      <spec>
        parse_physio_dicom(path: Path) -> PhysioLog
            Read private element (7fe1,1010) with pydicom. It is a LENGTH-PREFIXED container of five ASCII blocks:
            ECG, PULS, RESP, EXT, and Info. Parse each block's length prefix, then its ASCII body.
            Assert LogVersion == "EJA_1"; anything else is a hard stop rather than a best-effort parse.

            The Info block is LogDataType = ACQUISITION_INFO and carries NumVolumes, NumSlices, NumEchoes, FirstTime,
            LastTime, and a per-volume table (VOLUME SLICE ACQ_START_TICS ACQ_FINISH_TICS). This is exactly what BIDS
            StartTime requires.

        SamplingFrequency = 1 / (SampleTime * 2.5e-3).      # Siemens tick = 2.5 ms; SampleTime = 2 on PULS/RESP -> 200 Hz
        StartTime is computed from the ACQUISITION_INFO block's volume-0 ACQ_START_TICS, relative to its associated run.

        associate_physio(logs, bolds) -> dict[int, PhysioLog]
            SAME physics-guard pattern as the fieldmap mapping: temporal adjacency, CONFIRMED by an INDEPENDENT
            geometry match of ACQUISITION_INFO's NumVolumes and NumSlices against the candidate BOLD run's own
            n_volumes and slice count. NO NAME MATCHING ANYWHERE. Disagreement -> PhysioAssociationError.

        write_physio(log, run_prefix, bids_dir) -> None
            Emits BIDS _physio.tsv.gz + _physio.json alongside the functional run.
            COLUMNS: PULS -> `cardiac`, RESP -> `respiratory` (the BIDS-named conventions).
            ECG AND EXT ARE NOT WRITTEN TO THE BIDS TREE. On the verified example the ECG was pinned flat across all
            four leads (no electrodes attached) and EXT is a trigger line; shipping them would place constant,
            non-physiological data in the tree and could mislead a downstream user into believing ECG was recorded.
            The RAW multi-channel log is PRESERVED under sourcedata/, so ECG remains fully recoverable if a future
            session actually attaches electrodes. This is consistent with the ND anatomical (C5) and the excluded runs
            (C7): nothing acquired is destroyed, but only interpretable data enters the tree.
      </spec>
      <dependencies>C1, C4, C5, C7</dependencies>
      <risk>medium - a bespoke binary-container parser. Contained: it is additive, and a failure here cannot corrupt
        the imaging tree.</risk>
      <rollback>Delete physio.py; the imaging tree is unaffected.</rollback>
    </change>

    <change id="C10" priority="P0" source_item="T2 stage 4, T5 (upsert), T10 + A2 (scrub), A3, A4">
      <file path="fmri_bids_recon/tsv.py" action="create" />
      <file path="fmri_bids_recon/stage4_assemble.py" action="create" />
      <description>
        Stage 4. BIDS tree assembly. This module is the SINGLE WRITER of everything that enters the BIDS tree, which
        is what makes the sidecar deny-list (A2) enforceable as an invariant rather than a convention. It also
        implements the additive upsert that replaces the legacy pipeline's destructive `rm` of the dataset-level
        files.
      </description>
      <spec>
        --- THE SIDECAR DENY-LIST (A2). The engine-owned scrub. -------------------------------------------------
        SIDECAR_DENY_LIST: frozenset = {
            "AcquisitionDateTime", "PatientAge", "PatientBirthDate", "PatientID", "PatientName",
            "PatientSex", "PatientSize", "PatientWeight", "SeriesInstanceUID", "StudyID",
            "StudyInstanceUID",
            # residual person-/site-identifying keys, per T10's scrub specification. dcm2niix's own -ba y
            # does NOT remove all of these, which is precisely why T10 says not to trust the flag alone:
            "AccessionNumber", "ReferringPhysicianName", "InstitutionName", "InstitutionAddress",
            "InstitutionalDepartmentName", "StationName", "DeviceSerialNumber", "PerformedProcedureStepDescription",
        }
        scrub(raw: dict) -> dict
            Returns a copy with every deny-listed key removed. This is a DENY-LIST, not an allow-list, deliberately:
            an allow-list would silently drop acquisition parameters that a future dcm2niix release begins to emit,
            and the downstream consumer's REQUIRED_ACQ_PARAMS contract makes silent parameter loss the more dangerous
            failure. New identifier keys, by contrast, are rare and are caught by the C14 audit.
        AUDIT (C14): after assembly, EVERY sidecar written into the BIDS tree is re-read and asserted to contain no
            deny-listed key. This is the enforcement, not the intention.

        --- tsv.py: atomic, additive upsert ---------------------------------------------------------------------
        upsert_tsv(path, rows, key) -> None
            Read-modify-write under an flock on a sibling lockfile, merging by `key` and NEVER overwriting an
            existing row's unrelated columns. Written to a tempfile in the same directory, then os.replace (atomic).
            THIS REPLACES THE LEGACY `rm` OF THE DATASET-LEVEL FILES. The report's root-cause analysis (T1) traces
            that `rm` to a chain of workarounds for an unnamed concurrency problem: participants.tsv is a single
            SHARED file, concurrent SLURM array tasks appending to it race and corrupt it, so the legacy script
            converted into a per-subject BIDS root and then deleted the colliding dataset-level files, thereby
            silently destroying the accumulating subject roster on every run. That is fatal to a longitudinal design.
            The fix is architectural (isolate-then-merge, C16) plus additive upsert here. NOTHING IS EVER DELETED AND
            REGENERATED.

        --- stage4_assemble.py -----------------------------------------------------------------------------------
        assemble(mapping, roles, labels, run_idx, config, staging) -> AssemblyResult

          Paths. ses- is ALWAYS emitted, zero-padded to two digits, from timepoint 1 (T5). The report's argument is
          preserved in the docstring: BIDS permits OMITTING ses- for a single-session dataset and converters routinely
          do so, but omitting it at timepoint 1 and then collecting timepoint 2 forces a rename of every file in the
          dataset AND a rewrite of every IntendedFor path. Emitting it always costs nothing and moots the
          anticipated-session-count question entirely (two digits covers 99 waves).

          Naming:
            anat/  sub-<L>_ses-<NN>_T1w.nii.gz              (the NORM reconstruction; the ND twin -> sourcedata/)
            func/  sub-<L>_ses-<NN>_task-<t>_run-<NN>_bold.nii.gz
                   sub-<L>_ses-<NN>_task-<t>_run-<NN>_sbref.nii.gz
            dwi/   sub-<L>_ses-<NN>_dwi.nii.gz  (+ .bval/.bvec)
            fmap/  sub-<L>_ses-<NN>_acq-func_dir-<PA|AP>_run-<NN>_epi.nii.gz     (T4: acq-func / acq-dwi + dir- + run-)
                   sub-<L>_ses-<NN>_acq-dwi_dir-<PA|AP>_run-<NN>_epi.nii.gz

          Dataset-level files, ALL by additive upsert, NEVER deleted and regenerated (T5):
            dataset_description.json    created if absent; left alone if present
            README, CHANGES             created if absent
            participants.tsv            upsert by participant_id                                         (T5)
            sub-<L>/sub-<L>_sessions.tsv   upsert by session_id. COLUMNS: session_id, wave, acq_time, age.  (A3)
                                           acq_time  <- AcquisitionDateTime  (from staging; DERIVED)
                                           age       <- exact decimal years from PatientBirthDate and the study date,
                                                        falling back to PatientAge only when PatientBirthDate is absent
                                           wave      <- config-supplied, NOT derived
                                        These columns are BIDS-sanctioned demographics and are the reason the
                                        identifiers are read at all. They are written to the secure server (A1).
            .../ses-<NN>/sub-<L>_ses-<NN>_scans.tsv   per-session; filename, acq_time, and the T7 exclusion record.

          sourcedata/ receives, verbatim and unscrubbed: the ND anatomical twins, the excluded (aborted) runs, the raw
          multi-channel physio logs, the unclassified series (A6), and the staging sidecars (which preserve the
          SeriesInstanceUID/StudyInstanceUID provenance link back to the source DICOM that the tree scrub removes).

          PatientID CROSS-CHECK (A4): builds the PatientID <-> sub- map across the run and emits a WARNING (never
          fatal, never a rename) when one PatientID maps to two sub- labels or one sub- label carries two PatientIDs.
          PatientID is never a naming source and never enters the tree.
      </spec>
      <dependencies>C1, C2, C5, C6, C7, C8</dependencies>
      <risk>high - this module is the single writer, so a defect in scrub() or upsert_tsv() has the widest blast
        radius in the system. The C14 post-write audit exists precisely because the deny-list must be verified, not
        trusted.</risk>
      <rollback>Delete tsv.py and stage4_assemble.py. The BIDS tree is written only by this module, so removing it
        leaves staging intact and the tree unbuilt.</rollback>
    </change>

    <change id="C11" priority="P0" source_item="T4 (rendering: BOTH IntendedFor and B0Field*)">
      <file path="fmri_bids_recon/stage5_render.py" action="create" />
      <description>
        Stage 5. The swappable renderer. Serialises the SINGLE authoritative mapping from C8 into fieldmap association
        metadata. The separation of MAPPING from RENDERING is the architectural core of T4: the mapping is a property
        of the acquisition (recoverable from DICOM, independent of any consumer), while the rendering is a consumer
        contract. The legacy design's defining failure was that the mapping existed ONLY as duplicated string literals
        inside sed commands.
      </description>
      <spec>
        render(mapping, bids_root) -> None
            Emits BOTH renderings, generated from the SAME Mapping object, so they CANNOT contradict each other:

            IntendedFor          SUBJECT-RELATIVE LEGACY paths (T4), e.g.
                                 "ses-01/func/sub-<L>_ses-01_task-<t>_run-01_bold.nii.gz"
                                 NOT BIDS URIs. Since B0Field* already serves modern consumers, IntendedFor's role
                                 here is maximum BACKWARD compatibility, which argues for the most conservative
                                 encoding available.
            B0FieldIdentifier    on each fieldmap of a pair; B0FieldSource on each of that pair's targets. A stable
                                 identifier derived from the pair's (modality, run index).

            WHY BOTH (the research finding that dissolves the deferred decision): SDCFlows applies a DATASET-SCOPED
            precedence rule -- if B0FieldIdentifier appears ANYWHERE in the dataset, IntendedFor is ignored
            EVERYWHERE. fMRIPrep (via SDCFlows) prefers B0Field*; QSIPrep 1.1.x reads ONLY IntendedFor. Emitting both
            from one mapping therefore satisfies fMRIPrep, QSIPrep, and whatever the downstream in-house pipeline
            eventually settles on. Both fields are legal BIDS and their coexistence is not an error. This means the
            fieldmap-metadata contract decision the user deferred NEVER HAS TO BE MADE.

        The renderer writes ONLY into sidecars already produced by C10, and therefore inherits the deny-list. It adds
        no key that is not a fieldmap association key.
      </spec>
      <dependencies>C1, C8, C10</dependencies>
      <risk>medium - IntendedFor path format is a known source of downstream breakage; the subject-relative legacy
        form is chosen deliberately for maximum compatibility.</risk>
      <rollback>Delete stage5_render.py. The tree remains valid BIDS but carries no fieldmap association, i.e. it
        reverts to exactly the silent-failure state the refactor exists to eliminate. This module must not be skipped.</rollback>
    </change>

    <change id="C12" priority="P0" source_item="T8 (three-layer validation gate)">
      <file path="fmri_bids_recon/stage6_validate.py" action="create" />
      <description>
        Stage 6. The validation gate, in three layers with DISTINCT roles. The gate is anchored on the finding that
        explains why the original bug survived undetected for so long: BIDS-VALIDATOR DOES NOT FLAG A FIELDMAP WITH NO
        IntendedFor. Such a dataset validates completely clean, then runs clean through preprocessing, which simply
        SKIPS distortion correction. There is no error, no warning, and no output that looks wrong. That is the exact
        profile of the presenting complaint, and it is why the gate cannot rest on bids-validator alone.
      </description>
      <spec>
        LAYER 1 -- ENGINE ASSERTIONS (BLOCKING, per-subject; THE STRONGEST LAYER).
            These run BEFORE anything is written to the BIDS tree. No general-purpose validator can perform them,
            because none of them know what these fieldmaps are supposed to correct. The layer is not new code: it is
            the aggregate of the guards raised in C3, C5, C6, C7, C8, C9. This module asserts that the full guard set
            executed, and fails if any guard was SKIPPED (a guard that silently did not run is the failure mode the
            whole refactor exists to eliminate):
              dcm2niix version floor; AcquisitionDateTime/SeriesNumber ordering agreement; anat suffix physics/name
              agreement; opposite PE within each pair; dir- label agreeing with the signed PE; fieldmap geometry and
              EES matching its targets; every target owning exactly one pair; no orphan pairs; label injectivity;
              non-empty labels; no label drift; no rename collision; exact volume counts; physio geometry agreement.

        LAYER 2 -- BIDS-VALIDATOR (BLOCKING, per-subject).
            run_bids_validator(bids_root) -> raises ValidationError on non-zero exit. Spec compliance only.
            Necessary, cheap, and (as established) blind to semantic emptiness.

        LAYER 3 -- CuBIDS (NON-BLOCKING, per-cohort review artifact).
            The tool that WOULD have caught the original bug. Surfaces what no per-subject check can: a subject whose
            fieldmap coverage differs from the cohort; two task labels sharing one Parameter Group (the C6 rename
            case); an acquisition parameter that drifted mid-study. It is INHERENTLY COHORT-LEVEL, so it is generated
            after each batch and REVIEWED, not gated on.

        MRIQC IS EXPLICITLY OUT OF SCOPE for this module: it measures data QUALITY (motion, SNR, ghosting), not
        conversion CORRECTNESS. Distinct question, distinct remediation, distinct module.
      </spec>
      <dependencies>C1, C3, C5, C6, C7, C8, C9, C10, C11</dependencies>
      <risk>medium - Layer 1's "assert every guard executed" is itself the guard against a guard being skipped.</risk>
      <rollback>Delete stage6_validate.py.</rollback>
    </change>

    <change id="C13" priority="P0" source_item="T2 (six-stage engine), T9 (idempotency)">
      <file path="fmri_bids_recon/manifest.py" action="create" />
      <file path="fmri_bids_recon/__main__.py" action="create" />
      <description>
        The CLI and the idempotency manifest. Wires the six stages into two commands matching the isolate-then-merge
        execution model (T9).
      </description>
      <spec>
        manifest.py -- the Nipoppy "doughnut" pattern (T9, R5): a per-(subject, session) status record
            (pending | converted | assembled | validated | failed) with a timestamp and the dcm2niix version. Re-runs
            SKIP completed units and RESUME cleanly after a partial failure. Written by upsert_tsv (C10), so it is
            safe under the concurrent array tasks.

        __main__.py:
          `python -m fmri_bids_recon convert --config <yaml> --participant <sub> --session <ses>`
              One (subject, session). Runs: version assertion (C3) -> stage 1 (C4) -> stage 2 (C5) -> labels (C6) ->
              runs (C7) -> stage 3 (C8) -> physio (C9). Writes the result to PRIVATE STAGING as a serialised
              intermediate. WRITES NOTHING to the BIDS root. This is the SLURM array task.
          `python -m fmri_bids_recon assemble --config <yaml>`
              Serial. Reads every staged intermediate, then stage 4 (C10) -> stage 5 (C11) -> stage 6 (C12) -> the
              conversion report (C14). The ONLY process that touches the BIDS root, which is what eliminates the
              concurrency hazard by construction rather than by deletion.

        Exit codes: 0 success; 1 GuardError (with the guard name and the topic it enforces); 2 configuration error.
        Log messages carry field NAMES, series numbers, counts, and derived labels only. NEVER a PHI value (A1).
      </spec>
      <dependencies>C1..C12</dependencies>
      <risk>medium - the convert/assemble split is what enforces the concurrency fix; collapsing them into one command
        would silently reintroduce the legacy race.</risk>
      <rollback>Delete manifest.py and __main__.py; the stage modules remain importable.</rollback>
    </change>

    <change id="C14" priority="P0" source_item="T7, T8, A6, A2 (audit), A4">
      <file path="fmri_bids_recon/report.py" action="create" />
      <description>
        The conversion report. Under A6 and C7 the engine now COMPLETES in the presence of exclusions and
        unclassified series rather than halting, which makes this report the sole channel through which those
        decisions become visible. It is a first-class deliverable, not logging.
      </description>
      <spec>
        write_conversion_report(results, bids_root) -> Path
          Emits, per (subject, session):
            EXCLUDED RUNS (C7)          task label, observed count, registered expected count, sourcedata path.
            UNCLASSIFIED SERIES (A6)    series number, why no rule matched, sourcedata path. Prominently, because
                                        this is where a genuinely-new BOLD variant would otherwise vanish quietly.
            NEW TASKS AUTO-REGISTERED (C6)
            REVIEW FLAGS                single-run new task with no comparison count (C7); anatomical with no NORM
                                        variant (C5).
            FIELDMAP MAPPING            the full pair -> targets table, so the association the legacy pipeline never
                                        made is human-readable and checkable.
            PatientID CROSS-CHECK (A4)  warnings only; NEVER the PatientID value itself.
            SIDECAR SCRUB AUDIT (A2)    re-reads EVERY sidecar written into the BIDS tree and asserts that no
                                        deny-listed key survives. Reports the KEY NAMES found, never their values.
                                        A survivor is a HARD ERROR: the deny-list is enforced here, not merely
                                        intended in C10.
            PROVENANCE                  dcm2niix version, engine version, config path, container image hash if set.
        The report contains NO PHI value under any circumstance: field names, series numbers, counts, and derived
        labels only.
      </spec>
      <dependencies>C1, C5, C6, C7, C8, C10</dependencies>
      <risk>medium - under A6 this report is load-bearing for correctness, not merely informational. If it is not
        read, an unclassified functional series is omitted silently.</risk>
      <rollback>Delete report.py.</rollback>
    </change>

    <change id="C15" priority="P1" source_item="T9 (Apptainer, version pinning as a scientific dependency)">
      <file path="hpc/Apptainer.def" action="create" />
      <description>
        A single Apptainer container pinning dcm2niix, bids-validator and CuBIDS to verified versions. Apptainer
        rather than Docker because HPC nodes have no Docker daemon (R5). The image hash is CITABLE IN A METHODS
        SECTION, which is what converts this scientific dependency from ambient to reproducible.
      </description>
      <spec>
        Bootstrap from a minimal Debian base. Pins:
            dcm2niix >= 1.0.20260416   (the VERIFIED FLOOR: signed PhaseEncodingDirection recovery from XA enhanced
                                        DICOM with no CSA headers was verified on exactly this version, and XA support
                                        has evolved substantially across releases; an older binary silently emits no
                                        PhaseEncodingDirection, at which point EVERY fieldmap association the engine
                                        builds is unfounded)
            bids-validator (2.x), CuBIDS, python 3.12, pydicom, nibabel, numpy, PyYAML
        %runscript delegates to `python -m bids_recon`.
        The container does not remove the need for the C3 runtime assertion: C3 runs regardless of how the environment
        was provisioned, because the engine must be safe when run outside the container too.
      </spec>
      <dependencies>C13</dependencies>
      <risk>low - build-time only; cannot corrupt data.</risk>
      <rollback>Delete hpc/Apptainer.def.</rollback>
    </change>

    <change id="C16" priority="P1" source_item="T9 (isolate, then merge)">
      <file path="hpc/convert_array.sbatch" action="create" />
      <file path="hpc/assemble.sbatch" action="create" />
      <description>
        SLURM orchestration. The concurrency hazard behind the legacy `rm` is fixed ARCHITECTURALLY here, not by
        deletion: array tasks convert into PRIVATE staging with no shared state, and a single serial job merges into
        the BIDS root.
      </description>
      <spec>
        convert_array.sbatch   #SBATCH --array=1-N. Task i reads participant i from the config and runs
                               `apptainer exec ... python -m fmri_bids_recon convert`. Writes ONLY to its own private
                               staging directory. No shared state whatsoever, therefore no race.
        assemble.sbatch        Submitted with --dependency=afterok:<array job id>. Runs `python -m fmri_bids_recon
                               assemble` ONCE, serially. The single writer to the BIDS root.

        WHY THIS IS THE FIX (T1, T9): scans.tsv is per-session and sessions.tsv is per-subject, so both are naturally
        isolated. Only participants.tsv and the dataset-level files need the serial merge, and they UPSERT rather than
        overwrite (C10). No races, no deletions, and the subject roster accumulates correctly across waves. Snakemake
        and Nextflow were considered and rejected as substantial machinery for what is genuinely a two-stage pipeline.
      </spec>
      <dependencies>C13, C15</dependencies>
      <risk>low - scheduler glue.</risk>
      <rollback>Delete hpc/.</rollback>
    </change>

    <change id="C17" priority="P2" source_item="T10 (defacing is an OPT-IN PUBLISHING step)">
      <file path="fmri_bids_recon/deface.py" action="create" />
      <description>
        The opt-in defacing stage. NOT part of the analysis path and NOT invoked by `convert` or `assemble`. It is
        implemented last, and deliberately as a separate command, because the report's central argument here is an
        asymmetry: internal analysis does not require defacing; SHARING does.
      </description>
      <spec>
        `python -m fmri_bids_recon deface --config <yaml>` emits `derivatives/defaced/`. It NEVER modifies anat/.

        THE ANALYSIS TREE KEEPS NATIVE ANATOMICALS (T10, LOCKED). Defacing is DESTRUCTIVE and NOT SCIENTIFICALLY FREE:
        removing facial features alters the anatomical volume that FreeSurfer and fMRIPrep register and segment
        against, with published evidence of perturbed cortical thickness estimates and registration quality; and the
        tools are imperfect at their own job (R6 accuracy figures: pydeface ~83%, afni_refacer ~89%, quickshear ~39%).
        Defacing the tree that the downstream pipeline consumes would inject an irreversible, results-altering
        transformation into the ANALYSIS path in order to satisfy a SHARING requirement that has not yet arrived.
        Keeping it a separate, opt-in publishing step means the choice of defacing tool can also be revisited later
        without re-running conversion.
      </spec>
      <dependencies>C13</dependencies>
      <risk>low - additive and off the analysis path by construction.</risk>
      <rollback>Delete deface.py.</rollback>
    </change>

  </changes>

  <execution_order>
    C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17

    Rationale for the ordering. C1 (errors) is first because every guard depends on it and a guard that cannot raise
    is not a guard. C2/C3 (config, version floor) precede any conversion. C4 (staging) must precede C5 because
    classification consumes sidecars. C5 (classification) must precede C6 (labels) for the reason the report states
    explicitly: the derived protocol prefix is computed over the series RETAINED AFTER CLASSIFICATION, and computing
    it over raw series would find no prefix at all because the scout does not carry one. C7 (volume counts) precedes
    C8 because run- indices are assigned over survivors only. C8 (mapping) precedes C10/C11 because both consume the
    single Mapping object. C10 (assembly) precedes C11 (rendering) because the renderer writes into sidecars the
    assembler has already produced, which is what makes the deny-list inherited rather than re-implemented. C12
    (validation) and C14 (report) come after everything they inspect. C15-C17 are deployment and publishing concerns
    and do not block the engine.

    NOT MODIFIED BY THIS PLAN: fmri-bids-recon.sh and bids-heuristic-bw.py remain in place, untouched and unreferenced (A5).
  </execution_order>

  <build_prerequisite>
    PyYAML must be installed into the `fmri-bids-recon` conda environment before C2 can be exercised. Per the Environment
    Pre-Flight contract this requires explicit per-invocation user approval and is performed by the orchestrator, not
    by a dispatched execution agent. It is a mechanical dependency, not a design decision.
  </build_prerequisite>
</implement_plan>
