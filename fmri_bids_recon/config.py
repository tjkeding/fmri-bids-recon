"""Configuration loading and registry persistence for fmri-bids-recon.

Provides StudyConfig, ParticipantEntry, and TaskRegistryEntry dataclasses
along with load_config() and save_registry() for YAML-backed study configuration.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .errors import ConfigError


# ---------------------------------------------------------------------------
# Geometry tolerance constants
# ---------------------------------------------------------------------------
# Tolerances sized to absorb dcm2niix float jitter, NOT voxel-scaled;
# verified within-block delta 0.0mm, nearest block 2.53mm.
GEOMETRY_POSITION_TOL_MM = 0.1
GEOMETRY_ORIENTATION_TOL = 1e-4
GEOMETRY_VOXEL_TOL_MM = 1e-3

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TaskRegistryEntry:
    """Registry record for a known task label.

    Parameters
    ----------
    label : str
        BIDS task label (alphanumeric, no ``task-`` prefix).
    expected_volumes : int or None
        Expected number of volumes for this task, or None if not constrained.
    first_seen : str
        ISO-8601 date string (YYYY-MM-DD) of the first acquisition date for
        this label.
    signature : tuple or None
        Persisted acquisition fingerprint tuple
        ``(repetition_time, effective_echo_spacing, multiband_factor, matrix)``
        where *matrix* is an inner tuple, or None for entries registered before
        signature persistence was introduced.
    """

    label: str
    expected_volumes: Optional[int]
    first_seen: str
    signature: Optional[tuple] = None


@dataclass
class ParticipantEntry:
    """Single participant/session source-data pointer.

    Parameters
    ----------
    source : Path
        Absolute path to the raw DICOM directory for this participant/session.
    sub : str
        BIDS subject label (alphanumeric, no ``sub-`` prefix).
    ses : str
        BIDS session label (zero-padded integer, at least 2 digits).
    wave : str
        Study wave identifier (free-form string; may duplicate ``ses``).
    """

    source: Path
    sub: str
    ses: str
    wave: str


@dataclass
class StudyConfig:
    """Top-level configuration for an fmri-bids-recon study.

    Parameters
    ----------
    bids_root : Path
        Absolute path to the BIDS dataset root directory.
    staging_root : Path
        Absolute path to the staging scratch directory.  Must NOT be a
        subdirectory of ``bids_root`` to prevent concurrency hazards.
    dicom_root : Path
        Absolute path to the raw DICOM root directory.
    dicom_template : str
        Per-subject/session path template under ``dicom_root``.  Supports
        ``{subject}`` and ``{session}`` format placeholders.
    subjects : list[str]
        List of subject IDs to process (alphanumeric, no ``sub-`` prefix).
    sessions : list[str]
        List of session labels to process (zero-padded integer, at least 2 digits).
    physio : bool
        Whether to extract physiological data.  Defaults to False.
    deface : bool
        Whether to run the defacing stage.  Defaults to False.  Requires
        ``pydeface`` and FSL ``flirt`` on PATH; the pipeline verifies both
        at startup when this flag is True.
    participants : list[ParticipantEntry]
        Derived. Ordered list of participant/session entries resolved from the
        cross product of subjects x sessions.  Populated by load_config().
    task_registry : dict[str, TaskRegistryEntry]
        Derived. Mapping of task label to its registry entry.  Populated by
        load_config() from the sidecar ``.registry.yaml`` file.

    Properties
    ----------
    sourcedata_root : Path
        Derived path: ``bids_root / 'sourcedata'``.
    study_name : str
        Derived from ``bids_root.name``.
    """

    bids_root: Path
    staging_root: Path
    dicom_root: Path
    dicom_template: str
    subjects: list[str]
    sessions: list[str]
    physio: bool = False
    deface: bool = False
    participants: list[ParticipantEntry] = field(default_factory=list)
    task_registry: dict[str, TaskRegistryEntry] = field(default_factory=dict)

    @property
    def sourcedata_root(self) -> Path:
        return self.bids_root / "sourcedata"

    @property
    def study_name(self) -> str:
        return self.bids_root.name


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_RE_BIDS_ALPHANUM = re.compile(r"^[a-zA-Z0-9]+$")
_RE_SES_PADDED = re.compile(r"^[0-9]{2,}$")


def _validate_bids_label(value: str, field_name: str) -> None:
    if not _RE_BIDS_ALPHANUM.match(value):
        raise ValueError(
            f"ParticipantEntry.{field_name} '{value}' is not BIDS-legal "
            f"(must match ^[a-zA-Z0-9]+$)."
        )


def _validate_ses_label(ses: str) -> None:
    if not _RE_SES_PADDED.match(ses):
        raise ValueError(
            f"ParticipantEntry.ses '{ses}' does not match ^[0-9]{{2,}}$ "
            f"(must be a zero-padded integer with at least 2 digits)."
        )


def _is_subpath(child: Path, parent: Path) -> bool:
    """Return True if *child* is the same path as or a subdirectory of *parent*."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(path: str | Path) -> StudyConfig:
    """Load a study configuration YAML file and return a validated StudyConfig.

    Parameters
    ----------
    path : str or Path
        Path to the YAML configuration file.

    Returns
    -------
    StudyConfig
        Populated and validated configuration object.

    Raises
    ------
    FileNotFoundError
        If *path* itself does not exist, or if ``subjects`` is a string
        pointing to a non-existent file.
    ValueError
        If any subject label violates the alphanumeric constraint, if any
        session label is not zero-padded with at least 2 digits, if duplicate
        entries are found within the subjects or sessions lists, if
        ``staging_root`` is a subdirectory of (or equal to) ``bids_root``,
        or if ``subjects`` is a string that is not an absolute path.
    ConfigError
        If no DICOM paths resolve to existing directories after the full
        subjects x sessions cross-product expansion.
    """
    _log = logging.getLogger(__name__)

    path = Path(path)
    with path.open("r") as fh:
        raw = yaml.safe_load(fh)

    bids_root = Path(raw["bids_root"])
    staging_root = Path(raw["staging_root"])
    dicom_root = Path(raw["dicom_root"])
    dicom_template = str(raw["dicom_template"])
    if "{subject}" not in dicom_template:
        raise ValueError(
            "dicom_template must contain a '{subject}' placeholder."
        )
    if "{session}" not in dicom_template:
        raise ValueError(
            "dicom_template must contain a '{session}' placeholder."
        )
    raw_subjects = raw["subjects"]
    if isinstance(raw_subjects, str):
        subjects_path = Path(raw_subjects)
        if not subjects_path.is_absolute():
            raise ValueError(
                f"subjects file path must be absolute, got: '{raw_subjects}'"
            )
        if not subjects_path.exists():
            raise FileNotFoundError(
                f"subjects file not found: '{subjects_path}'"
            )
        subjects = []
        with subjects_path.open("r") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                subjects.append(stripped)
        if not subjects:
            raise ValueError(
                f"subjects file contains no valid entries: '{subjects_path}'"
            )
    elif isinstance(raw_subjects, list):
        subjects = [str(s) for s in raw_subjects]
    else:
        raise ValueError(
            f"subjects must be a YAML list of IDs or an absolute path to a "
            f"text file, got type: {type(raw_subjects).__name__}"
        )
    sessions = [str(s) for s in raw["sessions"]]
    physio = bool(raw.get("physio", False))
    deface = bool(raw.get("deface", False))

    # Validate subject labels
    for sub in subjects:
        _validate_bids_label(sub, "sub")

    # Validate session labels
    for ses in sessions:
        _validate_ses_label(ses)

    # Reject duplicate subjects
    seen_subjects: set[str] = set()
    for sub in subjects:
        if sub in seen_subjects:
            raise ValueError(
                f"Duplicate subject entry detected in subjects list: '{sub}'. "
                f"Each subject ID must appear at most once."
            )
        seen_subjects.add(sub)

    # Reject duplicate sessions
    seen_sessions: set[str] = set()
    for ses in sessions:
        if ses in seen_sessions:
            raise ValueError(
                f"Duplicate session entry detected in sessions list: '{ses}'. "
                f"Each session label must appear at most once."
            )
        seen_sessions.add(ses)

    # Guard: staging_root must not be inside bids_root
    if _is_subpath(staging_root, bids_root):
        raise ValueError(
            f"staging_root '{staging_root}' is a subpath of bids_root "
            f"'{bids_root}'. This is a concurrency hazard: pipeline writes "
            f"to staging_root would modify the BIDS dataset in-flight. "
            f"Set staging_root to a directory outside bids_root."
        )

    # Participant expansion via cross product of subjects x sessions
    participants: list[ParticipantEntry] = []
    for sub in subjects:
        for ses in sessions:
            resolved_path = Path(dicom_root) / dicom_template.format(subject=sub, session=ses)
            if not resolved_path.exists():
                _log.info(
                    "DICOM path not found for sub=%s ses=%s; skipping. "
                    "Resolved path: %s",
                    sub,
                    ses,
                    resolved_path,
                )
                continue
            participants.append(
                ParticipantEntry(
                    source=resolved_path,
                    sub=sub,
                    ses=ses,
                    wave=ses,
                )
            )

    # Raise if no participants resolved
    if not participants:
        raise ConfigError(
            "No DICOM paths resolved for any subject/session pair in the config.",
            context={
                "subjects": subjects,
                "sessions": sessions,
                "dicom_root": str(dicom_root),
                "dicom_template": dicom_template,
            },
        )

    # Load task_registry from sidecar file
    sidecar_path = Path(path).with_suffix(".registry.yaml")
    task_registry: dict[str, TaskRegistryEntry] = {}
    if sidecar_path.exists():
        with sidecar_path.open("r") as fh:
            sidecar_raw = yaml.safe_load(fh) or {}
        for label, trec in (sidecar_raw or {}).items():
            sig_raw = trec.get("signature")
            signature = None
            if sig_raw is not None:
                tr_v, ees_v, mb_v, matrix_v = sig_raw
                signature = (
                    tr_v, ees_v, mb_v,
                    tuple(matrix_v) if matrix_v is not None else None,
                )
            task_registry[label] = TaskRegistryEntry(
                label=str(trec["label"]),
                expected_volumes=(
                    int(trec["expected_volumes"])
                    if trec.get("expected_volumes") is not None
                    else None
                ),
                first_seen=str(trec["first_seen"]),
                signature=signature,
            )

    return StudyConfig(
        bids_root=bids_root,
        staging_root=staging_root,
        dicom_root=dicom_root,
        dicom_template=dicom_template,
        subjects=subjects,
        sessions=sessions,
        physio=physio,
        deface=deface,
        participants=participants,
        task_registry=task_registry,
    )


