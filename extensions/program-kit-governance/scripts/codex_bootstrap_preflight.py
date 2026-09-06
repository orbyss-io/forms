from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping


CODEX_AGENT_ENVIRONMENT_KEYS = (
    "CODEX_SESSION_ID",
    "CODEX_THREAD_ID",
    "CODEX_INTERNAL_ORIGINATOR_OVERRIDE",
)
CONSTITUTION_SKILL = Path(".agents/skills/speckit-constitution/SKILL.md")
PYTHON_RESOLVER = Path(".specify/scripts/python/resolve_template.py")
POWERSHELL_RESOLVER = Path(".specify/scripts/powershell/resolve-template.ps1")
SHELL_RESOLVER = Path(".specify/scripts/bash/resolve-template.sh")
SUPPORTED_RESOLVERS = {
    "py": PYTHON_RESOLVER,
    "ps": POWERSHELL_RESOLVER,
    "sh": SHELL_RESOLVER,
}
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
BOOTSTRAP_WORKFLOW_ID = "program-kit-bootstrap"


def resolve_integration(requested: str, project_root: Path) -> str:
    """Resolve Spec Kit's ``auto`` integration without importing Spec Kit."""
    value = requested.strip().lower()
    if value and value != "auto":
        return value

    candidates = (
        (project_root / ".specify" / "integration.json", ("default_integration", "integration")),
        (project_root / ".specify" / "init-options.json", ("integration", "ai")),
    )
    for path, keys in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        for key in keys:
            candidate = payload.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip().lower()
    return value


