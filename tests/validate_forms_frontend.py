from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src/typescript"
sys.path.insert(0, str(ROOT / "eng"))
import js_toolchain


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--renew-lock", action="store_true")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    package = json.loads((WORKSPACE / "package.json").read_text(encoding="utf-8"))
    if package.get("scripts", {}).get("build") != "tsc -b && npm run build --workspace=@orbyss-io/forms-angular":
        raise AssertionError("The frontend build must include Angular partial compilation after framework-neutral TypeScript builds.")
    if package.get("scripts", {}).get("test") != "npm run build && node --test tests/runtime.test.mjs":
        raise AssertionError("The frontend unit command must be shell-glob independent on Windows and POSIX.")
    if package["devDependencies"] != {
        "@axe-core/playwright": "4.13.0",
        "@playwright/test": "1.62.1",
        "esbuild": "0.28.2",
        "typescript": "7.0.2",
    }:
        raise AssertionError("The frontend workspace must use only the governed compiler and browser-acceptance pins at the root.")

    withdrawn = {
        "forms-codemirror", "forms-lookups-react", "forms-monaco",
        "forms-modeler", "forms-modeler-angular", "forms-modeler-react", "forms-modeler-vue",
        "forms-schema-modeler", "forms-schema-modeler-angular", "forms-schema-modeler-react",
        "forms-schema-modeler-vue", "localization-management", "localization-management-angular",
        "localization-management-react", "localization-management-vue",
    }
    present_withdrawn = sorted(name for name in withdrawn if (WORKSPACE / "packages" / name).exists())
    if present_withdrawn:
        raise AssertionError(f"Rejected management UI packages still exist: {present_withdrawn}")

    package_files = sorted((WORKSPACE / "packages").glob("*/package.json"))
    expected = {
        "@orbyss-io/forms-contracts",
        "@orbyss-io/forms-renderer-registry",
        "@orbyss-io/forms-jsonforms-runtime",
        "@orbyss-io/forms-ajv-build",
        "@orbyss-io/forms-editor-contracts",
        "@orbyss-io/forms-wizard",
        "@orbyss-io/forms-actions",
        "@orbyss-io/forms-angular",
        "@orbyss-io/forms-lookups",
        "@orbyss-io/forms-react",
        "@orbyss-io/forms-vue",
        "@orbyss-io/forms-ui-theme",
    }
    manifests = [json.loads(path.read_text(encoding="utf-8")) for path in package_files]
    names = {manifest["name"] for manifest in manifests}
    if names != expected:
        raise AssertionError(f"Unexpected frontend package set: {sorted(names)}")

    by_name = {manifest["name"]: manifest for manifest in manifests}
    contracts = by_name["@orbyss-io/forms-contracts"]
    if contracts.get("dependencies") or contracts.get("peerDependencies"):
        raise AssertionError("Frontend form contracts must remain dependency-free.")

    runtime_manifest = by_name["@orbyss-io/forms-jsonforms-runtime"]
    runtime_dependencies = runtime_manifest["dependencies"]
    if runtime_manifest.get("peerDependencies") != {"@jsonforms/core": "3.8.0"} or "ajv" in runtime_dependencies:
        raise AssertionError("The JSON Forms runtime must exact-pin JSON Forms core as a peer and must not compile AJV at runtime.")

    editor_contracts = by_name["@orbyss-io/forms-editor-contracts"]
    if editor_contracts.get("dependencies") or editor_contracts.get("peerDependencies") or editor_contracts.get("devDependencies"):
        raise AssertionError("The shared JSON editor contract must remain dependency-free.")

    editor_policy = (WORKSPACE / "packages/forms-editor-contracts/src/index.ts").read_text(encoding="utf-8")
    if "tabSize: 2" not in editor_policy or "tabKeyIndents: true" not in editor_policy:
        raise AssertionError("Application-owned editors must receive the governed two-space Tab indentation policy.")

    wizard_dependencies = by_name["@orbyss-io/forms-wizard"]["dependencies"]
    if wizard_dependencies != {"@orbyss-io/forms-contracts": "0.1.0"}:
        raise AssertionError("The shared wizard state machine must remain framework-neutral.")

    action_dependencies = by_name["@orbyss-io/forms-actions"]["dependencies"]
    if action_dependencies != {"@orbyss-io/forms-contracts": "0.1.0"}:
        raise AssertionError("The governed action controller must remain framework-neutral.")

    theme = by_name["@orbyss-io/forms-ui-theme"]
    if theme.get("dependencies") or theme.get("peerDependencies") or theme.get("devDependencies"):
        raise AssertionError("The framework-neutral theme contract must remain dependency-free.")
    if theme.get("files") != ["dist", "default.css"] or theme.get("exports", {}).get("./default.css") != "./default.css":
        raise AssertionError("The default theme must remain an explicit optional CSS export.")
    if theme.get("sideEffects") != ["./default.css"]:
        raise AssertionError("Only the explicitly imported default theme may be marked as a side effect.")
    theme_css = (WORKSPACE / "packages/ui-theme/default.css").read_text(encoding="utf-8")
    if "@layer orbyss-forms.theme" not in theme_css or "[data-pk-theme" not in theme_css:
        raise AssertionError("The default theme must remain scoped and cascade-layered.")
    lookup_dependencies = by_name["@orbyss-io/forms-lookups"]["dependencies"]
    if lookup_dependencies != {"@orbyss-io/forms-contracts": "0.1.0"}:
        raise AssertionError("Searchable lookups must remain framework-neutral and depend only on JSON-safe contracts.")

    base_config = json.loads((WORKSPACE / "tsconfig.base.json").read_text(encoding="utf-8"))
    if base_config["compilerOptions"].get("skipLibCheck") is not False:
        raise AssertionError("Library declaration checking must remain enabled for the frontend workspace.")
    quarantined = {"forms-angular", "forms-react", "forms-vue"}
    for config_path in (WORKSPACE / "packages").glob("*/tsconfig.json"):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        skipped = config.get("compilerOptions", {}).get("skipLibCheck", False)
        if skipped != (config_path.parent.name in quarantined):
            raise AssertionError(f"Unexpected library-check quarantine: {config_path}")

    react_manifest = by_name["@orbyss-io/forms-react"]
    if react_manifest.get("dependencies") != {
        "@orbyss-io/forms-contracts": "0.1.0",
        "@orbyss-io/forms-jsonforms-runtime": "0.1.0",
    }:
        raise AssertionError("The thin React binding must depend only on governed runtime integration.")
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
    if react_manifest.get("files") != ["dist"] or react_manifest.get("sideEffects") is not False \
            or "./styles.css" in react_manifest.get("exports", {}):
        raise AssertionError("The thin React binding must not publish renderer components or CSS.")

    vue_manifest = by_name["@orbyss-io/forms-vue"]
    if vue_manifest.get("dependencies") != {
        "@orbyss-io/forms-contracts": "0.1.0",
        "@orbyss-io/forms-jsonforms-runtime": "0.1.0",
    } or vue_manifest.get("peerDependencies") != {
        "@jsonforms/core": "3.8.0",
        "@jsonforms/vue": "3.8.0",
        "vue": "3.5.42",
    } or vue_manifest.get("devDependencies") != {"vue": "3.5.42"}:
        raise AssertionError("The Vue binding crossed its governed framework-neutral runtime boundary.")
    if vue_manifest.get("files") != ["dist"] or vue_manifest.get("sideEffects") is not False \
            or "./styles.css" in vue_manifest.get("exports", {}):
        raise AssertionError("The thin Vue binding must not publish renderer components or CSS.")

    angular_manifest = by_name["@orbyss-io/forms-angular"]
    if angular_manifest.get("dependencies") != {
        "@orbyss-io/forms-contracts": "0.1.0",
        "@orbyss-io/forms-jsonforms-runtime": "0.1.0",
    } or angular_manifest.get("peerDependencies") != {
        "@angular/common": "22.1.5",
        "@angular/core": "22.1.5",
        "@angular/forms": "22.1.5",
        "@jsonforms/angular": "3.8.0",
        "@jsonforms/core": "3.8.0",
        "rxjs": "7.8.2",
    } or angular_manifest.get("devDependencies") != {
        "@angular/compiler": "22.1.5",
        "@angular/compiler-cli": "22.1.5",
        "typescript": "6.0.3",
    }:
        raise AssertionError("The Angular binding crossed its governed framework or compiler boundary.")

    validation_presentation = {
        "packages/forms-react/src/index.tsx": (
            'validationMode = "ValidateAndHide"',
            "consumer-supplied JSON Forms renderers",
        ),
        "packages/forms-vue/src/index.ts": (
            'default: "ValidateAndHide"',
            "validationMode: props.validationMode",
        ),
        "packages/forms-angular/src/index.ts": (
            '@Input() validationMode: ValidationMode = "ValidateAndHide"',
            '[validationMode]="validationMode"',
            '@Input({ required: true }) renderers!',
            "consumer-supplied JSON Forms renderers",
        ),
    }
    for relative, required_markers in validation_presentation.items():
        source = (WORKSPACE / relative).read_text(encoding="utf-8")
        for marker in required_markers:
            if marker not in source:
                raise AssertionError(f"{relative} lost governed delayed validation presentation: {marker}")

    for relative in ("packages/forms-react/src/index.tsx", "packages/forms-vue/src/index.ts"):
        source = (WORKSPACE / relative).read_text(encoding="utf-8")
        for forbidden in (
            "withJsonFormsControlProps",
            "OrbyssWizard",
            "OrbyssActionBar",
            "Orbyss.SearchableSelect",
            "pk-form-control",
            "pk-form-wizard",
            "pk-form-actions",
        ):
            if forbidden in source:
                raise AssertionError(f"The thin framework binding contains a withdrawn renderer component: {relative}: {forbidden}")

    for manifest in manifests:
        if manifest.get("exports", {}).get("./styles.css") == "./styles.css" \
                and manifest.get("sideEffects") != ["./styles.css"]:
            raise AssertionError(f"Explicit component CSS may be tree-shaken: {manifest['name']}")
        dependencies = {
            dependency
            for section in ("dependencies", "devDependencies", "peerDependencies")
            for dependency in manifest.get(section, {})
        }
        if any("monaco" in dependency.lower() for dependency in dependencies):
            raise AssertionError(f"A withdrawn Monaco component dependency remains: {manifest['name']}")

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
    locked_paths = lock.get("packages", {})
    if any(any(name in path for name in withdrawn) for path in locked_paths):
        raise AssertionError("The npm lockfile still contains a rejected management UI package.")
    if "node_modules/monaco-editor" in locked_paths or any("node_modules/@codemirror/" in path for path in locked_paths):
        raise AssertionError("The npm lockfile still contains a withdrawn editor component dependency.")

    run(["test", "--ignore-scripts", "--no-audit", "--no-fund"])
    angular_output = (WORKSPACE / "packages/forms-angular/dist/index.js").read_text(encoding="utf-8")
    if "ɵɵngDeclareComponent" not in angular_output or 'version: "22.1.5"' not in angular_output:
        raise AssertionError("The Angular package was not partial-compiled by the exact Angular compiler.")
    run(["pack", "--workspaces", "--dry-run", "--ignore-scripts", "--no-audit", "--no-fund"])
    print("Forms engine contracts, theme tokens, JSON Forms runtime, AJV parity, headless actions/lookups/wizard, editor contracts, and thin React/Vue/Angular bindings passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
