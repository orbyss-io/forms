from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src" / "typescript"
EXPECTED_PACKAGES = (
    "@orbyss-io/program-kit-forms-actions",
    "@orbyss-io/program-kit-forms-ajv-build",
    "@orbyss-io/program-kit-forms-angular",
    "@orbyss-io/program-kit-forms-contracts",
    "@orbyss-io/program-kit-forms-editor-contracts",
    "@orbyss-io/program-kit-forms-jsonforms-runtime",
    "@orbyss-io/program-kit-forms-lookups",
    "@orbyss-io/program-kit-forms-react",
    "@orbyss-io/program-kit-forms-renderer-registry",
    "@orbyss-io/program-kit-forms-vue",
    "@orbyss-io/program-kit-forms-wizard",
    "@orbyss-io/program-kit-ui-theme",
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
    runtime_version = (ROOT / "RUNTIME_VERSION").read_text(encoding="utf-8").strip()
    if args.tag is not None and args.tag != f"v{version}":
        raise AssertionError(f"Release tag {args.tag!r} does not match v{version}.")

    root_manifest = json.loads((WORKSPACE / "package.json").read_text(encoding="utf-8"))
    if root_manifest.get("version") != runtime_version:
        raise AssertionError("The frontend workspace version must match RUNTIME_VERSION.")

    manifests = load_manifests()
    if tuple(sorted(str(manifest["name"]) for manifest in manifests)) != EXPECTED_PACKAGES:
        raise AssertionError("The publishable frontend family is not the approved exact 12-package set.")

    expected_repository = {
        "type": "git",
        "url": "git+https://github.com/orbyss-io/program-kit.git",
    }
    expected_publish = {
        "registry": "https://npm.pkg.github.com",
        "access": "public",
        "tag": "preview",
    }
    for manifest in manifests:
        name = str(manifest["name"])
        if manifest.get("version") != runtime_version:
            raise AssertionError(f"{name} does not match RUNTIME_VERSION.")
        if manifest.get("private") is True:
            raise AssertionError(f"{name} is unexpectedly private.")
        if manifest.get("license") != "MIT":
            raise AssertionError(f"{name} does not declare the repository license.")
        repository = manifest.get("repository")
        if not isinstance(repository, dict) or any(repository.get(key) != value for key, value in expected_repository.items()):
            raise AssertionError(f"{name} is not linked to the Program Kit repository.")
        if not str(repository.get("directory", "")).startswith("src/typescript/packages/"):
            raise AssertionError(f"{name} has no package directory association.")
        if manifest.get("publishConfig") != expected_publish:
            raise AssertionError(f"{name} can publish outside the approved GitHub Packages preview channel.")

    for config_path in (WORKSPACE / "packages").glob("*/tsconfig.json"):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        build_info = str(config.get("compilerOptions", {}).get("tsBuildInfoFile", ""))
        if build_info.startswith("dist/"):
            raise AssertionError(f"{config_path.parent.name} would publish TypeScript build cache metadata.")

    workflow = (ROOT / ".github" / "workflows" / "publish-frontend.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    required = (
        "environment: frontend-packages-production",
        "packages: write",
        "registry-url: https://npm.pkg.github.com",
        'scope: "@orbyss-io"',
        "npm ci --ignore-scripts",
        "npm pack --workspaces",
        "npm publish",
        "--tag=preview",
        "NODE_AUTH_TOKEN: ${{ github.token }}",
        "Verify clean GitHub Packages installation",
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
    if (
        "publish-frontend:\n    needs: release" not in release
        or "uses: ./.github/workflows/publish-frontend.yml" not in release
    ):
        raise AssertionError("The tag release does not gate frontend publication on full release validation.")
    if "publish-nuget:\n    needs: [release, publish-frontend]" not in release:
        raise AssertionError("NuGet publication must wait for successful frontend publication.")
    if "publish-host-image:\n    needs: [release, publish-frontend, publish-nuget]" not in release:
        raise AssertionError("Host-image publication must wait for both package families.")

    print("Tag-only GitHub Packages publication contract passed for the exact frontend engine family.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
