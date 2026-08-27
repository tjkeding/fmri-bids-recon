"""Entry point for the fmri-bids-recon pipeline.

Thin CLI wrapper around load_and_validate() and run(). All pipeline logic
lives in pipeline.py; this module handles argument parsing, logging setup,
and exit code mapping.

Logging uses field names, series numbers, counts, and derived labels only.
PHI values are never logged.
"""

from __future__ import annotations

import os
import re
import sys

_STRIPPED_PATHS: list[str] = []


def _sanitize_sys_path() -> None:
    version_pattern = re.compile(r'python(\d+\.\d+)')
    current = f"{sys.version_info.major}.{sys.version_info.minor}"
    foreign = [p for p in sys.path if (m := version_pattern.search(p)) and m.group(1) != current]
    for p in foreign:
        sys.path.remove(p)
        _STRIPPED_PATHS.append(p)
    if foreign and "PYTHONPATH" in os.environ:
        kept = [e for e in os.environ["PYTHONPATH"].split(os.pathsep)
                if not (m := version_pattern.search(e)) or m.group(1) == current]
        if kept:
            os.environ["PYTHONPATH"] = os.pathsep.join(kept)
        else:
            del os.environ["PYTHONPATH"]


_sanitize_sys_path()

import argparse
import logging
from pathlib import Path

from .config import load_and_validate
from .pipeline import run
from .errors import GuardError, ConfigError, ToolUnavailableError, ToolVersionError, BidsReconError
from . import __version__

logger = logging.getLogger(__name__)


def _setup_logging(log_file: Path | None = None) -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file is not None:
        file_handler = logging.FileHandler(str(log_file))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    root.setLevel(logging.DEBUG)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fmri-bids-recon",
        description="DICOM-to-BIDS reconstruction pipeline (v{})".format(__version__),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {}".format(__version__),
    )
    parser.add_argument(
        "config_positional",
        nargs="?",
        default=None,
        metavar="CONFIG",
        help="Path to the study configuration YAML file (positional form).",
    )
    parser.add_argument(
        "--config",
        dest="config_named",
        default=None,
        metavar="PATH",
        help="Path to the study configuration YAML file (named form).",
    )
    parser.add_argument(
        "--subject",
        default=None,
        metavar="ID",
        help="Process only this subject (filters the config subjects list).",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        type=Path,
        metavar="PATH",
        help="Write DEBUG-level logs to this file (INFO to console).",
    )
    parser.add_argument(
        "--strict-versions",
        action="store_true",
        default=False,
        help="Enforce exact version matches for Class A tool pins.",
    )
    return parser


def main() -> None:
    """DICOM-to-BIDS reconstruction pipeline entry point.

    Exit codes (orchestrator contract):
        0 = Success (proceed to next stage)
        1 = Pipeline invariant violation / GuardError (stop, do not retry)
        2 = Config / input validation error (stop, user must fix config)
        3 = Completed with warnings (proceed, flag for QC review)
        4 = External tool unavailable or version mismatch (stop, environment issue)
        5 = Model error (reserved; not raised by bids-recon)
    """
    parser = _build_parser()
    args = parser.parse_args()

    config_path = args.config_named or args.config_positional
    if config_path is None:
        parser.error("config path required (positional or --config)")

    _setup_logging(args.log_file)

    if _STRIPPED_PATHS:
        logger.info(
            'Sanitized sys.path: stripped %d foreign-version entr%s.',
            len(_STRIPPED_PATHS),
            'y' if len(_STRIPPED_PATHS) == 1 else 'ies',
        )

    strict = args.strict_versions or os.environ.get(
        "FMRI_BIDS_RECON_STRICT_VERSIONS", ""
    ).lower() in ("1", "true", "yes")

    try:
        config = load_and_validate(config_path, subject=args.subject)
        result = run(config, strict_versions=strict)
        has_high_warnings = any(
            w.get("severity") == "high" for w in result.warnings
        )
        if result.status == "warning" or has_high_warnings:
            sys.exit(3)
        sys.exit(0)
    except GuardError as exc:
        logger.error('Pipeline invariant violated: %s', exc, exc_info=True)
        sys.exit(1)
    except ToolUnavailableError as exc:
        logger.error('Tool unavailable, dataset is UNCHECKED: %s', exc)
        sys.exit(4)
    except ToolVersionError as exc:
        logger.error('Tool version mismatch: %s', exc)
        sys.exit(4)
    except ConfigError as exc:
        logger.error('Configuration error: %s', exc)
        sys.exit(2)
    except BidsReconError as exc:
        logger.critical('Pipeline error: %s', exc)
        sys.exit(1)
    except Exception as exc:
        logger.critical('Unexpected error: %s', exc, exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