def is_codex_agent_invocation(
    *,
    integration: str,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Detect an outer Program Kit run launched by a Codex agent session."""
    if integration.lower() != "codex":
        return False
    environ = environ if environ is not None else os.environ
    return any(environ.get(key) for key in CODEX_AGENT_ENVIRONMENT_KEYS)


def _read_json_object(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _validated_run_state(project_root: Path, run_id: str) -> tuple[Path, dict]:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise RuntimeError(f"Invalid workflow run ID: {run_id!r}")
    runs_root = (project_root / ".specify" / "workflows" / "runs").resolve()
    run_dir = (runs_root / run_id).resolve()
    if run_dir.parent != runs_root:
        raise RuntimeError(f"Workflow run path escapes the project run directory: {run_id!r}")
    state_path = run_dir / "state.json"
    state = _read_json_object(state_path)
    if not state:
        raise RuntimeError(f"Workflow run state is missing or invalid: {state_path}")
    if state.get("run_id") != run_id:
        raise RuntimeError(f"Workflow run state does not match run ID {run_id!r}")
    return state_path, state


def competing_bootstrap_runs(project_root: Path, current_run_id: str) -> list[str]:
    """Return other Program Kit bootstrap runs still persisted as running."""
    if not RUN_ID_PATTERN.fullmatch(current_run_id):
        raise RuntimeError(f"Invalid current workflow run ID: {current_run_id!r}")
    runs_root = project_root / ".specify" / "workflows" / "runs"
    competing: list[str] = []
    if not runs_root.is_dir():
        return competing
    for state_path in runs_root.glob("*/state.json"):
        run_id = state_path.parent.name
        if run_id == current_run_id or not RUN_ID_PATTERN.fullmatch(run_id):
            continue
        try:
            _, state = _validated_run_state(project_root, run_id)
        except RuntimeError:
            continue
        if state.get("run_id") != run_id or state.get("status") != "running":
            continue
        workflow_id = state.get("installed_workflow_id") or state.get("workflow_id")
        if workflow_id == BOOTSTRAP_WORKFLOW_ID:
            competing.append(run_id)
    return sorted(competing)


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def abandon_bootstrap_run(project_root: Path, run_id: str) -> None:
    """Explicitly terminate one persisted running Program Kit bootstrap run."""
    state_path, state = _validated_run_state(project_root, run_id)
    workflow_id = state.get("installed_workflow_id") or state.get("workflow_id")
    if workflow_id != BOOTSTRAP_WORKFLOW_ID:
        raise RuntimeError(f"Run {run_id!r} is not a Program Kit bootstrap run")
    if state.get("status") != "running":
        raise RuntimeError(
            f"Run {run_id!r} has status {state.get('status')!r}; only a running run can be abandoned"
        )

    timestamp = datetime.now(timezone.utc).isoformat()
    reason = "Explicitly abandoned by the operator before starting a replacement Program Kit bootstrap run."
    state["status"] = "aborted"
    state["updated_at"] = timestamp
    state["error"] = reason
    _atomic_write_json(state_path, state)

    log_path = state_path.with_name("log.jsonl")
    event = {
        "event": "workflow_abandoned",
        "status": "aborted",
        "reason": reason,
        "timestamp": timestamp,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def concurrent_run_diagnostic(run_ids: list[str]) -> str:
    identifiers = ", ".join(run_ids)
    example = run_ids[0]
    return f"""PROGRAM_KIT_CONCURRENT_BOOTSTRAP_RUN

Program Kit stopped before intake or research because another bootstrap run is
still recorded as running: {identifiers}

Do not run two governance bootstraps concurrently; they write the same
constitution, approvals, architecture, and roadmap artifacts.

If the listed run still has a live `specify workflow` process, return to that
terminal and let it finish or stop it first. If the process is gone and the run
is an abandoned stale record, preserve its history and explicitly terminate it
from a normal user-owned shell:

  python .specify/extensions/program-kit-governance/scripts/codex_bootstrap_preflight.py --abandon-run {example}

Then start a new Program Kit bootstrap run. Do not edit or delete workflow state
JSON by hand.
"""


def declared_script_flavor(project_root: Path, integration: str) -> str:
    """Read the script flavor recorded by Spec Kit initialization."""
    integration_state = _read_json_object(project_root / ".specify" / "integration.json")
    settings = integration_state.get("integration_settings")
    if isinstance(settings, dict):
        selected = settings.get(integration)
        if isinstance(selected, dict):
            value = selected.get("script")
            if isinstance(value, str) and value.strip():
                return value.strip().lower()

    init_options = _read_json_object(project_root / ".specify" / "init-options.json")
    value = init_options.get("script")
    return value.strip().lower() if isinstance(value, str) else ""


def referenced_constitution_resolver(project_root: Path) -> tuple[str, Path]:
    """Resolve the executable template resolver named by the installed constitution skill."""
    skill = project_root / CONSTITUTION_SKILL
    try:
        text = skill.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Installed constitution skill is missing or unreadable: {skill}") from exc

    normalized = text.replace("\\", "/")
    matches = [
        (flavor, resolver)
        for flavor, resolver in SUPPORTED_RESOLVERS.items()
        if resolver.as_posix() in normalized
    ]
    if len(matches) != 1:
        references = sorted(
            set(re.findall(r"\.specify/scripts/[^\s`]+resolve[^\s`]+", normalized))
        )
        detail = ", ".join(references) if references else "none"
        raise RuntimeError(
            "Installed constitution skill does not name exactly one supported resolver "
            f"(found: {detail})"
        )
    return matches[0]


def inspect_script_runtime(project_root: Path, integration: str) -> tuple[str, Path]:
    """Inspect and cross-check Spec Kit's recorded and generated script flavors."""
    referenced_flavor, relative_resolver = referenced_constitution_resolver(project_root)
    declared_flavor = declared_script_flavor(project_root, integration)
    if declared_flavor and declared_flavor != referenced_flavor:
        raise RuntimeError(
            "Spec Kit script flavor is inconsistent: initialization records "
            f"{declared_flavor!r}, but the constitution skill references {referenced_flavor!r}"
        )
    resolver = project_root / relative_resolver
    if not resolver.is_file():
        raise RuntimeError(
            f"The constitution skill references a resolver that does not exist: {relative_resolver}"
        )
    return referenced_flavor, resolver


def _resolver_command(flavor: str, resolver: Path) -> list[str]:
    if flavor == "py":
        return [sys.executable, str(resolver), "constitution-template", "--json"]
    if flavor == "sh":
        executable = shutil.which("bash")
        if executable is None:
            raise RuntimeError("No Bash executable is available for the referenced resolver")
        return [executable, str(resolver), "constitution-template", "--json"]
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        raise RuntimeError("No PowerShell executable is available for the referenced resolver")
    return [
        executable,
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-File",
        str(resolver),
        "constitution-template",
        "-Json",
    ]


def verify_windows_resolver(
    project_root: Path,
    flavor: str,
    resolver: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    """Execute the installed resolver exactly far enough to prove it is usable."""
    command = _resolver_command(flavor, resolver)
    child_environment = os.environ.copy()
    if flavor == "py":
        child_environment["PYTHONIOENCODING"] = "utf-8"
        child_environment["PYTHONUTF8"] = "1"
    try:
        result = runner(
            command,
            cwd=project_root,
            env=child_environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Resolver execution could not start: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no diagnostic output").strip()
        detail = " ".join(detail.split())[:600]
        raise RuntimeError(f"Resolver execution failed with exit code {result.returncode}: {detail}")
    if "TEMPLATE_CONTENT" not in (result.stdout or ""):
        raise RuntimeError("Resolver execution did not return the expected template payload")


def verify_git_worktree(
    project_root: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    """Require the Git work tree that Codex exec uses as its trust boundary."""
    repository = project_root.resolve()
    excludes = "" if os.name == "nt" else "/dev/null"
    try:
        result = runner(
            [
                "git",
                "-c",
                f"safe.directory={repository.as_posix()}",
                "-c",
                f"core.excludesFile={excludes}",
                "-C",
                str(repository),
                "rev-parse",
                "--is-inside-work-tree",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Git work-tree validation could not start: {exc}") from exc
    if result.returncode != 0 or (result.stdout or "").strip().lower() != "true":
        detail = (result.stderr or result.stdout or "not a Git work tree").strip()
        detail = " ".join(detail.split())[:600]
        raise RuntimeError(detail)


def diagnostic() -> str:
    return """PROGRAM_KIT_CODEX_AGENT_BOUNDARY

Program Kit stopped before Spec Kit started a nested Codex CLI.

The outer bootstrap command is running from a Codex Desktop task or an
interactive Codex CLI agent. Both are agent environments. Spec Kit dispatches
Codex workflow steps with `codex exec`, so the outer orchestration must instead
be started by the human from a normal user-owned shell.

On native Windows, Codex's preferred elevated sandbox uses dedicated
lower-privilege identities and filesystem permission boundaries. Running
initialization or installation from that identity can leave `.agents`,
`.specify`, or related paths owned by the sandbox identity. Later sandbox setup
may then fail while applying protective ACLs. Nested `codex exec` is a second,
independent reason not to start the outer workflow from an agent.

Open a normal PowerShell or WSL terminal yourself, change to the repository
root, and run the full command there, for example:

  specify workflow run program-kit-bootstrap --input "bootstrap_intake=docs/architecture/bootstrap-intake.json" --input "integration=auto"

Do not ask this agent to run that command outside its sandbox, approve an
escalation exception, install an approval rule, or start another interactive
`codex` agent. The Spec Kit workers launched by the normal shell remain
sandboxed.

If an agent already performed initialization or installation, rerunning init
alone may not repair ownership. Review the clean-start and ownership guidance:
  .specify/extensions/program-kit-governance/references/codex-desktop-windows.md
"""


def script_runtime_diagnostic(problem: str) -> str:
    if "PyYAML is required" in problem or "No module named 'yaml'" in problem:
        remediation = """Install the resolver's missing dependency into the exact Python interpreter
used by the workflow, then verify the resolver directly:

  python -m pip install --disable-pip-version-check "PyYAML>=6,<7"
  python .specify/scripts/python/resolve_template.py constitution-template --json

Do not rerun Spec Kit initialization for this dependency error; reinitialization
does not install packages into the `python` interpreter."""
    else:
        remediation = """Cleanly regenerate Spec Kit's integration files with the Python flavor:

  specify init . --force --non-interactive --integration codex --script py

Then confirm that `.specify/scripts/python/resolve_template.py` exists and that
`.agents/skills/speckit-constitution/SKILL.md` references it before restarting
the Program Kit workflow. This merge-style reinitialization preserves installed
Program Kit extension registration, but review `git status` before continuing."""

    return f"""PROGRAM_KIT_SPEC_KIT_SCRIPT_RUNTIME

Program Kit stopped before intake or research because the installed Codex
constitution skill does not have a usable Spec Kit template resolver on
Windows.

{problem}

From a normal user-owned PowerShell terminal in the repository root:

{remediation}

Do not weaken the machine or user execution policy, broadly unblock repository
files, or grant unrestricted execution. If ownership is already wrong, follow
the conservative clean-start guidance instead:
  .specify/extensions/program-kit-governance/references/codex-desktop-windows.md
"""


def git_worktree_diagnostic(problem: str) -> str:
    return f"""PROGRAM_KIT_CODEX_GIT_WORKTREE

Program Kit stopped before intake or research because Codex workflow workers
require the repository root to be inside a Git work tree.

{problem}

From a normal user-owned PowerShell terminal in the repository root, initialize
Git and verify the work tree before starting a new Program Kit workflow run:

  git init
  git status

This preserves existing project files. Do not bypass Codex's repository check
with `--skip-git-repo-check`.
"""


def evaluate_preflight(
    integration: str,
    project_root: Path,
    *,
    current_run_id: str = "",
    environ: Mapping[str, str] | None = None,
    platform_name: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, str]:
    if current_run_id:
        try:
            competing = competing_bootstrap_runs(project_root, current_run_id)
        except RuntimeError as exc:
            return {"action": "run-state-blocked", "diagnostic": str(exc)}
        if competing:
            return {
                "action": "concurrent-run-blocked",
                "diagnostic": concurrent_run_diagnostic(competing),
            }
    resolved = resolve_integration(integration, project_root)
    if is_codex_agent_invocation(integration=resolved, environ=environ):
        return {"action": "agent-boundary-blocked", "diagnostic": diagnostic()}
    if resolved != "codex":
        return {"action": "continue", "script_flavor": "not-applicable"}

    try:
        verify_git_worktree(project_root, runner=runner)
    except RuntimeError as exc:
        return {
            "action": "git-worktree-blocked",
            "diagnostic": git_worktree_diagnostic(str(exc)),
        }

    try:
        flavor, resolver = inspect_script_runtime(project_root, resolved)
        current_platform = platform_name if platform_name is not None else os.name
        if current_platform == "nt":
            verify_windows_resolver(project_root, flavor, resolver, runner=runner)
    except RuntimeError as exc:
        return {
            "action": "script-runtime-blocked",
            "diagnostic": script_runtime_diagnostic(str(exc)),
        }
    return {"action": "continue", "script_flavor": flavor}


def run_preflight(integration: str, project_root: Path, current_run_id: str = "") -> int:
    result = evaluate_preflight(
        integration, project_root, current_run_id=current_run_id
    )
    if result["action"] == "continue":
        return 0
    print(result["diagnostic"], file=sys.stderr)
    return 2


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(
        description="Validate the Codex execution boundary and installed Spec Kit resolver."
    )
    parser.add_argument("--integration", default="auto")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--abandon-run", default="")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a workflow-switch action and always return success.",
    )
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    if args.abandon_run:
        try:
            abandon_bootstrap_run(project_root, args.abandon_run)
        except RuntimeError as exc:
            print(f"Program Kit run recovery failed: {exc}", file=sys.stderr)
            return 2
        print(f"Program Kit bootstrap run {args.abandon_run} is marked aborted.")
        return 0
    result = evaluate_preflight(
        args.integration, project_root, current_run_id=args.run_id
    )
    if args.json:
        print(json.dumps(result))
        return 0
    if result["action"] != "continue":
        print(result["diagnostic"], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
