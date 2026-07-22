"""Physiological log parsing, association, and BIDS export for fmri-bids-recon.

Handles Siemens PMU (Physiological Monitoring Unit) DICOM exports stored in
private element (7fe1,1010). Parses ECG, PULS, RESP, EXT, and ACQUISITION_INFO
blocks, associates each log with the correct BOLD run via temporal adjacency and
geometry guard, and writes BIDS-compliant _physio.tsv.gz / _physio.json pairs.
"""

from __future__ import annotations

import gzip
import io
import json
import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pydicom

from .errors import PhysioAssociationError, PhysioParseError
from .sidecar import Series

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

_LOG_VERSION_REQUIRED = "EJA_1"

# Siemens trigger / marker codes are >= 5000; these are not physiological data.
_TRIGGER_THRESHOLD = 5000


@dataclass
class PhysioChannel:
    """One physiological channel extracted from a Siemens PMU block.

    Parameters
    ----------
    name : str
        Channel identifier (e.g. 'ECG', 'PULS', 'RESP', 'EXT').
    sample_time : int
        Inter-sample interval in 2.5 ms ticks (SampleTime field from header).
    data : list[int]
        Raw ADC samples with trigger markers filtered out (values >= 5000 removed).
    """

    name: str
    sample_time: int
    data: list[int] = field(default_factory=list)


@dataclass
class AcquisitionInfo:
    """Parsed ACQUISITION_INFO block from a Siemens PMU log.

    Parameters
    ----------
    num_volumes : int
        Total number of BOLD volumes recorded.
    num_slices : int
        Number of slices per volume.
    num_echoes : int
        Number of echoes per volume (1 for single-echo sequences).
    first_time : int
        Timestamp of the first acquisition tic (2.5 ms units).
    last_time : int
        Timestamp of the last acquisition tic (2.5 ms units).
    volume_table : list[dict]
        Per-volume metadata rows; each dict contains at minimum
        'acq_start_tics' (int).
    """

    num_volumes: int
    num_slices: int
    num_echoes: int
    first_time: int
    last_time: int
    volume_table: list[dict] = field(default_factory=list)


@dataclass
class PhysioLog:
    """Complete parsed representation of one Siemens PMU DICOM file.

    Parameters
    ----------
    channels : dict[str, PhysioChannel]
        Keyed by channel name ('ECG', 'PULS', 'RESP', 'EXT').
    acq_info : AcquisitionInfo | None
        Parsed ACQUISITION_INFO block; None if absent.
    series_number : int
        DICOM SeriesNumber of the source DICOM file.
    acquisition_datetime : str | None
        ISO-format acquisition datetime string from DICOM header; None if absent.
    """

    channels: dict[str, PhysioChannel]
    acq_info: AcquisitionInfo | None
    series_number: int
    acquisition_datetime: str | None


# ---------------------------------------------------------------------------
# Internal parsing helpers
# ---------------------------------------------------------------------------

def _parse_data_block(block_text: str, channel_name: str) -> PhysioChannel:
    """Parse a single ECG/PULS/RESP/EXT data block into a PhysioChannel.

    Parameters
    ----------
    block_text : str
        Raw ASCII text of one PMU block.
    channel_name : str
        Expected channel identifier for labelling purposes.

    Returns
    -------
    PhysioChannel
        Parsed channel with trigger markers removed.
    """
    sample_time = 0
    raw_samples: list[int] = []

    for line in block_text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("LogDataType:"):
            # e.g. "LogDataType: ECG"
            continue

        if line.startswith("SampleTime:"):
            # e.g. "SampleTime:  2500"
            try:
                sample_time = int(line.split(":", 1)[1].strip())
            except (IndexError, ValueError):
                pass
            continue

        if line.startswith("LogVersion:"):
            ver = line.split(":", 1)[1].strip()
            if ver != _LOG_VERSION_REQUIRED:
                raise ValueError(
                    f"Unsupported physio log version: {ver!r}. "
                    f"Expected {_LOG_VERSION_REQUIRED!r}."
                )
            continue

        # Data lines: space-separated integers (possibly interleaved with
        # trigger markers and end-of-block markers).
        tokens = line.split()
        for tok in tokens:
            # Skip non-numeric tokens (e.g. channel labels, 'LOGVERSION')
            try:
                val = int(tok)
            except ValueError:
                continue
            # Siemens trigger markers >= 5000 are not physiological data
            if val < _TRIGGER_THRESHOLD:
                raw_samples.append(val)

    return PhysioChannel(
        name=channel_name,
        sample_time=sample_time,
        data=raw_samples,
    )


