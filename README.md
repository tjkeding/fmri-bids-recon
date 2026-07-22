# fmri-bids-recon

A DICOM-to-BIDS reconstruction pipeline for multi-session fMRI studies.

fmri-bids-recon converts raw DICOM directories into a [BIDS](https://bids-specification.readthedocs.io/)-compliant dataset with fieldmap association metadata, physiological trace extraction, automated defacing, and three-layer validation. The pipeline is designed for longitudinal studies with multiple subjects, sessions, and modalities (T1w, T2w, BOLD, DWI, fieldmaps).

## Design Principles

- **Faithful reconstruction.** Every DICOM-derived field that dcm2niix writes to a sidecar is preserved in the BIDS tree. The pipeline performs no information filtering. De-identification, if required, is a separate downstream operation.
- **Halt on uncertainty.** The pipeline enforces 14 integrity guards. Any guard violation halts execution before outputs are written, rather than emitting a warning and continuing. This is a deliberate design choice: a halted pipeline produces no result, whereas a silently wrong result can propagate through an entire analysis.
- **Geometry-primary fieldmap association.** Fieldmap-to-target pairing uses a five-criterion geometry check (image position, orientation, voxel size, matrix dimensions, phase-encoding axis) with configurable tolerances. Nearest-in-time tiebreaking applies only among geometry-eligible candidates.
- **Atomic writes.** Phase 1 (convert) writes all intermediate state to a staging directory. Phase 2 (guard check) runs before any output is committed to `bids_root`. Phase 3 (assemble) writes the final tree. A failed guard check produces no partial BIDS output.
- **Resumability.** A manifest tracks which (subject, session) pairs have been assembled and validated. Re-running the pipeline skips already-validated pairs.

## Pipeline Stages

The pipeline executes seven stages in sequence:

| Stage | Name | Description |
|-------|------|-------------|
| 1 | **Convert** | Invokes dcm2niix on each (subject, session), classifies series into BIDS roles, resolves task labels, pairs fieldmaps, and optionally extracts physiological traces. Writes intermediate state to the staging directory. |
| 2 | **Guard check** | Asserts that all 14 integrity guards executed and passed. Runs before any output is committed to `bids_root`. |
| 3 | **Assemble** | Writes the BIDS directory tree: NIfTI files, JSON sidecars, scans/sessions/participants TSVs, conversion reports, and fieldmap association metadata (IntendedFor + B0FieldIdentifier/B0FieldSource). |
| 4 | **Registry save** | Persists the task registry to a sidecar YAML file alongside the configuration. |
| 5 | **Deface** | Generates defaced copies of anatomical images in `derivatives/defaced/` via pydeface. The analysis `anat/` directories are never modified. |
| 6 | **Validate** | Runs bids-validator-deno against the assembled tree and emits a grouped findings report. |
| 7 | **CUBIDs** | Generates an Entity Sets / Parameter Groups review artifact via cubids (non-blocking; skipped if cubids is not installed). |

## Prerequisites

- **conda** (or **mamba**) available on PATH.
- Outbound network access during one-time environment setup (conda downloads packages from conda-forge and PyPI).
- No root or `sudo` access is required.

## Installation

### Option A: pip install from GitHub (recommended)

```bash
conda create -n fmri-bids-recon python=3.12 -y
conda activate fmri-bids-recon
pip install git+https://github.com/<org>/fmri-bids-recon.git
```

### Option B: local editable install

```bash
git clone https://github.com/<org>/fmri-bids-recon.git
cd fmri-bids-recon
conda env create -f environment.yml
conda activate fmri-bids-recon
pip install -e .
```

Verify the installation:

```bash
conda activate fmri-bids-recon
fmri-bids-recon --help                # entry point works
dcm2niix --version                    # >= 1.0.20260416
bids-validator-deno --version         # >= 3.0.0
python -c "import pydicom, nibabel, numpy, yaml; print('ok')"
```

## Configuration

Create a study configuration YAML from the provided template:

```bash
cp config/study.example.yaml config/my_study.yaml
```

Required fields:

```yaml
bids_root: '/absolute/path/to/bids_root'       # Output BIDS dataset
staging_root: '/absolute/path/to/staging'       # Intermediate staging (must not be inside bids_root)
dicom_root: '/absolute/path/to/raw/dicoms'      # Root of raw DICOM tree
dicom_template: '{subject}/{session}'           # Path template under dicom_root

subjects:                                        # Inline list...
  - '001'
  - '002'
# subjects: '/absolute/path/to/subject_ids.txt' # ...or text file

sessions:
  - '01'
  - '02'

physio: false    # Set true to extract physiological traces
```

See `config/study.example.yaml` for full documentation of each field, and `INPUT_SPECIFICATION.md` for the exhaustive input schema.

## Usage

```bash
conda activate fmri-bids-recon
fmri-bids-recon config/my_study.yaml
```

The pipeline processes every (subject, session) pair from the cross product of the `subjects` and `sessions` lists. Pairs whose DICOM path does not exist on disk are skipped.

## Output Structure

```
<bids_root>/
  sub-001/
    ses-01/
      anat/           # T1w, T2w NIfTI + sidecars
      func/           # BOLD NIfTI + sidecars (with B0FieldSource)
      fmap/           # Fieldmap EPI pairs (with IntendedFor, B0FieldIdentifier)
      dwi/            # Diffusion NIfTI + sidecars
  derivatives/
    fmri-bids-recon/  # Conversion reports, manifest
    defaced/          # Defaced anatomical images
  code/
    cubids/           # CUBIDs review artifact
  sourcedata/
    provenance/       # Original staging sidecars (full dcm2niix output)
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success. No spec errors. |
| 1 | Guard error. A pipeline integrity invariant was violated. |
| 2 | Configuration error. Malformed config or no participants resolved. |
| 3 | Spec findings. The BIDS validator reported errors. The tree IS written; errors describe spec-compliance issues. |
| 4 | Tool unavailable. An external tool could not run. The dataset is UNCHECKED. |

## Guard System

The pipeline enforces 14 named guards:

| Guard | Description |
|-------|-------------|
| `dcm2niix_version_floor` | dcm2niix version meets the minimum verified floor. |
| `anat_suffix_physics` | Physics-derived verdict agrees with the anatomical name token. |
| `label_injectivity` | No two distinct series descriptions resolve to the same BIDS label. |
| `non_empty_labels` | No series description strips to an empty label. |
| `no_label_drift` | A known description re-derives to the same label as previously recorded. |
| `no_rename_collision` | No undeclared task rename detected via signature matching. |
| `exact_volume_counts` | BOLD volume counts match the registered expected count. |
| `fmap_phase_encoding_opposite` | Fieldmap pair members have opposite phase-encoding directions. |
| `fmap_phase_encoding_label_match` | Phase-encoding direction agrees with the _PA/_AP name token. |
| `fmap_geometry_match` | Fieldmap pair members pass the five-criterion geometry check. |
| `fmap_coverage_complete` | Every functional/diffusion target has at least one valid fieldmap pair. |
| `fmap_sbref_geometry_match` | SBRef passenger series passes the geometry check against its host pair. |
| `physio_association` | Physio file geometry matches its candidate BOLD run. |
| `conversion_success` | dcm2niix returned exit status 0. |

All guards initialize to `False` and self-record to `True` after their check passes. The meta-guard (`assert_guards_executed`) runs before any output is written and halts if any guard is still `False`.

## Dependencies

Managed via conda (`environment.yml`):

| Package | Version | Role |
|---------|---------|------|
| Python | 3.12 | Runtime |
| pydicom | 3.0.1 | DICOM header parsing |
| nibabel | 5.3.2 | NIfTI I/O and geometry extraction |
| numpy | 1.26.4 | Array operations |
| pyyaml | 6.0.2 | Configuration loading |
| dcm2niix | 1.0.20260416 | DICOM-to-NIfTI conversion |
| bids-validator-deno | 3.0.0 | BIDS spec compliance validation |
| cubids | 1.1.0 | Entity/parameter group review |
| pydeface | 2.1.0 | Anatomical defacing |

## License

[License information to be added.]
