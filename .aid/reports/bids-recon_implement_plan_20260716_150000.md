<implement_plan>
  <meta project="bids-recon" mode="implement" submodule="plan" timestamp="2026-07-16T15:00:00-05:00" />
  <input_reports>
    <report path="bids-recon_brainstorm_20260716_120000.md" mode="brainstorm" key_items="3" />
  </input_reports>

  <corrections>
    Adversary A11 in the brainstorm report specifies "InstitutionName in BIDS sidecar." InstitutionName is NOT on the current SIDECAR_DENY_LIST (it was removed in a prior change; see stage4_assemble.py). The deny list contains: PatientAge, PatientBirthDate, PatientID, PatientName, PatientSex, PatientSize, PatientWeight, SeriesInstanceUID, StudyID, StudyInstanceUID, AccessionNumber, ReferringPhysicianName, PerformedProcedureStepDescription. A11 is corrected to: "Surviving deny-listed field (PatientSex) in a BIDS sidecar." Fabricated institutional identifiers (e.g., "Simulated Brain Institute") are retained in clean sidecars; they are non-traceable.
  </corrections>

  <changes>
    <change id="C1" priority="P0" source_item="brainstorm action item 1 (generation script), action item 2 (adversary matrix)">
      <file path="tools/simulated_bids/__init__.py" action="create" />
      <file path="tools/simulated_bids/config.py" action="create" />
      <file path="tools/simulated_bids/noise.py" action="create" />
      <description>Package skeleton, acquisition parameter configuration, demographics table, and structured noise generator. This is the foundation all other modules depend on.</description>
      <spec>
## tools/simulated_bids/__init__.py

Empty file. Package marker only.

## tools/simulated_bids/config.py

All constants and configuration for the simulated dataset.

```python
"""Configuration constants for the simulated BIDS dataset generator."""
from __future__ import annotations
import numpy as np

# ---------------------------------------------------------------------------
# Scanner (non-PHI; institutional IDs fabricated, scanner model sampled)
# ---------------------------------------------------------------------------
SCANNER = {
    "Modality": "MR",
    "MagneticFieldStrength": 3,
    "ImagingFrequency": 123.218,
    "Manufacturer": "Siemens",
    "ManufacturersModelName": "MAGNETOM Prisma",
    "InstitutionName": "Simulated Brain Institute",
    "InstitutionalDepartmentName": "Simulated Neuroimaging Center",
    "InstitutionAddress": "123 Simulation Ave, Faketown, ST, US, 00000",
    "DeviceSerialNumber": "SIM001",
    "StationName": "SimScanner",
    "BodyPart": "BRAIN",
    "PatientPosition": "HFS",
    "SoftwareVersions": "syngo MR XA30",
    "NonlinearGradientCorrection": False,
    "ConversionSoftware": "simulated",
    "ConversionSoftwareVersion": "1.0.0",
}

# ---------------------------------------------------------------------------
# Acquisition parameters (moments sampled from real data)
# ---------------------------------------------------------------------------
T1W_PARAMS = {
    "shape": (176, 256, 256),
    "voxel_size": (1.0, 1.0, 1.0),
    "RepetitionTime": 2.5,
    "EchoTime": 0.00214,
    "FlipAngle": 8,
    "InversionTime": 1.06,
    "MRAcquisitionType": "3D",
    "ScanningSequence": "GR\\IR",
    "SequenceVariant": "SK\\SP\\MP",
    "ImageType": ["ORIGINAL", "PRIMARY", "M", "NONE", "MAGNITUDE"],
    "PulseSequenceName": "tfl_me3d1_16ns",
    "SeriesDescription": "ABCD_T1w_MPR_vNav",
    "ProtocolName": "ABCD_T1w_MPR_vNav",
}

T2W_PARAMS = {
    "shape": (176, 256, 256),
    "voxel_size": (1.0, 1.0, 1.0),
    "RepetitionTime": 3.2,
    "EchoTime": 0.564,
    "FlipAngle": 120,
    "MRAcquisitionType": "3D",
    "ScanningSequence": "SE",
    "SequenceVariant": "SK\\SP",
    "ImageType": ["ORIGINAL", "PRIMARY", "M", "NONE", "MAGNITUDE"],
    "PulseSequenceName": "spc_314ns",
    "SeriesDescription": "ABCD_T2w_SPC_vNav",
    "ProtocolName": "ABCD_T2w_SPC_vNav",
}

BOLD_PARAMS = {
    "shape_spatial": (90, 90, 60),
    "voxel_size": (2.4, 2.4, 2.4),
    "RepetitionTime": 0.8,
    "EchoTime": 0.03,
    "FlipAngle": 52,
    "MultibandAccelerationFactor": 6,
    "MRAcquisitionType": "2D",
    "ScanningSequence": "EP",
    "SequenceVariant": "SK\\SS",
    "ImageType": ["ORIGINAL", "PRIMARY", "FMRI", "NONE", "MAGNITUDE"],
    "PulseSequenceName": "epfid2d1_90",
    "EffectiveEchoSpacing": 0.000510012,
    "TotalReadoutTime": 0.045391,
    "PhaseEncodingDirection": "j",
    "BandwidthPerPixelPhaseEncode": 21.786,
    "PixelBandwidth": 2778,
    "DwellTime": 2e-06,
    "BaseResolution": 90,
    "n_slices_per_mb_group": 10,  # 60 slices / MB6
}

BOLD_REST_VOLUMES = 383
BOLD_ENBACK_VOLUMES = 370

DWI_PARAMS = {
    "shape_spatial": (140, 140, 81),
    "voxel_size": (1.7, 1.7, 1.7),
    "RepetitionTime": 4.2,
    "EchoTime": 0.0892,
    "FlipAngle": 90,
    "MultibandAccelerationFactor": 3,
    "MRAcquisitionType": "2D",
    "ScanningSequence": "EP",
    "SequenceVariant": "SK\\SS",
    "ImageType": ["ORIGINAL", "PRIMARY", "DIFFUSION", "NONE", "MAGNITUDE"],
    "PulseSequenceName": "epse2d1_140",
    "EffectiveEchoSpacing": 0.000689998,
    "TotalReadoutTime": 0.0959097,
    "PhaseEncodingDirection": "j",
    "BaseResolution": 140,
    "n_volumes": 103,
    "n_b0": 7,
    "b_values": [0, 500, 1000, 2000, 3000],
    "SeriesDescription": "ABCD_dMRI",
    "ProtocolName": "ABCD_dMRI",
}

FMAP_EPI_PARAMS = {
    "shape_spatial": (90, 90, 60),
    "voxel_size": (2.4, 2.4, 2.4),
    "n_volumes": 3,
    "EchoTime": 0.08,
    "RepetitionTime": 7.033,
    "EffectiveEchoSpacing": 0.000510012,
    "TotalReadoutTime": 0.045391,
    "ImageType": ["ORIGINAL", "PRIMARY", "FMRI", "NONE", "MAGNITUDE"],
}

# ---------------------------------------------------------------------------
# Modality inventory per clean subject-session (reference only)
# ---------------------------------------------------------------------------
# Each entry: (modality_type, task_or_acq, n_runs)
CLEAN_INVENTORY = [
    ("T1w", None, 1),
    ("T2w", None, 1),
    ("bold_rest", "rest", 3),
    ("bold_enback", "emotionalnback", 2),
    ("dwi", None, 1),
    ("fmap_func", "func", 2),   # 2 AP/PA pairs
    ("fmap_dwi", "dwi", 1),     # 1 AP/PA pair
]

# Fieldmap association structure (clean baseline):
# pepolarfunc01 -> enback runs 1-2
# pepolarfunc02 -> rest runs 1-3
# pepolardwi01  -> dwi run

# ---------------------------------------------------------------------------
# Demographics (fully fabricated, uniform distributions, ages 9-16)
# ---------------------------------------------------------------------------
# Baseline ages (ses-01) uniform ~9-12; +2y per session; full range 9-16.
DEMOGRAPHICS = [
    {"participant_id": "sub-001", "sex": "F", "handedness": "R", "age_ses01": 9.2},
    {"participant_id": "sub-002", "sex": "M", "handedness": "L", "age_ses01": 9.8},
    {"participant_id": "sub-003", "sex": "F", "handedness": "A", "age_ses01": 10.1},
    {"participant_id": "sub-004", "sex": "M", "handedness": "R", "age_ses01": 10.5},
    {"participant_id": "sub-005", "sex": "F", "handedness": "L", "age_ses01": 10.9},
    {"participant_id": "sub-006", "sex": "M", "handedness": "A", "age_ses01": 11.3},
    {"participant_id": "sub-007", "sex": "F", "handedness": "R", "age_ses01": 11.7},
    {"participant_id": "sub-008", "sex": "M", "handedness": "R", "age_ses01": 12.0},
    {"participant_id": "sub-009", "sex": "F", "handedness": "L", "age_ses01": 12.4},
    {"participant_id": "sub-010", "sex": "M", "handedness": "A", "age_ses01": 12.0},
]

SESSION_INTERVAL_YEARS = 2.0
SESSIONS = ["ses-01", "ses-02", "ses-03"]
N_SUBJECTS = 10

def age_at_session(base_age: float, ses_index: int) -> float:
    """Return age for a given session index (0-based)."""
    return round(base_age + ses_index * SESSION_INTERVAL_YEARS, 1)
```

