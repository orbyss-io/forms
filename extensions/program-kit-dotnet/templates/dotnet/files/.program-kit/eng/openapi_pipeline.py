from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

import js_toolchain
import shell_composition
import runtime_closure
from program_kit_version import PROGRAM_KIT_VERSION


REQUIRED = {
    "schemaVersion",
    "identity",
    "documentName",
    "shell",
    "producer",
    "features",
    "packageClosure",
    "rawDocument",
    "artifact",
    "baseline",
    "compatibility",
    "generator",
    "application",
}


def configure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(repository: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"PKO201 {field} must be a non-empty repository-relative path.")
    pure = PurePosixPath(value.replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts or (pure.parts and ":" in pure.parts[0]):
        raise ValueError(f"PKO201 {field} must be a repository-relative path without traversal: {value!r}")
    resolved = (repository / Path(*pure.parts)).resolve()
    try:
        resolved.relative_to(repository)
    except ValueError as error:
        raise ValueError(f"PKO201 {field} escapes the repository: {value!r}") from error
    return resolved


def load_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"PKO202 cannot load {label} {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"PKO202 {label} must be a JSON object: {path}")
    return value


def validate_stage(repository: Path, value: object, name: str, output: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"PKO203 {name} must be an object.")
    required = {"directory", "packageJson", "lockFile", "script", output}
    missing = sorted(required - set(value))
    if missing:
        raise ValueError(f"PKO203 {name} is missing: {', '.join(missing)}.")
    script = value.get("script")
    if not isinstance(script, str) or not script or any(character.isspace() for character in script):
        raise ValueError(f"PKO203 {name}.script must be one npm script name.")
    resolved = {
        "directory": relative_path(repository, value["directory"], f"{name}.directory"),
        "packageJson": relative_path(repository, value["packageJson"], f"{name}.packageJson"),
        "lockFile": relative_path(repository, value["lockFile"], f"{name}.lockFile"),
        "script": script,
        output: relative_path(repository, value[output], f"{name}.{output}"),
    }
    directory = resolved["directory"]
    assert isinstance(directory, Path)
    for field in ("packageJson", "lockFile"):
        candidate = resolved[field]
        assert isinstance(candidate, Path)
        try:
            candidate.relative_to(directory)
        except ValueError as error:
            raise ValueError(f"PKO203 {name}.{field} must stay inside {name}.directory.") from error
    return resolved


def validate_contract(
    repository: Path, path: Path, exporter_version: str, oasdiff_version: str
) -> tuple[dict, dict]:
    value = load_json(path, "OpenAPI contract")
    missing = sorted(REQUIRED - set(value))
    if missing or value.get("schemaVersion") != 1:
        raise ValueError(
            f"PKO204 unsupported or incomplete OpenAPI contract {path}; missing: {', '.join(missing)}."
        )
    producer = value.get("producer")
    if not isinstance(producer, dict) or producer.get("kind") != "ProgramKit.OpenApi.Exporter":
        raise ValueError("PKO204 producer.kind must be ProgramKit.OpenApi.Exporter.")
    if producer.get("version") != exporter_version:
        raise ValueError(
            f"PKO204 contract exporter version must equal managed tool pin {exporter_version!r}."
        )
    features = value.get("features")
    if (
        not isinstance(features, list)
        or not features
        or any(not isinstance(item, str) or not item for item in features)
        or len(features) != len(set(features))
    ):
        raise ValueError("PKO204 features must be a non-empty array of unique identities.")
    if str(value.get("packageClosure", "")).replace("\\", "/") != "artifacts/runnable-host/packages":
        raise ValueError(
            "PKO204 packageClosure must be the validated artifacts/runnable-host/packages closure."
        )
    compatibility = value.get("compatibility")
    if not isinstance(compatibility, dict) or not isinstance(compatibility.get("oasdiffVersion"), str):
        raise ValueError("PKO204 compatibility must pin oasdiffVersion and an approval path.")
    if compatibility.get("oasdiffVersion") != oasdiff_version:
        raise ValueError(
            f"PKO204 contract oasdiff version must equal managed tool pin {oasdiff_version!r}."
        )
    resolved = {
        "packages": relative_path(repository, value["packageClosure"], "packageClosure"),
        "raw": relative_path(repository, value["rawDocument"], "rawDocument"),
        "artifact": relative_path(repository, value["artifact"], "artifact"),
        "baseline": relative_path(repository, value["baseline"], "baseline"),
        "approval": relative_path(repository, compatibility.get("approval"), "compatibility.approval"),
        "generator": validate_stage(repository, value.get("generator"), "generator", "generatedTypes"),
        "application": validate_stage(repository, value.get("application"), "application", "tsconfig"),
    }
    distinct = [resolved[name] for name in ("raw", "artifact", "baseline")]
    if len(set(distinct)) != len(distinct):
        raise ValueError("PKO204 rawDocument, artifact, and baseline must use distinct paths.")
    return value, resolved


def run(
    command: list[str],
    cwd: Path,
    label: str,
    environment: dict[str, str] | None = None,
    timeout: int = 600,
) -> None:
    result = subprocess.run(command, cwd=cwd, env=environment, check=False, timeout=timeout)
    if result.returncode != 0:
        raise ValueError(f"PKO205 {label} failed with exit code {result.returncode}.")


def repository_nuget_environment(repository: Path) -> dict[str, str]:
    cache = repository / ".program-kit/cache"
    paths = {
        "NUGET_PACKAGES": cache / "nuget/packages",
        "NUGET_HTTP_CACHE_PATH": cache / "nuget/http",
        "NUGET_SCRATCH": cache / "nuget/scratch",
        "NUGET_PLUGINS_CACHE_PATH": cache / "nuget/plugins",
        "DOTNET_CLI_HOME": cache / "dotnet-home",
    }
    environment = os.environ.copy()
    for name, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        environment[name] = str(path)
    environment["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    environment["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
    environment["DOTNET_NOLOGO"] = "1"
    if os.name == "nt":
        roaming = cache / "profile/roaming"
        local = cache / "profile/local"
        roaming.mkdir(parents=True, exist_ok=True)
        local.mkdir(parents=True, exist_ok=True)
        environment["APPDATA"] = str(roaming)
        environment["LOCALAPPDATA"] = str(local)
    return environment


def ensure_openapi_toolchain(
    repository: Path, evidence: Path, environment: dict[str, str]
) -> None:
    command = [
        sys.executable,
        str(repository / ".program-kit/eng/toolchain.py"),
        "--repository",
        str(repository),
        "--evidence",
        str(evidence),
        "--include-openapi",
    ]
    result = subprocess.run(
        command,
        cwd=repository,
        env=environment,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        raise ValueError(
            "PKO210 exact OpenAPI toolchain evidence could not be renewed without system changes or "
            "downloads. Stage the reviewed pinned oasdiff binary with toolchain.py --include-openapi "
            "--remediate and explicit approval, then rerun the pipeline."
        )


def prepare_openapi_toolchain(repository: Path, evidence: Path) -> None:
    # Resolve user-managed SDK/Node/npm/oasdiff paths before NuGet isolation changes the
    # Windows profile roots used by version managers such as fnm. Later executions use
    # the absolute, re-verified commands recorded in the evidence file.
    ensure_openapi_toolchain(repository, evidence, os.environ.copy())
    js_toolchain.context(repository, evidence)


def restore_exporter(
    dotnet: str, manifest: Path, repository: Path, environment: dict[str, str]
) -> None:
    config = repository / "NuGet.config"
    if not config.is_file():
        raise ValueError(f"PKO211 reviewed repository NuGet.config is missing: {config}")
    run(
        [
            dotnet,
            "tool",
            "restore",
            "--tool-manifest",
            str(manifest),
            "--configfile",
            str(config),
            "--disable-parallel",
        ],
        repository,
        "managed OpenAPI exporter restore",
        environment,
    )


def tool_version(repository: Path) -> tuple[Path, str]:
    manifest = repository / ".program-kit/eng/.config/dotnet-tools.json"
    value = load_json(manifest, "managed .NET tool manifest")
    tools = value.get("tools")
    entry = tools.get("programkit.openapi.exporter") if isinstance(tools, dict) else None
    version = entry.get("version") if isinstance(entry, dict) else None
    if not isinstance(version, str) or not version:
        raise ValueError("PKO206 managed tool manifest does not pin ProgramKit.OpenApi.Exporter.")
    return manifest, version


def npm_stage(
    repository: Path,
    evidence: Path,
    stage: dict[str, object],
    name: str,
) -> dict[str, str]:
    directory = stage["directory"]
    package_json = stage["packageJson"]
    lock_file = stage["lockFile"]
    assert isinstance(directory, Path) and isinstance(package_json, Path) and isinstance(lock_file, Path)
    for path, label in ((package_json, "package.json"), (lock_file, "package lock")):
        if not path.is_file():
            raise ValueError(f"PKO207 {name} {label} is missing: {path}")
    installed = js_toolchain.run_npm(
        repository,
        evidence,
        ["ci", "--ignore-scripts", "--strict-peer-deps", "--engine-strict"],
        directory,
        300,
    )
    if installed.returncode != 0:
        raise ValueError(f"PKO205 {name} npm ci failed with exit code {installed.returncode}.")
    generated = js_toolchain.run_npm(
        repository,
        evidence,
        ["run", str(stage["script"])],
        directory,
        300,
    )
    if generated.returncode != 0:
        raise ValueError(f"PKO205 {name} npm script failed with exit code {generated.returncode}.")
    output_name = "generatedTypes" if name == "generator" else "tsconfig"
    output = stage[output_name]
    assert isinstance(output, Path)
    if not output.is_file():
        raise ValueError(f"PKO207 {name} did not produce or retain {output_name}: {output}")
    return {
        "packageJsonSha256": sha256(package_json),
        "lockFileSha256": sha256(lock_file),
        f"{output_name}Sha256": sha256(output),
    }


def execute_contract(
    repository: Path,
    contract_path: Path,
    contract: dict,
    paths: dict,
    exporter: Path | None,
    dotnet: str,
    toolchain_evidence: Path,
    oasdiff: str,
    nuget_environment: dict[str, str],
    initialize: bool,
    update: bool,
    effective_shells: Path,
) -> dict:
    identity = str(contract["identity"])
    staged_root = paths["packages"].parent
    runtime_closure.validate(
        repository,
        staged_root,
        repository / runtime_closure.EVIDENCE,
        PROGRAM_KIT_VERSION,
    )
    export_evidence = repository / f".program-kit/evidence/openapi/{identity}-export.json"
    exporter_command = [dotnet, str(exporter)] if exporter else [
        dotnet, "tool", "run", "programkit-openapi-export", "--"
    ]
    run(
        exporter_command
        + [
            "--repository", str(repository),
            "--packages", str(paths["packages"]),
            "--shells", str(effective_shells),
            "--hostsettings", str(staged_root / "hostsettings.json"),
            "--contract", str(contract_path),
            "--output", str(paths["raw"]),
            "--evidence", str(export_evidence),
        ],
        repository / ".program-kit/eng" if exporter is None else repository,
        f"OpenAPI export for {identity}",
        nuget_environment,
    )
    normalizer = repository / ".program-kit/eng/openapi_contracts.py"
    normalize_command = [
        sys.executable,
        str(normalizer),
        "--generated", str(paths["raw"]),
        "--artifact", str(paths["artifact"]),
        "--baseline", str(paths["baseline"]),
        "--approval", str(paths["approval"]),
        "--oasdiff", oasdiff,
        "--oasdiff-version", str(contract["compatibility"]["oasdiffVersion"]),
    ]
    if initialize:
        normalize_command.extend(["--initialize-baseline", "--write-generated"])
    elif update:
        normalize_command.append("--write-generated")
    run(normalize_command, repository, f"OpenAPI normalization for {identity}")
    generator = npm_stage(repository, toolchain_evidence, paths["generator"], "generator")
    application = npm_stage(repository, toolchain_evidence, paths["application"], "application")
    return {
        "identity": identity,
        "contractSha256": sha256(contract_path),
        "exportEvidenceSha256": sha256(export_evidence),
        "rawDocumentSha256": sha256(paths["raw"]),
        "artifactSha256": sha256(paths["artifact"]),
        "baselineSha256": sha256(paths["baseline"]),
        "generator": generator,
        "application": application,
    }


def main() -> int:
    configure_utf8()
    parser = argparse.ArgumentParser(description="Run the producer-first Program Kit OpenAPI contract pipeline.")
    parser.add_argument("--repository", default=".")
    parser.add_argument("--registry", default=".program-kit/openapi-contracts.json")
    parser.add_argument("--exporter", default="", help=argparse.SUPPRESS)
    parser.add_argument("--initialize-baselines", action="store_true")
    parser.add_argument("--update-artifacts", action="store_true")
    args = parser.parse_args()
    try:
        repository = Path(args.repository).resolve()
        registry_path = relative_path(repository, args.registry, "registry")
        registry = load_json(registry_path, "OpenAPI registry")
        contracts = registry.get("contracts")
        if registry.get("schemaVersion") != 1 or not isinstance(contracts, list):
            raise ValueError("PKO208 OpenAPI registry must use schemaVersion 1 and a contracts array.")
        if not contracts:
            print("OpenAPI contract pipeline is not configured; no contracts are registered.")
            return 0
        manifest, version = tool_version(repository)
        oasdiff_version = (repository / ".oasdiff-version").read_text(encoding="utf-8").strip().removeprefix("v")
        if not oasdiff_version:
            raise ValueError("PKO206 managed .oasdiff-version does not pin oasdiff.")
        toolchain_evidence = repository / ".program-kit/evidence/toolchain.json"
        prepare_openapi_toolchain(repository, toolchain_evidence)
        nuget_environment = repository_nuget_environment(repository)
        toolchain = load_json(toolchain_evidence, "toolchain evidence")
        commands = toolchain.get("commands", {})
        dotnet_values = commands.get("dotnet") if isinstance(commands, dict) else None
        if not isinstance(dotnet_values, list) or len(dotnet_values) != 1 or not Path(dotnet_values[0]).is_file():
            raise ValueError("PKO210 exact dotnet command evidence is missing; run toolchain.py first.")
        dotnet = str(dotnet_values[0])
        oasdiff_values = commands.get("oasdiff") if isinstance(commands, dict) else None
        if not isinstance(oasdiff_values, list) or len(oasdiff_values) != 1 or not Path(oasdiff_values[0]).is_file():
            raise ValueError("PKO210 exact oasdiff command evidence is missing; run toolchain.py --include-openapi first.")
        oasdiff = str(oasdiff_values[0])
        exporter = Path(args.exporter).resolve() if args.exporter else None
        if exporter is not None and not exporter.is_file():
            raise ValueError(f"PKO209 exporter test override is missing: {exporter}")
        if exporter is None:
            restore_exporter(dotnet, manifest, repository, nuget_environment)
        effective_shells = repository / ".program-kit/cache/openapi/effective-shells.json"
        shell_composition.write(repository / "artifacts/runnable-host", effective_shells)
        evidence = []
        seen: set[str] = set()
        for item in contracts:
            contract_path = relative_path(repository, item, "registry contract")
            contract, paths = validate_contract(repository, contract_path, version, oasdiff_version)
            identity = str(contract["identity"])
            if identity in seen:
                raise ValueError(f"PKO208 duplicate OpenAPI contract identity: {identity}")
            seen.add(identity)
            evidence.append(
                execute_contract(
                    repository,
                    contract_path,
                    contract,
                    paths,
                    exporter,
                    dotnet,
                    toolchain_evidence,
                    oasdiff,
                    nuget_environment,
                    args.initialize_baselines,
                    args.update_artifacts,
                    effective_shells,
                )
            )
        evidence_path = repository / ".program-kit/evidence/openapi/pipeline.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "producer": {"kind": "ProgramKit.OpenApi.Exporter", "version": version},
                    "registrySha256": sha256(registry_path),
                    "contracts": evidence,
                    "satisfied": True,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"OpenAPI producer, compatibility, generation, and application compile pipeline passed ({evidence_path}).")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
