from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "extensions/program-kit-governance/scripts"))
import ui_profile


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="program-kit-ui-") as temporary:
        fixture = Path(temporary)
        ui_profile.execute(fixture, "init")
        ui_profile.execute(fixture, "build")
        result = subprocess.run(["dotnet", "run", "--project", str(ROOT / "tests/dotnet/ProgramKit.Web.Discovery.Probe"),
                                 "-c", "Release", "--", str(fixture)], cwd=ROOT, capture_output=True, text=True, timeout=180)
        if result.returncode:
            raise AssertionError(result.stdout + "\n" + result.stderr)
        print(result.stdout.strip().splitlines()[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
