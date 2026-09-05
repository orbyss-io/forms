from __future__ import annotations

import subprocess
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    project = root / "tests/dotnet/ProgramKit.Authentication.DPoP.Probe/ProgramKit.Authentication.DPoP.Probe.csproj"
    result = subprocess.run(
        [
            "dotnet",
            "run",
            "--project",
            str(project),
            "--configuration",
            "Release",
            "--no-restore",
            "--no-build",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Provider-neutral DPoP probe failed.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    print(
        "RFC 9449 outbound proof generation, key persistence, token/request binding, freshness, "
        "replaceable replay storage, and single-use nonce invariants passed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
