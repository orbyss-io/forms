from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "tests/dotnet/ProgramKit.Identity.Keycloak.Admin.Probe/ProgramKit.Identity.Keycloak.Admin.Probe.csproj"


def main() -> int:
    completed = subprocess.run(
        ["dotnet", "run", "--project", str(PROJECT), "--configuration", "Release"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if completed.returncode != 0:
        raise AssertionError(f"Keycloak Admin consumer probe failed:\n{completed.stdout}\n{completed.stderr}")
    print(completed.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
