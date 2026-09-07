from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model(intent: Path, documentation: Path) -> dict:
    common = {
        "ownership": "Project",
        "technology": "",
        "evidence": ["e-001"],
        "decision_refs": [],
        "tags": [],
        "properties": {},
        "perspectives": [],
        "url": "",
        "group": "",
        "archetype": "",
    }
    return {
        "schema_version": "1.0",
        "model_id": "review-system",
        "title": "Review system",
        "sources": [
            {
                "id": "project-intent",
                "path": "docs/architecture/project-intent.md",
                "sha256": digest(intent),
                "format": "program-kit-intent-markdown",
                "importer": {"id": "program-kit-intake", "version": "1.0"},
            }
        ],
        "decisions": [],
        "documentation": [
            {
                "id": "architecture-readme",
                "path": "docs/architecture/README.md",
                "sha256": digest(documentation),
                "scope": "Architecture review",
            }
        ],
        "constraints": [],
        "elements": [
            {
                "id": "reviewer",
                "type": "person",
                "name": "Reviewer",
                "description": "Reviews the architecture.",
                "status": "explicit",
                **{**common, "ownership": ""},
            },
            {
                "id": "review-system",
                "type": "software-system",
                "name": "Review system",
                "description": "Provides the review surface.",
                "status": "proposed",
                **common,
            },
            {
                "id": "review-context",
                "type": "bounded-context",
                "name": "Review context",
                "description": "Owns review behavior.",
                "status": "proposed",
                **common,
            },
        ],
        "relationships": [
            {
                "id": "reviews",
                "source": "reviewer",
                "target": "review-system",
                "description": "Reviews",
                "technology": "HTTPS",
                "status": "explicit",
                "evidence": ["e-001"],
                "decision_refs": [],
                "tags": [],
                "properties": {},
                "perspectives": [],
                "url": "",
            }
        ],
        "views": [
            {
                "key": "system-context",
                "type": "system-context",
                "title": "System Context",
                "description": "Review boundary",
                "scope": "review-system",
                "elements": ["reviewer", "review-system"],
                "relationships": ["reviews"],
                "decision_refs": [],
                "filters": [],
                "order": [],
                "layout": {"rankDirection": "lr"},
                "animations": [],
                "properties": {},
            },
            {
                "key": "domain-context",
                "type": "domain-context",
                "title": "Domain Context",
                "description": "Review domain",
                "scope": "",
                "elements": ["review-system", "review-context"],
                "relationships": [],
                "decision_refs": [],
                "filters": [],
                "order": [],
                "layout": {"rankDirection": "lr"},
                "animations": [],
                "properties": {},
            },
        ],
        "configuration": {
            "styles": [],
            "themes": [],
            "terminology": {},
            "branding": {},
            "properties": {},
        },
        "extensions": [],
    }


def create_project(root: Path, architecture, value: dict | None = None) -> dict:
    intent = root / "docs/architecture/project-intent.md"
    documentation = root / "docs/architecture/README.md"
    write(intent, "# Intent\n\nA reviewer inspects the system.\n")
    write(documentation, "# Architecture\n")
    value = value or model(intent, documentation)
    map_path = root / "docs/architecture/architecture-map.json"
    dsl_path = root / "docs/architecture/workspace.dsl"
    write(map_path, json.dumps(value, indent=2) + "\n")
    write(dsl_path, architecture.StructurizrDslExporter().export(value))
    intake = {
        "schema_version": "1.0",
        "status": "confirmed",
        "artifacts": {
            "project_intent": {
                "path": "docs/architecture/project-intent.md",
                "sha256": digest(intent),
                "bytes": intent.stat().st_size,
            },
            "architecture_map": {
                "path": "docs/architecture/architecture-map.json",
                "sha256": digest(map_path),
                "bytes": map_path.stat().st_size,
            },
            "c4_projection": {
                "path": "docs/architecture/workspace.dsl",
                "sha256": digest(dsl_path),
                "bytes": dsl_path.stat().st_size,
            },
        },
    }
    write(root / "docs/architecture/bootstrap-intake.json", json.dumps(intake, indent=2) + "\n")
    return value


def snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): digest(path)
        for path in root.rglob("*")
        if path.is_file()
    }


