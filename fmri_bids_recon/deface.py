"""Defacing utilities for fmri-bids-recon.

Provides deface(), an opt-in publishing step that emits defaced anatomicals
to derivatives/defaced/ under the BIDS root. The analysis anat/ directories
are never modified.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from .config import StudyConfig
from .errors import ToolUnavailableError

logger = logging.getLogger(__name__)


def _build_fsl_env() -> dict[str, str]:
    """Return a per-call environment dict with FSL's bin directory reachable.

    Copies the current process environment and, when FSLDIR is set, appends
    $FSLDIR/bin to PATH (if not already present) so that pydeface's internal
    nipype calls can find flirt without requiring users to source fsl.sh.
    Also sets FSLOUTPUTTYPE to NIFTI_GZ if not already set. Unlike the prior
    _ensure_fsl_env(), this does NOT mutate os.environ -- the returned dict
    is scoped to the specific subprocess.run() call it is passed to, with no
    effect on unrelated later calls in the same process.
    """
    env = os.environ.copy()
    fsl_dir = env.get("FSLDIR")
    if fsl_dir:
        fsl_bin = str(Path(fsl_dir) / "bin")
        current_path = env.get("PATH", "")
        if fsl_bin not in current_path.split(os.pathsep):
            env["PATH"] = current_path + os.pathsep + fsl_bin
            logger.info("Appended %s to PATH for FSL tool access (scoped to this call).", fsl_bin)
        if "FSLOUTPUTTYPE" not in env:
            env["FSLOUTPUTTYPE"] = "NIFTI_GZ"
    return env


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
    ToolUnavailableError
        If the defacing tool binary is absent or exits non-zero. The
        original exception is preserved via the exception cause chain.
    """
    if tool not in ("pydeface", "afni_refacer"):
        raise ValueError(f"Unsupported defacing tool: {tool}")

    fsl_env = _build_fsl_env()

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
                        env=fsl_env,
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
                        env=fsl_env,
                    )
            except subprocess.CalledProcessError as exc:
                raise ToolUnavailableError(
                    f"Defacing tool '{tool}' failed on {input_path.name}: "
                    f"exit code {exc.returncode}",
                    context={
                        "tool": tool,
                        "input_path": str(input_path),
                        "returncode": exc.returncode,
                    },
                ) from exc
            except FileNotFoundError as exc:
                raise ToolUnavailableError(
                    f"Defacing tool '{tool}' binary not found: {exc}",
                    context={
                        "tool": tool,
                        "input_path": str(input_path),
                    },
                ) from exc

            if output_path.exists():
                output_paths.append(output_path)
                logger.info("Defaced %s -> %s", input_path, output_path)
            else:
                logger.warning(
                    "Defacing produced no output for %s; not recorded.",
                    output_path,
                )

    return output_paths
