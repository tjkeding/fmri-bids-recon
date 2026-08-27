<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-07-16T12:00:00-05:00" />
  <context_files>
    <file path="bids_recon/config.py" relevance="StudyConfig dataclass and cross-product expansion logic; generation script must produce config-compatible directory structure" />
    <file path="bids_recon/__main__.py" relevance="Pipeline entry point; 7-phase linear flow; exit codes 0/1/2/3/4" />
    <file path="bids_recon/stage1_convert.py" relevance="dcm2niix conversion; BIDS-level simulation bypasses this stage" />
    <file path="bids_recon/stage4_assemble.py" relevance="SIDECAR_DENY_LIST, sessions.tsv/scans.tsv generation, PatientID cross-check" />
    <file path="bids_recon/labels.py" relevance="Task label derivation, collision/drift/rename guards; adversaries A3, A5 target this module" />
    <file path="bids_recon/errors.py" relevance="Error hierarchy (GuardError, ConfigError, SpecFinding, etc.); adversaries must trigger specific error types" />
    <file path="bids_recon/stage3_map.py" relevance="Fieldmap pairing and mapping; adversaries A13, A22, A23 target this module" />
  </context_files>

  <research>
    <agent id="R1" topic="Synthetic DICOM generation tools">
      No turnkey tool exists for generating Siemens XA30 synthetic DICOMs with the full private-tag complement needed by dcm2niix. XA30 Enhanced DICOMs require multi-frame structure with SharedFunctionalGroupsSequence, PerFrameFunctionalGroupsSequence, and private tags (0021,1104), (0021,1106), (0021,1009), (0021,111C). The practical approach would be pydicom-based construction using dcm_qa_xa30 reference files as templates, but the implementation cost is prohibitive relative to testing value. (Sources: dcm2niix documentation, pydicom API, dcm_qa_xa30 repository)
    </agent>

    <agent id="R2" topic="Synthetic MRI voxel data approaches">
      Consensus across nilearn, nibabel, and DIPY: random-noise numpy arrays wrapped in Nifti1Image with explicitly set affine, sform/qform codes, and pixdim fields are the standard fixture for pipeline-logic testing. Shepp-Logan phantoms, BrainWeb tissue simulators, and GAN/diffusion-model approaches optimize for image-content realism irrelevant to structural/format validity testing. Critical header fields: sform_code, qform_code, pixdim, and 4th-dimension length. (Sources: nilearn _utils/data_gen.py; nibabel documentation nipy.org/nibabel; Gach et al. 2008 IEEE EMBC; BrainWeb McConnell Brain Imaging Centre; DIPY gradient_table documentation; Kouw and Loog 2021 Medical Image Analysis)
    </agent>

    <agent id="R3" topic="Common BIDS validation failures">
      Most frequent real-world validation errors: NOT_INCLUDED (25.9% of 548 OpenNeuro datasets), REPETITION_TIME_MISMATCH (NIfTI header vs JSON sidecar), SIDECAR_KEY_REQUIRED for TaskName, SLICE_TIMING_NOT_DEFINED and SliceTiming-exceeds-RepetitionTime (ms vs s unit confusion), TSV_VALUE_INCORRECT_TYPE (locale-driven decimal separators). CuBIDS (Cieslak et al. 2022) documented hidden acquisition parameter heterogeneity passing validation but producing inconsistent preprocessing. BIDS Validator 2.0 (Nov 2024) introduced systematic type-checking generating new warnings for absent RECOMMENDED fields. (Sources: EEGDash/OpenNeuro audit arXiv:2606.16041; bids-validator issue #776; NeuroStars community; CuBIDS doi:10.1016/j.neuroimage.2022.119609; BIDS Validator 2.0 blog)
    </agent>

    <agent id="R4" topic="Downstream preprocessing crash modes">
      Dominant failure categories: (1) missing PhaseEncodingDirection causes silent SDC skip or ValueError; (2) DatasetType=derivative causes silent SDC bypass; (3) non-session-specific B0FieldIdentifier causes cross-session fieldmap pairing crash; (4) missing SliceTiming causes silent skip, out-of-range values cause 3dTshift crash; (5) QSIPrep does not support BIDS inheritance for bval/bvec or BIDS-URI for IntendedFor; (6) RepetitionTime mismatch between pixdim4 and sidecar affects tools differently (fMRIPrep reads sidecar, others read header); (7) reverse-PE DWI in dwi/ instead of fmap/ causes silent concatenation. (Sources: NeuroStars threads; QSIPrep documentation; fMRIPrep changelogs; SDCFlows changelogs)
    </agent>

    <agent id="R5" topic="Fieldmap specification edge cases">
      Key findings: (1) B0FieldIdentifier/B0FieldSource introduced in BIDS v1.7 as IntendedFor replacement; specification recommends using both simultaneously for compatibility; (2) SDCFlows <2.0.11 collapsed multiple PEPolar pairs into one estimator (silent misassociation); (3) SDCFlows <2.5.0 pooled PEPolar fieldmaps with differing IntendedFor lists; (4) IntendedFor path format inconsistency (subject-relative vs dataset-relative) caused silent failures through SDCFlows 2.8.1; (5) PhaseEncodingDirection and TotalReadoutTime are REQUIRED but mismatch between fieldmap and target is not validator-blocked; (6) fMRIPrep historically treated IntendedFor inconsistently across fieldmap types. (Sources: BIDS Specification stable; SDCFlows changelogs 2.0.9-2.8.1; fMRIPrep 23.1.3 changelog; fMRIPrep issue #2628)
    </agent>

    <agent id="R6" topic="NIfTI header and JSON sidecar structural edge cases">
      Key findings: (1) qform/sform disagreement causes tool-dependent spatial reference divergence (ANTs uses qform, nibabel prefers sform); (2) both xform codes = 0 causes fslreorient2std failure, FreeSurfer orientation unknown; (3) oblique acquisitions cause alignment failures in AFNI-based workflows; (4) scl_slope=0 treated as undefined, scl_slope=NaN means consumed; (5) dcm2niix can produce invalid UTF-8 in JSON sidecars from vendor-private DICOM tags; (6) RepetitionTime mismatch (pixdim4 vs JSON) has asymmetric downstream impact; (7) INT16/UINT16 mixed within session when intensities straddle 32767 boundary. (Sources: NeuroStars discussions; fMRIPrep issues; nibabel issue #1015; dcm2niix issue #476; ANTsPy issue #173)
    </agent>

    <agent id="R7" topic="Longitudinal study data management failures">
      Key findings: (1) Siemens XA30 upgrades introduce breaking DICOM tag changes (DwellTime lost, SequenceName renamed to PulseSequenceName, InversionTime to InversionTimes); (2) protocol non-compliance is pervasive: mrQA detected deviations in TR, TE, FlipAngle, PhaseEncodingDirection across 20+ datasets including ABCD; (3) scanner hardware upgrades (Trio-to-Prisma) introduce systematic bias in cortical/subcortical measures (Kaufmann et al. 2021); (4) head coil changes introduce 6-9% volume bias and up to 27.5% connectivity measure bias; (5) ADNI developed phantom-based gradient drift monitoring for post-hoc correction; (6) non-biological variance affects up to 50% of ABCD scans. Session mislabeling and participant re-enrollment under different IDs are likely underreported. (Sources: dcm2niix issue #538; Sinha et al. 2024 Neuroinformatics; Casey et al. 2018 bioRxiv; Kaufmann et al. 2021 NeuroImage; PMC6648353; Jack et al. 2008 JMRI; ABCD reliability study bioRxiv 2024)
    </agent>

    <agent id="R8" topic="Scanner console and technologist errors">
      Key findings: (1) incorrect patient registration propagates into PatientName/PatientID/PatientBirthDate tags; modality worklist bypass or wrong worklist selection; (2) protocol non-compliance from manual console overrides (FOV, slice count, TR/TE, flip angle, PE direction) detected by mrQA in ABCD; (3) aborted sequences retain complete SeriesUID and SeriesDescription, differing only in image count; (4) repeated scouts produce multiple series with identical descriptions causing classification ambiguity; (5) coil configuration errors stored in private CSA headers (0029,1020 CoilString), invisible to standard-tag-only tools; (6) patient positioning errors (HFS vs FFS) flip Z-axis in ImageOrientationPatient; (7) AutoAlign failure requires manual slice positioning, introducing inter-session orientation variability; (8) wrong body part/non-brain protocol produces unrecognized SeriesDescription. (Sources: Sinha et al. 2024; ABCD QC documentation; BIDScoin documentation; BIDS discussion groups; Siemens AutoAlign documentation; DICOM Standard)
    </agent>

    <agent id="R9" topic="Post-acquisition raw data handling errors">
      Key findings: (1) incomplete DICOM transfers with silent rejection (AE Title/port mismatch); (2) partial series from manual scan halt cause dcm2niix to split output, crashing HeuDiConv; (3) subject ID labeling errors discovered in widely-used public datasets (same subject mislabeled as different, or different subjects labeled as same); (4) ABCD reprocessed 861 cases due to duplicate functional runs; (5) incomplete anonymization corrupts required DICOM tags (StudyInstanceUID, SeriesInstanceUID, FrameOfReferenceUID), breaking series grouping; (6) metadata inconsistency across sessions (wrong tracer, PE direction, institution name) passes format validation; (7) storage migration strips private tags, losing acquisition parameters for sidecar generation; (8) UK Biobank reported 104 subjects missing at least one expected series. (Sources: MedIAI Blog; HeuDiConv issue #814; arXiv:2110.04055; ABCD documentation; arXiv:2410.12402; Frontiers in Neuroscience PMC8081968; arXiv:2007.01251)
    </agent>
  </research>

  <topics>
    <topic id="T1" title="Simulation Approach">
      <summary>BIDS-level simulation (constructing NIfTI + JSON sidecar pairs directly with nibabel and json) rather than DICOM-level simulation (constructing synthetic DICOMs to feed through dcm2niix). This bypasses stage 1 (convert) but exercises stages 2-8 where the pipeline's value-add and bug surface area reside.</summary>
      <research>R1 found no turnkey tool for Siemens XA30 synthetic DICOMs. R2 confirmed nibabel + numpy random arrays are the standard pipeline-logic testing fixture across nilearn, DIPY, and fMRIPrep test suites.</research>
      <approaches>
        <approach id="A1" label="BIDS-level" feasibility="high" risk="low">
          <description>Construct NIfTI files with nibabel (numpy arrays + affine) and JSON sidecars with json.dumps. All parameters explicit and controllable.</description>
          <pros>Low implementation complexity; stable against dcm2niix updates; established pattern in the field; all downstream pipeline guards exercisable</pros>
          <cons>Stage 1 (dcm2niix conversion) untested; cannot test DICOM-specific edge cases</cons>
        </approach>
        <approach id="A2" label="DICOM-level" feasibility="low" risk="high">
          <description>Construct synthetic Siemens XA30 Enhanced DICOMs with pydicom, including multi-frame structure and vendor-private tags, then convert through dcm2niix.</description>
          <pros>Full pipeline coverage including stage 1; tests dcm2niix edge cases</pros>
          <cons>Very high implementation complexity; brittle to dcm2niix updates; no existing tooling; vendor-private tag structure underdocumented</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">BIDS-level simulation. Stage 1 coverage can be addressed separately using dcm_qa_xa30 reference DICOMs if needed.</decision>
    </topic>

    <topic id="T2" title="Dataset Composition">
      <summary>10 subjects (sub-001 through sub-010), 3 sessions (ses-01, ses-02, ses-03), yielding N=30 subject-sessions suitable for small-scale longitudinal mixed-effects models. 1 clean subject, 9 adversarial subjects with graded severity.</summary>
      <research>N/A (design decision based on statistical and practical requirements)</research>
      <approaches>
        <approach id="A1" label="10x3 with severity gradient" feasibility="high" risk="low">
          <description>10 subjects, 3 sessions. 1 clean subject as regression baseline. 9 adversarial subjects with 1-2 minor issues through 5+ major issues, mixing adversary types within subjects.</description>
          <pros>N=30 supports random intercepts/slopes with 3 timepoints; 3 sessions tests longitudinal registry guards; severity gradient creates diagnostic spectrum; cross-project reuse value</pros>
          <cons>~70-90 GB disk footprint at full dimensions</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        10x3 design with severity gradient. Modality inventory per clean subject-session (verified against pipeline output):
        - anat: T1w (1), T2w (1)
        - func: BOLD rest (3 runs, each with sbref), BOLD emotionalnback (2 runs, each with sbref)
        - dwi: 1 dwi run (with bval/bvec) + 3 sbref files
        - fmap: acq-func 2 AP/PA pairs, acq-dwi 1 AP/PA pair
        Total: 24 NIfTI files per clean subject-session.
        Voxel fill: structured noise (low-frequency spatial gradient + Gaussian noise) for compressible but non-trivial data.
      </decision>
    </topic>

    <topic id="T3" title="Adversarial Taxonomy">
      <summary>28 atomic adversary types (A1-A28) derived from first-principles analysis plus systematic literature review across 7 research topics (R3-R9). Adversaries are mixed within subjects with a severity gradient ranging from 1 minor issue to 5+ major issues.</summary>
      <research>R3-R9 collectively identified 13 additional adversary types beyond the initial 15, covering BIDS validation failures, downstream preprocessing crash modes, fieldmap association edge cases, NIfTI header anomalies, longitudinal data management failures, scanner console errors, and post-acquisition data handling errors.</research>
      <approaches>
        <approach id="A1" label="28-type mixed-severity pool" feasibility="high" risk="low">
          <description>
            28 atomic adversary types distributed across 9 adversarial subjects with increasing density:

            Session-level (2):
            - A1: Missing session (DICOM path absent for one session)
            - A2: Empty session (DICOM path exists, zero convertible series)

            Human-centric series-level (6):
            - A3: Protocol typo (STUDY_rset_bold instead of STUDY_rest_bold)
            - A4: Scan restart (truncated run + complete re-acquisition)
            - A5: Protocol rename across sessions (STUDY_faces_bold to STUDY_emotion_bold)
            - A6: Mixed PatientIDs within a session
            - A7: Stale unreplaced scan from prior subject
            - A8: Wrong acquisition parameters (MB=4 instead of MB=6)

            Computational format/structure (7):
            - A9: Missing optional modality (no T2w or no DWI)
            - A10: Missing sidecar field (EffectiveEchoSpacing absent)
            - A11: Surviving PHI field (InstitutionName in BIDS sidecar)
            - A12: bval/bvec dimension mismatch (102 bvals, 103 bvecs)
            - A13: Geometry mismatch (fmap voxel size differs from target BOLD)
            - A14: SBRef orphan (no matching BOLD run)
            - A15: Duplicate sidecar key casing (RepetitionTime and repetitiontime)

            NIfTI header anomalies (4):
            - A16: RepetitionTime NIfTI/JSON mismatch (pixdim4 disagrees with sidecar)
            - A17: qform/sform disagreement (different affine transforms)
            - A18: scl_slope anomaly (set to 0 or NaN)
            - A19: Mixed data types across runs (INT16 vs FLOAT32)

            Sidecar/metadata anomalies (4):
            - A20: SliceTiming wrong units (milliseconds instead of seconds)
            - A21: TaskName missing from JSON sidecar
            - A22: IntendedFor path format error (dataset-relative instead of subject-relative)
            - A23: TotalReadoutTime mismatch between fieldmap and target

            Longitudinal/cross-session (2):
            - A24: Protocol parameter drift (small TR change across sessions)
            - A25: Duplicate functional run (repeated export)

            Acquisition-level BIDS manifestation (3):
            - A26: Patient positioning error (FFS orientation, flipped Z-axis)
            - A27: Repeated scout/localizer series
            - A28: Locale decimal separator in participants.tsv

            Severity gradient tiers:
            - Clean: 1 subject (0 adversaries)
            - Mild: 2-3 subjects (1-2 minor)
            - Moderate: 2-3 subjects (2-4 mixed, including session-level)
            - Severe: 2-3 subjects (4+ including session-level + human-centric + computational)

            Each adversary appears at least once across the full dataset; no two subjects share the identical adversary combination. Per-subject assignment deferred to implementation planning.
          </description>
          <pros>Comprehensive coverage of documented failure modes; severity gradient enables diagnostic isolation; mixed adversaries per subject test interaction effects; research-grounded in empirical failure patterns from ABCD, OpenNeuro, CuBIDS, and tool-specific issue trackers</pros>
          <cons>28 types is a large pool; per-subject assignment requires careful balancing during implementation; some adversaries (A22, A23) target fieldmap logic that may interact unpredictably when co-occurring</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">28-type mixed-severity pool with per-subject assignment deferred to implementation planning.</decision>
    </topic>

    <topic id="T4" title="Synthetic Demographics">
      <summary>Fabricated participant metadata for participants.tsv with uniform distributions across sex, handedness, and age.</summary>
      <research>N/A (design decision; no participant information from real data used)</research>
      <approaches>
        <approach id="A1" label="Uniform demographics, no group" feasibility="high" risk="low">
          <description>
            - participant_id: sub-001 through sub-010
            - age: uniform distribution 9-16 years; baseline (ses-01) ages ~9-12, ~2-year inter-session intervals, so ses-03 ages reach ~13-16; full 9-16 range covered across the dataset
            - sex: uniform (5M/5F)
            - handedness: uniform (~3-4 per category across R/L/A)
            - No group variable
            - No adversarial content in demographics (A28 locale error targets TSV formatting, not demographic values)
          </description>
          <pros>Simple; supports sex/handedness-stratified analyses; age range appropriate for developmental neuroimaging (ABCD-adjacent); no unnecessary complexity</pros>
          <cons>Uniform distributions are unrealistic for population sampling (real cohorts skew); acceptable for pipeline testing where demographic realism is not the test criterion</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Uniform demographics with no group variable. Age range 9-16 across all sessions.</decision>
    </topic>

    <topic id="T5" title="Storage Location, Dataset Size, and Packaging">
      <summary>Dataset stored at ~/simulated-bids-dataset/ for cross-project reuse. Full acquisition dimensions with structured noise fill (~70-90 GB estimated). Generation script parameterized by output directory with clean baseline generated once and adversarial modifications applied as copy-then-mutate.</summary>
      <research>R2 confirmed that pipeline logic testing depends on header fields and dimensional contracts, not voxel content. Structured noise (low-frequency gradient + Gaussian) chosen as compromise between compressibility and non-triviality.</research>
      <approaches>
        <approach id="A1" label="Full dimensions, structured noise, ~/simulated-bids-dataset/" feasibility="high" risk="low">
          <description>
            - Output path: ~/simulated-bids-dataset/
            - Full acquisition dimensions (verified from RAW_TEST_SUBJ_1 pipeline output):
              - T1w/T2w: 176x256x256, 1mm isotropic
              - BOLD: 90x90x60, 2.4mm, TR=0.8s, rest=383 vols, enback=370 vols
              - DWI: 140x140x81, 1.7mm, TR=4.2s, 103 vols
            - Voxel fill: structured noise (low-frequency spatial gradient + Gaussian noise)
            - Estimated disk footprint: ~70-90 GB (structured noise compresses ~30-50% under gzip)
            - Available disk space: 427 GB (21-25% consumption)
            - Generation script accepts output directory argument
            - Clean baseline generated once; adversarial modifications applied as separate copy-then-mutate layer
          </description>
          <pros>Full-size data exercises minimum-dimension requirements in downstream tools; immediately usable for benchmarking runtime performance; cross-project reuse value; structured noise compresses well while avoiding constant-value rejection</pros>
          <cons>~70-90 GB is substantial; generation time ~30-60 min; each full regeneration costs the same (mitigated by copy-then-mutate layer)</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">Full dimensions at ~/simulated-bids-dataset/ with structured noise fill.</decision>
    </topic>
  </topics>

  <action_items>
    <item priority="P0" target_mode="implement" description="Build the BIDS dataset generation script: Python script using nibabel, numpy, and json to construct the complete simulated dataset at ~/simulated-bids-dataset/ per the locked T1-T5 specifications. The script must: (1) generate clean baseline data for sub-001 across all 3 sessions with the full modality inventory; (2) generate 9 adversarial subjects with mixed adversary types per the A1-A28 pool and severity gradient; (3) generate dataset_description.json, participants.tsv, sessions.tsv, and scans.tsv; (4) use structured noise (low-frequency spatial gradient + Gaussian) for voxel fill; (5) sample acquisition parameters from real data distribution moments (not copy verbatim); (6) accept output directory as CLI argument; (7) separate clean baseline generation from adversarial mutation layer." />
    <item priority="P0" target_mode="implement" description="Design the per-subject adversary assignment matrix: map each of the 28 adversary types (A1-A28) to specific subject-session slots, ensuring (a) every type appears at least once, (b) no two subjects share identical adversary combinations, (c) severity gradient from mild (1-2 adversaries) to severe (5+), (d) session-level adversaries (A1, A2) are distributed across different subjects." />
    <item priority="P1" target_mode="test" description="Validate the generated dataset: run bids-validator-deno against the clean subject to confirm zero errors; run it against each adversarial subject to confirm that expected validation errors/warnings are triggered by the intended adversaries and no unexpected errors appear." />
    <item priority="P1" target_mode="implement" description="Create a dataset manifest/README documenting: which adversary types are present in each subject-session, expected pipeline behavior per adversary, and the parameter distributions used for sampling." />
    <item priority="P2" target_mode="test" description="Run the bids-recon pipeline against the clean subject to confirm it produces the expected BIDS output structure with zero errors and only expected warnings." />
  </action_items>

  <next_steps>Recommended: /implement to build the generation script and adversary assignment matrix. The P0 items (generation script + assignment matrix) should be implemented together as a single coordinated change, since the assignment matrix drives the script's adversarial mutation logic.</next_steps>
</brainstorm_report>
