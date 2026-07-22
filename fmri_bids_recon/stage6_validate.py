"""Stage 6: Validation layer for fmri-bids-recon.

Three-layer validation:
    Layer 1 (meta-guard): assert_guards_executed -- ensures every named guard
        ran during the pipeline; a guard that never ran is indistinguishable
        from a guard that does not work.
    Layer 2: run_bids_validator -- spec compliance via bids-validator-deno;
        returns list[SpecFinding] parsed from the validator's JSON output.
    Layer 3: generate_cubids_report -- Entity Sets / Parameter Groups review
        artifact via cubids; NON-BLOCKING, returns None if cubids is absent.
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from .errors import GuardError, ToolUnavailableError, SpecFinding

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Meta-guard registry
# ---------------------------------------------------------------------------

ALL_GUARD_NAMES: list[str] = [
    "dcm2niix_version_floor",
    "anat_suffix_physics",
    "opposite_pe_within_pair",
    "dir_label_pe_agreement",
    "fieldmap_pairing_unambiguous",
    "fieldmap_target_geometry_match",
    "pe_axis_target_match",
    "association_unambiguous",
    "no_orphan_pairs",
    "label_injectivity",
    "non_empty_labels",
    "no_label_drift",
    "no_rename_collision",
    "exact_volume_counts",
]


# ---------------------------------------------------------------------------
# Layer 1: meta-guard
# ---------------------------------------------------------------------------


def assert_guards_executed(guard_log: dict[str, bool]) -> None:
    """Verify that every named guard in ALL_GUARD_NAMES was executed.

    A guard is considered executed when its entry in *guard_log* is ``True``.
    A missing key or a ``False`` value both indicate that the guard did not
    complete successfully.

    Parameters
    ----------
    guard_log:
        Mapping of guard name to execution status (``True`` = ran and passed).

    Raises
    ------
    GuardError
        If one or more guards were not executed, listing all skipped guard
        names in the ``context`` dict under the key ``"skipped_guards"``.
    """
    skipped: list[str] = [
        name for name in ALL_GUARD_NAMES if not guard_log.get(name, False)
    ]
    if skipped:
        raise GuardError(
            f"Meta-guard failure: {len(skipped)} guard(s) were not executed: "
            + ", ".join(skipped),
            context={"skipped_guards": skipped},
        )


# ---------------------------------------------------------------------------
# Layer 2: bids-validator (spec compliance, BLOCKING)
# ---------------------------------------------------------------------------


def run_bids_validator(bids_root: Path) -> list[SpecFinding]:
    """Run the BIDS validator CLI against *bids_root* and return findings.

    Executes ``bids-validator-deno --json -o <tmpfile> <bids_root>`` as a
    subprocess. The return code is ignored entirely; output parsing drives
    all branching. On any tool-level failure (binary absent, no output file,
    unparseable JSON, missing ``'issues'`` key) a ``ToolUnavailableError`` is
    raised to signal that the dataset is UNCHECKED.

    Parameters
    ----------
    bids_root:
        Absolute path to the BIDS dataset root directory.

    Returns
    -------
    list[SpecFinding]
        One ``SpecFinding`` per issue record in the validator's JSON output.

    Raises
    ------
    ToolUnavailableError
        If the validator binary is absent, produces no output, outputs
        invalid JSON, or its output lacks the expected ``'issues'`` key.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmpfile_path = tmp.name
    tmp.close()
    try:
        try:
            result = subprocess.run(
                ["bids-validator-deno", "--json", "-o", tmpfile_path, str(bids_root)],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise ToolUnavailableError(
                "bids-validator-deno not found on PATH; dataset is UNCHECKED.",
                context={"error": str(exc)},
            ) from exc

        if not os.path.exists(tmpfile_path) or os.path.getsize(tmpfile_path) == 0:
            raise ToolUnavailableError(
                "bids-validator-deno produced no output file; dataset is UNCHECKED.",
                context={"stderr": result.stderr[-2000:]},
            )

        try:
            with open(tmpfile_path) as fh:
                parsed = json.load(fh)
        except json.JSONDecodeError:
            raise ToolUnavailableError(
                "bids-validator-deno output is not valid JSON; dataset is UNCHECKED.",
                context={"stderr": result.stderr[-2000:]},
            )

        if "issues" not in parsed:
            raise ToolUnavailableError(
                "bids-validator-deno output missing issues key; dataset is UNCHECKED.",
                context={"keys": list(parsed.keys())},
            )

        issues_block = parsed.get("issues")
        if not isinstance(issues_block, dict) or "issues" not in issues_block:
            raise ToolUnavailableError(
                "bids-validator-deno output has an unexpected 'issues' shape; dataset is UNCHECKED.",
                context={"issues_type": type(issues_block).__name__})
        issues_list = issues_block["issues"]
        code_messages = issues_block.get("codeMessages", {})

        return [
            SpecFinding(
                severity=rec.get("severity", ""),
                code=rec.get("code", ""),
                location=rec.get("location", ""),
                message=code_messages.get(rec.get("code", ""), rec.get("issueMessage", "")),
            )
            for rec in issues_list
        ]
    finally:
        try:
            os.unlink(tmpfile_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Layer 3: cubids report (NON-BLOCKING, review artifact)
# ---------------------------------------------------------------------------


def generate_cubids_report(bids_root: Path, output_dir: Path) -> Path | None:
    """Generate a cubids Entity Sets / Parameter Groups report.

    Runs ``cubids group <bids_root>`` (or ``cubids-group <bids_root>``) to
    produce grouping metadata in *output_dir*.  This is a review artifact
    generated after each batch and is explicitly NON-BLOCKING: if cubids is
    not installed or the command fails for any reason, a warning is logged and
    ``None`` is returned.  Callers must not rely on the return value for
    pipeline gating decisions.

    Parameters
    ----------
    bids_root:
        Absolute path to the BIDS dataset root directory.
    output_dir:
        Directory where cubids will write its output files.

    Returns
    -------
    Path or None
        Path to *output_dir* on success; ``None`` if cubids is unavailable or
        the command exits with an error.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Try the subcommand form first (cubids >= 1.0), then the hyphenated form.
    for cmd in (
        ["cubids", "group", str(bids_root), str(output_dir)],
        ["cubids-group", str(bids_root), str(output_dir)],
    ):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            # Binary not on PATH; try next variant.
            continue

        if result.returncode == 0:
            return output_dir

        logger.warning(
            "cubids group exited with code %d; report not generated. "
            "stdout: %s  stderr: %s",
            result.returncode,
            result.stdout.strip(),
            result.stderr.strip(),
        )
        return None

    logger.warning(
        "cubids is not available on this system; skipping Entity Sets / "
        "Parameter Groups report for %s.",
        bids_root,
    )
    return None
