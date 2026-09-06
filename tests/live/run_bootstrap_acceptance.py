from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import IO


AGENT_ENVIRONMENT_KEYS = (
    "CODEX_SESSION_ID",
    "CODEX_THREAD_ID",
    "CODEX_INTERNAL_ORIGINATOR_OVERRIDE",
)
CI_ENVIRONMENT_KEYS = ("CI", "GITHUB_ACTIONS", "TF_BUILD", "BUILD_BUILDID")


class AcceptanceError(RuntimeError):
    pass


class QuietCatalogHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def git_excludes_override() -> str:
    """Disable inaccessible global excludes without using Windows' rejected NUL path."""
    return "" if os.name == "nt" else os.devnull


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AcceptanceError(f"Expected a JSON object in {path}")
    return value


def run_logged(command: list[str], cwd: Path, log: IO[str]) -> None:
    printable = subprocess.list2cmdline(command)
    log.write(f"\n$ {printable}\n")
    log.flush()
    result = subprocess.run(
        command,
        cwd=cwd,
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise AcceptanceError(f"Setup command exited with {result.returncode}: {printable}")


def run_logged_with_catalog_retry(
    command: list[str], cwd: Path, log: IO[str], attempts: int = 3
) -> None:
    """Retry only a known transient local-catalog archive transfer failure."""
    printable = subprocess.list2cmdline(command)
    for attempt in range(1, attempts + 1):
        log.write(f"\n$ {printable} (attempt {attempt}/{attempts})\n")
        log.flush()
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        log.write(output)
        log.flush()
        if result.returncode == 0:
            return
        retryable = (
            re.search(r"Failed to save extension\s+archive", output) is not None
            and "No changes were recorded" in output
        )
        if not retryable or attempt == attempts:
            raise AcceptanceError(
                f"Setup command exited with {result.returncode}: {printable}"
            )
        log.write("Transient localhost catalog transfer reset; retrying unchanged install.\n")
        log.flush()
        time.sleep(1)


def specify_bridge_command(root: Path, *arguments: str) -> list[str]:
    site_packages = Path(sysconfig.get_paths()["purelib"]).resolve()
    return [
        sys.executable,
        str(root / "scripts/invoke_specify.py"),
        "--site-packages",
        str(site_packages),
        "--",
        *arguments,
    ]


def install_local_candidate_bundle(
    root: Path,
    project: Path,
    packages: Path,
    integration: str,
    log: IO[str],
) -> None:
    commands = (
        ("workflow", "add", str(packages / "workflow"), "--dev"),
        ("extension", "add", str(packages / "governance"), "--dev", "--force"),
        ("extension", "add", str(packages / "dotnet"), "--dev", "--force"),
        ("preset", "add", "--dev", str(packages / "preset")),
        (
            "bundle",
            "install",
            str(packages / "bundle/bundle.yml"),
            "--offline",
            "--integration",
            integration,
        ),
    )
    log.write(
        "Windows local-catalog downloads are unavailable in this installed Python/OpenSSL runtime; "
        "installing the extracted candidate components before recording the real offline bundle.\n"
    )
    log.flush()
    for arguments in commands:
        run_logged(specify_bridge_command(root, *arguments), project, log)


def safe_extract(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    destination_root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            try:
                target.relative_to(destination_root)
            except ValueError as exc:
                raise AcceptanceError(
                    f"Archive entry escapes extraction directory: {member.filename}"
                ) from exc
        archive.extractall(destination)


def prepare_local_catalog_server(
    root: Path,
    artifacts: Path,
    packages: Path,
    evidence: Path,
    version: str,
) -> tuple[http.server.ThreadingHTTPServer, threading.Thread, str]:
    server_root = evidence / "catalog-server"
    server_root.mkdir(parents=True, exist_ok=False)
    archive_names = {
        "governance": f"program-kit-governance-{version}.zip",
        "dotnet": f"program-kit-dotnet-{version}.zip",
        "preset": f"program-kit-governance-preset-{version}.zip",
    }
    for archive_name in archive_names.values():
        shutil.copy2(artifacts / archive_name, server_root / archive_name)
    shutil.copy2(packages / "workflow" / "workflow.yml", server_root / "workflow.yml")

    handler = functools.partial(QuietCatalogHandler, directory=str(server_root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    base_url = f"http://127.0.0.1:{server.server_port}"

    catalogs = {
        name: load_json(root / "catalogs" / f"{name}.json")
        for name in ("extensions", "presets", "workflows")
    }
    catalogs["extensions"]["catalog_url"] = f"{base_url}/extensions.json"
    catalogs["extensions"]["extensions"]["program-kit-governance"]["download_url"] = (
        f"{base_url}/{archive_names['governance']}"
    )
    catalogs["extensions"]["extensions"]["program-kit-dotnet"]["download_url"] = (
        f"{base_url}/{archive_names['dotnet']}"
    )
    catalogs["presets"]["catalog_url"] = f"{base_url}/presets.json"
    catalogs["presets"]["presets"]["program-kit-governance-preset"]["download_url"] = (
        f"{base_url}/{archive_names['preset']}"
    )
    catalogs["workflows"]["catalog_url"] = f"{base_url}/workflows.json"
    catalogs["workflows"]["workflows"]["program-kit-bootstrap"]["url"] = (
        f"{base_url}/workflow.yml"
    )
    for name, catalog in catalogs.items():
        write_json(server_root / f"{name}.json", catalog)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, base_url


def stream_pipe(pipe: IO[str], destination: Path, display: IO[str] | None = None) -> None:
    with destination.open("w", encoding="utf-8", newline="\n") as log:
        for line in iter(pipe.readline, ""):
            log.write(line)
            log.flush()
            if display is not None:
                display.write(line)
                display.flush()
    pipe.close()


def discover_run_state(
    project: Path, excluded_run_ids: set[str] | None = None
) -> tuple[Path | None, dict | None]:
    excluded_run_ids = excluded_run_ids or set()
    candidates = sorted(
        (
            path
            for path in (project / ".specify/workflows/runs").glob("*/state.json")
            if path.parent.name not in excluded_run_ids
        ),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    if not candidates:
        return None, None
    path = candidates[0]
    try:
        return path, load_json(path)
    except (OSError, json.JSONDecodeError, AcceptanceError):
        return path, None


def read_run_state(project: Path, run_id: str | None) -> tuple[Path | None, dict | None]:
    if not run_id:
        return discover_run_state(project)
    path = project / ".specify/workflows/runs" / run_id / "state.json"
    if not path.is_file():
        return path, None
    try:
        return path, load_json(path)
    except (OSError, json.JSONDecodeError, AcceptanceError):
        return path, None


def append_monitor(path: Path, payload: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_worker_guidance(project: Path, integration: str) -> None:
    if integration != "codex":
        return
    safe_directory = project.resolve().as_posix()
    excludes_override = git_excludes_override().replace("\\", "/")
    guidance = f"""# Disposable live-acceptance worker guidance

This repository is owned by the Program Kit live acceptance harness and is safe to modify within
the requested bootstrap workflow. The Codex worker is intentionally launched with
`--sandbox workspace-write`.

Windows sandbox workers may see a different SID from the repository owner. For every Git command,
use the command-scoped form
`git -c safe.directory={safe_directory} -c core.excludesFile={excludes_override} <command>`. On
Windows the value is deliberately empty because Git rejects `NUL` as an excludes file; on POSIX it
is `/dev/null`. The override prevents harmless permission warnings when the sandbox cannot read the
user's global Git ignore file. Never run `git config --global`, never disable the sandbox, and never add a
persistent safe-directory entry.

Use UTF-8 for Python subprocess output. Read compact bootstrap stage briefs first; do not print
complete evidence indexes, generated artifacts, or repository-wide diffs. Report concise counts,
paths, and validation results.
"""
    destination = project / "AGENTS.md"
    if destination.is_file():
        existing = destination.read_text(encoding="utf-8").rstrip()
        guidance = existing + "\n\n---\n\n" + guidance
    destination.write_text(guidance, encoding="utf-8", newline="\n")


def load_monitor(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def analyze_metrics(
    evidence: Path, run_id: str | None, workflow_duration: float | None = None
) -> dict:
    stderr_path = evidence / "workflow.stderr.log"
    stdout_path = evidence / "workflow.stdout.log"
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
    token_values = [int(value.replace(",", "")) for value in re.findall(r"tokens used\s*[\r\n]+\s*([0-9,]+)", stderr_text)]
    intake_stderr_path = evidence / "intake.stderr.log"
    intake_stderr = (
        intake_stderr_path.read_text(encoding="utf-8", errors="replace")
        if intake_stderr_path.is_file()
        else ""
    )
    intake_token_values = [
        int(value.replace(",", ""))
        for value in re.findall(r"tokens used\s*[\r\n]+\s*([0-9,]+)", intake_stderr)
    ]
    agent_stages = (
        "assessment",
        "research",
        "constitution-draft",
        "architecture",
        "tooling",
        "specification-roadmap",
        "readiness",
    )
    monitor = load_monitor(evidence / "monitor.jsonl")
    observed_steps = {
        record.get("current_step_id")
        for record in monitor
        if isinstance(record.get("current_step_id"), str)
    }
    observed_agent_stages = [stage for stage in agent_stages if stage in observed_steps]
    stage_tokens = dict(zip(observed_agent_stages, token_values))
    if intake_token_values:
        stage_tokens = {"intake-skill": sum(intake_token_values), **stage_tokens}
    unattributed_tokens = token_values[len(observed_agent_stages) :]
    stage_durations: dict[str, float] = {}
    for index, record in enumerate(monitor[:-1]):
        step = record.get("current_step_id")
        start = record.get("elapsed_seconds")
        end = monitor[index + 1].get("elapsed_seconds")
        if isinstance(step, str) and isinstance(start, (int, float)) and isinstance(end, (int, float)):
            stage_durations[step] = round(float(end) - float(start), 3)
    if monitor and workflow_duration is not None:
        final_record = monitor[-1]
        final_step = final_record.get("current_step_id")
        final_start = final_record.get("elapsed_seconds")
        if (
            final_record.get("status") == "running"
            and isinstance(final_step, str)
            and isinstance(final_start, (int, float))
            and workflow_duration > float(final_start)
        ):
            stage_durations[final_step] = round(workflow_duration - float(final_start), 3)
    contexts: dict[str, dict] = {}
    if run_id:
        context_root = evidence / "project/.specify/workflows/runs" / run_id / "program-kit-context"
        for path in sorted(context_root.glob("*.json")):
            label = path.name
            contexts[label] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    artifacts: dict[str, dict] = {}
    artifact_root = evidence / "project/docs/architecture"
    if artifact_root.is_dir():
        for path in sorted(item for item in artifact_root.rglob("*") if item.is_file()):
            label = path.relative_to(evidence / "project").as_posix()
            artifacts[label] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    return {
        "agent_session_count": len(token_values) + len(intake_token_values),
        "agent_tokens_total": sum(token_values) + sum(intake_token_values),
        "agent_tokens_by_stage": stage_tokens,
        "unattributed_agent_tokens": unattributed_tokens,
        "stage_duration_seconds": stage_durations,
        "workflow_stdout_bytes": stdout_path.stat().st_size if stdout_path.is_file() else 0,
        "workflow_stderr_bytes": stderr_path.stat().st_size if stderr_path.is_file() else 0,
        "contexts": contexts,
        "artifacts": artifacts,
    }


def performance_warnings(metrics: dict, budgets: dict) -> list[str]:
    warnings: list[str] = []
    total_budget = budgets.get("agent_tokens_total")
    if isinstance(total_budget, int) and metrics.get("agent_tokens_total", 0) > total_budget:
        warnings.append(
            f"Agent token total {metrics['agent_tokens_total']} exceeds advisory budget {total_budget}"
        )
    stderr_budget = budgets.get("workflow_stderr_bytes")
    if isinstance(stderr_budget, int) and metrics.get("workflow_stderr_bytes", 0) > stderr_budget:
        warnings.append(
            f"Workflow stderr {metrics['workflow_stderr_bytes']} bytes exceeds advisory budget {stderr_budget}"
        )
    context_budget = budgets.get("stage_brief_bytes")
    if isinstance(context_budget, int):
        for name, record in metrics.get("contexts", {}).items():
            if name.endswith(".evidence.json"):
                continue
            if record.get("bytes", 0) > context_budget:
                warnings.append(
                    f"Stage brief {name} is {record['bytes']} bytes; advisory budget is {context_budget}"
                )
    artifact_budgets = budgets.get("artifact_bytes", {})
    if isinstance(artifact_budgets, dict):
        for name, budget in artifact_budgets.items():
            record = metrics.get("artifacts", {}).get(name)
            if isinstance(budget, int) and record and record.get("bytes", 0) > budget:
                warnings.append(
                    f"Artifact {name} is {record['bytes']} bytes; advisory budget is {budget}"
                )
    return warnings


def terminate_owned_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def worker_environment(project: Path, integration: str) -> tuple[dict[str, str], list[str], dict[str, object]]:
    environment = os.environ.copy()
    removed = [key for key in AGENT_ENVIRONMENT_KEYS if environment.pop(key, None)]
    environment["PROGRAM_KIT_LIVE_ACCEPTANCE"] = "clean-bootstrap"
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    worker_settings: dict[str, object] = {}
    if integration == "codex":
        environment["SPECKIT_INTEGRATION_CODEX_EXTRA_ARGS"] = "--sandbox workspace-write"
        try:
            git_config_count = int(environment.get("GIT_CONFIG_COUNT", "0"))
        except ValueError as exc:
            raise AcceptanceError("GIT_CONFIG_COUNT must be an integer") from exc
        environment[f"GIT_CONFIG_KEY_{git_config_count}"] = "safe.directory"
        environment[f"GIT_CONFIG_VALUE_{git_config_count}"] = str(project)
        environment[f"GIT_CONFIG_KEY_{git_config_count + 1}"] = "core.excludesFile"
        excludes_override = git_excludes_override()
        environment[f"GIT_CONFIG_VALUE_{git_config_count + 1}"] = excludes_override
        environment["GIT_CONFIG_COUNT"] = str(git_config_count + 2)
        worker_settings = {
            "sandbox": "workspace-write",
            "git_safe_directory": str(project),
            "git_safe_directory_parent_scope": "workflow-process-only-best-effort",
            "git_safe_directory_worker_fallback": (
                f"git -c safe.directory={project.resolve().as_posix()} "
                f"-c core.excludesFile={excludes_override} <command>"
            ),
            "git_excludes_file_process_scope": excludes_override,
            "global_git_configuration_modified": False,
        }
    return environment, removed, worker_settings


def run_intake_skill(
    codex: str,
    project: Path,
    evidence: Path,
    timeout_seconds: int,
) -> tuple[int, float]:
    final_message = project / ".program-kit-live/intake.final.txt"
    final_message.parent.mkdir(parents=True, exist_ok=True)
    prompt = (
        "Use $speckit-program-kit-governance-bootstrap. Treat PROJECT_REQUEST.md as the user's "
        "complete initial description and explicit confirmation. Conduct the skill exactly as installed, "
        "create and validate all canonical intake artifacts, and finish with its required single-line "
        "bootstrap command. Do not run the bootstrap workflow. This is a disposable live-acceptance "
        "repository; preserve concise evidence in the repository and do not merely describe the files."
    )
    command = [
        codex,
        "exec",
        "--sandbox",
        "workspace-write",
        "--cd",
        str(project),
        "--json",
        "--output-last-message",
        str(final_message),
        prompt,
    ]
    environment, removed, worker_settings = worker_environment(project, "codex")
    write_json(
        evidence / "intake.invocation.json",
        {
            "command": command,
            "cwd": str(project),
            "integration": "codex",
            "started_at": utc_now(),
            "agent_environment_keys_removed_from_disposable_child": removed,
            "worker_settings": worker_settings,
        },
    )
    process = subprocess.Popen(
        command,
        cwd=project,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    if process.stdout is None or process.stderr is None:
        terminate_owned_process(process)
        raise AcceptanceError("Could not capture intake-skill output streams")
    stdout_thread = threading.Thread(
        target=stream_pipe,
        args=(process.stdout, evidence / "intake.stdout.log"),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=stream_pipe,
        args=(process.stderr, evidence / "intake.stderr.log"),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    started = time.monotonic()
    print("Conversational intake skill started")
    try:
        while process.poll() is None:
            elapsed = time.monotonic() - started
            if elapsed > timeout_seconds:
                terminate_owned_process(process)
                raise AcceptanceError(
                    f"Conversational intake skill exceeded its {timeout_seconds}-second timeout"
                )
            time.sleep(2)
        return_code = process.wait()
    except BaseException:
        terminate_owned_process(process)
        raise
    finally:
        stdout_thread.join(timeout=10)
        stderr_thread.join(timeout=10)
        if final_message.is_file():
            shutil.copy2(final_message, evidence / "intake.final.txt")
    elapsed = time.monotonic() - started
    print(f"Conversational intake skill completed: exit={return_code} elapsed={round(elapsed, 1)}s")
    return return_code, elapsed


def validate_intake_skill_result(
    project: Path,
    evidence: Path,
    expectations: dict,
) -> tuple[dict, list[str]]:
    failures: list[str] = []
    intake_expectations = expectations.get("intake_skill")
    if not isinstance(intake_expectations, dict):
        return {}, ["Scenario is missing intake-skill expectations"]
    validator = project / ".specify/extensions/program-kit-governance/scripts/bootstrap_intake.py"
    command = [
        sys.executable,
        str(validator),
        "validate",
        "--project-root",
        str(project),
        "--intake",
        "docs/architecture/bootstrap-intake.json",
        "--json",
    ]
    validation = subprocess.run(
        command,
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    (evidence / "intake.validation.log").write_text(
        (validation.stdout or "") + (validation.stderr or ""),
        encoding="utf-8",
        newline="\n",
    )
    if validation.returncode != 0:
        failures.append(f"Generated intake failed deterministic validation ({validation.returncode})")
    intake_path = project / "docs/architecture/bootstrap-intake.json"
    intake: dict = {}
    if intake_path.is_file():
        try:
            intake = load_json(intake_path)
        except (OSError, json.JSONDecodeError, AcceptanceError) as exc:
            failures.append(f"Generated intake is unreadable: {exc}")
    else:
        failures.append("Conversational skill did not create docs/architecture/bootstrap-intake.json")
    intake_project = intake.get("project") if isinstance(intake.get("project"), dict) else {}
    expected_name = intake_expectations.get("project_name")
    if expected_name and intake_project.get("name") != expected_name:
        failures.append(f"Generated intake project name is not {expected_name!r}")
    final_message_path = evidence / "intake.final.txt"
    final_message = (
        final_message_path.read_text(encoding="utf-8", errors="replace")
        if final_message_path.is_file()
        else ""
    )
    expected_command = intake_expectations.get("final_command")
    command_lines = [line.strip() for line in final_message.splitlines() if line.strip() == expected_command]
    if not expected_command or len(command_lines) != 1:
        failures.append("Conversational skill did not emit exactly one expected portable bootstrap command")
    return {
        "path": "docs/architecture/bootstrap-intake.json",
        "status": intake.get("status"),
        "project_name": intake_project.get("name"),
        "capability_count": len(intake.get("capability_assessments", []))
        if isinstance(intake.get("capability_assessments"), list)
        else 0,
        "open_item_count": len(intake.get("open_items", []))
        if isinstance(intake.get("open_items"), list)
        else 0,
        "final_command_verified": bool(expected_command and len(command_lines) == 1),
    }, failures


def run_workflow(
    specify: str,
    project: Path,
    integration: str,
    evidence: Path,
    timeout_seconds: int,
    *,
    command: list[str] | None = None,
    evidence_prefix: str = "",
    progress_label: str = "Live bootstrap",
    excluded_run_ids: set[str] | None = None,
) -> tuple[int, float, str | None]:
    if command is None:
        command = [
            specify,
            "workflow",
            "run",
            "program-kit-bootstrap",
            "--input",
            "bootstrap_intake=docs/architecture/bootstrap-intake.json",
            "--input",
            f"integration={integration}",
            "--input",
            "auto_approve_and_ratify=true",
            "--json",
        ]
    environment, removed, worker_settings = worker_environment(project, integration)
    write_json(
        evidence / f"{evidence_prefix}invocation.json",
        {
            "command": command,
            "cwd": str(project),
            "integration": integration,
            "started_at": utc_now(),
            "agent_environment_keys_removed_from_disposable_child": removed,
            "worker_settings": worker_settings,
        },
    )
    process = subprocess.Popen(
        command,
        cwd=project,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    if process.stdout is None or process.stderr is None:
        terminate_owned_process(process)
        raise AcceptanceError("Could not capture workflow output streams")
    stdout_thread = threading.Thread(
        target=stream_pipe,
        args=(process.stdout, evidence / f"{evidence_prefix}workflow.stdout.log", sys.stdout),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=stream_pipe,
        args=(process.stderr, evidence / f"{evidence_prefix}workflow.stderr.log"),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    monitor = evidence / f"{evidence_prefix}monitor.jsonl"
    started = time.monotonic()
    last_state: tuple[object, ...] | None = None
    run_id: str | None = None
    try:
        while process.poll() is None:
            elapsed = time.monotonic() - started
            state_path, state = discover_run_state(project, excluded_run_ids)
            if state:
                run_id = str(state.get("run_id") or state_path.parent.name)
                state_key = (
                    state.get("status"),
                    state.get("current_step_index"),
                    state.get("current_step_id"),
                )
                if state_key != last_state:
                    append_monitor(
                        monitor,
                        {
                            "timestamp": utc_now(),
                            "elapsed_seconds": round(elapsed, 3),
                            "process_id": process.pid,
                            "run_id": run_id,
                            "status": state_key[0],
                            "current_step_index": state_key[1],
                            "current_step_id": state_key[2],
                        },
                    )
                    print(
                        f"{progress_label} progress: "
                        f"step={state_key[2]} status={state_key[0]} elapsed={round(elapsed, 1)}s"
                    )
                    last_state = state_key
            if elapsed > timeout_seconds:
                append_monitor(
                    monitor,
                    {
                        "timestamp": utc_now(),
                        "elapsed_seconds": round(elapsed, 3),
                        "process_id": process.pid,
                        "event": "timeout",
                    },
                )
                terminate_owned_process(process)
                raise AcceptanceError(
                    f"{progress_label} exceeded its {timeout_seconds}-second timeout"
                )
            time.sleep(2)
        return_code = process.wait()
        elapsed = time.monotonic() - started
        state_path, state = discover_run_state(project, excluded_run_ids)
        if state:
            run_id = str(state.get("run_id") or state_path.parent.name)
            state_key = (
                state.get("status"),
                state.get("current_step_index"),
                state.get("current_step_id"),
            )
            if state_key != last_state:
                append_monitor(
                    monitor,
                    {
                        "timestamp": utc_now(),
                        "elapsed_seconds": round(elapsed, 3),
                        "process_id": process.pid,
                        "run_id": run_id,
                        "status": state_key[0],
                        "current_step_index": state_key[1],
                        "current_step_id": state_key[2],
                    },
                )
    except BaseException:
        terminate_owned_process(process)
        raise
    finally:
        stdout_thread.join(timeout=10)
        stderr_thread.join(timeout=10)
    return return_code, time.monotonic() - started, run_id


def install_candidate(
    root: Path,
    project: Path,
    packages: Path,
    integration: str,
    setup_log: Path,
) -> None:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    artifacts = root / "artifacts"
    archives = {
        "governance": artifacts / f"program-kit-governance-{version}.zip",
        "dotnet": artifacts / f"program-kit-dotnet-{version}.zip",
        "preset": artifacts / f"program-kit-governance-preset-{version}.zip",
        "workflow": artifacts / f"program-kit-bootstrap-{version}.zip",
        "bundle": artifacts / f"program-kit-{version}.zip",
    }
    with setup_log.open("w", encoding="utf-8", newline="\n") as log:
        run_logged([sys.executable, str(root / "scripts/build_release.py")], root, log)
        for name, archive in archives.items():
            if not archive.is_file():
                raise AcceptanceError(f"Candidate release archive was not built: {archive}")
            safe_extract(archive, packages / name)
        run_logged(["git", "init"], project, log)
        run_logged(
            specify_bridge_command(
                root,
                "init",
                ".",
                "--force",
                "--non-interactive",
                "--integration",
                integration,
                "--script",
                "py",
                "--ignore-agent-tools",
            ),
            project,
            log,
        )
        server, thread, base_url = prepare_local_catalog_server(
            root, artifacts, packages, setup_log.parent, version
        )
        try:
            run_logged(
                specify_bridge_command(
                    root,
                    "extension",
                    "catalog",
                    "add",
                    f"{base_url}/extensions.json",
                    "--name",
                    "program-kit-live-candidate",
                    "--priority",
                    "1",
                    "--install-allowed",
                ),
                project,
                log,
            )
            run_logged(
                specify_bridge_command(
                    root,
                    "preset",
                    "catalog",
                    "add",
                    f"{base_url}/presets.json",
                    "--name",
                    "program-kit-live-candidate",
                    "--priority",
                    "1",
                    "--install-allowed",
                ),
                project,
                log,
            )
            run_logged(
                specify_bridge_command(
                    root,
                    "workflow",
                    "catalog",
                    "add",
                    f"{base_url}/workflows.json",
                    "--name",
                    "program-kit-live-candidate",
                ),
                project,
                log,
            )
            # Spec Kit 1.0.1 requires the workflow to be preinstalled before
            # bundle installation. The remaining components are installed and
            # provenance-recorded by the real bundle machinery.
            if os.name == "nt":
                install_local_candidate_bundle(root, project, packages, integration, log)
            else:
                run_logged(
                    specify_bridge_command(root, "workflow", "add", "program-kit-bootstrap"),
                    project,
                    log,
                )
                run_logged_with_catalog_retry(
                    specify_bridge_command(
                        root,
                        "bundle",
                        "install",
                        str(archives["bundle"]),
                        "--integration",
                        integration,
                    ),
                    project,
                    log,
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=10)


def validate_result(
    root: Path,
    project: Path,
    expectations: dict,
    run_id: str | None,
    validation_log: Path,
) -> tuple[dict, list[str]]:
    failures: list[str] = []
    workflow_completed = False
    state_path, state = read_run_state(project, run_id)
    if not state_path or not state:
        failures.append("No readable Spec Kit workflow state was produced")
        state = {}
    else:
        run_id = run_id or str(state.get("run_id") or state_path.parent.name)
        workflow_completed = state.get("status") == "completed"
        if not workflow_completed:
            failures.append(f"Workflow status is {state.get('status')!r}, expected 'completed'")
        failed_steps = [
            step_id
            for step_id, record in state.get("step_results", {}).items()
            if isinstance(record, dict) and record.get("status") != "completed"
        ]
        if failed_steps:
            failures.append(f"Workflow has non-completed steps: {failed_steps}")

    file_evidence: list[dict] = []
    for relative in expectations["required_files"]:
        path = project / relative
        if not path.is_file():
            if workflow_completed:
                failures.append(f"Required artifact is missing: {relative}")
            continue
        file_evidence.append(
            {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}
        )

    readiness = project / "docs/architecture/readiness-report.md"
    if readiness.is_file():
        first_line = readiness.read_text(encoding="utf-8").splitlines()[0]
        if workflow_completed and first_line != expectations["readiness_first_line"]:
            failures.append(
                f"Readiness first line is {first_line!r}, expected {expectations['readiness_first_line']!r}"
            )

    expected_approval_mode = expectations.get("approval_mode")
    if workflow_completed and expected_approval_mode:
        for relative in (
            ".specify/governance/bootstrap-assessment-approval.json",
            ".specify/memory/constitution-ratification.json",
            ".specify/governance/bootstrap-approval.json",
        ):
            path = project / relative
            if not path.is_file():
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("approval_mode") != expected_approval_mode:
                failures.append(
                    f"{relative} approval mode is {record.get('approval_mode')!r}, "
                    f"expected {expected_approval_mode!r}"
                )

    if run_id:
        context_root = project / ".specify/workflows/runs" / run_id / "program-kit-context"
        for stage in expectations["required_context_stages"]:
            for suffix in (".json", ".evidence.json"):
                path = context_root / f"{stage}{suffix}"
                if workflow_completed and not path.is_file():
                    failures.append(f"Bootstrap context is missing: {path.name}")

    validator = project / ".specify/extensions/program-kit-governance/scripts/governance_state.py"
    with validation_log.open("w", encoding="utf-8", newline="\n") as log:
        if workflow_completed and validator.is_file():
            result = subprocess.run(
                [
                    sys.executable,
                    str(validator),
                    "validate-bootstrap",
                    "--require-approval",
                    "--require-ready",
                ],
                cwd=project,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if result.returncode != 0:
                failures.append(
                    f"Final governance validator exited with {result.returncode}; see validation.log"
                )
        elif workflow_completed:
            failures.append("Installed governance-state validator is missing")
        else:
            log.write("Final governance validation skipped because the workflow did not complete.\n")
    return {"run_id": run_id, "state": state, "files": file_evidence}, failures


MANAGED_BASELINE_PATTERNS = (
    ".specify/extensions/program-kit-governance/**/*",
    ".specify/extensions/program-kit-dotnet/**/*",
    ".specify/presets/program-kit-governance-preset/**/*",
    ".specify/workflows/program-kit-bootstrap/**/*",
    ".specify/bundles/**/*",
    ".specify/extensions.yml",
    ".agents/skills/speckit-program-kit-*/**/*",
    ".claude/skills/speckit-program-kit-*/**/*",
    ".claude/commands/speckit.program-kit-*",
    "eng/program-kit/**/*",
)


def snapshot_managed_baseline(project: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for pattern in MANAGED_BASELINE_PATTERNS:
        for path in project.glob(pattern):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
                result[path.relative_to(project).as_posix()] = sha256(path)
    return dict(sorted(result.items()))


def find_python_313() -> list[str] | None:
    candidates: list[list[str]] = []
    if sys.version_info[:2] == (3, 13):
        candidates.append([sys.executable])
    executable = shutil.which("python3.13")
    if executable:
        candidates.append([executable])
    launcher = shutil.which("py")
    if launcher:
        candidates.append([launcher, "-3.13"])
    for command in candidates:
        probe = subprocess.run(
            [*command, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if probe.returncode == 0 and "Python 3.13" in (probe.stdout + probe.stderr):
            return command
    return None


def run_validation_command(
    command: list[str], project: Path, log: IO[str], label: str
) -> subprocess.CompletedProcess[str]:
    log.write(f"\n## {label}\n$ {subprocess.list2cmdline(command)}\n")
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    log.write(result.stdout)
    log.write(result.stderr)
    log.write(f"exit_code={result.returncode}\n")
    log.flush()
    return result


def validate_first_slice(
    project: Path,
    expectations: dict,
    run_id: str | None,
    python_command: list[str],
    managed_before: dict[str, str],
    validation_log: Path,
) -> tuple[dict, list[str]]:
    failures: list[str] = []
    workflow_completed = False
    state_path, state = read_run_state(project, run_id)
    if not state_path or not state:
        failures.append("No readable first-slice workflow state was produced")
        state = {}
    else:
        run_id = run_id or str(state.get("run_id") or state_path.parent.name)
        workflow_completed = state.get("status") == "completed"
        if not workflow_completed:
            failures.append(
                f"First-slice workflow status is {state.get('status')!r}, expected 'completed'"
            )
        failed_steps = [
            step_id
            for step_id, record in state.get("step_results", {}).items()
            if isinstance(record, dict) and record.get("status") != "completed"
        ]
        if failed_steps:
            failures.append(f"First-slice workflow has non-completed steps: {failed_steps}")

    feature_directories = sorted(
        path.parent for path in (project / "specs").glob("*/spec.md") if path.is_file()
    )
    feature: Path | None = feature_directories[0] if len(feature_directories) == 1 else None
    if len(feature_directories) != 1:
        if workflow_completed:
            failures.append(
                f"Expected exactly one first-slice feature directory, found {len(feature_directories)}"
            )

    file_evidence: list[dict] = []
    if feature:
        for name in expectations["required_feature_files"]:
            path = feature / name
            if not path.is_file():
                if workflow_completed:
                    failures.append(
                        f"First-slice artifact is missing: {path.relative_to(project).as_posix()}"
                    )
                continue
            file_evidence.append(
                {
                    "path": path.relative_to(project).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )

        traceability_contracts = {
            "spec.md": (
                "## Governance Traceability",
                "**Specification roadmap entry**:",
                "**Architecture constraints**:",
                "**Owned contracts and data**:",
            ),
            "plan.md": (
                "## Architecture Realization",
                "**Roadmap entry and status transition**:",
                "**Vertical-slice path**:",
                "**Artifact ownership manifest**:",
            ),
            "tasks.md": (
                "## Governance Completion Evidence",
                "**Roadmap transition**:",
                "**Path and ownership protection**:",
            ),
        }
        if workflow_completed:
            for name, markers in traceability_contracts.items():
                path = feature / name
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8")
                missing = [marker for marker in markers if marker not in text]
                if missing:
                    failures.append(
                        f"{path.relative_to(project).as_posix()} is missing governance context: {missing}"
                    )
                template_placeholders = (
                    "[ROADMAP ID and title]",
                    "[Outcome independently verified by this feature]",
                    "[Ratified constitution principles",
                    "[Owned modules, contracts",
                    "[Behavior or technical work intentionally outside this feature]",
                )
                if any(value in text for value in template_placeholders):
                    failures.append(
                        f"{path.relative_to(project).as_posix()} retains unfilled governance placeholders"
                    )

    managed_after = snapshot_managed_baseline(project)
    managed_changes = sorted(
        path
        for path in set(managed_before) | set(managed_after)
        if managed_before.get(path) != managed_after.get(path)
    )
    if managed_changes:
        failures.append(
            "First-slice work changed Program Kit-managed baseline files: "
            + ", ".join(managed_changes)
        )
    write_json(
        validation_log.parent / "first-slice-managed-baseline.json",
        {
            "before": managed_before,
            "after": managed_after,
            "changes": managed_changes,
        },
    )

    command_evidence: dict[str, dict] = {}
    roadmap_status: str | None = None
    with validation_log.open("w", encoding="utf-8", newline="\n") as log:
        if workflow_completed and feature:
            ownership_validator = (
                project
                / ".specify/extensions/program-kit-governance/scripts/artifact_ownership.py"
            )
            ownership = run_validation_command(
                [
                    *python_command,
                    str(ownership_validator),
                    "--manifest",
                    str(feature / "artifact-ownership.json"),
                    "--tasks",
                    str(feature / "tasks.md"),
                    "--plan",
                    str(feature / "plan.md"),
                ],
                project,
                log,
                "Artifact ownership",
            )
            command_evidence["artifact_ownership"] = {
                "exit_code": ownership.returncode,
                "stdout": ownership.stdout,
                "stderr": ownership.stderr,
            }
            if ownership.returncode != 0:
                failures.append(
                    "Artifact ownership validation failed; see first-slice.validation.log"
                )

            lifecycle = project / ".program-kit/lifecycle" / f"{feature.name}.json"
            if not lifecycle.is_file():
                failures.append(
                    f"Hash-bound feature lifecycle evidence is missing: {lifecycle.relative_to(project).as_posix()}"
                )
            else:
                try:
                    lifecycle_state = load_json(lifecycle)
                    phases = lifecycle_state.get("phases", {})
                    if not isinstance(phases, dict):
                        raise AcceptanceError("Lifecycle phases must be a JSON object")
                    clarification = phases.get("afterSpecifyClarification", {})
                    analysis_phase = phases.get("afterTasksAnalysis", {})
                    if not isinstance(clarification, dict) or not isinstance(
                        analysis_phase, dict
                    ):
                        raise AcceptanceError("Lifecycle phase records must be JSON objects")
                    if clarification.get("outcome") not in {
                        "no-questions",
                        "questions-answered",
                    }:
                        failures.append(
                            "First-slice clarification lifecycle evidence is incomplete"
                        )
                    if analysis_phase.get("readyForImplementation") is not True:
                        failures.append(
                            "First-slice analysis did not record implementation readiness"
                        )
                    if lifecycle_state.get("active"):
                        failures.append(
                            "First-slice lifecycle still contains an active interrupted phase"
                        )
                except (OSError, json.JSONDecodeError, AcceptanceError) as exc:
                    failures.append(f"First-slice lifecycle evidence is unreadable: {exc}")
            analysis = project / ".program-kit/evidence/after-tasks-analysis.md"
            if not analysis.is_file():
                failures.append("Canonical after-tasks analysis evidence is missing")

            roadmap = project / "docs/architecture/specification-roadmap.md"
            roadmap_text = roadmap.read_text(encoding="utf-8") if roadmap.is_file() else ""
            roadmap_match = re.search(
                r"^\s*-?\s*\*\*Status\*\*:\s*(Ready|Active|Delivered)\s*$",
                roadmap_text,
                re.MULTILINE,
            )
            roadmap_status = roadmap_match.group(1) if roadmap_match else None

            pyproject = project / "pyproject.toml"
            if pyproject.is_file():
                pyproject_text = pyproject.read_text(encoding="utf-8")
                try:
                    import tomllib

                    project_metadata = tomllib.loads(pyproject_text).get("project", {})
                    if not isinstance(project_metadata, dict):
                        raise TypeError("[project] must be a TOML table")
                    requires_python = project_metadata.get("requires-python")
                    if not isinstance(requires_python, str) or "3.13" not in requires_python:
                        failures.append(
                            "pyproject.toml does not declare the required Python 3.13 runtime"
                        )
                    dependencies = project_metadata.get("dependencies", [])
                    if dependencies:
                        failures.append(
                            "pyproject.toml declares third-party runtime dependencies despite the standard-library-only scope"
                        )
                except (ValueError, TypeError) as exc:
                    failures.append(f"pyproject.toml could not be inspected: {exc}")

            consumer_tests = sorted(
                path
                for path in (project / "tests").rglob("test*.py")
                if path.is_file()
            )
            if not consumer_tests:
                failures.append("First-slice implementation produced no discoverable unittest files")

        if workflow_completed:
            tests = run_validation_command(
                [*python_command, "-m", "unittest", "discover", "-s", "tests", "-v"],
                project,
                log,
                "Consumer test suite",
            )
            command_evidence["tests"] = {
                "exit_code": tests.returncode,
                "stdout": tests.stdout,
                "stderr": tests.stderr,
            }
            if tests.returncode != 0:
                failures.append("Consumer test suite failed; see first-slice.validation.log")

            greeting = run_validation_command(
                [*python_command, "-m", "greeting"], project, log, "Greeting success path"
            )
            command_evidence["greeting"] = {
                "exit_code": greeting.returncode,
                "stdout": greeting.stdout,
                "stderr": greeting.stderr,
            }
            if greeting.returncode != 0:
                failures.append(f"Greeting success path exited with {greeting.returncode}, expected 0")
            if greeting.stdout != expectations["expected_stdout"]:
                failures.append(
                    f"Greeting stdout is {greeting.stdout!r}, expected {expectations['expected_stdout']!r}"
                )
            if greeting.stderr:
                failures.append(f"Greeting success path wrote stderr: {greeting.stderr!r}")

            invalid = run_validation_command(
                [*python_command, "-m", "greeting", "unexpected"],
                project,
                log,
                "Greeting rejected-argument path",
            )
            command_evidence["invalid_argument"] = {
                "exit_code": invalid.returncode,
                "stdout": invalid.stdout,
                "stderr": invalid.stderr,
            }
            expected_exit = expectations["expected_argument_exit_code"]
            if invalid.returncode != expected_exit:
                failures.append(
                    f"Greeting rejected-argument path exited with {invalid.returncode}, expected {expected_exit}"
                )
            if invalid.stdout:
                failures.append(f"Greeting rejected-argument path wrote stdout: {invalid.stdout!r}")
            if not invalid.stderr.strip():
                failures.append("Greeting rejected-argument path did not write a usage error to stderr")
        else:
            log.write("Independent first-slice validation skipped because the workflow did not complete.\n")

    if workflow_completed and feature and roadmap_status not in {"Active", "Delivered"}:
        failures.append(
            "The implemented first roadmap entry is neither Active nor Delivered after independent validation"
        )

    return (
        {
            "run_id": run_id,
            "state": state,
            "feature_directory": feature.relative_to(project).as_posix() if feature else None,
            "roadmap_status": roadmap_status,
            "files": file_evidence,
            "managed_baseline_file_count": len(managed_before),
            "managed_baseline_changes": managed_changes,
            "commands": command_evidence,
        },
        failures,
    )


def write_report(
    evidence: Path,
    scenario: str,
    integration: str,
    duration: float,
    workflow_exit_code: int | None,
    result: dict,
    failures: list[str],
    warnings: list[str],
) -> None:
    status = "passed" if workflow_exit_code == 0 and not failures else "failed"
    payload = {
        "schema_version": "1.3",
        "scenario": scenario,
        "integration": integration,
        "status": status,
        "duration_seconds": round(duration, 3),
        "workflow_exit_code": workflow_exit_code,
        "completed_at": utc_now(),
        "failures": failures,
        "warnings": warnings,
        "result": result,
    }
    write_json(evidence / "report.json", payload)
    lines = [
        "# Program Kit live acceptance",
        "",
        f"- Status: **{status.upper()}**",
        f"- Scenario: `{scenario}`",
        f"- Integration: `{integration}`",
        f"- Duration: `{round(duration, 1)} seconds`",
        f"- Workflow exit code: `{workflow_exit_code}`",
        f"- Run ID: `{result.get('run_id')}`",
        "",
        "## Failures",
        "",
    ]
    lines.extend(f"- {failure}" for failure in failures)
    if not failures:
        lines.append("- None")
    lines.extend(["", "## Performance observations", ""])
    lines.extend(f"- {warning}" for warning in warnings)
    if not warnings:
        lines.append("- All advisory budgets were met")
    metrics = result.get("metrics", {})
    if metrics:
        lines.extend(
            [
                "",
                f"- Agent sessions observed: `{metrics.get('agent_session_count', 0)}`",
                f"- Agent tokens observed: `{metrics.get('agent_tokens_total', 0)}`",
                f"- Captured stderr: `{metrics.get('workflow_stderr_bytes', 0)} bytes`",
            ]
        )
    first_slice = result.get("first_slice")
    intake_skill = result.get("intake_skill")
    if isinstance(intake_skill, dict):
        lines.extend(
            [
                "",
                "## Conversational intake skill",
                "",
                f"- Status: `{intake_skill.get('status')}`",
                f"- Exit code: `{intake_skill.get('workflow_exit_code')}`",
                f"- Duration: `{intake_skill.get('duration_seconds')} seconds`",
                f"- Project: `{intake_skill.get('project_name')}`",
                f"- Capability assessments: `{intake_skill.get('capability_count')}`",
                f"- Open items: `{intake_skill.get('open_item_count')}`",
                f"- Portable command verified: `{intake_skill.get('final_command_verified')}`",
            ]
        )
    if isinstance(first_slice, dict):
        lines.extend(
            [
                "",
                "## First-slice continuation",
                "",
                f"- Status: `{first_slice.get('status')}`",
                f"- Workflow exit code: `{first_slice.get('workflow_exit_code')}`",
                f"- Run ID: `{first_slice.get('run_id')}`",
                f"- Feature directory: `{first_slice.get('feature_directory')}`",
                f"- Managed baseline changes: `{len(first_slice.get('managed_baseline_changes', []))}`",
            ]
        )
        if first_slice.get("reason"):
            lines.append(f"- Reason: {first_slice['reason']}")
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "- `workflow.stdout.log`: structured workflow result.",
            "- `workflow.stderr.log`: live agent and gate output stream.",
            "- `monitor.jsonl`: workflow step transitions and elapsed time.",
            "- `validation.log`: final governance validation.",
            "- `project/`: preserved disposable consumer for diagnosis.",
            "",
        ]
    )
    if isinstance(intake_skill, dict):
        lines[-1:-1] = [
            "- `intake.invocation.json`: exact intake-worker command and sandbox settings.",
            "- `intake.stdout.log` and `intake.stderr.log`: complete intake-worker streams.",
            "- `intake.final.txt`: final skill response containing the portable handoff command.",
            "- `intake.validation.log`: deterministic validation of the generated contract.",
        ]
    if isinstance(first_slice, dict) and first_slice.get("workflow_exit_code") is not None:
        lines[-1:-1] = [
            "- `first-slice.workflow.stdout.log`: structured first-slice workflow result.",
            "- `first-slice.workflow.stderr.log`: first-slice agent and hook output.",
            "- `first-slice.monitor.jsonl`: first-slice workflow transitions.",
            "- `first-slice.validation.log`: independent ownership, test, and CLI validation.",
            "- `first-slice-managed-baseline.json`: before/after hashes for Program Kit-managed files.",
        ]
    (evidence / "report.md").write_text(
        "\n".join(lines), encoding="utf-8", newline="\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the opt-in, API-consuming Program Kit bootstrap acceptance suite."
    )
    parser.add_argument("--scenario", default="clean-bootstrap", choices=("clean-bootstrap",))
    parser.add_argument("--integration", default="codex", choices=("codex", "claude"))
    parser.add_argument(
        "--approved",
        action="store_true",
        help="Confirm that the user explicitly requested this paid live agent run.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    parser.add_argument(
        "--exercise-intake-skill",
        action="store_true",
        help="Run the installed conversational bootstrap skill from the raw scenario request before bootstrap.",
    )
    parser.add_argument("--intake-timeout-seconds", type=int, default=3600)
    parser.add_argument(
        "--continue-first-slice",
        action="store_true",
        help="After bootstrap, run the first Ready slice through specify, plan, tasks, and implement.",
    )
    parser.add_argument("--first-slice-timeout-seconds", type=int, default=7200)
    parser.add_argument("--output-root", default="artifacts/live-acceptance")
    args = parser.parse_args()

    if not args.approved:
        print(
            "LIVE_ACCEPTANCE_APPROVAL_REQUIRED: Run the paid live bootstrap acceptance suite only "
            "after an explicit user request. Re-run with --approved to acknowledge that request.",
            file=sys.stderr,
        )
        return 3
    active_ci = [key for key in CI_ENVIRONMENT_KEYS if os.environ.get(key)]
    if active_ci:
        print(
            "LIVE_ACCEPTANCE_CI_FORBIDDEN: This paid agentic suite must not run in CI "
            f"({', '.join(active_ci)} is set).",
            file=sys.stderr,
        )
        return 3
    if args.timeout_seconds < 60:
        print("Live acceptance timeout must be at least 60 seconds.", file=sys.stderr)
        return 3
    if args.intake_timeout_seconds < 60:
        print("Conversational intake timeout must be at least 60 seconds.", file=sys.stderr)
        return 3
    if args.exercise_intake_skill and args.integration != "codex":
        print(
            "INTAKE_SKILL_CODEX_REQUIRED: The live conversational-intake phase currently requires the Codex integration.",
            file=sys.stderr,
        )
        return 3
    if args.first_slice_timeout_seconds < 60:
        print("First-slice timeout must be at least 60 seconds.", file=sys.stderr)
        return 3
    specify = shutil.which("specify")
    integration_cli = shutil.which(args.integration)
    if not specify or not integration_cli:
        print(
            f"Required CLI is missing: specify={specify!r}, {args.integration}={integration_cli!r}",
            file=sys.stderr,
        )
        return 3
    python_313 = find_python_313() if args.continue_first_slice else None
    if args.continue_first_slice and python_313 is None:
        print(
            "FIRST_SLICE_PYTHON_313_REQUIRED: The clean-bootstrap continuation must independently "
            "run the fixture with Python 3.13 before starting paid agent sessions.",
            file=sys.stderr,
        )
        return 3

    root = Path(__file__).resolve().parents[2]
    scenario_root = Path(__file__).resolve().parent / "scenarios" / args.scenario
    expectations = load_json(scenario_root / "expectations.json")
    output_root = (root / args.output_root).resolve()
    try:
        output_root.relative_to(root)
    except ValueError:
        print("Live acceptance output must stay inside the Program Kit repository.", file=sys.stderr)
        return 3
    identifier = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + f"-{args.scenario}-{args.integration}-{uuid.uuid4().hex[:6]}"
    )
    evidence = output_root / identifier
    project = evidence / "project"
    packages = evidence / "packages"
    project.mkdir(parents=True, exist_ok=False)
    if args.exercise_intake_skill:
        shutil.copyfile(scenario_root / "PROJECT_REQUEST.md", project / "PROJECT_REQUEST.md")
    else:
        shutil.copytree(scenario_root / "docs", project / "docs")
    print(f"Live acceptance evidence: {evidence}")

    started = time.monotonic()
    workflow_exit_code: int | None = None
    workflow_duration: float | None = None
    run_id: str | None = None
    failures: list[str] = []
    result: dict = {}
    intake_phase: dict | None = None
    try:
        install_candidate(
            root,
            project,
            packages,
            args.integration,
            evidence / "setup.log",
        )
        write_worker_guidance(project, args.integration)
        if args.exercise_intake_skill:
            intake_exit_code, intake_duration = run_intake_skill(
                integration_cli,
                project,
                evidence,
                args.intake_timeout_seconds,
            )
            intake_result, intake_failures = validate_intake_skill_result(
                project,
                evidence,
                expectations,
            )
            intake_phase = {
                **intake_result,
                "workflow_exit_code": intake_exit_code,
                "duration_seconds": round(intake_duration, 3),
                "status": (
                    "passed" if intake_exit_code == 0 and not intake_failures else "failed"
                ),
            }
            failures.extend(intake_failures)
            if intake_exit_code != 0:
                failures.append(f"Conversational intake skill exited with {intake_exit_code}")
            if failures:
                raise AcceptanceError("Conversational intake did not produce a bootstrap-ready contract")
        workflow_exit_code, workflow_duration, run_id = run_workflow(
            specify,
            project,
            args.integration,
            evidence,
            args.timeout_seconds,
        )
        if workflow_exit_code != 0:
            failures.append(f"Workflow process exited with {workflow_exit_code}")
        result, validation_failures = validate_result(
            root,
            project,
            expectations,
            run_id,
            evidence / "validation.log",
        )
        if intake_phase is not None:
            result["intake_skill"] = intake_phase
        failures.extend(validation_failures)
        if args.continue_first_slice and not failures:
            managed_before = snapshot_managed_baseline(project)
            known_run_ids = {
                path.name
                for path in (project / ".specify/workflows/runs").iterdir()
                if path.is_dir()
            }
            first_slice = expectations.get("first_slice")
            if not isinstance(first_slice, dict):
                raise AcceptanceError("Scenario is missing first-slice expectations")
            first_slice_command = [
                specify,
                "workflow",
                "run",
                str(scenario_root / "first-slice-workflow.yml"),
                "--input",
                f"integration={args.integration}",
                "--input",
                f"feature_description={first_slice['feature_description']}",
                "--json",
            ]
            first_exit_code, first_duration, first_run_id = run_workflow(
                specify,
                project,
                args.integration,
                evidence,
                args.first_slice_timeout_seconds,
                command=first_slice_command,
                evidence_prefix="first-slice.",
                progress_label="First-slice lifecycle",
                excluded_run_ids=known_run_ids,
            )
            if first_exit_code != 0:
                failures.append(f"First-slice workflow process exited with {first_exit_code}")
            first_result, first_failures = validate_first_slice(
                project,
                first_slice,
                first_run_id,
                python_313 or [sys.executable],
                managed_before,
                evidence / "first-slice.validation.log",
            )
            first_result["workflow_exit_code"] = first_exit_code
            first_result["duration_seconds"] = round(first_duration, 3)
            first_result["status"] = (
                "passed" if first_exit_code == 0 and not first_failures else "failed"
            )
            result["first_slice"] = first_result
            failures.extend(first_failures)
    except KeyboardInterrupt:
        failures.append("Live bootstrap was interrupted by the operator")
        state_path, state = discover_run_state(project)
        result = {
            "run_id": state.get("run_id") if state else run_id,
            "state_path": str(state_path) if state_path else None,
            "state": state or {},
            "files": [],
        }
    except (AcceptanceError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
        state_path, state = discover_run_state(project)
        result = {
            "run_id": state.get("run_id") if state else run_id,
            "state_path": str(state_path) if state_path else None,
            "state": state or {},
            "files": [],
        }
    if intake_phase is not None and "intake_skill" not in result:
        result["intake_skill"] = intake_phase
    if args.continue_first_slice and "first_slice" not in result:
        result["first_slice"] = {
            "status": "not-run",
            "workflow_exit_code": None,
            "run_id": None,
            "feature_directory": None,
            "managed_baseline_changes": [],
            "reason": "The continuation did not complete; inspect the recorded failures and preserved project.",
        }
    resolved_run_id = str(result.get("run_id") or run_id or "") or None
    metrics = analyze_metrics(evidence, resolved_run_id, workflow_duration)
    warnings = performance_warnings(metrics, expectations.get("advisory_budgets", {}))
    if workflow_exit_code not in (None, 0):
        warnings.insert(0, "Performance observations are partial because the workflow failed")
    result["metrics"] = metrics
    duration = time.monotonic() - started
    write_report(
        evidence,
        args.scenario,
        args.integration,
        duration,
        workflow_exit_code,
        result,
        failures,
        warnings,
    )
    print(f"Live acceptance report: {evidence / 'report.md'}")
    return 0 if workflow_exit_code == 0 and not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
