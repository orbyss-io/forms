from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "extensions/program-kit-governance/scripts"))
sys.path.insert(0, str(ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/eng/program-kit"))
import ui_profile
import js_toolchain


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help="Restore the isolated pinned npm graph with scripts disabled")
    parser.add_argument("--install-browser", action="store_true", help="Provision pinned Chromium, Firefox, WebKit and Linux system dependencies")
    args = parser.parse_args()
    fixture = ROOT / "artifacts/ui-browser"
    fixture.mkdir(parents=True, exist_ok=True)
    if not (fixture / ".program-kit/ui/profile.json").exists():
        ui_profile.execute(fixture, "init")
    ui_profile.execute(fixture, "build")
    ui_profile.execute(fixture, "check")
    package_root = fixture / ui_profile.OUTPUT / "acceptance/tests"
    package = json.loads((package_root / "package.json").read_text())
    node, _ = js_toolchain.resolve_node(ROOT, package["engines"]["node"], "node", "auto")
    if node is None:
        raise ValueError(f"Install the approved Node {package['engines']['node']} runtime first")
    npm, _ = js_toolchain.resolve_npm(ROOT, node, package["engines"]["npm"], "npm")
    if npm is None:
        raise ValueError(f"Install the approved npm {package['engines']['npm']} toolchain first")
    cache = js_toolchain.require_writable_cache(ROOT / "artifacts/ui-npm-cache")
    environment, trust, _ = js_toolchain.trust_environment(ROOT, cache)
    environment["PATH"] = str(node.parent) + os.pathsep + environment.get("PATH", "")
    def run(command: list[str], timeout: int = 300) -> None:
        result = subprocess.run(command, cwd=package_root, env=environment, capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            raise AssertionError(result.stdout + "\n" + result.stderr)
        print(result.stdout.strip())
    if args.install:
        run(npm + ["ci", "--ignore-scripts", "--no-audit", "--no-fund", "--strict-ssl=true", "--fetch-retries=0", "--fetch-timeout=30000"])
    if args.install_browser:
        command = [str(node), str(package_root / "node_modules/playwright/cli.js"), "install", "chromium", "firefox", "webkit"]
        if sys.platform.startswith("linux"):
            command.append("--with-deps")
        run(command)
    run([str(node), "--test", "analytics.test.mjs"])
    run(npm + ["exec", "--no", "--", "tailwindcss", "-i", "tailwind-input.css", "-o", "../tailwind-compiled.css", "--minify"])
    compiled = (package_root.parent / "tailwind-compiled.css").read_text(encoding="utf-8")
    if ".bg-primary" not in compiled or "var(--pk-primary)" not in compiled or ".text-on-primary" not in compiled:
        raise AssertionError("Tailwind did not compile the semantic-token bridge")
    print("Pinned Tailwind semantic-token compilation passed.")
    run([str(node), "browser.mjs"])
    (fixture / "toolchain-evidence.json").write_text(json.dumps({"node": package["engines"]["node"], "npm": package["engines"]["npm"],
        "trust": trust, "scriptsEnabled": False, "lockSha256": ui_profile.digest((package_root / "package-lock.json").read_bytes())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