## tools/simulated_bids/noise.py

Structured noise generator: low-frequency spatial gradient plus Gaussian noise.

```python
"""Structured noise generation for synthetic NIfTI volumes."""
from __future__ import annotations
import numpy as np

def structured_noise_3d(shape: tuple[int, int, int], rng: np.random.Generator) -> np.ndarray:
    """Generate a single 3D volume of structured noise.

    Creates a smooth low-frequency gradient (meshgrid-based) plus
    additive Gaussian noise. The gradient provides spatial structure
    that compresses well under gzip, while the noise prevents
    constant-value rejection by downstream tools.

    Parameters
    ----------
    shape : tuple of 3 ints
        (x, y, z) dimensions.
    rng : numpy.random.Generator
        Seeded random generator for reproducibility.

    Returns
    -------
    np.ndarray
        float32 array of shape *shape*.
    """
    x = np.linspace(0, 1, shape[0], dtype=np.float32)
    y = np.linspace(0, 1, shape[1], dtype=np.float32)
    z = np.linspace(0, 1, shape[2], dtype=np.float32)
    gx, gy, gz = np.meshgrid(x, y, z, indexing="ij")
    gradient = (gx + 0.5 * gy + 0.3 * gz).astype(np.float32)
    noise = rng.normal(0, 0.15, shape).astype(np.float32)
    return gradient + noise


def structured_noise_4d(
    shape_3d: tuple[int, int, int],
    n_volumes: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate a 4D volume stack with per-volume structured noise.

    Each volume shares the same gradient pattern but with independent
    Gaussian noise, simulating temporal variation in fMRI/DWI data.

    Parameters
    ----------
    shape_3d : tuple of 3 ints
        Spatial (x, y, z) dimensions.
    n_volumes : int
        Number of volumes (4th dimension).
    rng : numpy.random.Generator
        Seeded random generator.

    Returns
    -------
    np.ndarray
        float32 array of shape (*shape_3d, n_volumes).
    """
    x = np.linspace(0, 1, shape_3d[0], dtype=np.float32)
    y = np.linspace(0, 1, shape_3d[1], dtype=np.float32)
    z = np.linspace(0, 1, shape_3d[2], dtype=np.float32)
    gx, gy, gz = np.meshgrid(x, y, z, indexing="ij")
    gradient = (gx + 0.5 * gy + 0.3 * gz).astype(np.float32)

    out = np.empty((*shape_3d, n_volumes), dtype=np.float32)
    for vol in range(n_volumes):
        noise = rng.normal(0, 0.15, shape_3d).astype(np.float32)
        out[..., vol] = gradient + noise
    return out
```
      </spec>
      <dependencies>none</dependencies>
      <risk>low - foundational constants and pure functions with no external side effects</risk>
      <rollback>Delete tools/simulated_bids/ directory</rollback>
    </change>

    <change id="C2" priority="P0" source_item="brainstorm action item 1 (generation script)">
      <file path="tools/simulated_bids/modalities.py" action="create" />
      <description>NIfTI + JSON sidecar generators for all modalities: T1w, T2w, BOLD (rest + enback with SBRef), DWI (with bval/bvec and SBRef files), and fieldmap EPI pairs. Each generator writes files to disk and returns the list of created paths for scans.tsv.</description>
      <spec>
## tools/simulated_bids/modalities.py

All modality generators. Each function creates the NIfTI (.nii.gz), JSON sidecar, and any ancillary files (bval, bvec) for one acquisition.

**Key design decisions:**
- Every NIfTI is written with sform_code=1 (scanner anat), qform_code=1, matching affine.
- Affines are diagonal: np.diag([*voxel_size, 1.0]) with a small translation offset.
- SliceTiming for BOLD: generated as a repeating MB-group pattern. With 60 slices and MB=6, there are 10 slice groups. Timing = [group_index * (TR / n_groups)] repeated MB times. All values in seconds.
- bval format: single-row, space-separated integers.
- bvec format: 3 rows (x, y, z), space-separated floats, unit vectors for b>0.
- All JSON files written with json.dump(dict, f, indent=4, sort_keys=False).

