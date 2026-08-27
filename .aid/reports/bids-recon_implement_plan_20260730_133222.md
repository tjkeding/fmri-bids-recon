<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-30T13:32:22Z" />
  <input_reports>
    <report path="bids-recon_brainstorm_20260730_132204.md" mode="brainstorm" key_items="9" />
  </input_reports>

  <assumptions_and_decisions>
    1. noise.py is DELETED after both modalities.py and adversaries.py are migrated to tissue-based synthesis. adversaries.py uses new convenience functions (synthesize_quick_3d, synthesize_quick_4d) from tissue.py at its 7 call sites (A4, A7, A13, A27, A31). These convenience functions encapsulate the full spatial pipeline (load label map, random perturbation, resample, intensity map, B1, Rician noise) in a single call, producing tissue-realistic replacement data that isolates each adversary's intended structural defect from signal-quality confounds. Each adversary already initializes its own deterministic RNG, so the fresh random perturbation per adversary call is both reproducible and more realistic (replacement data from a re-acquisition or different protocol would naturally have a different head position).
    2. scipy.ndimage.affine_transform is used for label-map resampling (order=0 nearest-neighbor). scipy 1.18.0 is already installed.
    3. No pandas dependency. events.tsv is written with Python string formatting (onset\tduration\ttrial_type columns).
    4. The BrainWeb discrete ("crisp") anatomical model is a raw unsigned-byte volume (181x217x181, 1mm isotropic, 12 classes 0-11). Download via the BrainWeb CGI interface; convert to NIfTI with nibabel.
    5. _make_affine and _save_nifti remain in modalities.py (adversaries.py imports them at line 20). No change to their signatures or behavior.
    6. INT16_QUANT_LEVELS=4095 and scl_slope/scl_inter quantization in _save_nifti are preserved unchanged.
    7. Per-subject RNG seeding from profile seed is preserved. The session-level perturbation affine and per-run baseline offsets are drawn from the same subject RNG stream.
  </assumptions_and_decisions>

  <changes>
    <change id="C1" priority="P0" source_item="brainstorm action item 1">
      <file path="tools/simulated_bids/data/brainweb_crisp.nii.gz" action="create" />
      <file path="tools/simulated_bids/data/download_brainweb.py" action="create" />
      <description>Download BrainWeb 12-class discrete anatomical model and convert to NIfTI. Store the NIfTI at tools/simulated_bids/data/brainweb_crisp.nii.gz. The download script is a one-time utility, not a runtime dependency.</description>
      <spec>
        download_brainweb.py:
        - Standalone script (not part of the package runtime; run once by the orchestrator).
        - Downloads raw unsigned-byte gzip file from BrainWeb CGI:
          URL: https://brainweb.bic.mni.mcgill.ca/cgi/brainweb1?do_download_1=yes&amp;type_value=1&amp;contrast_value=0&amp;slice_value=0&amp;noise_value=0&amp;rf_value=0&amp;format_value=raw_byte&amp;zip_value=gnuzip
        - Decompresses gzip, reshapes raw bytes to numpy uint8 (181, 217, 181) in Fortran order (column-major, MINC convention).
        - Constructs a NIfTI-1 affine placing the volume in approximate MNI space:
          affine = diag([-1, 1, 1, 1]) @ translate([90, -126, -72])
          (1mm isotropic, X-axis flipped for radiological-to-neurological convention)
        - Saves as brainweb_crisp.nii.gz with sform_code=1, qform_code=1.
        - Prints tissue-class histogram for verification (12 classes, 0-11).
        - If the BrainWeb CGI URL is unreachable, falls back to a manual-download instruction message.

        Tissue class mapping (BrainWeb discrete model):
          0: Background, 1: CSF, 2: Grey Matter, 3: White Matter, 4: Fat,
          5: Muscle/Skin, 6: Skin, 7: Skull, 8: Vessels, 9: Connective,
          10: Dura Mater, 11: Bone Marrow

        Execution: orchestrator runs `python3 tools/simulated_bids/data/download_brainweb.py` once, then verifies the output file exists and has the expected shape.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - one-time download; verification by histogram</risk>
      <rollback>Delete tools/simulated_bids/data/</rollback>
    </change>

    <change id="C2" priority="P0" source_item="brainstorm action item 6">
      <file path="tools/simulated_bids/config.py" action="modify" />
      <description>Extend config.py with all synthesis parameters: per-tissue intensity tables, motion ranges, B1/B0 field parameters, NSS parameters, HRF distribution parameters, FC model parameters, EN-back task timing constants.</description>
      <spec>
        Add the following constants after the existing FMAP_EPI_PARAMS block:

        TISSUE_CLASSES dict mapping class ID (int) to name (str):
          {0: "background", 1: "csf", 2: "gm", 3: "wm", 4: "fat",
           5: "muscle", 6: "skin", 7: "skull", 8: "vessels",
           9: "connective", 10: "dura", 11: "marrow"}

        Per-modality intensity tables (dict[int, float], normalized 0-1):
          T1W_INTENSITIES:
            0:0.0, 1:0.15, 2:0.65, 3:0.85, 4:0.90, 5:0.55, 6:0.55,
            7:0.20, 8:0.35, 9:0.40, 10:0.30, 11:0.80
          T2W_INTENSITIES:
            0:0.0, 1:0.95, 2:0.70, 3:0.45, 4:0.80, 5:0.40, 6:0.40,
            7:0.10, 8:0.60, 9:0.30, 10:0.25, 11:0.75
          T2STAR_INTENSITIES (BOLD/fmap EPI):
            0:0.0, 1:0.70, 2:0.55, 3:0.40, 4:0.35, 5:0.25, 6:0.25,
            7:0.05, 8:0.30, 9:0.20, 10:0.15, 11:0.30
          DWI_S0_INTENSITIES (b=0 baseline, T2-weighted):
            0:0.0, 1:0.90, 2:0.65, 3:0.50, 4:0.75, 5:0.35, 6:0.35,
            7:0.08, 8:0.55, 9:0.25, 10:0.20, 11:0.70
          DWI_ADC (mm^2/s per tissue class):
            0:0.0, 1:3.0e-3, 2:0.8e-3, 3:0.7e-3, 4:0.1e-3, 5:1.5e-3,
            6:1.5e-3, 7:0.3e-3, 8:2.0e-3, 9:1.0e-3, 10:0.8e-3, 11:0.5e-3

        BRAINWEB_SHAPE = (181, 217, 181)
        BRAINWEB_VOXEL_SIZE = (1.0, 1.0, 1.0)

        Perturbation parameters:
          SESSION_ROT_RANGE = 15.0   # degrees, per axis
          SESSION_TRANS_RANGE = 20.0 # mm, per axis
          RUN_ROT_RANGE = 3.0        # degrees, per axis
          RUN_TRANS_RANGE = 5.0      # mm, per axis

        Motion parameters (within-run per-volume jitter):
          MOTION_TRANS_SD = 0.3   # mm, SD of per-volume translation
          MOTION_ROT_SD = 0.2    # degrees, SD of per-volume rotation

        B1 bias field:
          B1_AMPLITUDE = 0.15  # max deviation from unity (field = 1 +/- amplitude)

        B0 field:
          B0_MAX_SHIFT = 4.0  # max voxel displacement along PE direction

        NSS transient:
          NSS_N_FRAMES = 5     # number of non-steady-state frames
          NSS_AMPLITUDE = 0.15 # fractional elevation above steady state
          NSS_TAU = 2.5        # decay time constant in volumes

        HRF parameters (voxel-varying, drawn from distributions):
          HRF_PEAK_MEAN = 5.5   # seconds
          HRF_PEAK_SD = 0.5     # seconds
          HRF_UNDERSHOOT_MEAN = 0.35  # ratio
          HRF_UNDERSHOOT_SD = 0.1     # ratio
          HRF_DURATION = 32.0   # seconds, total HRF support

        Activation:
          ACTIVATION_GM_FRACTION_RANGE = (0.20, 0.40)  # fraction of GM voxels
          ACTIVATION_SIGNAL_CHANGE_0BACK = (0.005, 0.015)  # fractional
          ACTIVATION_SIGNAL_CHANGE_2BACK = (0.010, 0.020)

        FC model:
          FC_N_NETWORKS = 6          # number of independent networks
          FC_BANDPASS = (0.01, 0.1)  # Hz
          FC_AMPLITUDE = 0.01        # fractional signal change

        AR(1):
          AR1_PHI_RANGE = (0.3, 0.5)

        Spike:
          SPIKE_FRACTION = 0.02  # fraction of volumes with spikes
          SPIKE_MAGNITUDE = 5.0  # multiplicative factor for spike volumes

        SNR (Rician noise):
          SNR_T1W = 40.0
          SNR_T2W = 35.0
          SNR_BOLD = 25.0
          SNR_DWI = 20.0
          SNR_FMAP = 25.0

        EN-back task timing:
          ENBACK_N_BLOCKS = 8
          ENBACK_CUE_DURATION = 2.5       # seconds
          ENBACK_TRIALS_PER_BLOCK = 10
          ENBACK_TRIAL_DURATION = 2.5     # seconds (2.0s stim + 0.5s ISI)
          ENBACK_BLOCK_DURATION = 27.5    # cue + 10 trials
          ENBACK_CONDITIONS = [
              "0back_happy", "0back_fear", "0back_neut", "0back_place",
              "2back_happy", "2back_fear", "2back_neut", "2back_place",
          ]
          ENBACK_LOAD_OVERLAP = 0.50  # within-load spatial overlap
          ENBACK_CROSS_OVERLAP = 0.30 # across-load spatial overlap

        Linear drift:
          DRIFT_AMPLITUDE = 0.02  # fractional change over full run

        Do NOT modify or remove any existing constants. The new constants are additive.
      </spec>
      <dependencies>none</dependencies>
      <risk>low - additive constants only; no existing code affected</risk>
      <rollback>Revert config.py to prior state</rollback>
    </change>

    <change id="C3" priority="P0" source_item="brainstorm action item 4">
      <file path="tools/simulated_bids/events.py" action="create" />
      <description>Create events.py: ABCD emotional n-back task timing, pseudo-random block ordering, neural stimulus timecourse generation, BIDS events.tsv writing.</description>
      <spec>
        Module: tools/simulated_bids/events.py

        Imports: numpy, pathlib, config constants (ENBACK_*, BOLD_ENBACK_VOLUMES, BOLD_PARAMS["RepetitionTime"])

        Function: generate_enback_events(n_volumes: int, tr: float, rng: np.random.Generator) -> tuple[list[dict], dict[str, np.ndarray]]
          Purpose: Generate block timing for one EN-back run and the neural stimulus timecourses.

          Algorithm:
          1. Total run duration = n_volumes * tr (= 296s).
          2. Total task time = ENBACK_N_BLOCKS * ENBACK_BLOCK_DURATION (= 220s).
          3. Total fixation = run_duration - task_time (= 76s).
          4. Distribute fixation across ENBACK_N_BLOCKS + 1 intervals:
             - Jitter each interval around mean (76 / 9 ~ 8.4s) using rng.dirichlet,
               with minimum 4.0s per interval.
          5. Block ordering: create list of 8 conditions from ENBACK_CONDITIONS.
             Shuffle with constraint: 0-back and 2-back blocks alternate.
             Implementation: separate 0back and 2back conditions, shuffle each independently,
             interleave (starting with 0back or 2back randomly).
          6. Compute onset for each block = cumulative fixation + prior block durations.
          7. Build events list: each block is one dict with keys {onset, duration, trial_type}.
             Duration = ENBACK_BLOCK_DURATION (27.5s, includes cue + trials).
          8. Build neural timecourses: for each unique condition, create a 1D array of length
             n_timepoints = int(run_duration / tr). Set neural_tc[condition][onset_sample:offset_sample] = 1.0
             (boxcar). onset_sample = round(onset / tr), offset_sample = round((onset + duration) / tr).

          Returns:
            events: list of dicts [{onset, duration, trial_type}, ...]
            neural_tc: dict mapping condition_name -> np.ndarray of shape (n_volumes,)

        Function: write_events_tsv(events: list[dict], out_path: Path) -> None
          Purpose: Write BIDS-compliant events.tsv.
          Format: tab-separated, columns: onset, duration, trial_type.
          onset and duration formatted to 3 decimal places.
          Header line: "onset\tduration\ttrial_type\n"
      </spec>
      <dependencies>C2 (uses ENBACK_* constants from config.py)</dependencies>
      <risk>low - new file, no existing code affected</risk>
      <rollback>Delete events.py</rollback>
    </change>

    <change id="C4" priority="P0" source_item="brainstorm action item 2">
      <file path="tools/simulated_bids/tissue.py" action="create" />
      <description>Create tissue.py: BrainWeb label map I/O, per-subject affine perturbation, nearest-neighbor resampling, per-tissue intensity mapping, B1 bias field, B0 field, Rician noise.</description>
      <spec>
        Module: tools/simulated_bids/tissue.py

        Imports: numpy, nibabel, pathlib, scipy.ndimage (affine_transform),
                 config constants (BRAINWEB_*, TISSUE_CLASSES, intensity tables, B1/B0/SNR params)

        Module-level:
          _LABEL_MAP_CACHE: dict = {}  (keyed by file path string)
          _DATA_DIR = Path(__file__).parent / "data"

        Function: load_label_map() -> np.ndarray
          Load BrainWeb label map from _DATA_DIR / "brainweb_crisp.nii.gz".
          Cache in _LABEL_MAP_CACHE. Return uint8 array of shape (181, 217, 181).
          Raise FileNotFoundError with instruction to run download_brainweb.py if missing.

        Function: make_perturbation_affine(rng: np.random.Generator, rot_range: float, trans_range: float) -> np.ndarray
          Generate a 4x4 rigid-body affine from random rotation angles (each axis drawn
          from Uniform(-rot_range, +rot_range) degrees) and translations (each axis drawn
          from Uniform(-trans_range, +trans_range) mm). Rotation constructed via
          Rz @ Ry @ Rx composition. Return 4x4 float64 matrix.

        Function: resample_labels(label_map: np.ndarray, session_affine: np.ndarray, run_offset_affine: np.ndarray, target_shape: tuple[int,int,int], target_voxel_size: tuple[float,...]) -> tuple[np.ndarray, np.ndarray]
          Resample the BrainWeb label map to a target voxel grid with the combined
          session + run-offset perturbation applied.

          Algorithm:
          1. Compose: combined = run_offset_affine @ session_affine
          2. Build target-voxel-to-BrainWeb-voxel mapping:
             The BrainWeb template has its own affine (from the NIfTI header).
             target_phys = A_target @ voxel  (where A_target encodes the target grid in scanner space)
             source_voxel = inv(A_brainweb) @ inv(combined) @ target_phys
             Simplify to a single composite affine mapping target voxel -> source voxel.
          3. Use scipy.ndimage.affine_transform(label_map, composite[:3,:3], composite[:3,3],
             output_shape=target_shape, order=0, mode='constant', cval=0).
          4. Build the output NIfTI affine: A_output = combined @ A_brainweb @ scale(target_voxel_size / brainweb_voxel_size)
             Simplified: construct from the perturbation and target voxel size, centering the volume.
          Return (resampled_labels: uint8, output_affine: float64 4x4).

        Function: tissue_intensities(labels: np.ndarray, intensity_table: dict[int, float]) -> np.ndarray
          Map discrete label values to float32 intensities via vectorized lookup.
          Use a 12-element lookup array indexed by label value.
          Return float32 array, same shape as labels.

        Function: generate_b1_field(shape: tuple[int,int,int], amplitude: float, rng: np.random.Generator) -> np.ndarray
          Generate smooth multiplicative bias field as a 2nd-order 3D polynomial:
            coords = meshgrid of normalized [-1,1] coordinates for each axis
            coefficients = rng.uniform(-1, 1, size=10) (constant, 3 linear, 6 quadratic terms)
            field = 1.0 + amplitude * (c0 + c1*x + c2*y + c3*z + c4*x*y + c5*x*z + c6*y*z + c7*x^2 + c8*y^2 + c9*z^2)
            Normalize: field = field / field.mean()  (so mean multiplicative effect ~ 1.0)
          Return float32 array of shape.

        Function: generate_b0_field(shape: tuple[int,int,int], max_shift: float, rng: np.random.Generator) -> np.ndarray
          Generate smooth B0 inhomogeneity field representing voxel displacement (in voxels)
          along the phase-encoding direction.
          Same polynomial approach as B1, but output is displacement in voxels (not multiplicative).
            field = max_shift * polynomial(normalized_coords, rng_coefficients)
          Return float32 array of shape.

        Function: apply_b0_distortion(volume: np.ndarray, b0_field: np.ndarray, polarity: float) -> np.ndarray
          Apply geometric distortion along axis 1 (j / PE direction).
          polarity = +1.0 for PE=j (PA), -1.0 for PE=j- (AP).
          For each (i, k) column, compute displaced j-coordinates:
            j_displaced = j_original + polarity * b0_field[i, :, k]
          Resample the column at the displaced positions using linear interpolation (np.interp).
          Return float32 array, same shape as input.

        Function: add_rician_noise(data: np.ndarray, snr: float, rng: np.random.Generator) -> np.ndarray
          Add Rician noise: magnitude of complex Gaussian.
          noise_sd = data.mean() / snr (where data.mean() is over nonzero voxels)
          real = data + rng.normal(0, noise_sd, data.shape)
          imag = rng.normal(0, noise_sd, data.shape)
          return np.sqrt(real**2 + imag**2).astype(np.float32)

        Function: synthesize_volume_3d(modality: str, labels: np.ndarray, output_affine: np.ndarray, b1_field: np.ndarray, rng: np.random.Generator, b_value: float = 0.0) -> tuple[np.ndarray, np.ndarray]
          High-level 3D synthesis for structural modalities and single-volume acquisitions.
          1. Select intensity table by modality: "t1w" -> T1W_INTENSITIES, "t2w" -> T2W_INTENSITIES,
             "t2star" -> T2STAR_INTENSITIES, "dwi" -> (see below).
          2. Map labels to intensities via tissue_intensities().
          3. For DWI: if b_value > 0, apply exponential attenuation:
             s0 = tissue_intensities(labels, DWI_S0_INTENSITIES)
             adc = tissue_intensities(labels, DWI_ADC)  (reuse same lookup for ADC)
             volume = s0 * np.exp(-b_value * adc)
             For b_value == 0: volume = tissue_intensities(labels, DWI_S0_INTENSITIES)
          4. Apply B1 bias: volume *= b1_field
          5. Add Rician noise: volume = add_rician_noise(volume, SNR_by_modality, rng)
          Return (volume: float32, output_affine: float64 4x4).

        Function: synthesize_quick_3d(modality: str, shape: tuple[int,int,int], voxel_size: tuple[float,...], rng: np.random.Generator) -> np.ndarray
          Convenience function for adversary modules. Encapsulates the full spatial synthesis
          pipeline in one call: load label map, generate fresh random perturbation, resample
          to target grid, map intensities, apply B1 bias, add Rician noise.

          Implementation:
          1. label_map = load_label_map()
          2. perturb = make_perturbation_affine(rng, SESSION_ROT_RANGE, SESSION_TRANS_RANGE)
          3. labels, _ = resample_labels(label_map, perturb, np.eye(4), shape, voxel_size)
          4. b1 = generate_b1_field(shape, B1_AMPLITUDE, rng)
          5. volume, _ = synthesize_volume_3d(modality, labels, np.eye(4), b1, rng)
          Return float32 array of given shape.

          Design rationale: adversary replacement data uses a fresh random perturbation
          (not the session context) because (a) adversaries operate post-hoc without access
          to the session context, (b) replacement data from a re-acquisition or different
          protocol would naturally have a different head position, and (c) each adversary's
          own deterministic RNG (e.g., np.random.default_rng(7001) in A4) ensures
          reproducibility across regenerations.

        Function: synthesize_quick_4d(modality: str, shape_3d: tuple[int,int,int], n_volumes: int, voxel_size: tuple[float,...], rng: np.random.Generator) -> np.ndarray
          Convenience function for adversary modules. Stacks n_volumes independent 3D
          tissue-synthesized volumes into a 4D array. All volumes share the same spatial
          structure (same perturbation, same B1 field) but have independent Rician noise
          realizations.

          Implementation:
          1. label_map = load_label_map()
          2. perturb = make_perturbation_affine(rng, SESSION_ROT_RANGE, SESSION_TRANS_RANGE)
          3. labels, _ = resample_labels(label_map, perturb, np.eye(4), shape_3d, voxel_size)
          4. b1 = generate_b1_field(shape_3d, B1_AMPLITUDE, rng)
          5. out = np.empty((*shape_3d, n_volumes), dtype=np.float32)
          6. For v in range(n_volumes):
               vol, _ = synthesize_volume_3d(modality, labels, np.eye(4), b1, rng)
               out[..., v] = vol
          Return float32 array of shape (*shape_3d, n_volumes).
      </spec>
      <dependencies>C1 (needs brainweb_crisp.nii.gz), C2 (needs intensity tables and parameters from config)</dependencies>
      <risk>medium - core spatial synthesis; correctness depends on affine composition</risk>
      <rollback>Delete tissue.py</rollback>
    </change>

    <change id="C5" priority="P0" source_item="brainstorm action item 3">
      <file path="tools/simulated_bids/bold_signal.py" action="create" />
      <description>Create bold_signal.py: full BOLD temporal signal chain (NSS, motion, STC, B0 distortion, spikes, HRF, task modulation, FC networks, drift, AR(1), Rician noise).</description>
      <spec>
        Module: tools/simulated_bids/bold_signal.py

        Imports: numpy, config constants (NSS_*, HRF_*, ACTIVATION_*, FC_*, AR1_*,
                 SPIKE_*, DRIFT_*, SNR_BOLD, MOTION_*, T2STAR_INTENSITIES, BOLD_PARAMS)
        From tissue: tissue_intensities, generate_b1_field, add_rician_noise, apply_b0_distortion

        Function: _double_gamma_hrf(t: np.ndarray, peak_time: float, undershoot_ratio: float) -> np.ndarray
          Compute a double-gamma HRF.
          peak = t**(peak_time / 0.9) * np.exp(-t / 0.9) (simplified Glover 1999 parameterization)
          undershoot = t**((peak_time + 6.0) / 0.9) * np.exp(-t / 0.9)
          hrf = peak - undershoot_ratio * undershoot
          Normalize: hrf /= hrf.max()
          Return 1D float64 array.

        Function: generate_activation_maps(gm_mask: np.ndarray, conditions: list[str], rng: np.random.Generator) -> dict[str, np.ndarray]
          Generate condition-specific activation masks with controlled overlap.
          1. Total GM voxels = gm_mask.sum().
          2. Sample activation fraction from Uniform(*ACTIVATION_GM_FRACTION_RANGE) -> n_active.
          3. For each condition, select n_active voxels from GM:
             - Group conditions by load (0back vs 2back).
             - Within-load conditions share ENBACK_LOAD_OVERLAP fraction of their voxels
               (overlap pool drawn first, then each condition fills the remainder independently).
             - Across-load overlap is ENBACK_CROSS_OVERLAP fraction.
          4. For each condition, assign signal change magnitude:
             - 0back conditions: Uniform(*ACTIVATION_SIGNAL_CHANGE_0BACK)
             - 2back conditions: Uniform(*ACTIVATION_SIGNAL_CHANGE_2BACK)
          Return dict mapping condition -> float32 3D array (same shape as gm_mask)
          where each voxel's value is 0.0 (inactive) or the assigned signal change magnitude.

        Function: _generate_fc_signals(n_networks: int, n_volumes: int, tr: float, rng: np.random.Generator) -> np.ndarray
          Generate bandpass-filtered random timecourses for FC networks.
          1. For each network, generate white noise (n_volumes,).
          2. Apply FFT-based brick-wall bandpass filter:
             fft = np.fft.rfft(noise); freqs = np.fft.rfftfreq(n_volumes, d=tr)
             mask = (freqs >= FC_BANDPASS[0]) & (freqs <= FC_BANDPASS[1])
             fft[~mask] = 0; filtered = np.fft.irfft(fft, n=n_volumes)
          3. Normalize each timecourse to zero mean, unit variance.
          Return float64 array of shape (n_networks, n_volumes).

        Function: _assign_network_maps(gm_mask: np.ndarray, n_networks: int, rng: np.random.Generator) -> np.ndarray
          Assign each GM voxel a weight for each network.
          For each network: select ~15-25% of GM voxels (random subset).
          Weight = FC_AMPLITUDE for selected voxels, 0 otherwise.
          Return float32 array of shape (*gm_mask.shape, n_networks).

        Function: synthesize_bold_4d(labels: np.ndarray, n_volumes: int, tr: float, task_events: dict[str, np.ndarray] | None, activation_maps: dict[str, np.ndarray] | None, b0_field: np.ndarray, b1_field: np.ndarray, slice_timing: list[float], rng: np.random.Generator) -> np.ndarray
          Full 4D BOLD synthesis pipeline. Steps executed in order:

          1. BASELINE: tissue_intensities(labels, T2STAR_INTENSITIES) -> S_tissue (3D).

          2. TASK RESPONSE (if task_events is not None):
             For each condition in task_events:
               - Generate voxel-varying HRF params: peak_time per voxel from N(HRF_PEAK_MEAN, HRF_PEAK_SD),
                 undershoot per voxel from N(HRF_UNDERSHOOT_MEAN, HRF_UNDERSHOOT_SD).
               - For efficiency, bin HRF params into ~20 clusters (unique HRFs),
                 convolve each cluster's neural_tc with its HRF, then broadcast to member voxels.
                 This avoids n_voxels independent convolutions.
               - task_bold[v, t] += activation_maps[condition][v] * convolved_tc[v, t]

          3. FC NETWORKS:
             fc_signals = _generate_fc_signals(FC_N_NETWORKS, n_volumes, tr, rng)
             fc_weights = _assign_network_maps(gm_mask, FC_N_NETWORKS, rng)
             network_signal[v, t] = sum_k(fc_weights[v, k] * fc_signals[k, t])

          4. LINEAR DRIFT:
             drift = np.linspace(0, DRIFT_AMPLITUDE, n_volumes)

          5. COMPOSE CLEAN SIGNAL:
             S_clean[v, t] = S_tissue[v] * (1 + task_bold[v,t] + network_signal[v,t] + drift[t]) * b1_field[v]

          6. NSS TRANSIENT:
             For t in range(NSS_N_FRAMES):
               S_clean[:, :, :, t] *= (1 + NSS_AMPLITUDE * exp(-t / NSS_TAU))

          7. AR(1) NOISE:
             phi = rng.uniform(*AR1_PHI_RANGE)
             Generate AR(1) noise volume: n[v,0] = N(0,1); n[v,t] = phi*n[v,t-1] + sqrt(1-phi^2)*N(0,1)
             noise_sd = S_tissue.mean() / SNR_BOLD (over nonzero voxels)
             S_clean += noise_sd * ar1_noise

          8. RICIAN NOISE:
             S_noisy = add_rician_noise applied per-volume (uses remaining noise budget after AR(1))
             Rician SNR set higher than SNR_BOLD to avoid double-counting with AR(1).
             Implementation: add_rician_noise(S_clean, SNR_BOLD * 2.0, rng) per volume.

          9. SIGNAL SPIKES:
             n_spike_vols = round(SPIKE_FRACTION * n_volumes)
             spike_indices = rng.choice(range(NSS_N_FRAMES, n_volumes), n_spike_vols, replace=False)
             S_noisy[:,:,:, spike_indices] *= SPIKE_MAGNITUDE
             (spikes are global intensity bursts affecting entire volumes)

          10. SLICE-TIMING OFFSETS:
              For each slice group g (MB group, determined by slice_timing array):
                time_offset = slice_timing[g]
                fractional_shift = time_offset / tr
                For each voxel in slice group g, shift the timecourse by fractional_shift
                using linear interpolation between adjacent volumes.
              Note: slice groups are defined by unique values in the slice_timing array.

          11. B0 GEOMETRIC DISTORTION:
              For each volume t: S_out[:,:,:,t] = apply_b0_distortion(S_noisy[:,:,:,t], b0_field, +1.0)
              (PA direction; the preprocessing pipeline's TOPUP will estimate and correct this)

          12. PER-VOLUME MOTION:
              For each volume t (after NSS_N_FRAMES):
                Generate small rigid-body perturbation:
                  rot = rng.normal(0, MOTION_ROT_SD, 3)  # degrees
                  trans = rng.normal(0, MOTION_TRANS_SD, 3)  # mm
                Apply as a small affine warp to the volume using scipy.ndimage.affine_transform
                with order=1 (linear interpolation).
              Store motion parameters (6 DOF per volume) for potential output.

          Return float32 array of shape (*labels.shape, n_volumes).

          Performance note: the most expensive operations are per-volume affine warps (motion)
          and per-slice-group temporal interpolation (STC). For a 90x90x60x383 volume, expect
          ~30-60 seconds per run on a modern CPU. Total generation time for 17 subjects x
          3 sessions x 4 BOLD runs ~ 2-4 hours (vs ~30 minutes for the current noise-only approach).
      </spec>
      <dependencies>C2 (config constants), C4 (tissue synthesis functions)</dependencies>
      <risk>high - most complex module; many interacting temporal components; performance-sensitive</risk>
      <rollback>Delete bold_signal.py</rollback>
    </change>

    <change id="C6" priority="P0" source_item="brainstorm action items 5, 7">
      <file path="tools/simulated_bids/modalities.py" action="modify" />
      <description>Update modalities.py: replace structured_noise imports with tissue/bold_signal/events imports. Update all generate_* functions to use tissue-based synthesis. Add events.tsv generation for EN-back BOLD.</description>
      <spec>
        Import changes:
        - REMOVE: from .noise import structured_noise_3d, structured_noise_4d
        - ADD: from .tissue import (load_label_map, make_perturbation_affine, resample_labels,
                 synthesize_volume_3d, generate_b1_field, generate_b0_field, apply_b0_distortion,
                 add_rician_noise, tissue_intensities)
        - ADD: from .bold_signal import synthesize_bold_4d, generate_activation_maps
        - ADD: from .events import generate_enback_events, write_events_tsv
        - ADD: from .config import (T2STAR_INTENSITIES, DWI_S0_INTENSITIES, DWI_ADC,
                 SESSION_ROT_RANGE, SESSION_TRANS_RANGE, RUN_ROT_RANGE, RUN_TRANS_RANGE,
                 SNR_T1W, SNR_T2W, SNR_DWI, SNR_FMAP, ENBACK_CONDITIONS)

        All generate_* function signatures gain new parameters:
          session_labels: np.ndarray  (resampled label map for this session, from __main__.py)
          session_affine: np.ndarray  (output affine for this session, from __main__.py)
          b1_field: np.ndarray        (B1 field for this session, from __main__.py)
          b0_field: np.ndarray | None (B0 field for EPI modalities, from __main__.py)

        The rng parameter remains; patient_fields remains.

        generate_t1w(out_dir, sub, ses, run, rng, patient_fields, session_labels, session_affine, b1_field):
          1. volume, _ = synthesize_volume_3d("t1w", session_labels, session_affine, b1_field, rng)
          2. _save_nifti(volume, session_affine, T1W_PARAMS["RepetitionTime"], path)
          3. Sidecar JSON as before.

        generate_t2w(out_dir, sub, ses, run, rng, patient_fields, session_labels, session_affine, b1_field):
          Same pattern as T1w with modality="t2w".

        generate_bold(out_dir, sub, ses, task, run, n_volumes, b0_field_source, rng, patient_fields,
                      session_labels, session_affine, b1_field, b0_field,
                      activation_maps=None, task_events=None):
          1. bold_4d = synthesize_bold_4d(session_labels, n_volumes, BOLD_PARAMS["RepetitionTime"],
                                          task_events, activation_maps, b0_field, b1_field,
                                          slice_timing_array, rng)
          2. _save_nifti(bold_4d, session_affine, BOLD_PARAMS["RepetitionTime"], bold_path)
          3. SBRef: synthesize_volume_3d("t2star", session_labels, session_affine, b1_field, rng)
             Apply B0 distortion to SBRef: apply_b0_distortion(sbref, b0_field, +1.0)
          4. If task == "emotionalnback" and task_events is not None:
             write_events_tsv(task_events["events_list"], func_dir / f"{bold_stem}_events.tsv")
             (BIDS events.tsv filename convention: bold stem with _events.tsv suffix is
              {sub}_{ses}_task-{task}_run-{run}_events.tsv)
          5. Sidecars as before.

        generate_dwi(out_dir, sub, ses, b0_field_source, rng, patient_fields,
                     session_labels, session_affine, b1_field, b0_field):
          1. Generate bvals as before (unchanged).
          2. For each volume v with b-value b:
             vol = synthesize_volume_3d("dwi", session_labels, session_affine, b1_field, rng, b_value=b)
             stack into 4D.
          3. _save_nifti(dwi_4d, session_affine, DWI_PARAMS["RepetitionTime"], path)
          4. SBRef files: synthesize_volume_3d("dwi", ..., b_value=0) for each SBRef.
          5. bvecs as before (unchanged). Sidecars as before.

        generate_fmap_pair(out_dir, sub, ses, acq, run, intended_for, b0_field_id, rng,
                           patient_fields, session_labels, session_affine, b1_field, b0_field):
          1. For PA: vol = synthesize_volume_3d("t2star", session_labels, session_affine, b1_field, rng)
             Apply B0 distortion: apply_b0_distortion(vol, b0_field, +1.0)  # PA = +j
             Stack 3 volumes (with per-volume Rician noise variation).
          2. For AP: same volume, apply_b0_distortion(vol, b0_field, -1.0)   # AP = -j
             Stack 3 volumes.
          3. _save_nifti, sidecars as before.

        _make_affine and _save_nifti are UNCHANGED (adversaries.py imports them).
        _bold_slice_timing and _base_sidecar are UNCHANGED.
      </spec>
      <dependencies>C2, C3, C4, C5</dependencies>
      <risk>medium - multiple function signature changes; must preserve _make_affine/_save_nifti for adversaries</risk>
      <rollback>Revert modalities.py to prior state</rollback>
    </change>

    <change id="C7" priority="P0" source_item="brainstorm action items 2, 5 (integration)">
      <file path="tools/simulated_bids/__main__.py" action="modify" />
      <description>Update __main__.py to generate session-level perturbation, B1/B0 fields, activation maps, and EN-back events; pass these through to modality generators.</description>
      <spec>
        Import changes:
        - ADD: from .tissue import (load_label_map, make_perturbation_affine, resample_labels,
                 generate_b1_field, generate_b0_field)
        - ADD: from .bold_signal import generate_activation_maps
        - ADD: from .events import generate_enback_events
        - ADD: from .config import (SESSION_ROT_RANGE, SESSION_TRANS_RANGE,
                 RUN_ROT_RANGE, RUN_TRANS_RANGE, B1_AMPLITUDE, ENBACK_CONDITIONS)

        Modify generate_clean_session:
          New signature: generate_clean_session(out_dir, sub, ses, demo, ses_index, rng, label_map)
            label_map parameter: the raw BrainWeb label map (loaded once in main()).

          At the top of generate_clean_session, BEFORE any modality generation:
          1. Generate session-level perturbation affine:
             session_perturb = make_perturbation_affine(rng, SESSION_ROT_RANGE, SESSION_TRANS_RANGE)
          2. Resample label map to each target resolution needed:
             For T1w/T2w (1mm): labels_1mm, affine_1mm = resample_labels(label_map, session_perturb, np.eye(4), T1W_PARAMS["shape"], T1W_PARAMS["voxel_size"])
             For BOLD/fmap (2.4mm): labels_bold, affine_bold = resample_labels(label_map, session_perturb, np.eye(4), BOLD_PARAMS["shape_spatial"], BOLD_PARAMS["voxel_size"])
             For DWI (1.7mm): labels_dwi, affine_dwi = resample_labels(label_map, session_perturb, np.eye(4), DWI_PARAMS["shape_spatial"], DWI_PARAMS["voxel_size"])
          3. Generate B1 field for each resolution:
             b1_1mm = generate_b1_field(T1W_PARAMS["shape"], B1_AMPLITUDE, rng)
             b1_bold = generate_b1_field(BOLD_PARAMS["shape_spatial"], B1_AMPLITUDE, rng)
             b1_dwi = generate_b1_field(DWI_PARAMS["shape_spatial"], B1_AMPLITUDE, rng)
          4. Generate B0 field (BOLD resolution, shared across all EPI):
             b0_field = generate_b0_field(BOLD_PARAMS["shape_spatial"], B0_MAX_SHIFT, rng)
          5. Generate activation maps for EN-back (one set per session, shared across runs):
             activation_maps = generate_activation_maps(labels_bold == 2, ENBACK_CONDITIONS, rng)

          Pass session_labels, session_affine, b1_field, b0_field, activation_maps
          to each generate_* call.

          For EN-back BOLD runs: generate per-run events:
            events, neural_tc = generate_enback_events(BOLD_ENBACK_VOLUMES, BOLD_PARAMS["RepetitionTime"], rng)
            Pass task_events={"events_list": events, "neural_tc": neural_tc}
            and activation_maps=activation_maps to generate_bold.

          For rest BOLD runs: pass task_events=None, activation_maps=None.

        Modify main():
          Before the subject loop, load the BrainWeb label map once:
            label_map = load_label_map()
          Pass label_map to generate_clean_session.

        Update the manifest line in manifest.py (line 96):
          Change "Voxel fill: structured noise (low-frequency spatial gradient + Gaussian)."
          to "Voxel fill: tissue-based synthesis from BrainWeb 12-class anatomical model."
      </spec>
      <dependencies>C2, C3, C4, C5, C6</dependencies>
      <risk>medium - orchestration logic; must ensure consistent RNG state across all modalities within a session</risk>
      <rollback>Revert __main__.py and manifest.py to prior state</rollback>
    </change>

    <change id="C8" priority="P0" source_item="adversary transparency finding (implement:plan codebase audit)">
      <file path="tools/simulated_bids/adversaries.py" action="modify" />
      <description>Replace structured_noise imports with tissue-based synthesis convenience functions. Update all 7 call sites across adversaries A4, A7, A13, A27, and A31 to use synthesize_quick_3d and synthesize_quick_4d from tissue.py.</description>
      <spec>
        Import changes:
        - REMOVE (line 19): from .noise import structured_noise_3d, structured_noise_4d
        - ADD: from .tissue import synthesize_quick_3d, synthesize_quick_4d
        - KEEP (line 20): from .modalities import _make_affine, _save_nifti  (unchanged)

        Call site migrations (7 sites):

        A4 (scan restart, line ~436):
          BEFORE: structured_noise_4d(BOLD_PARAMS["shape_spatial"], BOLD_REST_VOLUMES, rng)
                  with rng = np.random.default_rng(7001)
          AFTER:  synthesize_quick_4d("t2star", BOLD_PARAMS["shape_spatial"], BOLD_REST_VOLUMES,
                    tuple(BOLD_PARAMS["voxel_size"]), rng)
                  with rng = np.random.default_rng(7001) (unchanged)

        A7 (stale study, line ~458):
          BEFORE: structured_noise_4d(BOLD_PARAMS["shape_spatial"], BOLD_REST_VOLUMES, rng)
                  with rng = np.random.default_rng(9999)
          AFTER:  synthesize_quick_4d("t2star", BOLD_PARAMS["shape_spatial"], BOLD_REST_VOLUMES,
                    tuple(BOLD_PARAMS["voxel_size"]), rng)
                  with rng = np.random.default_rng(9999) (unchanged)

        A27 (localizer, line ~514):
          BEFORE: structured_noise_3d((256, 256, 3), rng)
                  with rng = np.random.default_rng(3333)
                  and non-standard affine np.diag([1.0, 1.0, 5.0, 1.0])
          AFTER:  synthesize_quick_3d("t1w", (256, 256, 3), (1.0, 1.0, 5.0), rng)
                  with rng = np.random.default_rng(3333) (unchanged)
          Note: A27's non-standard voxel size (1.0, 1.0, 5.0) is the adversary's intended
          geometric defect (thick-slice localizer); this is correctly passed through voxel_size.

        A31 (voxel drift, line ~621, main BOLD):
          BEFORE: structured_noise_4d(shape, BOLD_REST_VOLUMES, rng)
                  with shape from spec["details"] and rng = np.random.default_rng(8801)
          AFTER:  synthesize_quick_4d("t2star", shape, BOLD_REST_VOLUMES,
                    tuple(voxel_size), rng)
                  with rng = np.random.default_rng(8801) (unchanged)
          Note: shape and voxel_size are already computed from spec["details"] earlier in A31.

        A31 (voxel drift, line ~625, SBRef):
          BEFORE: structured_noise_4d(shape, 1, rng)[..., 0]
          AFTER:  synthesize_quick_3d("t2star", shape, tuple(voxel_size), rng)
          Note: was previously generating 4D with 1 volume and squeezing; now uses direct 3D.

        A31 (voxel drift, line ~640, fieldmap):
          BEFORE: structured_noise_4d(shape, FMAP_EPI_PARAMS["n_volumes"], rng)
          AFTER:  synthesize_quick_4d("t2star", shape, FMAP_EPI_PARAMS["n_volumes"],
                    tuple(voxel_size), rng)

        A13 (fmap geometry, line ~671):
          BEFORE: structured_noise_4d(FMAP_EPI_PARAMS["shape_spatial"],
                    FMAP_EPI_PARAMS["n_volumes"], rng)
                  with rng = np.random.default_rng(5678) and drifted voxel size
          AFTER:  synthesize_quick_4d("t2star", FMAP_EPI_PARAMS["shape_spatial"],
                    FMAP_EPI_PARAMS["n_volumes"],
                    tuple(drifted_voxel_size), rng)
                  with rng = np.random.default_rng(5678) (unchanged)
          Note: drifted_voxel_size is already computed earlier in A13 (the adversary's intended
          geometric defect); passing it as voxel_size produces tissue data resampled to the
          wrong grid, which is exactly what A13 tests.

        All adversary-specific logic (file paths, NIfTI overwriting, sidecar manipulation,
        adversary flags) is UNCHANGED. Only the data-fill calls are migrated.
      </spec>
      <dependencies>C4 (needs synthesize_quick_3d, synthesize_quick_4d from tissue.py)</dependencies>
      <risk>medium - 7 call sites across 5 adversary functions; each must preserve the adversary's intended structural defect while switching the data fill. Per-call-site verification required.</risk>
      <rollback>Revert adversaries.py to prior state</rollback>
    </change>

    <change id="C9" priority="P0" source_item="adversary transparency finding (implement:plan codebase audit)">
      <file path="tools/simulated_bids/noise.py" action="delete" />
      <description>Delete noise.py. After C6 (modalities.py migration) and C8 (adversaries.py migration), no module imports structured_noise_3d or structured_noise_4d. Retaining noise.py would leave a dead module that could be accidentally re-imported, reintroducing the signal-quality confound.</description>
      <spec>
        Pre-condition verification (MANDATORY before deletion):
          grep -rn "from .noise import\|from noise import\|import noise" tools/simulated_bids/
          must return zero matches after C6 and C8 are applied.

        If any matches remain, HALT and report the unexpected importer to the user.

        Delete: tools/simulated_bids/noise.py
      </spec>
      <dependencies>C6 (removes modalities.py noise import), C8 (removes adversaries.py noise import)</dependencies>
      <risk>low - deletion of dead module; pre-condition grep prevents accidental breakage</risk>
      <rollback>Restore noise.py from git (git checkout HEAD -- tools/simulated_bids/noise.py)</rollback>
    </change>
  </changes>

  <execution_order>C1, C2, C3, C4, C5, C6, C7, C8, C9</execution_order>

  <notes>
    - C1 is executed by the orchestrator (network download), not a dispatched agent.
    - C2 and C3 are independent and can be dispatched in parallel after C1 completes.
    - C4 depends on C1 and C2 (needs the BrainWeb file and intensity tables).
    - C5 depends on C2 and C4 (needs config constants and tissue synthesis functions).
    - C6 depends on C3, C4, C5 (needs all three new modules).
    - C7 depends on C6 (needs the updated modalities.py signatures).
    - C8 depends on C4 (needs tissue.py convenience functions). Independent of C6 and C7.
    - C9 depends on C6 AND C8 (both must complete before deletion is safe). Pre-condition grep enforced.
    - No existing tests are modified (test updates are target_mode="test" in the brainstorm, out of scope for this implement).
    - Expected generation time increase: ~30 min (current) to ~2-4 hours (tissue synthesis) for the full 17-subject x 3-session dataset.
  </notes>
</implement_plan>
