"""Physiological data ingestion and BIDS export for fmri-bids-recon.

Ingests dcm2niix's native per-channel BIDS physio export (recording-cardiac,
recording-respiratory, recording-external_trigger .json/.tsv.gz triplets),
groups channels by SeriesNumber, associates each physio recording with the
nearest preceding BOLD run via a trigger-derived volume count guard, and
copies the dcm2niix-native files verbatim into the BIDS func/ tree.
"""

from __future__ import annotations

import gzip
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .errors import PhysioAssociationError, PhysioParseError
from .sidecar import Series

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class NativePhysioChannel:
    """One channel file from dcm2niix's native per-channel BIDS physio export.

    Parameters
    ----------
    label : str
        Channel identifier parsed from the filename token following
        '_recording-' (e.g. 'cardiac', 'respiratory', 'external_trigger').
    sampling_frequency : float
        SamplingFrequency from the channel's JSON sidecar, in Hz.
    start_time : float
        StartTime from the channel's JSON sidecar, in seconds.
    columns : tuple[str, ...]
        Columns from the channel's JSON sidecar, naming the TSV's fields
        in order. Read dynamically rather than assumed, since dcm2niix's
        per-channel column layout is not hardcoded by this codebase.
    data : dict[str, np.ndarray]
        Column name -> sample array, keyed exactly as declared in `columns`.
    json_path : Path
        Absolute path to the channel's JSON sidecar in the staging directory.
    tsv_path : Path
        Absolute path to the channel's .tsv.gz in the staging directory.
    """

    label: str
    sampling_frequency: float
    start_time: float
    columns: tuple[str, ...]
    data: dict[str, np.ndarray]
    json_path: Path
    tsv_path: Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_native_channel(json_path: Path) -> NativePhysioChannel:
    """Load one dcm2niix-native _recording-<label>_physio.json/.tsv.gz pair.

    The label is parsed from the JSON filename (the token between
    '_recording-' and '_physio.json'). The companion TSV path is derived
    by replacing the '.json' suffix with '.tsv.gz'. The TSV is headerless
    (per BIDS convention for continuous recordings); columns are assigned
    by position from the JSON's `Columns` array -- this must have as many
    entries as the TSV has tab-separated fields, else raise
    PhysioParseError (a malformed sidecar/TSV pairing).
    """
    # Parse label from filename
    name = json_path.name
    m = re.search(r"_recording-(.+)_physio\.json$", name)
    if m is None:
        raise PhysioParseError(
            f"Cannot parse recording label from filename: {name!r}",
            context={"json_path": str(json_path)},
        )
    label = m.group(1)

    # Read JSON sidecar
    try:
        sidecar = json.loads(json_path.read_text())
    except Exception as exc:
        raise PhysioParseError(
            f"Failed to read JSON sidecar {json_path}: {exc}",
            context={"json_path": str(json_path)},
        ) from exc

    sampling_frequency: float = float(sidecar.get("SamplingFrequency", 0.0))
    start_time: float = float(sidecar.get("StartTime", 0.0))
    columns_list: list[str] = sidecar.get("Columns", [])
    columns: tuple[str, ...] = tuple(columns_list)

    # Derive TSV path
    tsv_path = json_path.with_suffix("").with_suffix(".tsv.gz")

    # Read TSV.GZ (headerless)
    rows: list[list[str]] = []
    try:
        with gzip.open(str(tsv_path), "rt", encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if line:
                    rows.append(line.split("\t"))
    except Exception as exc:
        raise PhysioParseError(
            f"Failed to read TSV {tsv_path}: {exc}",
            context={"tsv_path": str(tsv_path)},
        ) from exc

    # Validate column count
    if rows:
        n_fields = len(rows[0])
        if len(columns) != n_fields:
            raise PhysioParseError(
                f"Columns sidecar declares {len(columns)} columns but TSV has "
                f"{n_fields} tab-separated fields in {tsv_path}.",
                context={"json_path": str(json_path), "tsv_path": str(tsv_path)},
            )

    # Build data arrays keyed by column name
    data: dict[str, np.ndarray] = {}
    if columns and rows:
        for col_idx, col_name in enumerate(columns):
            values = []
            for row in rows:
                try:
                    values.append(float(row[col_idx]))
                except (IndexError, ValueError):
                    values.append(float("nan"))
            data[col_name] = np.array(values, dtype=np.float64)

    return NativePhysioChannel(
        label=label,
        sampling_frequency=sampling_frequency,
        start_time=start_time,
        columns=columns,
        data=data,
        json_path=json_path,
        tsv_path=tsv_path,
    )


def discover_native_physio(
    physio_sidecar_paths: list[Path],
) -> dict[int, dict[str, NativePhysioChannel]]:
    """Group dcm2niix-native physio sidecars by SeriesNumber, then by channel label.

    *physio_sidecar_paths* is the list load_series() already classified via
    _is_physio_sidecar() and returned separately from imaging Series -- this
    function does not re-classify by content, only groups the already-
    confirmed physio sidecars by filename structure (dcm2niix's own
    '{series_number}_..._recording-{label}_physio.json' naming convention,
    consistent with the '-f %s_%d' pattern stage1_convert.py passes to
    dcm2niix). The series_number is parsed as the leading integer token
    before the first underscore. Returns {series_number: {label: NativePhysioChannel}}.
    """
    result: dict[int, dict[str, NativePhysioChannel]] = {}

    for json_path in physio_sidecar_paths:
        # Parse series number: leading integer before first underscore
        stem = json_path.name
        m = re.match(r"^(\d+)_", stem)
        if m is None:
            continue
        series_number = int(m.group(1))

        try:
            channel = _load_native_channel(json_path)
        except PhysioParseError:
            raise

        if series_number not in result:
            result[series_number] = {}
        result[series_number][channel.label] = channel

    return result


# ---------------------------------------------------------------------------
# Trigger-derived volume counting and association
# ---------------------------------------------------------------------------


def _count_trigger_events(samples: np.ndarray) -> int:
    """Count discrete trigger pulses in *samples* via rising-edge detection.

    Threshold is the midpoint between the observed min and max sample
    value; a rising edge is any sample-to-sample transition from below
    to at-or-above that threshold. Deliberately encoding-agnostic (works
    whether the channel is boolean 0/1 pulses or amplitude-coded events).
    An incorrect edge-count here is caught downstream by the geometry
    guard in associate_native_physio() (mismatch against bold.n_volumes
    raises PhysioAssociationError) -- halt on uncertainty, not silent
    propagation.
    """
    if len(samples) < 2:
        return 0
    lo = float(np.min(samples))
    hi = float(np.max(samples))
    if hi == lo:
        return 0
    threshold = (lo + hi) / 2.0
    below = samples[:-1] < threshold
    at_or_above = samples[1:] >= threshold
    rising_edges = np.logical_and(below, at_or_above)
    return int(np.sum(rising_edges))


def _find_trigger_column(
    channels: dict[str, NativePhysioChannel],
) -> tuple[str, np.ndarray]:
    """Locate the BIDS-canonical shared trigger column across *channels*.

    Prefers an exact column name 'trigger'; falls back to the first column
    name containing 'trigger' case-insensitively (e.g. 'external_trigger_peak')
    if no exact match exists in any channel. Raises PhysioParseError if no
    candidate column is found in any channel.
    """
    # Exact match first
    for channel in channels.values():
        if "trigger" in channel.data:
            return ("trigger", channel.data["trigger"])

    # Case-insensitive substring fallback
    for channel in channels.values():
        for col_name, col_data in channel.data.items():
            if "trigger" in col_name.lower():
                return (col_name, col_data)

    raise PhysioParseError(
        "No trigger column found in any physio channel. "
        f"Available channels: {list(channels)}, "
        f"columns: {[list(ch.columns) for ch in channels.values()]}",
        context={"channels": list(channels)},
    )


def associate_native_physio(
    recordings: dict[int, dict[str, NativePhysioChannel]],
    bolds: list[Series],
) -> dict[int, int]:
    """Associate each physio recording with a BOLD run.

    For each recording, restrict to BOLD series whose series_number is <=
    the recording's series_number and take the one with the largest such
    series_number (nearest preceding); if none precede, fall back to the
    nearest by absolute |series_number difference|. SeriesNumber substitutes
    for the retired acquisition_datetime-based ordering because dcm2niix's
    native physio JSON carries no absolute-clock field -- SeriesNumber is a
    standard DICOM field that increases monotonically with acquisition
    order, so this is a like-for-like substitution of the ordering key.

    After selection, hard-guards the match: derives num_volumes via
    _find_trigger_column() + _count_trigger_events() and compares against
    the selected BOLD's n_volumes; raises PhysioAssociationError on mismatch.

    Note: the retired function's second geometry signal, num_slices, is NOT
    reproduced (dcm2niix's native trigger channel exposes only per-volume
    timing). The guard is single-signal (num_volumes) where it was
    previously two-signal.

    Returns {bold_series_number: physio_series_number}.
    """
    result: dict[int, int] = {}

    for physio_series_number, channels in recordings.items():
        # Find nearest preceding BOLD by series_number
        preceding = [b for b in bolds if b.series_number <= physio_series_number]
        if preceding:
            best_bold = max(preceding, key=lambda b: b.series_number)
        else:
            best_bold = min(
                bolds,
                key=lambda b: abs(b.series_number - physio_series_number),
            )

        # Geometry guard: count trigger-derived volumes
        try:
            _col_name, trigger_samples = _find_trigger_column(channels)
        except PhysioParseError as exc:
            raise PhysioAssociationError(
                f"Physio series {physio_series_number}: {exc}",
                context={
                    "physio_series": physio_series_number,
                    "bold_series": best_bold.series_number,
                },
            ) from exc

        num_volumes = _count_trigger_events(trigger_samples)
        if num_volumes != best_bold.n_volumes:
            raise PhysioAssociationError(
                f"Trigger-derived num_volumes ({num_volumes}) does not match "
                f"BOLD n_volumes ({best_bold.n_volumes}) for BOLD series "
                f"{best_bold.series_number} (physio series {physio_series_number}).",
                context={
                    "physio_series": physio_series_number,
                    "bold_series": best_bold.series_number,
                    "trigger_num_volumes": num_volumes,
                    "bold_n_volumes": best_bold.n_volumes,
                },
            )

        result[best_bold.series_number] = physio_series_number

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_physio(
    physio_series_number: int,
    staging_dir: Path,
    run_prefix: str,
    bids_dir: Path,
) -> list[Path]:
    """Copy dcm2niix's native per-channel physio export to the BIDS tree.

    Re-globs *staging_dir* for '{physio_series_number}_*_recording-*_physio.json'
    (and each JSON's companion .tsv.gz) directly -- a fresh, minimal lookup for
    the one already-associated series, not a re-derivation of the association
    computed earlier in associate_native_physio(). For each channel found,
    copies (shutil.copy2, verbatim -- no re-derivation or recombination) to
    bids_dir / f'{run_prefix}_recording-{label}_physio.tsv.gz' and the matching
    '.json'. dcm2niix's native output already satisfies the BIDS _physio.json
    contract, so no sidecar rewriting is performed.

    The retired write_physio()'s sourcedata/<run_prefix>_physio_raw.txt
    provenance dump is NOT reproduced: since this replacement copies dcm2niix's
    complete native per-channel output directly into func/ with no filtering
    step, there is no lossy transformation left to provide raw provenance
    against.

    Returns all paths written (2 files per channel found: .tsv.gz + .json).
    """
    written: list[Path] = []

    pattern = f"{physio_series_number}_*_recording-*_physio.json"
    json_paths = sorted(staging_dir.glob(pattern))

    bids_dir.mkdir(parents=True, exist_ok=True)

    for json_path in json_paths:
        # Parse label from filename
        m = re.search(r"_recording-(.+)_physio\.json$", json_path.name)
        if m is None:
            continue
        label = m.group(1)

        tsv_path = json_path.with_suffix("").with_suffix(".tsv.gz")

        dest_json = bids_dir / f"{run_prefix}_recording-{label}_physio.json"
        dest_tsv = bids_dir / f"{run_prefix}_recording-{label}_physio.tsv.gz"

        shutil.copy2(str(json_path), str(dest_json))
        written.append(dest_json)

        if tsv_path.exists():
            shutil.copy2(str(tsv_path), str(dest_tsv))
            written.append(dest_tsv)

    return written