**Function signatures:**

```python
"""Modality generators for the simulated BIDS dataset."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import nibabel as nib
from .config import (
    SCANNER, T1W_PARAMS, T2W_PARAMS, BOLD_PARAMS,
    BOLD_REST_VOLUMES, BOLD_ENBACK_VOLUMES,
    DWI_PARAMS, FMAP_EPI_PARAMS,
)
from .noise import structured_noise_3d, structured_noise_4d


def _make_affine(voxel_size: tuple[float, ...]) -> np.ndarray:
    """Diagonal affine with small translation offset."""
    aff = np.diag([*voxel_size, 1.0]).astype(np.float64)
    aff[:3, 3] = [-voxel_size[0] * 5, -voxel_size[1] * 5, -voxel_size[2] * 2]
    return aff


def _save_nifti(data: np.ndarray, affine: np.ndarray, pixdim4: float,
                out_path: Path) -> None:
    """Write a NIfTI-1 image with sform_code=qform_code=1."""
    img = nib.Nifti1Image(data, affine)
    hdr = img.header
    hdr.set_sform(affine, code=1)
    hdr.set_qform(affine, code=1)
    hdr["pixdim"][4] = pixdim4
    nib.save(img, str(out_path))


def _bold_slice_timing(n_slices: int, mb_factor: int, tr: float) -> list[float]:
    """Generate CMRR multiband slice timing array.

    Pattern: n_slices/mb_factor groups, each group's time =
    group_index * (TR / n_groups), repeated mb_factor times.
    """
    n_groups = n_slices // mb_factor
    group_times = [round(i * tr / n_groups, 4) for i in range(n_groups)]
    return group_times * mb_factor


def _base_sidecar(params: dict, series_num: int = 1) -> dict:
    """Merge SCANNER constants with modality-specific params."""
    sc = dict(SCANNER)
    sc.update({
        "SeriesNumber": series_num,
        "AcquisitionNumber": 1,
    })
    for key in ["RepetitionTime", "EchoTime", "FlipAngle", "MRAcquisitionType",
                "ScanningSequence", "SequenceVariant", "ImageType",
                "PulseSequenceName", "SeriesDescription", "ProtocolName",
                "SliceThickness", "BaseResolution",
                "MultibandAccelerationFactor", "EffectiveEchoSpacing",
                "TotalReadoutTime", "PhaseEncodingDirection",
                "BandwidthPerPixelPhaseEncode", "PixelBandwidth", "DwellTime",
                "InversionTime"]:
        if key in params:
            sc[key] = params[key]
    if "voxel_size" in params:
        sc["SliceThickness"] = params["voxel_size"][2]
    return sc


def generate_t1w(out_dir: Path, sub: str, ses: str, run: int,
                 rng: np.random.Generator) -> list[Path]:
    """Generate T1w NIfTI + JSON. Returns list of created NIfTI paths."""
    anat_dir = out_dir / sub / ses / "anat"
    anat_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{sub}_{ses}_run-{run:02d}_T1w"

    data = structured_noise_3d(T1W_PARAMS["shape"], rng)
    _save_nifti(data, _make_affine(T1W_PARAMS["voxel_size"]),
                T1W_PARAMS["RepetitionTime"], anat_dir / f"{stem}.nii.gz")

    sc = _base_sidecar(T1W_PARAMS)
    with open(anat_dir / f"{stem}.json", "w") as f:
        json.dump(sc, f, indent=4)

    return [anat_dir / f"{stem}.nii.gz"]


def generate_t2w(out_dir: Path, sub: str, ses: str, run: int,
                 rng: np.random.Generator) -> list[Path]:
    """Generate T2w NIfTI + JSON. Returns list of created NIfTI paths."""
    anat_dir = out_dir / sub / ses / "anat"
    anat_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{sub}_{ses}_run-{run:02d}_T2w"

    data = structured_noise_3d(T2W_PARAMS["shape"], rng)
    _save_nifti(data, _make_affine(T2W_PARAMS["voxel_size"]),
                T2W_PARAMS["RepetitionTime"], anat_dir / f"{stem}.nii.gz")

    sc = _base_sidecar(T2W_PARAMS)
    with open(anat_dir / f"{stem}.json", "w") as f:
        json.dump(sc, f, indent=4)

    return [anat_dir / f"{stem}.nii.gz"]


def generate_bold(out_dir: Path, sub: str, ses: str, task: str, run: int,
                  n_volumes: int, b0_field_source: str,
                  rng: np.random.Generator) -> list[Path]:
    """Generate BOLD NIfTI + SBRef NIfTI + JSON sidecars.

    Returns list of created NIfTI paths (bold + sbref).

    The BOLD sidecar includes: TaskName, SliceTiming, B0FieldSource.
    The SBRef sidecar is identical minus SliceTiming.
    """
    func_dir = out_dir / sub / ses / "func"
    func_dir.mkdir(parents=True, exist_ok=True)
    bold_stem = f"{sub}_{ses}_task-{task}_run-{run:02d}_bold"
    sbref_stem = f"{sub}_{ses}_task-{task}_run-{run:02d}_sbref"

    # BOLD 4D
    data = structured_noise_4d(BOLD_PARAMS["shape_spatial"], n_volumes, rng)
    _save_nifti(data, _make_affine(BOLD_PARAMS["voxel_size"]),
                BOLD_PARAMS["RepetitionTime"], func_dir / f"{bold_stem}.nii.gz")

    sc = _base_sidecar(BOLD_PARAMS)
    sc["TaskName"] = task
    sc["SliceTiming"] = _bold_slice_timing(
        BOLD_PARAMS["shape_spatial"][2],
        BOLD_PARAMS["MultibandAccelerationFactor"],
        BOLD_PARAMS["RepetitionTime"],
    )
    sc["B0FieldSource"] = [b0_field_source]
    sc["SeriesDescription"] = f"ABCD_fMRI_{task}"
    sc["ProtocolName"] = f"ABCD_fMRI_{task}"
    with open(func_dir / f"{bold_stem}.json", "w") as f:
        json.dump(sc, f, indent=4)

    # SBRef (single volume, same spatial dims)
    sbref_data = structured_noise_3d(BOLD_PARAMS["shape_spatial"], rng)
    _save_nifti(sbref_data, _make_affine(BOLD_PARAMS["voxel_size"]),
                BOLD_PARAMS["RepetitionTime"], func_dir / f"{sbref_stem}.nii.gz")

    sbref_sc = dict(sc)
    del sbref_sc["SliceTiming"]
    with open(func_dir / f"{sbref_stem}.json", "w") as f:
        json.dump(sbref_sc, f, indent=4)

    return [func_dir / f"{bold_stem}.nii.gz", func_dir / f"{sbref_stem}.nii.gz"]


def generate_dwi(out_dir: Path, sub: str, ses: str,
                 b0_field_source: str,
                 rng: np.random.Generator) -> list[Path]:
    """Generate DWI NIfTI + JSON + bval + bvec + 3 SBRef files.

    DWI file: dir-PA_run-04_dwi (matching real pipeline output naming).
    SBRef files: dir-PA_run-01_sbref, dir-AP_run-02_sbref, dir-PA_run-03_sbref.

    bval: single row, space-separated. 103 values drawn from [0, 500, 1000, 2000, 3000]
    with ~7 b=0 volumes distributed evenly.

    bvec: 3 rows (x, y, z). Unit vectors for b>0 volumes; [0,0,0] for b=0.
    """
    dwi_dir = out_dir / sub / ses / "dwi"
    dwi_dir.mkdir(parents=True, exist_ok=True)
    created = []

    # Main DWI volume
    dwi_stem = f"{sub}_{ses}_dir-PA_run-04_dwi"
    n_vols = DWI_PARAMS["n_volumes"]
    data = structured_noise_4d(DWI_PARAMS["shape_spatial"], n_vols, rng)
    _save_nifti(data, _make_affine(DWI_PARAMS["voxel_size"]),
                DWI_PARAMS["RepetitionTime"], dwi_dir / f"{dwi_stem}.nii.gz")
    created.append(dwi_dir / f"{dwi_stem}.nii.gz")

    bvals = _generate_bvals(n_vols, DWI_PARAMS["n_b0"],
                            DWI_PARAMS["b_values"], rng)
    with open(dwi_dir / f"{dwi_stem}.bval", "w") as f:
        f.write(" ".join(str(b) for b in bvals) + "\n")

    bvecs = _generate_bvecs(bvals, rng)
    with open(dwi_dir / f"{dwi_stem}.bvec", "w") as f:
        for row in bvecs:
            f.write(" ".join(f"{v:.6f}" for v in row) + "\n")

    # DWI JSON sidecar
    sc = _base_sidecar(DWI_PARAMS)
    sc["B0FieldSource"] = [b0_field_source]
    with open(dwi_dir / f"{dwi_stem}.json", "w") as f:
        json.dump(sc, f, indent=4)

    # 3 SBRef files (single-volume each)
    for dir_label, run_num in [("PA", 1), ("AP", 2), ("PA", 3)]:
        sbref_stem = f"{sub}_{ses}_dir-{dir_label}_run-{run_num:02d}_sbref"
        sbref_data = structured_noise_3d(DWI_PARAMS["shape_spatial"], rng)
        _save_nifti(sbref_data, _make_affine(DWI_PARAMS["voxel_size"]),
                    DWI_PARAMS["RepetitionTime"],
                    dwi_dir / f"{sbref_stem}.nii.gz")
        sbref_sc = _base_sidecar(DWI_PARAMS)
        sbref_sc["PhaseEncodingDirection"] = "j" if dir_label == "PA" else "j-"
        with open(dwi_dir / f"{sbref_stem}.json", "w") as f:
            json.dump(sbref_sc, f, indent=4)
        created.append(dwi_dir / f"{sbref_stem}.nii.gz")

    return created


def _generate_bvals(n_vols, n_b0, b_values, rng):
    """Generate bval array with evenly spaced b=0 volumes."""
    bvals = [0] * n_vols
    b0_indices = set(np.linspace(0, n_vols - 1, n_b0, dtype=int))
    non_zero_bvals = [b for b in b_values if b > 0]
    for i in range(n_vols):
        if i not in b0_indices:
            bvals[i] = rng.choice(non_zero_bvals)
    return bvals


def _generate_bvecs(bvals, rng):
    """Generate unit-vector bvecs for b>0, zero-vectors for b=0."""
    n = len(bvals)
    bvecs = np.zeros((3, n), dtype=np.float64)
    for i, b in enumerate(bvals):
        if b > 0:
            vec = rng.normal(0, 1, 3)
            vec /= np.linalg.norm(vec)
            bvecs[:, i] = vec
    return bvecs


def generate_fmap_pair(out_dir: Path, sub: str, ses: str,
                       acq: str, run: int,
                       intended_for: list[str],
                       b0_field_id: str,
                       rng: np.random.Generator) -> list[Path]:
    """Generate an AP/PA fieldmap EPI pair with IntendedFor and B0FieldIdentifier.

    Creates two files:
      fmap/{sub}_{ses}_acq-{acq}_dir-PA_run-{run:02d}_epi.nii.gz  (PE=j)
      fmap/{sub}_{ses}_acq-{acq}_dir-AP_run-{run:02d}_epi.nii.gz  (PE=j-)

    Both sidecars share: IntendedFor (subject-relative paths), B0FieldIdentifier.
    """
    fmap_dir = out_dir / sub / ses / "fmap"
    fmap_dir.mkdir(parents=True, exist_ok=True)
    created = []

    for dir_label, pe_dir in [("PA", "j"), ("AP", "j-")]:
        stem = f"{sub}_{ses}_acq-{acq}_dir-{dir_label}_run-{run:02d}_epi"
        data = structured_noise_4d(FMAP_EPI_PARAMS["shape_spatial"],
                                   FMAP_EPI_PARAMS["n_volumes"], rng)
        _save_nifti(data, _make_affine(FMAP_EPI_PARAMS["voxel_size"]),
                    FMAP_EPI_PARAMS["RepetitionTime"],
                    fmap_dir / f"{stem}.nii.gz")

        sc = _base_sidecar(FMAP_EPI_PARAMS)
        sc["PhaseEncodingDirection"] = pe_dir
        sc["IntendedFor"] = intended_for
        sc["B0FieldIdentifier"] = [b0_field_id]
        with open(fmap_dir / f"{stem}.json", "w") as f:
            json.dump(sc, f, indent=4)
        created.append(fmap_dir / f"{stem}.nii.gz")

    return created
```

