from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml


FORBIDDEN_WORKAROUND_PHRASES = (
    "Always allow",
    "first four argument tokens",
    "program-kit-bootstrap.rules",
    "codex execpolicy",
    "approve only this exact prefix",
    "Set-ExecutionPolicy Bypass",
    "-ExecutionPolicy Bypass",
    "Unblock-File",
)


def load_module(root: Path):
    path = root / "extensions/program-kit-governance/scripts/codex_bootstrap_preflight.py"
    spec = importlib.util.spec_from_file_location("codex_bootstrap_preflight", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_phrases(label: str, text: str, phrases: tuple[str, ...]) -> None:
    normalized_text = " ".join(text.split())
    for phrase in phrases:
        if " ".join(phrase.split()) not in normalized_text:
            raise AssertionError(f"{label} is missing actionable text: {phrase}")


def reject_workaround(label: str, text: str) -> None:
    normalized_text = " ".join(text.split())
    for phrase in FORBIDDEN_WORKAROUND_PHRASES:
        if " ".join(phrase.split()) in normalized_text:
            raise AssertionError(f"{label} reintroduced an unsafe workaround: {phrase}")


def initialize_python_consumer(project: Path) -> None:
    subprocess.run(
        [
            "specify",
            "init",
            ".",
            "--force",
            "--non-interactive",
            "--integration",
            "codex",
            "--script",
            "py",
            "--ignore-agent-tools",
        ],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def validate_python_consumer(module) -> None:
    with tempfile.TemporaryDirectory(prefix="program-kit-python-consumer-") as temp:
        project = Path(temp)
        initialize_python_consumer(project)
        resolver = project / module.PYTHON_RESOLVER
        skill = project / module.CONSTITUTION_SKILL
        if not resolver.is_file():
            raise AssertionError("Python-flavor initialization did not install resolve_template.py")
        skill_text = skill.read_text(encoding="utf-8")
        if module.PYTHON_RESOLVER.as_posix() not in skill_text.replace("\\", "/"):
            raise AssertionError("Generated constitution skill does not reference the Python resolver")
        if module.declared_script_flavor(project, "codex") != "py":
            raise AssertionError("Spec Kit did not record the Python script flavor")
        flavor, referenced = module.inspect_script_runtime(project, "codex")
        if flavor != "py" or referenced != resolver:
            raise AssertionError("Preflight did not resolve the generated Python runtime")

        missing_git = module.evaluate_preflight(
            "codex", project, environ={}, platform_name="nt"
        )
        if missing_git.get("action") != "git-worktree-blocked":
            raise AssertionError(f"Non-Git Codex consumer was not rejected: {missing_git}")
        require_phrases(
            "Missing Git work-tree diagnostic",
            missing_git["diagnostic"],
            (
                "PROGRAM_KIT_CODEX_GIT_WORKTREE",
                "before intake or research",
                "git init",
                "git status",
                "preserves existing project files",
                "Do not bypass",
                "--skip-git-repo-check",
            ),
        )

        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        result = module.evaluate_preflight(
            "codex", project, environ={}, platform_name="nt"
        )
        if result != {"action": "continue", "script_flavor": "py"}:
            raise AssertionError(f"Usable Python resolver was unexpectedly rejected: {result}")

        observed_git: list[str] = []

        def ownership_safe_runner(command, **kwargs):
            observed_git.extend(command)
            return subprocess.CompletedProcess(command, 0, stdout="true\n", stderr="")

        module.verify_git_worktree(project, runner=ownership_safe_runner)
        if (
            f"safe.directory={project.resolve().as_posix()}" not in observed_git
            or not any(value.startswith("core.excludesFile=") for value in observed_git)
        ):
            raise AssertionError(f"Git ownership validation is not command-scoped and path-normalized: {observed_git}")

        integration_path = project / ".specify/integration.json"
        integration = json.loads(integration_path.read_text(encoding="utf-8"))
        integration["integration_settings"]["codex"]["script"] = "ps"
        integration_path.write_text(json.dumps(integration), encoding="utf-8")
        powershell_resolver = project / module.POWERSHELL_RESOLVER
        powershell_resolver.parent.mkdir(parents=True, exist_ok=True)
        powershell_resolver.write_text(
            "# Cross-platform fixture; execution is replaced by blocked_runner.\n",
            encoding="utf-8",
        )
        skill.write_text(
            skill_text.replace(
                module.PYTHON_RESOLVER.as_posix(),
                module.POWERSHELL_RESOLVER.as_posix(),
            ),
            encoding="utf-8",
        )

        def blocked_runner(*args, **kwargs):
            command = args[0]
            if command and Path(command[0]).name.lower().startswith("git"):
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout="true\n",
                    stderr="",
                )
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout="",
                stderr="PSSecurityException: the resolver is not digitally signed",
            )

        original_which = module.shutil.which
        module.shutil.which = lambda name: "powershell.exe" if name == "powershell" else None
        try:
            blocked = module.evaluate_preflight(
                "codex",
                project,
                environ={},
                platform_name="nt",
                runner=blocked_runner,
            )
        finally:
            module.shutil.which = original_which
        if blocked.get("action") != "script-runtime-blocked":
            raise AssertionError(f"Blocked PowerShell resolver was not rejected: {blocked}")
        require_phrases(
            "PowerShell resolver diagnostic",
            blocked["diagnostic"],
            (
                "PROGRAM_KIT_SPEC_KIT_SCRIPT_RUNTIME",
                "before intake or research",
                "PSSecurityException",
                "specify init . --force --non-interactive --integration codex --script py",
                ".specify/scripts/python/resolve_template.py",
                "Do not weaken",
            ),
        )
        reject_workaround("PowerShell resolver diagnostic", blocked["diagnostic"])

        missing_pyyaml = module.script_runtime_diagnostic(
            "Resolver execution failed with exit code 1: "
            "ERROR: PyYAML is required to resolve preset template composition"
        )
        require_phrases(
            "Missing PyYAML diagnostic",
            missing_pyyaml,
            (
                "PROGRAM_KIT_SPEC_KIT_SCRIPT_RUNTIME",
                'python -m pip install --disable-pip-version-check "PyYAML>=6,<7"',
                "python .specify/scripts/python/resolve_template.py constitution-template --json",
                "Do not rerun Spec Kit initialization",
            ),
        )
        if "specify init" in missing_pyyaml:
            raise AssertionError("Missing PyYAML diagnostic incorrectly recommends reinitialization")
        reject_workaround("Missing PyYAML diagnostic", missing_pyyaml)


