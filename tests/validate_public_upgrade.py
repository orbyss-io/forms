from __future__ import annotations

import argparse
import contextlib
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Iterator

import yaml


REPOSITORY = "https://raw.githubusercontent.com/orbyss-io/program-kit"
CURRENT = f"{REPOSITORY}/main/catalogs"
EXPECTED_HOOKS = {
    "before_constitution",
    "after_constitution",
    "before_specify",
    "after_specify",
    "after_plan",
    "after_tasks",
    "before_implement",
    "after_implement",
}


def run(*args: str, cwd: Path, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    # Desktop hosts can inject a named-pipe TLS key logger that crashes the
    # Windows Specify/OpenSSL process before catalog I/O begins.
    environment.pop("SSLKEYLOGFILE", None)
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            env=environment,
            input=input_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        output = "\n".join(value.strip() for value in (exc.stdout, exc.stderr) if value.strip())
        if output:
            print(output, file=sys.stderr)
        raise


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@contextlib.contextmanager
def candidate_catalogs(root: Path, artifacts: Path | None) -> Iterator[str]:
    if artifacts is None:
        yield CURRENT
        return

    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    required = {
        "extensions.json": root / "catalogs/extensions.json",
        "presets.json": root / "catalogs/presets.json",
        "workflows.json": root / "catalogs/workflows.json",
        "bundles.json": root / "catalogs/bundles.json",
        f"program-kit-governance-{version}.zip": artifacts / f"program-kit-governance-{version}.zip",
        f"program-kit-dotnet-{version}.zip": artifacts / f"program-kit-dotnet-{version}.zip",
        f"program-kit-governance-preset-{version}.zip": artifacts / f"program-kit-governance-preset-{version}.zip",
        f"program-kit-{version}.zip": artifacts / f"program-kit-{version}.zip",
        f"program-kit-bootstrap-{version}.yml": root / "workflows/program-kit-bootstrap/workflow.yml",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Candidate upgrade inputs are missing: {missing}")

    with tempfile.TemporaryDirectory(prefix="program-kit-candidate-catalog-") as directory:
        server_root = Path(directory)
        handler = lambda *args, **kwargs: QuietHandler(  # noqa: E731
            *args, directory=str(server_root), **kwargs
        )
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            for name, source in required.items():
                if name.endswith(".json"):
                    continue
                shutil.copyfile(source, server_root / name)

            for name in ("extensions.json", "presets.json", "workflows.json", "bundles.json"):
                value = json.loads(required[name].read_text(encoding="utf-8"))
                if name == "extensions.json":
                    for entry in value["extensions"].values():
                        entry["download_url"] = f"{base}/{Path(entry['download_url']).name}"
                elif name == "presets.json":
                    for entry in value["presets"].values():
                        entry["download_url"] = f"{base}/{Path(entry['download_url']).name}"
                elif name == "workflows.json":
                    for entry in value["workflows"].values():
                        entry["url"] = f"{base}/program-kit-bootstrap-{version}.yml"
                else:
                    for entry in value["bundles"].values():
                        entry["download_url"] = f"{base}/{Path(entry['download_url']).name}"
                (server_root / name).write_text(
                    json.dumps(value, indent=2) + "\n", encoding="utf-8"
                )
            yield base
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def tag_file(root: Path, tag: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{tag}:{relative}"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return result.stdout


@contextlib.contextmanager
def previous_release_catalogs(
    root: Path,
    tag: str,
    version: str,
    artifacts: Path | None,
) -> Iterator[str]:
    if artifacts is None:
        yield f"{REPOSITORY}/{tag}/catalogs"
        return

    archive_names = (
        f"program-kit-governance-{version}.zip",
        f"program-kit-dotnet-{version}.zip",
        f"program-kit-governance-preset-{version}.zip",
        f"program-kit-{version}.zip",
    )
    missing = [
        str(artifacts / name)
        for name in archive_names
        if not (artifacts / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(f"Previous release archives are missing: {missing}")

    with tempfile.TemporaryDirectory(prefix="program-kit-previous-catalog-") as directory:
        server_root = Path(directory)
        handler = lambda *args, **kwargs: QuietHandler(  # noqa: E731
            *args, directory=str(server_root), **kwargs
        )
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            for name in archive_names:
                shutil.copyfile(artifacts / name, server_root / name)
            workflow_name = f"program-kit-bootstrap-{version}.yml"
            (server_root / workflow_name).write_bytes(
                tag_file(root, tag, "workflows/program-kit-bootstrap/workflow.yml")
            )
            for name in ("extensions.json", "presets.json", "workflows.json", "bundles.json"):
                value = json.loads(tag_file(root, tag, f"catalogs/{name}"))
                if name == "extensions.json":
                    for entry in value["extensions"].values():
                        entry["download_url"] = f"{base}/{Path(entry['download_url']).name}"
                elif name == "presets.json":
                    for entry in value["presets"].values():
                        entry["download_url"] = f"{base}/{Path(entry['download_url']).name}"
                elif name == "workflows.json":
                    for entry in value["workflows"].values():
                        entry["url"] = f"{base}/{workflow_name}"
                else:
                    for entry in value["bundles"].values():
                        entry["download_url"] = f"{base}/{Path(entry['download_url']).name}"
                (server_root / name).write_text(
                    json.dumps(value, indent=2) + "\n", encoding="utf-8"
                )
            yield base
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def replace_catalogs(project: Path, base: str) -> None:
    specify = project / ".specify"
    (specify / "extension-catalogs.yml").write_text(
        yaml.safe_dump(
            {
                "catalogs": [
                    {
                        "name": "program-kit",
                        "url": f"{base}/extensions.json",
                        "priority": 10,
                        "install_allowed": True,
                        "description": "Program Kit upgrade regression",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (specify / "workflow-catalogs.yml").write_text(
        yaml.safe_dump(
            {
                "catalogs": [
                    {
                        "name": "program-kit",
                        "url": f"{base}/workflows.json",
                        "priority": 1,
                        "install_allowed": True,
                        "description": "Program Kit upgrade regression",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (specify / "preset-catalogs.yml").write_text(
        yaml.safe_dump(
            {
                "catalogs": [
                    {
                        "name": "program-kit",
                        "url": f"{base}/presets.json",
                        "priority": 10,
                        "install_allowed": True,
                        "description": "Program Kit upgrade regression",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (specify / "bundle-catalogs.yml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "catalogs": [
                    {
                        "id": "program-kit",
                        "url": f"{base}/bundles.json",
                        "priority": 10,
                        "install_policy": "install-allowed",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def previous_stable(root: Path, current_version: str) -> tuple[str, str]:
    current = tuple(int(part) for part in current_version.split("."))
    result = subprocess.run(
        ["git", "tag", "--list", "v*.*.*"],
        cwd=root,
        text=True,
        check=True,
        capture_output=True,
    )
    candidates: list[tuple[tuple[int, int, int], str]] = []
    for tag in result.stdout.splitlines():
        match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag.strip())
        if match is None:
            continue
        parsed = tuple(int(part) for part in match.groups())
        if parsed < current:
            candidates.append((parsed, tag.strip()))
    if not candidates:
        raise RuntimeError(f"No stable tag precedes v{current_version}")
    version, tag = max(candidates)
    return ".".join(str(part) for part in version), tag


def manifest_version(path: Path, section: str) -> str:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value[section]["version"]


def installed_versions(project: Path) -> dict[str, str]:
    specify = project / ".specify"
    registry = json.loads(
        (specify / "workflows/workflow-registry.json").read_text(encoding="utf-8")
    )
    records = json.loads((specify / "bundle-records.json").read_text(encoding="utf-8"))
    bundle = next(record for record in records["bundles"] if record["bundle_id"] == "program-kit")
    extension_record = next(
        component
        for component in bundle["contributed_components"]
        if component["kind"] == "extensions"
        and component["id"] == "program-kit-governance"
    )
    dotnet_extension_record = next(
        component
        for component in bundle["contributed_components"]
        if component["kind"] == "extensions"
        and component["id"] == "program-kit-dotnet"
    ) if any(
        component["kind"] == "extensions" and component["id"] == "program-kit-dotnet"
        for component in bundle["contributed_components"]
    ) else None
    versions = {
        "extension": manifest_version(
            specify / "extensions/program-kit-governance/extension.yml", "extension"
        ),
        "workflow": manifest_version(
            specify / "workflows/program-kit-bootstrap/workflow.yml", "workflow"
        ),
        "workflow registry": registry["workflows"]["program-kit-bootstrap"]["version"],
        "bundle record": bundle["version"],
        "bundle extension record": extension_record["version"],
    }
    if dotnet_extension_record is not None:
        versions["dotnet extension"] = manifest_version(
            specify / "extensions/program-kit-dotnet/extension.yml", "extension"
        )
        versions["bundle .NET extension record"] = dotnet_extension_record["version"]
    return versions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate upgrading the previous stable Program Kit release to the current one."
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        help="Use locally built candidate archives instead of the public current-release catalogs.",
    )
    parser.add_argument(
        "--previous-dir",
        type=Path,
        help="Use cached previous-release archives instead of its public catalogs.",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    current_version = (root / "VERSION").read_text(encoding="utf-8").strip()
    previous_version, previous_tag = previous_stable(root, current_version)
    source_workflow = yaml.safe_load(
        (root / "workflows/program-kit-bootstrap/workflow.yml").read_text(
            encoding="utf-8"
        )
    )
    expected_steps = [step["id"] for step in source_workflow.get("steps", [])]
    artifacts = args.candidate_dir.resolve() if args.candidate_dir else None
    previous_artifacts = args.previous_dir.resolve() if args.previous_dir else None
    with candidate_catalogs(root, artifacts) as current_catalogs, previous_release_catalogs(
        root, previous_tag, previous_version, previous_artifacts
    ) as previous_catalogs, tempfile.TemporaryDirectory(
        prefix="program-kit-public-upgrade-"
    ) as directory:
        project = Path(directory)
        run(
            "specify",
            "init",
            ".",
            "--force",
            "--non-interactive",
            "--integration",
            "codex",
            "--ignore-agent-tools",
            cwd=project,
        )
        replace_catalogs(project, previous_catalogs)

        # Reproduce a genuine installation of the immediately preceding stable release, including
        # the Spec Kit 1.0.1 workflow-preinstallation workaround.
        run("specify", "workflow", "add", "program-kit-bootstrap", cwd=project)
        run("specify", "bundle", "install", "program-kit", cwd=project)
        initial = installed_versions(project)
        if set(initial.values()) != {previous_version}:
            raise AssertionError(
                f"Expected a coherent v{previous_version} installation, got {initial}"
            )

        # Older initializers registered immutable release-tag catalogs. Replace
        # them through the public CLI before updating so "latest" can advance.
        run("specify", "extension", "catalog", "remove", "program-kit", cwd=project)
        run("specify", "preset", "catalog", "remove", "program-kit", cwd=project)
        run("specify", "workflow", "catalog", "remove", "0", cwd=project)
        run("specify", "bundle", "catalog", "remove", "program-kit", cwd=project)
        run(
            "specify", "extension", "catalog", "add", f"{current_catalogs}/extensions.json",
            "--name", "program-kit", "--install-allowed", cwd=project,
        )
        run(
            "specify", "preset", "catalog", "add", f"{current_catalogs}/presets.json",
            "--name", "program-kit", "--install-allowed", cwd=project,
        )
        run(
            "specify", "workflow", "catalog", "add", f"{current_catalogs}/workflows.json",
            "--name", "program-kit", cwd=project,
        )
        run(
            "specify", "bundle", "catalog", "add", f"{current_catalogs}/bundles.json",
            "--id", "program-kit", "--policy", "install-allowed", cwd=project,
        )

        # Capture the historical unsafe order. Bundle update refreshes the
        # extension and bundle record, but cannot refresh the separately owned
        # workflow in Spec Kit 1.0.1.
        run(
            "specify",
            "bundle",
            "update",
            "program-kit",
            "--integration",
            "codex",
            cwd=project,
            input_text="y\n",
        )
        mixed = installed_versions(project)
        if mixed["workflow"] != previous_version or mixed["extension"] != current_version:
            raise AssertionError(f"Regression did not reproduce the mixed installation: {mixed}")

        governance = (
            project
            / ".specify/extensions/program-kit-governance/scripts/governance_state.py"
        )
        preflight = subprocess.run(
            [sys.executable, str(governance), "validate-installation"],
            cwd=project,
            text=True,
            capture_output=True,
        )
        output = preflight.stdout + preflight.stderr
        if preflight.returncode == 0:
            raise AssertionError("Mixed-version installation unexpectedly passed preflight")
        for phrase in (
            "version-incoherent",
            "upgrade_program_kit.py",
        ):
            if phrase not in output:
                raise AssertionError(f"Preflight output is missing {phrase!r}: {output}")

        # Apply the documented repair in the mandatory order.
        run(
            "specify",
            "workflow",
            "update",
            "program-kit-bootstrap",
            cwd=project,
            input_text="y\n",
        )
        run(
            "specify",
            "bundle",
            "update",
            "program-kit",
            "--integration",
            "codex",
            cwd=project,
            input_text="y\n",
        )
        repaired = installed_versions(project)
        if set(repaired.values()) != {current_version}:
            raise AssertionError(
                f"Upgrade repair did not converge on v{current_version}: {repaired}"
            )
        run(sys.executable, str(governance), "validate-installation", cwd=project)

        extensions = yaml.safe_load(
            (project / ".specify/extensions.yml").read_text(encoding="utf-8")
        )
        hooks = set(extensions.get("hooks", {}))
        if hooks != EXPECTED_HOOKS:
            raise AssertionError(f"Installed hooks {sorted(hooks)} != {sorted(EXPECTED_HOOKS)}")

        workflow = yaml.safe_load(
            (
                project / ".specify/workflows/program-kit-bootstrap/workflow.yml"
            ).read_text(encoding="utf-8")
        )
        step_ids = [step["id"] for step in workflow.get("steps", [])]
        if step_ids != expected_steps:
            raise AssertionError(f"Installed workflow steps {step_ids} != {expected_steps}")

    print(
        f"Live public-catalog v{previous_version} to v{current_version} upgrade test passed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
