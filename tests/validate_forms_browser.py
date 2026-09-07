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
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--install-browser", action="store_true")
    parser.add_argument("--engines", default="chromium,firefox,webkit")
    args = parser.parse_args()
    package = json.loads((WORKSPACE / "package.json").read_text(encoding="utf-8"))
    node, _ = js_toolchain.resolve_node(ROOT, package["engines"]["node"], "node", "auto")
    if node is None:
        raise AssertionError(f"Install the approved Node {package['engines']['node']} runtime first.")
    npm, _ = js_toolchain.resolve_npm(ROOT, node, package["engines"]["npm"], "npm")
    if npm is None:
        raise AssertionError(f"Install the approved npm {package['engines']['npm']} toolchain first.")
    cache = js_toolchain.require_writable_cache(ROOT / "artifacts/forms-npm-cache")
    environment, trust, _ = js_toolchain.trust_environment(ROOT, cache)
    environment["PATH"] = str(node.parent) + os.pathsep + environment.get("PATH", "")
    environment["PYTHONUTF8"] = "1"

    def run(command: list[str], timeout: int = 300) -> None:
        result = subprocess.run(
            command,
            cwd=WORKSPACE,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if result.returncode != 0:
            raise AssertionError(result.stdout + "\n" + result.stderr)
        if result.stdout.strip():
            print(result.stdout.strip())

    if args.install:
        run(npm + ["ci", "--ignore-scripts", "--no-audit", "--no-fund", "--strict-ssl=true", "--fetch-retries=0", "--fetch-timeout=30000"])
    if args.install_browser:
        command = [str(node), str(WORKSPACE / "node_modules/playwright/cli.js"), "install", *args.engines.split(",")]
        if sys.platform.startswith("linux"):
            command.append("--with-deps")
        run(command)
    run(npm + ["run", "build", "--ignore-scripts", "--no-audit", "--no-fund"])
    run([str(node), "tests/forms-browser/build.mjs"])
    run([str(node), "tests/forms-browser/browser.mjs", f"--engines={args.engines}"])
    evidence = json.loads((ROOT / "artifacts/forms-browser/build-evidence.json").read_text(encoding="utf-8"))
    if evidence != {
        "schema": "urn:orbyss:forms:browser-acceptance:1",
        "bytes": evidence["bytes"],
        "dynamicCodeGeneration": False,
        "sourceMaps": False,
    } or not isinstance(evidence["bytes"], int) or evidence["bytes"] <= 0:
        raise AssertionError("Forms browser build evidence is invalid.")
    print(f"Forms browser toolchain trust: {trust}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
