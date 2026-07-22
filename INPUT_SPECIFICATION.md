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
| `physio` | boolean | `false` | Enable physiological data extraction (Siemens PMU DICOM parsing, temporal association, BIDS export). |

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

### 2.3 Physiological Data (optional)

When `physio: true`, the pipeline parses Siemens PMU (Physiological Monitoring Unit) DICOM exports stored in the private element `(7fe1,1010)`. Supported channel types: ECG, PULS, RESP, EXT, ACQUISITION_INFO.

PMU DICOMs must be present in the same session directory as the imaging DICOMs. Association with BOLD runs uses temporal adjacency and geometry matching.

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
| pydeface | 2.1.0 | Anatomical defacing (requires FSL `flirt` at runtime) |
| dcm2niix | 1.0.20260416 | DICOM-to-NIfTI conversion (pip wheel bundles the binary) |
| bids-validator-deno | 3.0.0 | BIDS spec compliance validation (pip wheel bundles the Deno runtime) |

### 3.3 External Tool Requirements

| Tool | Version Floor | Enforcement | Notes |
|------|--------------|-------------|-------|
| dcm2niix | 1.0.20260416 | Hard (guard: `dcm2niix_version_floor`). Pipeline refuses to run if the version is below the floor. | Installed via pip wheel; no separate installation required. |
| bids-validator-deno | 3.0.0 | Soft (exit code 4 if unavailable). Dataset is written but UNCHECKED. | Installed via pip wheel. |
| FSL `flirt` | any | Soft (deface stage skipped if unavailable). | Required only for the deface stage. Must be installed separately. |
| cubids | 1.1.0 | Soft (CUBIDs report skipped if unavailable). | Installed via pip. |

### 3.4 Conda Environment

For server deployments, `environment.yml` provides a complete conda environment specification with all pinned dependencies. The recommended workflow is:

```bash
conda env create -f environment.yml -n fmri-bids-recon
conda activate fmri-bids-recon
pip install -e .
```

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
3. **Physiological data restricted to Siemens PMU format**: other physiological recording formats (BIOPAC, BrainVision) are not parsed.
4. **Defacing requires FSL**: the `pydeface` package is a Python wrapper around FSL's `flirt`. Systems without FSL installed will skip the deface stage silently.
