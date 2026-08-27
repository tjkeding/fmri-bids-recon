# fmri-bids-recon Input Specification

This document provides an exhaustive description of all inputs consumed by the fmri-bids-recon pipeline: configuration parameters, file format requirements, environment dependencies, and runtime constraints. It is intended as a machine-readable reference for reproducible invocations.

---

## 1. Study Configuration YAML

The pipeline accepts a single positional argument: the absolute path to a YAML configuration file. A template is provided at `config/study.example.yaml`.

### 1.1 Required Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `bids_root` | string (absolute path) | Must be an existing directory or creatable by the pipeline. | Root of the output BIDS dataset. The `study_name` property is derived from this directory's basename. |
| `staging_root` | string (absolute path) | Must NOT be a subdirectory of (or equal to) `bids_root`. Enforced at load time. | Scratch directory for intermediate pipeline state. Written during Phase 1 (convert), read during Phase 3 (assemble). |
| `dicom_root` | string (absolute path) | Must exist on disk. | Root of the raw DICOM directory tree. |
| `dicom_template` | string | Must contain `{subject}` and `{session}` format placeholders. | Per-subject/session path template relative to `dicom_root`. Evaluated as `dicom_root / dicom_template.format(subject=<id>, session=<label>)`. |
| `subjects` | list of strings, or string (absolute path) | Each entry must match `^[a-zA-Z0-9]+$`. No `sub-` prefix. No duplicates. If a string, must be an absolute path to an existing file. | Subject IDs to process. If a string, treated as an absolute path to a single-column text file (blank lines and `#` comment lines are skipped). |
| `sessions` | list of strings | Each entry must match `^[0-9]{2,}$` (zero-padded integer, minimum 2 digits). No `ses-` prefix. No duplicates. | Session labels to process. |

### 1.2 Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `physio` | boolean | `false` | Enable physiological data extraction. When true, the pipeline discovers dcm2niix's native per-channel physio export in the staging directory, associates each recording with the nearest preceding BOLD run via a trigger-derived volume-count geometry guard, and copies the files verbatim into the BIDS func/ tree. |
| `deface` | boolean | `false` | Enable anatomical defacing via pydeface. When true, the pipeline resolves `flirt` via the `FSLDIR` environment variable (falling back to PATH lookup) and verifies both `pydeface` and `flirt` at startup. Halts immediately if either is absent. Defaced copies are written to `derivatives/defaced/`; the analysis `anat/` directories are never modified. |

### 1.3 Derived Fields (populated by `load_config()`)

These fields are computed at load time and are not specified in the YAML file.

| Field | Type | Derivation |
|-------|------|------------|
| `participants` | list of `ParticipantEntry` | Cross product of `subjects` x `sessions`, filtered to pairs whose resolved DICOM path exists on disk. |
| `task_registry` | dict of `TaskRegistryEntry` | Loaded from the sidecar file `<config_path>.registry.yaml` if it exists; empty dict otherwise. |
| `sourcedata_root` | Path (property) | `bids_root / 'sourcedata'` |
| `study_name` | str (property) | `bids_root.name` |

### 1.4 Validation Rules

The following rules are enforced by `load_config()` at startup. Violations raise `ValueError` or `ConfigError` before any processing begins.

1. **Subject label format**: every entry in `subjects` must match `^[a-zA-Z0-9]+$`.
2. **Session label format**: every entry in `sessions` must match `^[0-9]{2,}$`.
3. **No duplicate subjects**: duplicate entries within the `subjects` list are rejected.
3a. **Subjects file path**: if `subjects` is a string, it must be an absolute path to an existing file containing at least one valid entry.
4. **No duplicate sessions**: duplicate entries within the `sessions` list are rejected.
5. **Staging isolation**: `staging_root` must not be a subdirectory of (or equal to) `bids_root`. This prevents concurrency hazards where pipeline writes to staging would modify the BIDS dataset in-flight.
6. **At least one resolved participant**: after the `subjects` x `sessions` cross product is expanded and filtered to existing DICOM paths, at least one `ParticipantEntry` must remain. If all paths are missing, a `ConfigError` is raised.

### 1.5 Task Registry Sidecar

The pipeline maintains a sidecar file at `<config_path>.registry.yaml` (e.g., `study.yaml.registry.yaml`). This file is created and updated automatically as new task labels are encountered during conversion. **Do not add a `task_registry` key to the main config YAML; it will be ignored.**

