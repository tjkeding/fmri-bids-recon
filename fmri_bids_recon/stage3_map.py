"""Stage 3: fieldmap grouping and coverage mapping for fmri-bids-recon.

Groups fieldmaps into geometry-compatible units (paired or single mode) and
assigns each unit to the functional or diffusion targets it covers, using a
geometry-primary assignment policy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .sidecar import Series
from .warnings import graded_warning, SEVERITY_HIGH, SEVERITY_MEDIUM
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
class FieldmapUnit:
    """A validated fieldmap unit: paired (two opposite-PE series) or single.

    Parameters
    ----------
    members : list[Series]
        1 member (single mode) or 2 members (paired mode, sorted by
        acquisition_datetime).
    modality : str
        ``'func'`` (FMAP_FUNC) or ``'dwi'`` (FMAP_DWI).
    mode : str
        ``'paired'`` or ``'single'``.
    run_index : int
        1-based index within the same modality's units.
    dir_labels : list[str]
        1 or 2 voxel-space PE direction labels (e.g. ``['j', 'j-']``).
        Anatomical conversion via PE_DIRECTION_TO_LABEL at assembly time.
    """

    members: list[Series]
    modality: str
    mode: str
    run_index: int
    dir_labels: list[str]


@dataclass
class Mapping:
    """Complete fieldmap-to-target assignment for all units.

    Parameters
    ----------
    units : list[FieldmapUnit]
        All validated fieldmap units.
    unit_to_targets : dict[int, list[Series]]
        Maps each unit's position in ``units`` to the list of target series
        it covers.
    unpaired_fmaps : list[Series]
        Fieldmap series that could not be paired (absent PE, odd-count
        remainder). Routed to sourcedata/unpaired_fmap by stage 4.
    """

    units: list[FieldmapUnit]
    unit_to_targets: dict[int, list[Series]]
    unpaired_fmaps: list[Series] = field(default_factory=list)
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


@dataclass
class GREFieldmapSet:
    """A GRE (gradient-echo) fieldmap set: phase series with magnitude companions.

    Parameters
    ----------
    phase_series : list[Series]
        1 phase series (BIDS Case 1 or 3) or 2 phase series (Case 2).
    magnitude_series : list[Series]
        Magnitude companion series, geometry-matched to phase_series.
    bids_case : int
        1, 2, 3, or 0 (indeterminate).
    run_index : int
        1-based index among GRE fieldmap sets.
    targets : list[Series]
        Assigned BOLD/DWI target series, populated by map_gre_fieldmaps().
    """

    phase_series: list[Series]
    magnitude_series: list[Series]
    bids_case: int
    run_index: int
    targets: list[Series] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Geometry helper
# ---------------------------------------------------------------------------


def _geometry_check(a: Series, b: Series, *, check_pe_axis: bool = True) -> GeometryResult:
    """Return a GeometryResult describing geometry compatibility between series a and b.

    Checks image_position (within GEOMETRY_POSITION_TOL_MM per axis), the
    3x3 rotation block of the affine (within GEOMETRY_ORIENTATION_TOL),
    voxel_sizes (within GEOMETRY_VOXEL_TOL_MM), exact matrix equality, and
    (when check_pe_axis is True) identical non-None pe_axis.  Returns a
    GeometryResult with compatible=False immediately if any of image_position,
    affine, voxel_sizes, or (when checked) pe_axis is None on either series,
    reporting the None field names in failures.

    Parameters
    ----------
    a : Series
        First series.
    b : Series
        Second series.
    check_pe_axis : bool
        When False, the pe_axis criterion (and its None-guard) is skipped.
        Used for GRE magnitude rescue (CR F8), where magnitude reconstructions
        frequently lack a populated PhaseEncodingDirection despite sharing
        position, orientation, voxel size, and matrix with their phase
        companion (same underlying k-space acquisition).

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
            *([("a.pe_axis", a.pe_axis)] if check_pe_axis else []),
            ("b.image_position", b.image_position),
            ("b.affine", b.affine),
            ("b.voxel_sizes", b.voxel_sizes),
            *([("b.pe_axis", b.pe_axis)] if check_pe_axis else []),
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
    if check_pe_axis and a.pe_axis != b.pe_axis:
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