def _parse_acquisition_info_block(block_text: str) -> AcquisitionInfo:
    """Parse the ACQUISITION_INFO block.

    Parameters
    ----------
    block_text : str
        Raw ASCII text of the ACQUISITION_INFO block.

    Returns
    -------
    AcquisitionInfo
        Structured acquisition metadata.
    """
    num_volumes = 0
    num_slices = 0
    num_echoes = 1
    first_time = 0
    last_time = 0
    volume_table: list[dict] = []

    # Track whether we are inside the per-volume table
    in_table = False
    table_keys: list[str] = []

    for line in block_text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if line_stripped.startswith("NumVolumes:"):
            try:
                num_volumes = int(line_stripped.split(":", 1)[1].strip())
            except (IndexError, ValueError):
                pass
        elif line_stripped.startswith("NumSlices:"):
            try:
                num_slices = int(line_stripped.split(":", 1)[1].strip())
            except (IndexError, ValueError):
                pass
        elif line_stripped.startswith("NumEchoes:"):
            try:
                num_echoes = int(line_stripped.split(":", 1)[1].strip())
            except (IndexError, ValueError):
                pass
        elif line_stripped.startswith("FirstTime:"):
            try:
                first_time = int(line_stripped.split(":", 1)[1].strip())
            except (IndexError, ValueError):
                pass
        elif line_stripped.startswith("LastTime:"):
            try:
                last_time = int(line_stripped.split(":", 1)[1].strip())
            except (IndexError, ValueError):
                pass
        elif line_stripped.startswith("acq_start_tics") or (
            "acq_start_tics" in line_stripped and not in_table
        ):
            # Header row of the volume table
            in_table = True
            table_keys = line_stripped.split()
        elif in_table:
            tokens = line_stripped.split()
            if len(tokens) == len(table_keys):
                row: dict = {}
                for k, v in zip(table_keys, tokens):
                    try:
                        row[k] = int(v)
                    except ValueError:
                        row[k] = v
                volume_table.append(row)

    return AcquisitionInfo(
        num_volumes=num_volumes,
        num_slices=num_slices,
        num_echoes=num_echoes,
        first_time=first_time,
        last_time=last_time,
        volume_table=volume_table,
    )


def _split_length_prefixed_blocks(payload: bytes) -> list[bytes]:
    """Decode the length-prefixed container in private element (7fe1,1010).

    The format is: [uint32_LE length][<length> bytes of ASCII text], repeated.

    Parameters
    ----------
    payload : bytes
        Raw bytes from DICOM private element value.

    Returns
    -------
    list[bytes]
        Ordered list of raw block byte strings.
    """
    blocks: list[bytes] = []
    buf = io.BytesIO(payload)

    while True:
        length_bytes = buf.read(4)
        if len(length_bytes) < 4:
            break
        (block_len,) = struct.unpack_from("<I", length_bytes)
        if block_len == 0:
            break
        block_data = buf.read(block_len)
        if len(block_data) < block_len:
            break
        blocks.append(block_data)

    return blocks


# Mapping from LogDataType header values to canonical channel names
_CHANNEL_NAMES = {
    "ECG": "ECG",
    "ECG1": "ECG",
    "PULS": "PULS",
    "RESP": "RESP",
    "EXT": "EXT",
    "EXT1": "EXT",
}


# ---------------------------------------------------------------------------
# Datetime helpers
# ---------------------------------------------------------------------------

