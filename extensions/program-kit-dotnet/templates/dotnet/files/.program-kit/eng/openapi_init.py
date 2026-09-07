from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from pathlib import Path


def relative_path(value: str, name: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not value:
        raise ValueError(f"PKO101 {name} must be a non-empty repository-relative path")
    return path.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a governed Program Kit OpenAPI contract.")
    parser.add_argument("--repository", default=".")
    parser.add_argument("--identity", required=True)
    parser.add_argument("--document-name", required=True)
    parser.add_argument("--shell", required=True)
    parser.add_argument("--feature", action="append", required=True)
    parser.add_argument("--application-directory", required=True)
    parser.add_argument("--application-script", default="typecheck")
    parser.add_argument("--application-tsconfig", required=True)
    args = parser.parse_args()
    try:
        repository = Path(args.repository).resolve()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.identity):
            raise ValueError("PKO101 identity must use letters, digits, dots, underscores, or hyphens")
        application = relative_path(args.application_directory, "application-directory")
        tsconfig = relative_path(args.application_tsconfig, "application-tsconfig")
        defaults = json.loads((repository / ".program-kit/openapi-defaults.json").read_text(encoding="utf-8"))
        tool_manifest = json.loads((repository / ".program-kit/eng/.config/dotnet-tools.json").read_text(encoding="utf-8"))
        exporter = tool_manifest["tools"]["programkit.openapi.exporter"]["version"]
        oasdiff = defaults["compatibility"]["version"]
        generator_default = defaults["typescriptGenerator"]
        generator_package = generator_default["package"]
        generator_version = generator_default["version"]
        if (
            generator_default.get("isolation") != "separate-package-and-lockfile"
            or not isinstance(generator_package, str)
            or not generator_package
            or not isinstance(generator_version, str)
            or not generator_version
        ):
            raise ValueError("PKO103 managed TypeScript generator defaults are invalid")
        contract_relative = f"contracts/openapi/{args.identity}.contract.json"
        contract_path = repository / contract_relative
        if contract_path.exists():
            raise ValueError(f"PKO102 contract already exists: {contract_relative}")
        registry_path = repository / ".program-kit/openapi-contracts.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        contracts = registry.get("contracts")
        if registry.get("schemaVersion") != 1 or not isinstance(contracts, list):
            raise ValueError("PKO103 OpenAPI registry must use schemaVersion 1 and a contracts array")
        if contract_relative in contracts:
            raise ValueError(f"PKO102 registry already contains {contract_relative}")
        generator = f"tools/openapi/{args.identity}"
        generator_package_relative = f"{generator}/package.json"
        generator_package_path = repository / generator_package_relative
        if generator_package_path.exists():
            raise ValueError(f"PKO102 generator package already exists: {generator_package_relative}")
        generated_types = f"{generator}/generated/types.ts"
        generator_input = posixpath.relpath(
            f"contracts/openapi/{args.identity}.json", generator
        )
        contract = {
            "schemaVersion": 1,
            "identity": args.identity,
            "documentName": args.document_name,
            "shell": args.shell,
            "producer": {"kind": "ProgramKit.OpenApi.Exporter", "version": exporter},
            "features": list(dict.fromkeys(args.feature)),
            "packageClosure": "artifacts/runnable-host/packages",
            "rawDocument": f"artifacts/openapi/{args.identity}.raw.json",
            "artifact": f"contracts/openapi/{args.identity}.json",
            "baseline": f"contracts/openapi/{args.identity}.baseline.json",
            "compatibility": {
                "oasdiffVersion": oasdiff,
                "approval": f"contracts/openapi/{args.identity}.breaking-change.json",
            },
            "generator": {
                "directory": generator,
                "packageJson": generator_package_relative,
                "lockFile": f"{generator}/package-lock.json",
                "script": "generate",
                "generatedTypes": generated_types,
            },
            "application": {
                "directory": application,
                "packageJson": f"{application}/package.json",
                "lockFile": f"{application}/package-lock.json",
                "script": args.application_script,
                "tsconfig": tsconfig,
            },
        }
        package = {
            "name": f"program-kit-openapi-{args.identity.lower().replace('_', '-')}",
            "version": "1.0.0",
            "private": True,
            "type": "module",
            "scripts": {
                "generate": f"openapi-typescript {generator_input} --output generated/types.ts"
            },
            "devDependencies": {generator_package: generator_version},
        }
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8", newline="\n")
        generator_package_path.parent.mkdir(parents=True, exist_ok=True)
        generator_package_path.write_text(
            json.dumps(package, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        registry["contracts"] = contracts + [contract_relative]
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"Initialized {contract_relative} with managed exporter {exporter} and oasdiff {oasdiff}.")
        print(f"Created isolated {generator_package}@{generator_version} package at {generator_package_relative}.")
        print(
            "After resolving the managed toolchain, create its lockfile with: "
            f"python .program-kit/eng/js_toolchain.py --repository . npm -- --prefix {generator} "
            "install --package-lock-only --ignore-scripts --strict-peer-deps --engine-strict"
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
