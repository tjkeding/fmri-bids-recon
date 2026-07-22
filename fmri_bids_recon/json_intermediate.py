"""JSON-based intermediate serialization for the fmri-bids-recon pipeline.

Provides round-trip encoding and decoding of the intermediate dict that is
written after Phase 1 (convert) and read at the start of Phase 3 (assemble).
All non-JSON-native types are tagged with a ``__type__`` discriminator so the
decoder can reconstruct the original Python objects faithfully.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime
from pathlib import Path as PathLib

from .sidecar import Series
from .stage2_classify import Role
from .stage3_map import Mapping, FieldmapPair
from .runs import Excluded
from .labels import RegistryDelta
from .config import TaskRegistryEntry
from .errors import ReviewFlag
from .physio import PhysioLog, PhysioChannel, AcquisitionInfo

# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

_DATACLASS_TYPES = (
    Series,
    FieldmapPair,
    Mapping,
    Excluded,
    RegistryDelta,
    TaskRegistryEntry,
    PhysioLog,
    PhysioChannel,
    AcquisitionInfo,
)


def _encode(obj):
    """Recursively encode *obj* into a JSON-serialisable structure."""
    # ReviewFlag (Exception subclass) — check before dataclass test
    if isinstance(obj, ReviewFlag):
        return {
            "__type__": "ReviewFlag",
            "f": {
                "message": str(obj),
                "context": _encode(obj.context),
            },
        }

    # Known dataclasses — check before dict, since dataclasses are not dicts
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            "__type__": type(obj).__name__,
            "f": {
                field.name: _encode(getattr(obj, field.name))
                for field in dataclasses.fields(obj)
            },
        }

    # Role (StrEnum)
    if isinstance(obj, Role):
        return {"__type__": "Role", "v": obj.value}

    # Path
    if isinstance(obj, PathLib):
        return {"__type__": "Path", "v": str(obj)}

    # datetime
    if isinstance(obj, datetime):
        return {"__type__": "datetime", "v": obj.isoformat()}

    # tuple
    if isinstance(obj, tuple):
        return {"__type__": "tuple", "v": [_encode(x) for x in obj]}

    # frozenset
    if isinstance(obj, frozenset):
        return {"__type__": "frozenset", "v": sorted([_encode(x) for x in obj])}

    # dict with ALL int keys — must be checked BEFORE general dict handling
    if isinstance(obj, dict) and obj and all(isinstance(k, int) for k in obj.keys()):
        return {
            "__type__": "int_key_dict",
            "v": {str(k): _encode(v) for k, v in obj.items()},
        }

    # dict with str keys (or empty dict)
    if isinstance(obj, dict):
        return {k: _encode(v) for k, v in obj.items()}

    # list
    if isinstance(obj, list):
        return [_encode(x) for x in obj]

    # primitives: str, int, float, bool, None
    return obj


# ---------------------------------------------------------------------------
# Decoding
# ---------------------------------------------------------------------------

_DATACLASS_MAP: dict[str, type] = {cls.__name__: cls for cls in _DATACLASS_TYPES}


def _decode(obj):
    """Recursively decode a structure previously produced by :func:`_encode`."""
    if isinstance(obj, dict):
        tag = obj.get("__type__")
        if tag is None:
            # Plain str-key dict
            return {k: _decode(v) for k, v in obj.items()}

        if tag == "Path":
            return PathLib(obj["v"])

        if tag == "datetime":
            return datetime.fromisoformat(obj["v"])

        if tag == "tuple":
            return tuple(_decode(x) for x in obj["v"])

        if tag == "frozenset":
            return frozenset(_decode(x) for x in obj["v"])

        if tag == "Role":
            return Role(obj["v"])

        if tag == "int_key_dict":
            return {int(k): _decode(v) for k, v in obj["v"].items()}

        if tag == "ReviewFlag":
            rf = ReviewFlag(obj["f"]["message"], context=_decode(obj["f"]["context"]))
            return rf

        if tag in _DATACLASS_MAP:
            cls = _DATACLASS_MAP[tag]
            return cls(**{k: _decode(v) for k, v in obj["f"].items()})

        # Unknown tag: return as-is to avoid silent data loss
        return obj

    if isinstance(obj, list):
        return [_decode(x) for x in obj]

    # primitives
    return obj


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def dump_intermediate(data: dict, path: PathLib) -> None:
    """Serialise *data* to *path* as a human-readable JSON file."""
    encoded = _encode(data)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(encoded, fh, indent=2)


def load_intermediate(path: PathLib) -> dict:
    """Deserialise the JSON file at *path* back into the intermediate dict."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return _decode(raw)
