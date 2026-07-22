<implement_plan>
  <meta project="fmri-bids-recon" mode="implement" submodule="plan" timestamp="2026-07-15T19:18:50Z" />
  <input_reports>
    <report path="(none: action items specified directly in the deployment discussion)" mode="conversation" key_items="5" />
  </input_reports>

  <context>
    Deployment substrate pivots from an Apptainer/Singularity container to a conda
    environment. Rationale: the pipeline is an internal, single-run-per-project,
    single-user tool; a hermetic container was judged overkill for now, and conda
    removes the image build, the apptainer bind flags, and the filesystem-visibility
    question entirely. Verified facts underpinning the pins:
      - dcm2niix 1.0.20260416 is the code's enforced version floor
        (fmri_bids_recon/versions.py:10) AND the latest published release; it is on PyPI
        with a Linux x86_64 manylinux wheel that bundles the executable
        (dcm2niix-1.0.20260416-cp38-abi3-manylinux_2_17_x86_64...whl), so
        `pip install dcm2niix==1.0.20260416` satisfies the floor with no separate build.
      - The GitHub release asset dcm2niix_lnx.zip for v1.0.20260416 has verified
        SHA256 e88b40f6ebbcf9f47ebfdd7bb5f0127297cb7e8b06266a91a4642b5814031bd0
        (865821 bytes; contains a single dcm2niix executable). Used only by the
        retained container recipe.
      - run_bids_validator invokes bare `bids-validator <bids_root>` (no flags),
        non-zero exit = failure (fmri_bids_recon/stage6_validate.py:83-123). The intended
        validator is bids-validator@1.14.13 on Node.js 20, the same pairing the
        container targeted; this avoids the local Node 25 / validator 1.5.3 breakage.
      - cubids is invoked as `cubids group <bids_root> <out>` (non-blocking) and is a
        pinned pip dependency.
    The build phase only writes files; it creates no conda environment locally. The
    environment is created on the server by the operator running hpc/setup_env.sh.
  </context>

  <changes>

    <change id="C1" priority="P0" source_item="conda env spec">
      <file path="environment.yml" action="create" />
      <description>
        Declarative conda environment specification. Python 3.12 and Node.js 20 from
        conda-forge; all pipeline libraries plus the dcm2niix binary pinned via pip to
        the versions the container already targeted. bids-validator is NOT in this file
        (installed via npm by setup_env.sh, since npm-global installs are not expressible
        in environment.yml).
      </description>
      <spec>
Write the file with exactly this content:

# Conda environment for the fmri-bids-recon DICOM-to-BIDS pipeline.
#
# Create with:   conda env create -f environment.yml
# Then install the BIDS validator into the env (see hpc/setup_env.sh). Running
# hpc/setup_env.sh performs both steps in one command.
#
# Python and Node.js come from conda-forge; all pipeline libraries and the
# dcm2niix binary are pinned via pip. dcm2niix 1.0.20260416 is the pipeline's
# enforced version floor and ships as a manylinux wheel that bundles the
# executable, so no separate dcm2niix build is required.
name: fmri-bids-recon
channels:
  - conda-forge
dependencies:
  - python=3.12
  - nodejs=20
  - pip
  - pip:
      - pydicom==3.0.1
      - nibabel==5.3.2
      - numpy==2.2.3
      - pyyaml==6.0.2
      - cubids==1.1.0
      - dcm2niix==1.0.20260416
      </spec>
      <dependencies>none</dependencies>
      <risk>low - new file; declarative spec consumed only on the server.</risk>
      <rollback>Delete environment.yml.</rollback>
    </change>

    <change id="C2" priority="P0" source_item="env setup script">
      <file path="hpc/setup_env.sh" action="create" />
      <description>
        One-command server-side setup: create/update the conda env from environment.yml,
        then install the pinned bids-validator into that env's Node prefix via npm.
      </description>
      <spec>
Write the file with exactly this content:

#!/bin/bash
# One-time environment setup for the fmri-bids-recon pipeline.
#
# Usage:  bash hpc/setup_env.sh [ENV_NAME]
#
# Creates (or updates) the conda environment defined in environment.yml and
# installs the pinned BIDS validator into it via npm. After this completes,
# dcm2niix, bids-validator, and cubids are all on PATH whenever the environment
# is active.
#
# Requires: conda (or mamba) available on PATH. If your cluster needs a module
# load to expose conda (e.g. `module load miniconda`), run that first.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
ENV_NAME="${1:-fmri-bids-recon}"

