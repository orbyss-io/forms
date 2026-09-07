from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def run_state(project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    script = project / ".specify/extensions/program-kit-governance/scripts/governance_state.py"
    result = subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise AssertionError(
            f"governance_state.py {' '.join(arguments)} failed:\n{result.stdout}{result.stderr}"
        )
    return result


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roadmap() -> str:
    return """# Specification roadmap

### SLC-CALCULATE-001: Calculate a visible price

- **User-visible outcome**: A shopper submits a quantity and sees the calculated price.
- **Scope**: One request through a displayed calculation result.
- **Non-goals**: Persistence, accounts, discounts, and production scaling.
- **Required Accepted ADRs**: None
- **Dependencies**: Approved bootstrap baseline only.
- **Owned public contracts**: Calculate-price request and response.
- **Owned lifecycle portions**: Input validation through displayed result.
- **Owned data**: Ephemeral quantity and calculated amount.
- **Quality scenarios**: A valid quantity returns the deterministic amount in one interaction.
- **Verification responsibility**: Price calculation feature owner.
- **Recommended sequence**: 1
- **Status**: Ready
"""


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    artifacts = root / "artifacts"
    required_archives = {
        "governance": artifacts / f"program-kit-governance-{version}.zip",
        "dotnet": artifacts / f"program-kit-dotnet-{version}.zip",
        "preset": artifacts / f"program-kit-governance-preset-{version}.zip",
        "workflow": artifacts / f"program-kit-bootstrap-{version}.zip",
    }
    missing = [str(path) for path in required_archives.values() if not path.is_file()]
    if missing:
        raise AssertionError(f"Build release assets before the clean-consumer test: {missing}")

    with tempfile.TemporaryDirectory(prefix="program-kit-clean-consumer-") as directory:
        project = Path(directory)
        destinations = {
            "governance": project / ".specify/extensions/program-kit-governance",
            "dotnet": project / ".specify/extensions/program-kit-dotnet",
            "preset": project / ".specify/presets/program-kit-governance-preset",
            "workflow": project / ".specify/workflows/program-kit-bootstrap",
        }
        for name, archive in required_archives.items():
            destinations[name].mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive) as package:
                package.extractall(destinations[name])

        write(
            project / ".specify/workflows/workflow-registry.json",
            json.dumps(
                {
                    "schema_version": "1.0",
                    "workflows": {
                        "program-kit-bootstrap": {
                            "version": version,
                            "source": "release-regression",
                        }
                    },
                },
                indent=2,
            )
            + "\n",
        )
        write(
            project / ".specify/presets/.registry",
            json.dumps(
                {
                    "schema_version": "1.0",
                    "presets": {
                        "program-kit-governance-preset": {
                            "version": version,
                            "source": "release-regression",
                        }
                    },
                },
                indent=2,
            )
            + "\n",
        )
        write(
            project / ".specify/bundle-records.json",
            json.dumps(
                {
                    "schema_version": "1.0",
                    "bundles": [
                        {
                            "bundle_id": "program-kit",
                            "version": version,
                            "contributed_components": [
                                {
                                    "kind": "extensions",
                                    "id": "program-kit-governance",
                                    "version": version,
                                },
                                {
                                    "kind": "extensions",
                                    "id": "program-kit-dotnet",
                                    "version": version,
                                },
                                {
                                    "kind": "presets",
                                    "id": "program-kit-governance-preset",
                                    "version": version,
                                },
                                {
                                    "kind": "workflows",
                                    "id": "program-kit-bootstrap",
                                    "version": version,
                                },
                            ],
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
        )
        write(
            project / ".specify/integration.json",
            '{"integration":"codex","default_integration":"codex"}\n',
        )
        write(
            project / "docs/architecture/project-intent.md",
            "# Confirmed price-calculator intent\n",
        )
        write(
            project / "docs/architecture/bootstrap-intake.json",
            '{"schema_version":"1.0","status":"confirmed"}\n',
        )

        for relative in (
            "docs/architecture/bootstrap-assessment.md",
            "docs/architecture/decision-backlog.md",
            "docs/architecture/tooling-evaluation.md",
        ):
            write(project / relative, f"# {Path(relative).stem}\n")
        decisions = {
            "schema_version": "1.0",
            "default_profile": {"id": "program-kit-standard", "version": version},
            "selected_profiles": [],
            "choices": [
                {
                    "id": "calculation-boundary",
                    "decision": "Keep the first slice inside the calculation boundary",
                    "source": "explicit-intake",
                    "rationale": "It produces the first observable consumer outcome",
                    "override": "Use a later reviewed decision",
                }
            ],
            "overrides": [],
            "acknowledgements": [],
            "unresolved": [],
            "deferred": [],
        }
        write(
            project / "docs/architecture/bootstrap-decisions.json",
            json.dumps(decisions, indent=2) + "\n",
        )
        run_state(project, "write-review", "--stage", "assessment")
        run_state(project, "accept-assessment", "--verdict", "approve")

        write(
            project / ".specify/memory/constitution.md",
            """# Price Calculator Constitution

**Status**: Draft

## Core Principles

### I. Observable calculation outcomes
Every slice delivers verified user-visible behavior.

## Constraints

Architecture decisions require explicit evidence.

## Workflow

Specifications follow ratified governance and Accepted ADRs.

## Governance

Amendments require human approval. Version changes follow semantic versioning. Compliance is reviewed at each gate.

**Version**: 1.0.0 | **Ratified**: PENDING_RATIFICATION | **Last Amended**: 2026-09-01
""",
        )
        run_state(project, "begin")
        run_state(project, "write-review", "--stage", "constitution")
        run_state(project, "ratify", "--verdict", "ratify")

        assessment_approval = json.loads(
            (project / ".specify/governance/bootstrap-assessment-approval.json").read_text(
                encoding="utf-8"
            )
        )
        decision_hash = assessment_approval["artifacts"][
            "docs/architecture/bootstrap-decisions.json"
        ]
        artifacts_text = {
            "docs/architecture/README.md": "# Architecture navigation\n",
            "docs/architecture/architecture-map.json": "{}\n",
            "docs/architecture/workspace.dsl": "workspace \"Price Calculator\" {\n}\n",
            "docs/architecture/architecture.md": (
                "# Architecture\n\nSLC-CALCULATE-001 owns the calculation outcome and contract.\n"
            ),
            "docs/architecture/quality-attributes.md": "# Quality attributes\n",
            "docs/architecture/technology-radar.md": "# Technology radar\n",
            "docs/architecture/traceability.md": (
                "# Traceability\n\nSLC-CALCULATE-001 traces design to calculation verification.\n"
            ),
            "docs/architecture/quality-system.md": "# Quality system\n",
            "docs/architecture/specification-roadmap.md": roadmap(),
            "docs/architecture/decisions/README.md": "# Decisions\n",
            "docs/architecture/decisions/bootstrap-baseline.md": (
                "# Bootstrap baseline\n\n- Status: Accepted\n\n"
                f"Profile: program-kit-standard {version}\n\n"
                f"Decision register: {decision_hash}\n\n"
                "calculation-boundary is adopted.\n"
            ),
        }
        for relative, text in artifacts_text.items():
            write(project / relative, text)

        run_state(project, "synchronize-roadmap")
        run_state(project, "validate-bootstrap-consistency")
        run_state(project, "validate-bootstrap", "--require-ready")

        architecture = (project / "docs/architecture/architecture.md").read_text(
            encoding="utf-8"
        )
        traceability = (project / "docs/architecture/traceability.md").read_text(
            encoding="utf-8"
        )
        for label, text in (("architecture", architecture), ("traceability", traceability)):
            if "| `SLC-CALCULATE-001` | Calculate a visible price | `Ready` |" not in text:
                raise AssertionError(f"{label} does not agree with the authoritative Ready roadmap")

        run_state(project, "write-review", "--stage", "bootstrap")
        run_state(project, "accept-bootstrap", "--verdict", "approve")
        write(
            project / "docs/architecture/readiness-report.md",
            "**Status**: READY\n\n# Readiness report\n\nSLC-CALCULATE-001 is ready.\n",
        )
        completed = run_state(project, "complete-bootstrap")
        if "deterministically complete" not in completed.stdout:
            raise AssertionError("complete-bootstrap did not report success")
        completion_path = project / ".specify/governance/bootstrap-completion.json"
        if not completion_path.is_file():
            raise AssertionError("complete-bootstrap did not create bootstrap-completion.json")
        run_state(project, "validate-completion")

        completion = json.loads(completion_path.read_text(encoding="utf-8"))
        if completion["constitution_sha256"] != sha256(
            project / ".specify/memory/constitution.md"
        ):
            raise AssertionError("Completion constitution hash is invalid")
        if completion["bootstrap_approval_sha256"] != sha256(
            project / ".specify/governance/bootstrap-approval.json"
        ):
            raise AssertionError("Completion approval hash is invalid")
        if completion["readiness_report"]["sha256"] != sha256(
            project / "docs/architecture/readiness-report.md"
        ):
            raise AssertionError("Completion readiness-report hash is invalid")

    print("Clean-consumer bootstrap consistency and completion regression passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
