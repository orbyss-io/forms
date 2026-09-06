from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src/typescript"
sys.path.insert(0, str(ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/eng/program-kit"))
import js_toolchain


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--renew-lock", action="store_true")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    package = json.loads((WORKSPACE / "package.json").read_text(encoding="utf-8"))
    if package.get("scripts", {}).get("test") != "npm run build && node --test tests/runtime.test.mjs":
        raise AssertionError("The frontend unit command must be shell-glob independent on Windows and POSIX.")
    if package["devDependencies"] != {
        "@axe-core/playwright": "4.13.0",
        "@playwright/test": "1.62.1",
        "esbuild": "0.28.2",
        "typescript": "7.0.2",
    }:
        raise AssertionError("The frontend workspace must use only the governed compiler and browser-acceptance pins at the root.")

    package_files = sorted((WORKSPACE / "packages").glob("*/package.json"))
    expected = {
        "@orbyss/program-kit-forms-contracts",
        "@orbyss/program-kit-forms-renderer-registry",
        "@orbyss/program-kit-forms-jsonforms-runtime",
        "@orbyss/program-kit-forms-ajv-build",
        "@orbyss/program-kit-forms-codemirror",
        "@orbyss/program-kit-forms-wizard",
        "@orbyss/program-kit-forms-actions",
        "@orbyss/program-kit-forms-modeler",
        "@orbyss/program-kit-forms-modeler-react",
        "@orbyss/program-kit-forms-lookups",
        "@orbyss/program-kit-forms-lookups-react",
        "@orbyss/program-kit-forms-react",
        "@orbyss/program-kit-localization-management",
        "@orbyss/program-kit-localization-management-react",
    }
    manifests = [json.loads(path.read_text(encoding="utf-8")) for path in package_files]
    names = {manifest["name"] for manifest in manifests}
    if names != expected:
        raise AssertionError(f"Unexpected frontend package set: {sorted(names)}")

    by_name = {manifest["name"]: manifest for manifest in manifests}
    contracts = by_name["@orbyss/program-kit-forms-contracts"]
    if contracts.get("dependencies") or contracts.get("peerDependencies"):
        raise AssertionError("Frontend form contracts must remain dependency-free.")

    runtime_manifest = by_name["@orbyss/program-kit-forms-jsonforms-runtime"]
    runtime_dependencies = runtime_manifest["dependencies"]
    if runtime_manifest.get("peerDependencies") != {"@jsonforms/core": "3.8.0"} or "ajv" in runtime_dependencies:
        raise AssertionError("The JSON Forms runtime must exact-pin JSON Forms core as a peer and must not compile AJV at runtime.")

    codemirror_dependencies = by_name["@orbyss/program-kit-forms-codemirror"]["dependencies"]
    if codemirror_dependencies.get("codemirror") != "6.0.2":
        raise AssertionError("CodeMirror 6 must remain the default editor.")

    wizard_dependencies = by_name["@orbyss/program-kit-forms-wizard"]["dependencies"]
    if wizard_dependencies != {"@orbyss/program-kit-forms-contracts": "0.9.9-preview.1"}:
        raise AssertionError("The shared wizard state machine must remain framework-neutral.")

    action_dependencies = by_name["@orbyss/program-kit-forms-actions"]["dependencies"]
    if action_dependencies != {"@orbyss/program-kit-forms-contracts": "0.9.9-preview.1"}:
        raise AssertionError("The governed action controller must remain framework-neutral.")

    modeler = by_name["@orbyss/program-kit-forms-modeler"]
    if modeler.get("dependencies") or modeler.get("peerDependencies"):
        raise AssertionError("The provider-neutral form modeler must remain dependency-free.")

    modeler_react = by_name["@orbyss/program-kit-forms-modeler-react"]
    if modeler_react.get("dependencies") != {
        "@orbyss/program-kit-forms-codemirror": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-modeler": "0.9.9-preview.1",
    } or modeler_react.get("peerDependencies") != {
        "react": "19.2.8",
    } or modeler_react.get("devDependencies") != {"@types/react": "19.2.18"}:
        raise AssertionError("The React modeler must compose only the governed modeler and default editor packages.")

    localization_management = by_name["@orbyss/program-kit-localization-management"]
    if localization_management.get("dependencies") or localization_management.get("peerDependencies"):
        raise AssertionError("Localization management contracts and session state must remain dependency-free.")

    localization_react = by_name["@orbyss/program-kit-localization-management-react"]
    if localization_react.get("dependencies") != {
        "@orbyss/program-kit-localization-management": "0.9.9-preview.1",
    } or localization_react.get("peerDependencies") != {
        "react": "19.2.8",
    } or localization_react.get("devDependencies") != {"@types/react": "19.2.18"}:
        raise AssertionError("The React localization plane crossed its governed framework-neutral boundary.")

    lookup_dependencies = by_name["@orbyss/program-kit-forms-lookups"]["dependencies"]
    if lookup_dependencies != {"@orbyss/program-kit-forms-contracts": "0.9.9-preview.1"}:
        raise AssertionError("Searchable lookups must remain framework-neutral and depend only on JSON-safe contracts.")

    lookup_react = by_name["@orbyss/program-kit-forms-lookups-react"]
    if lookup_react.get("dependencies") != {
        "@orbyss/program-kit-forms-contracts": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-lookups": "0.9.9-preview.1",
    } or lookup_react.get("peerDependencies") != {
        "@jsonforms/core": "3.8.0",
        "@jsonforms/react": "3.8.0",
        "react": "19.2.8",
    } or lookup_react.get("devDependencies") != {"@types/react": "19.2.18"}:
        raise AssertionError("The optional React lookup renderer crossed its governed package boundary.")

    base_config = json.loads((WORKSPACE / "tsconfig.base.json").read_text(encoding="utf-8"))
    if base_config["compilerOptions"].get("skipLibCheck") is not False:
        raise AssertionError("Library declaration checking must remain enabled for the frontend workspace.")
    quarantined = {"forms-react", "forms-lookups-react"}
    for config_path in (WORKSPACE / "packages").glob("*/tsconfig.json"):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        skipped = config.get("compilerOptions", {}).get("skipLibCheck", False)
        if skipped != (config_path.parent.name in quarantined):
            raise AssertionError(f"Unexpected library-check quarantine: {config_path}")

    react_manifest = by_name["@orbyss/program-kit-forms-react"]
    if react_manifest.get("dependencies") != {
        "@orbyss/program-kit-forms-actions": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-contracts": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-wizard": "0.9.9-preview.1",
    }:
        raise AssertionError("The React binding must compose only the governed framework-neutral form packages.")
    if react_manifest.get("peerDependencies") != {
        "@jsonforms/core": "3.8.0",
        "@jsonforms/react": "3.8.0",
        "react": "19.2.8",
    }:
        raise AssertionError("The React binding must expose exact framework peer boundaries.")
    if react_manifest.get("devDependencies") != {
        "@types/react": "19.2.18",
        "@types/react-dom": "19.2.7",
        "react-dom": "19.2.8",
    }:
        raise AssertionError("The React binding must compile against the governed React type pin.")
    if react_manifest.get("files") != ["dist", "styles.css"] or react_manifest.get("exports", {}).get("./styles.css") != "./styles.css":
        raise AssertionError("The semantic React control baseline must remain an explicit optional CSS export.")

    all_dependency_names = {
        dependency
        for manifest in manifests
        for section in ("dependencies", "devDependencies", "peerDependencies")
        for dependency in manifest.get(section, {})
    }
    if any("monaco" in dependency.lower() for dependency in all_dependency_names):
        raise AssertionError("Monaco leaked into the default frontend workspace.")

    node, _ = js_toolchain.resolve_node(ROOT, package["engines"]["node"], "node", "auto")
    if node is None:
        raise AssertionError(f"Install the approved Node {package['engines']['node']} runtime first.")
    npm, _ = js_toolchain.resolve_npm(ROOT, node, package["engines"]["npm"], "npm")
    if npm is None:
        raise AssertionError(f"Install the approved npm {package['engines']['npm']} toolchain first.")
    cache = js_toolchain.require_writable_cache(ROOT / "artifacts/forms-npm-cache")
    environment, _, _ = js_toolchain.trust_environment(ROOT, cache)
    environment["PATH"] = str(node.parent) + os.pathsep + environment.get("PATH", "")

    def run(arguments: list[str], timeout: int = 180) -> None:
        result = subprocess.run(
            npm + arguments,
            cwd=WORKSPACE,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"Managed npm command failed: {arguments}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )

    if args.renew_lock:
        run(["install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund", "--strict-ssl=true", "--fetch-retries=0", "--fetch-timeout=30000"])
    if args.install:
        run(["ci", "--ignore-scripts", "--no-audit", "--no-fund", "--strict-ssl=true", "--fetch-retries=0", "--fetch-timeout=30000"])

    lock = json.loads((WORKSPACE / "package-lock.json").read_text(encoding="utf-8"))
    if lock.get("lockfileVersion") != 3:
        raise AssertionError("The frontend workspace requires a committed npm lockfile v3.")
    if "monaco" in json.dumps(lock, sort_keys=True).lower():
        raise AssertionError("Monaco leaked into the isolated default frontend lockfile.")

    run(["test", "--ignore-scripts", "--no-audit", "--no-fund"])
    run(["pack", "--workspaces", "--dry-run", "--ignore-scripts", "--no-audit", "--no-fund"])
    print("Forms frontend contracts, JSON Forms runtime, AJV parity, renderer/actions, modeler UI, searchable lookups, localization management, React bindings, wizard state, and CodeMirror default passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