def save_registry(config: StudyConfig, path: str | Path) -> None:
    """Atomically persist the task_registry to the sidecar registry YAML file.

    The sidecar file is located at ``<path>.registry.yaml`` (i.e., the config
    path with the ``.yaml`` suffix replaced by ``.registry.yaml``).  The main
    config YAML is not modified.

    If the sidecar exists, its content is read first and the ``task_registry``
    is merged in; otherwise the sidecar is created from scratch.  The write is
    atomic: the new content is written to a temporary file in the same directory,
    then renamed via ``os.replace``.

    Parameters
    ----------
    config : StudyConfig
        Config object whose ``task_registry`` will be serialised.
    path : str or Path
        Path to the main YAML configuration file.  The sidecar is derived from
        this path; the main config file is not read or modified.
    """
    path = Path(path)
    sidecar_path = path.with_suffix(".registry.yaml")

    if sidecar_path.exists():
        with sidecar_path.open("r") as fh:
            existing = yaml.safe_load(fh) or {}
    else:
        existing = {}

    serialised_registry: dict = {}
    for label, entry in config.task_registry.items():
        entry_dict = {
            "label": entry.label,
            "expected_volumes": entry.expected_volumes,
            "first_seen": entry.first_seen,
        }
        if entry.signature is not None:
            tr_v, ees_v, mb_v, matrix_v = entry.signature
            entry_dict["signature"] = [
                tr_v, ees_v, mb_v,
                list(matrix_v) if matrix_v is not None else None,
            ]
        serialised_registry[label] = entry_dict

    existing.update(serialised_registry)

    dir_path = sidecar_path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".yaml.tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            yaml.safe_dump(existing, fh, default_flow_style=False, sort_keys=False)
        os.replace(tmp_path, sidecar_path)
    except Exception:
        # Clean up temp file on failure; ignore secondary errors.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