def group_fieldmaps(
    fmaps: list[tuple[Series, Role]],
    ordered: list[Series],
    guard_log: dict,
) -> tuple[list[FieldmapUnit], list[Series]]:
    """Group EPI fieldmaps into geometry-compatible units and validate phase-encoding.

    Partitions fieldmaps into geometry groups via the transitive closure of
    :func:`_geometry_check` (union-find). Series with absent
    PhaseEncodingDirection are routed to the unpaired list with a high-severity
    graded_warning. Within each geometry group, series are split by modality
    (func/dwi) and paired consecutively by acquisition_datetime. Odd-count
    modality sub-groups pair as many as possible and route the remainder to
    unpaired_fmaps with a high-severity graded_warning.

    Parameters
    ----------
    fmaps : list[tuple[Series, Role]]
        Fieldmap series paired with their classification roles (FMAP_FUNC or
        FMAP_DWI).
    ordered : list[Series]
        All series sorted by acquisition_datetime, as returned by
        :func:`order_series`.
    guard_log : dict
        Mutable dict updated with validation gate outcomes:
        ``opposite_pe_within_pair``, ``dir_label_pe_agreement``,
        ``fieldmap_pairing_unambiguous``.

    Returns
    -------
    tuple[list[FieldmapUnit], list[Series]]
        ``(units, unpaired_fmaps)``. Units are validated fieldmap units in
        geometry-group then modality (func, dwi) order. unpaired_fmaps are
        series that could not be paired (absent PE direction, odd-count
        remainder).

    Raises
    ------
    PhaseEncodingError
        If consecutive pair members do not carry opposite PE directions, or if
        a series description token (_PA or _AP) disagrees with the
        physics-derived BIDS label.
    """
    if not fmaps:
        guard_log["fieldmap_pairing_unambiguous"] = True
        return [], []

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

    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = _find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(i)

    # Step 2: Absent-PE detection. Route series with no PhaseEncodingDirection
    # to unpaired_fmaps before the modality split.
    unpaired_fmaps: list[Series] = []
    filtered_groups: dict[int, list[int]] = {}
    for root, indices in groups.items():
        filtered: list[int] = []
        for idx in indices:
            s, _role = fmaps[idx]
            if s.phase_encoding_direction is None:
                if s.phase_encoding_axis is not None:
                    graded_warning(
                        logger, SEVERITY_HIGH, "ABSENT_PE_DIRECTION",
                        f"Series {s.series_number}: PhaseEncodingDirection absent "
                        f"(PhaseEncodingAxis={s.phase_encoding_axis!r} present "
                        f"without polarity). Cannot verify opposite-PE pairing. "
                        f"Route to sourcedata/unpaired_fmap. To enable fieldmap "
                        f"correction, add PhaseEncodingDirection to the sidecar "
                        f"manually or use a controlled-vocabulary protocol naming "
                        f"convention.",
                    )
                else:
                    graded_warning(
                        logger, SEVERITY_HIGH, "ABSENT_PE_DIRECTION",
                        f"Series {s.series_number}: PhaseEncodingDirection absent. "
                        f"Cannot verify opposite-PE pairing. Route to "
                        f"sourcedata/unpaired_fmap.",
                    )
                unpaired_fmaps.append(s)
            else:
                filtered.append(idx)
        if filtered:
            filtered_groups[root] = filtered

    # Step 3: Within each geometry group, split by modality and group into units.
    run_index_by_modality: dict[str, int] = {"func": 1, "dwi": 1}
    units: list[FieldmapUnit] = []

    for _root, indices in filtered_groups.items():
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

            if len(members) % 2 != 0:
                graded_warning(
                    logger, SEVERITY_HIGH, "ODD_FIELDMAP_COUNT",
                    f"Geometry group contains {len(members)} {modality} fieldmap "
                    f"series (series: {[s.series_number for s in members]}). "
                    f"Cannot form balanced opposite-PE pairs. Paired fieldmaps "
                    f"assigned where possible; remainder routed to "
                    f"sourcedata/unpaired_fmap.",
                )
                unpaired_fmaps.append(members[-1])
                members = members[:-1]

            for k in range(len(members) - 1):
                if members[k].acquisition_datetime == members[k + 1].acquisition_datetime:
                    raise PhaseEncodingError(
                        f"Fieldmap series {members[k].series_number} and "
                        f"{members[k + 1].series_number} share identical "
                        f"AcquisitionDateTime "
                        f"({members[k].acquisition_datetime}); "
                        f"consecutive-pairing order is arbitrary.",
                        context={
                            "modality": modality,
                            "series_a": members[k].series_number,
                            "series_b": members[k + 1].series_number,
                            "acquisition_datetime": str(
                                members[k].acquisition_datetime
                            ),
                        },
                    )

            for i in range(0, len(members), 2):
                a = members[i]
                b = members[i + 1]

                ped_a = a.phase_encoding_direction
                ped_b = b.phase_encoding_direction

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

                for s_check, ped_check in ((a, ped_a), (b, ped_b)):
                    desc_upper = s_check.description.upper()
                    for token in ("_PA", "_AP"):
                        if token in desc_upper:
                            expected_dir = token.lstrip("_")
                            physics_label = PE_DIRECTION_TO_LABEL[ped_check]
                            if physics_label != expected_dir:
                                raise PhaseEncodingError(
                                    f"Series {s_check.series_number}: description "
                                    f"token '{token}' disagrees with physics-derived "
                                    f"PE label '{physics_label}' "
                                    f"(phase_encoding_direction="
                                    f"{s_check.phase_encoding_direction!r}).",
                                    context={
                                        "series_number": s_check.series_number,
                                        "description": s_check.description,
                                        "name_token": token,
                                        "physics_label": physics_label,
                                        "phase_encoding_direction": (
                                            s_check.phase_encoding_direction
                                        ),
                                    },
                                )

                guard_log["dir_label_pe_agreement"] = True

                units.append(
                    FieldmapUnit(
                        members=[a, b],
                        modality=modality,
                        mode="paired",
                        run_index=run_index_by_modality[modality],
                        dir_labels=[ped_a, ped_b],
                    )
                )
                run_index_by_modality[modality] += 1

    guard_log["fieldmap_pairing_unambiguous"] = True
    return units, unpaired_fmaps


