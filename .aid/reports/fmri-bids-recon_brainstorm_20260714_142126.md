<brainstorm_report>
  <meta project="fmri-bids-recon" mode="brainstorm" timestamp="2026-07-14T18:21:26Z" />

  <redaction_note>
    All person-centered content and all lab-, site-, and study-identifying content is excluded from this report by
    directive. No patient identifiers, no institution or device identifiers, no study or protocol name, and no
    acquisition dates appear anywhere. Acquisition times are recorded as ELAPSED OFFSETS from the first fieldmap
    rather than as clock times; the temporal argument depends only on ordering and adjacency, so nothing analytic is
    lost. Scanner platform, series, task, and acquisition-parameter characterization IS retained, because it describes
    the imaging protocol rather than any person, and because it is the evidence base for the decisions below.

    The study-protocol prefix token observed in the example data is written throughout as `<STUDY>`. Its literal value
    is deliberately not recorded, and by design it is never needed: the engine DERIVES this token at runtime (T6)
    rather than being told it.
  </redaction_note>

  <context_files>
    <file path="fmri-bids-recon.sh" relevance="Legacy SLURM driver. Contains the IntendedFor sed block that has never executed (unreachable behind `exit 0` at line 41; `checkdir` commented out at line 34). Also the destructive `rm` of dataset-level BIDS files at lines 146-149." />
    <file path="bids-heuristic-bw.py" relevance="Legacy heudiconv heuristic. Source of the misclassification. Undefined name `er_1` at line 74; broad-substring `elif` chain that shadows all distortion-map branches; three fmap keys sharing one identical template (lines 48-50)." />
