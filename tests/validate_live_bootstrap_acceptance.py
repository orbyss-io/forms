from __future__ import annotations

import json
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from live.run_bootstrap_acceptance import (
    AcceptanceError,
    analyze_metrics,
    discover_run_state,
    git_excludes_override,
    performance_warnings,
    run_logged_with_catalog_retry,
    snapshot_managed_baseline,
    specify_bridge_command,
    validate_intake_skill_result,
    validate_first_slice,
    validate_result,
)
from specify_cli.workflows.engine import WorkflowDefinition, validate_workflow


def run_guard(runner: Path, *args: str, env: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, str(runner), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def require(path: Path, *phrases: str) -> None:
    text = " ".join(path.read_text(encoding="utf-8").split())
    missing = [phrase for phrase in phrases if " ".join(phrase.split()) not in text]
    if missing:
        raise AssertionError(f"{path} is missing live-acceptance policy text: {missing}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    runner = root / "tests/live/run_bootstrap_acceptance.py"
    wrapper = root / "scripts/Test-LiveBootstrap.ps1"
    scenario = root / "tests/live/scenarios/clean-bootstrap"
    for path in (
        runner,
        wrapper,
        scenario / "docs/architecture/project-intent.md",
        scenario / "docs/architecture/architecture-map.json",
        scenario / "docs/architecture/workspace.dsl",
        scenario / "docs/architecture/bootstrap-intake.json",
        scenario / "PROJECT_REQUEST.md",
        scenario / "expectations.json",
        scenario / "first-slice-workflow.yml",
        root / "docs/live-bootstrap-acceptance.md",
        root / "AGENTS.md",
    ):
        if not path.is_file():
            raise AssertionError(f"Live bootstrap acceptance component is missing: {path}")

    runner_text = runner.read_text(encoding="utf-8")
    if "auto_approve_and_ratify=true" not in runner_text:
        raise AssertionError("Live bootstrap must exercise the public automatic approval option")
    for legacy_input in (
        "assessment_verdict=approve",
        "constitution_verdict=ratify",
        "bootstrap_verdict=approve",
    ):
        if legacy_input in runner_text:
            raise AssertionError(
                f"Live bootstrap still bypasses the public option with {legacy_input}"
            )

    expectations = json.loads((scenario / "expectations.json").read_text(encoding="utf-8"))
    intake_expectations = expectations.get("intake_skill", {})
    if intake_expectations.get("project_name") != "Greeting CLI" or not intake_expectations.get("final_command"):
        raise AssertionError("Clean-bootstrap scenario is missing conversational-intake assertions")

    original_run = subprocess.run
    expected_excludes = "" if os.name == "nt" else os.devnull
    if git_excludes_override() != expected_excludes:
        raise AssertionError("Live worker Git excludes override is not platform-safe")
    git_probe = subprocess.run(
        ["git", "-c", f"core.excludesFile={git_excludes_override()}", "status", "--short"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if git_probe.returncode != 0 or "cannot use nul" in git_probe.stderr.lower():
        raise AssertionError(f"Live worker Git excludes override is unusable: {git_probe.stderr}")
    bridge = specify_bridge_command(root, "workflow", "add", "program-kit-bootstrap")
    if (
        bridge[0] != sys.executable
        or Path(bridge[1]) != root / "scripts/invoke_specify.py"
        or "--site-packages" not in bridge
        or bridge[-3:] != ["workflow", "add", "program-kit-bootstrap"]
    ):
        raise AssertionError(f"Live setup does not use the installed Specify Python bridge: {bridge}")
    retry_results = iter(
        (
            subprocess.CompletedProcess(
                ["specify"],
                1,
                stdout="",
                stderr=(
                    "Failed to save extension\narchive: connection reset. "
                    "No changes were recorded."
                ),
            ),
            subprocess.CompletedProcess(["specify"], 0, stdout="installed\n", stderr=""),
        )
    )
    try:
        subprocess.run = lambda *args, **kwargs: next(retry_results)
        retry_log = io.StringIO()
        run_logged_with_catalog_retry(["specify"], root, retry_log)
        if "attempt 2/3" not in retry_log.getvalue():
            raise AssertionError("Transient local-catalog transfer was not retried")
    finally:
        subprocess.run = original_run

    with tempfile.TemporaryDirectory(prefix="program-kit-live-guard-") as directory:
        denied = run_guard(runner, "--exercise-intake-skill", "--output-root", directory)
        if denied.returncode != 3 or "LIVE_ACCEPTANCE_APPROVAL_REQUIRED" not in denied.stderr:
            raise AssertionError(f"Unapproved live run was not refused: {denied}")
        if any(Path(directory).iterdir()):
            raise AssertionError("Unapproved live run created output before refusing")

    with tempfile.TemporaryDirectory(prefix="program-kit-live-intake-mode-") as directory:
        denied = run_guard(
            runner,
            "--approved",
            "--exercise-intake-skill",
            "--integration",
            "claude",
            "--output-root",
            directory,
        )
        if denied.returncode != 3 or "INTAKE_SKILL_CODEX_REQUIRED" not in denied.stderr:
            raise AssertionError(f"Unsupported live intake integration was not refused: {denied}")
        if any(Path(directory).iterdir()):
            raise AssertionError("Unsupported intake mode created output before refusing")

    with tempfile.TemporaryDirectory(prefix="program-kit-live-intake-validation-") as directory:
        temp_root = Path(directory)
        project = temp_root / "project"
        evidence = temp_root / "evidence"
        shutil.copytree(scenario / "docs", project / "docs")
        scripts = project / ".specify/extensions/program-kit-governance/scripts"
        scripts.mkdir(parents=True)
        for name in ("bootstrap_intake.py", "architecture_map.py"):
            shutil.copy2(root / "extensions/program-kit-governance/scripts" / name, scripts / name)
        evidence.mkdir()
        (evidence / "intake.final.txt").write_text(
            intake_expectations["final_command"] + "\n",
            encoding="utf-8",
        )
        intake_result, intake_failures = validate_intake_skill_result(
            project,
            evidence,
            expectations,
        )
        if intake_failures or not intake_result.get("final_command_verified"):
            raise AssertionError(f"Generated-intake seam validation is invalid: {intake_failures}")

    with tempfile.TemporaryDirectory(prefix="program-kit-live-metrics-") as directory:
        evidence = Path(directory)
        (evidence / "workflow.stderr.log").write_text(
            "tokens used\n1,200\ntokens used\n300\n", encoding="utf-8"
        )
        (evidence / "workflow.stdout.log").write_text("{}\n", encoding="utf-8")
        (evidence / "intake.stderr.log").write_text("tokens used\n50\n", encoding="utf-8")
        monitor = [
            {"status": "running", "current_step_id": "assessment", "elapsed_seconds": 2.0},
            {"status": "running", "current_step_id": "research", "elapsed_seconds": 7.0},
        ]
        (evidence / "monitor.jsonl").write_text(
            "".join(json.dumps(record) + "\n" for record in monitor), encoding="utf-8"
        )
        metrics = analyze_metrics(evidence, None, workflow_duration=10.0)
        if metrics["agent_tokens_by_stage"] != {"intake-skill": 50, "assessment": 1200, "research": 300}:
            raise AssertionError(f"Agent token attribution is invalid: {metrics}")
        if metrics["stage_duration_seconds"] != {"assessment": 5.0, "research": 3.0}:
            raise AssertionError(f"Stage duration attribution is invalid: {metrics}")
        if performance_warnings(metrics, {"agent_tokens_total": 1000}) != [
            "Agent token total 1550 exceeds advisory budget 1000"
        ]:
            raise AssertionError("Live advisory budgets are not reported predictably")

    with tempfile.TemporaryDirectory(prefix="program-kit-live-failure-") as directory:
        project = Path(directory)
        state_path = project / ".specify/workflows/runs/failed-run/state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps(
                {
                    "run_id": "failed-run",
                    "status": "failed",
                    "step_results": {"research": {"status": "failed"}},
                }
            ),
            encoding="utf-8",
        )
        _, failures = validate_result(
            root,
            project,
            {
                "required_files": ["downstream.md"],
                "required_context_stages": ["readiness"],
                "readiness_first_line": "**Status**: READY",
            },
            "failed-run",
            project / "validation.log",
        )
        if failures != [
            "Workflow status is 'failed', expected 'completed'",
            "Workflow has non-completed steps: ['research']",
        ]:
            raise AssertionError(f"Failed live report cascaded downstream noise: {failures}")

        second_state = project / ".specify/workflows/runs/second-run/state.json"
        second_state.parent.mkdir(parents=True)
        second_state.write_text(
            json.dumps({"run_id": "second-run", "status": "completed"}),
            encoding="utf-8",
        )
        selected_path, selected = discover_run_state(project, {"second-run"})
        if (
            selected_path != state_path
            or not selected
            or selected.get("run_id") != "failed-run"
        ):
            raise AssertionError("Workflow state exclusion did not isolate the continuation run")

        _, first_slice_failures = validate_first_slice(
            project,
            {
                "required_feature_files": [],
                "expected_stdout": "Hello, Program Kit!\n",
                "expected_argument_exit_code": 2,
            },
            "failed-run",
            [sys.executable],
            {},
            project / "first-slice.validation.log",
        )
        if first_slice_failures != [
            "First-slice workflow status is 'failed', expected 'completed'",
            "First-slice workflow has non-completed steps: ['research']",
        ]:
            raise AssertionError(
                f"Failed first-slice report cascaded downstream noise: {first_slice_failures}"
            )

    with tempfile.TemporaryDirectory(prefix="program-kit-live-managed-") as directory:
        project = Path(directory)
        managed = (
            project
            / ".specify/extensions/program-kit-governance/commands/example.md"
        )
        managed.parent.mkdir(parents=True)
        managed.write_text("managed\n", encoding="utf-8")
        unrelated = project / "greeting/__main__.py"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("print('hello')\n", encoding="utf-8")
        snapshot = snapshot_managed_baseline(project)
        if list(snapshot) != [
            ".specify/extensions/program-kit-governance/commands/example.md"
        ]:
            raise AssertionError(f"Managed baseline snapshot has the wrong scope: {snapshot}")

    with tempfile.TemporaryDirectory(prefix="program-kit-live-first-slice-") as directory:
        project = Path(directory)
        state_path = project / ".specify/workflows/runs/slice-run/state.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps(
                {
                    "run_id": "slice-run",
                    "status": "completed",
                    "step_results": {
                        name: {"status": "completed"}
                        for name in ("specify", "plan", "tasks", "implement")
                    },
                }
            ),
            encoding="utf-8",
        )
        feature = project / "specs/001-greeting"
        feature.mkdir(parents=True)
        (feature / "spec.md").write_text(
            "## Governance Traceability\n"
            "- **Specification roadmap entry**: SPC-001\n"
            "- **Architecture constraints**: Constitution\n"
            "- **Owned contracts and data**: CLI, no data\n",
            encoding="utf-8",
        )
        (feature / "plan.md").write_text(
            "## Architecture Realization\n"
            "- **Roadmap entry and status transition**: SPC-001\n"
            "- **Vertical-slice path**: user to output\n"
            "- **Artifact ownership manifest**: artifact-ownership.json\n",
            encoding="utf-8",
        )
        (feature / "tasks.md").write_text(
            "## Governance Completion Evidence\n"
            "- **Roadmap transition**: Delivered\n"
            "- **Path and ownership protection**: validated\n",
            encoding="utf-8",
        )
        (feature / "artifact-ownership.json").write_text("{}\n", encoding="utf-8")
        lifecycle = project / ".program-kit/lifecycle/001-greeting.json"
        lifecycle.parent.mkdir(parents=True)
        lifecycle.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "phases": {
                        "afterSpecifyClarification": {"outcome": "no-questions"},
                        "afterTasksAnalysis": {"readyForImplementation": True},
                    },
                }
            ),
            encoding="utf-8",
        )
        analysis = project / ".program-kit/evidence/after-tasks-analysis.md"
        analysis.parent.mkdir(parents=True)
        analysis.write_text(
            "# Specification Analysis Report\n\n"
            "| ID | Category | Severity | Location(s) | Summary | Recommendation |\n"
            "|----|----------|----------|-------------|---------|----------------|\n"
            "| — | — | — | — | No findings | Proceed |\n",
            encoding="utf-8",
        )
        roadmap = project / "docs/architecture/specification-roadmap.md"
        roadmap.parent.mkdir(parents=True)
        roadmap.write_text("### SPC-001: Greeting\n\n**Status**: Delivered\n", encoding="utf-8")
        greeting = project / "greeting/__main__.py"
        greeting.parent.mkdir(parents=True)
        greeting.write_text(
            "import sys\n"
            "if len(sys.argv) != 1:\n"
            "    print('usage: python -m greeting', file=sys.stderr)\n"
            "    raise SystemExit(2)\n"
            "print('Hello, Program Kit!')\n",
            encoding="utf-8",
        )
        consumer_test = project / "tests/test_greeting.py"
        consumer_test.parent.mkdir(parents=True)
        consumer_test.write_text(
            "import unittest\n\n"
            "class GreetingTests(unittest.TestCase):\n"
            "    def test_fixture(self):\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        ownership = (
            project
            / ".specify/extensions/program-kit-governance/scripts/artifact_ownership.py"
        )
        ownership.parent.mkdir(parents=True)
        ownership.write_text("raise SystemExit(0)\n", encoding="utf-8")
        managed_before = snapshot_managed_baseline(project)
        cache = ownership.parent / "__pycache__/artifact_ownership.cpython-313.pyc"
        cache.parent.mkdir()
        cache.write_bytes(b"ephemeral bytecode")
        if snapshot_managed_baseline(project) != managed_before:
            raise AssertionError("ephemeral Python bytecode was treated as managed baseline drift")
        result, success_failures = validate_first_slice(
            project,
            {
                "required_feature_files": [
                    "spec.md",
                    "plan.md",
                    "tasks.md",
                    "artifact-ownership.json",
                ],
                "expected_stdout": "Hello, Program Kit!\n",
                "expected_argument_exit_code": 2,
            },
            "slice-run",
            [sys.executable],
            managed_before,
            project / "first-slice.validation.log",
        )
        if success_failures or result.get("managed_baseline_changes"):
            raise AssertionError(
                f"Valid first-slice evidence was rejected: {success_failures}, {result}"
            )

    ci_environment = os.environ.copy()
    ci_environment["CI"] = "true"
    denied_ci = run_guard(runner, "--approved", env=ci_environment)
    if denied_ci.returncode != 3 or "LIVE_ACCEPTANCE_CI_FORBIDDEN" not in denied_ci.stderr:
        raise AssertionError(f"CI live run was not refused: {denied_ci}")

    expectations = json.loads((scenario / "expectations.json").read_text(encoding="utf-8"))
    if expectations.get("scenario") != "clean-bootstrap":
        raise AssertionError("Clean-bootstrap expectations have the wrong scenario ID")
    if expectations.get("readiness_first_line") != "**Status**: READY":
        raise AssertionError("Clean-bootstrap scenario does not require exact READY evidence")
    first_slice = expectations.get("first_slice", {})
    if (
        not isinstance(first_slice, dict)
        or "first Ready entry" not in first_slice.get("feature_description", "")
        or first_slice.get("required_feature_files")
        != ["spec.md", "plan.md", "tasks.md", "artifact-ownership.json"]
        or first_slice.get("expected_stdout") != "Hello, Program Kit!\n"
        or first_slice.get("expected_argument_exit_code") != 2
    ):
        raise AssertionError(f"Clean-bootstrap first-slice expectations are invalid: {first_slice}")

    first_slice_workflow = WorkflowDefinition.from_yaml(
        scenario / "first-slice-workflow.yml"
    )
    workflow_errors = validate_workflow(first_slice_workflow)
    if workflow_errors:
        raise AssertionError(f"First-slice workflow is invalid: {workflow_errors}")
    first_slice_yaml = yaml.safe_load(
        (scenario / "first-slice-workflow.yml").read_text(encoding="utf-8")
    )
    first_slice_steps = [step["id"] for step in first_slice_yaml["steps"]]
    if first_slice_steps != [
        "specify-first-slice",
        "plan-first-slice",
        "tasks-first-slice",
        "implement-first-slice",
    ]:
        raise AssertionError(f"First-slice lifecycle is incomplete: {first_slice_steps}")
    stages = expectations.get("required_context_stages")
    if stages != ["research", "architecture", "tooling", "roadmap", "readiness"]:
        raise AssertionError(f"Live scenario context coverage is incomplete: {stages}")
    budgets = expectations.get("advisory_budgets", {})
    scalar_budgets = {
        key: value for key, value in budgets.items() if key != "artifact_bytes"
    }
    artifact_budgets = budgets.get("artifact_bytes", {})
    if (
        not all(isinstance(value, int) and value > 0 for value in scalar_budgets.values())
        or not isinstance(artifact_budgets, dict)
        or not all(isinstance(value, int) and value > 0 for value in artifact_budgets.values())
    ):
        raise AssertionError(f"Live scenario advisory budgets are invalid: {budgets}")

    require(
        root / "AGENTS.md",
        "entirely user-invoked",
        "Do not ask",
        "do not report it as skipped",
        "Never add the paid live suite to CI",
        "Never pass `-Approved` without an explicit user request",
        "Pass `-ContinueFirstSlice` only when",
    )
    policy_files = (
        root / "AGENTS.md",
        root / "README.md",
        root / "docs/live-bootstrap-acceptance.md",
        root / "docs/releasing-0.8.1.md",
        root / "docs/releasing-0.8.2.md",
        root / "docs/releasing-0.8.3.md",
        root / "docs/releasing-0.8.4.md",
        root / "docs/releasing-0.9.6.md",
        root / "docs/releasing-0.9.7.md",
        root / "docs/releasing-0.9.9.md",
        wrapper,
        runner,
    )
    forbidden_policy = (
        "Do you want me to run the paid live bootstrap acceptance suite before publishing",
        "Before publishing, ask the user",
        "If the user answers no",
        "explicitly skipped",
        "record that explicit skip",
    )
    for policy_file in policy_files:
        policy_text = policy_file.read_text(encoding="utf-8")
        for forbidden in forbidden_policy:
            if forbidden in policy_text:
                raise AssertionError(
                    f"{policy_file} restores a forbidden publication prompt: {forbidden}"
                )
    require(
        root / "README.md",
        "completely optional and user-invoked",
        "Publishing must not prompt for it or record it as skipped",
    )
    require(
        root / "docs/live-bootstrap-acceptance.md",
        "entirely user-invoked",
        "publication must not prompt for it",
        "clean-bootstrap",
        "real bundle provenance machinery",
        "workflow.stdout.log",
        "workflow.stderr.log",
        "monitor.jsonl",
        "Failed runs are retained",
        "must not be generalized",
        "command-scoped",
        "git -c safe.directory",
        "core.excludesFile",
        "never changes global Git configuration",
        "advisory",
        "Could not find home directory",
        "outer harness process",
        "inner `--sandbox workspace-write`",
        "first complete feature lifecycle",
        "first-slice.validation.log",
        "first-slice-managed-baseline.json",
        "-ExerciseIntakeSkill",
        "exact portable one-line workflow command",
    )
    require(
        wrapper,
        "LIVE_ACCEPTANCE_APPROVAL_REQUIRED",
        "only when the user explicitly requests",
        "publication must not prompt",
        "LIVE_ACCEPTANCE_CI_FORBIDDEN",
        "--approved",
        "--continue-first-slice",
        "--exercise-intake-skill",
    )
    require(
        runner,
        "after an explicit user request",
        "127.0.0.1",
        "bundle",
        "install",
        "program-kit-live-candidate",
        "--sandbox workspace-write",
        "safe.directory",
        "core.excludesFile",
        "write_worker_guidance",
        "PYTHONUTF8",
        "analyze_metrics",
        ".evidence.json",
        "server.shutdown()",
        "$speckit-program-kit-governance-bootstrap",
        "specify_bridge_command",
        "install_local_candidate_bundle",
        '"--offline"',
        "validate_intake_skill_result",
    )
    print("Live bootstrap acceptance request, CI, fixture, and evidence contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
