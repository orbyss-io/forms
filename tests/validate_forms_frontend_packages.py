from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src/typescript"
sys.path.insert(0, str(ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/eng/program-kit"))
import js_toolchain


def run(command: list[str], cwd: Path, environment: dict[str, str], timeout: int = 240) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Command failed: {command}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def main() -> int:
    root_manifest = json.loads((WORKSPACE / "package.json").read_text(encoding="utf-8"))
    node, _ = js_toolchain.resolve_node(ROOT, root_manifest["engines"]["node"], "node", "auto")
    if node is None:
        raise AssertionError(f"Install the approved Node {root_manifest['engines']['node']} runtime first.")
    npm, _ = js_toolchain.resolve_npm(ROOT, node, root_manifest["engines"]["npm"], "npm")
    if npm is None:
        raise AssertionError(f"Install the approved npm {root_manifest['engines']['npm']} toolchain first.")
    cache = js_toolchain.require_writable_cache(ROOT / "artifacts/forms-npm-cache")
    environment, trust, _ = js_toolchain.trust_environment(ROOT, cache)
    environment["PATH"] = str(node.parent) + os.pathsep + environment.get("PATH", "")
    environment["PYTHONUTF8"] = "1"

    manifests = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((WORKSPACE / "packages").glob("*/package.json"))
    ]
    names = sorted(manifest["name"] for manifest in manifests)
    if len(names) != 23 or len(set(names)) != len(names):
        raise AssertionError("The clean frontend consumer requires exactly twenty-three unique packages.")

    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="forms-package-isolation-", dir=artifacts) as temporary:
        root = Path(temporary)
        packs = root / "packs"
        consumer = root / "consumer"
        packs.mkdir()
        consumer.mkdir()
        run(
            npm + ["pack", "--workspaces", "--pack-destination", str(packs), "--ignore-scripts"],
            WORKSPACE,
            environment,
        )
        archives = sorted(packs.glob("*.tgz"))
        if len(archives) != len(names):
            raise AssertionError(f"Expected {len(names)} frontend archives, found {len(archives)}.")

        packed_names: set[str] = set()
        for archive in archives:
            with tarfile.open(archive, "r:gz") as package:
                members = {member.name for member in package.getmembers() if member.isfile()}
                required = {"package/package.json", "package/dist/index.js", "package/dist/index.d.ts"}
                if not required.issubset(members):
                    raise AssertionError(f"Frontend archive {archive.name} is missing {sorted(required - members)}.")
                manifest_member = package.extractfile("package/package.json")
                if manifest_member is None:
                    raise AssertionError(f"Frontend archive {archive.name} has no readable manifest.")
                packed = json.loads(manifest_member.read().decode("utf-8"))
                packed_names.add(packed["name"])
                if packed["version"] != root_manifest["version"]:
                    raise AssertionError(f"Frontend archive {archive.name} has a divergent version.")
                for export_target in packed.get("exports", {}).values():
                    if isinstance(export_target, str) and export_target.endswith(".css"):
                        member = "package/" + export_target.removeprefix("./")
                        if member not in members:
                            raise AssertionError(f"Frontend archive {archive.name} omits exported stylesheet {export_target}.")
        if packed_names != set(names):
            raise AssertionError("Packed frontend identities do not match the workspace package set.")

        (consumer / "package.json").write_text(
            json.dumps({"name": "program-kit-clean-consumer", "private": True, "type": "module"}),
            encoding="utf-8",
        )
        install_arguments = [
            "install",
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
            "--strict-ssl=true",
            "--fetch-retries=0",
            "--fetch-timeout=30000",
            "--package-lock=false",
            "@jsonforms/core@3.8.0",
            "@jsonforms/angular@3.8.0",
            "@jsonforms/react@3.8.0",
            "@jsonforms/vue@3.8.0",
            "@angular/common@22.1.5",
            "@angular/core@22.1.5",
            "@angular/forms@22.1.5",
            "react@19.2.8",
            "react-dom@19.2.8",
            "rxjs@7.8.2",
            "vue@3.5.42",
            "monaco-editor@0.56.0",
            *(str(archive) for archive in archives),
        ]
        run(npm + install_arguments, consumer, environment)
        node_names = [name for name in names if name not in {
            "@orbyss/program-kit-forms-angular",
            "@orbyss/program-kit-forms-monaco",
        }]
        module_probe = (
            "const names=" + json.dumps(node_names) + ";"
            "for(const name of names){const value=await import(name);"
            "if(Object.keys(value).length===0)throw new Error(`No public exports: ${name}`);}" 
            "console.log(`Imported ${names.length} Program Kit frontend packages.`);"
        )
        imported = run([str(node), "--input-type=module", "--eval", module_probe], consumer, environment)
        if f"Imported {len(node_names)} Program Kit frontend packages." not in imported.stdout:
            raise AssertionError("The clean frontend consumer did not import every Node-loadable package.")

        angular_entry = consumer / "angular-entry.js"
        angular_entry.write_text(
            'import { ProgramKitJsonFormsAngularComponent } from "@orbyss/program-kit-forms-angular";\n'
            'console.log(ProgramKitJsonFormsAngularComponent);\n',
            encoding="utf-8",
        )
        esbuild = WORKSPACE / "node_modules" / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
        run([
            str(esbuild),
            str(angular_entry),
            "--bundle",
            "--platform=browser",
            "--format=esm",
            "--outfile=angular-bundle.js",
            "--external:@angular/*",
            "--external:@jsonforms/*",
            "--external:rxjs",
            "--log-level=error",
        ], consumer, environment)
        if not (consumer / "angular-bundle.js").is_file():
            raise AssertionError("The clean frontend consumer did not resolve the Angular package for browser bundling.")

        monaco_entry = consumer / "monaco-entry.js"
        monaco_entry.write_text(
            'import { monacoJsonEditorAdapter } from "@orbyss/program-kit-forms-monaco";\n'
            'console.log(monacoJsonEditorAdapter);\n',
            encoding="utf-8",
        )
        run([
            str(esbuild),
            str(monaco_entry),
            "--bundle",
            "--platform=browser",
            "--format=esm",
            "--outfile=monaco-bundle.js",
            "--external:monaco-editor",
            "--log-level=error",
        ], consumer, environment)
        if not (consumer / "monaco-bundle.js").is_file():
            raise AssertionError("The clean frontend consumer did not resolve the optional Monaco adapter for browser bundling.")

    print(f"Forms frontend clean pack/install/import isolation passed ({trust} toolchain).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
