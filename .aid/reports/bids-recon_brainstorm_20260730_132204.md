<brainstorm_report>
  <meta project="bids-recon" mode="brainstorm" timestamp="2026-07-30T13:22:04Z" />
  <context_files>
    <file path="tools/simulated_bids/noise.py" relevance="Current noise generation (gradient + Gaussian); root cause of pipeline failures; to be replaced by tissue-based synthesis" />
    <file path="tools/simulated_bids/modalities.py" relevance="Per-modality generators calling noise functions; call sites to be updated" />
    <file path="tools/simulated_bids/config.py" relevance="Scanner constants, acquisition parameters, demographics, profiles; to be extended with tissue intensity tables" />
    <file path="tools/simulated_bids/adversaries.py" relevance="Post-hoc adversary mutations; confirmed unchanged by this redesign" />
    <file path="tools/simulated_bids/scaffold.py" relevance="BIDS metadata generation; confirmed unchanged by this redesign" />
  </context_files>
  <topics>
    <topic id="T1" title="Template/Phantom Source Selection">
      <summary>Selected BrainWeb Simulated Brain Database as the geometric foundation for tissue-based synthesis. BrainWeb provides a 12-class discrete anatomical model (Background, CSF, Grey Matter, White Matter, Fat, Muscle, Muscle/Skin, Skull, Vessels, Connective Tissue, Dura Mater, Bone Marrow) at 1mm isotropic resolution (181x217x181 voxels). Maps are in native template space; per-subject random affine perturbations place each subject in a unique native space, and the preprocessing pipeline handles normalization to standard space.</summary>
      <research>BrainWeb (Collins et al., 1998; Aubert-Broche et al., 2006) is the standard simulated brain phantom for MRI validation. Five sources were evaluated: BrainWeb, MNI152, FreeSurfer fsaverage, Harvard-Oxford atlas, and procedural generation. BrainWeb was selected for its 12-class tissue coverage (including skull and extracranial tissues needed for skull-stripping and segmentation testing), citation-only licensing, and established use in MRI simulation validation studies.</research>
      <approaches>
        <approach id="A1" label="BrainWeb 12-class discrete model" feasibility="high" risk="low">
          <description>Download the BrainWeb crisp discrete anatomical model. Use 12 tissue class labels as the spatial template for all modality synthesis. Apply per-subject affine perturbations and nearest-neighbor resampling to target modality resolutions.</description>
          <pros>12-class coverage including extracranial structures; 1mm isotropic resolution sufficient for all target modalities; well-validated in MRI simulation literature; citation-only licensing</pros>
          <cons>Single template anatomy (all subjects share the same morphology before perturbation); fixed to adult brain morphology (ABCD is pediatric/adolescent)</cons>
        </approach>
        <approach id="A2" label="Procedural volumetric generation" feasibility="low" risk="high">
          <description>Generate tissue-like spatial structure procedurally using Perlin noise, ellipsoid masks, or similar computational geometry.</description>
          <pros>No external dependency; unlimited variation across subjects</pros>
          <cons>Cannot produce anatomically plausible sulcal folding, ventricle geometry, or tissue boundary topology; segmentation and registration tools would fail on non-anatomical geometry</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">BrainWeb 12-class discrete model selected. The single-template limitation is acceptable because (a) the simulation's purpose is pipeline validation, not population-level anatomical variability studies, and (b) per-subject affine perturbations provide sufficient geometric diversity for registration testing.</decision>
    </topic>

    <topic id="T2" title="Modality-Specific Signal Synthesis">
      <summary>Comprehensive tissue-based signal model replacing the gradient+Gaussian noise generator. The model synthesizes per-voxel intensity from tissue class labels using modality-appropriate signal equations, adds physically motivated artifacts (B1 bias, B0 distortion, motion, slice-timing offsets, signal spikes, NSS transient), and includes anti-inverse-crime mechanisms (voxel-varying HRF, AR(1) noise, spatially heterogeneous activation) to prevent unrealistically perfect pipeline reconstruction.</summary>
      <research>The signal model draws on standard MRI physics (Bernstein et al., 2004; Haacke et al., 1999) for per-tissue intensity mapping, Rician noise (Gudbjartsson &amp; Patz, 1995), and B1 inhomogeneity modeling. The anti-inverse-crime framework is grounded in the inverse problems literature (Kaipio &amp; Somersalo, 2005; Colton &amp; Kress, 2013), where using the same forward model for both simulation and reconstruction yields artificially perfect results. The ABCD emotional n-back task structure follows Casey et al. (2018) and Barch et al. (2013). The spatial-component FC model follows the ICA-based network decomposition framework (Beckmann et al., 2005; Smith et al., 2009).</research>
      <approaches>
        <approach id="A1" label="Full tissue-based synthesis with anti-inverse-crime" feasibility="high" risk="low">
          <description>Complete signal model with 17 components as specified below.</description>
          <pros>Exercises every preprocessing stage; prevents inverse crime; produces realistic contrast maps and temporal dynamics</pros>
          <cons>Increased computational cost relative to noise-only generation; more complex codebase</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        Full tissue-based synthesis model with the following 17 locked components:

        SPATIAL FOUNDATION:
        1. BrainWeb 12-class label map as geometric template
        2. Per-subject random affine perturbations for native space (rigid-body: rotation +/-15 deg, translation +/-20 mm per session; between-run offsets: +/-3 deg, +/-5 mm)

        NOISE MODEL:
        3. Rician noise (magnitude of complex Gaussian, matching MRI physics)
        4. AR(1) temporally autocorrelated noise (phi ~0.3-0.5) [anti-inverse-crime mechanism]

        STRUCTURAL MODALITIES (T1w, T2w):
        Per-tissue-class intensity mapping from label map. B1 multiplicative bias field (smooth spatial inhomogeneity).

        BOLD (REST + TASK):
        5. Both resting-state (383 volumes, 2 runs) and task BOLD (370 volumes, 2 runs)
        6. ABCD emotional n-back task simulation: 8 blocks/run (2 conditions x 4 stimulus categories), alternating 0-back/2-back, 27.5s blocks (2.5s cue + 10 trials x 2.5s), seeded pseudo-random block order
        7. Events.tsv generation for EN-back (onset, duration, trial_type columns)
        8. Per-volume rigid-body motion perturbations (within-run jitter)
        9. Per-run baseline position offsets (between-scan motion for L1.4)
        10. B1 multiplicative bias field
        11. Voxel-varying HRF (time-to-peak ~5.5s SD~0.5s, undershoot ratio ~0.35 SD~0.1) [anti-inverse-crime mechanism]
        12. Spatially heterogeneous activation (20-40% of GM voxels, 0.5-2.0% signal change) [anti-inverse-crime mechanism]
        13. Condition-graded activation maps: 50% overlap within same memory load, 30% across loads; 2-back signal change > 0-back
        14. Spatial-component FC model (N=5-7 independent networks, bandpass 0.01-0.1 Hz) for both rest and task BOLD
        15. Slice-timing offset in voxel data (per-MB-group acquisition time, exercises F0 STC)
        16. B0-induced geometric distortion in EPI data (voxel displacement along PE direction, exercises L1.2a/b TOPUP)
        17. Signal spikes/temporal outliers (~1-3% of volumes, exercises Dx Despike)
        18. NSS leading transient (A~0.1-0.2, tau~2-3 volumes, exponential decay; exercises L0.1, F1, F6)
        19. Linear drift

        FULL BOLD SIGNAL MODEL:
        S(v,t) = [S_tissue(v) * (1 + task_response(v,t) + network_signal(v,t) + drift(t)) * B1(v) * NSS(t)] + rician_noise(v,t)
        where task_response includes per-condition activation modulated by voxel-varying HRF convolution with block timecourse.

        DWI:
        20. Isotropic ADC per tissue class (WM ~0.7e-3, GM ~0.8e-3, CSF ~3.0e-3 mm2/s)
        Signal: S(b) = S0_tissue * exp(-b * ADC_tissue) + Rician noise
        Anisotropic diffusion tensor deferred.

        FIELDMAP EPI:
        B0 distortion applied with opposite polarity for AP/PA pair (TOPUP estimation target).

        PIPELINE COVERAGE VERIFICATION:
        All preprocessing stages verified against fmri-preproc pipeline (pipeline.py, layer1_minproc.py, layer2_cloudpipe.py):
        - L0.1 NSS detection: NSS transient (item 18)
        - L1.1 Within-scan motion: per-volume motion (item 8)
        - L1.2a/b TOPUP SDC: B0 distortion (item 16)
        - L1.3a/b GradUnwarp: optional/config-gated, no simulation needed
        - L1.4 Between-scan motion: per-run baseline offsets (item 9)
        - M1 Echo combination: single-echo passthrough (E=1)
        - L1.5 fMRI-to-T1w: tissue contrast at both resolutions
        - S1a-S1e FastSurfer: T1w tissue contrast + skull boundary
        - S2 T1w-to-MNI: native-space anatomy + per-subject perturbation
        - S3 BOLD-to-T1w: BOLD tissue contrast + T1w anatomy
        - Dx Despike: signal spikes (item 17)
        - F0 STC: slice-timing offsets (item 15)
        - F1 BOLD reference: NSS frames (item 18)
        - F2-F5 Warp + mask: composite warp from S2/S3
        - F6 Confounds: motion params, tissue masks, WM/CSF signal, NSS indicators, drift
        - F7 QC: tSNR, FD, enorm
      </decision>
    </topic>

    <topic id="T3" title="Integration Architecture">
      <summary>Retrofit plan for integrating tissue-based synthesis into the existing simulated BIDS generator. Three new modules replace/supplement the noise generator. The adversary system and scaffold are unchanged. BrainWeb label map is downloaded and stored locally.</summary>
      <research>Architecture analysis grounded in direct reading of the existing generator codebase (noise.py, modalities.py, config.py, adversaries.py, scaffold.py) and the downstream fmri-preproc pipeline (pipeline.py, layer1_minproc.py, layer2_cloudpipe.py).</research>
      <approaches>
        <approach id="A1" label="Three-module split with thin orchestrator" feasibility="high" risk="low">
          <description>Replace noise.py with tissue.py (label map I/O, affine perturbation, resampling, per-tissue intensity, B1, Rician noise). Add bold_signal.py (full BOLD temporal chain: NSS, motion, STC, B0, spikes, HRF convolution, task modulation, FC networks, drift, AR(1)). Add events.py (ABCD EN-back timing, events.tsv generation). modalities.py becomes a thin orchestrator calling tissue/bold_signal functions and writing NIfTI + JSON.</description>
          <pros>Clean separation of spatial (tissue.py) and temporal (bold_signal.py) concerns; events.py isolates task-specific logic; modalities.py remains the single entry point for each modality; adversary system completely transparent to the change</pros>
          <cons>Three new files increases module count; bold_signal.py may be large given the number of temporal components</cons>
        </approach>
      </approaches>
      <decision status="decided" chosen="A1">
        Three-module split with the following locked specifications:

        BRAINWEB LABEL MAP:
        - Download BrainWeb discrete anatomical model, store at tools/simulated_bids/data/
        - Format conversion to NIfTI if needed (BrainWeb distributes MINC or raw binary)
        - Citation attribution in tissue.py header

        MODULE STRUCTURE:
        - tissue.py (replaces noise.py): BrainWeb I/O, per-subject affine perturbation (rigid-body, nearest-neighbor resampling), resolution resampling to target modality grid, per-tissue-class intensity mapping, B1 bias field generation, Rician noise. Exports synthesize_volume_3d().
        - bold_signal.py (new): NSS transient, per-volume motion, slice-timing offsets, B0 geometric distortion, signal spikes, voxel-varying HRF convolution, task-evoked modulation, spatial-component FC model, linear drift, AR(1) noise. Exports synthesize_bold_4d().
        - events.py (new): ABCD emotional n-back block timing, pseudo-random block ordering (seeded by subject RNG), neural stimulus timecourse generation, BIDS events.tsv writing. Exports generate_enback_events().
        - modalities.py (updated): thin orchestrator; each generate_* function calls tissue/bold_signal, passes result to _save_nifti, writes sidecar JSON.
        - config.py (extended): per-tissue intensity tables, motion parameter ranges, B1/B0 parameters, NSS parameters, HRF parameter distributions, FC model parameters, EN-back task timing constants.
        - adversaries.py: unchanged (post-hoc file mutations)
        - scaffold.py: unchanged (BIDS metadata)

        PER-SUBJECT NATIVE-SPACE PERTURBATION:
        - Per-session: rotation Uniform(-15, +15) deg each axis, translation Uniform(-20, +20) mm each axis
        - Per-run (between-scan): rotation Uniform(-3, +3) deg, translation Uniform(-5, +5) mm
        - Rigid-body only (6 DOF); nearest-neighbor interpolation preserves discrete labels
        - Same perturbed label map reused for all modalities within a subject-session

        EN-BACK TASK SPECIFICATION:
        - 8 blocks per run: 1 per condition (2 loads x 4 stimulus categories)
        - Block structure: 2.5s instruction cue + 10 trials x 2.5s (2.0s stimulus + 0.5s ISI) = 27.5s
        - Block ordering: alternating 0-back/2-back, stimulus category order seeded by subject RNG
        - Inter-block fixation: ~8.4s average (296s total - 220s task = 76s across 9 intervals)
        - events.tsv columns: onset, duration, trial_type (e.g. 0back_happy, 2back_fear, 0back_place)
        - Condition-graded activation: 50% spatial overlap within same load, 30% across loads
        - Signal change: 2-back 1.0-2.0%, 0-back 0.5-1.5%

        UNCHANGED SYSTEMS:
        - int16 quantization with scl_slope/scl_inter (_save_nifti)
        - Per-subject RNG seeding from profile seed
        - BIDS file naming conventions
        - Adversary dispatch (apply_adversaries)
        - Scaffold generation
      </decision>
    </topic>
  </topics>
  <action_items>
    <item priority="P0" target_mode="implement" description="Download BrainWeb discrete anatomical model and store at tools/simulated_bids/data/ as NIfTI (convert from MINC/raw if needed)" />
    <item priority="P0" target_mode="implement" description="Create tissue.py replacing noise.py: BrainWeb I/O, per-subject affine perturbation, nearest-neighbor resampling, per-tissue intensity mapping, B1 bias field, Rician noise" />
    <item priority="P0" target_mode="implement" description="Create bold_signal.py: full BOLD temporal signal chain (NSS, motion, STC, B0 distortion, spikes, voxel-varying HRF, task modulation, FC networks, drift, AR(1), Rician noise)" />
    <item priority="P0" target_mode="implement" description="Create events.py: ABCD emotional n-back task timing, block ordering, neural stimulus timecourse, events.tsv generation" />
    <item priority="P0" target_mode="implement" description="Update modalities.py: replace structured_noise calls with tissue/bold_signal synthesis; add events.tsv generation for EN-back BOLD runs" />
    <item priority="P0" target_mode="implement" description="Extend config.py: per-tissue intensity tables (T1w, T2w, T2*, DWI ADC), motion parameter ranges, B1/B0 field parameters, NSS parameters, HRF distribution parameters, FC model parameters, EN-back task timing constants" />
    <item priority="P1" target_mode="test" description="Update test suite: replace noise-function tests with tissue-synthesis tests; add signal model validation tests (tissue contrast ratios, noise distribution, motion parameter ranges, events.tsv BIDS compliance)" />
    <item priority="P1" target_mode="implement" description="Remove noise.py after tissue.py is verified" />
    <item priority="P2" target_mode="test" description="End-to-end validation: regenerate both adversarial and clean datasets with tissue-based synthesis; verify all 31 adversary types still materialize; smoke-test through fmri-preproc pipeline" />
  </action_items>
  <next_steps>Proceed with /implement to build the tissue-based synthesis system. Recommended phase ordering: (1) download and verify BrainWeb label map, (2) build tissue.py with structural modality support (T1w, T2w), (3) build events.py, (4) build bold_signal.py, (5) update modalities.py and config.py, (6) update tests, (7) regenerate datasets and validate.</next_steps>
</brainstorm_report>
