"""Manifest tracking for fmri-bids-recon pipeline runs.

Maintains a TSV-backed record of per-(subject, session) pipeline status,
supporting idempotent re-runs via the should_skip predicate.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .tsv import upsert_tsv

# ---------------------------------------------------------------------------
# Status vocabulary
# ---------------------------------------------------------------------------

VALID_STATUSES = ("pending", "converted", "assembled", "validated", "failed")


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class ManifestEntry:
    """One row in the pipeline manifest TSV.

    Parameters
    ----------
    sub : str
        BIDS subject label (without ``sub-`` prefix).
    ses : str
        BIDS session label (without ``ses-`` prefix).
    status : str
        One of ``pending``, ``converted``, ``assembled``, ``validated``,
        ``failed``.
    timestamp : str
        ISO 8601 timestamp of the last status update.
    dcm2niix_version : str or None
        Version string reported by dcm2niix at conversion time; ``None``
        when the conversion stage has not yet run.
    """

    sub: str
    ses: str
    status: str
    timestamp: str  # ISO 8601
    dcm2niix_version: str | None


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def read_manifest(path: Path) -> dict[tuple[str, str], ManifestEntry]:
    """Read a manifest TSV and return a dict keyed by ``(sub, ses)``.

    Parameters
    ----------
    path : Path
        Path to the manifest TSV file.  Returns an empty dict if the file
        does not exist.

    Returns
    -------
    dict[tuple[str, str], ManifestEntry]
        Mapping from ``(sub, ses)`` to the corresponding
        :class:`ManifestEntry`.
    """
    if not path.exists():
        return {}

    result: dict[tuple[str, str], ManifestEntry] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            sub = row.get("sub", "")
            ses = row.get("ses", "")
            dcm2niix_version = row.get("dcm2niix_version") or None
            if dcm2niix_version in ("n/a", ""):
                dcm2niix_version = None
            entry = ManifestEntry(
                sub=sub,
                ses=ses,
                status=row.get("status", "pending"),
                timestamp=row.get("timestamp", ""),
                dcm2niix_version=dcm2niix_version,
            )
            result[(sub, ses)] = entry
    return result


def update_manifest(path: Path, entry: ManifestEntry) -> None:
    """Upsert a single :class:`ManifestEntry` into the manifest TSV.

    Uses :func:`~fmri_bids_recon.tsv.upsert_tsv` with the composite key
    ``sub_ses = f'{entry.sub}_{entry.ses}'`` for atomic read-modify-write.

    Parameters
    ----------
    path : Path
        Destination manifest TSV (created if absent).
    entry : ManifestEntry
        Record to insert or update.
    """
    if entry.status not in VALID_STATUSES:
        raise ValueError(
            f"Manifest status {entry.status!r} is not one of {VALID_STATUSES}."
        )
    row = {
        "sub_ses": f"{entry.sub}_{entry.ses}",
        "sub": entry.sub,
        "ses": entry.ses,
        "status": entry.status,
        "timestamp": entry.timestamp,
        "dcm2niix_version": entry.dcm2niix_version if entry.dcm2niix_version is not None else "n/a",
    }
    upsert_tsv(path, [row], key="sub_ses")


# ---------------------------------------------------------------------------
# Idempotency predicate
# ---------------------------------------------------------------------------

def should_skip(manifest: dict[tuple[str, str], ManifestEntry], sub: str, ses: str) -> bool:
    """Return ``True`` if ``(sub, ses)`` already has status ``'validated'``.

    Used by pipeline entry points to enable idempotent re-runs: a
    successfully validated session is not re-processed unless the manifest
    entry is reset externally.

    Parameters
    ----------
    manifest : dict[tuple[str, str], ManifestEntry]
        In-memory manifest produced by :func:`read_manifest`.
    sub : str
        Subject label (without ``sub-`` prefix).
    ses : str
        Session label (without ``ses-`` prefix).

    Returns
    -------
    bool
        ``True`` if the entry exists and its status is ``'validated'``.
    """
    entry = manifest.get((sub, ses))
    return entry is not None and entry.status == "validated"
