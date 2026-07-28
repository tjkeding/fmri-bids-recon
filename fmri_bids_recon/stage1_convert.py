"""Stage 1: DICOM-to-NIfTI conversion and staging-directory management.

Invokes dcm2niix on the source directory to produce NIfTI + JSON sidecars in
a staging directory.
"""

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import ConversionError

logger = logging.getLogger(__name__)


@dataclass
class StagingResult:
    """Output of convert_to_staging."""

    staging_dir: Path
    sidecar_paths: list[Path]
    dcm2niix_version: str
    stderr_output: str


def convert_to_staging(
    source: Path,
    staging: Path,
    dcm2niix: str = "dcm2niix",
) -> StagingResult:
    """Convert DICOM files in *source* to NIfTI + JSON sidecars in *staging*.

    Parameters
    ----------
    source:
        Root directory containing raw DICOM files.
    staging:
        Output directory for dcm2niix-produced NIfTI and JSON sidecar files.
    dcm2niix:
        Path or name of the dcm2niix executable. Defaults to ``'dcm2niix'``
        (i.e., resolved from PATH).

    Returns
    -------
    StagingResult
        Populated with the staging directory path, all discovered JSON sidecar
        paths, the dcm2niix version string, and the captured stderr output.

    Notes
    -----
    ``-ba n`` is REQUIRED: the dcm2niix default ``-ba y`` suppresses BIDS
    keys that the engine needs for downstream processing.

    ``-f '%s_%d'`` prefixes each output filename with a zero-padded
    SeriesNumber so that staging outputs can be joined back to the DICOM index.
    """
    # Clean only the contents of the staging leaf to ensure a reproducible
    # conversion run; never traverse to a parent directory.
    if staging.exists():
        for child in staging.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        logger.info(
            "Cleaned stale staging leaf for reproducible conversion: %s", staging
        )
    staging.mkdir(parents=True, exist_ok=True)

    # Retrieve dcm2niix version string before conversion.
    version_result = subprocess.run(
        [dcm2niix, "--version"],
        capture_output=True,
        text=True,
    )
    dcm2niix_version = (version_result.stdout + version_result.stderr).strip()

    # Invoke dcm2niix.
    # -ba n : do NOT anonymize BIDS sidecars (preserves all keys the engine needs)
    # -b  y : write BIDS JSON sidecars
    # -z  y : compress NIfTI output with gzip
    # -f '%s_%d' : filename pattern: SeriesNumber_SeriesDescription
    # -o    : output directory
    cmd = [
        dcm2niix,
        "-ba", "n",
        "-b", "y",
        "-z", "y",
        "-f", "%s_%d",
        "-o", str(staging),
        str(source),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ConversionError(
            f"dcm2niix exited {proc.returncode} for staging {staging}.",
            context={"returncode": proc.returncode, "stderr": proc.stderr[-2000:]},
        )
    stderr_output = proc.stderr

    # Collect all JSON sidecar paths produced in the staging directory.
    sidecar_paths = sorted(staging.rglob("*.json"))

    return StagingResult(
        staging_dir=staging,
        sidecar_paths=sidecar_paths,
        dcm2niix_version=dcm2niix_version,
        stderr_output=stderr_output,
    )


