from __future__ import annotations

import argparse
import ipaddress
import json
import os
import socket
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src/typescript"
OUTPUT = ROOT / "artifacts/forms-browser"
TOOLCHAIN = ROOT / "eng"
sys.path.insert(0, str(TOOLCHAIN))
import js_toolchain


CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src 'self' data:; base-uri 'none'; form-action 'self'"
)
FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/build-evidence.json": ("build-evidence.json", "application/json; charset=utf-8"),
}


def run(command: list[str], environment: dict[str, str]) -> None:
    result = subprocess.run(
        command,
        cwd=WORKSPACE,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stdout + "\n" + result.stderr).strip())
    if result.stdout.strip():
        print(result.stdout.strip(), flush=True)


def build_fixture(install: bool) -> str:
    package = json.loads((WORKSPACE / "package.json").read_text(encoding="utf-8"))
    node, _ = js_toolchain.resolve_node(ROOT, package["engines"]["node"], "node", "auto")
    if node is None:
        raise RuntimeError(f"Install the approved Node {package['engines']['node']} runtime first.")
    npm, _ = js_toolchain.resolve_npm(ROOT, node, package["engines"]["npm"], "npm")
    if npm is None:
        raise RuntimeError(f"Install the approved npm {package['engines']['npm']} toolchain first.")
    cache = js_toolchain.require_writable_cache(ROOT / "artifacts/forms-npm-cache")
    environment, trust, _ = js_toolchain.trust_environment(ROOT, cache)
    environment["PATH"] = str(node.parent) + os.pathsep + environment.get("PATH", "")
    environment["PYTHONUTF8"] = "1"
    if install:
        run(
            npm
            + [
                "ci",
                "--ignore-scripts",
                "--no-audit",
                "--no-fund",
                "--strict-ssl=true",
                "--fetch-retries=0",
                "--fetch-timeout=30000",
            ],
            environment,
        )
    run(npm + ["run", "build", "--ignore-scripts", "--no-audit", "--no-fund"], environment)
    run([str(node), "tests/forms-browser/build.mjs"], environment)
    return trust


class AcceptanceHandler(BaseHTTPRequestHandler):
    server_version = "OrbyssPhysicalAcceptance/1"
    sys_version = ""

    def do_HEAD(self) -> None:
        self._serve(False)

    def do_GET(self) -> None:
        self._serve(True)

    def _serve(self, include_body: bool) -> None:
        raw_path = unquote(urlsplit(self.path).path)
        descriptor = FILES.get(raw_path)
        if descriptor is None:
            self.send_error(404)
            return
        filename, content_type = descriptor
        target = OUTPUT / filename
        if not target.is_file():
            self.send_error(503, "Acceptance fixture has not been built")
            return
        content = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if include_body:
            self.wfile.write(content)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}", flush=True)


def private_addresses() -> list[str]:
    candidates: set[str] = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 80))
            candidates.add(probe.getsockname()[0])
    except OSError:
        pass
    try:
        for result in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            candidates.add(result[4][0])
    except OSError:
        pass
    return sorted(
        address
        for address in candidates
        if ipaddress.ip_address(address).is_private and not ipaddress.ip_address(address).is_loopback
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the Orbyss Forms physical-acceptance showcase.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=4173, type=int)
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    trust = "not-applicable"
    if not args.no_build:
        trust = build_fixture(args.install)
    missing = [filename for filename, _ in FILES.values() if not (OUTPUT / filename).is_file()]
    if missing:
        raise RuntimeError(f"Acceptance fixture is incomplete: {', '.join(sorted(set(missing)))}")

    server = ThreadingHTTPServer((args.host, args.port), AcceptanceHandler)
    port = server.server_address[1]
    urls = [f"http://127.0.0.1:{port}/"]
    if args.host in {"0.0.0.0", "::"}:
        urls.extend(f"http://{address}:{port}/" for address in private_addresses())
    elif args.host not in {"127.0.0.1", "localhost"}:
        urls.append(f"http://{args.host}:{port}/")
    evidence = {
        "schema": "urn:orbyss:forms:physical-acceptance-server:1",
        "host": args.host,
        "port": port,
        "urls": list(dict.fromkeys(urls)),
        "toolchainTrust": trust,
    }
    print("ORBYSS_FORMS_PHYSICAL_ACCEPTANCE=" + json.dumps(evidence, separators=(",", ":")), flush=True)
    print("Press Ctrl+C to stop the physical-acceptance server.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
