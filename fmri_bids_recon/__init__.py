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

__version__ = '1.10.0'

from .config import load_and_validate
from .pipeline import run, BidsReconResult