Each registry entry contains:

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | BIDS task label (alphanumeric, no `task-` prefix). |
| `expected_volumes` | integer or null | Expected BOLD volume count for this task. Null if not yet established. |
| `first_seen` | string (ISO-8601 date) | Date of first acquisition for this label (YYYY-MM-DD). |
| `signature` | list or null | Acquisition fingerprint: `[repetition_time, effective_echo_spacing, multiband_factor, [matrix_dims]]`. Null for legacy entries. |
| `prefix` | list or null | Label-derivation prefix in force at registration time (persisted as a list, reconstructed as a tuple on load). Used by the `no_label_drift` guard to re-derive a registered label against the session that registered it, rather than the current session's prefix. Null for entries registered before prefix persistence was introduced. |

---

## 2. DICOM Input Requirements

### 2.1 Directory Structure

The pipeline expects raw DICOM files organized under `dicom_root` according to `dicom_template`. For the default template `{subject}/{session}`, the expected structure is:

```
<dicom_root>/
  001/
    01/
      <DICOM files for subject 001, session 01>
    02/
      <DICOM files for subject 001, session 02>
  002/
    01/
      ...
```

All DICOM files within a resolved session directory are processed. The pipeline does not recurse into subdirectories beyond the resolved path.

### 2.2 Supported Modalities

The classifier (stage 2) assigns BIDS roles based on sidecar fields written by dcm2niix. Supported modalities and their classification criteria:

| Role | BIDS Suffix | Classification Signal |
|------|-------------|----------------------|
| T1w | `_T1w` | Anatomical with T1-weighted MR physics |
| T2w | `_T2w` | Anatomical with T2-weighted MR physics |
| BOLD | `_bold` | Functional EPI with `PhaseEncodingDirection` |
| DWI | `_dwi` | Diffusion-weighted imaging |
| Fieldmap (functional) | `_epi` | EPI acquired for distortion correction |
| Fieldmap (SBRef) | `_sbref` | Single-band reference passenger series |

**Calibration sequence exclusion**: after the initial classification pass, a two-layer post-classification guard demotes spurious fieldmap candidates to `DROP_CALIBRATION` (silently discarded). The primary layer checks phase-encoding (PE) axis compatibility: an `FMAP_FUNC` series whose PE axis does not match any BOLD series (or an `FMAP_DWI` series whose PE axis does not match any DWI series) is demoted. This is a physics-based guard rooted in the requirement that a fieldmap must share its target's PE axis for distortion correction to be applicable (Jezzard and Balaban, MRM 1995). The secondary layer applies a compound keyword guard: series matching known calibration description keywords (e.g., "setter", "prescan") that are single-volume and whose description stem does not match any target modality series are also demoted. If no target modality series exist in the session, both layers are bypassed to avoid false demotion in partial or aborted protocols.

### 2.3 Physiological Data (optional)

When `physio: true`, the pipeline ingests dcm2niix's native per-channel BIDS physiological export. dcm2niix (>= 1.0.20260416) detects vendor-specific physiological recordings in the DICOM source (e.g., Siemens PhysioLog series with SOPClassUID 1.2.840.10008.5.1.4.1.1.66) and produces per-channel `.json` + `.tsv.gz` pairs in the staging directory, named `{series_number}_{description}_recording-{label}_physio.*`. No NIfTI companion is produced for these files.

**Classification**: physio sidecars are identified by the presence of all three BIDS-required fields for `_physio.json` files: `SamplingFrequency`, `StartTime`, and `Columns` (per BIDS specification v1.11.1). This is a spec-grounded, vendor-agnostic classification signal. Sidecars meeting this criterion are separated from the imaging series list during `load_series()` and routed to the physio ingestion path.

**Channel labels**: dcm2niix produces three channels for Siemens PhysioLog data: `cardiac`, `respiratory`, and `external_trigger`. The `external_trigger` channel carries a `trigger` column encoding volume-onset pulses. Other scanners or dcm2niix versions may produce different channel sets; the pipeline handles any label that dcm2niix encodes in the `_recording-{label}_physio` filename convention.

**Association**: each physio recording (grouped by SeriesNumber) is associated with the nearest preceding BOLD run by SeriesNumber. A trigger-derived volume-count geometry guard verifies the association: the number of rising edges in the trigger column must equal the BOLD run's `n_volumes`. A mismatch raises `PhysioAssociationError` (a `GuardError` subclass) and halts the pipeline.

