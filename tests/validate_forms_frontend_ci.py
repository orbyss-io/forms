from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    workflow = (ROOT / ".github/workflows/frontend-ci.yml").read_text(encoding="utf-8")
    general_workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    if "permissions:\n  contents: read" not in workflow:
        raise AssertionError("CI must retain a read-only repository permission boundary.")
    for forbidden in ("packages: write", "npm publish", "publish-nuget", "publish-host-image"):
        if forbidden in workflow:
            raise AssertionError(f"Non-publishing CI contains forbidden publication authority: {forbidden}")

    if "validate_forms_frontend.py --install" in general_workflow or "validate_forms_browser.py" in general_workflow:
        raise AssertionError("The general validation job must not duplicate the dedicated frontend gate.")
    if "  contracts:" not in workflow or "  browser:" not in workflow:
        raise AssertionError("Frontend contracts and browser acceptance must have dedicated CI jobs.")

    _, jobs = workflow.split("jobs:", maxsplit=1)
    contract_job, browser_job = jobs.split("  browser:", maxsplit=1)
    for required in (
        "python tests/validate_forms_frontend_ci.py",
        "python tests/validate_forms_frontend.py --install",
        "python tests/validate_forms_frontend_packages.py",
    ):
        if required not in contract_job:
            raise AssertionError(f"Frontend contract CI is missing: {required}")

    for required in (
        "fail-fast: false",
        "engine: [chromium, firefox, webkit]",
        "--install --install-browser --engines ${{ matrix.engine }}",
        "forms-browser-${{ matrix.engine }}-${{ github.sha }}",
    ):
        if required not in browser_job:
            raise AssertionError(f"Cross-engine frontend CI is missing: {required}")

    path_filters = (
        '      - ".github/workflows/frontend-ci.yml"',
        '      - "src/typescript/**"',
        '      - "src/typescript/tests/forms-browser/**"',
        '      - "tests/validate_forms_frontend_ci.py"',
    )
    for required in path_filters:
        if workflow.count(required) != 2:
            raise AssertionError(f"Push and pull-request path filters are missing: {required}")

    print("Read-only frontend CI contract and Chromium/Firefox/WebKit matrix passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