def write_run_state(
    project: Path,
    run_id: str,
    *,
    workflow_id: str = "program-kit-bootstrap",
    status: str = "running",
) -> Path:
    run_dir = project / ".specify" / "workflows" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    state_path = run_dir / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "workflow_id": workflow_id,
                "installed_workflow_id": workflow_id,
                "installed_registry_root": None,
                "status": status,
                "current_step_index": 2,
                "current_step_id": "intake",
                "step_results": {},
                "workflow_dir": str(project / ".specify/workflows/program-kit-bootstrap"),
                "created_at": "2026-09-01T12:00:00+00:00",
                "updated_at": "2026-09-01T12:00:01+00:00",
                "error": None,
            }
        ),
        encoding="utf-8",
    )
    return state_path


def validate_abandoned_run_recovery(module) -> None:
    with tempfile.TemporaryDirectory(prefix="program-kit-run-recovery-") as temp:
        project = Path(temp)
        write_run_state(project, "current1")
        stale_path = write_run_state(project, "stale001")
        write_run_state(project, "done0001", status="completed")
        unrelated = write_run_state(project, "other001", workflow_id="other-workflow")

        competing = module.competing_bootstrap_runs(project, "current1")
        if competing != ["stale001"]:
            raise AssertionError(f"Unexpected competing bootstrap runs: {competing}")
        blocked = module.evaluate_preflight(
            "claude", project, current_run_id="current1", environ={}
        )
        if blocked.get("action") != "concurrent-run-blocked":
            raise AssertionError(f"Competing bootstrap run was not blocked: {blocked}")
        require_phrases(
            "Concurrent bootstrap diagnostic",
            blocked["diagnostic"],
            (
                "PROGRAM_KIT_CONCURRENT_BOOTSTRAP_RUN",
                "stale001",
                "Do not run two governance bootstraps concurrently",
                "--abandon-run stale001",
                "Do not edit or delete workflow state JSON by hand",
            ),
        )

        module.abandon_bootstrap_run(project, "stale001")
        stale_state = json.loads(stale_path.read_text(encoding="utf-8"))
        if stale_state.get("status") != "aborted" or not stale_state.get("error"):
            raise AssertionError("Explicit run abandonment did not persist terminal evidence")
        log_text = stale_path.with_name("log.jsonl").read_text(encoding="utf-8")
        if '"event": "workflow_abandoned"' not in log_text:
            raise AssertionError("Explicit run abandonment did not append historical evidence")
        if json.loads(unrelated.read_text(encoding="utf-8"))["status"] != "running":
            raise AssertionError("Run recovery changed an unrelated workflow")
        for rejected_run_id in ("../escape", "done0001", "other001"):
            try:
                module.abandon_bootstrap_run(project, rejected_run_id)
            except RuntimeError:
                pass
            else:
                raise AssertionError(
                    f"Run recovery unexpectedly abandoned {rejected_run_id!r}"
                )

        result = module.evaluate_preflight(
            "claude", project, current_run_id="current1", environ={}
        )
        if result != {"action": "continue", "script_flavor": "not-applicable"}:
            raise AssertionError(f"Recovered workflow state was unexpectedly rejected: {result}")