def _select_unit(
    s: Series,
    units: list[FieldmapUnit],
    eligible: list[int],
    kind: str,
) -> int:
    """Select the nearest-in-time eligible unit, raising on a tie."""
    if len(eligible) == 1:
        return eligible[0]

    def _time_dist(unit_idx: int) -> float:
        u = units[unit_idx]
        unit_dt = max(m.acquisition_datetime for m in u.members)
        return abs((s.acquisition_datetime - unit_dt).total_seconds())

    sorted_eligible = sorted(eligible, key=_time_dist)
    d0 = _time_dist(sorted_eligible[0])
    d1 = _time_dist(sorted_eligible[1])
    if d0 == d1:
        raise FieldmapCoverageError(
            f"{kind} {s.series_number} (description={s.description!r}) has "
            f"a time-distance tie between eligible fieldmap units "
            f"{sorted_eligible[0]} and {sorted_eligible[1]}; "
            f"association is ambiguous.",
            context={
                "series_number": s.series_number,
                "description": s.description,
                "tied_unit_indices": [sorted_eligible[0], sorted_eligible[1]],
            },
        )
    return sorted_eligible[0]


def map_fieldmaps(
    units: list[FieldmapUnit],
    targets: list[tuple[Series, Role]],
    ordered: list[Series],
    guard_log: dict,
    unpaired_fmaps: list[Series] | None = None,
) -> Mapping:
    """Assign each target series to a geometry-compatible fieldmap unit.

    For each target (iterated in ascending acquisition_datetime order): the
    eligible set is all units whose first member passes _geometry_check against
    the target (geometry compatibility implies matching pe_axis).  If exactly
    one eligible unit exists it is chosen directly; if multiple exist, the unit
    whose latest member's acquisition_datetime is nearest in time to the target
    is chosen (a tie in time distance raises :exc:`FieldmapCoverageError`).
    After assignment, every unit must serve at least one target (orphan check).

    Parameters
    ----------
    units : list[FieldmapUnit]
        Validated fieldmap units from :func:`group_fieldmaps`.
    targets : list[tuple[Series, Role]]
        Target series (BOLD or DWI) with their classification roles.
    ordered : list[Series]
        All series sorted by acquisition_datetime, as returned by
        :func:`order_series`.
    guard_log : dict
        Mutable dict updated with validation gate outcomes:
        ``fieldmap_target_geometry_match``, ``pe_axis_target_match``,
        ``association_unambiguous``, ``no_orphan_pairs``.
    unpaired_fmaps : list[Series] or None
        Fieldmap series routed to sourcedata by :func:`group_fieldmaps`.
        Passed through to the returned Mapping.

    Returns
    -------
    Mapping
        Assignment indexed by position in ``units``.  ``bids_relative_paths``
        uses its default_factory and is populated later by stage 4.

    Raises
    ------
    FieldmapCoverageError
        If a time-distance tie exists among multiple eligible units.
    """
    _ROLE_TO_MODALITY: dict[Role, str] = {
        Role.BOLD: "func",
        Role.DWI: "dwi",
    }
    _SBREF_MODALITY: dict[Role, str] = {Role.SBREF: "func", Role.DWI_SBREF: "dwi"}

    unit_to_targets: dict[int, list[Series]] = {i: [] for i in range(len(units))}

    targets_sorted = sorted(targets, key=lambda x: x[0].acquisition_datetime)

    for s, role in targets_sorted:
        modality = _ROLE_TO_MODALITY.get(role)
        if modality is None:
            continue

        checks = [(i, _geometry_check(u.members[0], s)) for i, u in enumerate(units)]
        eligible = [i for i, result in checks if result.compatible]

        guard_log["fieldmap_target_geometry_match"] = True
        guard_log["pe_axis_target_match"] = True

        if not eligible:
            candidate_units = [
                {
                    "unit_index": i,
                    "run_index": units[i].run_index,
                    "modality": units[i].modality,
                    "series": [m.series_number for m in units[i].members],
                    "failures": result.failures,
                }
                for i, result in checks
                if not result.compatible
            ]
            graded_warning(
                logger, "high", "FIELDMAP_COVERAGE_GAP",
                f"Series {s.series_number} (description={s.description!r}, "
                f"modality={modality!r}) has no geometry-compatible fieldmap unit. "
                f"Candidate diagnostics: {candidate_units}",
            )
            continue

        chosen = _select_unit(s, units, eligible, "Series")

        unit_to_targets[chosen].append(s)

    guard_log["association_unambiguous"] = True

    for i, u in enumerate(units):
        if not unit_to_targets[i]:
            graded_warning(
                logger, "medium", "ORPHAN_FIELDMAP_UNIT",
                f"Fieldmap unit (run_index={u.run_index}, modality={u.modality!r}, "
                f"series={[m.series_number for m in u.members]}) has no assigned "
                f"targets.",
            )

    guard_log["no_orphan_pairs"] = True

    for s, role in targets_sorted:
        modality = _SBREF_MODALITY.get(role)
        if modality is None:
            continue

        checks = [(i, _geometry_check(u.members[0], s)) for i, u in enumerate(units)]
        eligible = [i for i, result in checks if result.compatible]

        if not eligible:
            diagnostics = [
                {
                    "unit_index": i,
                    "run_index": units[i].run_index,
                    "modality": units[i].modality,
                    "series": [m.series_number for m in units[i].members],
                    "failures": result.failures,
                }
                for i, result in checks
                if not result.compatible
            ]
            logger.warning(
                "SBRef series %d (%s) has no geometry-compatible fieldmap "
                "unit; B0FieldSource will not be assigned. "
                "Per-unit diagnostics: %s",
                s.series_number,
                s.description,
                diagnostics,
            )
            continue

        chosen = _select_unit(s, units, eligible, "SBRef series")

        unit_to_targets[chosen].append(s)

    return Mapping(
        units=units,
        unit_to_targets=unit_to_targets,
        unpaired_fmaps=unpaired_fmaps if unpaired_fmaps is not None else [],
    )


