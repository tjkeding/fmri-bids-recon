"""Task label derivation and registry resolution for fmri-bids-recon.

Derives BIDS task labels from SeriesDescription strings, enforces injectivity
(collision guard), detects label drift against the frozen registry, and detects
undeclared task renames via acquisition-signature matching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .config import TaskRegistryEntry
from .errors import EmptyLabelError, LabelCollisionError, LabelDriftError, TaskRenameError
from .sidecar import Series
from .stage2_classify import Role


# ---------------------------------------------------------------------------
# Stop-words
# ---------------------------------------------------------------------------

BIDS_STOP_WORDS: frozenset[str] = frozenset({
    # entity keywords
    "task", "run", "dir", "acq", "rec", "echo", "part", "chunk", "ses", "sub",
    # suffix / modality
    "fmri", "bold", "epi", "sbref", "dwi", "dmri", "t1w", "t2w", "mprage",
    "spc", "tse", "flair",
    # directions
    "ap", "pa", "lr", "rl", "is", "si",
    # vendor recon tokens
    "nd", "norm", "mb", "dis2d", "setter", "vnav", "distortionmap", "physiolog",
})

_RE_SPLIT = re.compile(r"[_\-\s]+")
_RE_ALPHANUM = re.compile(r"[^a-z0-9]")
_SBREF_SUFFIX_RE = re.compile(r"[_\s]*sbref\s*$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Prefix derivation
# ---------------------------------------------------------------------------

def derive_prefix(descriptions: list[str]) -> tuple[str, ...]:
    """Find the longest common leading token sequence across all descriptions.

    Parameters
    ----------
    descriptions : list[str]
        SeriesDescription strings of all retained (non-dropped) series, as
        produced after role classification (DROP_* roles excluded).

    Returns
    -------
    tuple[str, ...]
        Longest common leading token sequence. Returns an empty tuple when
        *descriptions* is empty, any entry tokenizes to an empty list, or
        the first tokens do not agree across all descriptions.
    """
    if not descriptions:
        return ()

    tokenized: list[list[str]] = [
        [t for t in _RE_SPLIT.split(d) if t] for d in descriptions
    ]

    if not tokenized or any(not tokens for tokens in tokenized):
        return ()

    prefix: list[str] = []
    for i, token in enumerate(tokenized[0]):
        if all(len(tokens) > i and tokens[i] == token for tokens in tokenized[1:]):
            prefix.append(token)
        else:
            break

    return tuple(prefix)


# ---------------------------------------------------------------------------
# Label derivation
# ---------------------------------------------------------------------------

def derive_task_label(description: str, prefix: tuple[str, ...]) -> str:
    """Derive a BIDS task label from a SeriesDescription.

    Splits *description* on ``[_\\-\\s]``, strips the leading *prefix* tokens,
    discards tokens whose lowercase form is in :data:`BIDS_STOP_WORDS`,
    sanitizes each remaining token to lowercase alphanumeric only, and joins
    all non-empty results into a single string.

    Parameters
    ----------
    description : str
        SeriesDescription string.
    prefix : tuple[str, ...]
        Leading token sequence to strip (as returned by :func:`derive_prefix`).

    Returns
    -------
    str
        BIDS-legal task label (lowercase alphanumeric, no hyphens or
        underscores).

    Raises
    ------
    EmptyLabelError
        If all tokens are consumed by prefix stripping, stop-word filtering,
        or sanitization, leaving an empty label.
    """
    tokens = [t for t in _RE_SPLIT.split(description) if t]

    # Strip leading prefix tokens
    n = len(prefix)
    if n and tokens[:n] == list(prefix):
        tokens = tokens[n:]

    # Drop stop words; sanitize survivors to lowercase alphanumeric
    result_tokens: list[str] = []
    for token in tokens:
        if token.lower() in BIDS_STOP_WORDS:
            continue
        sanitized = _RE_ALPHANUM.sub("", token.lower())
        if sanitized:
            result_tokens.append(sanitized)

    label = "".join(result_tokens)
    if not label:
        raise EmptyLabelError(
            f"SeriesDescription '{description}' produced an empty BIDS task label "
            f"after prefix stripping and stop-word filtering.",
            context={"description": description, "prefix": prefix},
        )
    return label


# ---------------------------------------------------------------------------
# RegistryDelta dataclass
# ---------------------------------------------------------------------------

@dataclass
class RegistryDelta:
    """Incremental additions to the task registry from the current session.

    Parameters
    ----------
    new_entries : dict[str, TaskRegistryEntry]
        Mapping of SeriesDescription to new :class:`~fmri_bids_recon.config.TaskRegistryEntry`
        instances for descriptions not previously in the registry. Intended to
        be merged into the study config after user review.
    warnings : list[str]
        Non-blocking advisory messages generated during label resolution.
    """

    new_entries: dict[str, TaskRegistryEntry] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Acquisition signature
# ---------------------------------------------------------------------------

def acquisition_signature(s: Series) -> tuple:
    """Compute an acquisition fingerprint for rename detection.

    Run length (``n_volumes``) is deliberately excluded to allow BOLD and SBRef
    pairs to match each other, and to tolerate variable run lengths across
    sessions without triggering false rename alerts.

    Parameters
    ----------
    s : Series
        Series to fingerprint.

    Returns
    -------
    tuple
        ``(repetition_time, effective_echo_spacing, multiband_factor, matrix)``
        where TR is rounded to 4 decimal places and EES to 7 decimal places.
        Fields are ``None`` when the corresponding sidecar key is absent.
    """
    tr = round(s.repetition_time, 4) if s.repetition_time is not None else None
    ees = (
        round(s.effective_echo_spacing, 7)
        if s.effective_echo_spacing is not None
        else None
    )
    return (tr, ees, s.multiband_factor, s.matrix)


# ---------------------------------------------------------------------------
# Primary resolution function
# ---------------------------------------------------------------------------

_DROP_ROLES: frozenset[Role] = frozenset({
    Role.DROP_DERIVED,
    Role.DROP_SCOUT,
    Role.DROP_NAVIGATOR,
    Role.DROP_ANAT_ND_T1W,
    Role.DROP_ANAT_ND_T2W,
})


def resolve_labels(
    series_by_role: dict[int, tuple[Series, Role]],
    registry: dict[str, TaskRegistryEntry],
) -> tuple[dict[int, str], RegistryDelta]:
    """Resolve BIDS task labels for all BOLD and SBREF series.

    Applies the task-registry growth policy: frozen label reuse for known
    descriptions, auto-derivation for new descriptions, and three blocking
    guards: label drift, task rename by acquisition signature, and label
    collision (injectivity violation).

    The common prefix used for label derivation is computed from ALL retained
    (non-dropped) series in *series_by_role*, not only from BOLD/SBREF series,
    so that scanner-prefix conventions are stripped consistently.

    Parameters
    ----------
    series_by_role : dict[int, tuple[Series, Role]]
        Mapping of ``series_number`` to ``(Series, Role)`` for every classified
        series in the current session.
    registry : dict[str, TaskRegistryEntry]
        Existing task registry keyed by SeriesDescription. Descriptions absent
        from this dict are treated as new and auto-derived.

    Returns
    -------
    tuple[dict[int, str], RegistryDelta]
        ``(label_map, delta)`` where *label_map* maps each BOLD/SBREF
        ``series_number`` to its resolved task label, and *delta* carries new
        registry entries to be merged into the study config.

    Raises
    ------
    LabelDriftError
        If a registered description re-derives to a label that differs from the
        frozen registry value, indicating an undeclared label change.
    TaskRenameError
        If a new description's acquisition signature matches a series associated
        with an old registry description absent from the current session,
        indicating an undeclared task rename.
    LabelCollisionError
        If two or more distinct descriptions resolve to the same task label,
        violating BIDS label injectivity.
    EmptyLabelError
        Propagated from :func:`derive_task_label` when a description strips to
        an empty label.
    """
    # ------------------------------------------------------------------
    # Prefix: derived from ALL retained (non-dropped) series descriptions
    # ------------------------------------------------------------------
    retained_descriptions: list[str] = [
        s.description
        for _snum, (s, role) in series_by_role.items()
        if role not in _DROP_ROLES
    ]
    prefix = derive_prefix(retained_descriptions)

    # ------------------------------------------------------------------
    # Collect BOLD / SBREF series
    # ------------------------------------------------------------------
    bold_sbref: list[tuple[int, Series]] = [
        (snum, s)
        for snum, (s, role) in series_by_role.items()
        if role in (Role.BOLD, Role.SBREF)
    ]

    # ------------------------------------------------------------------
    # Build acquisition-signature maps for rename detection.
    # Keyed over ALL series (not just BOLD/SBREF) so that old registry
    # descriptions still present in the session under non-BOLD roles can
    # be compared.
    # ------------------------------------------------------------------
    all_sig_by_desc: dict[str, set] = {}
    for _snum, (s, _role) in series_by_role.items():
        sig = acquisition_signature(s)
        all_sig_by_desc.setdefault(s.description, set()).add(sig)

    # BOLD/SBREF descriptions observed this session
    current_bs_descs: set[str] = {s.description for _snum, s in bold_sbref}

    # Old registry descriptions: in registry but absent from current BOLD/SBREF
    old_registry_descs: set[str] = set(registry.keys()) - current_bs_descs

    # ------------------------------------------------------------------
    # Resolve label per unique BOLD/SBREF description
    # ------------------------------------------------------------------
    desc_to_label: dict[str, str] = {}
    delta = RegistryDelta()

    unique_descs: set[str] = {s.description for _snum, s in bold_sbref}

    for desc in unique_descs:
        if desc in registry:
            # Frozen label reuse
            frozen_label = registry[desc].label

            # Drift guard: re-derive and compare against the frozen value
            re_derived = derive_task_label(desc, prefix)
            if re_derived != frozen_label:
                raise LabelDriftError(
                    f"SeriesDescription '{desc}' re-derives to label '{re_derived}' "
                    f"but the registry records '{frozen_label}'. Declare an explicit "
                    f"label update in the registry before proceeding.",
                    context={
                        "description": desc,
                        "frozen_label": frozen_label,
                        "re_derived_label": re_derived,
                    },
                )
            desc_to_label[desc] = frozen_label

        else:
            # Auto-derive new label
            new_label = derive_task_label(desc, prefix)
            desc_to_label[desc] = new_label

            # Register as a new entry
            new_sigs = all_sig_by_desc.get(desc, set())
            delta.new_entries[desc] = TaskRegistryEntry(
                label=new_label,
                expected_volumes=None,
                first_seen=date.today().isoformat(),
                signature=next(iter(new_sigs)) if new_sigs else None,
            )

            # Rename check: compare against the persisted registry
            # (config.task_registry).  Two conditions each independently
            # indicate an undeclared rename:
            #
            # 1. Acquisition-signature match — fires when old_desc appears
            #    somewhere in the current session (any role), meaning its
            #    acquisition fingerprint is available for comparison.
            #
            # 2. Label match against the persisted registry — fires when
            #    new_label equals the label already stored for old_desc in the
            #    persisted registry, regardless of whether old_desc is present
            #    in the current session.  This covers the primary cross-session
            #    rename scenario where the old description is entirely absent.
            for old_desc in old_registry_descs:
                old_label = registry[old_desc].label
                old_sigs = set(all_sig_by_desc.get(old_desc, set()))
                stored_sig = getattr(registry[old_desc], "signature", None)
                if stored_sig is not None:
                    old_sigs.add(stored_sig)
                sig_match = bool(new_sigs & old_sigs)
                label_match = (new_label == old_label)
                if sig_match or label_match:
                    raise TaskRenameError(
                        f"New description '{desc}' (derived label '{new_label}') "
                        f"{'shares an acquisition signature with' if sig_match else 'derives the same label as'} "
                        f"old registry description '{old_desc}' (label '{old_label}'), which is "
                        f"absent from the current session. Declare an explicit rename "
                        f"in the task registry before proceeding.",
                        context={
                            "new_description": desc,
                            "new_label": new_label,
                            "old_description": old_desc,
                            "old_label": old_label,
                            "matching_signatures": list(new_sigs & old_sigs),
                        },
                    )

    # ------------------------------------------------------------------
    # Collision check: enforce injectivity (distinct description -> unique label)
    # ------------------------------------------------------------------
    label_to_descs: dict[str, list[str]] = {}
    for desc, label in desc_to_label.items():
        label_to_descs.setdefault(label, []).append(desc)

    for label, descs in label_to_descs.items():
        if len(descs) > 1:
            stems = {_SBREF_SUFFIX_RE.sub("", d).lower().strip() for d in descs}
            if len(stems) > 1:
                raise LabelCollisionError(
                    f"Task label '{label}' is claimed by {len(descs)} distinct "
                    f"SeriesDescriptions: {descs}. Each description must produce a "
                    f"unique BIDS task label.",
                    context={"label": label, "descriptions": descs},
                )

    # ------------------------------------------------------------------
    # Build series_number -> task_label output map
    # ------------------------------------------------------------------
    label_map: dict[int, str] = {
        snum: desc_to_label[s.description] for snum, s in bold_sbref
    }

    return label_map, delta
