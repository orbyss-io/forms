from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


EXTENSION_CATALOG = (
    "https://raw.githubusercontent.com/orbyss-io/program-kit/"
    "main/catalogs/extensions.json"
)
WORKFLOW_CATALOG = (
    "https://raw.githubusercontent.com/orbyss-io/program-kit/"
    "main/catalogs/workflows.json"
)
PRESET_CATALOG = (
    "https://raw.githubusercontent.com/orbyss-io/program-kit/"
    "main/catalogs/presets.json"
)
BUNDLE_CATALOG = (
    "https://raw.githubusercontent.com/orbyss-io/program-kit/"
    "main/catalogs/bundles.json"
)
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

def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source_workflow = yaml.safe_load(
        (root / "workflows/program-kit-bootstrap/workflow.yml").read_text(
            encoding="utf-8"
        )
    )
    expected_steps = [step["id"] for step in source_workflow.get("steps", [])]
    with tempfile.TemporaryDirectory(prefix="program-kit-public-test-") as directory:
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
        run(
            "specify",
            "extension",
            "catalog",
            "add",
            EXTENSION_CATALOG,
            "--name",
            "program-kit",
            "--install-allowed",
            cwd=project,
        )
        run(
            "specify",
            "preset",
            "catalog",
            "add",
            PRESET_CATALOG,
            "--name",
            "program-kit",
            "--install-allowed",
            cwd=project,
        )
        run(
            "specify",
            "workflow",
            "catalog",
            "add",
            WORKFLOW_CATALOG,
            "--name",
            "program-kit",
            cwd=project,
        )
        run(
            "specify",
            "bundle",
            "catalog",
            "add",
            BUNDLE_CATALOG,
            "--id",
            "program-kit",
            "--policy",
            "install-allowed",
            cwd=project,
        )

        # Spec Kit 1.0.1's bundle adapter routes workflow IDs through the
        # local-dev installer. Preinstalling the catalog workflow avoids that
        # defect while preserving the bundle's pinned workflow reference.
        run("specify", "workflow", "add", "program-kit-bootstrap", cwd=project)
        run("specify", "bundle", "install", "program-kit", cwd=project)

        extensions = yaml.safe_load(
            (project / ".specify/extensions.yml").read_text(encoding="utf-8")
        )
        hooks = set(extensions.get("hooks", {}))
        if hooks != EXPECTED_HOOKS:
            raise AssertionError(f"Installed hooks {sorted(hooks)} != {sorted(EXPECTED_HOOKS)}")
        if "program-kit-governance" not in extensions.get("installed", []):
            raise AssertionError("Program Kit Governance extension was not registered")
        if "program-kit-dotnet" not in extensions.get("installed", []):
            raise AssertionError("Program Kit .NET extension was not registered")

        workflow = yaml.safe_load(
            (
                project
                / ".specify/workflows/program-kit-bootstrap/workflow.yml"
            ).read_text(encoding="utf-8")
        )
        step_ids = [step["id"] for step in workflow.get("steps", [])]
        if step_ids != expected_steps:
            raise AssertionError(f"Installed workflow steps {step_ids} != {expected_steps}")

        deployed_extension = project / ".specify/extensions/program-kit-governance"
        governance = deployed_extension / "scripts/governance_state.py"
        if not governance.is_file():
            raise AssertionError("Installed governance-state validator is missing")
        if not (deployed_extension / "scripts/codex_bootstrap_preflight.py").is_file():
            raise AssertionError("Installed Codex bootstrap preflight is missing")
        deployed_dotnet = project / ".specify/extensions/program-kit-dotnet"
        if not (deployed_dotnet / "scripts/dotnet_sync.py").is_file():
            raise AssertionError("Installed .NET sync extension is missing")
        if not (
            project
            / ".agents/skills/speckit-program-kit-governance-bootstrap/SKILL.md"
        ).is_file():
            raise AssertionError("Installed Codex-safe bootstrap skill is missing")
        if not (
            project
            / ".agents/skills/speckit-program-kit-governance-view-c4/SKILL.md"
        ).is_file():
            raise AssertionError("Installed C4 projection viewing skill is missing")
        run(sys.executable, str(governance), "validate-installation", cwd=project)
        for reference in ("vertical-slicing.md", "modularity-and-contracts.md", "default-adoption.md"):
            if not (deployed_extension / "references" / reference).is_file():
                raise AssertionError(f"Installed extension is missing {reference}")

    print("Live public-catalog installation test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