ENV_FILE="$REPO_ROOT/environment.yml"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: environment.yml not found at $ENV_FILE" >&2
    exit 1
fi

# Create the environment if it does not exist; otherwise update it in place.
if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "Updating existing environment '$ENV_NAME' from $ENV_FILE"
    conda env update -n "$ENV_NAME" -f "$ENV_FILE" --prune
else
    echo "Creating environment '$ENV_NAME' from $ENV_FILE"
    conda env create -n "$ENV_NAME" -f "$ENV_FILE"
fi

# Install the pinned BIDS validator into the environment's Node prefix. Running
# npm through `conda run` guarantees it targets this environment's Node install.
echo "Installing bids-validator@1.14.13 into '$ENV_NAME'"
conda run -n "$ENV_NAME" npm install -g bids-validator@1.14.13

echo "Environment '$ENV_NAME' is ready."
      </spec>
      <dependencies>C1 (consumes environment.yml)</dependencies>
      <risk>low - new file; executed only on the server by the operator.</risk>
      <rollback>Delete hpc/setup_env.sh.</rollback>
    </change>

    <change id="C3" priority="P0" source_item="convert script conda rewrite">
      <file path="hpc/convert_array.sbatch" action="modify" />
      <description>
        Replace the apptainer invocation with conda activation. Add CODE_DIR (positional
        $2) and optional ENV_NAME (positional $3, default fmri-bids-recon). Validate CODE_DIR
        contains a fmri_bids_recon package. Activate the env, then parse the participant list
        with the env's Python (removing the prior reliance on a host python3 having
        PyYAML), and run the module with CODE_DIR on PYTHONPATH.
      </description>
      <spec>
Replace the ENTIRE file content with exactly this:

#!/bin/bash
#SBATCH --job-name=bids-convert
#SBATCH --array=1-N
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=logs/convert_%A_%a.out
#SBATCH --error=logs/convert_%A_%a.err

# Usage: sbatch --array=1-N convert_array.sbatch <CONFIG> <CODE_DIR> [ENV_NAME]
#
#   CONFIG    Absolute path to the study config YAML.
#   CODE_DIR  Absolute path to the directory containing the fmri_bids_recon package.
#   ENV_NAME  Conda environment name (default: fmri-bids-recon).
#
# Each array task converts one (subject, session) pair into its own private
# staging directory. The subject and session are read from the Nth entry of the
# config's participants list, indexed by SLURM_ARRAY_TASK_ID (1-based).

CONFIG=$1
CODE_DIR=$2
ENV_NAME=${3:-fmri-bids-recon}

if [[ -z "$CONFIG" || -z "$CODE_DIR" ]]; then
    echo "ERROR: Usage: sbatch convert_array.sbatch <CONFIG> <CODE_DIR> [ENV_NAME]" >&2
    exit 1
fi

if [[ ! -d "$CODE_DIR/fmri_bids_recon" ]]; then
    echo "ERROR: '$CODE_DIR' does not contain a fmri_bids_recon package directory." >&2
    exit 1
fi

# --- Cluster conda initialization -------------------------------------------
# Ensure `conda` is on PATH. If your cluster requires a module load to expose
# conda, add it here (e.g.: module load miniconda). If conda is already on PATH
# via your login profile, no edit is needed.
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

# Resolve this array task's participant from the config using the environment's
# Python (which provides PyYAML).
TASK_INDEX=$SLURM_ARRAY_TASK_ID

PART=$(python - "$CONFIG" "$TASK_INDEX" <<'PY'
import sys, yaml
config_path, task_index = sys.argv[1], int(sys.argv[2])
with open(config_path) as fh:
    cfg = yaml.safe_load(fh)
entry = cfg["participants"][task_index - 1]
print(entry["sub"], entry.get("ses", ""))
PY
)

SUB=$(echo "$PART" | awk '{print $1}')
SES=$(echo "$PART" | awk '{print $2}')

if [[ -z "$SUB" ]]; then
    echo "ERROR: Could not resolve participant for array index $TASK_INDEX from $CONFIG" >&2
    exit 1
fi

echo "Array task $TASK_INDEX: sub=$SUB ses=$SES"