**Export**: the pipeline copies dcm2niix's native per-channel files verbatim (no re-derivation or recombination) into the BIDS `func/` directory, renaming them to the standard BIDS pattern: `{run_prefix}_recording-{label}_physio.{json,tsv.gz}`.

---

## 3. Environment Requirements

### 3.1 Python

- **Version**: >= 3.12 (enforced by `pyproject.toml` `requires-python`)

### 3.2 Runtime Dependencies

All dependencies are installable via pip (declared in `pyproject.toml`):

| Package | Minimum Version | Role |
|---------|----------------|------|
| pydicom | 3.0.1 | DICOM header parsing |
| nibabel | 5.3.2 | NIfTI I/O and geometry extraction |
| numpy | 1.26.4 | Array operations |
| pyyaml | 6.0.2 | YAML configuration loading |
| cubids | 1.1.0 | Entity/parameter group review artifact |
| pydeface | 2.1.0 | Anatomical defacing (requires FSL `flirt` via `FSLDIR` or PATH) |
| dcm2niix | 1.0.20260416 | DICOM-to-NIfTI conversion (pip wheel bundles the binary) |
| bids-validator-deno | 3.0.0 | BIDS spec compliance validation (pip wheel bundles the Deno runtime) |

### 3.3 External Tool Requirements

| Tool | Version Floor | Enforcement | Notes |
|------|--------------|-------------|-------|
| dcm2niix | 1.0.20260416 | Hard (guard: `dcm2niix_version_floor`). Pipeline refuses to run if the version is below the floor. | Installed via pip wheel; no separate installation required. |
| bids-validator-deno | 3.0.0 | Soft (exit code 4 if unavailable). Dataset is written but UNCHECKED. | Installed via pip wheel. |
| FSL `flirt` | any | Hard when `deface: true` (pre-flight check halts pipeline); stage skipped when `deface: false` (default). | Required only when the deface stage is enabled. Must be installed separately. Resolved via the `FSLDIR` environment variable (e.g., `module load FSL`), with PATH fallback. |
| cubids | 1.1.0 | Soft (CUBIDs report skipped if unavailable). | Installed via pip. |

### 3.4 Conda Environment

For server deployments, `environment.yml` provides a complete conda environment specification with all pinned dependencies. The recommended workflow is:

```bash
conda env create -f environment.yml -n fmri-bids-recon
conda activate fmri-bids-recon
pip install -e .
```

### 3.5 HPC Module-Based Environments

On HPC clusters where software is provided via environment modules (e.g., `module load`), the install and run steps must follow a specific ordering to prevent two classes of contamination:

1. **Install-time contamination**: loading FSL before `pip install` injects FSL's Python 3.11 site-packages into the environment. This causes pip to either fail with permission errors when attempting to upgrade FSL-owned packages, or silently skip installation of Python 3.12 wheels for packages FSL already provides (numpy, scipy, pandas), resulting in ABI-incompatible C extensions at runtime.

2. **Run-time PATH shadowing**: if FSL's `bin/` directory appears earlier on PATH than the conda environment's `bin/`, the system-provided `dcm2niix` (potentially an older, incompatible version) takes priority over the pip-installed copy.

**Install sequence** (one-time, clean shell without FSL loaded):

```bash
module load miniconda
conda create -n fmri-bids-recon python=3.12 -y
conda activate fmri-bids-recon
pip install git+https://github.com/tjkeding/fmri-bids-recon.git
```

If the default home-directory quota is insufficient for the conda environment, use the `-p` flag to place it on a project or scratch filesystem:

```bash
conda create -p /path/to/project/envs/fmri-bids-recon python=3.12 -y
```

**Run sequence** (each reconstruction):

```bash
module load FSL
module load miniconda
conda activate fmri-bids-recon
fmri-bids-recon <CONFIG>
```

`module load FSL` must precede `conda activate` so that the conda environment's `bin/` directory is prepended to PATH after FSL's, giving conda's binaries (including `dcm2niix` >= 1.0.20260416) priority.

The pipeline provides two runtime guards against module-system contamination:

| Guard | Location | Mechanism |
|-------|----------|-----------|
| sys.path sanitization | `__init__.py` (`_sanitize_sys_path()`) | At startup, strips foreign-version Python site-packages entries from `sys.path` and `PYTHONPATH` before scientific library imports. Version-aware: generalizes to any module that injects foreign-version paths. Complete no-op in clean environments. |
| FSLDIR-based tool resolution | `deface.py` (`_resolve_flirt()`, `_build_fsl_env()`) | Resolves `flirt` via `$FSLDIR/bin/flirt` rather than PATH lookup. At deface time, constructs a scoped environment dict (a copy of `os.environ` with `$FSLDIR/bin` appended to PATH and `FSLOUTPUTTYPE=NIFTI_GZ` set) and passes it via the `env=` parameter to `subprocess.run()`. The global `os.environ` is never mutated. |

