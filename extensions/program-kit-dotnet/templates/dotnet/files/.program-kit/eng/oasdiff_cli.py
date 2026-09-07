from __future__ import annotations

import re
import subprocess
from pathlib import Path


VERSION_PROBES = (("--version",), ("-v",), ("version",))
VERSION_PATTERN = re.compile(r"(?i)\boasdiff(?:\s+version)?\s+v?(\d+\.\d+\.\d+)\b")


def detect(command: Path | str, repository: Path) -> tuple[str | None, list[str] | None]:
    for arguments in VERSION_PROBES:
        try:
            result = subprocess.run(
                [str(command), *arguments],
                cwd=repository,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode != 0:
            continue
        match = VERSION_PATTERN.search(result.stdout + result.stderr)
        if match:
            return match.group(1), list(arguments)
    return None, None


def require(command: Path | str, repository: Path, expected: str) -> None:
    actual, _ = detect(command, repository)
    if actual != expected:
        raise ValueError(f"PKO007 expected oasdiff {expected}; resolved exact version was {actual or 'unavailable'}")
