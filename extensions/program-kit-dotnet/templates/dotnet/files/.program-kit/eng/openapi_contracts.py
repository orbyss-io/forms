from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import oasdiff_cli


HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def configure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_document(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"PKO001 generated OpenAPI document is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict) or not isinstance(value.get("openapi"), str):
        raise ValueError(f"PKO002 generated document is not an OpenAPI JSON object: {path}")
    return value


def validate_operation_identity(document: dict) -> None:
    identities: dict[str, str] = {}
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise ValueError("PKO003 OpenAPI paths must be an object.")
    for route, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            identity = operation.get("operationId")
            location = f"{method.upper()} {route}"
            if not isinstance(identity, str) or not identity.strip():
                raise ValueError(f"PKO004 operationId is required for deterministic identity: {location}")
            previous = identities.setdefault(identity, location)
            if previous != location:
                raise ValueError(f"PKO005 duplicate operationId '{identity}' at {previous} and {location}")


def check_tool(command: str, expected: str) -> None:
    oasdiff_cli.require(command, Path.cwd(), expected)


def approved(path: Path | None, baseline_hash: str, current_hash: str, version: str) -> bool:
    if path is None or not path.is_file():
        return False
    value = json.loads(path.read_text(encoding="utf-8"))
    return (
        isinstance(value, dict)
        and value.get("baselineSha256") == baseline_hash
        and value.get("revisionSha256") == current_hash
        and value.get("oasdiffVersion") == version
        and isinstance(value.get("approvedBy"), str)
        and bool(value["approvedBy"].strip())
    )


def main() -> int:
    configure_utf8()
    parser = argparse.ArgumentParser(description="Normalize and compatibility-check a Program Kit OpenAPI contract.")
    parser.add_argument("--generated", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--approval", default="")
    parser.add_argument("--oasdiff", default="oasdiff")
    parser.add_argument("--oasdiff-version", required=True)
    parser.add_argument("--initialize-baseline", action="store_true")
    parser.add_argument("--write-generated", action="store_true")
    args = parser.parse_args()
    try:
        generated = Path(args.generated).resolve()
        artifact = Path(args.artifact).resolve()
        baseline = Path(args.baseline).resolve()
        approval = Path(args.approval).resolve() if args.approval else None
        document = load_document(generated)
        validate_operation_identity(document)
        normalized = canonical_bytes(document)
        artifact.parent.mkdir(parents=True, exist_ok=True)

        if not artifact.is_file() or artifact.read_bytes() != normalized:
            if not args.write_generated:
                raise ValueError(
                    f"PKO008 generated OpenAPI output is stale: {artifact}. "
                    "Invoke .program-kit/eng/Build.ps1 with -UpdateOpenApiArtifact after reviewing the revision."
                )
            artifact.write_bytes(normalized)

        if not baseline.is_file():
            if not args.initialize_baseline:
                raise ValueError(
                    "PKO009 compatibility baseline is missing. Review the first contract and invoke once with "
                    "-InitializeOpenApiBaseline."
                )
            baseline.parent.mkdir(parents=True, exist_ok=True)
            baseline.write_bytes(normalized)
            print(f"created OpenAPI baseline {baseline}")
            return 0

        check_tool(args.oasdiff, args.oasdiff_version)
        result = subprocess.run(
            [args.oasdiff, "breaking", str(baseline), str(artifact), "--format", "json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode not in (0, 1):
            raise ValueError(f"PKO010 oasdiff failed ({result.returncode}): {(result.stderr or result.stdout).strip()}")
        if result.returncode == 1:
            baseline_hash = digest(baseline.read_bytes())
            current_hash = digest(normalized)
            if not approved(approval, baseline_hash, current_hash, args.oasdiff_version):
                raise ValueError(
                    "PKO011 unapproved breaking OpenAPI changes were detected. "
                    f"oasdiff output: {(result.stdout or result.stderr).strip()}"
                )
        print(f"OpenAPI contract is deterministic and compatible ({digest(normalized)})")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
