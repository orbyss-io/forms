from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src" / "typescript"
EXPECTED_PACKAGES = (
    "@orbyss-io/forms-actions",
    "@orbyss-io/forms-ajv-build",
    "@orbyss-io/forms-angular",
    "@orbyss-io/forms-contracts",
    "@orbyss-io/forms-editor-contracts",
    "@orbyss-io/forms-jsonforms-runtime",
    "@orbyss-io/forms-lookups",
    "@orbyss-io/forms-react",
    "@orbyss-io/forms-renderer-registry",
    "@orbyss-io/forms-vue",
    "@orbyss-io/forms-wizard",
    "@orbyss-io/forms-ui-theme",
)


def load_manifests() -> list[dict[str, object]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((WORKSPACE / "packages").glob("*/package.json"))
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag")
    parser.add_argument("--print-package-names", action="store_true")
    args = parser.parse_args()

    if args.print_package_names:
        print("\n".join(EXPECTED_PACKAGES))
        return 0

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if args.tag is not None and args.tag != f"v{version}":
        raise AssertionError(f"Release tag {args.tag!r} does not match v{version}.")

    root_manifest = json.loads((WORKSPACE / "package.json").read_text(encoding="utf-8"))
    if root_manifest.get("version") != version:
        raise AssertionError("The frontend workspace version must match VERSION.")

    manifests = load_manifests()
    if tuple(sorted(str(manifest["name"]) for manifest in manifests)) != tuple(sorted(EXPECTED_PACKAGES)):
        raise AssertionError("The publishable frontend family is not the approved exact 12-package set.")

    expected_repository = {
        "type": "git",
        "url": "git+https://github.com/orbyss-io/forms.git",
    }
    expected_publish = {
        "registry": "https://npm.pkg.github.com",
        "access": "public",
        "tag": "preview",
    }
    for manifest in manifests:
        name = str(manifest["name"])
        if manifest.get("version") != version:
            raise AssertionError(f"{name} does not match VERSION.")
        if manifest.get("private") is True:
            raise AssertionError(f"{name} is unexpectedly private.")
        if manifest.get("license") != "MIT":
            raise AssertionError(f"{name} does not declare the repository license.")
        repository = manifest.get("repository")
        if not isinstance(repository, dict) or any(repository.get(key) != value for key, value in expected_repository.items()):
            raise AssertionError(f"{name} is not linked to the Orbyss Forms repository.")
        if not str(repository.get("directory", "")).startswith("src/typescript/packages/"):
            raise AssertionError(f"{name} has no package directory association.")
        if manifest.get("publishConfig") != expected_publish:
            raise AssertionError(f"{name} can publish outside the approved GitHub Packages preview channel.")

    for config_path in (WORKSPACE / "packages").glob("*/tsconfig.json"):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        build_info = str(config.get("compilerOptions", {}).get("tsBuildInfoFile", ""))
        if build_info.startswith("dist/"):
            raise AssertionError(f"{config_path.parent.name} would publish TypeScript build cache metadata.")

    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    required = (
        "environment: forms-packages-production",
        "packages: write",
        "registry-url: https://npm.pkg.github.com",
        'scope: "@orbyss-io"',
        "validate_forms_frontend.py --install",
        "npm pack --workspaces",
        "npm publish",
        "--tag=preview",
        "NODE_AUTH_TOKEN: ${{ github.token }}",
        "Verify package family",
    )
    for marker in required:
        if marker not in workflow:
            raise AssertionError(f"Frontend publication workflow lost required behavior: {marker}")
    for forbidden in (
        "pull_request:",
        "branches:",
        "workflow_dispatch:",
        "NPM_TOKEN",
        "ORBYSS_PACKAGES_TOKEN",
        "npmjs.org",
    ):
        if forbidden in workflow:
            raise AssertionError(f"Frontend publication gained an unsafe trigger or credential: {forbidden}")
    if "dotnet nuget push" not in workflow or "NuGet/login@" not in workflow:
        raise AssertionError("The Forms release must publish its .NET family in the same validated release.")

    print("Tag-only GitHub Packages publication contract passed for the exact frontend engine family.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
