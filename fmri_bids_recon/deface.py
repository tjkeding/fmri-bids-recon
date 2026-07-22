"""Defacing utilities for fmri-bids-recon.

Provides deface(), an opt-in publishing step that emits defaced anatomicals
to derivatives/defaced/ under the BIDS root. The analysis anat/ directories
are never modified.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from .config import StudyConfig

logger = logging.getLogger(__name__)


def deface(config: StudyConfig, tool: str = "pydeface") -> list[Path]:
    """Emit defaced anatomicals to derivatives/defaced/ under the BIDS root.

    This is an opt-in publishing step and is NOT part of the analysis path.
    Files in anat/ are never modified; all output is written to a separate
    derivatives tree.

    Parameters
    ----------
    config : StudyConfig
        Loaded study configuration providing bids_root and participants.
    tool : str, optional
        Defacing tool to invoke. Supported values are ``'pydeface'`` (default)
        and ``'afni_refacer'``.

    Returns
    -------
    list[Path]
        Absolute paths to all defaced output files that were successfully
        created.

    Raises
    ------
    ValueError
        If ``tool`` is not one of the supported values.
    """
    if tool not in ("pydeface", "afni_refacer"):
        raise ValueError(f"Unsupported defacing tool: {tool}")

    output_paths: list[Path] = []

    for p in config.participants:
        anat_dir = (
            config.bids_root
            / f"sub-{p.sub}"
            / f"ses-{p.ses}"
            / "anat"
        )

        if not anat_dir.is_dir():
            logger.debug("No anat/ directory found for sub-%s ses-%s; skipping.", p.sub, p.ses)
            continue

        nifti_files = list(anat_dir.glob("*_T1w.nii*")) + list(anat_dir.glob("*_T2w.nii*"))

        for input_path in nifti_files:
            filename = input_path.name
            output_path = (
                config.bids_root
                / "derivatives"
                / "defaced"
                / f"sub-{p.sub}"
                / f"ses-{p.ses}"
                / "anat"
                / filename
            )

            output_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                if tool == "pydeface":
                    subprocess.run(
                        ["pydeface", str(input_path), "--outfile", str(output_path)],
                        check=True,
                    )
                elif tool == "afni_refacer":
                    subprocess.run(
                        [
                            "@afni_refacer_run",
                            "-input", str(input_path),
                            "-mode_deface",
                            "-prefix", str(output_path),
                        ],
                        check=True,
                    )
            except FileNotFoundError:
                logger.warning(
                    "Defacing tool '%s' not found on PATH; skipping %s.",
                    tool,
                    input_path,
                )
                continue

            if output_path.exists():
                output_paths.append(output_path)
                logger.info("Defaced %s -> %s", input_path, output_path)
            else:
                logger.warning(
                    "Defacing produced no output for %s; not recorded.",
                    output_path,
                )

    return output_paths
