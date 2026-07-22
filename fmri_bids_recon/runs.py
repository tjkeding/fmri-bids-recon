"""Run-count validation and run-index assignment for fmri-bids-recon.

Validates BOLD volume counts against the task registry and assigns
temporal run indices to surviving BOLD series.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .sidecar import Series
from .config import TaskRegistryEntry
from .errors import ReviewFlag


@dataclass
class Excluded:
    """Record of a BOLD series excluded due to a volume-count mismatch.

    Parameters
    ----------
    series : Series
        The excluded series object.
    task_label : str
        BIDS task label assigned to this series.
    observed_volumes : int
        Actual n_volumes found in the NIfTI file.
    expected_volumes : int
        Volume count required by the registry or within-session mode.
    """

    series: Series
    task_label: str
    observed_volumes: int
    expected_volumes: int


def check_volume_counts(
    bolds: list[tuple[Series, str]],
    registry: dict[str, TaskRegistryEntry],
) -> tuple[list[tuple[Series, str]], list[Excluded], dict[str, TaskRegistryEntry], list[ReviewFlag]]:
    """Validate BOLD volume counts against the task registry.

    For each task label, looks up expected_volumes from the registry via the
    series' description key.  Series with a known expected count undergo
    exact-match enforcement.  Series whose description is absent from the
    registry (or whose registry entry carries expected_volumes=None) are
    handled by within-session reasoning: if two or more runs of the task are
    present, the within-session mode establishes the expected count and
    outliers are excluded; if exactly one run is present, it is accepted,
    registered, and flagged for review.

    Parameters
    ----------
    bolds : list[tuple[Series, str]]
        Pairs of (series, task_label) for each BOLD candidate.
    registry : dict[str, TaskRegistryEntry]
        Mapping of SeriesDescription -> TaskRegistryEntry for known tasks.

    Returns
    -------
    surviving_bolds : list[tuple[Series, str]]
        BOLD pairs that passed volume-count validation.
    excluded_list : list[Excluded]
        Series excluded due to volume-count mismatches.
    new_registry_entries : dict[str, TaskRegistryEntry]
        SeriesDescription -> TaskRegistryEntry for tasks whose expected_volumes
        were established this session.
    review_flags : list[ReviewFlag]
        Non-blocking advisory flags for single-run first-observation tasks.
    """
    surviving_bolds: list[tuple[Series, str]] = []
    excluded_list: list[Excluded] = []
    new_registry_entries: dict[str, TaskRegistryEntry] = {}
    review_flags: list[ReviewFlag] = []

    # Classify each BOLD series as known (expected_volumes set in registry)
    # or unknown (no registry entry, or expected_volumes is None).
    known: list[tuple[Series, str]] = []
    unknown: list[tuple[Series, str]] = []
    for series, task_label in bolds:
        entry = registry.get(series.description)
        if entry is not None and entry.expected_volumes is not None:
            known.append((series, task_label))
        else:
            unknown.append((series, task_label))

    # Known series: exact-match enforcement, no threshold.
    for series, task_label in known:
        expected: int = registry[series.description].expected_volumes  # type: ignore[assignment]
        if series.n_volumes == expected:
            surviving_bolds.append((series, task_label))
        else:
            excluded_list.append(
                Excluded(
                    series=series,
                    task_label=task_label,
                    observed_volumes=series.n_volumes,
                    expected_volumes=expected,
                )
            )

    # Unknown series: group by task_label for within-session reasoning.
    unknown_by_task: dict[str, list[tuple[Series, str]]] = {}
    for series, task_label in unknown:
        unknown_by_task.setdefault(task_label, []).append((series, task_label))

    for task_label, group in unknown_by_task.items():
        n_runs = len(group)

        if n_runs >= 2:
            # Within-session mode establishes the expected count.
            counts = [s.n_volumes for s, _ in group]
            counter = Counter(counts)
            top = counter.most_common()
            if len(top) > 1 and top[0][1] == top[1][1]:
                review_flags.append(
                    ReviewFlag(
                        f"Task {task_label!r}: no unique modal volume count among "
                        f"{sorted(set(counts))}; no registry entry created, all runs "
                        f"retained pending review.",
                        {"code": "ambiguous_volume_mode"},
                    )
                )
                # do NOT create a new_registry_entries entry for this task; retain all bolds
                for series, tlabel in group:
                    surviving_bolds.append((series, tlabel))
            else:
                mode_count: int = top[0][0]

                for series, tlabel in group:
                    if series.n_volumes == mode_count:
                        surviving_bolds.append((series, tlabel))
                        # Register expected_volumes keyed by series description;
                        # first surviving description in the group sets the entry.
                        if series.description not in new_registry_entries:
                            prior = registry.get(series.description)
                            first_seen = (
                                prior.first_seen
                                if prior is not None
                                else series.acquisition_datetime.date().isoformat()
                            )
                            new_registry_entries[series.description] = TaskRegistryEntry(
                                label=tlabel,
                                expected_volumes=mode_count,
                                first_seen=first_seen,
                            )
                    else:
                        excluded_list.append(
                            Excluded(
                                series=series,
                                task_label=tlabel,
                                observed_volumes=series.n_volumes,
                                expected_volumes=mode_count,
                            )
                        )

        else:
            # Exactly 1 run: accept, register, and flag for review.
            series, tlabel = group[0]
            surviving_bolds.append((series, tlabel))

            prior = registry.get(series.description)
            first_seen = (
                prior.first_seen
                if prior is not None
                else series.acquisition_datetime.date().isoformat()
            )
            new_registry_entries[series.description] = TaskRegistryEntry(
                label=tlabel,
                expected_volumes=series.n_volumes,
                first_seen=first_seen,
            )

            review_flags.append(
                ReviewFlag(
                    f"Single-run first observation for task '{tlabel}' "
                    f"(series {series.series_number}, "
                    f"description '{series.description}'): "
                    f"n_volumes={series.n_volumes} registered without "
                    f"within-session corroboration.",
                    {
                        "task_label": tlabel,
                        "series_number": series.series_number,
                        "description": series.description,
                        "n_volumes": series.n_volumes,
                    },
                )
            )

    return surviving_bolds, excluded_list, new_registry_entries, review_flags


def assign_run_indices(
    surviving: list[tuple[Series, str]],
) -> dict[int, int]:
    """Assign 1-based run indices to surviving BOLD series.

    Groups series by task_label and assigns run indices (1, 2, ...) in
    acquisition_datetime order within each group.  Run indices are always
    emitted, including for singleton tasks.

    Parameters
    ----------
    surviving : list[tuple[Series, str]]
        Pairs of (series, task_label) that passed volume-count validation.

    Returns
    -------
    dict[int, int]
        Mapping of series_number -> run index (1-based).
    """
    task_groups: dict[str, list[Series]] = {}
    for series, task_label in surviving:
        task_groups.setdefault(task_label, []).append(series)

    run_map: dict[int, int] = {}
    for task_label, series_list in task_groups.items():
        ordered = sorted(series_list, key=lambda s: s.acquisition_datetime)
        for run_idx, series in enumerate(ordered, start=1):
            run_map[series.series_number] = run_idx

    return run_map