PYTHONPATH="$CODE_DIR" python -m fmri_bids_recon convert \
    --config "$CONFIG" \
    --participant "$SUB" \
    --session "$SES"
      </spec>
      <dependencies>none (independent file)</dependencies>
      <risk>medium - overwrite of an existing operational script; the conda-init line is
        site-dependent and documented as editable.</risk>
      <rollback>Restore the prior apptainer-based content of hpc/convert_array.sbatch.</rollback>
    </change>

    <change id="C4" priority="P0" source_item="assemble script conda rewrite">
      <file path="hpc/assemble.sbatch" action="modify" />
      <description>
        Replace the apptainer invocation with conda activation. Add CODE_DIR (positional
        $2) and optional ENV_NAME (positional $3, default fmri-bids-recon). Validate CODE_DIR
        contains a fmri_bids_recon package. Activate the env and run the assemble subcommand
        with CODE_DIR on PYTHONPATH. Preserve the "only process that touches the BIDS
        root" comment.
      </description>
      <spec>
Replace the ENTIRE file content with exactly this:

#!/bin/bash
#SBATCH --job-name=bids-assemble
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=logs/assemble_%j.out
#SBATCH --error=logs/assemble_%j.err

# Usage:
#   sbatch --dependency=afterok:<convert_array_job_id> assemble.sbatch <CONFIG> <CODE_DIR> [ENV_NAME]
#
#   CONFIG    Absolute path to the study config YAML.
#   CODE_DIR  Absolute path to the directory containing the fmri_bids_recon package.
#   ENV_NAME  Conda environment name (default: fmri-bids-recon).
#
# This is the ONLY process that touches the BIDS root. It runs serially after
# all convert array tasks have completed successfully.

CONFIG=$1
CODE_DIR=$2
ENV_NAME=${3:-fmri-bids-recon}

if [[ -z "$CONFIG" || -z "$CODE_DIR" ]]; then
    echo "ERROR: Usage: sbatch assemble.sbatch <CONFIG> <CODE_DIR> [ENV_NAME]" >&2
    exit 1
fi

if [[ ! -d "$CODE_DIR/fmri_bids_recon" ]]; then
    echo "ERROR: '$CODE_DIR' does not contain a fmri_bids_recon package directory." >&2
    exit 1
fi

# --- Cluster conda initialization -------------------------------------------
# Ensure `conda` is on PATH. If your cluster requires a module load to expose
# conda, add it here (e.g.: module load miniconda). If conda is already on PATH
# via your login profile, no edit is needed.
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

echo "Starting BIDS assembly from config: $CONFIG"

PYTHONPATH="$CODE_DIR" python -m fmri_bids_recon assemble \
    --config "$CONFIG"
      </spec>
      <dependencies>none (independent file)</dependencies>
      <risk>medium - overwrite of an existing operational script; the conda-init line is
        site-dependent and documented as editable.</risk>
      <rollback>Restore the prior apptainer-based content of hpc/assemble.sbatch.</rollback>
    </change>

    <change id="C5" priority="P1" source_item="container recipe version + integrity fix">
      <file path="hpc/Apptainer.def" action="modify" />
      <description>
        The container recipe is retained as a future option but currently pins a
        nonexistent future dcm2niix release, so it cannot build. Repin to the verified
        real release and wire the placeholder SHA256 into a genuine integrity check. Three
        edits only; do not otherwise alter the file.
      </description>
      <spec>
Make exactly these three edits to hpc/Apptainer.def, leaving all other lines unchanged:

1. Replace the line:
    DCM2NIIX_VERSION="v1.0.20261102"
   with:
    DCM2NIIX_VERSION="v1.0.20260416"

2. Replace the line:
    DCM2NIIX_SHA256="placeholder_update_after_release"
   with:
    DCM2NIIX_SHA256="e88b40f6ebbcf9f47ebfdd7bb5f0127297cb7e8b06266a91a4642b5814031bd0"

3. In the x86_64 branch, immediately AFTER the line:
        wget -q "${ASSET_URL}" -O dcm2niix_lnx.zip
   and BEFORE the line:
        unzip -o dcm2niix_lnx.zip -d /tmp/dcm2niix_bin
   insert this new line (matching the surrounding 8-space indentation):
        echo "${DCM2NIIX_SHA256}  dcm2niix_lnx.zip" | sha256sum -c -
      </spec>
      <dependencies>none (independent file)</dependencies>
      <risk>low - the file is not on the active conda deployment path; edits make an
        otherwise-broken recipe buildable and add real integrity verification.</risk>
      <rollback>Revert the three edited/inserted lines.</rollback>
    </change>

  </changes>

  <execution_order>C1, C2, C3, C4, C5 (all independent; may be applied concurrently by file)</execution_order>
</implement_plan>
