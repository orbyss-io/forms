from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from openapi_upgrade_reconciliation import (
    ReconciliationError,
    apply as apply_openapi_reconciliation,
    describe as describe_openapi_reconciliation,
    discover as discover_openapi_reconciliation,
)


COMPONENTS = (
    ("bundle", Path("bundle.yml")),
    ("governance extension", Path("extensions/program-kit-governance/extension.yml")),
    (".NET extension", Path("extensions/program-kit-dotnet/extension.yml")),
    ("governance preset", Path("presets/program-kit-governance-preset/preset.yml")),
    ("bootstrap workflow", Path("workflows/program-kit-bootstrap/workflow.yml")),
)


class UpgradeError(ValueError):
    pass


def configure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def manifest_version(path: Path, label: str) -> str:
    if not path.is_file():
        raise UpgradeError(f"PKU101 {label} is missing: {path}")
    match = re.search(
        r"^\s{2}version:\s*[\"']?([^\"'#\s]+)",
        path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match:
        raise UpgradeError(f"PKU101 {label} has no version: {path}")
    return match.group(1)


def validate_release(release: Path) -> str:
    version_path = release / "VERSION"
    if not version_path.is_file():
        raise UpgradeError(f"PKU101 release VERSION is missing: {version_path}")
    expected = version_path.read_text(encoding="utf-8").strip()
    if not expected:
        raise UpgradeError("PKU101 release VERSION is empty")
    versions = {
        label: manifest_version(release / relative, label)
        for label, relative in COMPONENTS
    }
    mismatches = {label: version for label, version in versions.items() if version != expected}
    if mismatches:
        details = ", ".join(f"{label}={version}" for label, version in mismatches.items())
        raise UpgradeError(
            f"PKU102 release source is version-incoherent; VERSION={expected}, {details}"
        )
    return expected


def load_managed_profile(target: Path) -> tuple[str, str] | None:
    path = target / ".program-kit/managed.json"
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise UpgradeError(f"PKU103 cannot read managed baseline state {path}: {error}") from error
    web = value.get("webProfile")
    persistence = value.get("persistenceProfile")
    if web not in {"none", "bff-cookie", "spa-pkce"} or persistence not in {
        "none", "ef-postgresql", "ef-sqlserver", "ef-sqlite",
    }:
        raise UpgradeError(
            "PKU103 existing managed baseline does not record supported web and persistence profiles"
        )
    return str(web), str(persistence)


def selected_integration(target: Path, requested: str) -> str:
    if requested != "auto":
        candidate = requested
    else:
        path = target / ".specify/integration.json"
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise UpgradeError(f"PKU104 cannot resolve integration from {path}: {error}") from error
        candidate = state.get("default_integration") or state.get("integration")
    if not isinstance(candidate, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", candidate):
        raise UpgradeError(f"PKU104 unsupported integration identity: {candidate!r}")
    return candidate


def require_existing_bundle(target: Path) -> None:
    path = target / ".specify/bundle-records.json"
    try:
        records = json.loads(path.read_text(encoding="utf-8")).get("bundles")
    except (OSError, json.JSONDecodeError) as error:
        raise UpgradeError(f"PKU109 cannot read existing bundle records {path}: {error}") from error
    if not any(
        isinstance(record, dict) and record.get("bundle_id") == "program-kit"
        for record in records or []
    ):
        raise UpgradeError(
            "PKU109 target has no existing Program Kit bundle record; use Initialize-ProgramKit for a fresh install"
        )


def current_version(target: Path) -> str:
    manifest = target / ".specify/extensions/program-kit-governance/extension.yml"
    return manifest_version(manifest, "installed Program Kit Governance extension")


def run_step(command: list[str], target: Path, label: str, number: int, total: int) -> None:
    print(f"[{number}/{total}] {label}")
    result = subprocess.run(command, cwd=target, check=False)
    if result.returncode != 0:
        raise UpgradeError(
            f"PKU105 {label} failed with exit code {result.returncode}; "
            "the Program Kit installation must not be used until validate-installation passes"
        )


def resolve_specify_command(single: str, vector_json: str) -> list[str]:
    if vector_json:
        try:
            vector = json.loads(vector_json)
        except json.JSONDecodeError as error:
            raise UpgradeError(f"PKU108 --specify-command-json is not valid JSON: {error}") from error
        if (
            not isinstance(vector, list)
            or not vector
            or any(not isinstance(item, str) or not item for item in vector)
        ):
            raise UpgradeError("PKU108 --specify-command-json must be a non-empty JSON string array")
        command = list(vector)
    else:
        command = [single]
    executable = shutil.which(command[0])
    if executable is None:
        candidate = Path(command[0])
        executable = str(candidate.resolve()) if candidate.is_file() else None
    if not executable:
        raise UpgradeError(f"PKU108 Spec Kit CLI is unavailable: {command[0]}")
    command[0] = executable
    return command


def run_specify_probe(
    command: list[str], arguments: list[str], target: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command + arguments,
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def uv_windows_specify_environment(command: list[str]) -> tuple[Path, Path] | None:
    if os.name != "nt" or len(command) != 1:
        return None
    launcher = Path(command[0])
    if launcher.suffix.lower() != ".exe" or not launcher.is_file():
        return None
    try:
        payload = launcher.read_bytes()
        marker = payload.rfind(b"#!")
        if marker < 0:
            return None
        shebang = payload[marker + 2 :].splitlines()[0].decode("utf-8").strip().strip('"')
        interpreter = Path(shebang)
        environment = interpreter.parent.parent
        configuration = (environment / "pyvenv.cfg").read_text(encoding="utf-8")
        site_packages = environment / "Lib/site-packages"
    except (OSError, UnicodeDecodeError, IndexError):
        return None
    if (
        not interpreter.is_absolute()
        or not interpreter.is_file()
        or not re.search(r"(?m)^uv\s*=\s*\S+\s*$", configuration)
        or not (site_packages / "specify_cli/__init__.py").is_file()
        or b"from specify_cli import main" not in payload[marker:]
    ):
        return None
    return interpreter.resolve(), site_packages.resolve()


def powershell_retry_command() -> str:
    def literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    return "& " + " ".join(literal(item) for item in [sys.executable, *sys.argv])


def preflight_specify(command: list[str], target: Path, release: Path) -> list[str]:
    failure: BaseException | subprocess.CompletedProcess[str]
    try:
        result = run_specify_probe(command, ["--version"], target)
        if result.returncode == 0:
            return command
        failure = result
    except (OSError, subprocess.TimeoutExpired) as error:
        failure = error

    uv_environment = uv_windows_specify_environment(command)
    bridge = release / "scripts/invoke_specify.py"
    if uv_environment and bridge.is_file():
        interpreter, site_packages = uv_environment
        fallback = [
            sys.executable,
            str(bridge.resolve()),
            "--site-packages",
            str(site_packages),
            "--",
        ]
        probes = (
            ["--version"],
            ["bundle", "install", "--help"],
            ["workflow", "add", "--help"],
            ["extension", "add", "--help"],
            ["preset", "remove", "--help"],
            ["preset", "add", "--help"],
        )
        try:
            probe_results = [run_specify_probe(fallback, probe, target) for probe in probes]
        except (OSError, subprocess.TimeoutExpired) as error:
            fallback_failure = str(error)
        else:
            rejected = next((item for item in probe_results if item.returncode != 0), None)
            if rejected is None:
                print(
                    "PKU114 uv-installed Spec Kit launcher cannot execute its managed Python in this "
                    f"context; using the release-owned bridge with the same environment: {site_packages}"
                )
                return fallback
            lines = (rejected.stderr or rejected.stdout).strip().splitlines()
            fallback_failure = lines[-1] if lines else f"exit {rejected.returncode}"
        raise UpgradeError(
            "PKU114 uv-installed Spec Kit launcher crosses an execution boundary that the current "
            f"Windows context cannot use (launcher={command[0]}, interpreter={interpreter}). The "
            f"release-owned bridge also failed before mutation: {fallback_failure}. Rerun from a "
            "normal user-owned PowerShell terminal with: "
            + powershell_retry_command()
        )

    if isinstance(failure, subprocess.CompletedProcess):
        lines = (failure.stderr or failure.stdout).strip().splitlines()
        suffix = f" Detail: {lines[-1]}" if lines else ""
        failure_description = f"exit {failure.returncode}"
    else:
        suffix = f" Detail: {failure}"
        failure_description = "an execution error"
    raise UpgradeError(
        "PKU112 Spec Kit CLI cannot execute before mutation "
        f"({failure_description}). Run the updater from a context that can execute the installed "
        "CLI, or pass an explicitly reviewed command vector with --specify-command-json."
        + suffix
    )


def repository_relative_path(target: Path, value: str, label: str) -> Path:
    """Resolve an installer-owned relative path without permitting an escape."""
    relative = Path(value.replace("\\", "/"))
    if not value or relative.is_absolute() or ".." in relative.parts:
        raise UpgradeError(f"PKU115 unsafe {label} destination: {value!r}")
    path = (target / relative).resolve()
    try:
        path.relative_to(target)
    except ValueError as error:
        raise UpgradeError(f"PKU115 {label} destination escapes the repository: {value!r}") from error
    return path


def read_destination_state(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise UpgradeError(f"PKU115 cannot inspect {label} destination state {path}: {error}") from error
    if not isinstance(value, dict):
        raise UpgradeError(f"PKU115 {label} destination state is not an object: {path}")
    return value


def common_destination_root(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    common = paths[0].parent
    for path in paths[1:]:
        candidate = path.parent
        while common != candidate and common not in candidate.parents:
            if common == common.parent:
                return None
            common = common.parent
    return common


def managed_mutation_destinations(
    target: Path,
    release: Path,
    integration: str,
    profile: tuple[str, str] | None,
    has_bootstrap_decisions: bool,
    reconciliation: dict | None,
    stale_locks: list[Path],
) -> tuple[dict[Path, set[str]], set[Path]]:
    """Return all known component roots and existing files touched by an upgrade.

    Spec Kit records the exact files owned by each installed integration. Those
    manifests are the durable source for agent-specific locations; this avoids
    encoding Codex's ``.agents`` layout (or any other integration layout) in the
    Program Kit updater.
    """
    roots: dict[Path, set[str]] = {}
    existing_files: set[Path] = set()

    def add_root(path: Path, reason: str) -> None:
        roots.setdefault(path, set()).add(reason)

    for relative, reason in (
        (".specify", "upgrade lock and Spec Kit registries"),
        (".specify/extensions", "extension installation"),
        (".specify/workflows", "workflow installation"),
        (".specify/presets", "preset installation"),
    ):
        add_root(target / relative, reason)

    integration_state_path = target / ".specify/integration.json"
    integration_state = read_destination_state(integration_state_path, "integration")
    agent_ids = {integration}
    installed = integration_state.get("installed_integrations", [])
    if isinstance(installed, list):
        agent_ids.update(item for item in installed if isinstance(item, str))

    for registry_relative, kind in (
        (".specify/extensions/.registry", "extension"),
        (".specify/presets/.registry", "preset"),
    ):
        registry_path = target / registry_relative
        if not registry_path.is_file():
            continue
        registry = read_destination_state(registry_path, kind)
        records = registry.get(kind + "s", {})
        if not isinstance(records, dict):
            raise UpgradeError(f"PKU115 {kind} destination registry is malformed: {registry_path}")
        for record in records.values():
            commands = record.get("registered_commands", {}) if isinstance(record, dict) else {}
            if isinstance(commands, dict):
                agent_ids.update(item for item in commands if isinstance(item, str))

    for agent_id in sorted(agent_ids):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", agent_id):
            raise UpgradeError(f"PKU115 unsafe installed integration identity: {agent_id!r}")
        manifest_path = target / ".specify/integrations" / f"{agent_id}.manifest.json"
        if not manifest_path.is_file():
            raise UpgradeError(
                f"PKU115 cannot determine the managed destination for integration {agent_id!r}; "
                f"its installation manifest is missing: {manifest_path}"
            )
        manifest = read_destination_state(manifest_path, f"{agent_id} integration")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise UpgradeError(
                f"PKU115 integration {agent_id!r} has no managed file destinations in {manifest_path}"
            )
        paths = [
            repository_relative_path(target, value, f"{agent_id} integration")
            for value in files
            if isinstance(value, str)
        ]
        if len(paths) != len(files):
            raise UpgradeError(f"PKU115 integration {agent_id!r} has malformed file destinations")
        command_paths = [
            path
            for path in paths
            if any(part.casefold().startswith("speckit") for part in path.relative_to(target).parts)
        ]
        root = common_destination_root(command_paths or paths)
        if root is None:
            raise UpgradeError(f"PKU115 cannot determine a common destination for integration {agent_id!r}")
        add_root(root, f"{agent_id} integration command registration")
        if root.is_dir():
            for path in root.rglob("*"):
                if not (path.is_file() or path.is_symlink()):
                    continue
                if any(
                    part.startswith("speckit-program-kit-")
                    or part.startswith("speckit.program-kit.")
                    for part in path.relative_to(root).parts
                ):
                    existing_files.add(path)

    if profile:
        managed_path = target / ".program-kit/managed.json"
        managed = read_destination_state(managed_path, "managed profile")
        files = managed.get("files")
        if not isinstance(files, dict):
            raise UpgradeError(f"PKU115 managed profile has no file destination map: {managed_path}")
        add_root(target / ".program-kit", "managed profile state")
        for value, record in files.items():
            if not isinstance(value, str):
                raise UpgradeError(f"PKU115 managed profile has a malformed file destination: {value!r}")
            path = repository_relative_path(target, value, "managed profile")
            add_root(path.parent, "managed profile synchronization")
            if (
                isinstance(record, dict)
                and record.get("ownership") == "managed"
                and (path.is_file() or path.is_symlink())
            ):
                existing_files.add(path)

        web, _ = profile
        desired_manifests = [
            release / "extensions/program-kit-dotnet/templates/dotnet/managed-files.json"
        ]
        if web != "none":
            desired_manifests.append(
                release
                / "extensions/program-kit-dotnet/templates/dotnet/web-profiles"
                / web
                / "managed-files.json"
            )
        for manifest_path in desired_manifests:
            manifest = read_destination_state(manifest_path, "release managed profile")
            entries = manifest.get("files")
            obsolete = manifest.get("obsoleteFiles", [])
            if not isinstance(entries, list) or not isinstance(obsolete, list):
                raise UpgradeError(f"PKU115 release managed profile manifest is malformed: {manifest_path}")
            desired_entries = [entry for entry in entries if isinstance(entry, dict)]
            desired = [entry.get("path") for entry in desired_entries] + obsolete
            if len(desired) != len(entries) + len(obsolete) or any(
                not isinstance(value, str) for value in desired
            ):
                raise UpgradeError(f"PKU115 release managed profile destinations are malformed: {manifest_path}")
            managed_desired = {
                entry.get("path")
                for entry in desired_entries
                if entry.get("ownership") == "managed"
            } | set(obsolete)
            for value in desired:
                path = repository_relative_path(target, value, "release managed profile")
                add_root(path.parent, "managed profile synchronization")
                if value in managed_desired and (path.is_file() or path.is_symlink()):
                    existing_files.add(path)

    if has_bootstrap_decisions:
        add_root(target / ".specify/governance", "governed upgrade record")

    if stale_locks or (target / ".program-kit/evidence/dotnet-lock-renewal.json").exists():
        add_root(target / ".program-kit/evidence", "NuGet lock renewal evidence")

    if reconciliation:
        paths = [entry["path"] for entry in reconciliation["contracts"]]
        paths.extend(reconciliation["planningPaths"])
        for feature_dir in reconciliation["featureDirs"]:
            state_path = target / ".program-kit/lifecycle" / f"{feature_identity(feature_dir)}.json"
            if state_path.is_file():
                paths.append(state_path)
        for path in paths:
            add_root(path.parent, "OpenAPI producer-pin reconciliation")
            if path.is_file() or path.is_symlink():
                existing_files.add(path)

    return roots, existing_files


def feature_identity(feature_dir: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "-", feature_dir.name)


def nearest_existing_directory(path: Path) -> Path:
    candidate = path if path.is_dir() else path.parent
    while not candidate.exists():
        if candidate == candidate.parent:
            raise OSError(f"no existing parent directory for {path}")
        candidate = candidate.parent
    if not candidate.is_dir():
        raise OSError(f"destination parent is not a directory: {candidate}")
    return candidate


def probe_mutation_directory(path: Path) -> None:
    directory = nearest_existing_directory(path)
    nonce = uuid.uuid4().hex
    first = directory / f".program-kit-write-probe-{nonce}.tmp"
    second = directory / f".program-kit-write-probe-{nonce}.renamed.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(first, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(descriptor, b"Program Kit destination capability probe\n")
        os.close(descriptor)
        descriptor = None
        os.replace(first, second)
        second.unlink()
    finally:
        if descriptor is not None:
            os.close(descriptor)
        for sentinel in (first, second):
            try:
                sentinel.unlink()
            except FileNotFoundError:
                pass


def preflight_mutation_destinations(
    target: Path,
    release: Path,
    integration: str,
    profile: tuple[str, str] | None,
    has_bootstrap_decisions: bool,
    reconciliation: dict | None,
    stale_locks: list[Path],
) -> None:
    roots, existing_files = managed_mutation_destinations(
        target,
        release,
        integration,
        profile,
        has_bootstrap_decisions,
        reconciliation,
        stale_locks,
    )
    try:
        for path in sorted(roots, key=lambda item: str(item).casefold()):
            probe_mutation_directory(path)
        for path in sorted(existing_files, key=lambda item: str(item).casefold()):
            if path.is_symlink():
                continue
            with path.open("r+b"):
                pass
    except OSError as error:
        blocked = path
        reason = ", ".join(sorted(roots.get(path, {"managed installer file replacement"})))
        raise UpgradeError(
            "PKU115 Program Kit cannot mutate every installer-owned destination in the current "
            f"execution context; no component mutation started. Blocked destination: {blocked} "
            f"({reason}; {error}). Rerun from a user-owned PowerShell outside this sandbox "
            "(elevate only if OS ACLs require it) with: "
            + powershell_retry_command()
        ) from error


def stale_program_kit_locks(target: Path, runtime_version: str) -> list[Path]:
    ignored = {".git", ".specify", "artifacts", "node_modules"}
    stale: list[Path] = []
    for path in target.rglob("packages.lock.json"):
        relative = path.relative_to(target)
        if any(part in ignored for part in relative.parts) or relative.parts[:2] == (".program-kit", "cache"):
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise UpgradeError(f"PKU113 cannot inspect NuGet lock file {path}: {error}") from error
        frameworks = value.get("dependencies", {})
        if not isinstance(frameworks, dict):
            continue
        entries = [
            (package_id, dependency)
            for dependencies in frameworks.values()
            if isinstance(dependencies, dict)
            for package_id, dependency in dependencies.items()
            if isinstance(package_id, str)
            and package_id.startswith("ProgramKit.")
            and isinstance(dependency, dict)
        ]
        if any(str(dependency.get("resolved", "")) != runtime_version for _, dependency in entries):
            stale.append(path)
    return sorted(stale)


def lock_renewal_commands(target: Path, locks: list[Path]) -> list[str]:
    solutions = sorted([*target.glob("*.slnx"), *target.glob("*.sln")])
    if len(solutions) == 1:
        subjects = [solutions[0].relative_to(target).as_posix()]
    else:
        subjects = []
        for lock in locks:
            projects = sorted([*lock.parent.glob("*.csproj"), *lock.parent.glob("*.fsproj")])
            if len(projects) != 1:
                raise UpgradeError(
                    f"PKU113 cannot select one project for stale lock {lock}; add one root solution or renew it explicitly"
                )
            subjects.append(projects[0].relative_to(target).as_posix())
        subjects = sorted(set(subjects))
    commands: list[str] = []
    for subject in subjects:
        commands.extend(
            [
                f"pwsh -NoProfile -File .program-kit/eng/Restore.ps1 -Subject {subject} -ForceEvaluate",
                f"pwsh -NoProfile -File .program-kit/eng/Restore.ps1 -Subject {subject} -LockedMode",
            ]
        )
    return commands


def write_lock_renewal(target: Path, runtime_version: str, locks: list[Path]) -> list[str]:
    commands = lock_renewal_commands(target, locks)
    path = target / ".program-kit/evidence/dotnet-lock-renewal.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "targetRuntimeVersion": runtime_version,
                "affectedLocks": [item.relative_to(target).as_posix() for item in locks],
                "renewalCommands": commands,
                "reason": "program-kit-runtime-pin-upgrade",
                "satisfied": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return commands


def satisfy_lock_renewal(target: Path, runtime_version: str) -> None:
    path = target / ".program-kit/evidence/dotnet-lock-renewal.json"
    if not path.is_file():
        return
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise UpgradeError(f"PKU113 cannot verify NuGet lock renewal evidence {path}: {error}") from error
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise UpgradeError(f"PKU113 NuGet lock renewal evidence is malformed: {path}")
    value["targetRuntimeVersion"] = runtime_version
    value["reason"] = "program-kit-runtime-locks-verified"
    value["satisfied"] = True
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def acquire_lock(target: Path) -> tuple[int, Path]:
    path = target / ".specify/program-kit-upgrade.lock"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise UpgradeError(
            f"PKU106 another Program Kit component mutation may be active: {path}"
        ) from error
    os.write(descriptor, f"pid={os.getpid()}\n".encode("utf-8"))
    return descriptor, path


def main() -> int:
    configure_utf8()
    parser = argparse.ArgumentParser(
        description="Upgrade every Program Kit component sequentially from one local release."
    )
    parser.add_argument("--release-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--target", default=".")
    parser.add_argument("--integration", default="auto")
    parser.add_argument(
        "--accept-openapi-producer-pin-reconciliation",
        action="store_true",
        help="Explicitly update registered Program Kit exporter pins and invalidate affected analysis readiness.",
    )
    parser.add_argument("--specify-command", default="specify", help=argparse.SUPPRESS)
    parser.add_argument("--specify-command-json", default="", help=argparse.SUPPRESS)
    args = parser.parse_args()
    descriptor: int | None = None
    lock_path: Path | None = None
    try:
        release = Path(args.release_root).resolve()
        target = Path(args.target).resolve()
        version = validate_release(release)
        runtime_version = (release / "RUNTIME_VERSION").read_text(encoding="utf-8").strip()
        if not runtime_version:
            raise UpgradeError("PKU101 release RUNTIME_VERSION is empty")
        if not (target / ".specify").is_dir():
            raise UpgradeError(f"PKU107 target is not an initialized Spec Kit project: {target}")
        require_existing_bundle(target)
        previous_version = current_version(target)
        profile = load_managed_profile(target)
        has_bootstrap_decisions = (target / "docs/architecture/bootstrap-decisions.json").is_file()
        reconciliation = discover_openapi_reconciliation(target, release)
        if reconciliation and not args.accept_openapi_producer_pin_reconciliation:
            raise UpgradeError(
                "PKU110 upgrade requires explicit OpenAPI producer-pin reconciliation before it can mutate "
                "Program Kit components. "
                + describe_openapi_reconciliation(target, reconciliation)
                + ". Re-run this exact updater command with "
                "--accept-openapi-producer-pin-reconciliation; it will update those consumer-owned pins "
                "atomically, invalidate affected after_tasks readiness, and stop with the required renewal path."
            )
        integration = selected_integration(target, args.integration)
        specify = resolve_specify_command(args.specify_command, args.specify_command_json)
        specify = preflight_specify(specify, target, release)
        stale_locks = stale_program_kit_locks(target, runtime_version)
        preflight_mutation_destinations(
            target,
            release,
            integration,
            profile,
            has_bootstrap_decisions,
            reconciliation,
            stale_locks,
        )
        descriptor, lock_path = acquire_lock(target)
        steps = [
            (specify + ["bundle", "install", str(release / "bundle.yml"), "--offline", "--integration", integration], "Resolve bundle composition record"),
            (specify + ["workflow", "add", str(release / "workflows/program-kit-bootstrap"), "--dev"], "Install bootstrap workflow"),
            (specify + ["extension", "add", str(release / "extensions/program-kit-governance"), "--dev", "--force"], "Install governance extension"),
            (specify + ["extension", "add", str(release / "extensions/program-kit-dotnet"), "--dev", "--force"], "Install .NET extension"),
            (specify + ["preset", "remove", "program-kit-governance-preset"], "Remove prior governance preset"),
            (specify + ["preset", "add", "--dev", str(release / "presets/program-kit-governance-preset")], "Install governance preset"),
        ]
        total = (
            len(steps)
            + (2 if profile else 0)
            + 1
            + (1 if has_bootstrap_decisions else 0)
            + (1 if reconciliation else 0)
        )
        for number, (command, label) in enumerate(steps, 1):
            run_step(command, target, label, number, total)
        next_step = len(steps) + 1
        if profile:
            web, persistence = profile
            sync = target / ".specify/extensions/program-kit-dotnet/scripts/dotnet_sync.py"
            write = [
                sys.executable, str(sync), "--target", str(target), "--profile-selected",
                "--host-runtime-accepted", "--preview-sources-approved",
                "--persistence-profile", persistence, "--web-profile", web,
            ]
            check = [
                sys.executable, str(sync), "--target", str(target), "--profile-selected",
                "--persistence-profile", persistence, "--web-profile", web, "--check",
            ]
            run_step(write, target, "Resynchronize managed .NET baseline", next_step, total)
            run_step(check, target, "Verify managed .NET baseline convergence", next_step + 1, total)
            next_step += 2
        validator = target / ".specify/extensions/program-kit-governance/scripts/governance_state.py"
        run_step(
            [sys.executable, str(validator), "validate-installation"],
            target,
            "Validate cross-component version coherence",
            next_step,
            total,
        )
        if has_bootstrap_decisions:
            run_step(
                [
                    sys.executable, str(validator), "record-upgrade",
                    "--previous-version", previous_version,
                    "--target-version", version,
                ],
                target,
                "Record accepted governed upgrade",
                next_step + 1,
                total,
            )
            next_step += 1
        renewal_required = False
        if reconciliation:
            print(f"[{next_step + 1}/{total}] Reconcile registered OpenAPI producer pins")
            changed = apply_openapi_reconciliation(target, reconciliation)
            print("atomically reconciled: " + ", ".join(changed))
            print(
                "PKU111 Program Kit components are coherent, but affected after_tasks analysis readiness "
                "was invalidated honestly. Run $speckit-analyze, then the Program Kit architecture check, "
                "then the Program Kit implementation check for each affected feature: "
                + ", ".join(path.name for path in reconciliation["featureDirs"]),
                file=sys.stderr,
            )
            renewal_required = True
        if stale_locks:
            commands = write_lock_renewal(target, runtime_version, stale_locks)
            print(
                "PKU113 Program Kit runtime pins changed while consumer NuGet lock files still resolve "
                f"an older version: {', '.join(path.relative_to(target).as_posix() for path in stale_locks)}. "
                "No network restore was run implicitly. Renew and verify with: "
                + " ; then ".join(commands),
                file=sys.stderr,
            )
            renewal_required = True
        else:
            satisfy_lock_renewal(target, runtime_version)
        if renewal_required:
            return 3
        print(
            f"Program Kit v{version} upgrade completed: workflow, extensions, preset, bundle record, "
            "managed baseline, and governed version authority are coherent."
        )
        return 0
    except (OSError, UpgradeError, ReconciliationError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if lock_path is not None:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
