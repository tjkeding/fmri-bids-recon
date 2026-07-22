"""Stage 1: DICOM-to-NIfTI conversion and source indexing.

Invokes dcm2niix on the source directory to produce NIfTI + JSON sidecars in
a staging directory. Also builds a DICOM index from the source files directly,
which is the only channel through which PhysioLog series (Raw Data Storage,
SOPClassUID 1.2.840.10008.5.1.4.1.1.66) reach the engine, because dcm2niix
silently skips them.
"""

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pydicom

from .errors import ConversionError

logger = logging.getLogger(__name__)


@dataclass
class DicomSeriesRecord:
    """Metadata record for a single DICOM series grouped by SeriesNumber."""

    series_number: int
    sop_class_uid: str
    modality: str | None
    series_description: str
    acquisition_datetime: str | None
    file_paths: list[Path]


@dataclass
class StagingResult:
    """Output of convert_to_staging."""

    staging_dir: Path
    sidecar_paths: list[Path]
    dicom_index: dict[int, DicomSeriesRecord]
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
        paths, the DICOM index built from *source*, the dcm2niix version
        string, and the captured stderr output.

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

    # Build the DICOM index directly from source (the only channel for
    # PhysioLog and other series dcm2niix silently skips).
    dicom_index = index_source_dicoms(source)

    return StagingResult(
        staging_dir=staging,
        sidecar_paths=sidecar_paths,
        dicom_index=dicom_index,
        dcm2niix_version=dcm2niix_version,
        stderr_output=stderr_output,
    )


def index_source_dicoms(source: Path) -> dict[int, DicomSeriesRecord]:
    """Index DICOM files in *source* by SeriesNumber.

    Groups all DICOM files under *source* by their SeriesNumber tag
    (0020,0011). For each series, reads one representative file with
    ``pydicom`` (``stop_before_pixels=True``) to extract series-level
    metadata; all file paths for the series are recorded.

    This index is the ONLY channel through which PhysioLog series
    (Raw Data Storage, SOPClassUID 1.2.840.10008.5.1.4.1.1.66) reach the
    engine, because dcm2niix silently skips them.

    Parameters
    ----------
    source:
        Root directory to search for DICOM files.

    Returns
    -------
    dict[int, DicomSeriesRecord]
        Mapping from SeriesNumber (int) to its :class:`DicomSeriesRecord`.
        Series whose SeriesNumber tag is absent are skipped.
    """
    # Collect all candidate DICOM files (any extension; dcm, ima, no-ext).
    candidate_files: list[Path] = []
    for path in source.rglob("*"):
        if path.is_file():
            candidate_files.append(path)

    # Group file paths by SeriesNumber using a lightweight header read.
    series_files: dict[int, list[Path]] = {}
    for file_path in candidate_files:
        try:
            ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
        except Exception:
            # Not a valid DICOM file; skip silently.
            continue

        series_number_elem = ds.get((0x0020, 0x0011))
        if series_number_elem is None:
            continue
        series_number = int(series_number_elem.value)

        series_files.setdefault(series_number, []).append(file_path)

    # Build the index by reading one representative file per series.
    dicom_index: dict[int, DicomSeriesRecord] = {}
    for series_number, paths in series_files.items():
        representative = paths[0]
        try:
            ds = pydicom.dcmread(str(representative), stop_before_pixels=True)
        except Exception:
            continue

        def _get_str(tag: tuple[int, int], default: str | None = None) -> str | None:
            elem = ds.get(tag)
            if elem is None:
                return default
            return str(elem.value).strip() or default

        sop_class_uid: str = _get_str((0x0008, 0x0016), "") or ""
        modality: str | None = _get_str((0x0008, 0x0060))
        series_description: str = _get_str((0x0008, 0x103E), "") or ""
        acquisition_datetime: str | None = _get_str((0x0008, 0x002A))

        dicom_index[series_number] = DicomSeriesRecord(
            series_number=series_number,
            sop_class_uid=sop_class_uid,
            modality=modality,
            series_description=series_description,
            acquisition_datetime=acquisition_datetime,
            file_paths=sorted(paths),
        )

    return dicom_index
