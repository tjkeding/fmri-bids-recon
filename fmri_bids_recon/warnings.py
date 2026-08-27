"""Structured warning framework for fmri-bids-recon.

Provides graded_warning() with a three-level severity taxonomy
(low/medium/high) aligned to the cross-pipeline contract under
the fmri-proc-orchestrator.

The accumulator is process-global and not thread-safe. Concurrent
in-process run() calls would interleave on the shared list, making
session status and exit code nondeterministic. The pipeline must be
parallelized at the process level (one run() per process, as in the
SLURM deployment model).
"""

from __future__ import annotations

import logging

SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"

_WARNING_ACCUMULATOR: list[dict] = []


def get_warnings() -> list[dict]:
    return list(_WARNING_ACCUMULATOR)


def clear_warnings() -> None:
    _WARNING_ACCUMULATOR.clear()


def graded_warning(
    logger: logging.Logger,
    severity: str,
    code: str,
    message: str,
    *,
    user_facing: bool = False,
) -> dict:
    level = logging.WARNING if user_facing else logging.INFO
    prefix = f"[{severity}:{code}]"
    full_message = f"{prefix} {message}"
    logger.log(level, full_message)
    result = {
        "severity": severity,
        "code": code,
        "message": message,
        "user_facing": user_facing,
    }
    _WARNING_ACCUMULATOR.append(result)
    return result