def validate_populated_repository_initializer(root: Path) -> None:
    suffix = "cmd" if os.name == "nt" else "sh"
    integration = "claude"
    source = root / f"Initialize-ProgramKit.{suffix}"
    with tempfile.TemporaryDirectory(prefix="program-kit-initializer-test-") as temp:
        project = Path(temp)
        initializer = project / source.name
        shutil.copyfile(source, initializer)
        if suffix == "sh":
            initializer.chmod(0o755)

        design = project / "product-vision.notes.md"
        application_file = project / "src" / "application.txt"
        integration_file = project / ".specify" / "integration.json"
        core_skill = project / ".agents/skills/speckit-constitution/SKILL.md"
        design.write_text("Existing initial design\n", encoding="utf-8")
        application_file.parent.mkdir()
        application_file.write_text("Existing application content\n", encoding="utf-8")
        integration_file.parent.mkdir()
        integration_file.write_text(
            '{"default_integration":"codex"}\n', encoding="utf-8"
        )
        core_skill.parent.mkdir(parents=True)
        core_skill.write_text("Existing core Spec Kit skill\n", encoding="utf-8")

        tool_dir = project / ".test-tools"
        tool_dir.mkdir()
        command_log = project / ".initializer-commands.log"
        pyyaml_marker = project / ".test-pyyaml-installed"
        if suffix == "cmd":
            stub = tool_dir / "specify.cmd"
            stub.write_text(
                "@echo off\n"
                "if \"%1\"==\"--version\" exit /b 0\n"
                '>>"%PROGRAM_KIT_TEST_LOG%" echo %*\n'
                "exit /b 0\n",
                encoding="utf-8",
            )
            python_stub = tool_dir / "python.cmd"
            python_stub.write_text(
                "@echo off\n"
                "if \"%1\"==\"--version\" exit /b 0\n"
                "if \"%1\"==\"-c\" (\n"
                "  if exist \"%PROGRAM_KIT_TEST_PYYAML%\" exit /b 0\n"
                "  exit /b 1\n"
                ")\n"
                "if \"%1\"==\"-m\" if \"%2\"==\"pip\" if \"%3\"==\"--version\" exit /b 0\n"
                "if \"%1\"==\"-m\" if \"%2\"==\"pip\" (\n"
                "  >\"%PROGRAM_KIT_TEST_PYYAML%\" echo installed\n"
                "  >>\"%PROGRAM_KIT_TEST_LOG%\" echo python %*\n"
                "  exit /b 0\n"
                ")\n"
                "if \"%~nx1\"==\"ensure_utf8.py\" (\n"
                "  >>\"%PROGRAM_KIT_TEST_LOG%\" echo python %*\n"
                "  exit /b 0\n"
                ")\n"
                "exit /b 1\n",
                encoding="utf-8",
            )
            command = [
                os.environ.get("COMSPEC", "cmd.exe"),
                "/d",
                "/c",
                initializer.name,
                integration,
            ]
        else:
            stub = tool_dir / "specify"
            stub.write_text(
                "#!/usr/bin/env sh\n"
                "if [ \"${1:-}\" = '--version' ]; then exit 0; fi\n"
                "printf '%s\\n' \"$*\" >> \"$PROGRAM_KIT_TEST_LOG\"\n",
                encoding="utf-8",
            )
            stub.chmod(0o755)
            python_stub = tool_dir / "python"
            python_stub.write_text(
                "#!/usr/bin/env sh\n"
                "if [ \"${1:-}\" = '--version' ]; then exit 0; fi\n"
                "if [ \"${1:-}\" = '-c' ]; then\n"
                "  [ -f \"$PROGRAM_KIT_TEST_PYYAML\" ]\n"
                "  exit $?\n"
                "fi\n"
                "if [ \"${1:-}\" = '-m' ] && [ \"${2:-}\" = 'pip' ] && [ \"${3:-}\" = '--version' ]; then exit 0; fi\n"
                "if [ \"${1:-}\" = '-m' ] && [ \"${2:-}\" = 'pip' ]; then\n"
                "  printf 'installed\\n' > \"$PROGRAM_KIT_TEST_PYYAML\"\n"
                "  printf 'python %s\\n' \"$*\" >> \"$PROGRAM_KIT_TEST_LOG\"\n"
                "  exit 0\n"
                "fi\n"
                "case \"${1:-}\" in *ensure_utf8.py) printf 'python %s\\n' \"$*\" >> \"$PROGRAM_KIT_TEST_LOG\"; exit 0;; esac\n"
                "exit 1\n",
                encoding="utf-8",
            )
            python_stub.chmod(0o755)
            bash = shutil.which("bash")
            if not bash:
                raise AssertionError("A Bash runner is required to validate the Bash initializer")
            command = [bash, initializer.name, integration]

        environment = os.environ.copy()
        for key in ("CODEX_SESSION_ID", "CODEX_THREAD_ID", "CODEX_INTERNAL_ORIGINATOR_OVERRIDE"):
            environment.pop(key, None)
        environment["PATH"] = str(tool_dir) + os.pathsep + environment.get("PATH", "")
        environment["PROGRAM_KIT_TEST_LOG"] = str(command_log)
        environment["PROGRAM_KIT_TEST_PYYAML"] = str(pyyaml_marker)

        missing_integration = subprocess.run(
            command[:-1],
            cwd=project,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if missing_integration.returncode != 2:
            raise AssertionError(f"{suffix} initializer did not require an integration ID")
        require_phrases(
            f"Missing integration {suffix} diagnostic",
            missing_integration.stdout + missing_integration.stderr,
            ("Supply exactly one Spec Kit integration ID",),
        )
        if command_log.exists():
            raise AssertionError("Initializer invoked a tool without an integration ID")

        missing_git = subprocess.run(
            command,
            cwd=project,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if missing_git.returncode != 2:
            raise AssertionError(f"{suffix} initializer did not reject a non-Git directory")
        require_phrases(
            f"Missing Git {suffix} diagnostic",
            missing_git.stdout + missing_git.stderr,
            (
                "not inside an initialized Git work tree",
                "git init",
                "git status",
                "then rerun",
            ),
        )
        if command_log.exists() or pyyaml_marker.exists():
            raise AssertionError("Initializer performed setup before rejecting missing Git")

        subprocess.run(
            ["git", "init"],
            cwd=project,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        completed = subprocess.run(
            command,
            cwd=project,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"{suffix} initializer rejected a populated repository: "
                f"{completed.stdout}{completed.stderr}"
            )
        if design.read_text(encoding="utf-8") != "Existing initial design\n":
            raise AssertionError("Initializer changed the existing initial design")
        if application_file.read_text(encoding="utf-8") != "Existing application content\n":
            raise AssertionError("Initializer changed an unrelated existing project file")
        if integration_file.read_text(encoding="utf-8") != '{"default_integration":"codex"}\n':
            raise AssertionError("Initializer test stub changed existing Spec Kit configuration")
        if core_skill.read_text(encoding="utf-8") != "Existing core Spec Kit skill\n":
            raise AssertionError("Initializer test stub changed the existing core Spec Kit skill")
        if not pyyaml_marker.is_file():
            raise AssertionError("Initializer did not install missing PyYAML before Spec Kit")
        if not (project / ".git").exists():
            raise AssertionError("Initializer test lost the user-initialized Git repository")
        commands = command_log.read_text(encoding="utf-8")
        require_phrases(
            f"Executed {suffix} initializer",
            commands,
            (
                "python -m pip install --disable-pip-version-check",
                "PyYAML>=6,<7",
                f"init . --force --non-interactive --integration {integration} --script py",
                "workflow add program-kit-bootstrap",
                f"bundle install program-kit --integration {integration}",
                "ensure_utf8.py",
                "extension catalog remove program-kit",
                "preset catalog remove program-kit",
                "workflow catalog remove 0",
                "bundle catalog remove program-kit",
                "program-kit/main/catalogs/extensions.json",
                "program-kit/main/catalogs/presets.json",
                "program-kit/main/catalogs/workflows.json",
                "program-kit/main/catalogs/bundles.json",
            ),
        )

        command_log.unlink()
        partial_marker = project / ".specify/workflow-catalogs.yml"
        partial_marker.write_text(
            "catalogs:\n  - name: program-kit\n", encoding="utf-8"
        )
        rejected = subprocess.run(
            command,
            cwd=project,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if rejected.returncode != 2:
            raise AssertionError(
                f"{suffix} initializer did not reject existing Program Kit: "
                f"{rejected.stdout}{rejected.stderr}"
            )
        require_phrases(
            f"Existing Program Kit {suffix} diagnostic",
            rejected.stdout + rejected.stderr,
            ("Program Kit is already installed", "update commands"),
        )
        if command_log.exists():
            raise AssertionError("Initializer invoked specify after detecting Program Kit")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    extension_root = root / "extensions/program-kit-governance"
    module = load_module(root)

    with tempfile.TemporaryDirectory(prefix="program-kit-codex-preflight-") as temp:
        project = Path(temp)
        specify = project / ".specify"
        specify.mkdir()
        (specify / "integration.json").write_text(
            json.dumps({"default_integration": "codex"}), encoding="utf-8"
        )
        if module.resolve_integration("auto", project) != "codex":
            raise AssertionError("auto did not resolve the initialized Codex integration")
        if module.resolve_integration("claude", project) != "claude":
            raise AssertionError("explicit integration should win over project config")

    for key in module.CODEX_AGENT_ENVIRONMENT_KEYS:
        if not module.is_codex_agent_invocation(
            integration="codex", environ={key: "test-value"}
        ):
            raise AssertionError(f"Codex agent environment was not detected from {key}")
    for case in (
        {"integration": "claude", "environ": {"CODEX_SESSION_ID": "test"}},
        {"integration": "codex", "environ": {}},
    ):
        if module.is_codex_agent_invocation(**case):
            raise AssertionError(f"False positive in preflight case: {case}")

    message = module.diagnostic()
    require_phrases(
        "Preflight diagnostic",
        message,
        (
            "PROGRAM_KIT_CODEX_AGENT_BOUNDARY",
            "normal PowerShell or WSL terminal",
            "run the full command there",
            "interactive Codex CLI agent",
            "dedicated lower-privilege identities",
            "`.agents`",
            "rerunning init alone may not repair ownership",
            "Do not ask this agent",
        ),
    )
    reject_workaround("Preflight diagnostic", message)
    validate_python_consumer(module)
    validate_abandoned_run_recovery(module)

    rule_files = list(extension_root.rglob("*.rules"))
    if rule_files:
        raise AssertionError(f"Extension must not package Codex approval rules: {rule_files}")

    workflow = yaml.safe_load(
        (root / "workflows/program-kit-bootstrap/workflow.yml").read_text(encoding="utf-8")
    )
    first = workflow["steps"][0]
    if first.get("id") != "codex-execution-preflight" or first.get("type") != "shell":
        raise AssertionError("Codex preflight must run before every agent-dispatched step")
    if "codex_bootstrap_preflight.py" not in first.get("run", ""):
        raise AssertionError("Workflow preflight does not invoke its diagnostic")
    if "--run-id {{ context.run_id }}" not in first.get("run", ""):
        raise AssertionError("Workflow preflight must identify its own validated run ID")
    if "inputs." in first.get("run", ""):
        raise AssertionError("Workflow preflight must not interpolate user input into a shell")
    if first.get("output_format") != "json" or "--json" not in first.get("run", ""):
        raise AssertionError("Workflow preflight must expose a structured switch action")

    boundary = workflow["steps"][1]
    if boundary.get("id") != "codex-execution-boundary" or boundary.get("type") != "switch":
        raise AssertionError("Structured preflight must be followed by its execution boundary")
    cases = boundary.get("cases", {})
    agent_blocked = cases.get("agent-boundary-blocked", [])
    runtime_blocked = cases.get("script-runtime-blocked", [])
    git_blocked = cases.get("git-worktree-blocked", [])
    concurrent_blocked = cases.get("concurrent-run-blocked", [])
    run_state_blocked = cases.get("run-state-blocked", [])
    if any(
        len(steps) != 1
        for steps in (
            agent_blocked,
            runtime_blocked,
            git_blocked,
            concurrent_blocked,
            run_state_blocked,
        )
    ):
        raise AssertionError("Each Codex preflight failure must have one diagnostic step")
    for label, blocked_step in (
        ("agent", agent_blocked[0]),
        ("runtime", runtime_blocked[0]),
        ("git", git_blocked[0]),
        ("concurrent run", concurrent_blocked[0]),
        ("run state", run_state_blocked[0]),
    ):
        if blocked_step.get("type") != "gate":
            raise AssertionError(f"Workflow-visible {label} stop must be a non-agent gate")
        if blocked_step.get("options") != ["abort"] or blocked_step.get("on_reject") != "abort":
            raise AssertionError(f"Workflow-visible {label} stop must only permit abort")
        require_phrases(
            f"Workflow-visible {label} stop",
            blocked_step.get("message", ""),
            (
                "Preflight stop (not a review gate)",
                "{{ steps.codex-execution-preflight.output.data.diagnostic }}",
            ),
        )
        if "integration" in blocked_step or "command" in blocked_step:
            raise AssertionError(f"Workflow-visible {label} stop must not dispatch an agent")
    workflow_text = (root / "workflows/program-kit-bootstrap/workflow.yml").read_text(
        encoding="utf-8"
    )
    if "program-kit-preflight-diagnostic" in workflow_text:
        raise AssertionError("Workflow still references the nonexistent diagnostic integration")

    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    initializer_expectations = {
        "cmd": (
            "specify init . --force --non-interactive --integration %PROGRAM_KIT_INTEGRATION% --script py",
            f'set "PROGRAM_KIT_REF=v{version}"',
            "specify workflow add program-kit-bootstrap",
            "specify bundle install program-kit --integration %PROGRAM_KIT_INTEGRATION%",
        ),
        "sh": (
            'specify init . --force --non-interactive --integration "$program_kit_integration" --script py',
            f'PROGRAM_KIT_REF="v{version}"',
            "specify workflow add program-kit-bootstrap",
            'specify bundle install program-kit --integration "$program_kit_integration"',
        ),
    }
    for suffix, expected in initializer_expectations.items():
        label = f"{suffix} consumer initializer"
        initializer_path = root / f"Initialize-ProgramKit.{suffix}"
        initializer = initializer_path.read_text(encoding="utf-8")
        require_phrases(
            label,
            initializer,
            expected
            + (
                "Program Kit initialization is complete",
                "not from a Codex Desktop task or interactive Codex CLI agent",
                "Program Kit is already installed",
                "specify --version",
                "python --version",
                "python -m pip --version",
                "python -m pip install --disable-pip-version-check",
                "PyYAML>=6,<7",
                "git --version",
                "git rev-parse --is-inside-work-tree",
                "git init",
                "extension catalog remove program-kit",
                "preset catalog remove program-kit",
                "workflow catalog remove 0",
                "bundle catalog remove program-kit",
                "program-kit/main/catalogs/extensions.json",
                "program-kit/main/catalogs/presets.json",
                "program-kit/main/catalogs/workflows.json",
                "program-kit/main/catalogs/bundles.json",
            ),
        )
        for noisy_post_install_phrase in (
            "detected. Start the bootstrap",
            "when ready, then start the bootstrap",
            "Start the bootstrap from this same normal shell",
        ):
            if noisy_post_install_phrase in initializer:
                raise AssertionError(
                    f"{label} contains noisy post-install guidance: "
                    f"{noisy_post_install_phrase}"
                )
        if "not empty" in initializer.lower():
            raise AssertionError(f"{label} still rejects populated repositories")
        reject_workaround(label, initializer)

    bash = shutil.which("bash") if os.name != "nt" else None
    if bash:
        subprocess.run([bash, "-n", str(root / "Initialize-ProgramKit.sh")], check=True)
    validate_populated_repository_initializer(root)

    skill = (
        extension_root / "commands/speckit.program-kit-governance.bootstrap.md"
    ).read_text(encoding="utf-8")
    require_phrases(
        "Bootstrap skill",
        skill,
        (
            "This skill is the Program Kit front door",
            "adaptive intake",
            "architecture-map.json",
            "Always emit exactly one physical",
            "normal user-owned terminal",
            "must never run",
            "bootstrap_intake=docs/architecture/bootstrap-intake.json",
        ),
    )
    reject_workaround("Bootstrap skill", skill)

    packaged_reference = (
        extension_root / "references/codex-desktop-windows.md"
    ).read_text(encoding="utf-8")
    require_phrases(
        "Packaged Windows reference",
        packaged_reference,
        (
            "normal user-owned PowerShell or WSL",
            "dedicated lower-privilege users",
            "SetNamedSecurityInfoW ... error 5",
            "git clone --no-hardlinks --no-checkout",
            "Preserve `.git`",
            "--script py",
            "resolve_template.py",
        ),
    )
    reject_workaround("Packaged Windows reference", packaged_reference)

    root_guidance = (root / "docs/codex-desktop-windows.md").read_text(encoding="utf-8")
    require_phrases(
        "Root Windows guide",
        root_guidance,
        (
            "normal user-owned PowerShell or WSL shell",
            "SetNamedSecurityInfoW ... error 5",
            "Rerunning `specify init` is not an ownership repair",
            "confirmed intake contract",
            "Preserve `.git`",
            "Initialize-ProgramKit.cmd",
            "Initialize-ProgramKit.sh",
            "--script py",
        ),
    )
    reject_workaround("Root Windows guide", root_guidance)

    readme = (root / "README.md").read_text(encoding="utf-8")
    require_phrases(
        "Root installation instructions",
        readme,
        (
            "The repository does not need to be empty",
            "Existing source, documentation, an initial design",
            "existing Spec Kit initialization are allowed",
            "existing or partial Program Kit installation",
            "Invoke-WebRequest",
            f"releases/download/v{version}/Initialize-ProgramKit-{version}.cmd",
            ".\\Initialize-ProgramKit.cmd codex",
            "curl -fL",
            f"releases/download/v{version}/Initialize-ProgramKit-{version}.sh",
            "bash ./Initialize-ProgramKit.sh codex",
            "use `claude` instead of `codex`",
        ),
    )
    reject_workaround("Root installation instructions", readme)

    print("Codex bootstrap boundary, Python resolver, and packaged guidance are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
