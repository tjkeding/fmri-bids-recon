"""Tool version registry for fmri-bids-recon.

Reads tools.lock.yaml, probes installed binaries, and validates pinned
versions using Class A (exact/floor) or Class B (floor-only) semantics.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import StudyConfig
from .errors import ToolVersionError

logger = logging.getLogger(__name__)


@dataclass
class ToolStatus:
    name: str
    pinned_version: str
    found_version: str | None
    pin_class: str
    status: str
    message: str


@dataclass
class ToolReport:
    tools: dict[str, ToolStatus] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(t.status == "error" for t in self.tools.values())


def _default_lockfile_path() -> Path:
    return Path(__file__).resolve().parent.parent / "tools.lock.yaml"


def _load_lockfile(path: Path) -> dict:
    with path.open("r") as fh:
        data = yaml.safe_load(fh)
    return data


def _resolve_binary(name: str, binary: str) -> str | None:
    if name == "flirt":
        fsl_dir = os.environ.get("FSLDIR")
        if fsl_dir:
            candidate = Path(fsl_dir) / "bin" / "flirt"
            if candidate.is_file():
                return str(candidate)
    return shutil.which(binary)


def _probe_tool(name: str, binary: str, version_flag: str) -> str | None:
    try:
        result = subprocess.run(
            [binary, version_flag],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout + result.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _parse_version(text: str, tool_name: str) -> tuple[int, ...] | None:
    if tool_name == "dcm2niix":
        match = re.search(r"v(\d+)\.(\d+)\.(\d+)", text)
        if match:
            return tuple(int(g) for g in match.groups())
    elif tool_name == "pydeface":
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
        if match:
            return tuple(int(g) for g in match.groups())
    elif tool_name == "flirt":
        match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?(?:\.(\d+))?", text)
        if match:
            return tuple(int(g) for g in match.groups() if g is not None)
    return None


def _parse_pinned_version(version_str: str) -> tuple[int, ...]:
    return tuple(int(x) for x in version_str.split("."))


def _compare_versions(
    found: tuple[int, ...],
    pinned: tuple[int, ...],
    pin_class: str,
    strict: bool,
    enforcement: str | None,
) -> tuple[str, str]:
    if enforcement == "declarative":
        if found != pinned[:len(found)]:
            found_str = ".".join(str(x) for x in found)
            pinned_str = ".".join(str(x) for x in pinned)
            return ("warning", f"version {found_str} differs from pin {pinned_str} (declarative)")
        return ("ok", "version matches pin")

    if pin_class == "A":
        if strict:
            if found == pinned:
                return ("ok", "exact match")
            found_str = ".".join(str(x) for x in found)
            pinned_str = ".".join(str(x) for x in pinned)
            return ("error", f"version {found_str} does not match pin {pinned_str} (strict)")
        if found < pinned:
            found_str = ".".join(str(x) for x in found)
            pinned_str = ".".join(str(x) for x in pinned)
            return ("error", f"version {found_str} is below floor {pinned_str}")
        if found > pinned:
            found_str = ".".join(str(x) for x in found)
            pinned_str = ".".join(str(x) for x in pinned)
            return ("warning", f"version {found_str} exceeds pin {pinned_str} (lenient)")
        return ("ok", "version matches pin")

    if found < pinned:
        found_str = ".".join(str(x) for x in found)
        pinned_str = ".".join(str(x) for x in pinned)
        return ("error", f"version {found_str} is below floor {pinned_str}")
    return ("ok", "version meets floor")


def preflight_tool_environments(
    config: StudyConfig,
    *,
    strict: bool = False,
    lockfile: Path | None = None,
) -> ToolReport:
    lock_path = lockfile or _default_lockfile_path()
    lock_data = _load_lockfile(lock_path)
    report = ToolReport()

    python_pin = lock_data.get("python")
    if python_pin:
        pinned_tuple = _parse_pinned_version(python_pin)
        found_tuple = (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
        found_str = f"{found_tuple[0]}.{found_tuple[1]}.{found_tuple[2]}"
        if found_tuple < pinned_tuple:
            py_status = "error" if strict else "warning"
            py_message = f"Python {found_str} is below floor {python_pin}"
        else:
            py_status = "ok"
            py_message = f"Python {found_str} meets floor {python_pin}"
        report.tools["python"] = ToolStatus(
            name="python",
            pinned_version=python_pin,
            found_version=found_str,
            pin_class="B",
            status=py_status,
            message=py_message,
        )
        logger.info("Tool python: %s (%s)", py_status, py_message)

    for name, spec in lock_data.get("binaries", {}).items():
        conditional = spec.get("conditional")
        if conditional and not getattr(config, conditional, False):
            report.tools[name] = ToolStatus(
                name=name,
                pinned_version=spec["version"],
                found_version=None,
                pin_class=spec["pin_class"],
                status="skipped",
                message=f"conditional on config.{conditional} (disabled)",
            )
            logger.info("Tool %s: skipped (config.%s is false)", name, conditional)
            continue

        binary_path = _resolve_binary(name, spec["binary"])
        if binary_path is None:
            msg = f"{spec['binary']} not found on PATH"
            if name == "flirt":
                msg += (
                    ". Set the FSLDIR environment variable"
                    " (e.g. via 'module load FSL')"
                    " or add FSL's bin directory to PATH."
                )
            report.tools[name] = ToolStatus(
                name=name,
                pinned_version=spec["version"],
                found_version=None,
                pin_class=spec["pin_class"],
                status="error",
                message=msg,
            )
            continue

        raw_output = _probe_tool(name, binary_path, spec["version_flag"])
        if raw_output is None:
            report.tools[name] = ToolStatus(
                name=name,
                pinned_version=spec["version"],
                found_version=None,
                pin_class=spec["pin_class"],
                status="error",
                message=f"failed to probe {spec['binary']}",
            )
            continue

        found_tuple = _parse_version(raw_output, name)
        if found_tuple is None:
            report.tools[name] = ToolStatus(
                name=name,
                pinned_version=spec["version"],
                found_version=None,
                pin_class=spec["pin_class"],
                status="error",
                message=f"could not parse version from output: {raw_output[:200]}",
            )
            continue

        pinned_tuple = _parse_pinned_version(spec["version"])
        enforcement = spec.get("enforcement")
        status, message = _compare_versions(
            found_tuple, pinned_tuple, spec["pin_class"], strict, enforcement,
        )

        found_str = ".".join(str(x) for x in found_tuple)
        report.tools[name] = ToolStatus(
            name=name,
            pinned_version=spec["version"],
            found_version=found_str,
            pin_class=spec["pin_class"],
            status=status,
            message=message,
        )
        logger.info("Tool %s: %s (%s)", name, status, message)

    if report.has_errors:
        error_tools = [t for t in report.tools.values() if t.status == "error"]
        messages = [f"{t.name}: {t.message}" for t in error_tools]
        raise ToolVersionError(
            "Tool version preflight failed: " + "; ".join(messages),
            context={"report": {n: t.status for n, t in report.tools.items()}},
        )

    return report
