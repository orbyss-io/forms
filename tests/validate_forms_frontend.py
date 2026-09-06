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
    if package.get("scripts", {}).get("build") != "tsc -b && npm run build --workspace=@orbyss/program-kit-forms-angular":
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

    package_files = sorted((WORKSPACE / "packages").glob("*/package.json"))
    expected = {
        "@orbyss/program-kit-forms-contracts",
        "@orbyss/program-kit-forms-renderer-registry",
        "@orbyss/program-kit-forms-jsonforms-runtime",
        "@orbyss/program-kit-forms-ajv-build",
        "@orbyss/program-kit-forms-codemirror",
        "@orbyss/program-kit-forms-editor-contracts",
        "@orbyss/program-kit-forms-monaco",
        "@orbyss/program-kit-forms-wizard",
        "@orbyss/program-kit-forms-actions",
        "@orbyss/program-kit-forms-angular",
        "@orbyss/program-kit-forms-modeler",
        "@orbyss/program-kit-forms-modeler-react",
        "@orbyss/program-kit-forms-schema-modeler",
        "@orbyss/program-kit-forms-schema-modeler-react",
        "@orbyss/program-kit-forms-schema-modeler-vue",
        "@orbyss/program-kit-forms-lookups",
        "@orbyss/program-kit-forms-lookups-react",
        "@orbyss/program-kit-forms-react",
        "@orbyss/program-kit-forms-vue",
        "@orbyss/program-kit-localization-management",
        "@orbyss/program-kit-localization-management-react",
        "@orbyss/program-kit-ui-theme",
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

    editor_contracts = by_name["@orbyss/program-kit-forms-editor-contracts"]
    if editor_contracts.get("dependencies") or editor_contracts.get("peerDependencies") or editor_contracts.get("devDependencies"):
        raise AssertionError("The shared JSON editor contract must remain dependency-free.")

    codemirror_dependencies = by_name["@orbyss/program-kit-forms-codemirror"]["dependencies"]
    if codemirror_dependencies != {
        "@codemirror/commands": "6.11.0",
        "@codemirror/lang-json": "6.0.2",
        "@codemirror/language": "6.12.4",
        "@codemirror/lint": "6.9.7",
        "@codemirror/view": "6.43.11",
        "@orbyss/program-kit-forms-editor-contracts": "0.9.9-preview.1",
        "codemirror": "6.0.2",
    }:
        raise AssertionError("CodeMirror 6 must remain the default editor.")

    monaco = by_name["@orbyss/program-kit-forms-monaco"]
    if monaco.get("dependencies") != {"@orbyss/program-kit-forms-editor-contracts": "0.9.9-preview.1"} \
            or monaco.get("peerDependencies") != {"monaco-editor": "0.56.0"} \
            or monaco.get("devDependencies") != {"monaco-editor": "0.56.0"}:
        raise AssertionError("Monaco must remain a separately installed exact-pinned editor adapter.")
    editor_policy = (WORKSPACE / "packages/forms-editor-contracts/src/index.ts").read_text(encoding="utf-8")
    codemirror_source = (WORKSPACE / "packages/forms-codemirror/src/index.ts").read_text(encoding="utf-8")
    monaco_source = (WORKSPACE / "packages/forms-monaco/src/index.ts").read_text(encoding="utf-8")
    if "tabSize: 2" not in editor_policy or "tabKeyIndents: true" not in editor_policy \
            or "indentUnit.of" not in codemirror_source or "indentWithTab" not in codemirror_source \
            or "tabFocusMode: !jsonEditorIndentationPolicy.tabKeyIndents" not in monaco_source \
            or "detectIndentation: false" not in monaco_source:
        raise AssertionError("CodeMirror and Monaco must share the governed two-space Tab indentation policy.")

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
        "@orbyss/program-kit-forms-editor-contracts": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-modeler": "0.9.9-preview.1",
        "@orbyss/program-kit-ui-theme": "0.9.9-preview.1",
    } or modeler_react.get("peerDependencies") != {
        "react": "19.2.8",
    } or modeler_react.get("devDependencies") != {"@types/react": "19.2.18"}:
        raise AssertionError("The React modeler must compose only the governed modeler and default editor packages.")

    schema_modeler = by_name["@orbyss/program-kit-forms-schema-modeler"]
    if schema_modeler.get("dependencies") or schema_modeler.get("peerDependencies") or schema_modeler.get("devDependencies"):
        raise AssertionError("The provider-neutral schema modeler must remain dependency-free.")
    schema_modeler_react = by_name["@orbyss/program-kit-forms-schema-modeler-react"]
    if schema_modeler_react.get("dependencies") != {
        "@orbyss/program-kit-forms-codemirror": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-editor-contracts": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-schema-modeler": "0.9.9-preview.1",
        "@orbyss/program-kit-ui-theme": "0.9.9-preview.1",
    } or schema_modeler_react.get("peerDependencies") != {"react": "19.2.8"} \
            or schema_modeler_react.get("devDependencies") != {"@types/react": "19.2.18"}:
        raise AssertionError("The React schema modeler crossed its governed framework-neutral boundary.")

    schema_modeler_vue = by_name["@orbyss/program-kit-forms-schema-modeler-vue"]
    if schema_modeler_vue.get("dependencies") != {
        "@orbyss/program-kit-forms-codemirror": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-editor-contracts": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-schema-modeler": "0.9.9-preview.1",
        "@orbyss/program-kit-ui-theme": "0.9.9-preview.1",
    } or schema_modeler_vue.get("peerDependencies") != {"vue": "3.5.42"} \
            or schema_modeler_vue.get("devDependencies") != {"vue": "3.5.42"}:
        raise AssertionError("The Vue schema modeler crossed its governed framework-neutral boundary.")

    localization_management = by_name["@orbyss/program-kit-localization-management"]
    if localization_management.get("dependencies") or localization_management.get("peerDependencies"):
        raise AssertionError("Localization management contracts and session state must remain dependency-free.")

    localization_react = by_name["@orbyss/program-kit-localization-management-react"]
    if localization_react.get("dependencies") != {
        "@orbyss/program-kit-localization-management": "0.9.9-preview.1",
        "@orbyss/program-kit-ui-theme": "0.9.9-preview.1",
    } or localization_react.get("peerDependencies") != {
        "react": "19.2.8",
    } or localization_react.get("devDependencies") != {"@types/react": "19.2.18"}:
        raise AssertionError("The React localization plane crossed its governed framework-neutral boundary.")

    theme = by_name["@orbyss/program-kit-ui-theme"]
    if theme.get("dependencies") or theme.get("peerDependencies") or theme.get("devDependencies"):
        raise AssertionError("The framework-neutral theme contract must remain dependency-free.")
    if theme.get("files") != ["dist", "default.css"] or theme.get("exports", {}).get("./default.css") != "./default.css":
        raise AssertionError("The default theme must remain an explicit optional CSS export.")
    if theme.get("sideEffects") != ["./default.css"]:
        raise AssertionError("Only the explicitly imported default theme may be marked as a side effect.")
    theme_css = (WORKSPACE / "packages/ui-theme/default.css").read_text(encoding="utf-8")
    if "@layer program-kit.theme" not in theme_css or "[data-pk-theme" not in theme_css:
        raise AssertionError("The default theme must remain scoped and cascade-layered.")
    for stylesheet in (
        WORKSPACE / "packages/forms-modeler-react/styles.css",
        WORKSPACE / "packages/forms-schema-modeler-react/styles.css",
        WORKSPACE / "packages/forms-schema-modeler-vue/styles.css",
        WORKSPACE / "packages/localization-management-react/styles.css",
    ):
        content = stylesheet.read_text(encoding="utf-8")
        if "@layer program-kit.components" not in content or "var(--pk-" not in content:
            raise AssertionError(f"Management stylesheet is outside the semantic theme contract: {stylesheet}")
    if (WORKSPACE / "packages/forms-schema-modeler-react/styles.css").read_text(encoding="utf-8") != \
            (WORKSPACE / "packages/forms-schema-modeler-vue/styles.css").read_text(encoding="utf-8"):
        raise AssertionError("React and Vue schema modelers must expose the same portable visual contract.")
    for source in (
        WORKSPACE / "packages/forms-modeler-react/src/index.tsx",
        WORKSPACE / "packages/forms-schema-modeler-react/src/index.tsx",
        WORKSPACE / "packages/forms-schema-modeler-vue/src/index.ts",
        WORKSPACE / "packages/localization-management-react/src/index.tsx",
    ):
        content = source.read_text(encoding="utf-8")
        if "data-pk-slot" not in content or "unstyled" not in content or "ProgramKitClassNames" not in content:
            raise AssertionError(f"Management binding does not expose slots, typed classes, and unstyled mode: {source}")

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
    quarantined = {"forms-angular", "forms-react", "forms-lookups-react", "forms-vue"}
    for config_path in (WORKSPACE / "packages").glob("*/tsconfig.json"):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        skipped = config.get("compilerOptions", {}).get("skipLibCheck", False)
        if skipped != (config_path.parent.name in quarantined):
            raise AssertionError(f"Unexpected library-check quarantine: {config_path}")

    react_manifest = by_name["@orbyss/program-kit-forms-react"]
    if react_manifest.get("dependencies") != {
        "@orbyss/program-kit-forms-actions": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-contracts": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-jsonforms-runtime": "0.9.9-preview.1",
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

    vue_manifest = by_name["@orbyss/program-kit-forms-vue"]
    if vue_manifest.get("dependencies") != {
        "@orbyss/program-kit-forms-contracts": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-jsonforms-runtime": "0.9.9-preview.1",
    } or vue_manifest.get("peerDependencies") != {
        "@jsonforms/core": "3.8.0",
        "@jsonforms/vue": "3.8.0",
        "vue": "3.5.42",
    } or vue_manifest.get("devDependencies") != {"vue": "3.5.42"}:
        raise AssertionError("The Vue binding crossed its governed framework-neutral runtime boundary.")
    if vue_manifest.get("files") != ["dist", "styles.css"] or vue_manifest.get("exports", {}).get("./styles.css") != "./styles.css":
        raise AssertionError("The semantic Vue control baseline must remain an explicit optional CSS export.")

    angular_manifest = by_name["@orbyss/program-kit-forms-angular"]
    if angular_manifest.get("dependencies") != {
        "@orbyss/program-kit-forms-contracts": "0.9.9-preview.1",
        "@orbyss/program-kit-forms-jsonforms-runtime": "0.9.9-preview.1",
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

    for manifest in manifests:
        if manifest["name"] == "@orbyss/program-kit-forms-monaco":
            continue
        dependencies = {
            dependency
            for section in ("dependencies", "devDependencies", "peerDependencies")
            for dependency in manifest.get(section, {})
        }
        if any("monaco" in dependency.lower() for dependency in dependencies):
            raise AssertionError(f"Monaco leaked outside its optional adapter: {manifest['name']}")

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
    monaco_lock = lock.get("packages", {}).get("node_modules/monaco-editor", {})
    if monaco_lock.get("version") != "0.56.0":
        raise AssertionError("The optional Monaco adapter must resolve its exact governed peer version.")

    run(["test", "--ignore-scripts", "--no-audit", "--no-fund"])
    angular_output = (WORKSPACE / "packages/forms-angular/dist/index.js").read_text(encoding="utf-8")
    if "ɵɵngDeclareComponent" not in angular_output or 'version: "22.1.5"' not in angular_output:
        raise AssertionError("The Angular package was not partial-compiled by the exact Angular compiler.")
    run(["pack", "--workspaces", "--dry-run", "--ignore-scripts", "--no-audit", "--no-fund"])
    print("Forms frontend contracts, theme slots/tokens, JSON Forms runtime, AJV parity, renderer/actions, React/Vue schema modeler UI, searchable lookups, localization management, React/Vue/Angular bindings, wizard state, CodeMirror default, and isolated Monaco adapter passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
