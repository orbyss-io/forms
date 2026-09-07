from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def configure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"PKN001 npm candidate manifest must be a JSON object: {path}")
    for collection in ("dependencies", "devDependencies", "optionalDependencies"):
        entries = value.get(collection, {})
        if not isinstance(entries, dict) or not all(
            isinstance(name, str) and isinstance(version, str)
            for name, version in entries.items()
        ):
            raise ValueError(f"PKN001 {collection} must be an object of package/version strings")
    return value


def write_evidence(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def resolve(
    package_json: Path,
    repository: Path,
    toolchain_evidence: Path,
    npm_command: str,
    evidence: Path,
    timeout: int,
) -> None:
    manifest = load_manifest(package_json)
    candidate = {
        "name": manifest.get("name", "program-kit-dependency-candidate"),
        "version": manifest.get("version", "0.0.0"),
        "private": True,
    }
    for collection in ("dependencies", "devDependencies", "optionalDependencies"):
        if manifest.get(collection):
            candidate[collection] = manifest[collection]
    with tempfile.TemporaryDirectory(prefix="program-kit-npm-graph-") as value:
        workspace = Path(value)
        candidate_path = workspace / "package.json"
        candidate_path.write_text(
            json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        arguments = [
            "install",
            "--package-lock-only",
            "--ignore-scripts",
            "--strict-peer-deps",
            "--engine-strict",
            "--no-audit",
            "--no-fund",
        ]
        environment = None
        if npm_command:
            command = [npm_command, "--strict-ssl=true", *arguments]
        else:
            wrapper = repository / ".program-kit/eng/js_toolchain.py"
            if not wrapper.is_file():
                raise ValueError(
                    "PKN003 managed JavaScript runtime wrapper is missing; synchronize the .NET profile first."
                )
            toolchain = json.loads(toolchain_evidence.read_text(encoding="utf-8"))
            npm = toolchain.get("commands", {}).get("npm")
            if not isinstance(npm, list) or not npm:
                raise ValueError("PKN003 exact npm command evidence is missing; run toolchain.py first.")
            command = [*npm, "--strict-ssl=true", *arguments]
            invocation = [
                sys.executable,
                str(wrapper),
                "--repository",
                str(repository),
                "--evidence",
                str(toolchain_evidence),
                "--timeout-seconds",
                str(timeout),
                "npm",
                "--",
                *arguments,
            ]
        result = subprocess.run(
            command if npm_command else invocation,
            cwd=workspace,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        lockfile = workspace / "package-lock.json"
        payload = {
            "schemaVersion": 1,
            "packageJson": str(package_json.resolve()),
            "packageJsonSha256": digest(package_json),
            "command": command,
            "satisfied": result.returncode == 0 and lockfile.is_file(),
        }
        if lockfile.is_file():
            payload["lockfileSha256"] = digest(lockfile)
        write_evidence(evidence, payload)
        if result.returncode != 0 or not lockfile.is_file():
            detail = (result.stdout or "").strip()
            if len(detail) > 2000:
                detail = detail[-2000:]
            raise ValueError(
                "PKN002 exact npm graph failed strict peer/engine/platform resolution; choose "
                "compatible versions or isolate the generator toolchain. Force and legacy-peer "
                f"bypasses are forbidden. npm stdout: {detail or 'see the visible stderr and repository npm cache logs'}"
            )
    print(f"PKN000 exact npm dependency graph resolved with strict peers: {evidence}")


def main() -> int:
    configure_utf8()
    parser = argparse.ArgumentParser(
        description="Resolve an exact npm candidate graph in isolation before architecture acceptance."
    )
    parser.add_argument("--package-json", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--repository", default=".")
    parser.add_argument("--toolchain-evidence", default=".program-kit/evidence/toolchain.json")
    parser.add_argument("--npm-command", default="", help=argparse.SUPPRESS)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    try:
        if args.npm_command and shutil.which(args.npm_command) is None and not Path(args.npm_command).is_file():
            raise ValueError(f"PKN003 npm command is unavailable: {args.npm_command}")
        if args.timeout_seconds < 1:
            raise ValueError("PKN004 timeout must be at least one second")
        repository = Path(args.repository).resolve()
        toolchain_evidence = Path(args.toolchain_evidence)
        if not toolchain_evidence.is_absolute():
            toolchain_evidence = repository / toolchain_evidence
        resolve(
            Path(args.package_json).resolve(),
            repository,
            toolchain_evidence,
            args.npm_command,
            Path(args.evidence).resolve(),
            args.timeout_seconds,
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
