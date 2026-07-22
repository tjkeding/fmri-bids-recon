"""Stage 3: fieldmap pairing and coverage mapping for fmri-bids-recon.

Maps each EPI fieldmap pair to the functional or diffusion targets it covers,
using a geometry-primary assignment policy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field  # noqa: F401 (field re-exported per spec)

from .sidecar import Series, modality_token  # noqa: F401 (modality_token re-exported)
from .stage2_classify import Role
from .errors import (
    PhaseEncodingError,
    FieldmapCoverageError,
)
from .config import (
    GEOMETRY_POSITION_TOL_MM,
    GEOMETRY_ORIENTATION_TOL,
    GEOMETRY_VOXEL_TOL_MM,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase-encoding direction constants
# ---------------------------------------------------------------------------

PE_DIRECTION_TO_LABEL: dict[str, str] = {
    "j": "PA",
    "j-": "AP",
    "i": "LR",
    "i-": "RL",
    "k": "IS",
    "k-": "SI",
}

PE_OPPOSITES: set[frozenset[str]] = {
    frozenset({"j", "j-"}),
    frozenset({"i", "i-"}),
    frozenset({"k", "k-"}),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class FieldmapPair:
    """A validated pair of EPI fieldmap series with opposite phase-encoding.

    Parameters
    ----------
    member_a : Series
        First fieldmap series (earlier in acquisition order).
    member_b : Series
        Second fieldmap series (later in acquisition order).
    modality : str
        ``'func'`` (FMAP_FUNC) or ``'dwi'`` (FMAP_DWI).
    run_index : int
        1-based index within the same modality's pairs.
    dir_a : str
        BIDS ``dir-`` label for member_a (e.g. ``'PA'``).
    dir_b : str
        BIDS ``dir-`` label for member_b (e.g. ``'AP'``).
    """

    member_a: Series
    member_b: Series
    modality: str
    run_index: int
    dir_a: str
    dir_b: str


@dataclass
class Mapping:
    """Complete fieldmap-to-target assignment for all pairs.

    Parameters
    ----------
    pairs : list[FieldmapPair]
        All validated fieldmap pairs.
    pair_to_targets : dict[int, list[Series]]
        Maps each pair's position in ``pairs`` to the list of target series
        it covers.
    """

    pairs: list[FieldmapPair]
    pair_to_targets: dict[int, list[Series]]
    bids_relative_paths: dict[int, str] = field(default_factory=dict)


@dataclass
class GeometryResult:
    """Outcome of a pairwise geometry compatibility check.

    Parameters
    ----------
    compatible : bool
        True when all geometry criteria are satisfied.
    failures : list[str]
        Human-readable diagnostic strings for each criterion that failed.
        Empty when compatible is True.
    """

    compatible: bool
    failures: list[str]


# ---------------------------------------------------------------------------
# Geometry helper
# ---------------------------------------------------------------------------


def _geometry_check(a: Series, b: Series) -> GeometryResult:
    """Return a GeometryResult describing geometry compatibility between series a and b.

    Checks image_position (within GEOMETRY_POSITION_TOL_MM per axis), the
    3x3 rotation block of the affine (within GEOMETRY_ORIENTATION_TOL),
    voxel_sizes (within GEOMETRY_VOXEL_TOL_MM), exact matrix equality, and
    identical non-None pe_axis.  Returns a GeometryResult with compatible=False
    immediately if any of image_position, affine, voxel_sizes, or pe_axis is
    None on either series, reporting the None field names in failures.

    Parameters
    ----------
    a : Series
        First series.
    b : Series
        Second series.

    Returns
    -------
    GeometryResult
        compatible=True when all geometry criteria are satisfied; compatible=False
        otherwise with failures listing each criterion that was not met, including
        the observed delta and tolerance exceeded.
    """
    none_fields = [
        name
        for name, v in [
            ("a.image_position", a.image_position),
            ("a.affine", a.affine),
            ("a.voxel_sizes", a.voxel_sizes),
            ("a.pe_axis", a.pe_axis),
            ("b.image_position", b.image_position),
            ("b.affine", b.affine),
            ("b.voxel_sizes", b.voxel_sizes),
            ("b.pe_axis", b.pe_axis),
        ]
        if v is None
    ]
    if none_fields:
        return GeometryResult(
            compatible=False,
            failures=[f"None geometry field(s): {', '.join(none_fields)}"],
        )

    failures: list[str] = []

    # 1. Image position: each axis within GEOMETRY_POSITION_TOL_MM.
    for idx, (va, vb) in enumerate(zip(a.image_position, b.image_position)):  # type: ignore[arg-type]
        delta = abs(va - vb)
        if delta > GEOMETRY_POSITION_TOL_MM:
            failures.append(
                f"image_position[{idx}]: delta={delta:.3f} mm > tol={GEOMETRY_POSITION_TOL_MM:.3f} mm"
            )

    # 2. Rotation block: rows 0-2, cols 0-2 of affine within GEOMETRY_ORIENTATION_TOL.
    #    The translation column is covered by image_position above.
    for row in range(3):
        for col in range(3):
            delta = abs(a.affine[row][col] - b.affine[row][col])  # type: ignore[index]
            if delta > GEOMETRY_ORIENTATION_TOL:
                failures.append(
                    f"affine[{row}][{col}]: delta={delta:.6f} > tol={GEOMETRY_ORIENTATION_TOL:.6f}"
                )

    # 3. Voxel sizes: each within GEOMETRY_VOXEL_TOL_MM.
    for idx, (va, vb) in enumerate(zip(a.voxel_sizes, b.voxel_sizes)):  # type: ignore[arg-type]
        delta = abs(va - vb)
        if delta > GEOMETRY_VOXEL_TOL_MM:
            failures.append(
                f"voxel_sizes[{idx}]: delta={delta:.3f} mm > tol={GEOMETRY_VOXEL_TOL_MM:.3f} mm"
            )

    # 4. Matrix: exact equality.
    if a.matrix != b.matrix:
        failures.append(f"matrix: {a.matrix!r} != {b.matrix!r}")

    # 5. PE axis: non-None and identical (None guard already applied above).
    if a.pe_axis != b.pe_axis:
        failures.append(f"pe_axis: {a.pe_axis!r} != {b.pe_axis!r}")

    return GeometryResult(compatible=len(failures) == 0, failures=failures)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def order_series(series: list[Series]) -> list[Series]:
    """Sort series ascending by acquisition_datetime.

    Parameters
    ----------
    series : list[Series]
        Unordered list of Series instances.

    Returns
    -------
    list[Series]
        Series sorted ascending by acquisition_datetime.

    Notes
    -----
    AcquisitionDateTime is the authoritative chronological anchor and SeriesNumber
    is NOT chronological on Siemens XA30, so a SeriesNumber/AcquisitionDateTime
    disagreement is expected and is not treated as an error.
    """
    return sorted(series, key=lambda s: s.acquisition_datetime)


def pair_fieldmaps(
    fmaps: list[tuple[Series, Role]],
    ordered: list[Series],
    guard_log: dict,
) -> list[FieldmapPair]:
    """Group EPI fieldmaps into geometry-compatible pairs and validate phase-encoding.

    Partitions fieldmaps into geometry groups via the transitive closure of
    :func:`_geometry_check` (union-find).  Within each geometry group,
    series are split by modality (func/dwi) and paired consecutively by
    acquisition_datetime.  Each modality sub-group must contain an even number
    of members; each consecutive pair must carry opposite PE directions.

    Parameters
    ----------
    fmaps : list[tuple[Series, Role]]
        Fieldmap series paired with their classification roles (FMAP_FUNC or FMAP_DWI).
    ordered : list[Series]
        All series sorted by acquisition_datetime, as returned by :func:`order_series`.
        Passed for context; pairing uses per-modality sort within each geometry group.
    guard_log : dict
        Mutable dict updated with validation gate outcomes:
        ``opposite_pe_within_pair``, ``dir_label_pe_agreement``,
        ``fieldmap_pairing_unambiguous``.

    Returns
    -------
    list[FieldmapPair]
        Validated fieldmap pairs in geometry-group then modality (func, dwi) order.

    Raises
    ------
    PhaseEncodingError
        If a geometry group's modality sub-group has an odd member count, if
        consecutive pair members do not carry opposite PE directions, or if a
        series description token (_PA or _AP) disagrees with the physics-derived
        BIDS label.
    """
    if not fmaps:
        guard_log["fieldmap_pairing_unambiguous"] = True
        return []

    # Step 1: Partition fmaps into geometry groups via transitive closure (union-find).
    n = len(fmaps)
    parent = list(range(n))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(x: int, y: int) -> None:
        px, py = _find(x), _find(y)
        if px != py:
            parent[px] = py

    series_list = [s for s, _ in fmaps]
    for i in range(n):
        for j in range(i + 1, n):
            if _geometry_check(series_list[i], series_list[j]).compatible:
                _union(i, j)

    # Collect indices belonging to each group, keyed by group root.
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = _find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(i)

    # Step 2 & 3: Within each geometry group, split by modality and pair consecutively.
    run_index_by_modality: dict[str, int] = {"func": 1, "dwi": 1}
    pairs: list[FieldmapPair] = []

    for _root, indices in groups.items():
        by_modality: dict[str, list[Series]] = {"func": [], "dwi": []}
        for idx in indices:
            s, role = fmaps[idx]
            if role == Role.FMAP_FUNC:
                by_modality["func"].append(s)
            elif role == Role.FMAP_DWI:
                by_modality["dwi"].append(s)

        for modality in ("func", "dwi"):
            members = sorted(
                by_modality[modality], key=lambda s: s.acquisition_datetime
            )
            if not members:
                continue

            # Must be even count; odd count cannot balance into opposite-PE pairs.
            if len(members) % 2 != 0:
                raise PhaseEncodingError(
                    f"Geometry group contains an odd number ({len(members)}) of "
                    f"'{modality}' fieldmap series; cannot form balanced "
                    f"opposite-PE pairs.",
                    context={
                        "modality": modality,
                        "count": len(members),
                        "series_numbers": [s.series_number for s in members],
                    },
                )

            for i in range(0, len(members), 2):
                a = members[i]
                b = members[i + 1]

                ped_a = a.phase_encoding_direction
                ped_b = b.phase_encoding_direction

                # GUARD 1: members must form an opposite PE pair. A None ped_a/ped_b
                # cannot reach here: _geometry_check requires a non-None pe_axis
                # on both series to group them at all, so a None-PE series is always
                # isolated into its own singleton group and fails the even-count
                # check above before this loop ever runs.
                if frozenset({ped_a, ped_b}) not in PE_OPPOSITES:
                    raise PhaseEncodingError(
                        f"Fieldmap pair members do not have opposite phase-encoding "
                        f"directions: series {a.series_number} ped={ped_a!r}, "
                        f"series {b.series_number} ped={ped_b!r}.",
                        context={
                            "modality": modality,
                            "series_a": a.series_number,
                            "ped_a": ped_a,
                            "series_b": b.series_number,
                            "ped_b": ped_b,
                        },
                    )

                guard_log["opposite_pe_within_pair"] = True

                dir_a = PE_DIRECTION_TO_LABEL[ped_a]
                dir_b = PE_DIRECTION_TO_LABEL[ped_b]

                # GUARD 4: cross-check description name token (_PA / _AP) against
                # the physics-derived BIDS dir- label.
                for s_check, dir_label in ((a, dir_a), (b, dir_b)):
                    desc_upper = s_check.description.upper()
                    for token in ("_PA", "_AP"):
                        if token in desc_upper:
                            expected_dir = token.lstrip("_")
                            if dir_label != expected_dir:
                                raise PhaseEncodingError(
                                    f"Series {s_check.series_number}: description token "
                                    f"'{token}' disagrees with physics-derived PE label "
                                    f"'{dir_label}' "
                                    f"(phase_encoding_direction="
                                    f"{s_check.phase_encoding_direction!r}).",
                                    context={
                                        "series_number": s_check.series_number,
                                        "description": s_check.description,
                                        "name_token": token,
                                        "physics_label": dir_label,
                                        "phase_encoding_direction": (
                                            s_check.phase_encoding_direction
                                        ),
                                    },
                                )

                guard_log["dir_label_pe_agreement"] = True

                pairs.append(
                    FieldmapPair(
                        member_a=a,
                        member_b=b,
                        modality=modality,
                        run_index=run_index_by_modality[modality],
                        dir_a=dir_a,
                        dir_b=dir_b,
                    )
                )
                run_index_by_modality[modality] += 1

    guard_log["fieldmap_pairing_unambiguous"] = True
    return pairs


def map_fieldmaps(
    pairs: list[FieldmapPair],
    targets: list[tuple[Series, Role]],
    ordered: list[Series],
    guard_log: dict,
) -> Mapping:
    """Assign each target series to a geometry-compatible fieldmap pair.

    For each target (iterated in ascending acquisition_datetime order): the
    eligible set is all pairs whose member_a passes _geometry_check against the
    target (geometry compatibility implies matching pe_axis).  If exactly one
    eligible pair exists it is chosen directly; if multiple exist, the pair
    whose later member's acquisition_datetime is nearest in time to the target
    is chosen (a tie in time distance raises :exc:`FieldmapCoverageError`).
    After assignment, every pair must serve at least one target (orphan check).

    Parameters
    ----------
    pairs : list[FieldmapPair]
        Validated fieldmap pairs from :func:`pair_fieldmaps`.
    targets : list[tuple[Series, Role]]
        Target series (BOLD or DWI) with their classification roles.
    ordered : list[Series]
        All series sorted by acquisition_datetime, as returned by :func:`order_series`.
        Passed for context; assignment uses per-target sort.
    guard_log : dict
        Mutable dict updated with validation gate outcomes:
        ``fieldmap_target_geometry_match``, ``pe_axis_target_match``,
        ``association_unambiguous``, ``no_orphan_pairs``.

    Returns
    -------
    Mapping
        Assignment indexed by position in ``pairs``.  ``bids_relative_paths``
        uses its default_factory and is populated later by stage 4.

    Raises
    ------
    FieldmapCoverageError
        If a target has no geometry-compatible pair, if a time-distance tie
        exists among multiple eligible pairs, or if any pair is left with no
        assigned targets (orphan pair).
    """
    _ROLE_TO_MODALITY: dict[Role, str] = {
        Role.BOLD: "func",
        Role.DWI: "dwi",
    }
    _SBREF_MODALITY: dict[Role, str] = {Role.SBREF: "func", Role.DWI_SBREF: "dwi"}

    pair_to_targets: dict[int, list[Series]] = {i: [] for i in range(len(pairs))}

    # Iterate targets in ascending acquisition_datetime for deterministic assignment.
    targets_sorted = sorted(targets, key=lambda x: x[0].acquisition_datetime)

    for s, role in targets_sorted:
        modality = _ROLE_TO_MODALITY.get(role)
        if modality is None:
            continue

        # Geometry-compatible pairs (pe_axis agreement is part of _geometry_check).
        checks = [(i, _geometry_check(p.member_a, s)) for i, p in enumerate(pairs)]
        eligible = [i for i, result in checks if result.compatible]

        guard_log["fieldmap_target_geometry_match"] = True
        guard_log["pe_axis_target_match"] = True

        if not eligible:
            candidate_pairs = [
                {
                    "pair_index": i,
                    "run_index": pairs[i].run_index,
                    "modality": pairs[i].modality,
                    "series": [pairs[i].member_a.series_number, pairs[i].member_b.series_number],
                    "failures": result.failures,
                }
                for i, result in checks
                if not result.compatible
            ]
            raise FieldmapCoverageError(
                f"Series {s.series_number} (description={s.description!r}, "
                f"modality={modality!r}) has no geometry-compatible fieldmap pair.",
                context={
                    "series_number": s.series_number,
                    "description": s.description,
                    "modality": modality,
                    "acquisition_datetime": str(s.acquisition_datetime),
                    "candidate_pairs": candidate_pairs,
                },
            )

        if len(eligible) == 1:
            chosen = eligible[0]
        else:
            # Nearest-in-time among eligible; pair time = later of the two members.
            def _time_dist(pair_idx: int) -> float:
                p = pairs[pair_idx]
                pair_dt = max(
                    p.member_a.acquisition_datetime,
                    p.member_b.acquisition_datetime,
                )
                return abs((s.acquisition_datetime - pair_dt).total_seconds())

            sorted_eligible = sorted(eligible, key=_time_dist)
            d0 = _time_dist(sorted_eligible[0])
            d1 = _time_dist(sorted_eligible[1])
            if d0 == d1:
                raise FieldmapCoverageError(
                    f"Series {s.series_number} (description={s.description!r}) has "
                    f"a time-distance tie between eligible fieldmap pairs "
                    f"{sorted_eligible[0]} and {sorted_eligible[1]}; "
                    f"association is ambiguous.",
                    context={
                        "series_number": s.series_number,
                        "description": s.description,
                        "tied_pair_indices": [sorted_eligible[0], sorted_eligible[1]],
                    },
                )
            chosen = sorted_eligible[0]

        pair_to_targets[chosen].append(s)

    guard_log["association_unambiguous"] = True

    # Orphan check: every pair must serve at least one target.
    for i, p in enumerate(pairs):
        if not pair_to_targets[i]:
            raise FieldmapCoverageError(
                f"Fieldmap pair (run_index={p.run_index}, modality={p.modality!r}, "
                f"series_a={p.member_a.series_number}, "
                f"series_b={p.member_b.series_number}) has no assigned targets.",
                context={
                    "pair_index": i,
                    "run_index": p.run_index,
                    "modality": p.modality,
                    "series_a": p.member_a.series_number,
                    "series_b": p.member_b.series_number,
                },
            )

    guard_log["no_orphan_pairs"] = True

    # Passenger pass: assign SBRef/DWI_SBREF targets to geometry-compatible
    # pairs for B0FieldSource metadata, without affecting orphan coverage.
    for s, role in targets_sorted:
        modality = _SBREF_MODALITY.get(role)
        if modality is None:
            continue

        checks = [(i, _geometry_check(p.member_a, s)) for i, p in enumerate(pairs)]
        eligible = [i for i, result in checks if result.compatible]

        if not eligible:
            diagnostics = [
                {
                    "pair_index": i,
                    "run_index": pairs[i].run_index,
                    "modality": pairs[i].modality,
                    "series": [
                        pairs[i].member_a.series_number,
                        pairs[i].member_b.series_number,
                    ],
                    "failures": result.failures,
                }
                for i, result in checks
                if not result.compatible
            ]
            logger.warning(
                "SBRef series %d (%s) has no geometry-compatible fieldmap "
                "pair; B0FieldSource will not be assigned. "
                "Per-pair diagnostics: %s",
                s.series_number,
                s.description,
                diagnostics,
            )
            continue

        if len(eligible) == 1:
            chosen = eligible[0]
        else:
            def _time_dist(pair_idx: int) -> float:
                p = pairs[pair_idx]
                pair_dt = max(
                    p.member_a.acquisition_datetime,
                    p.member_b.acquisition_datetime,
                )
                return abs((s.acquisition_datetime - pair_dt).total_seconds())

            sorted_eligible = sorted(eligible, key=_time_dist)
            d0 = _time_dist(sorted_eligible[0])
            d1 = _time_dist(sorted_eligible[1])
            if d0 == d1:
                raise FieldmapCoverageError(
                    f"SBRef series {s.series_number} "
                    f"(description={s.description!r}) has a time-distance "
                    f"tie between eligible fieldmap pairs "
                    f"{sorted_eligible[0]} and {sorted_eligible[1]}; "
                    f"association is ambiguous.",
                    context={
                        "series_number": s.series_number,
                        "description": s.description,
                        "tied_pair_indices": [
                            sorted_eligible[0],
                            sorted_eligible[1],
                        ],
                    },
                )
            chosen = sorted_eligible[0]

        pair_to_targets[chosen].append(s)

    return Mapping(pairs=pairs, pair_to_targets=pair_to_targets)