<file path="(read-only) fmri-preproc/fmri_preproc/bids_input.py" relevance="Downstream consumer contract. REQUIRED_ACQ_PARAMS = {repetition_time, phase_encoding_direction, echo_spacing}; NULLABLE = {multiband, slice_timing}. discover_runs() globs func/*_bold.nii[.gz] only; no fmap/ discovery. Fails closed with sys.exit(1) on >1 anat/*_T1w.nii.gz." />
    <file path="(read-only) fmri-preproc/fmri_preproc/stages/layer1_minproc.py" relevance="L1_2_SDC.run() raises NotImplementedError. Confirms SDC is not yet wired, and that total_readout_time is derived internally rather than consumed as an input." />
  </context_files>

  <empirical_findings>
    Established by direct measurement against the example session, not inferred from documentation. These are protocol
    and platform facts; they are the evidence base for the locked decisions and should be treated as verified inputs by
    downstream skills.

    SCANNER PLATFORM
    - Siemens MAGNETOM Prisma, software `syngo MR XA30`, 3T.
    - Enhanced multiframe DICOM (SOPClassUID 1.2.840.10008.5.1.4.1.1.4.1). PerFrameFunctionalGroupsSequence (5200,9230) PRESENT.
    - Classic CSA headers (0029,1010) and (0029,1020) are ABSENT. Any design depending on classic CSA parsing is non-viable
      on XA-generation data.

    DCM2NIIX CAPABILITY (the decisive finding; gates the whole architecture)
    - dcm2niix v1.0.20260416 DOES recover signed PhaseEncodingDirection from XA30 enhanced DICOM despite the absence of
      classic CSA. Verified: each PEPOLAR pair resolves to "j" and "j-". Polarity is correct and the two members of a pair
      are distinguishable.
    - EffectiveEchoSpacing (0.000510 s functional / 0.000689 s diffusion), TotalReadoutTime (0.045391 / 0.095909),
      RepetitionTime, 60-entry SliceTiming, and MultibandAccelerationFactor are all populated.
    - CONSEQUENCE: every field in fmri-preproc's REQUIRED_ACQ_PARAMS is present, and both NULLABLE_ACQ_PARAMS are present.
      The sys.exit(1) path in resolve_acquisition() will not trigger. The CSA-absence risk is closed.
    - CAVEAT: dcm2niix emits `Issue870 ParallelReductionFactorOutOfPlane estimated as 3 but DICOM reports 1` on the
      diffusion series. MultibandAccelerationFactor = 3 for dMRI is therefore dcm2niix's INFERENCE, not a header read.
      No such warning on BOLD (MB = 6). Low stakes (multiband is nullable and diffusion is not on fmri-preproc's functional
      path) but it must not be treated as ground truth.
    - CAVEAT: dcm2niix's own `BidsGuess` field is NOT trustworthy. It classified the T2w structural as
      `['func', '_acq-spc2p2_dir-RL_run-8_bold']`. Any design leaning on dcm2niix auto-BIDS guessing inherits this error.

    CLASSIFICATION TAGS (two distinct fields carry the load)
    - `ImageType` (DICOM standard): gives ORIGINAL vs DERIVED, and the modality token FMRI / DIFFUSION / M / OTHER.
    - `ImageTypeText` (Siemens, surfaced by dcm2niix in the sidecar): gives ND vs NORM and MB.
    - The duplicate anatomicals are distinguishable ONLY by ImageTypeText:
        ser 4 T1w = ORIGINAL/PRIMARY/M/ND          ser 5 T1w = ORIGINAL/PRIMARY/M/ND/NORM
        ser 8 T2w = ORIGINAL/PRIMARY/M/ND          ser 9 T2w = ORIGINAL/PRIMARY/M/ND/NORM
      Their standard `ImageType` values are byte-identical. A classifier reading only `ImageType` cannot tell them apart.

    SERIES INVENTORY (40 series; `<STUDY>` denotes the redacted protocol prefix token)
      1     localizer_32ch                            (scout; ImageTypeText NORM/DIS2D)
      2,3   <STUDY>_T1w_vNav_setter                   (navigator time series; 150 frames, 32x32 geometry)
      6,7   <STUDY>_T2w_vNav_setter                   (navigator time series; 122 frames, 32x32 geometry)
      4,5   <STUDY>_T1w_MPR_vNav                      (ND / NORM twins)
      8,9   <STUDY>_T2w_SPC_vNav                      (ND / NORM twins)
      10,12 <STUDY>_fMRI_DistortionMap_PA / _AP       (PEPOLAR pair 1)
      14,18 <STUDY>_fMRI_task_Emotional_n-back_SBRef  15,19 ..._n-back BOLD (370 volumes each)
      17,21 <STUDY>_fMRI_task_Emotional_n-back_PhysioLog
      22,24 <STUDY>_fMRI_DistortionMap_PA / _AP       (PEPOLAR pair 2)
      26,30,34,38 <STUDY>_fMRI_rest_SBRef             27,31,35,39 <STUDY>_fMRI_rest BOLD (383 volumes each)
      29,33,37,41 <STUDY>_fMRI_rest_PhysioLog
      42-45 <STUDY>_dMRI_DistortionMap_PA / _AP       46 <STUDY>_dMRI_SBRef   47 <STUDY>_dMRI (103 files)
      49,50 <STUDY>_dMRI_FA / <STUDY>_dMRI_ColFA      (DERIVED)
      99    PhoenixZIPReport                          (Modality = SR, CSA REPORT)
    - dcm2niix silently SKIPS the six PhysioLog series and PhoenixZIPReport. They need no exclusion rule, but physio data
      is discarded unless explicitly extracted (see T11).

    THE FIELDMAP MAPPING IS NOT RECOVERABLE FROM NAMES (the finding that reframes the whole refactor)
    - Series 10 and series 22 have the IDENTICAL SeriesDescription. So do series 12 and 24.
    - There is NO string in any header that distinguishes the n-back fieldmap pair from the rest fieldmap pair.
    - The legacy heuristic attempted to write `acq-rest` / `acq-enback` labels onto them. This was never achievable by
      string matching, on any data. The legacy design was not merely buggy; it was UNIMPLEMENTABLE AS SPECIFIED.
    - The information exists ONLY in acquisition order. Expressed as elapsed offsets from the first fieldmap, the nesting
      is perfect:
        t+00:00  fmap PA (10)      t+00:09  fmap AP (12)   ->  t+05:09 n-back (15), t+11:08 n-back (19)
        t+16:09  fmap PA (22)      t+16:18  fmap AP (24)   ->  t+17:59 rest (27), t+23:50 (31), t+30:08 (35), t+36:16 (39)
        t+43:56  dwi fmap PA (43)  t+44:19  dwi fmap AP (45) ->  t+44:46 dMRI (47)

    ACQUISITION SIGNATURES CANNOT DISTINGUISH TWO fMRI TASKS
    - The n-back and rest paradigms are PHYSICALLY IDENTICAL acquisitions: TR 0.8 s, EES 0.000510 s, TRT 0.045391 s,
      MB 6, 90x90x60. They differ only in run length (370 vs 383 volumes).
    - CONSEQUENCE: a renamed task and a genuinely-new task look the same to the scanner. Any "same signature, different
      name -> error" rule would fire on every legitimate new task. This directly constrains the T6 rename guard.

    PHYSIO PAYLOAD (verified empirically; no XA30 surprise)
    - PhysioLog series are Raw Data Storage (SOPClassUID 1.2.840.10008.5.1.4.1.1.66) with a Siemens private payload in
      (7fe1,1010), on the order of 10 MB.
    - The payload is PLAIN ASCII CMRR physio logs, five length-prefixed blocks: ECG, PULS, RESP, EXT, and Info.
    - `LogVersion = EJA_1` (canonical CMRR format). XA30 did NOT change this encoding.
    - The Info block is `LogDataType = ACQUISITION_INFO`, carrying NumVolumes, NumSlices, NumEchoes, FirstTime, LastTime,
      and a per-volume table `VOLUME SLICE ACQ_START_TICS ACQ_FINISH_TICS`. This is exactly what BIDS StartTime requires.
    - ACQUISITION_INFO geometry matches the BOLD runs exactly: the n-back physio logs report 370 volumes / 60 slices and
      the rest physio logs report 383 / 60, matching their runs. Physio-to-BOLD association therefore uses the SAME
      physics-guard pattern as the fieldmap mapping (temporal adjacency + independent geometry confirmation).
    - PULS / RESP SampleTime = 2 -> 2 x 2.5 ms ticks -> 200 Hz.
    - ECG is pinned flat across all four leads (no electrodes attached). EXT is a trigger line.

    PHI SURFACE (stated as a scrub specification; no values recorded)
    - DICOM headers carry the standard person-identifying and site-identifying field set, and dcm2niix COPIES patient
      identifiers into the JSON sidecar unless `-ba y` is set. The scrub list the engine must enforce is therefore the
      standard set: patient identifiers and demographics, accession and study identifiers, referring-physician fields,
      and institution / department / station / device-serial fields.
    - This is a specification of what the engine removes. No value from any of these fields appears in this report, and
      none may be propagated into the BIDS tree.
  </empirical_findings>

  <topics>

    <topic id="T1" title="Root-cause diagnosis of the legacy pipeline">
      <summary>
        The user's presenting complaint was "heudiconv is not behaving as expected" plus "there are lines that don't run."
        Both were traced to specific, mechanical causes. heudiconv itself is exonerated.

        WHY THE HEURISTIC MISCLASSIFIES. Traced against the actual SeriesDescriptions:
          - `'enback' in '<STUDY>_fMRI_task_Emotional_n-back'` is FALSE (the protocol writes `n-back`, hyphenated).
            Both n-back runs are silently DROPPED. The undefined-name bug at line 74 (`er_1`) never even fires, because
            its branch is unreachable on real data.
          - `'rest'` matches the rest BOLD series, its SBRef, AND its PhysioLog. SBRefs and physio logs are appended to
            info[rest] as if they were BOLD runs.
          - `'dMRI'` matches eight series, and `info[dwi]` is an ASSIGNMENT rather than an append, so the LAST match wins:
            a scanner-DERIVED colour-FA map. The actual 103-volume diffusion series is discarded and replaced by a derived
            image.
          - No branch matches the functional distortion maps at all (the heuristic expects a task token inside the fieldmap
            name that the protocol does not put there), so EVERY functional fieldmap is dropped.
          - T1w / T2w resolve by last-wins to an arbitrary member of the ND / NORM twin pair.

        WHY IntendedFor NEVER RAN. Two independent, each-sufficient causes:
          - `exit 0` at line 41 makes the entire `# ----- START EDITING HERE -----` block unreachable.
          - `checkdir` is commented out at line 34 but referenced at lines 70, 74, 88, 98, 105, so every `cd` and existence
            test would fail even if the `exit 0` were removed.

        WHY NOBODY NOTICED. bids-validator does NOT flag a fieldmap with an absent IntendedFor. Such a dataset validates
        completely clean, runs clean through preprocessing, and silently skips distortion correction. There is no error, no
        warning, and no output that looks wrong. CuBIDS is the tool that surfaces this class of defect.

        WHY THE `rm` OF DATASET-LEVEL FILES EXISTS (lines 146-149). The script converts into a PER-SUBJECT BIDS root
        (`-o ${bidsdir}/sub-${outputsub}`), so every subject gets its own dataset_description.json, README, CHANGES, and
        participants.tsv, which collide on merge. The `rm` is a workaround. But the per-subject root was itself a workaround
        for a deeper hazard: participants.tsv is a single SHARED file and concurrent SLURM array tasks appending to it race
        and corrupt it. The deletion is the last link in a chain of workarounds for an unnamed concurrency problem, and it
        silently destroys the accumulating subject roster, which is fatal longitudinally.
      </summary>
      <research>
        R7 exonerated `--minmeta`: it gates exactly one call (`embed_metadata_from_dicoms`), skipping only the dcmstack
        overlay. All dcm2niix-derived acquisition fields survive. The flag was never the problem.
      </research>
      <decision status="decided" chosen="none">
        Diagnostic topic; no design choice. Recorded because every subsequent decision is a response to one of these five
        failures, and because the causes must not be reintroduced.
      </decision>
    </topic>

    <topic id="T2" title="Conversion architecture">
      <summary>
        The ordering question: does series classification happen BEFORE dcm2niix (heudiconv heuristic model, operating on
        raw seqinfo) or AFTER it (operating on emitted JSON sidecars)?
      </summary>
      <research>
        R1/R2/R3 surveyed heudiconv, dcm2bids v3.2.0, BIDScoin v4.6.x, bidskit, ezBIDS. All shell out to dcm2niix as the
        underlying converter, so none differ in metadata-recovery capability. R3's recommended CSA-based
        PhaseEncodingDirectionPositive route is non-viable here (classic CSA absent on XA).
      </research>
      <approaches>
        <approach id="A1" label="dcm2niix-first engine" feasibility="high" risk="low">
          <description>
            Stage 1: dcm2niix converts the session into a staging directory.
            Stage 2: a project-agnostic rule engine classifies from the SIDECARS using acquisition physics.
            Stage 3: temporal fieldmap-to-target mapping from AcquisitionTime.
            Stage 4: BIDS tree assembly (naming, scaffolding, scans.tsv, sessions.tsv, participants.tsv upsert).
            Stage 5: swappable renderer emits fieldmap association metadata.
            Stage 6: validation gate.
            Per-study input is a small declarative YAML. Engine code is never edited per project.
          </description>
          <pros>
            Classifies from a vendor-normalised, community-maintained representation rather than raw vendor headers.
            Signed PhaseEncodingDirection, EffectiveEchoSpacing, ImageTypeText, AcquisitionTime and SliceTiming are all
            already resolved by dcm2niix, so the engine never re-implements Siemens header archaeology.
            Maximally reusable across future scanners and software versions, which was an explicit user directive.
            Core decision logic becomes testable with small, fully synthetic JSON fixtures rather than a real DICOM corpus.
          </pros>
          <cons>
            We own BIDS assembly (dataset_description.json, participants.tsv, scans.tsv, run-numbering, re-run idempotency)
            that heudiconv would otherwise provide. Mitigated by generating names against the official BIDS schema rather
            than inventing conventions, and by gating on bids-validator plus CuBIDS.
          </cons>
        </approach>
        <approach id="A2" label="heudiconv with a generic heuristic" feasibility="med" risk="high">
          <description>
            One project-agnostic heuristic that loads a study YAML; never edited per project. Retains heudiconv's
            scaffolding, provenance, and .heudiconv idempotent re-run tracking.
          </description>
          <pros>Keeps community-maintained BIDS assembly and re-run tracking. Preserves existing team familiarity.</pros>
          <cons>
            DECISIVE: a heuristic runs BEFORE dcm2niix, on raw seqinfo. ImageTypeText, AcquisitionTime, ScanningSequence and
            dim4 are all reachable via custom_seqinfo, but SIGNED PHASE-ENCODING POLARITY is not. On XA without CSA,
            recovering `j` vs `j-` is precisely the vendor archaeology dcm2niix performs. A generic heuristic would force us
            to re-implement and then maintain Siemens XA header parsing across future scanner software versions. For a
            converter intended to outlive this study, owning that code is the wrong liability.
          </cons>
        </approach>
        <approach id="A3" label="BIDScoin" feasibility="med" risk="med">
          <description>Bounded B0FieldIdentifier `[start:stop]` is purpose-built for temporal-adjacency fieldmap association.</description>
          <pros>Native support for exactly the temporal-nesting problem this protocol presents.</pros>
          <cons>
            Commits the dataset to B0Field* rendering, which triggers the dataset-scoped SDCFlows precedence rule and breaks
            QSIPrep (reads only IntendedFor), i.e. it forces the fieldmap-contract decision the user deferred. The bidsmap is
            also a per-study artifact edited via GUI, which is the same objection as a per-study heuristic.
          </cons>
        </approach>
        <approach id="A4" label="dcm2bids" feasibility="low" risk="high">
          <description>Declarative JSON config with criteria matching on sidecar fields.</description>
          <pros>Purely declarative; classifies post-dcm2niix, so it shares A1's information advantage.</pros>
          <cons>
            REJECTED ON EVIDENCE: the two functional fieldmap pairs are indistinguishable by any sidecar field except
            SeriesNumber. Disambiguation therefore requires hardcoding series numbers per study, which directly violates the
            user's reusability directive.
          </cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        LOCKED: dcm2niix-first engine. Chosen because classification must consume vendor-normalised sidecars rather than raw
        XA headers, because it is the only option that satisfies both the "no per-project logic file" and the "reusable on
        future datasets" directives, and because it makes the fieldmap mapping a first-class data structure rather than a
        naming side-effect. The user explicitly required maximum flexibility and no study-specific assumptions anywhere in
        the engine.
      </decision>
    </topic>

    <topic id="T3" title="Series classification rule set and anatomical variant selection">
      <summary>
        Every discriminator is an acquisition property. No rule anywhere in the engine may reference a study-specific string
        (no protocol prefix, no task name, no modality token lifted from a series name). Substring matching on
        SeriesDescription is what broke the legacy heuristic and it is banned from the classifier.
      </summary>
      <approaches>
        <approach id="A1" label="Physics-driven rule table" feasibility="high" risk="low">
          <description>
            drop derived     : ImageType[0] == DERIVED                                    -> ser 49, 50
            drop scout       : ImageTypeText has DIS2D, no MB, 2D single-slice            -> ser 1
            drop navigator   : navigator geometry (32x32), high frame count, no BIDS role -> ser 2, 3, 6, 7
            anat             : 3D, ImageType[2] == M, non-EPI                             -> ser 4, 5, 8, 9
            bold             : ImageType[2] == FMRI and dim4 > 1                          -> ser 15, 19, 27, 31, 35, 39
            sbref            : ImageType[2] == FMRI and dim4 == 1, followed by a bold     -> ser 14, 18, 26, 30, 34, 38
            fmap (func)      : ImageType[2] == FMRI, spin-echo EPI, opposite-PE partner   -> ser 10/12, 22/24
            dwi              : ImageType[2] == DIFFUSION, ORIGINAL, has b-vectors         -> ser 47
            fmap (dwi)       : ImageType[2] == DIFFUSION, spin-echo, opposite-PE partner  -> ser 43/45

            dir- labels are derived from the sidecar's signed PhaseEncodingDirection (j / j-), NOT from the _PA / _AP token
            in the series name. The name token becomes a CROSS-CHECK that fails loudly on disagreement, which converts the
            exact class of silent error that sank the original into a hard stop.
          </description>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        LOCKED: physics-driven rule table as above.

        ANATOMICAL VARIANT SELECTION (the hard consumer constraint):
        - The NORM (prescan-normalised, coil-bias-corrected) reconstruction goes to `anat/`.
        - The ND (un-normalised) twin is PRESERVED under `sourcedata/`. Nothing acquired is destroyed.
        - Rationale: this follows heudiconv's ReproIn convention, which explicitly prefers NORM when both exist, and matches
          the reference pipeline that fmri-preproc replicates.

        DETERMINATION (technical, not a preference): the ND twin MUST be physically separated into `sourcedata/`.
        `.bidsignore` is NOT sufficient, because it suppresses only the VALIDATOR, whereas bids_input.py reaches the file
        with a raw `glob` on `anat/*_T1w.nii.gz` which ignores `.bidsignore` entirely. An in-tree ND twin, however labelled
        or ignored, would still trigger the downstream `sys.exit(1)`. Entity labels do not rescue this either:
        `_rec-norm_T1w.nii.gz` and `_rec-nonorm_T1w.nii.gz` both match that glob.
      </decision>
    </topic>

    <topic id="T4" title="Fieldmap-to-target mapping and rendering">
      <summary>
        The user's presenting problem. Reframed by the empirical finding that the mapping is not a string problem at all: the
        two functional fieldmap pairs share an identical SeriesDescription, so the association exists ONLY in acquisition
        order. The architectural fix is to separate the MAPPING (which fieldmap corrects which scan: a property of the
        acquisition, recoverable from DICOM, independent of any consumer) from the RENDERING (which JSON keys it is
        serialised into: the consumer contract). The legacy design's defining failure was that the mapping existed only as
        duplicated string literals inside sed commands.
      </summary>
      <research>
        R2/R3: SDCFlows applies a DATASET-SCOPED precedence rule. If B0FieldIdentifier is present ANYWHERE in the dataset,
        IntendedFor is ignored EVERYWHERE. QSIPrep 1.1.x reads ONLY IntendedFor. fMRIPrep (via SDCFlows) prefers B0Field*.
        R4: bids-validator does not flag fieldmaps with absent IntendedFor; CuBIDS does surface the resulting anomaly.
      </research>
      <approaches>
        <approach id="A1" label="Temporal nesting, nearest-preceding-strict, render both" feasibility="high" risk="low">
          <description>
            ALGORITHM. Order all series by AcquisitionTime. Within each modality, each PEPOLAR pair owns every subsequent run
            until the next pair of that modality appears. A run that precedes ALL pairs of its modality is a HARD ERROR,
            never a guess.

            GUARDS (the mapping is only emitted if all hold):
              1. The two members of a pair have OPPOSITE PhaseEncodingDirection (j vs j-).
              2. The pair's EffectiveEchoSpacing and matrix geometry EQUAL its targets'. A fieldmap that does not share
                 readout geometry with its target cannot correct it, so this check makes cross-modality mismapping
                 impossible. Verified: functional fieldmaps and functional runs share EES 0.000510 s and 90x90x60 geometry;
                 diffusion fieldmaps and the dMRI run share EES 0.000689 s.
              3. Every target owns exactly one pair; every pair has at least one target. An orphan pair usually means an
                 aborted block and must stop the run rather than be quietly ignored.
              4. The dir- label derived from signed PhaseEncodingDirection MUST agree with the _PA / _AP token in the series
                 name. Disagreement is a hard error.

            RENDERING. Both IntendedFor AND B0FieldIdentifier/B0FieldSource are emitted, generated from the SINGLE
            authoritative mapping, so they cannot contradict each other. This satisfies fMRIPrep (prefers B0Field*), QSIPrep
            (reads only IntendedFor), and whatever fmri-preproc eventually settles on. Both fields are legal BIDS;
            coexistence is not an error.

            SIMPLIFICATION THAT FALLS OUT. The legacy `acq-rest` / `acq-enback` fieldmap labels are unnecessary as well as
            unimplementable. BIDS distinguishes the two pairs with `run-`, and the association is carried by metadata, not by
            the filename.
          </description>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        LOCKED.
        - Association policy: nearest-preceding pair of matching modality, STRICT. Errors rather than guessing when a run
          precedes all pairs of its modality.
        - Rendering: BOTH IntendedFor and B0Field*, from one mapping. This fully DISSOLVES the fieldmap-metadata contract
          decision the user deferred pending completion of fmri-preproc: it never has to be made.
        - IntendedFor path format: SUBJECT-RELATIVE LEGACY paths
          (e.g. "ses-01/func/sub-<label>_ses-01_task-rest_run-01_bold.nii.gz"), not BIDS URIs. Since B0Field* already serves
          modern consumers, IntendedFor's role here is maximum backward compatibility, which argues for the most conservative
          encoding.
        - Fieldmap naming: acq-func / acq-dwi + dir- + run-.
          e.g. fmap/sub-<label>_ses-01_acq-func_dir-PA_run-01_epi.nii.gz (first pair), run-02 (second pair);
               fmap/sub-<label>_ses-01_acq-dwi_dir-PA_run-01_epi.nii.gz  (diffusion pair).
      </decision>
    </topic>

    <topic id="T5" title="Longitudinal and multi-session structure">
      <summary>
        The user proposed parameterising the number of anticipated future sessions. Rejected on analysis: it solves a problem
        BIDS does not have and creates one it otherwise would not. A dataset containing only ses-01 is fully valid, and adding
        ses-02 later is fully valid; the spec is additive by construction. Pre-creating empty session directories reserves
        nothing and is non-idiomatic.

        THE ACTUAL LONGITUDINAL RISKS ARE ELSEWHERE, AND BOTH ARE SEVERE.
        1. BIDS permits OMITTING the ses- entity when a dataset has one session, and converters routinely do so. Omit it at
           timepoint 1 and then collect timepoint 2, and you must rename every file in the dataset and rewrite every
           IntendedFor path. This is the migration longitudinal studies actually get burned by. Fix costs nothing: always emit
           ses-, zero-padded to two digits (covers 99 waves, which moots the anticipated-count question).
        2. The legacy `rm ... participants.tsv` (see T1) DESTROYS THE ACCUMULATING SUBJECT ROSTER. In a longitudinal design
           every conversion run silently rewrites it. Additive upsert (merge by participant_id, never overwrite) is a
           precondition for adding ses-02 without disturbing ses-01.
      </summary>
      <decision status="decided" chosen="A1">
        LOCKED:
        - ses- is ALWAYS emitted, from timepoint 1, zero-padded to two digits (ses-01, ses-02, ...).
        - Session labels are stable numeric ORDINALS. The human-readable wave name, scan date, and age at scan live in
          `sub-<label>/sub-<label>_sessions.tsv`. This decouples the immutable directory label from the mutable study
          vocabulary: renaming a wave or inserting an unplanned timepoint edits a TSV cell instead of migrating the dataset
          and rewriting every IntendedFor path.
        - Dataset-level files (participants.tsv, dataset_description.json, README, CHANGES) use ADDITIVE UPSERT. They are
          NEVER deleted and regenerated.
        - NO anticipated-session-count parameter. It is not needed.
      </decision>
    </topic>

    <topic id="T6" title="Header-driven labelling and the study configuration">
      <summary>
        User directive: pull task names from headers, automate labelling, and hardcode nothing. A hard constraint was added
        mid-discussion: the engine must contain NO study-specific vocabulary whatsoever. A second constraint: user-supplied
        labels, not header-derived ones, for study and participant, because PatientID and StudyDescription frequently do not
        align with the labels assigned after data collection.
      </summary>
      <approaches>
        <approach id="A1" label="Derived-prefix + BIDS stop-list, registry-backed" feasibility="high" risk="low">
          <description>
            MECHANISM 1 (the protocol prefix is DERIVED, never listed). Take the longest common leading token sequence across
            all series RETAINED AFTER CLASSIFICATION (which excludes the scout, the vNav setters, and the derived maps). In
            the example session every retained series begins with the same token, so that token is discovered as the protocol
            namespace and stripped. On a different study the same computation discovers whatever that study's prefix is, or
            discovers none. This is a zero-entropy argument: a token present in every series carries no discriminative
            information and therefore cannot belong to a label whose purpose is to distinguish series.

            This is also why the engine never needs to be TOLD the protocol prefix, and why the literal token is not recorded
            anywhere in this report: it is computed at runtime from whatever data is presented.

            NOTE: this is a second reason classification must precede labelling. The scout carries no protocol prefix, so
            computing the prefix over RAW series would find nothing.

            MECHANISM 2 (the stop-list is BIDS vocabulary, never study vocabulary). Strip reserved words defined by the spec
            or by MRI physics: entity keywords (task, run, dir, acq, rec, echo), modality/suffix words (fmri, bold, epi, dwi,
            dmri, t1w, t2w, sbref), directions (ap, pa, lr, rl), and vendor recon tokens (nd, norm, mb, dis2d, setter). Every
            entry is defensible because every entry is defined outside any particular study.

            Then sanitise to alphanumeric, lowercase.

            WORKED EXAMPLE: `<STUDY>_fMRI_task_Emotional_n-back` -> strip the derived prefix -> strip the reserved tokens
            {fmri, task} -> sanitise -> `task-emotionalnback`. `<STUDY>_fMRI_rest` -> `task-rest`.

            HARD GUARDS (these are what make "fully automatic" safe, by converting silent mislabels into loud stops):
              - INJECTIVITY: two DISTINCT SeriesDescriptions collapsing to one label is a hard error. (Two runs of the same
                task legitimately SHARE a description; that is a run index, not a collision.)
              - NON-EMPTY: a label that strips to nothing is a hard error, never a fallback guess.

            NOTE ON WHAT HEADERS CANNOT GIVE: DICOM has no concept of "task". It is a study-design property, not a scanner
            property. SeriesDescription / ProtocolName is the only channel that exists. There is no header field being left
            unexploited.
          </description>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        LOCKED: fully automatic derivation via derived-prefix + BIDS stop-list, with injectivity and non-empty guards. No
        review gate (the user explicitly rejected a mandatory review step).

        TASK REGISTRY AND ITS GROWTH POLICY. The study config carries a registry keyed by SeriesDescription:
          - KNOWN description -> use the frozen label. Never re-derived, so it cannot drift.
          - UNKNOWN description, prior tasks still present -> AUTO-DERIVE, auto-register, log prominently. This is the
            post-pilot "new task added after the first N subjects" case, and it must keep working. Non-blocking.
          - RE-DERIVATION DISAGREEMENT (a known description would now derive to a different label, e.g. because a missing
            series shifted the discovered prefix) -> HARD ERROR. This is the drift guard.
          - LABEL COLLISION -> HARD ERROR.
          - RENAME SUSPICION -> HARD ERROR, requiring explicit resolution in the config.

        THE RENAME DISCRIMINATOR (constrained by the empirical finding that the two fMRI paradigms are physically identical
        acquisitions, so signature alone cannot distinguish a rename from an addition):
          - Old name STILL PRESENT + new name also present             -> a task was ADDED. Auto-register.
          - Old name ABSENT + new name present with MATCHING signature -> the task was RENAMED. HARD ERROR.
        The ambiguous case (a session that BOTH drops a task and adds one) resolves to HARD ERROR. Rationale: a false positive
        costs one config line; a false negative silently forks one task into two labels across a longitudinal dataset, which
        is far more expensive to discover and repair later.

        RUN ENTITY: `run-` is ALWAYS emitted, even for a singleton run, so the tree stays uniform across sessions and a later
        session acquiring a second run does not create an inconsistent naming pattern or a spurious CuBIDS variant group.
        fmri-preproc globs func/*_bold.nii[.gz] and is indifferent to run- presence, so this costs nothing downstream.

        PER-STUDY CONFIG (the ONLY per-study artifact; engine code is never edited):
          study_name:   "<user-supplied>"      # NOT StudyDescription
          participants:
            - {source: <dicom dir>, sub: "<user-supplied>", ses: "01"}   # NOT PatientID
          task_labels:  <auto-derived and auto-maintained registry>

        PatientID CROSS-CHECK (surfaced to the user, not assumed): PatientID may be read ONLY as a consistency check (warn if
        one PatientID maps to two sub- labels or vice versa) and must be kept out of the BIDS tree entirely, since it is PHI.
        It is never a naming source.
      </decision>
    </topic>

    <topic id="T7" title="Incomplete and aborted run detection">
      <summary>
        The failure mode the legacy `checkdir` logic was reaching for, and which never ran.

        MECHANISM. When a run is aborted and restarted, the scanner does not overwrite the partial series; it writes a NEW
        SERIES NUMBER. A resting-state scan aborted at 20 volumes and restarted produces two series with the same
        SeriesDescription, one with 20 volumes and one with the full 383. The run-numbering rule (acquisition order within
        task) would then emit run-01 (the 20-volume fragment) and run-02 (the real run), and the fragment enters the BIDS tree
        as a first-class run. fmri-preproc globs func/*_bold.nii[.gz], finds it, and preprocesses 20 volumes as if complete.
        Nothing anywhere raises an error. This is the same silent-corruption class as the IntendedFor failure. The example
        session is clean (370, 370, 383, 383, 383, 383), so this is latent, not active.

        DETECTOR. For a fixed stimulus paradigm, volume count is DETERMINISTIC. Expected count is therefore a property of the
        task and belongs in the same registry that holds task labels, auto-populated from the first complete observation.

        CHAOS-THEORY EXPOSURE, STATED EXPLICITLY. Any threshold is an arbitrary parameter with irreversible downstream
        consequences: a "90% of expected" rule would admit a 345-volume run as complete. EXACT-MATCH to the registered count
        is the defensible rule precisely because it has NO FREE PARAMETER. For a fixed paradigm, a deviation of even one volume
        means something went wrong, and the correct response is to say so rather than to quietly decide how much truncation is
        acceptable.

        RESIDUAL GAP: the first subject to run a brand-new task has no registered count. If that subject has >= 2 runs of the
        task, the within-session mode establishes it; with a single run there is nothing to compare, so it is accepted,
        registered, and flagged for review.
      </summary>
      <decision status="decided" chosen="A1">
        LOCKED: a run whose volume count deviates from its task's registered expected count is EXCLUDED from func/, PRESERVED
        (converted NIfTI + sidecar) under sourcedata/, and the exclusion is recorded in scans.tsv and in the conversion report
        with both counts. run- indices are assigned over the SURVIVING runs only. Conversion completes, so unattended HPC
        batches are not blocked. The fragment cannot silently enter preprocessing, and the decision is explicit and auditable
        rather than buried.
      </decision>
    </topic>

    <topic id="T8" title="Validation gate">
      <summary>
        Anchored on the finding that explains why the original bug survived: BIDS-VALIDATOR DOES NOT FLAG A FIELDMAP WITH NO
        IntendedFor. Such a dataset validates completely clean, then runs clean through preprocessing, which simply skips
        distortion correction. That is the exact profile of the presenting complaint. Validation was never going to catch it,
        so the gate cannot rest on bids-validator alone.
      </summary>
      <research>
        R4: bids-validator 2.0 is schema-driven and checks spec compliance only. CuBIDS groups scans into Entity Sets and
        Parameter Groups by acquisition parameters, surfacing heterogeneity and unexpected variants. MRIQC computes IQMs and
        has no built-in pass/fail.
      </research>
      <decision status="decided" chosen="A1">
        LOCKED, three layers with distinct roles:

        1. ENGINE ASSERTIONS (blocking, per-subject; the STRONGEST layer). Opposite PhaseEncodingDirection within a pair;
           fieldmap geometry and EffectiveEchoSpacing matching its targets; every target owning exactly one pair; no orphan
           pairs; label injectivity; no rename collision; exact volume counts; dir- label agreeing with signed
           PhaseEncodingDirection; dcm2niix version at or above the verified floor. These run BEFORE anything is written. No
           general-purpose validator can perform them, because none of them know what these fieldmaps are supposed to correct.
        2. BIDS-VALIDATOR (blocking, per-subject). Spec compliance. Necessary, cheap, and as established, blind to semantic
           emptiness.
        3. CuBIDS (non-blocking, per-cohort review artifact). The tool that WOULD have caught the original bug. Surfaces what
           per-subject checks cannot: a subject whose fieldmap coverage differs from the cohort, two task labels sharing one
           parameter group (the T6 rename case), an acquisition parameter that drifted mid-study. Inherently cohort-level, so
           it is generated after each batch and reviewed, not gated on.

        MRIQC IS OUT OF SCOPE for this module. It measures data QUALITY (motion, SNR, ghosting), not conversion CORRECTNESS.
        Distinct question, distinct remediation. It belongs to fmri-proc-orchestrator or its own module.
      </decision>
    </topic>

    <topic id="T9" title="HPC execution and reproducibility">
      <summary>
        Two structural points.

        ISOLATE, THEN MERGE. The concurrency hazard behind the legacy `rm` (see T1) is fixed architecturally, not by deletion.
        SLURM array tasks convert into PRIVATE STAGING DIRECTORIES with no shared state. A single serial assembly job then
        merges into the BIDS root. scans.tsv is per-session and sessions.tsv is per-subject, so both are naturally isolated;
        only participants.tsv and the dataset-level files need the serial merge, and they UPSERT rather than overwrite. No
        races, no deletions, and the roster accumulates correctly across waves.

        VERSION PINNING IS A SCIENTIFIC DEPENDENCY HERE, NOT AN ENVIRONMENT DETAIL. This entire design rests on dcm2niix
        recovering signed PhaseEncodingDirection from XA enhanced DICOM with no CSA headers. That was verified on
        v1.0.20260416. The capability is VERSION-DEPENDENT: XA support has evolved substantially across dcm2niix releases. An
        older binary on a cluster node could silently emit no PhaseEncodingDirection, at which point every fieldmap association
        we build is unfounded.
      </summary>
      <research>
        R5: Apptainer/Singularity is standard on HPC (no Docker daemon). Nipoppy's manifest ("doughnut") is the reference
        pattern for idempotent re-runs after partial failure.
      </research>
      <decision status="decided" chosen="A1">
        LOCKED:
        - ENVIRONMENT: a single Apptainer container with dcm2niix, bids-validator, and CuBIDS pinned to verified versions. The
          image hash is citable in a methods section, which makes the scientific dependency reproducible rather than ambient.
        - RUNTIME ASSERTION: the engine MUST assert the dcm2niix version at runtime and REFUSE TO PROCEED below the verified
          floor (v1.0.20260416), regardless of how the environment was provisioned.
        - ORCHESTRATION: one SLURM array task per (subject, session), converting into isolated staging, then a single
          `--dependency=afterok` merge job assembling the BIDS root.
        - IDEMPOTENCY: a manifest (Nipoppy "doughnut" pattern) recording per-unit status, so re-runs skip completed work and
          resume cleanly after partial failure.
        - Snakemake and Nextflow were considered and rejected as substantial machinery for what is genuinely a two-stage
          pipeline.
      </decision>
    </topic>

    <topic id="T10" title="PHI and defacing">
      <summary>
        Two independent PHI surfaces requiring OPPOSITE treatments.

        THE SIDECAR SURFACE is free to fix and should be non-negotiable. dcm2niix copies patient identifiers into the JSON
        sidecar by default. This costs nothing to suppress, destroys nothing, and there is no scientific argument against it.

        THE IMAGE SURFACE is the opposite: DEFACING IS DESTRUCTIVE AND NOT SCIENTIFICALLY FREE. Removing facial features
        alters the anatomical volume that FreeSurfer and fMRIPrep register and segment against, with published evidence of
        perturbed cortical thickness estimates and registration quality. The accuracy figures from R6 (pydeface ~83%,
        afni_refacer ~89%, quickshear ~39%) also show defacing is imperfect at its own job.

        THE KEY ASYMMETRY: internal analysis does not require defacing; SHARING does. Defacing the tree that fmri-preproc
        consumes would inject an irreversible, results-altering transformation into the analysis path in order to satisfy a
        sharing requirement that has not yet arrived. That is exactly the class of "trivial" upstream decision with profound
        sequential consequences that must be flagged rather than waved through.
      </summary>
      <research>R6: dataset-level BIDS file requirements; defacing tool accuracy comparison; BIDSonym as a BIDS-native wrapper.</research>
      <decision status="decided" chosen="A1">
        LOCKED:
        - SIDECAR DE-IDENTIFICATION IS ALWAYS APPLIED: dcm2niix `-ba y` PLUS an explicit scrub of residual PHI keys (do not
          trust the flag alone). Non-negotiable, zero cost. The scrub set is the standard person- and site-identifying DICOM
          field set (see the PHI SURFACE note in empirical_findings).
        - THE ANALYSIS TREE KEEPS NATIVE ANATOMICALS. No irreversible, results-altering transform enters the path that
          fmri-preproc consumes.
        - DEFACING IS AN OPT-IN PUBLISHING STEP, emitting `derivatives/defaced/` if and when a data-sharing requirement
          actually arrives. Defacing thereby becomes a publishing concern rather than a preprocessing one, and the choice of
          defacing tool can be revisited later without re-running conversion.
      </decision>
    </topic>

    <topic id="T11" title="Physiological recordings">
      <summary>
        Six PhysioLog series (one per functional run) are silently skipped by dcm2niix and therefore currently discarded. The
        user elected to extract them. Per the pre-report audit rule, XA30 support was VERIFIED EMPIRICALLY before being written
        into this spec rather than assumed from documentation. It verified cleanly: the payload is plain ASCII CMRR logs
        (LogVersion = EJA_1), and XA30 did not change the encoding. Extraction requires a parser for a documented ASCII format,
        not vendor reverse-engineering. See the PHYSIO PAYLOAD block in empirical_findings for the full structure.
      </summary>
      <decision status="decided" chosen="A1">
        LOCKED: extract to BIDS `_physio.tsv.gz` + `_physio.json` alongside each functional run.

        SPECIFICATION:
        - Parse the length-prefixed container in DICOM private element (7fe1,1010) into its five ASCII blocks: ECG, PULS, RESP,
          EXT, Info.
        - COLUMNS: PULS -> `cardiac`, RESP -> `respiratory` (the BIDS-named conventions). ECG and EXT are NOT written to the
          BIDS tree: ECG was pinned flat across all four leads (no electrodes attached) and EXT is a trigger line, so including
          them would ship constant, non-physiological data that could mislead a downstream user into believing ECG was
          recorded. The raw multi-channel log is PRESERVED under sourcedata/ so ECG remains recoverable if a future session
          actually attaches electrodes. This is consistent with how the ND anatomical (T3) and truncated runs (T7) are handled.
        - SamplingFrequency = 1 / (SampleTime x 2.5 ms). SampleTime = 2 on PULS / RESP -> 200 Hz.
        - StartTime is computed from the ACQUISITION_INFO block's volume-0 ACQ_START_TICS, relative to the associated run.
        - PHYSIO-TO-BOLD ASSOCIATION uses the SAME physics-guard pattern as the fieldmap mapping: temporal adjacency, CONFIRMED
          by an independent geometry match against ACQUISITION_INFO's NumVolumes and NumSlices. No name matching anywhere.
      </decision>
    </topic>

  </topics>

  <action_items>
    <item priority="P0" target_mode="implement" description="Build the dcm2niix-first conversion engine per T2-T11. Six stages: dcm2niix staging; physics-driven sidecar classification; temporal fieldmap and physio mapping; BIDS assembly with upsert; dual IntendedFor + B0Field* rendering; validation gate. Engine contains NO study-specific vocabulary. Per-study artifact is the declarative YAML in T6." />
    <item priority="P0" target_mode="implement" description="Implement every guard as a hard failure, not a warning: PE opposition within a pair; fieldmap geometry/EES matching targets; no orphan pairs; every target owns exactly one pair; label injectivity; non-empty labels; rename detection; exact volume counts; dir- label agreeing with signed PhaseEncodingDirection; dcm2niix version floor (v1.0.20260416). These guards ARE the refactor; the legacy pipeline failed because none of them existed." />
    <item priority="P0" target_mode="implement" description="Implement the PHI scrub (T10): dcm2niix -ba y plus an explicit residual-key scrub of the standard person- and site-identifying DICOM field set. No identifier of any kind may reach the BIDS tree, the sidecars, or any log or report the engine emits." />
    <item priority="P0" target_mode="other" description="OUTSIDE THIS SKILL (brainstorm is read-only): fix the latent ordering bug in  Step 7 clears the mode state BEFORE step 8 writes the session memory, which drops filesystem enforcement to the orchestrator policy and blocks the write. Swap steps 7 and 8 so the session memory is written while the mode is still active. User approved this fix; it could not be applied from within brainstorm." />
    <item priority="P1" target_mode="test" description="Design the test suite. Brainstorm does not design tests (user directive). Note the architectural payoff available to /test: because the engine classifies from SIDECARS rather than DICOMs, its entire decision logic is testable with small, FULLY SYNTHETIC JSON fixtures, with no real DICOM data in a repository. The adversarial cases matter most: every guard listed above must be PROVEN TO FIRE, since a guard that never fires in a test is indistinguishable from a guard that does not work." />
    <item priority="P1" target_mode="implement" description="Implement the CMRR physio parser per T11. Verified format: length-prefixed ASCII container in (7fe1,1010), five blocks, LogVersion = EJA_1." />
    <item priority="P2" target_mode="implement" description="Implement the opt-in derivatives/defaced/ publishing stage (T10). Not required for the analysis path; needed only if a data-sharing requirement arrives." />
    <item priority="P2" target_mode="other" description="Surfaced, and the user has ruled it OUT OF SCOPE for this project: fmri-preproc's example_config.yaml (lines 76-77, 87) states required acquisition fields as (total_readout_time, phase_encoding_direction, echo_spacing) and exposes total_readout_time, but bids_input.py's REQUIRED_ACQ_PARAMS is (repetition_time, phase_encoding_direction, echo_spacing) and never reads total_readout_time (layer1_minproc derives it internally). Recorded so the drift is not lost, per the user's explicit scope call to ignore it here. fmri-bids-recon proceeds on what bids_input.py actually enforces." />
  </action_items>

  <next_steps>
    Proceed to /implement (plan phase). This report is a complete, locked specification: every decision was explicitly approved
    by the user, no unapproved assumptions remain, and the one pending verification (XA30 physio encoding) was closed
    empirically before the report was written. /implement does not verify or research; it builds from the spec, and the spec is
    ready.

    Two items must be handled OUTSIDE /implement:
      - The new-project SKILL.md ordering fix (P0) requires a write to the skill framework and cannot be performed from a
        read-only skill.
      - Test design belongs to /test, per the user's directive that brainstorm does not design tests. Recommended sequencing is
        /test design BEFORE /implement build, consistent with the standing preference that no code change goes untested and
        that the suite is designed prior to a refactor.
  </next_steps>
</brainstorm_report>