Each `generate_*` function is self-contained: it creates directories, writes NIfTI + sidecar, and returns the list of NIfTI paths created (for scans.tsv population). All functions accept a seeded `rng` for reproducibility.
      </spec>
      <dependencies>C1</dependencies>
      <risk>medium - largest single module; NIfTI header details (sform/qform, pixdim) must be correct for downstream tools</risk>
      <rollback>Delete tools/simulated_bids/modalities.py</rollback>
    </change>

    <change id="C3" priority="P0" source_item="brainstorm action item 2 (adversary matrix)">
      <file path="tools/simulated_bids/adversaries.py" action="create" />
      <description>Adversary assignment matrix mapping each of 28 adversary types to specific subject-session-target slots, plus mutation functions that modify already-generated BIDS files to introduce each defect. Correction: A11 uses PatientSex (deny-listed), not InstitutionName (not deny-listed).</description>
      <spec>
## tools/simulated_bids/adversaries.py

Two components: (1) the ADVERSARY_MATRIX constant and (2) per-adversary mutation functions.

### ADVERSARY_MATRIX

A dict mapping subject_id (str) to a list of adversary specs. Each spec is a dict:
```python
{"id": "A1", "sessions": ["ses-02"], "target": "<description>", "details": {...}}
```

Full matrix (28 types across 9 subjects, severity gradient 1 to 7):

