from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


class TopologyError(ValueError):
    pass


def effective_networks(model: dict, service_name: str) -> set[str]:
    services = model.get("services", {})
    service = services.get(service_name, {}) if isinstance(services, dict) else {}
    attached = service.get("networks", {}) if isinstance(service, dict) else {}
    if isinstance(attached, list):
        keys = attached
    elif isinstance(attached, dict):
        keys = list(attached)
    else:
        keys = []
    definitions = model.get("networks", {})
    definitions = definitions if isinstance(definitions, dict) else {}
    result: set[str] = set()
    for key in keys:
        definition = definitions.get(key, {})
        name = definition.get("name") if isinstance(definition, dict) else None
        result.add(str(name or key))
    return result


def service_hostnames(model: dict, service_name: str) -> set[str]:
    service = model["services"][service_name]
    names = {service_name.casefold()}
    for key in ("hostname", "container_name"):
        value = service.get(key)
        if isinstance(value, str) and value:
            names.add(value.casefold())
    networks = service.get("networks", {})
    if isinstance(networks, dict):
        for settings in networks.values():
            aliases = settings.get("aliases", []) if isinstance(settings, dict) else []
            if isinstance(aliases, list):
                names.update(str(alias).casefold() for alias in aliases if alias)
    return names


def environment_hosts(service: dict) -> list[tuple[str, str]]:
    environment = service.get("environment", {})
    if not isinstance(environment, dict):
        return []
    result: list[tuple[str, str]] = []
    for key, value in environment.items():
        if not isinstance(value, str) or "://" not in value:
            continue
        host = urlsplit(value).hostname
        if host:
            result.append((str(key), host.casefold()))
    return result


def dependency_edges(models: dict[str, dict]) -> list[tuple[str, str, str]]:
    owners: dict[str, str] = {}
    for model_name, model in models.items():
        services = model.get("services", {})
        if not isinstance(services, dict):
            continue
        for service_name in services:
            identity = f"{model_name}:{service_name}"
            for hostname in service_hostnames(model, service_name):
                owners.setdefault(hostname, identity)

    edges: set[tuple[str, str, str]] = set()
    for model_name, model in models.items():
        services = model.get("services", {})
        if not isinstance(services, dict):
            continue
        for service_name, service in services.items():
            if not isinstance(service, dict):
                continue
            source = f"{model_name}:{service_name}"
            depends_on = service.get("depends_on", {})
            dependencies = depends_on if isinstance(depends_on, (dict, list)) else []
            for dependency in dependencies:
                target = f"{model_name}:{dependency}"
                if dependency in services and target != source:
                    edges.add((source, target, "depends_on"))
            for variable, hostname in environment_hosts(service):
                target = owners.get(hostname)
                if target and target != source:
                    edges.add((source, target, f"environment {variable}"))
    return sorted(edges)


def validate_desired(models: dict[str, dict], consumer_overlay: Path | None) -> None:
    by_identity = {
        f"{model_name}:{service_name}": (model, service_name)
        for model_name, model in models.items()
        for service_name in model.get("services", {})
    }
    for source, target, reason in dependency_edges(models):
        source_model, source_name = by_identity[source]
        target_model, target_name = by_identity[target]
        source_networks = effective_networks(source_model, source_name)
        target_networks = effective_networks(target_model, target_name)
        if source_networks & target_networks:
            continue
        path = str(consumer_overlay) if consumer_overlay else "the managed Compose files"
        candidates = ", ".join(sorted(target_networks)) or "a network attached to the target service"
        raise TopologyError(
            f"PKC001 Compose service {source_name!r} references {target_name!r} through {reason} "
            f"but shares no effective network. Source: {path}. Attach {source_name!r} to {candidates} "
            "in the consumer overlay, then rerun Dev.ps1 so Compose recreates the affected services."
        )


def run_json(command: list[str], cwd: Path) -> dict:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise TopologyError(
            f"PKC003 Docker Compose model resolution failed: {detail[-1] if detail else 'unknown error'}"
        )
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise TopologyError(f"PKC003 Docker returned a malformed Compose model: {error}") from error
    if not isinstance(value, dict) or not isinstance(value.get("services"), dict):
        raise TopologyError("PKC003 Docker returned an incomplete Compose model")
    return value


def compose_arguments(docker: str, files: list[Path]) -> list[str]:
    command = [docker, "compose"]
    for path in files:
        command.extend(["-f", str(path)])
    return command


def inspect_running_networks(
    docker: str, compose: list[str], service_name: str, repository: Path
) -> set[str]:
    result = subprocess.run(
        compose + ["ps", "-q", service_name],
        cwd=repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    identifiers = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 or len(identifiers) != 1:
        raise TopologyError(
            f"PKC002 Compose service {service_name!r} does not resolve to exactly one running container"
        )
    inspected = subprocess.run(
        [docker, "inspect", "--format", "{{json .NetworkSettings.Networks}}", identifiers[0]],
        cwd=repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if inspected.returncode != 0:
        raise TopologyError(f"PKC002 cannot inspect running Compose service {service_name!r}")
    try:
        networks = json.loads(inspected.stdout)
    except json.JSONDecodeError as error:
        raise TopologyError(f"PKC002 malformed network inspection for {service_name!r}: {error}") from error
    if not isinstance(networks, dict):
        raise TopologyError(f"PKC002 incomplete network inspection for {service_name!r}")
    return set(networks)


def verify_running(
    docker: str,
    models: dict[str, dict],
    compose_commands: dict[str, list[str]],
    repository: Path,
) -> None:
    for model_name, model in models.items():
        for service_name in model["services"]:
            desired = effective_networks(model, service_name)
            actual = inspect_running_networks(
                docker, compose_commands[model_name], service_name, repository
            )
            if actual != desired:
                raise TopologyError(
                    f"PKC002 running Compose service {service_name!r} has networks "
                    f"{sorted(actual)}, expected {sorted(desired)}. Rerun Dev.ps1 so the stale "
                    "container is force-recreated from the merged desired model."
                )


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Validate desired and running local Compose topology.")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--identity-compose", required=True)
    parser.add_argument("--application-compose", default="")
    parser.add_argument("--overlay", default="")
    parser.add_argument("--verify-running", action="store_true")
    parser.add_argument("--docker-command", default=os.environ.get("PROGRAMKIT_DOCKER_COMMAND", "docker"))
    args = parser.parse_args()
    try:
        repository = Path(args.repository).resolve()
        docker = shutil.which(args.docker_command)
        if docker is None:
            raise TopologyError("PKC003 Docker CLI is unavailable")
        identity_files = [Path(args.identity_compose).resolve()]
        application_files = [Path(args.application_compose).resolve()] if args.application_compose else []
        overlay = Path(args.overlay).resolve() if args.overlay else None
        if overlay:
            application_files.append(overlay)
        models = {
            "identity": run_json(
                compose_arguments(docker, identity_files) + ["config", "--format", "json"],
                repository,
            )
        }
        commands = {"identity": compose_arguments(docker, identity_files)}
        if application_files:
            models["application"] = run_json(
                compose_arguments(docker, application_files) + ["config", "--format", "json"],
                repository,
            )
            commands["application"] = compose_arguments(docker, application_files)
        validate_desired(models, overlay)
        if args.verify_running:
            verify_running(docker, models, commands, repository)
            print("Desired and running Compose network topology are coherent.")
        else:
            print("Merged Compose network topology is coherent before startup.")
        return 0
    except (OSError, TopologyError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
