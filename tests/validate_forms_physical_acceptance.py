from __future__ import annotations

import http.client
import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tests/serve_forms_physical_acceptance.py"
PREFIX = "PROGRAM_KIT_PHYSICAL_ACCEPTANCE="


def request(port: int, path: str) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request("GET", path)
    response = connection.getresponse()
    body = response.read()
    headers = {key.casefold(): value for key, value in response.getheaders()}
    connection.close()
    return response.status, headers, body


def main() -> int:
    required = [
        ROOT / "scripts/Start-FormsPhysicalAcceptance.ps1",
        ROOT / "docs/forms-physical-acceptance.md",
        ROOT / "docs/templates/forms-physical-acceptance-report.md",
    ]
    for path in required:
        if not path.is_file():
            raise AssertionError(f"Missing physical-acceptance asset: {path.relative_to(ROOT)}")

    process = subprocess.Popen(
        [sys.executable, str(SERVER), "--host", "127.0.0.1", "--port", "0"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output: list[str] = []
    try:
        deadline = time.monotonic() + 300
        descriptor = None
        lines: queue.Queue[str | None] = queue.Queue()

        def read_output() -> None:
            if process.stdout is not None:
                for captured in process.stdout:
                    lines.put(captured)
            lines.put(None)

        threading.Thread(target=read_output, daemon=True).start()
        while time.monotonic() < deadline:
            try:
                line = lines.get(timeout=min(1, max(0.01, deadline - time.monotonic())))
            except queue.Empty:
                if process.poll() is not None:
                    break
                continue
            if line is None:
                break
            output.append(line)
            if line.startswith(PREFIX):
                descriptor = json.loads(line[len(PREFIX) :])
                break
        if descriptor is None:
            raise AssertionError("Physical-acceptance server did not start:\n" + "".join(output))
        if descriptor["schema"] != "urn:program-kit:forms:physical-acceptance-server:1":
            raise AssertionError("Physical-acceptance server descriptor schema changed unexpectedly.")
        port = descriptor["port"]
        status, headers, body = request(port, "/")
        if status != 200 or b'<div id="root"></div>' not in body:
            raise AssertionError("Physical-acceptance index was not served.")
        expected_headers = {
            "cache-control": "no-store",
            "x-content-type-options": "nosniff",
            "referrer-policy": "no-referrer",
            "permissions-policy": "camera=(), microphone=(), geolocation=()",
        }
        for key, value in expected_headers.items():
            if headers.get(key) != value:
                raise AssertionError(f"Missing or invalid {key} response header.")
        csp = headers.get("content-security-policy", "")
        for directive in ("default-src 'none'", "script-src 'self'", "form-action 'self'"):
            if directive not in csp:
                raise AssertionError(f"Physical-acceptance CSP is missing {directive}.")
        unavailable = request(port, "/package.json")
        traversal = request(port, "/../VERSION")
        if unavailable[0] != 404 or traversal[0] != 404:
            raise AssertionError("Physical-acceptance server exposed a file outside its allowlist.")
        if unavailable[1].get("content-security-policy") != csp:
            raise AssertionError("Physical-acceptance error responses lost their security headers.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    print("Forms engine browser-fixture launcher, evidence, CSP, and file-isolation contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
