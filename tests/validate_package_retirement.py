from __future__ import annotations

import subprocess
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts/unlist_superseded_nuget.py").read_text(encoding="utf-8")
    workflow = root / ".github/workflows/unlist-superseded.yml"
    retired = {
        "Orbyss.Forms.Application",
        "Orbyss.Forms.Core",
        "Orbyss.Forms.Mcp.AspNetCore",
        "Orbyss.Forms.Tool",
    }
    for package_id in retired:
        if f'"{package_id}"' not in script:
            raise AssertionError(f"Retirement allowlist is missing {package_id}")
    if 'SUPERSEDED_VERSION = "0.1.0"' not in script or '"--version"' in script:
        raise AssertionError("Retirement must remain restricted to the superseded 0.1.0 version")
    if workflow.exists():
        raise AssertionError("Superseded-package retirement must remain a local NuGet CLI operation")
    for required in ("dotnet", "nuget", "delete", "--verify-public", "--execute", "NUGET_API_KEY"):
        if f'"{required}"' not in script and required not in script:
            raise AssertionError(f"Local retirement command is missing {required}")
    if "unlist_superseded_nuget.py" in (root / ".github/workflows/release.yml").read_text(encoding="utf-8"):
        raise AssertionError("Irreversible retirement must remain outside the stable release workflow")
    if "verify_unlisted(args.timeout_seconds)" not in script:
        raise AssertionError("Retirement execution must verify that NuGet.org reports every old version unlisted")
    result = subprocess.run(
        ["python", str(root / "scripts/unlist_superseded_nuget.py")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or "Dry run" not in result.stdout:
        raise AssertionError(f"Retirement dry run failed.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    print("Orbyss Forms superseded-package retirement contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
