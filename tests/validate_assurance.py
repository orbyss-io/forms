from __future__ import annotations

import subprocess
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    project = root / "tests/dotnet/ProgramKit.Authentication.Assurance.Probe"
    completed = subprocess.run(
        ["dotnet", "run", "--project", str(project), "-c", "Release", "--no-build"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "Provider-neutral assurance probe failed:\n" + completed.stdout + completed.stderr
        )
    print("Provider-neutral ACR, AMR, authentication-age, and authorization invariants passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