def _seconds_since_midnight(dt_str: str | None) -> float:
    """Return seconds elapsed since midnight from an AcquisitionDateTime string.

    Parameters
    ----------
    dt_str : str or None
        DICOM AcquisitionDateTime string in any of the formats parsed by the
        module (e.g. '20230101T123456.789000' or '20230101123456.789000').

    Returns
    -------
    float
        Seconds since midnight (hh*3600 + mm*60 + ss + microseconds/1e6),
        or 0.0 if the string is None or unparseable.
    """
    if dt_str is None:
        return 0.0
    from datetime import datetime
    for fmt in (
        "%Y%m%dT%H%M%S.%f",
        "%Y%m%dT%H%M%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y%m%d%H%M%S.%f",
        "%Y%m%d%H%M%S",
    ):
        try:
            dt = datetime.strptime(dt_str, fmt)
            return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond * 1e-6
        except ValueError:
            continue
    return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_physio_dicom(path: Path) -> PhysioLog:
    """Parse a Siemens PMU DICOM file into a PhysioLog.

    Reads private element (7fe1,1010), decodes the length-prefixed ASCII block
    container, and parses each block (ECG, PULS, RESP, EXT, ACQUISITION_INFO).
    Trigger markers (values >= 5000) are removed from all data channels.

    Parameters
    ----------
    path : Path
        Absolute path to the Siemens PMU DICOM file.

    Returns
    -------
    PhysioLog
        Parsed physiological log including all channels and acquisition info.

    Raises
    ------
    ValueError
        If LogVersion != 'EJA_1' or the private element is absent.
    KeyError
        If the private element (7fe1,1010) is missing from the DICOM.
    """
    ds = pydicom.dcmread(str(path), force=True)

    # Retrieve the private element (7FE1,1010)
    try:
        private_elem = ds[0x7FE1, 0x1010]
    except KeyError as exc:
        raise KeyError(
            f"DICOM file {path} does not contain private element (7FE1,1010): {exc}"
        ) from exc

    payload: bytes = private_elem.value

    # Extract DICOM-level metadata
    series_number: int = int(getattr(ds, "SeriesNumber", 0))
    acq_dt: str | None = getattr(ds, "AcquisitionDateTime", None)
    if acq_dt is None:
        acq_date = getattr(ds, "AcquisitionDate", "")
        acq_time = getattr(ds, "AcquisitionTime", "")
        acq_dt = f"{acq_date}T{acq_time}" if acq_date and acq_time else None

    # Decode the length-prefixed block container
    raw_blocks = _split_length_prefixed_blocks(payload)

    channels: dict[str, PhysioChannel] = {}
    acq_info: AcquisitionInfo | None = None

    for raw_block in raw_blocks:
        try:
            block_text = raw_block.decode("ascii", errors="replace")
        except Exception:
            continue

        # Determine block type from LogDataType header
        log_data_type: str | None = None
        for line in block_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("LogDataType:"):
                log_data_type = stripped.split(":", 1)[1].strip().upper()
                break

        if log_data_type is None:
            continue

        if log_data_type == "ACQUISITION_INFO":
            acq_info = _parse_acquisition_info_block(block_text)
        elif log_data_type in _CHANNEL_NAMES:
            canonical = _CHANNEL_NAMES[log_data_type]
            channel = _parse_data_block(block_text, canonical)
            channels[canonical] = channel
        # Unknown block types are silently skipped

    return PhysioLog(
        channels=channels,
        acq_info=acq_info,
        series_number=series_number,
        acquisition_datetime=acq_dt,
    )


