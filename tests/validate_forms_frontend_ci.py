from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    if "permissions:\n  contents: read" not in workflow:
        raise AssertionError("CI must retain a read-only repository permission boundary.")
    for forbidden in ("packages: write", "npm publish", "dotnet nuget push"):
        if forbidden in workflow:
            raise AssertionError(f"Non-publishing CI contains forbidden publication authority: {forbidden}")

    for job in ("  dotnet:", "  frontend:", "  browser:"):
        if job not in workflow:
            raise AssertionError(f"CI is missing its dedicated job: {job.strip()}")

    frontend_job = workflow.split("  frontend:", maxsplit=1)[1].split("  browser:", maxsplit=1)[0]
    for required in (
        "python tests/validate_forms_frontend_ci.py",
        "python tests/validate_forms_frontend.py --install",
        "python tests/validate_forms_frontend_packages.py",
        "python tests/validate_forms_physical_acceptance.py",
        "npm pack --workspaces",
    ):
        if required not in frontend_job:
            raise AssertionError(f"Frontend contract CI is missing: {required}")

    browser_job = workflow.split("  browser:", maxsplit=1)[1]
    for required in (
        "fail-fast: false",
        "engine: [chromium, firefox, webkit]",
        "--install --install-browser --engines ${{ matrix.engine }}",
        "forms-browser-${{ matrix.engine }}-${{ github.sha }}",
    ):
        if required not in browser_job:
            raise AssertionError(f"Cross-engine frontend CI is missing: {required}")

    print("Read-only CI contract and Chromium/Firefox/WebKit matrix passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

