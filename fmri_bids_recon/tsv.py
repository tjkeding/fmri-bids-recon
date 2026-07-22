"""Atomic tab-separated-value upsert with flock-protected read-modify-write."""

from __future__ import annotations

import csv
import fcntl
import hashlib
import os
import tempfile
from pathlib import Path


def upsert_tsv(path: Path, rows: list[dict], key: str) -> None:
    """Merge *rows* into *path* using *key* as the unique row identifier.

    Performs a read-modify-write under an exclusive ``flock`` on a sibling
    lockfile ``{path}.lock``, then atomically replaces the target via
    ``os.replace`` so that concurrent readers never observe a partial write.

    If *path* does not exist, it is created with the column set inferred from
    *rows*.  If it does exist, rows whose *key* value matches an existing row
    update that row's columns (only the columns present in the incoming row are
    overwritten; unrelated columns are preserved).  Rows with novel *key*
    values are appended.

    Parameters
    ----------
    path : Path
        Destination TSV file.
    rows : list[dict]
        Rows to upsert.  All dicts should share the same key set, though the
        implementation tolerates heterogeneous column sets.
    key : str
        Column name used as the merge key.
    """
    if not rows:
        return

    digest = hashlib.sha1(str(Path(path).resolve()).encode()).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"fmri_bids_recon_{digest}.lock"

    lock_fh = open(lock_path, "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)

        # Read existing rows and column order.
        existing: list[dict] = []
        existing_cols: list[str] = []
        if path.exists():
            with open(path, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                existing_cols = list(reader.fieldnames or [])
                existing = list(reader)

        # Build a mutable index of existing rows by key value.
        index: dict[str, dict] = {}
        for row in existing:
            if key in row:
                index[row[key]] = row

        # Merge incoming rows.
        for incoming in rows:
            k = incoming[key]
            if k in index:
                # Selective update: only columns provided by the incoming row.
                index[k].update(incoming)
            else:
                new_row = dict(incoming)
                index[k] = new_row
                existing.append(new_row)

        # Determine final column order: preserve existing columns first, then
        # append any new columns introduced by the incoming rows.
        seen_cols: set[str] = set(existing_cols)
        incoming_cols: list[str] = []
        for incoming in rows:
            for col in incoming:
                if col not in seen_cols:
                    seen_cols.add(col)
                    incoming_cols.append(col)
        final_cols: list[str] = existing_cols + incoming_cols
        if not final_cols:
            final_cols = list(rows[0].keys())

        # Write to a tempfile in the same directory, then atomic replace.
        dir_ = path.parent
        dir_.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tsv.tmp")
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as tmp_fh:
                writer = csv.DictWriter(
                    tmp_fh,
                    fieldnames=final_cols,
                    delimiter="\t",
                    extrasaction="ignore",
                    lineterminator="\n",
                    restval="n/a",
                )
                writer.writeheader()
                writer.writerows(existing)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    finally:
        fcntl.flock(lock_fh, fcntl.LOCK_UN)
        lock_fh.close()