# ---------------------------------------------------------------------------
# GRE fieldmap grouping
# ---------------------------------------------------------------------------


def group_gre_fieldmaps(
    classified: dict[int, Role],
    series_map: dict[int, Series],
    guard_log: dict,
) -> tuple[list[GREFieldmapSet], list[Series]]:
    """Group GRE (gradient-echo) fieldmap phase series with magnitude companions.

    For each FMAP_GRE_PHASE series, finds geometry-compatible magnitude
    companions among UNCLASSIFIED series (geometry-primary magnitude rescue,
    CR F8), then clusters phase series that share geometry (a BIDS Case 2 set
    is acquired as two phase outputs from the same underlying acquisition and
    is therefore geometrically identical) into fieldmap sets, and determines
    the explicit BIDS case (1, 2, 3, or 0/indeterminate; CR F5) for each set.

    Parameters
    ----------
    classified : dict[int, Role]
        Mapping of series_number to Role, as produced by
        :func:`~fmri_bids_recon.stage2_classify.classify`. Mutated in place:
        magnitude series matched during rescue are reclassified from
        UNCLASSIFIED to FMAP_GRE_MAG.
    series_map : dict[int, Series]
        Mapping of series_number to Series for all series in the session.
    guard_log : dict
        Mutable dict updated with validation gate outcomes (unused by this
        function currently; accepted for interface symmetry with
        :func:`group_fieldmaps`).

    Returns
    -------
    tuple[list[GREFieldmapSet], list[Series]]
        ``(gre_sets, unassociated_magnitudes)``. unassociated_magnitudes are
        GRE-candidate magnitude series (GR in scanning_sequence, PHASE not in
        image_type, still UNCLASSIFIED) that matched no phase series.
    """
    phase_series_all = [
        series_map[sn] for sn, role in classified.items() if role == Role.FMAP_GRE_PHASE
    ]
    if not phase_series_all:
        return [], []

    def _magnitude_candidates() -> list[Series]:
        return [
            s
            for sn, s in series_map.items()
            if classified.get(sn) == Role.UNCLASSIFIED
            and "GR" in s.scanning_sequence
            and "PHASE" not in s.image_type
        ]

    # Step 1: geometry-primary magnitude rescue, per phase series.
    rescued_magnitudes: dict[int, list[Series]] = {}
    matched_magnitude_sns: set[int] = set()

    for phase in phase_series_all:
        candidates = _magnitude_candidates()
        geometry_matches = [
            c for c in candidates
            if _geometry_check(phase, c, check_pe_axis=False).compatible
        ]

        if not geometry_matches:
            graded_warning(
                logger, SEVERITY_MEDIUM, "GRE_MAGNITUDE_MISSING",
                f"GRE fieldmap phase series {phase.series_number} "
                f"(description={phase.description!r}) has no geometry-compatible "
                f"magnitude companion.",
            )
            rescued_magnitudes[phase.series_number] = []
            continue

        if len(geometry_matches) > 2:
            geometry_matches = sorted(
                geometry_matches,
                key=lambda c: abs(c.series_number - phase.series_number),
            )[:2]

        rescued_magnitudes[phase.series_number] = geometry_matches
        for c in geometry_matches:
            classified[c.series_number] = Role.FMAP_GRE_MAG
            matched_magnitude_sns.add(c.series_number)

    # Step 2: cluster phase series sharing geometry into fieldmap sets
    # (union-find, same transitive-closure algorithm as group_fieldmaps).
    n = len(phase_series_all)
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

    for i in range(n):
        for j in range(i + 1, n):
            if _geometry_check(
                phase_series_all[i], phase_series_all[j], check_pe_axis=False
            ).compatible:
                _union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        root = _find(i)
        clusters.setdefault(root, []).append(i)

    # Step 3: explicit BIDS case determination per cluster.
    gre_sets: list[GREFieldmapSet] = []
    run_index = 1
    for _root, indices in clusters.items():
        cluster_phases = sorted(
            (phase_series_all[i] for i in indices),
            key=lambda s: s.acquisition_datetime,
        )

        cluster_magnitudes: list[Series] = []
        seen_mag_sns: set[int] = set()
        for p in cluster_phases:
            for m in rescued_magnitudes.get(p.series_number, []):
                if m.series_number not in seen_mag_sns:
                    cluster_magnitudes.append(m)
                    seen_mag_sns.add(m.series_number)

        bids_case = 0
        if len(cluster_phases) == 2:
            te0 = cluster_phases[0].echo_time
            te1 = cluster_phases[1].echo_time
            if te0 is not None and te1 is not None and te0 != te1:
                bids_case = 2
        elif len(cluster_phases) == 1:
            p = cluster_phases[0]
            if p.raw.get("EchoTime1") is not None and p.raw.get("EchoTime2") is not None:
                bids_case = 1
            elif p.raw.get("Units") == "Hz":
                bids_case = 3

        if bids_case == 0:
            graded_warning(
                logger, SEVERITY_HIGH, "GRE_CASE_INDETERMINATE",
                f"GRE fieldmap set (phase series "
                f"{[s.series_number for s in cluster_phases]}) cannot be "
                f"classified as BIDS Case 1/2/3. Missing: EchoTime1+EchoTime2 "
                f"(Case 1), multiple phase outputs with distinct EchoTime "
                f"(Case 2), or Units='Hz' (Case 3). Routing to sourcedata.",
            )

        gre_sets.append(
            GREFieldmapSet(
                phase_series=cluster_phases,
                magnitude_series=cluster_magnitudes,
                bids_case=bids_case,
                run_index=run_index,
            )
        )
        run_index += 1

    unassociated_magnitudes = [
        c for c in _magnitude_candidates() if c.series_number not in matched_magnitude_sns
    ]

    return gre_sets, unassociated_magnitudes


