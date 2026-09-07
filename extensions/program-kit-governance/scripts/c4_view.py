from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import quote


# Dynamic architecture-map loading must not create __pycache__ in the consumer repository.
sys.dont_write_bytecode = True


ARCHITECTURE_MAP = Path("docs/architecture/architecture-map.json")
WORKSPACE_DSL = Path("docs/architecture/workspace.dsl")
BOOTSTRAP_INTAKE = Path("docs/architecture/bootstrap-intake.json")
PROJECT_INTENT = Path("docs/architecture/project-intent.md")
PROFILE = Path(__file__).resolve().parents[1] / "references/c4-viewer-tool.json"
STATE_ENVIRONMENT = "PROGRAM_KIT_C4_STATE_ROOT"
WAR_ENVIRONMENT = "PROGRAM_KIT_STRUCTURIZR_WAR"
DIRECTIVE = re.compile(r'^\s*!(docs|adrs)\s+("(?:[^"\\]|\\.)+")\s*$', re.MULTILINE)


class C4ViewError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise C4ViewError(f"Missing {label}: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise C4ViewError(f"Cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise C4ViewError(f"{label} must be a JSON object: {path}")
    return value


def load_profile() -> dict:
    profile = load_json(PROFILE, "managed C4 viewer profile")
    selected = profile.get("selected")
    required = {
        "product",
        "command",
        "version",
        "docker_image",
        "docker_digest",
        "java_war",
        "java_war_url",
        "java_minimum",
        "default_port",
    }
    if (
        profile.get("schema_version") != "1.0"
        or not isinstance(selected, dict)
        or set(selected) != required
        or selected.get("command") != "local"
        or selected.get("docker_image") != f"structurizr/structurizr:{selected.get('version')}"
    ):
        raise C4ViewError(f"Managed C4 viewer profile has an invalid pin contract: {PROFILE}")
    return profile


def architecture_module():
    path = Path(__file__).with_name("architecture_map.py")
    spec = importlib.util.spec_from_file_location("program_kit_c4_architecture_map", path)
    if spec is None or spec.loader is None:
        raise C4ViewError(f"Cannot load architecture-map support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical_project_root(value: str | Path) -> Path:
    root = Path(value).resolve()
    if not root.is_dir():
        raise C4ViewError(f"Project root is not a directory: {root}")
    return root


def _artifact_record(intake: dict, key: str, expected: Path) -> dict:
    artifacts = intake.get("artifacts")
    record = artifacts.get(key) if isinstance(artifacts, dict) else None
    if (
        not isinstance(record, dict)
        or set(record) != {"path", "sha256", "bytes"}
        or record.get("path") != expected.as_posix()
        or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256", "")))
        or not isinstance(record.get("bytes"), int)
    ):
        raise C4ViewError(
            f"Bootstrap intake has no valid registered {key} hash for {expected.as_posix()}"
        )
    return record


def validate_projection(project_root: Path) -> dict:
    map_path = project_root / ARCHITECTURE_MAP
    dsl_path = project_root / WORKSPACE_DSL
    intake_path = project_root / BOOTSTRAP_INTAKE
    if not map_path.is_file():
        raise C4ViewError(f"Canonical architecture map is missing: {ARCHITECTURE_MAP.as_posix()}")
    if not dsl_path.is_file():
        raise C4ViewError(
            f"C4 projection is missing: {WORKSPACE_DSL.as_posix()}. Regenerate it from the canonical map."
        )

    architecture = architecture_module()
    try:
        model = architecture.load_object(map_path)
        architecture.validate_model(model, project_root)
    except (architecture.ArchitectureMapError, OSError, UnicodeError) as exc:
        raise C4ViewError(f"Canonical architecture map is invalid or has stale source hashes: {exc}") from exc
    try:
        actual_text = dsl_path.read_text(encoding="utf-8")
        architecture.StructurizrDslImporter().import_path(dsl_path, model)
    except (architecture.ArchitectureMapError, OSError, UnicodeError) as exc:
        raise C4ViewError(f"Structurizr DSL projection is malformed: {exc}") from exc
    expected_text = architecture.StructurizrDslExporter().export(model)
    normalize = lambda value: value.replace("\r\n", "\n").replace("\r", "\n")
    if normalize(actual_text) != normalize(expected_text):
        raise C4ViewError(
            "C4 projection is stale relative to docs/architecture/architecture-map.json; "
            "regenerate workspace.dsl from the canonical map before review"
        )

    intake = load_json(intake_path, "bootstrap intake")
    intake_status = intake.get("status")
    if intake_status not in {"draft", "confirmed"}:
        raise C4ViewError(
            f"Bootstrap intake status must be draft or confirmed: {BOOTSTRAP_INTAKE.as_posix()}"
        )
    map_record = _artifact_record(intake, "architecture_map", ARCHITECTURE_MAP)
    dsl_record = _artifact_record(intake, "c4_projection", WORKSPACE_DSL)
    map_hash = sha256_file(map_path)
    dsl_hash = sha256_file(dsl_path)
    map_match = map_record["sha256"] == map_hash and map_record["bytes"] == map_path.stat().st_size
    dsl_match = dsl_record["sha256"] == dsl_hash and dsl_record["bytes"] == dsl_path.stat().st_size
    if intake_status == "draft":
        intent_path = project_root / PROJECT_INTENT
        intent_record = _artifact_record(intake, "project_intent", PROJECT_INTENT)
        if not intent_path.is_file():
            raise C4ViewError(f"Draft intake artifact is missing: {PROJECT_INTENT.as_posix()}")
        intent_match = (
            intent_record["sha256"] == sha256_file(intent_path)
            and intent_record["bytes"] == intent_path.stat().st_size
        )
        mismatched = [
            path.as_posix()
            for path, matches in (
                (PROJECT_INTENT, intent_match),
                (ARCHITECTURE_MAP, map_match),
                (WORKSPACE_DSL, dsl_match),
            )
            if not matches
        ]
        if mismatched:
            raise C4ViewError(
                "Draft bootstrap intake hashes do not match current artifacts: "
                + ", ".join(mismatched)
            )
        binding = "draft-intake"
        review_mode = "draft-intake-review"
    else:
        if map_match != dsl_match:
            changed = WORKSPACE_DSL if map_match else ARCHITECTURE_MAP
            raise C4ViewError(
                f"Registered intake hashes show partial architecture drift at {changed.as_posix()}; "
                "refresh the generated pair and its governance evidence before review"
            )
        binding = "confirmed-intake" if map_match else "evolved-together-from-confirmed-intake"
        review_mode = "confirmed-baseline-review"
    view_keys = [view["key"] for view in model["views"]]
    return {
        "project_root": str(project_root),
        "canonical_map": ARCHITECTURE_MAP.as_posix(),
        "projection": WORKSPACE_DSL.as_posix(),
        "map_sha256": map_hash,
        "projection_sha256": dsl_hash,
        "projection_current": True,
        "projection_parsed": True,
        "intake_status": intake_status,
        "intake_binding": binding,
        "review_mode": review_mode,
        "confirmation_performed": False,
        "architecture_acceptance_performed": False,
        "registered_map_sha256": map_record["sha256"],
        "registered_projection_sha256": dsl_record["sha256"],
        "view_keys": view_keys,
        "primary_view_key": view_keys[0],
    }


def diagram_url(port: int, view_key: str) -> str:
    return f"http://localhost:{port}/workspace/1/diagrams#{quote(view_key, safe='')}"


def run_capture(arguments: Sequence[str], timeout: float = 10) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(arguments),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(list(arguments), 127, "", str(exc))


def java_major(output: str) -> int | None:
    match = re.search(r'(?:version\s+"|openjdk\s+)(?:1\.)?(\d+)(?:[._"]|\s)', output, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def default_war_path(profile: dict) -> Path:
    selected = profile["selected"]
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        cache = Path(os.environ["LOCALAPPDATA"]) / "ProgramKit" / "tools"
    else:
        cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "program-kit" / "tools"
    return cache / "structurizr" / selected["version"] / selected["java_war"]


def discover_runtimes(profile: dict, war: str | None = None) -> dict:
    selected = profile["selected"]
    docker_path = shutil.which("docker")
    docker = {
        "installed": docker_path is not None,
        "path": docker_path,
        "daemon_available": False,
        "image": selected["docker_image"],
        "image_local": False,
        "diagnostic": "Docker is not installed",
    }
    if docker_path:
        version = run_capture((docker_path, "version", "--format", "{{.Server.Version}}"))
        docker["daemon_available"] = version.returncode == 0 and bool(version.stdout.strip())
        docker["diagnostic"] = (
            f"Docker server {version.stdout.strip()}" if docker["daemon_available"] else
            (version.stderr.strip() or "Docker is installed but its daemon is unavailable")
        )
        if docker["daemon_available"]:
            image = run_capture((docker_path, "image", "inspect", selected["docker_image"], "--format", "{{json .RepoDigests}}"))
            docker["image_local"] = (
                image.returncode == 0 and selected["docker_digest"] in image.stdout
            )
            if not docker["image_local"]:
                if image.returncode == 0:
                    docker["diagnostic"] = (
                        f"Local {selected['docker_image']} does not match tested digest "
                        f"{selected['docker_digest']}; explicit authorization is required before refreshing it"
                    )
                else:
                    docker["diagnostic"] = (
                        f"Pinned image is not local; explicit authorization is required before: "
                        f"docker pull {selected['docker_image']}"
                    )

    java_path = shutil.which("java")
    java = {
        "installed": java_path is not None,
        "path": java_path,
        "major": None,
        "supported": False,
        "war": None,
        "war_local": False,
        "diagnostic": "Java is not installed",
    }
    candidates: list[Path] = []
    if war:
        candidates.append(Path(war).expanduser())
    if os.environ.get(WAR_ENVIRONMENT):
        candidates.append(Path(os.environ[WAR_ENVIRONMENT]).expanduser())
    candidates.append(default_war_path(profile))
    existing = next((path.resolve() for path in candidates if path.is_file()), None)
    if java_path:
        result = run_capture((java_path, "-version"))
        major = java_major(result.stdout + "\n" + result.stderr)
        java["major"] = major
        java["supported"] = major is not None and major >= selected["java_minimum"]
        java["war"] = str(existing) if existing else str(candidates[0])
        java["war_local"] = existing is not None
        if not java["supported"]:
            java["diagnostic"] = (
                f"Java {major or 'unknown'} is available; Structurizr {selected['version']} requires "
                f"Java {selected['java_minimum']} or newer"
            )
        elif not existing:
            java["diagnostic"] = (
                f"Pinned WAR is not local; explicit authorization is required before downloading "
                f"{selected['java_war_url']} to {default_war_path(profile)}"
            )
        else:
            java["diagnostic"] = f"Supported Java {major} and pinned WAR are available"
    return {"docker": docker, "java": java}


def port_available(port: int, host: str = "127.0.0.1") -> bool:
    if not 1 <= port <= 65535:
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def select_port(preferred: int, attempts: int = 100) -> int:
    for port in range(preferred, min(65536, preferred + attempts)):
        if port_available(port):
            return port
    raise C4ViewError(f"No free localhost port found from {preferred} through {preferred + attempts - 1}")


def session_identifier(project_root: Path) -> str:
    identity = str(project_root.resolve())
    if os.name == "nt":
        identity = identity.casefold()
    return sha256_bytes(identity.encode("utf-8"))[:12]


def state_root() -> Path:
    configured = os.environ.get(STATE_ENVIRONMENT)
    return Path(configured).resolve() if configured else Path(tempfile.gettempdir()).resolve() / "program-kit-c4-view"


def session_directory(project_root: Path) -> Path:
    return state_root() / session_identifier(project_root)


def _safe_session_path(path: Path) -> Path:
    base = state_root().resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(base)
    except ValueError as exc:
        raise C4ViewError(f"Viewer state path escaped its temporary root: {resolved}") from exc
    if len(relative.parts) < 1:
        raise C4ViewError(f"Refusing to operate on the viewer state root: {resolved}")
    return resolved


def render_command(arguments: Sequence[str], platform: str | None = None) -> str:
    platform = os.name if platform is None else platform
    return subprocess.list2cmdline(list(arguments)) if platform == "nt" else shlex.join(arguments)


def build_docker_command(
    docker: str, image: str, data_directory: Path, name: str, port: int
) -> list[str]:
    return [
        docker,
        "run",
        "--detach",
        "--rm",
        "--name",
        name,
        "--label",
        "program-kit.c4-viewer=true",
        "--publish",
        f"127.0.0.1:{port}:{port}",
        "--env",
        f"PORT={port}",
        "--volume",
        f"{os.fspath(data_directory)}:/usr/local/structurizr",
        image,
        "local",
    ]


def build_java_command(java: str, war: Path, data_directory: Path, port: int) -> list[str]:
    return [
        java,
        "-Dserver.address=127.0.0.1",
        f"-Dserver.port={port}",
        "-jar",
        os.fspath(war),
        "local",
        os.fspath(data_directory),
    ]


def _directive_paths(project_root: Path, text: str) -> list[tuple[Path, Path]]:
    paths: list[tuple[Path, Path]] = []
    for match in DIRECTIVE.finditer(text):
        try:
            raw = json.loads(match.group(2))
        except json.JSONDecodeError as exc:
            raise C4ViewError(f"Invalid {match.group(1)} path in workspace.dsl: {match.group(2)}") from exc
        relative = Path(raw)
        if relative.is_absolute():
            raise C4ViewError(f"Structurizr {match.group(1)} path must be repository-relative: {raw}")
        source = (project_root / relative).resolve()
        try:
            source.relative_to(project_root)
        except ValueError as exc:
            raise C4ViewError(f"Structurizr {match.group(1)} path escapes the repository: {raw}") from exc
        if not source.exists():
            raise C4ViewError(f"Structurizr {match.group(1)} input is missing: {raw}")
        paths.append((source, relative))
    return paths


def stage_projection(project_root: Path, target: Path) -> None:
    target = _safe_session_path(target)
    target.mkdir(parents=True, exist_ok=False)
    dsl = project_root / WORKSPACE_DSL
    shutil.copy2(dsl, target / "workspace.dsl")
    text = dsl.read_text(encoding="utf-8")
    for source, relative in _directive_paths(project_root, text):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)


def _state_file(project_root: Path) -> Path:
    return session_directory(project_root) / "state.json"


def load_state(project_root: Path) -> dict | None:
    path = _state_file(project_root)
    if not path.is_file():
        return None
    return load_json(path, "C4 viewer state")


def process_alive(pid: int) -> bool:
    if not isinstance(pid, int) or pid < 1:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def session_active(state: dict, runtimes: dict | None = None) -> bool:
    runtime = state.get("runtime")
    if runtime == "java":
        return process_alive(state.get("pid"))
    if runtime == "docker":
        docker = (runtimes or {}).get("docker", {})
        executable = docker.get("path") or shutil.which("docker")
        if not executable or not docker.get("daemon_available", True):
            return False
        result = run_capture((executable, "container", "inspect", state.get("container", ""), "--format", "{{.State.Running}}"))
        return result.returncode == 0 and result.stdout.strip().lower() == "true"
    return False


def write_state(project_root: Path, state: dict) -> None:
    path = _safe_session_path(_state_file(project_root))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def cleanup_directory(project_root: Path) -> None:
    directory = _safe_session_path(session_directory(project_root))
    if directory.exists():
        shutil.rmtree(directory)


def stop_session(project_root: Path, runtimes: dict | None = None) -> bool:
    state = load_state(project_root)
    if state is None:
        cleanup_directory(project_root)
        return False
    if state.get("runtime") == "docker":
        docker = (runtimes or {}).get("docker", {})
        executable = docker.get("path") or shutil.which("docker")
        if not executable or not docker.get("daemon_available", True):
            raise C4ViewError(
                "Cannot reach Docker to stop the recorded C4 viewer; temporary state was preserved"
            )
        result = run_capture(
            (executable, "container", "rm", "--force", state.get("container", "")), timeout=20
        )
        if result.returncode != 0:
            raise C4ViewError(
                "Docker did not remove the recorded C4 viewer; temporary state was preserved: "
                + (result.stderr.strip() or result.stdout.strip())
            )
    elif state.get("runtime") == "java" and process_alive(state.get("pid")):
        try:
            os.kill(state["pid"], signal.SIGTERM)
        except OSError as exc:
            raise C4ViewError(
                "Could not stop the recorded Java C4 viewer; temporary state was preserved"
            ) from exc
    cleanup_directory(project_root)
    return True


def wait_ready(url: str, active: Callable[[], bool], timeout: float = 45) -> None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + timeout
    last_error = "no response"
    while time.monotonic() < deadline:
        if not active():
            raise C4ViewError("Structurizr stopped before the localhost viewer became ready")
        try:
            with opener.open(url, timeout=1) as response:
                if 200 <= response.status < 500:
                    return
        except Exception as exc:  # localhost readiness has platform-specific failure types
            last_error = str(exc)
        time.sleep(0.25)
    raise C4ViewError(f"Structurizr did not become ready at {url}: {last_error}")


def choose_runtime(runtimes: dict, requested: str) -> str:
    docker_ready = runtimes["docker"]["daemon_available"] and runtimes["docker"]["image_local"]
    java_ready = runtimes["java"]["supported"] and runtimes["java"]["war_local"]
    if requested in {"auto", "docker"} and docker_ready:
        return "docker"
    if requested in {"auto", "java"} and java_ready:
        return "java"
    diagnostics = [runtimes["docker"]["diagnostic"], runtimes["java"]["diagnostic"]]
    if requested != "auto":
        diagnostics.insert(0, f"Requested {requested} runtime is unavailable")
    raise C4ViewError("No supported local Structurizr runtime is ready. " + " | ".join(diagnostics))


def start_session(
    project_root: Path,
    requested_runtime: str,
    requested_port: int | None,
    war: str | None,
    open_browser: bool,
    detach: bool,
) -> dict:
    profile = load_profile()
    validation = validate_projection(project_root)
    runtimes = discover_runtimes(profile, war)
    existing = load_state(project_root)
    if (
        existing
        and existing.get("runtime") == "docker"
        and not runtimes["docker"]["daemon_available"]
    ):
        raise C4ViewError(
            "A Docker-backed C4 viewer is recorded, but Docker is inaccessible; "
            "the session state was preserved so it can be stopped safely"
        )
    if existing and session_active(existing, runtimes):
        if existing.get("projection_sha256") != validation["projection_sha256"]:
            raise C4ViewError(
                "A viewer for an older projection is already running; stop it before starting the current projection"
            )
        existing["reused"] = True
        existing["url"] = diagram_url(existing["port"], validation["primary_view_key"])
        existing["intake_status"] = validation["intake_status"]
        existing["review_mode"] = validation["review_mode"]
        existing["confirmation_performed"] = False
        existing["architecture_acceptance_performed"] = False
        if open_browser:
            webbrowser.open(existing["url"])
        return existing
    if existing:
        cleanup_directory(project_root)

    runtime = choose_runtime(runtimes, requested_runtime)
    preferred = requested_port or profile["selected"]["default_port"]
    port = select_port(preferred)
    directory = _safe_session_path(session_directory(project_root))
    directory.mkdir(parents=True, exist_ok=False)
    data_directory = directory / "data"
    try:
        stage_projection(project_root, data_directory)
        identifier = session_identifier(project_root)
        health_url = f"http://localhost:{port}/"
        url = diagram_url(port, validation["primary_view_key"])
        state = {
            "schema_version": "1.0",
            "project_root": str(project_root),
            "runtime": runtime,
            "port": port,
            "url": url,
            "health_url": health_url,
            "primary_view_key": validation["primary_view_key"],
            "projection_sha256": validation["projection_sha256"],
            "intake_status": validation["intake_status"],
            "review_mode": validation["review_mode"],
            "confirmation_performed": False,
            "architecture_acceptance_performed": False,
            "data_directory": str(data_directory),
            "reused": False,
        }
        if runtime == "docker":
            docker = runtimes["docker"]["path"]
            name = f"program-kit-c4-{identifier}"
            command = build_docker_command(
                docker, profile["selected"]["docker_image"], data_directory, name, port
            )
            result = run_capture(command, timeout=45)
            if result.returncode != 0:
                raise C4ViewError(f"Structurizr Docker startup failed: {result.stderr.strip() or result.stdout.strip()}")
            state.update({"container": name, "container_id": result.stdout.strip(), "command": command})
        else:
            java = runtimes["java"]["path"]
            war_path = Path(runtimes["java"]["war"])
            command = build_java_command(java, war_path, data_directory, port)
            stdout = (directory / "structurizr.stdout.log").open("w", encoding="utf-8")
            stderr = (directory / "structurizr.stderr.log").open("w", encoding="utf-8")
            flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, creationflags=flags)
            stdout.close()
            stderr.close()
            state.update({"pid": process.pid, "command": command})
        write_state(project_root, state)
        wait_ready(health_url, lambda: session_active(state, runtimes))
        if open_browser:
            webbrowser.open(url)
        if not detach:
            try:
                while session_active(state, runtimes):
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            finally:
                stop_session(project_root, runtimes)
            state["stopped"] = True
        return state
    except BaseException as startup_error:
        try:
            stop_session(project_root, runtimes)
        except C4ViewError as cleanup_error:
            raise C4ViewError(
                f"{startup_error}; cleanup also failed and temporary state was preserved: {cleanup_error}"
            ) from cleanup_error
        if directory.exists():
            cleanup_directory(project_root)
        raise


def inspection(project_root: Path, war: str | None = None, preferred_port: int | None = None) -> dict:
    profile = load_profile()
    result = validate_projection(project_root)
    runtimes = discover_runtimes(profile, war)
    existing = load_state(project_root)
    active = existing if existing and session_active(existing, runtimes) else None
    port = active["port"] if active else select_port(preferred_port or profile["selected"]["default_port"])
    result.update(
        {
            "profile": profile["profile_id"],
            "structurizr_version": profile["selected"]["version"],
            "port": port,
            "runtimes": runtimes,
            "viewer_ready": (
                runtimes["docker"]["daemon_available"] and runtimes["docker"]["image_local"]
            ) or (runtimes["java"]["supported"] and runtimes["java"]["war_local"]),
            "active_session": active,
            "repository_writes": False,
            "external_network_calls": False,
            "confirmation_performed": False,
            "architecture_acceptance_performed": False,
        }
    )
    return result


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Validate and view Program Kit's generated C4 projection.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "start", "stop"):
        command = subparsers.add_parser(name)
        command.add_argument("--project-root", default=".")
    inspect_parser = subparsers.choices["inspect"]
    inspect_parser.add_argument("--war")
    inspect_parser.add_argument("--port", type=int)
    inspect_parser.add_argument("--json", action="store_true")
    start_parser = subparsers.choices["start"]
    start_parser.add_argument("--war")
    start_parser.add_argument("--port", type=int)
    start_parser.add_argument("--runtime", choices=("auto", "docker", "java"), default="auto")
    start_parser.add_argument("--open", action="store_true")
    start_parser.add_argument("--detach", action="store_true")
    args = parser.parse_args()
    try:
        root = canonical_project_root(args.project_root)
        if args.command == "inspect":
            payload = inspection(root, args.war, args.port)
            if args.json:
                print(json.dumps(payload, indent=2))
            else:
                print(f"C4 projection is current and parseable: {payload['projection']}")
                print(f"Review mode: {payload['review_mode']}")
                print("Viewing does not confirm the intake or accept the architecture.")
                print(f"Managed Structurizr version: {payload['structurizr_version']}")
                print(f"Viewer ready: {str(payload['viewer_ready']).lower()}; selected port: {payload['port']}")
        elif args.command == "start":
            payload = start_session(root, args.runtime, args.port, args.war, args.open, args.detach)
            if payload.get("stopped"):
                print("Structurizr Local stopped and temporary viewer state removed.")
            else:
                print(f"Structurizr Local is available at {payload['url']}")
                print(f"Read-only review mode: {payload['review_mode']}")
                print("Viewing did not confirm the intake or accept the architecture.")
                print("The first diagram opens directly; use the left thumbnail rail to switch views.")
                print(
                    "A magnifier on an element opens a linked detail view; no magnifier means the "
                    "architecture map defines no deeper C4 view. Use +/- to zoom the canvas."
                )
                print("Stop and remove temporary viewer state with:")
                print("python .specify/extensions/program-kit-governance/scripts/c4_view.py stop --project-root .")
        else:
            stopped = stop_session(root, discover_runtimes(load_profile()))
            print("Structurizr Local stopped and temporary viewer state removed." if stopped else "No active C4 viewer session was recorded.")
    except (C4ViewError, OSError, UnicodeError, ValueError) as exc:
        print(f"Program Kit C4 viewer failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