```python
ADVERSARY_MATRIX = {
    "sub-002": [  # Mild (1 adversary)
        {"id": "A9", "sessions": ["ses-02"], "target": "missing_T2w"},
    ],
    "sub-003": [  # Mild (2 adversaries)
        {"id": "A10", "sessions": ["ses-01"], "target": "bold_rest_run01_missing_ees"},
        {"id": "A27", "sessions": ["ses-03"], "target": "extra_localizer_series"},
    ],
    "sub-004": [  # Mild-Moderate (2 adversaries)
        {"id": "A24", "sessions": ["ses-02", "ses-03"], "target": "tr_drift_rest_bold",
         "details": {"ses-02": 0.801, "ses-03": 0.802}},
        {"id": "A28", "sessions": ["ses-01", "ses-02", "ses-03"],
         "target": "locale_decimal_participants_tsv"},
    ],
    "sub-005": [  # Moderate (3 adversaries)
        {"id": "A3", "sessions": ["ses-01"], "target": "protocol_typo_rest",
         "details": {"wrong": "ABCD_fMRI_rset", "correct": "ABCD_fMRI_rest"}},
        {"id": "A16", "sessions": ["ses-02"], "target": "t1w_pixdim4_mismatch",
         "details": {"pixdim4": 0.0, "json_tr": 2.5}},
        {"id": "A21", "sessions": ["ses-03"], "target": "enback_run01_missing_taskname"},
    ],
    "sub-006": [  # Moderate (3 adversaries)
        {"id": "A1", "sessions": ["ses-02"], "target": "missing_session"},
        {"id": "A13", "sessions": ["ses-01"], "target": "fmap_geometry_mismatch",
         "details": {"fmap_voxel": 2.5}},
        {"id": "A20", "sessions": ["ses-03"], "target": "slicetiming_milliseconds"},
    ],
    "sub-007": [  # Moderate-Severe (4 adversaries)
        {"id": "A4", "sessions": ["ses-01"], "target": "scan_restart_rest",
         "details": {"truncated_volumes": 140, "extra_run": 4}},
        {"id": "A8", "sessions": ["ses-02"], "target": "wrong_mb_enback",
         "details": {"wrong_mb": 4}},
        {"id": "A17", "sessions": ["ses-03"], "target": "t1w_qform_sform_disagree",
         "details": {"z_offset_mm": 0.5}},
        {"id": "A22", "sessions": ["ses-01"], "target": "intendedfor_path_format",
         "details": {"format": "bids_uri"}},
    ],
    "sub-008": [  # Severe (5 adversaries)
        {"id": "A5", "sessions": ["ses-01", "ses-02"], "target": "protocol_rename",
         "details": {"ses-01_desc": "ABCD_fMRI_faces",
                     "ses-02_desc": "ABCD_fMRI_emotion"}},
        {"id": "A11", "sessions": ["ses-02"], "target": "surviving_phi_field",
         "details": {"field": "PatientSex", "value": "F"}},
        {"id": "A14", "sessions": ["ses-03"], "target": "orphan_sbref"},
        {"id": "A18", "sessions": ["ses-01"], "target": "dwi_scl_slope_nan"},
        {"id": "A25", "sessions": ["ses-03"], "target": "duplicate_rest_run"},
    ],
    "sub-009": [  # Severe (6 adversaries)
        {"id": "A2", "sessions": ["ses-03"], "target": "empty_session"},
        {"id": "A6", "sessions": ["ses-01"], "target": "mixed_patient_ids",
         "details": {"id_a": "SIM_PT_009A", "id_b": "SIM_PT_009B"}},
        {"id": "A12", "sessions": ["ses-02"], "target": "bval_bvec_mismatch",
         "details": {"bval_count": 102, "bvec_count": 103}},
        {"id": "A15", "sessions": ["ses-01"], "target": "duplicate_sidecar_key_casing"},
        {"id": "A19", "sessions": ["ses-02"], "target": "mixed_dtype_across_runs",
         "details": {"run01_dtype": "int16", "run02_dtype": "float32"}},
        {"id": "A23", "sessions": ["ses-01"], "target": "fmap_trt_mismatch",
         "details": {"fmap_trt": 0.060, "bold_trt": 0.045391}},
    ],
    "sub-010": [  # Extreme (7 adversaries)
        {"id": "A7", "sessions": ["ses-01"], "target": "stale_extra_series",
         "details": {"desc": "OtherStudy_motor_bold"}},
        {"id": "A26", "sessions": ["ses-02"], "target": "ffs_orientation"},
        {"id": "A3", "sessions": ["ses-03"], "target": "protocol_typo_enback",
         "details": {"wrong": "ABCD_fMRI_emotionalnbck",
                     "correct": "ABCD_fMRI_emotionalnback"}},
        {"id": "A6", "sessions": ["ses-02"], "target": "mixed_patient_ids",
         "details": {"id_a": "SIM_PT_010A", "id_b": "SIM_PT_010B"}},
        {"id": "A9", "sessions": ["ses-03"], "target": "missing_dwi"},
        {"id": "A17", "sessions": ["ses-01"], "target": "bold_qform_sform_disagree",
         "details": {"z_offset_mm": 0.3}},
        {"id": "A20", "sessions": ["ses-02"],
         "target": "slicetiming_milliseconds_enback"},
    ],
}
```

### Mutation functions

Each adversary has an `apply_A{n}(out_dir, sub, spec)` function that modifies files in place. All mutations operate on already-generated clean files. Functions grouped by mutation type:

**File deletion mutations** (A1, A9):
- `apply_A1`: `shutil.rmtree(out_dir / sub / ses)` for the specified session.
- `apply_A9`: Delete all files matching the target modality pattern in the specified session.