def _relaxed_geometry_check(a: Series, b: Series) -> GeometryResult:
    """Relaxed geometry compatibility for GRE-to-EPI target association.

    Checks image_position and orientation only (same tolerances as
    :func:`_geometry_check`). Voxel sizes and matrix are NOT checked, since
    GRE fieldmap resolution commonly differs from the EPI target's resolution.
    pe_axis is NOT checked, since FUGUE-based GRE fieldmap correction is
    phase-encoding-direction-agnostic.

    Parameters
    ----------
    a : Series
        First series (typically a GRE fieldmap set's reference phase series).
    b : Series
        Second series (typically a BOLD or DWI target).

    Returns
    -------
    GeometryResult
        compatible=True when position and orientation are within tolerance;
        compatible=False otherwise, with failures listing each criterion not
        met.
    """
    none_fields = [
        name
        for name, v in [
            ("a.image_position", a.image_position),
            ("a.affine", a.affine),
            ("b.image_position", b.image_position),
            ("b.affine", b.affine),
        ]
        if v is None
    ]
    if none_fields:
        return GeometryResult(
            compatible=False,
            failures=[f"None geometry field(s): {', '.join(none_fields)}"],
        )

    failures: list[str] = []

    for idx, (va, vb) in enumerate(zip(a.image_position, b.image_position)):  # type: ignore[arg-type]
        delta = abs(va - vb)
        if delta > GEOMETRY_POSITION_TOL_MM:
            failures.append(
                f"image_position[{idx}]: delta={delta:.3f} mm > tol={GEOMETRY_POSITION_TOL_MM:.3f} mm"
            )

    for row in range(3):
        for col in range(3):
            delta = abs(a.affine[row][col] - b.affine[row][col])  # type: ignore[index]
            if delta > GEOMETRY_ORIENTATION_TOL:
                failures.append(
                    f"affine[{row}][{col}]: delta={delta:.6f} > tol={GEOMETRY_ORIENTATION_TOL:.6f}"
                )

    return GeometryResult(compatible=len(failures) == 0, failures=failures)


