from __future__ import annotations

import subprocess
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    project = root / (
        "tests/dotnet/ProgramKit.Authentication.ClientCredentials.Probe/"
        "ProgramKit.Authentication.ClientCredentials.Probe.csproj"
    )
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
            "Provider-neutral OAuth client-credentials probe failed.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    print("Provider-neutral OAuth client-credentials wire, cache, and transport invariants passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