def associate_physio(
    logs: list[PhysioLog],
    bolds: list[Series],
) -> dict[int, PhysioLog]:
    """Associate each PhysioLog with the temporally nearest preceding BOLD run.

    For each PhysioLog, the BOLD run whose acquisition_datetime most closely
    precedes (or is nearest to) the physio log's acquisition_datetime is
    selected as the match. A geometry guard confirms that acq_info.num_volumes
    matches the BOLD series' n_volumes and acq_info.num_slices matches
    bold.matrix[2].

    Parameters
    ----------
    logs : list[PhysioLog]
        Parsed physiological logs to associate.
    bolds : list[Series]
        BOLD Series objects to match against.

    Returns
    -------
    dict[int, PhysioLog]
        Mapping of BOLD series_number -> PhysioLog.

    Raises
    ------
    PhysioAssociationError
        If geometry (num_volumes or num_slices) does not match for the best
        temporal candidate.
    """
    from datetime import datetime

    def _parse_dt(dt_str: str | None) -> datetime | None:
        if dt_str is None:
            return None
        for fmt in (
            "%Y%m%dT%H%M%S.%f",
            "%Y%m%dT%H%M%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            # DICOM ACQ datetime: YYYYMMDDHHMMSS.ffffff
            "%Y%m%d%H%M%S.%f",
            "%Y%m%d%H%M%S",
        ):
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        return None

    result: dict[int, PhysioLog] = {}

    bold_times: list[tuple[datetime | None, Series]] = [
        (_parse_dt(b.acquisition_datetime.isoformat() if b.acquisition_datetime else None), b)
        for b in bolds
    ]

    for log in logs:
        log_time = _parse_dt(log.acquisition_datetime)

        best_bold: Series | None = None

        if log_time is not None:
            # Restrict to BOLD runs that start before (or at) the physio log;
            # take the latest among those. Fall back to absolute nearest if no
            # preceding run exists.
            preceding = [
                (bt, b) for bt, b in bold_times if bt is not None and bt <= log_time
            ]
            if preceding:
                best_bold = max(preceding, key=lambda x: x[0])[1]
            else:
                timed = [(bt, b) for bt, b in bold_times if bt is not None]
                if timed:
                    best_bold = min(
                        timed,
                        key=lambda x: abs((log_time - x[0]).total_seconds()),
                    )[1]
                elif bold_times:
                    best_bold = bold_times[0][1]
        else:
            # No timestamps available; assign first BOLD
            if bold_times:
                best_bold = bold_times[0][1]

        if best_bold is None:
            continue

        # Geometry guard: acq_info must be present to verify run geometry.
        if log.acq_info is None:
            raise PhysioAssociationError(
                f"Physio log {log!r} has no ACQUISITION_INFO block; cannot verify run geometry.",
                context={"physio_series": log.series_number,
                         "bold_series": best_bold.series_number},
            )

        if log.acq_info.num_volumes != best_bold.n_volumes:
            raise PhysioAssociationError(
                f"Physio num_volumes ({log.acq_info.num_volumes}) does not match "
                f"BOLD n_volumes ({best_bold.n_volumes}) for series "
                f"{best_bold.series_number}.",
                context={
                    "physio_series": log.series_number,
                    "bold_series": best_bold.series_number,
                    "physio_num_volumes": log.acq_info.num_volumes,
                    "bold_n_volumes": best_bold.n_volumes,
                },
            )
        if log.acq_info.num_slices != best_bold.matrix[2]:
            raise PhysioAssociationError(
                f"Physio num_slices ({log.acq_info.num_slices}) does not match "
                f"BOLD matrix[2] ({best_bold.matrix[2]}) for series "
                f"{best_bold.series_number}.",
                context={
                    "physio_series": log.series_number,
                    "bold_series": best_bold.series_number,
                    "physio_num_slices": log.acq_info.num_slices,
                    "bold_matrix_z": best_bold.matrix[2],
                },
            )

        result[best_bold.series_number] = log

    return result