**File addition mutations** (A4, A7, A14, A25, A27):
- `apply_A4`: Truncate one rest BOLD to `truncated_volumes` frames (re-write NIfTI), then generate a new run with the next index (full volumes).
- `apply_A7`: Generate an extra BOLD NIfTI + sidecar with the stale SeriesDescription in func/.
- `apply_A14`: Remove the BOLD NIfTI for one run but leave its SBRef in place (orphaned SBRef).
- `apply_A25`: Copy rest run-01 files to run-04 (duplicate).
- `apply_A27`: Generate a localizer NIfTI (small 3D, e.g., 256x256x3) in func/ with non-standard naming.

**Sidecar field mutations** (A3, A5, A8, A10, A11, A15, A20, A21, A24):
- `apply_A3`: Rewrite SeriesDescription, ProtocolName, and TaskName in the target sidecar with the typo value.
- `apply_A5`: In ses-01, change SeriesDescription/ProtocolName to faces variant; in ses-02, change to emotion variant. Both sidecars keep identical acquisition params (same physical sequence, renamed across sessions).
- `apply_A8`: Change MultibandAccelerationFactor in the target sidecar.
- `apply_A10`: Delete EffectiveEchoSpacing from the target sidecar.
- `apply_A11`: Add `"PatientSex": "F"` to the target sidecar (deny-listed field that survived scrubbing).
- `apply_A15`: Add `"repetitiontime": 0.8` alongside existing `"RepetitionTime": 0.8` (duplicate key with different casing).
- `apply_A20`: Multiply all SliceTiming values by 1000 (seconds to milliseconds).
- `apply_A21`: Delete TaskName from the target sidecar.
- `apply_A24`: Change RepetitionTime in sidecars for affected sessions (small parametric drift).

**NIfTI header mutations** (A16, A17, A18, A19, A26):
- `apply_A16`: Load NIfTI, set `hdr["pixdim"][4] = 0.0`, re-save.
- `apply_A17`: Load NIfTI, set qform with Z-offset differing from sform by the specified mm, re-save.
- `apply_A18`: Load NIfTI, set `hdr["scl_slope"] = np.nan`, re-save.
- `apply_A19`: Load run-01 NIfTI, cast data to int16, re-save with dtype=np.int16. Run-02 stays float32.
- `apply_A26`: Flip the Z-axis in the affine (negate 3rd diagonal element and offset), re-save. Simulates a feet-first-supine orientation error.