def map_gre_fieldmaps(
    gre_sets: list[GREFieldmapSet],
    targets: list[tuple[Series, Role]],
    guard_log: dict,
) -> list[GREFieldmapSet]:
    """Assign each BOLD/DWI target to a geometry-compatible GRE fieldmap set.

    For each target, the eligible set is all determinate (bids_case != 0)
    GRE fieldmap sets whose first phase series passes
    :func:`_relaxed_geometry_check` against the target. If exactly one
    eligible set exists it is chosen directly; if multiple exist, the set
    whose latest phase series' acquisition_datetime is nearest in time to the
    target is chosen (a tie in time distance raises
    :exc:`FieldmapCoverageError`). Indeterminate sets (bids_case=0) are
    excluded from association and route to sourcedata via stage 4.

    Parameters
    ----------
    gre_sets : list[GREFieldmapSet]
        GRE fieldmap sets from :func:`group_gre_fieldmaps`.
    targets : list[tuple[Series, Role]]
        Target series (BOLD or DWI) with their classification roles.
    guard_log : dict
        Mutable dict updated with validation gate outcomes (unused by this
        function currently; accepted for interface symmetry with
        :func:`map_fieldmaps`).

    Returns
    -------
    list[GREFieldmapSet]
        The same gre_sets list, with each set's ``targets`` field populated.

    Raises
    ------
    FieldmapCoverageError
        If a time-distance tie exists among multiple eligible sets for a
        given target.
    """
    _ROLE_TO_MODALITY: dict[Role, str] = {
        Role.BOLD: "func",
        Role.DWI: "dwi",
    }

    eligible_sets = [(i, gs) for i, gs in enumerate(gre_sets) if gs.bids_case != 0]

    targets_sorted = sorted(targets, key=lambda x: x[0].acquisition_datetime)

    for s, role in targets_sorted:
        if role not in _ROLE_TO_MODALITY:
            continue

        checks = [
            (i, _relaxed_geometry_check(gs.phase_series[0], s))
            for i, gs in eligible_sets
        ]
        matches = [i for i, result in checks if result.compatible]

        if not matches:
            continue

        if len(matches) == 1:
            chosen = matches[0]
        else:
            def _time_dist(idx: int) -> float:
                gs = gre_sets[idx]
                set_dt = max(m.acquisition_datetime for m in gs.phase_series)
                return abs((s.acquisition_datetime - set_dt).total_seconds())

            sorted_matches = sorted(matches, key=_time_dist)
            d0 = _time_dist(sorted_matches[0])
            d1 = _time_dist(sorted_matches[1])
            if d0 == d1:
                raise FieldmapCoverageError(
                    f"Series {s.series_number} (description={s.description!r}) has "
                    f"a time-distance tie between eligible GRE fieldmap sets "
                    f"{sorted_matches[0]} and {sorted_matches[1]}; association is "
                    f"ambiguous.",
                    context={
                        "series_number": s.series_number,
                        "description": s.description,
                        "tied_set_indices": [sorted_matches[0], sorted_matches[1]],
                    },
                )
            chosen = sorted_matches[0]

        gre_sets[chosen].targets.append(s)

    return gre_sets