def write_physio(
    log: PhysioLog,
    run_prefix: str,
    bids_dir: Path,
    bold: Series,
) -> list[Path]:
    """Write BIDS physiological data files for one run.

    Writes:
    - ``<run_prefix>_physio.tsv.gz``: headerless gzip-compressed TSV with columns
      'cardiac' (PULS channel) and 'respiratory' (RESP channel).
    - ``<run_prefix>_physio.json``: BIDS sidecar with SamplingFrequency, StartTime,
      and Columns.
    - ``sourcedata/<run_prefix>_physio_raw.txt``: unfiltered multi-channel raw log
      preserved for provenance.

    Parameters
    ----------
    log : PhysioLog
        Parsed physio log to export.
    run_prefix : str
        BIDS run prefix string (e.g. 'sub-01_task-rest_run-01').
    bids_dir : Path
        Root of the BIDS dataset directory.
    bold : Series
        Matched BOLD Series object (used for StartTime computation).

    Returns
    -------
    list[Path]
        Absolute paths of all files written.
    """
    written: list[Path] = []

    # Sampling frequency: SampleTime is in 2.5 ms ticks per spec
    puls_channel = log.channels.get("PULS")
    resp_channel = log.channels.get("RESP")

    # Guard A1a: at least one channel must report a positive SampleTime.
    sample_time_ticks: int | None = None
    for ch in (puls_channel, resp_channel):
        if ch is not None and ch.sample_time > 0:
            sample_time_ticks = ch.sample_time
            break

    if sample_time_ticks is None:
        raise PhysioParseError(
            f"No channel in {run_prefix} reports a positive SampleTime; "
            "cannot derive SamplingFrequency.",
            context={"channels": list(log.channels)},
        )

    # Guard A1b: PULS and RESP must share the same sample rate.
    rates = {
        name: ch.sample_time
        for name, ch in log.channels.items()
        if name in ("PULS", "RESP") and ch is not None and ch.sample_time > 0
    }
    if len(set(rates.values())) > 1:
        raise PhysioParseError(
            f"PULS/RESP sample rates disagree in {run_prefix}: {rates}.",
            context={"rates": rates},
        )

    # Guard A1c: acquisition window must match n_volumes * TR within tolerance.
    if log.acq_info is not None and log.acq_info.volume_table and bold.repetition_time is not None:
        window_s = (
            log.acq_info.volume_table[-1]["acq_start_tics"]
            - log.acq_info.volume_table[0]["acq_start_tics"]
            + 320
        ) * 2.5e-3
        expected_s = bold.n_volumes * bold.repetition_time
        if abs(window_s - expected_s) > max(0.05 * expected_s, bold.repetition_time):
            raise PhysioParseError(
                f"Acquisition window {window_s:.1f}s disagrees with "
                f"n_volumes*TR {expected_s:.1f}s for {run_prefix}.",
                context={"window_s": window_s, "expected_s": expected_s},
            )

    sampling_freq = 1.0 / (sample_time_ticks * 2.5e-3)

    # Compute StartTime: offset between physio recording start and the first
    # volume, both expressed on the PMU clock (tics-since-midnight * 2.5e-3 s).
    # Because both terms share the same midnight reference, the offset is exact.
    start_time: float = 0.0
    if log.acq_info is not None and log.acq_info.volume_table:
        first_volume_tics = log.acq_info.volume_table[0].get("acq_start_tics")
        if first_volume_tics is not None:
            first_volume_secs = first_volume_tics * 2.5e-3
            rec = _seconds_since_midnight(log.acquisition_datetime)
            start_time = rec - first_volume_secs

    # Build data array: cardiac (PULS) and respiratory (RESP) columns only
    cardiac_data = np.array(puls_channel.data if puls_channel is not None else [], dtype=np.float32)
    resp_data = np.array(resp_channel.data if resp_channel is not None else [], dtype=np.float32)

    # Align lengths to the shorter channel
    n_samples = min(
        len(cardiac_data) if len(cardiac_data) > 0 else 0,
        len(resp_data) if len(resp_data) > 0 else 0,
    )
    if n_samples > 0:
        cardiac_data = cardiac_data[:n_samples]
        resp_data = resp_data[:n_samples]
    else:
        # Use whichever channel has data
        n_samples = max(len(cardiac_data), len(resp_data))
        if len(cardiac_data) == 0:
            cardiac_data = np.zeros(n_samples, dtype=np.float32)
        if len(resp_data) == 0:
            resp_data = np.zeros(n_samples, dtype=np.float32)

    # Write TSV.GZ (headerless, tab-separated)
    tsv_gz_path = bids_dir / f"{run_prefix}_physio.tsv.gz"
    tsv_gz_path.parent.mkdir(parents=True, exist_ok=True)

    buf = io.StringIO()
    for c, r in zip(cardiac_data, resp_data):
        buf.write(f"{c:.6f}\t{r:.6f}\n")
    tsv_bytes = buf.getvalue().encode("utf-8")

    with gzip.open(str(tsv_gz_path), "wb") as fh:
        fh.write(tsv_bytes)
    written.append(tsv_gz_path)

    # Write JSON sidecar
    json_path = bids_dir / f"{run_prefix}_physio.json"
    sidecar = {
        "SamplingFrequency": float(sampling_freq),
        "StartTime": float(start_time),
        "Columns": ["cardiac", "respiratory"],
    }
    json_path.write_text(json.dumps(sidecar, indent=2))
    written.append(json_path)

    # Preserve raw multi-channel log under sourcedata/
    sourcedata_dir = bids_dir / "sourcedata"
    sourcedata_dir.mkdir(parents=True, exist_ok=True)
    raw_path = sourcedata_dir / f"{run_prefix}_physio_raw.txt"

    raw_lines: list[str] = []
    for ch_name, ch in log.channels.items():
        raw_lines.append(f"# Channel: {ch_name}")
        raw_lines.append(f"# SampleTime: {ch.sample_time}")
        raw_lines.append(" ".join(str(v) for v in ch.data))
        raw_lines.append("")

    raw_path.write_text("\n".join(raw_lines))
    written.append(raw_path)

    return written