**Fieldmap mutations** (A13, A22, A23):
- `apply_A13`: Re-generate fmap pair NIfTI with 2.5mm voxels instead of 2.4mm; update affine and sidecar voxel-dependent fields. Geometry mismatch with target BOLD.
- `apply_A22`: Rewrite IntendedFor values to use `bids::sub-XXX/ses-YY/...` URI format instead of subject-relative paths.
- `apply_A23`: Change TotalReadoutTime in fmap sidecars to 0.060 (mismatched with BOLD's 0.045391).

**Gradient table mutations** (A12):
- `apply_A12`: Truncate bval file to 102 entries (remove last), leave bvec at 103 columns.

**Session-level mutations** (A2):
- `apply_A2`: Delete all NIfTI, JSON, bval, bvec files within the session but leave the empty subdirectory structure intact (anat/, func/, dwi/, fmap/ exist but are empty).

**PatientID mutations** (A6):
- `apply_A6`: Walk all JSON sidecars in the session. For the first half (by filename sort), add `"PatientID": id_a`; for the second half, add `"PatientID": id_b`. Both PatientID and PatientSex are on the deny list; their presence tests whether the scrub audit catches unscrubbed fields.

**TSV mutations** (A28):
- `apply_A28`: Post-process participants.tsv: for the target subject's age column, replace period with comma (locale-driven decimal separator error).

**Dispatcher:**
```python
def apply_adversaries(out_dir: Path, sub: str) -> list[str]:
    """Apply all adversaries assigned to a subject. Returns list of applied IDs."""
    specs = ADVERSARY_MATRIX.get(sub, [])
    applied = []
    for spec in specs:
        fn = globals()[f"apply_{spec['id']}"]
        fn(out_dir, sub, spec)
        applied.append(spec["id"])
    return applied
```

**Ordering constraint**: Adversaries that delete files (A1, A2, A9) must run AFTER sidecar/header mutations targeting the same session, or the mutations would fail on missing files. The dispatcher iterates the matrix list in order, so file-deletion adversaries are placed last in each subject's list when co-occurring with in-place mutations on the same session.
      </spec>
      <dependencies>C1, C2</dependencies>
      <risk>high - 28 distinct mutation functions; each must produce the intended defect without corrupting the overall BIDS structure in unintended ways; interaction effects between co-occurring adversaries on the same subject must not cause crashes during generation</risk>
      <rollback>Delete tools/simulated_bids/adversaries.py</rollback>
    </change>

    <change id="C4" priority="P0" source_item="brainstorm action item 1 (generation script)">
      <file path="tools/simulated_bids/scaffold.py" action="create" />
      <file path="tools/simulated_bids/__main__.py" action="create" />
      <description>BIDS scaffold file generators (dataset_description.json, participants.tsv, sessions.tsv, scans.tsv) and CLI entry point that orchestrates the full generation pipeline.</description>
      <spec>
## tools/simulated_bids/scaffold.py

Functions to write BIDS-required metadata files.

```python
"""BIDS scaffold file generators."""
from __future__ import annotations
import json
from pathlib import Path
from .config import DEMOGRAPHICS, SESSIONS, age_at_session


def write_dataset_description(out_dir: Path) -> None:
    """Write dataset_description.json with DatasetType=raw."""
    desc = {
        "Name": "Simulated BIDS Dataset",
        "BIDSVersion": "1.9.0",
        "DatasetType": "raw",
        "License": "CC0",
        "GeneratedBy": [{"Name": "simulated_bids", "Version": "1.0.0"}],
    }
    with open(out_dir / "dataset_description.json", "w") as f:
        json.dump(desc, f, indent=4)


def write_participants_tsv(out_dir: Path) -> None:
    """Write participants.tsv with fabricated demographics."""
    lines = ["participant_id\tage\tsex\thandedness"]
    for d in DEMOGRAPHICS:
        lines.append(
            f"{d['participant_id']}\t{d['age_ses01']}\t{d['sex']}\t{d['handedness']}"
        )
    (out_dir / "participants.tsv").write_text("\n".join(lines) + "\n")

    meta = {
        "age": {"Description": "Age at ses-01 in years", "Units": "years"},
        "sex": {
            "Description": "Biological sex",
            "Levels": {"M": "male", "F": "female"},
        },
        "handedness": {
            "Description": "Handedness",
            "Levels": {"R": "right", "L": "left", "A": "ambidextrous"},
        },
    }
    with open(out_dir / "participants.json", "w") as f:
        json.dump(meta, f, indent=4)


def write_sessions_tsv(out_dir: Path, sub: str, base_age: float) -> None:
    """Write {sub}_sessions.tsv with age per session."""
    sub_dir = out_dir / sub
    sub_dir.mkdir(parents=True, exist_ok=True)
    lines = ["session_id\tage"]
    for i, ses in enumerate(SESSIONS):
        age = age_at_session(base_age, i)
        lines.append(f"{ses}\t{age}")
    (sub_dir / f"{sub}_sessions.tsv").write_text("\n".join(lines) + "\n")

    meta = {"age": {"Description": "Age at session in years", "Units": "years"}}
    with open(sub_dir / f"{sub}_sessions.json", "w") as f:
        json.dump(meta, f, indent=4)


def write_scans_tsv(out_dir: Path, sub: str, ses: str,
                    nifti_paths: list[Path]) -> None:
    """Write {sub}_{ses}_scans.tsv listing all NIfTI files."""
    ses_dir = out_dir / sub / ses
    lines = ["filename\tacq_time"]
    for p in sorted(nifti_paths):
        rel = p.relative_to(ses_dir)
        lines.append(f"{rel}\tn/a")
    (ses_dir / f"{sub}_{ses}_scans.tsv").write_text("\n".join(lines) + "\n")
```

## tools/simulated_bids/__main__.py

CLI entry point. Run as: `conda run -n bids-recon python -m tools.simulated_bids ~/simulated-bids-dataset/`

```python
"""CLI entry point for the simulated BIDS dataset generator."""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path
import numpy as np

from .config import DEMOGRAPHICS, SESSIONS, N_SUBJECTS
from .config import BOLD_REST_VOLUMES, BOLD_ENBACK_VOLUMES
from .modalities import (
    generate_t1w, generate_t2w, generate_bold,
    generate_dwi, generate_fmap_pair,
)
from .scaffold import (
    write_dataset_description, write_participants_tsv,
    write_sessions_tsv, write_scans_tsv,
)
from .adversaries import apply_adversaries, ADVERSARY_MATRIX
from .manifest import write_manifest


def generate_clean_session(out_dir: Path, sub: str, ses: str,
                           rng: np.random.Generator) -> list[Path]:
    """Generate all clean modality files for one subject-session.

    Returns list of all NIfTI paths created.
    """
    all_paths = []

    # Anatomical
    all_paths.extend(generate_t1w(out_dir, sub, ses, run=1, rng=rng))
    all_paths.extend(generate_t2w(out_dir, sub, ses, run=1, rng=rng))

    # Functional: 3 rest runs + 2 enback runs
    for run in range(1, 4):
        all_paths.extend(generate_bold(
            out_dir, sub, ses, "rest", run, BOLD_REST_VOLUMES,
            b0_field_source="pepolarfunc02", rng=rng))
    for run in range(1, 3):
        all_paths.extend(generate_bold(
            out_dir, sub, ses, "emotionalnback", run, BOLD_ENBACK_VOLUMES,
            b0_field_source="pepolarfunc01", rng=rng))

    # DWI
    all_paths.extend(generate_dwi(
        out_dir, sub, ses, b0_field_source="pepolardwi01", rng=rng))

    # Fieldmaps
    # pepolarfunc01 -> enback runs 1-2
    enback_intended = [
        f"{ses}/func/{sub}_{ses}_task-emotionalnback_run-{r:02d}_bold.nii.gz"
        for r in range(1, 3)
    ]
    all_paths.extend(generate_fmap_pair(
        out_dir, sub, ses, "func", run=1,
        intended_for=enback_intended,
        b0_field_id="pepolarfunc01", rng=rng))

    # pepolarfunc02 -> rest runs 1-3
    rest_intended = [
        f"{ses}/func/{sub}_{ses}_task-rest_run-{r:02d}_bold.nii.gz"
        for r in range(1, 4)
    ]
    all_paths.extend(generate_fmap_pair(
        out_dir, sub, ses, "func", run=2,
        intended_for=rest_intended,
        b0_field_id="pepolarfunc02", rng=rng))

    # pepolardwi01 -> dwi
    dwi_intended = [f"{ses}/dwi/{sub}_{ses}_dir-PA_run-04_dwi.nii.gz"]
    all_paths.extend(generate_fmap_pair(
        out_dir, sub, ses, "dwi", run=1,
        intended_for=dwi_intended,
        b0_field_id="pepolardwi01", rng=rng))

    return all_paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a simulated BIDS dataset with adversarial examples.")
    parser.add_argument("output_dir", type=Path,
                        help="Root directory for the BIDS dataset.")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility.")
    args = parser.parse_args()

    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    t0 = time.time()

    # Phase 1: generate all subjects as clean
    print(f"Generating {N_SUBJECTS} subjects x {len(SESSIONS)} sessions...")
    for demo in DEMOGRAPHICS:
        sub = demo["participant_id"]
        sub_rng = np.random.default_rng(rng.integers(0, 2**31))
        for ses in SESSIONS:
            print(f"  {sub}/{ses}...", end=" ", flush=True)
            paths = generate_clean_session(out, sub, ses, sub_rng)
            write_scans_tsv(out, sub, ses, paths)
            print(f"{len(paths)} files")
        write_sessions_tsv(out, sub, demo["age_ses01"])

    # Phase 2: write scaffold
    write_dataset_description(out)
    write_participants_tsv(out)

    # Phase 3: apply adversarial mutations
    print("\nApplying adversarial mutations...")
    for sub in sorted(ADVERSARY_MATRIX):
        applied = apply_adversaries(out, sub)
        if applied:
            print(f"  {sub}: {', '.join(applied)}")

    # Phase 4: write manifest
    write_manifest(out)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed / 60:.1f} minutes. Dataset at: {out}")


if __name__ == "__main__":
    main()
```

The generation flow is:
1. Generate ALL 10 subjects as clean (correct demographics per subject).
2. Write dataset-level scaffold files.
3. Apply adversarial mutations to sub-002 through sub-010 in place.
4. Write the dataset manifest/README.

Each subject gets a deterministic sub-RNG derived from the master seed, so regenerating a single subject produces identical output regardless of generation order.
      </spec>
      <dependencies>C1, C2, C3</dependencies>
      <risk>medium - orchestration logic must correctly sequence generation and mutation; fieldmap IntendedFor paths must exactly match the generated BOLD filenames</risk>
      <rollback>Delete tools/simulated_bids/scaffold.py and __main__.py</rollback>
    </change>

    <change id="C5" priority="P1" source_item="brainstorm action item 3 (dataset manifest)">
      <file path="tools/simulated_bids/manifest.py" action="create" />
      <description>Generate a README.md at the dataset root documenting: which adversary types are present in each subject-session, expected pipeline behavior per adversary, acquisition parameter summary, and generation metadata.</description>
      <spec>
## tools/simulated_bids/manifest.py

```python
"""Generate the dataset manifest (README.md) documenting adversary assignments."""
from __future__ import annotations
from pathlib import Path
from .adversaries import ADVERSARY_MATRIX

ADVERSARY_DESCRIPTIONS = {
    "A1": "Missing session: entire session directory absent",
    "A2": "Empty session: session directory exists with empty subdirectories only",
    "A3": "Protocol name typo in SeriesDescription/TaskName",
    "A4": "Scan interruption/restart: truncated run + complete re-acquisition",
    "A5": "Protocol rename across sessions (same acquisition signature)",
    "A6": "Mixed PatientIDs within a session (deny-listed field injected)",
    "A7": "Stale unreplaced scan from a different study protocol",
    "A8": "Wrong MultibandAccelerationFactor in sidecar",
    "A9": "Missing optional modality (T2w or DWI absent)",
    "A10": "Missing EffectiveEchoSpacing from BOLD sidecar",
    "A11": "Surviving deny-listed field (PatientSex) in BIDS sidecar",
    "A12": "bval/bvec dimension mismatch (bval shorter than bvec)",
    "A13": "Fieldmap geometry mismatch (different voxel size from target BOLD)",
    "A14": "Orphan SBRef (no matching BOLD run)",
    "A15": "Duplicate sidecar key with different casing (RepetitionTime + repetitiontime)",
    "A16": "RepetitionTime NIfTI pixdim4 vs JSON sidecar mismatch",
    "A17": "qform/sform affine disagreement in NIfTI header",
    "A18": "scl_slope set to NaN in NIfTI header",
    "A19": "Mixed data types across runs (int16 vs float32)",
    "A20": "SliceTiming values in milliseconds instead of seconds",
    "A21": "TaskName missing from JSON sidecar",
    "A22": "IntendedFor uses BIDS-URI format instead of subject-relative path",
    "A23": "TotalReadoutTime mismatch between fieldmap and target BOLD",
    "A24": "Protocol parameter drift: small TR change across sessions",
    "A25": "Duplicate functional run (identical files with different run index)",
    "A26": "Patient positioning error: feet-first-supine (flipped Z-axis in affine)",
    "A27": "Repeated scout/localizer series (extra NIfTI in session)",
    "A28": "Locale-driven decimal separator (comma instead of period) in participants.tsv",
}


def write_manifest(out_dir: Path) -> None:
    """Write README.md at the dataset root."""
    lines = [
        "# Simulated BIDS Dataset",
        "",
        "Synthetic neuroimaging dataset for pipeline testing and validation.",
        "Generated by `tools/simulated_bids` from the bids-recon project.",
        "",
        "## Dataset Structure",
        "",
        "- 10 subjects (sub-001 through sub-010), 3 sessions each",
        "- sub-001: clean baseline (no adversaries)",
        "- sub-002 through sub-010: adversarial examples with graded severity",
        "",
        "## Modality Inventory (per clean subject-session)",
        "",
        "| Modality | Runs | Dimensions | Voxel Size |",
        "|----------|------|------------|------------|",
        "| T1w | 1 | 176x256x256 | 1.0mm iso |",
        "| T2w | 1 | 176x256x256 | 1.0mm iso |",
        "| BOLD rest | 3 (+ SBRef each) | 90x90x60x383 | 2.4mm iso |",
        "| BOLD emotionalnback | 2 (+ SBRef each) | 90x90x60x370 | 2.4mm iso |",
        "| DWI | 1 (+ 3 SBRef) | 140x140x81x103 | 1.7mm iso |",
        "| fmap func | 2 AP/PA pairs | 90x90x60x3 | 2.4mm iso |",
        "| fmap dwi | 1 AP/PA pair | 90x90x60x3 | 2.4mm iso |",
        "",
        "## Adversary Assignment Matrix",
        "",
        "| Subject | Severity | Adversaries |",
        "|---------|----------|-------------|",
        "| sub-001 | Clean | (none) |",
    ]

    for sub in sorted(ADVERSARY_MATRIX):
        specs = ADVERSARY_MATRIX[sub]
        n = len(specs)
        severity = {
            1: "Mild", 2: "Mild-Moderate", 3: "Moderate",
            4: "Moderate-Severe", 5: "Severe", 6: "Severe",
            7: "Extreme",
        }.get(n, f"{n} adversaries")
        ids = ", ".join(s["id"] for s in specs)
        lines.append(f"| {sub} | {severity} ({n}) | {ids} |")

    lines.extend(["", "## Adversary Details", ""])
    for sub in sorted(ADVERSARY_MATRIX):
        lines.append(f"### {sub}")
        lines.append("")
        for spec in ADVERSARY_MATRIX[sub]:
            aid = spec["id"]
            desc = ADVERSARY_DESCRIPTIONS.get(aid, "Unknown")
            sessions = ", ".join(spec["sessions"])
            lines.append(f"- **{aid}** ({sessions}): {desc}")
            if "details" in spec:
                for k, v in spec["details"].items():
                    lines.append(f"  - {k}: {v}")
        lines.append("")

    lines.extend(["## Adversary Type Reference", ""])
    for aid in sorted(ADVERSARY_DESCRIPTIONS, key=lambda x: int(x[1:])):
        lines.append(f"- **{aid}**: {ADVERSARY_DESCRIPTIONS[aid]}")

    lines.extend([
        "",
        "## Generation",
        "",
        "```bash",
        "conda run -n bids-recon python -m tools.simulated_bids ~/simulated-bids-dataset/",
        "```",
        "",
        "Voxel fill: structured noise (low-frequency spatial gradient + Gaussian).",
        "All demographic data is completely fabricated.",
        "Scanner model parameters are sampled from real acquisition distribution moments;",
        "institutional identifiers are fabricated.",
    ])

    (out_dir / "README.md").write_text("\n".join(lines) + "\n")
```
      </spec>
      <dependencies>C3</dependencies>
      <risk>low - pure text generation with no side effects beyond writing README.md</risk>
      <rollback>Delete tools/simulated_bids/manifest.py</rollback>
    </change>
  </changes>

  <execution_order>C1, C2, C3, C4, C5</execution_order>
</implement_plan>