These guards mean that a simple `module load FSL` followed by `conda activate` is sufficient. No manual PATH manipulation, environment variable exports, or FSL shell configuration scripts (`source $FSLDIR/etc/fslconf/fsl.sh`) are required.

---

## 4. Geometry Tolerance Constants

The five-criterion geometry check for fieldmap-to-target pairing uses the following tolerances, defined in `fmri_bids_recon/config.py`:

| Constant | Value | Unit | Purpose |
|----------|-------|------|---------|
| `GEOMETRY_POSITION_TOL_MM` | 0.1 | mm | Image position tolerance |
| `GEOMETRY_ORIENTATION_TOL` | 1e-4 | unitless | Image orientation cosine tolerance |
| `GEOMETRY_VOXEL_TOL_MM` | 1e-3 | mm | Voxel size tolerance |

These tolerances are sized to absorb dcm2niix float-representation jitter, not voxel-scaled differences. Within-block position delta is 0.0 mm; nearest-block delta is 2.53 mm, providing a clear separation.

---

## 5. Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | No errors. Advisory warnings may be present in the conversion report. |
| 1 | Guard error | A pipeline integrity invariant was violated. Full traceback is printed. Investigate the guard named in the error message. |
| 2 | Configuration error | Malformed config, no participants resolved, or dcm2niix version below floor. |
| 3 | Spec findings | BIDS validator reported errors. The tree IS written; errors describe spec-compliance issues in the output. |
| 4 | Tool unavailable | An external tool (e.g., bids-validator-deno) could not run. The dataset is UNCHECKED. |

---

## 6. Output Structure

The pipeline writes the following directory tree under `bids_root`:

```
<bids_root>/
  sub-<sub>/
    ses-<ses>/
      anat/           # T1w, T2w NIfTI + JSON sidecars
      func/           # BOLD NIfTI + JSON sidecars (with B0FieldSource)
      fmap/           # Fieldmap EPI pairs (with IntendedFor, B0FieldIdentifier)
      dwi/            # Diffusion NIfTI + JSON sidecars (if present)
  derivatives/
    fmri-bids-recon/  # Conversion reports, manifest.tsv
    defaced/          # Defaced anatomical images (if pydeface + FSL available)
  code/
    cubids/           # CUBIDs review artifact (if cubids available)
  sourcedata/
    provenance/       # Original staging sidecars (full dcm2niix output)
```

---

## 7. Known Limitations

1. **Single-site assumption**: the classifier and geometry tolerances are validated against Siemens XA30 DICOM output. Other scanner vendors or software versions may produce sidecar fields that the classifier does not recognize.
2. **No incremental fieldmap re-pairing**: if new sessions are added after the initial run, fieldmap pairs are computed independently per session. Cross-session fieldmap sharing is not supported.
3. **Physiological data requires dcm2niix native export**: the pipeline ingests dcm2niix's native per-channel BIDS physio output (`.json` + `.tsv.gz` pairs with `SamplingFrequency`, `StartTime`, and `Columns` fields). It does not parse raw vendor-specific DICOM private elements directly. Any scanner or protocol whose physiological recordings dcm2niix decodes into this native format is supported; those it does not decode are not available to the pipeline.
4. **Defacing requires FSL**: the `pydeface` package is a Python wrapper around FSL's `flirt`. When `deface: true` is set in the study config, the pipeline resolves `flirt` via the `FSLDIR` environment variable (falling back to PATH lookup) and verifies both tools at startup. On HPC clusters using environment modules, `module load FSL` sets `FSLDIR`; no additional PATH manipulation or `source fsl.sh` is required.
5. **Calibration exclusion validated on Siemens only**: the PE axis validation layer of the calibration sequence exclusion pass is vendor-agnostic by design (rooted in the physical necessity that a fieldmap must share its target's PE axis). However, the guard has been validated only against Siemens vNav setter calibration sequences. Cross-vendor validation against GE and Philips calibration DICOM samples is required to confirm coverage. The keyword guard layer currently includes Siemens-specific terms ("setter", "prescan"); additional vendor-specific keywords may be needed as empirical samples become available.