def expect_failure(action, text: str) -> None:
    try:
        action()
    except Exception as exc:
        if text not in str(exc):
            raise AssertionError(f"Expected {text!r} in {exc!r}") from exc
        return
    raise AssertionError(f"Expected failure containing {text!r}")


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    scripts = repository / "extensions/program-kit-governance/scripts"
    architecture = load_module(scripts / "architecture_map.py", "test_c4_architecture")
    viewer = load_module(scripts / "c4_view.py", "test_c4_viewer")

    profile = viewer.load_profile()
    if profile["selected"]["version"] in {"", "latest"}:
        raise AssertionError("Structurizr viewer must use an exact managed version")
    if not profile["selected"]["docker_digest"].startswith("sha256:"):
        raise AssertionError("Structurizr viewer image has no tested registry digest")
    if not profile["selected"]["java_war_url"].endswith(f"/{profile['selected']['java_war']}"):
        raise AssertionError("Structurizr WAR retrieval does not bind the exact managed filename")
    if profile["selected"]["default_port"] != 8081:
        raise AssertionError("C4 viewer must avoid Program Kit's Keycloak port 8080")
    if viewer.java_major('openjdk version "21.0.8"') != 21:
        raise AssertionError("Java runtime parsing did not recognize Java 21")
    if viewer.java_major('java version "1.8.0_411"') != 8:
        raise AssertionError("Java runtime parsing did not recognize legacy Java 8")

    with tempfile.TemporaryDirectory(prefix="Program Kit C4 tests ") as directory:
        tests_root = Path(directory)
        os.environ[viewer.STATE_ENVIRONMENT] = str(tests_root / "viewer state")
        project = tests_root / "consumer repository with spaces"
        value = create_project(project, architecture)

        valid = viewer.validate_projection(project)
        if not valid["projection_current"] or valid["intake_binding"] != "confirmed-intake":
            raise AssertionError(f"Current projection was not accepted: {valid}")
        if valid["primary_view_key"] != "system-context":
            raise AssertionError(f"Viewer did not select the first generated diagram: {valid}")
        if viewer.diagram_url(8081, valid["primary_view_key"]) != (
            "http://localhost:8081/workspace/1/diagrams#system-context"
        ):
            raise AssertionError("Viewer did not build a direct, local diagram URL")

        before = snapshot(project)
        data = viewer.session_directory(project) / "data"
        data.parent.mkdir(parents=True)
        viewer.stage_projection(project, data)
        if not (data / "workspace.dsl").is_file() or not (data / "docs/architecture/README.md").is_file():
            raise AssertionError("Temporary viewer staging lost the DSL or its documentation input")
        if snapshot(project) != before:
            raise AssertionError("View-only staging changed the consumer repository")
        viewer.cleanup_directory(project)

        dsl_path = project / "docs/architecture/workspace.dsl"
        original_dsl = dsl_path.read_text(encoding="utf-8")
        for expected_style in ("background #2563EB", "ProgramKitStatus:proposed", "routing Orthogonal"):
            if expected_style not in original_dsl:
                raise AssertionError(f"Generated projection omitted review styling: {expected_style}")
        write(dsl_path, original_dsl + "// manual edit\n")
        expect_failure(lambda: viewer.validate_projection(project), "stale relative")
        write(dsl_path, "workspace {\n")
        expect_failure(lambda: viewer.validate_projection(project), "malformed")
        write(dsl_path, original_dsl)
        dsl_path.unlink()
        expect_failure(lambda: viewer.validate_projection(project), "C4 projection is missing")
        write(dsl_path, original_dsl)

        intake_path = project / "docs/architecture/bootstrap-intake.json"
        registered = json.loads(intake_path.read_text(encoding="utf-8"))
        value["title"] = "Evolved review system"
        write(project / "docs/architecture/architecture-map.json", json.dumps(value, indent=2) + "\n")
        write(dsl_path, architecture.StructurizrDslExporter().export(value))
        evolved = viewer.validate_projection(project)
        if evolved["intake_binding"] != "evolved-together-from-confirmed-intake":
            raise AssertionError("A current generated pair did not report its older intake binding")
        registered["artifacts"]["architecture_map"]["sha256"] = digest(project / "docs/architecture/architecture-map.json")
        registered["artifacts"]["architecture_map"]["bytes"] = (project / "docs/architecture/architecture-map.json").stat().st_size
        write(intake_path, json.dumps(registered, indent=2) + "\n")
        expect_failure(lambda: viewer.validate_projection(project), "partial architecture drift")

        create_project(project, architecture, model(project / "docs/architecture/project-intent.md", project / "docs/architecture/README.md"))
        state = {
            "schema_version": "1.0",
            "project_root": str(project),
            "runtime": "java",
            "pid": os.getpid(),
            "port": 8081,
            "url": "http://localhost:8081/",
            "projection_sha256": digest(project / "docs/architecture/workspace.dsl"),
            "data_directory": str(viewer.session_directory(project) / "data"),
        }
        viewer.write_state(project, state)
        active_inspection = viewer.inspection(project)
        if active_inspection["port"] != 8081 or not active_inspection["active_session"]:
            raise AssertionError("Inspection did not report the recorded active viewer and its port")
        repeated = viewer.start_session(project, "auto", None, None, False, True)
        if not repeated.get("reused") or repeated["pid"] != os.getpid():
            raise AssertionError("Repeated invocation did not reuse the collision-safe active session")
        viewer.cleanup_directory(project)

        calls: list[list[str]] = []
        viewer.write_state(
            project,
            {
                "schema_version": "1.0",
                "runtime": "docker",
                "container": f"program-kit-c4-{viewer.session_identifier(project)}",
            },
        )
        expect_failure(
            lambda: viewer.stop_session(
                project, {"docker": {"path": "docker", "daemon_available": False}}
            ),
            "temporary state was preserved",
        )
        if not viewer.session_directory(project).is_dir():
            raise AssertionError("Inaccessible Docker caused the recoverable session state to be deleted")
        original_capture = viewer.run_capture
        viewer.run_capture = lambda arguments, timeout=10: (
            calls.append(list(arguments))
            or subprocess.CompletedProcess(list(arguments), 0, "", "")
        )
        try:
            if not viewer.stop_session(project, {"docker": {"path": "docker", "daemon_available": True}}):
                raise AssertionError("Recorded viewer was not stopped")
        finally:
            viewer.run_capture = original_capture
        if not calls or calls[0][1:4] != ["container", "rm", "--force"]:
            raise AssertionError(f"Cleanup did not target the exact recorded container: {calls}")
        if viewer.session_directory(project).exists():
            raise AssertionError("Cleanup retained temporary viewer state")

        windows_data = Path("C:/Repositories/Program Kit review/viewer data")
        docker_command = viewer.build_docker_command(
            "docker.exe", profile["selected"]["docker_image"], windows_data, "program-kit-c4-abc", 8081
        )
        expected_mount = f"{os.fspath(windows_data)}:/usr/local/structurizr"
        if docker_command[-3] != expected_mount:
            raise AssertionError("Windows path with spaces was split or lost in Docker command construction")
        rendered_windows = viewer.render_command(docker_command, "nt")
        if '"' not in rendered_windows or "latest" in docker_command:
            raise AssertionError("Windows command diagnostics did not quote the spaced mount path")
        posix_command = viewer.build_java_command(
            "/usr/bin/java", PurePosixPath("/opt/Program Kit/structurizr.war"), PurePosixPath("/tmp/review packet"), 8082
        )
        if "/tmp/review packet" not in posix_command or "'/tmp/review packet'" not in viewer.render_command(posix_command, "posix"):
            raise AssertionError("POSIX path handling did not preserve a spaced argument")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
            occupied.bind(("127.0.0.1", 0))
            port = occupied.getsockname()[1]
            if port < 65535 and viewer.select_port(port, 2) != port + 1:
                raise AssertionError("Port selection did not avoid an occupied localhost port")
        if viewer.select_port(8081) == 8080:
            raise AssertionError("Port selection regressed to the Keycloak default")

        docker_missing = {
            "docker": {"daemon_available": True, "image_local": False, "diagnostic": "image missing"},
            "java": {"supported": False, "war_local": False, "diagnostic": "java unavailable"},
        }
        expect_failure(lambda: viewer.choose_runtime(docker_missing, "auto"), "image missing")
        java_ready = {
            "docker": {"daemon_available": False, "image_local": False, "diagnostic": "docker unavailable"},
            "java": {"supported": True, "war_local": True, "diagnostic": "java ready"},
        }
        if viewer.choose_runtime(java_ready, "auto") != "java":
            raise AssertionError("Supported local Java/WAR fallback was not selected")

        discovery_before = snapshot(project)
        original_which = viewer.shutil.which
        original_capture = viewer.run_capture
        observed: list[list[str]] = []
        viewer.shutil.which = lambda name: "docker" if name == "docker" else None
        viewer.run_capture = lambda arguments, timeout=10: (
            observed.append(list(arguments))
            or subprocess.CompletedProcess(
                list(arguments),
                0 if arguments[1] == "version" else 1,
                "29.0.1\n" if arguments[1] == "version" else "",
                "image absent" if arguments[1] != "version" else "",
            )
        )
        try:
            discovery = viewer.discover_runtimes(profile)
        finally:
            viewer.shutil.which = original_which
            viewer.run_capture = original_capture
        if discovery["docker"]["image_local"] or any("pull" in command for command in observed):
            raise AssertionError("Runtime discovery pulled or treated the missing pinned image as local")
        if snapshot(project) != discovery_before:
            raise AssertionError("Runtime discovery changed the consumer repository")
        del os.environ[viewer.STATE_ENVIRONMENT]

    print("C4 projection viewing validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
