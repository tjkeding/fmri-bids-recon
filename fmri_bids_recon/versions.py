"""Version floor enforcement for external binaries used by fmri-bids-recon."""

from __future__ import annotations

import re
import subprocess

from .errors import VersionFloorError

DCM2NIIX_VERSION_FLOOR = "1.0.20260416"


def parse_dcm2niix_version(text: str) -> tuple[int, int, int]:
    """Extract the version tuple from dcm2niix --version output.

    Parameters
    ----------
    text : str
        Raw text output (stdout or stderr) from ``dcm2niix --version``.

    Returns
    -------
    tuple[int, int, int]
        A three-element tuple ``(major, minor, date_int)`` where the third
        component is a date-like integer compared numerically.

    Raises
    ------
    ValueError
        If no version token matching ``vX.Y.ZZZZZZZZ`` can be found in *text*.
    """
    match = re.search(r"v(\d+)\.(\d+)\.(\d+)", text)
    if match is None:
        raise ValueError(
            f"Cannot parse dcm2niix version from output: {text!r}"
        )
    major, minor, date_int = int(match.group(1)), int(match.group(2)), int(match.group(3))
    return (major, minor, date_int)


def assert_dcm2niix_version(binary: str = "dcm2niix") -> str:
    """Assert that the installed dcm2niix meets the minimum version floor.

    Parameters
    ----------
    binary : str
        Name or absolute path of the dcm2niix executable.

    Returns
    -------
    str
        The version string (e.g. ``'1.0.20260416'``) on success, suitable
        for inclusion in the provenance record.

    Raises
    ------
    VersionFloorError
        If the parsed version tuple is strictly below the floor tuple defined
        by :data:`DCM2NIIX_VERSION_FLOOR`.
    """
    result = subprocess.run(
        [binary, "--version"],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    version_tuple = parse_dcm2niix_version(output)
    floor_tuple = parse_dcm2niix_version("v" + DCM2NIIX_VERSION_FLOOR)

    if version_tuple < floor_tuple:
        version_str = ".".join(str(x) for x in version_tuple)
        raise VersionFloorError(
            f"dcm2niix version {version_str} is below the required floor "
            f"{DCM2NIIX_VERSION_FLOOR}.",
            context={
                "found": version_str,
                "floor": DCM2NIIX_VERSION_FLOOR,
                "binary": binary,
            },
        )

    return ".".join(str(x) for x in version_tuple)
