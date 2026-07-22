"""Sidecar loading and Series dataclass for fmri-bids-recon.

Reads dcm2niix-produced JSON sidecars from the staging directory and
pairs each with its companion NIfTI file to produce Series objects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import nibabel as nib

from .errors import ConversionError


@dataclass(frozen=True)
class Series:
    """Immutable representation of one MRI series from the staging directory.

    Parameters
    ----------
    series_number : int
        DICOM SeriesNumber.
    description : str
        DICOM SeriesDescription.
    image_type : tuple[str, ...]
        DICOM ImageType tokens (e.g. ('ORIGINAL', 'PRIMARY', 'M')).
    image_type_text : tuple[str, ...]
        dcm2niix ImageTypeText tokens (e.g. ('NORM', 'DIS2D')).
    acquisition_datetime : datetime
        Parsed from sidecar AcquisitionDateTime (ISO format).
    repetition_time : float | None
        TR in seconds.
    echo_time : float | None
        TE in seconds.
    inversion_time : float | None
        TI in seconds.
    scanning_sequence : tuple[str, ...]
        DICOM ScanningSequence tokens (e.g. ('GR',) or ('SE', 'GR')).
    mr_acquisition_type : str | None
        '2D' or '3D'.
    phase_encoding_direction : str | None
        Signed BIDS phase-encoding direction: 'j', 'j-', 'i', 'i-', 'k', 'k-'.
    effective_echo_spacing : float | None
        EffectiveEchoSpacing in seconds.
    total_readout_time : float | None
        TotalReadoutTime in seconds.
    multiband_factor : int | None
        MultibandAccelerationFactor.
    slice_timing : tuple[float, ...] | None
        SliceTiming values in seconds.
    matrix : tuple[int, int, int]
        NIfTI image dimensions (i, j, k).
    n_volumes : int
        Number of volumes; NIfTI shape[3] if ndim >= 4 else 1.
    nifti_path : Path
        Absolute path to the companion .nii.gz (or .nii) file.
    sidecar_path : Path
        Absolute path to the JSON sidecar.
    raw : dict
        Full staging sidecar dict including identifiers.
    """

    series_number: int
    description: str
    image_type: tuple[str, ...]
    image_type_text: tuple[str, ...]
    acquisition_datetime: datetime
    repetition_time: float | None
    echo_time: float | None
    inversion_time: float | None
    scanning_sequence: tuple[str, ...]
    mr_acquisition_type: str | None
    phase_encoding_direction: str | None
    effective_echo_spacing: float | None
    total_readout_time: float | None
    multiband_factor: int | None
    slice_timing: tuple[float, ...] | None
    matrix: tuple[int, int, int]
    n_volumes: int
    nifti_path: Path
    sidecar_path: Path
    raw: dict
    software_versions: str | None = None
    affine: tuple[tuple[float, ...], ...] | None = None
    image_position: tuple[float, float, float] | None = None
    voxel_sizes: tuple[float, float, float] | None = None

    @property
    def pe_axis(self) -> str | None:
        """Phase-encoding AXIS (first char of PhaseEncodingDirection), polarity-stripped.

        'j' and 'j-' both return 'j'. A fieldmap pair shares its targets' PE axis; the
        opposite polarities distinguish the pair members, not the axis.
        """
        if not self.phase_encoding_direction:
            return None
        return self.phase_encoding_direction[0]


def _find_nifti(sidecar_path: Path) -> Path:
    """Return the NIfTI companion for a sidecar, preferring .nii.gz.

    Parameters
    ----------
    sidecar_path : Path
        Path to the JSON sidecar file.

    Returns
    -------
    Path
        Path to the companion NIfTI file.

    Raises
    ------
    FileNotFoundError
        If no companion NIfTI file exists alongside the sidecar.
    """
    stem = sidecar_path.stem  # removes .json
    parent = sidecar_path.parent
    for suffix in (".nii.gz", ".nii"):
        candidate = parent / (stem + suffix)
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No companion NIfTI found for sidecar: {sidecar_path}"
    )


def _parse_acquisition_datetime(raw_value: str) -> datetime:
    """Parse an AcquisitionDateTime string to a datetime object.

    Handles ISO-8601 strings with or without fractional seconds, as produced
    by dcm2niix (e.g. '2025-01-15T10:30:00.000000').

    Parameters
    ----------
    raw_value : str
        AcquisitionDateTime string from the JSON sidecar.

    Returns
    -------
    datetime
        Parsed datetime object (naive, no timezone).
    """
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y%m%dT%H%M%S.%f",
        "%Y%m%dT%H%M%S",
    ):
        try:
            return datetime.strptime(raw_value, fmt)
        except ValueError:
            continue
    # Fallback: strip trailing fractional seconds that exceed microsecond
    # precision and retry with the standard fromisoformat.
    return datetime.fromisoformat(raw_value)


def _to_str_tuple(value: object) -> tuple[str, ...]:
    """Normalise a sidecar field to a tuple of strings.

    Parameters
    ----------
    value : object
        A string, list of strings, or None.

    Returns
    -------
    tuple[str, ...]
        Empty tuple if value is None or falsy.
    """
    if value is None:
        return ()
    if isinstance(value, str):
        if "\\" in value:
            return tuple(value.split("\\"))
        return (value,)
    return tuple(str(v) for v in value)


def _to_float_tuple_or_none(value: object) -> tuple[float, ...] | None:
    """Normalise a sidecar SliceTiming list to a tuple of floats, or None.

    Parameters
    ----------
    value : object
        A list of numbers or None.

    Returns
    -------
    tuple[float, ...] | None
    """
    if value is None:
        return None
    return tuple(float(v) for v in value)


def load_series(staging: Path) -> list[Series]:
    """Load all Series objects from a staging directory.

    Iterates over every JSON sidecar found directly in ``staging``, pairs each
    with its companion NIfTI file, opens the NIfTI header for geometry, and
    constructs a :class:`Series` instance. The returned list is sorted by
    ``series_number`` (ascending).

    Parameters
    ----------
    staging : Path
        Directory produced by dcm2niix containing .json and .nii.gz files.

    Returns
    -------
    list[Series]
        All successfully loaded series, sorted by SeriesNumber.

    Raises
    ------
    FileNotFoundError
        Propagated from :func:`_find_nifti` if a companion NIfTI is absent.
    """
    series_list: list[Series] = []

    for sidecar_path in sorted(staging.glob("*.json")):
        with sidecar_path.open("r", encoding="utf-8") as fh:
            raw: dict = json.load(fh)

        nifti_path = _find_nifti(sidecar_path)
        img = nib.load(str(nifti_path))
        shape = img.header.get_data_shape()  # type: ignore[attr-defined]
        matrix: tuple[int, int, int] = (int(shape[0]), int(shape[1]), int(shape[2]))
        n_volumes: int = int(shape[3]) if len(shape) >= 4 else 1

        aff = img.affine
        affine = tuple(tuple(float(v) for v in row) for row in aff)
        image_position = (float(aff[0, 3]), float(aff[1, 3]), float(aff[2, 3]))
        zooms = img.header.get_zooms()
        voxel_sizes = (float(zooms[0]), float(zooms[1]), float(zooms[2]))

        acq_dt_raw: str = raw.get("AcquisitionDateTime", "")
        try:
            acquisition_datetime = _parse_acquisition_datetime(acq_dt_raw)
        except (ValueError, TypeError) as exc:
            raise ConversionError(
                f"Series sidecar {sidecar_path.name} has missing or unparseable "
                f"AcquisitionDateTime ({acq_dt_raw!r}); cannot order or associate it.",
                context={"sidecar": str(sidecar_path), "raw": acq_dt_raw}) from exc

        slice_timing_raw = raw.get("SliceTiming")
        slice_timing = _to_float_tuple_or_none(slice_timing_raw)

        multiband_raw = raw.get("MultibandAccelerationFactor")
        multiband_factor: int | None = (
            int(multiband_raw) if multiband_raw is not None else None
        )

        s = Series(
            series_number=int(raw.get("SeriesNumber", 0)),
            description=str(raw.get("SeriesDescription", "")),
            image_type=_to_str_tuple(raw.get("ImageType")),
            image_type_text=_to_str_tuple(raw.get("ImageTypeText")),
            acquisition_datetime=acquisition_datetime,
            repetition_time=raw.get("RepetitionTime"),
            echo_time=raw.get("EchoTime"),
            inversion_time=raw.get("InversionTime"),
            scanning_sequence=_to_str_tuple(raw.get("ScanningSequence")),
            mr_acquisition_type=raw.get("MRAcquisitionType"),
            phase_encoding_direction=raw.get("PhaseEncodingDirection"),
            effective_echo_spacing=raw.get("EffectiveEchoSpacing"),
            total_readout_time=raw.get("TotalReadoutTime"),
            multiband_factor=multiband_factor,
            slice_timing=slice_timing,
            matrix=matrix,
            n_volumes=n_volumes,
            nifti_path=nifti_path,
            sidecar_path=sidecar_path,
            raw=raw,
            software_versions=raw.get("SoftwareVersions"),
            affine=affine,
            image_position=image_position,
            voxel_sizes=voxel_sizes,
        )
        series_list.append(s)

    series_list.sort(key=lambda s: s.series_number)
    return series_list


def modality_token(s: Series) -> str:
    """Return the modality token from the third ImageType element.

    Parameters
    ----------
    s : Series
        A loaded Series instance.

    Returns
    -------
    str
        ``s.image_type[2]`` if at least three tokens are present, else
        ``'OTHER'``.
    """
    return s.image_type[2] if len(s.image_type) > 2 else "OTHER"
