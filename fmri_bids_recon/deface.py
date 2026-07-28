"""Defacing utilities for fmri-bids-recon.

Provides deface(), an opt-in publishing step that emits defaced anatomicals
to derivatives/defaced/ under the BIDS root. The analysis anat/ directories
are never modified.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from .config import StudyConfig
from .errors import ToolUnavailableError

logger = logging.getLogger(__name__)


def _resolve_flirt() -> str | None:
    """Return an absolute path to the flirt binary, or None if not found.

    Checks $FSLDIR/bin/flirt first; falls back to shutil.which("flirt").
    """
    fsl_dir = os.environ.get("FSLDIR")
    if fsl_dir:
        candidate = Path(fsl_dir) / "bin" / "flirt"
        if candidate.is_file():
            return str(candidate)
    return shutil.which("flirt")


def assert_deface_tools() -> None:
    """Pre-flight: verify pydeface and FSL flirt are reachable.

    Called at pipeline startup when config.deface is True. Resolves flirt
    via $FSLDIR/bin/flirt (if the FSLDIR environment variable is set) or
    PATH lookup. Raises ToolUnavailableError if either binary is absent,
    halting the pipeline before any DICOM processing begins.
    """
    missing: list[str] = []
    if shutil.which("pydeface") is None:
        missing.append("pydeface")
    if _resolve_flirt() is None:
        missing.append("flirt")
    if missing:
        msg = (
            f"deface is enabled but required tool(s) not on PATH: "
            f"{', '.join(missing)}. Install the required tools or "
            f"set deface: false in the config."
        )
        if "flirt" in missing:
            msg += (
                " Set the FSLDIR environment variable (e.g. via 'module load FSL')"
                " or add FSL's bin directory to PATH."
            )
        raise ToolUnavailableError(msg)


def _ensure_fsl_env() -> None:
    """Ensure FSL binaries are reachable for downstream subprocess calls.

    When FSLDIR is set, appends $FSLDIR/bin to PATH (if not already
    present) so that pydeface's internal nipype calls can find flirt
    without requiring users to source fsl.sh. Also sets FSLOUTPUTTYPE
    to NIFTI_GZ if not already set.
    """
    fsl_dir = os.environ.get("FSLDIR")
    if not fsl_dir:
        return
    fsl_bin = str(Path(fsl_dir) / "bin")
    current_path = os.environ.get("PATH", "")
    if fsl_bin not in current_path.split(os.pathsep):
        os.environ["PATH"] = current_path + os.pathsep + fsl_bin
        logger.info("Appended %s to PATH for FSL tool access.", fsl_bin)
    if "FSLOUTPUTTYPE" not in os.environ:
        os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"


def deface(config: StudyConfig, tool: str = "pydeface") -> list[Path]:
    """Emit defaced anatomicals to derivatives/defaced/ under the BIDS root.

    This is an opt-in publishing step and is NOT part of the analysis path.
    Files in anat/ are never modified; all output is written to a separate
    derivatives tree.

    Parameters
    ----------
    config : StudyConfig
        Loaded study configuration providing bids_root and participants.
    tool : str, optional
        Defacing tool to invoke. Supported values are ``'pydeface'`` (default)
        and ``'afni_refacer'``.

    Returns
    -------
    list[Path]
        Absolute paths to all defaced output files that were successfully
        created.

    Raises
    ------
    ValueError
        If ``tool`` is not one of the supported values.
    """
    if tool not in ("pydeface", "afni_refacer"):
        raise ValueError(f"Unsupported defacing tool: {tool}")

    _ensure_fsl_env()

    output_paths: list[Path] = []

    for p in config.participants:
        anat_dir = (
            config.bids_root
            / f"sub-{p.sub}"
            / f"ses-{p.ses}"
            / "anat"
        )

        if not anat_dir.is_dir():
            logger.debug("No anat/ directory found for sub-%s ses-%s; skipping.", p.sub, p.ses)
            continue

        nifti_files = list(anat_dir.glob("*_T1w.nii*")) + list(anat_dir.glob("*_T2w.nii*"))

        for input_path in nifti_files:
            filename = input_path.name
            output_path = (
                config.bids_root
                / "derivatives"
                / "defaced"
                / f"sub-{p.sub}"
                / f"ses-{p.ses}"
                / "anat"
                / filename
            )

            output_path.parent.mkdir(parents=True, exist_ok=True)

            if tool == "pydeface":
                subprocess.run(
                    ["pydeface", str(input_path), "--outfile", str(output_path)],
                    check=True,
                )
            elif tool == "afni_refacer":
                subprocess.run(
                    [
                        "@afni_refacer_run",
                        "-input", str(input_path),
                        "-mode_deface",
                        "-prefix", str(output_path),
                    ],
                    check=True,
                )

            if output_path.exists():
                output_paths.append(output_path)
                logger.info("Defaced %s -> %s", input_path, output_path)
            else:
                logger.warning(
                    "Defacing produced no output for %s; not recorded.",
                    output_path,
                )

    return output_paths
