from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def model(intent: Path, decision: Path | None = None) -> dict:
    decisions = []
    decision_refs: list[str] = []
    status = "explicit"
    if decision is not None:
        decisions.append(
            {
                "id": "adr-001",
                "path": "docs/architecture/decisions/ADR-001.md",
                "sha256": digest(decision),
                "title": "System boundary",
                "date": "2026-09-06",
                "status": "Accepted",
                "scope": "Greeting system",
                "owner": "Maintainers",
                "supersedes": [],
            }
        )
        decision_refs = ["adr-001"]
        status = "accepted"
    common = {
        "ownership": "Project",
        "technology": "",
        "evidence": ["e-001"],
        "decision_refs": decision_refs,
        "tags": [],
        "properties": {},
        "perspectives": [],
        "url": "",
        "group": "",
        "archetype": "",
    }
    return {
        "schema_version": "1.0",
        "model_id": "greeting-system",
        "title": "Greeting system",
        "sources": [
            {
                "id": "project-intent",
                "path": "docs/architecture/project-intent.md",
                "sha256": digest(intent),
                "format": "program-kit-intent-markdown",
                "importer": {"id": "program-kit-intake", "version": "1.0"},
            }
        ],
        "decisions": decisions,
        "documentation": [],
        "constraints": [],
        "elements": [
            {
                "id": "visitor",
                "type": "person",
                "name": "Visitor",
                "description": "Requests a greeting.",
                "status": "explicit",
                **{**common, "ownership": "", "decision_refs": []},
            },
            {
                "id": "greeting",
                "type": "software-system",
                "name": "Greeting",
                "description": "Shows the greeting.",
                "status": status,
                **common,
            },
            {
                "id": "greeting-context",
                "type": "bounded-context",
                "name": "Greeting context",
                "description": "Candidate domain boundary.",
                "status": "proposed",
                **{**common, "decision_refs": []},
            },
        ],
        "relationships": [
            {
                "id": "requests-greeting",
                "source": "visitor",
                "target": "greeting",
                "description": "Requests a greeting",
                "technology": "",
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
                "description": "Greeting boundary",
                "scope": "greeting",
                "elements": ["visitor", "greeting"],
                "relationships": ["requests-greeting"],
                "decision_refs": decision_refs,
                "filters": [],
                "order": [],
                "layout": {"rankDirection": "lr"},
                "animations": [],
                "properties": {},
            },
            {
                "key": "domain-context",
                "type": "domain-context",
                "title": "Domain Context Map",
                "description": "Candidate context",
                "scope": "",
                "elements": ["greeting", "greeting-context"],
                "relationships": [],
                "decision_refs": decision_refs,
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
        "extensions": [
            {
                "id": "blocked-script",
                "kind": "structurizr-script",
                "content": "!script unsafe.groovy",
                "policy": "blocked-executable",
                "source": "workspace.dsl:1",
            }
        ],
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    scripts = root / "extensions/program-kit-governance/scripts"
    architecture = load_module(scripts / "architecture_map.py", "test_architecture_map")
    intake_module = load_module(scripts / "bootstrap_intake.py", "test_bootstrap_intake")

    skill = (
        root
        / "extensions/program-kit-governance/commands/speckit.program-kit-governance.bootstrap.md"
    ).read_text(encoding="utf-8")
    command = (
        'specify workflow run program-kit-bootstrap --input '
        '"bootstrap_intake=docs/architecture/bootstrap-intake.json" --input "integration=auto"'
    )
    if command not in skill or "`\n" in command or "\\\n" in command:
        raise AssertionError("Bootstrap skill does not contain the portable one-line command")
    if any(token in skill for token in ("--input initial_design", "normalize-design", "bootstrap-brief.json")):
        raise AssertionError("Bootstrap skill retained the legacy front door")

    with tempfile.TemporaryDirectory(prefix="program-kit-intake-") as directory:
        project = Path(directory)
        intent = project / "docs/architecture/project-intent.md"
        decision = project / "docs/architecture/decisions/ADR-001.md"
        write(intent, "# Greeting\n\n[E-001] A visitor receives a greeting.\n")
        write(decision, "# ADR-001: System boundary\n\n- **Status**: Accepted\n")
        value = model(intent, decision)
        architecture.validate_model(value, project)
        dsl = architecture.StructurizrDslExporter().export(value)
        if "greeting-context =" in dsl or "greeting_context =" not in dsl:
            raise AssertionError("C4 projection did not translate canonical IDs into portable DSL identifiers")
        if "ProgramKitId:greeting-context" not in dsl:
            raise AssertionError("C4 projection did not retain the canonical Program Kit identity")
        if "!adrs \"docs/architecture/decisions\"" not in dsl:
            raise AssertionError("Structurizr projection did not attach the ADR catalog")
        if "// BLOCKED structurizr-script: !script unsafe.groovy" not in dsl:
            raise AssertionError("Executable DSL extension was not rendered inert")
        dsl_path = project / "docs/architecture/workspace.dsl"
        map_path = project / "docs/architecture/architecture-map.json"
        write(dsl_path, dsl)
        write(map_path, json.dumps(value, indent=2) + "\n")
        imported = architecture.StructurizrDslImporter().import_path(dsl_path, value).model
        architecture.validate_model(imported, project)
        if {item["id"] for item in imported["decisions"]} != {"adr-001"}:
            raise AssertionError("C4 round trip lost canonical ADR links")
        active_dsl = dsl.replace(
            "// BLOCKED structurizr-script: !script unsafe.groovy",
            "!script unsafe.groovy",
        )
        write(dsl_path, active_dsl)
        guarded = architecture.StructurizrDslImporter().import_path(dsl_path, value).model
        blocked = [
            item
            for item in guarded["extensions"]
            if item["content"] == "!script unsafe.groovy"
            and item["policy"] == "blocked-executable"
        ]
        if len(blocked) != 1:
            raise AssertionError("Structurizr import did not preserve executable DSL as one inert extension")

        detailed = json.loads(json.dumps(value))
        detailed["elements"].extend(
            [
                {
                    "id": "greeting-api",
                    "type": "container",
                    "name": "Greeting API",
                    "description": "Receives greeting requests.",
                    "status": "proposed",
                    "ownership": "Project",
                    "technology": "HTTP",
                    "parent": "greeting",
                    "evidence": ["e-001"],
                    "decision_refs": [],
                    "tags": [],
                    "properties": {},
                    "perspectives": [],
                    "url": "",
                    "group": "",
                    "archetype": "",
                },
                {
                    "id": "greeting-handler",
                    "type": "component",
                    "name": "Greeting handler",
                    "description": "Produces the greeting response.",
                    "status": "proposed",
                    "ownership": "Project",
                    "technology": "Python",
                    "parent": "greeting-api",
                    "evidence": ["e-001"],
                    "decision_refs": [],
                    "tags": [],
                    "properties": {},
                    "perspectives": [],
                    "url": "",
                    "group": "",
                    "archetype": "",
                },
            ]
        )
        detailed["views"].extend(
            [
                {
                    "key": "containers",
                    "type": "container",
                    "title": "Greeting containers",
                    "description": "Container detail",
                    "scope": "greeting",
                    "elements": ["greeting-api"],
                    "relationships": [],
                    "decision_refs": [],
                    "filters": [],
                    "order": [],
                    "layout": {"rankDirection": "lr"},
                    "animations": [],
                    "properties": {},
                },
                {
                    "key": "components",
                    "type": "component",
                    "title": "Greeting components",
                    "description": "Component detail",
                    "scope": "greeting-api",
                    "elements": ["greeting-handler"],
                    "relationships": [],
                    "decision_refs": [],
                    "filters": [],
                    "order": [],
                    "layout": {"rankDirection": "lr"},
                    "animations": [],
                    "properties": {},
                },
            ]
        )
        detailed_dsl = architecture.StructurizrDslExporter().export(detailed)
        write(dsl_path, detailed_dsl)
        detailed_roundtrip = architecture.StructurizrDslImporter().import_path(dsl_path, detailed).model
        architecture.validate_model(detailed_roundtrip, project)
        parent_by_id = {
            item["id"]: item.get("parent") for item in detailed_roundtrip["elements"]
        }
        if parent_by_id.get("greeting-api") != "greeting" or parent_by_id.get("greeting-handler") != "greeting-api":
            raise AssertionError("C4 container/component round trip lost hierarchy")

        stale = json.loads(json.dumps(value))
        stale["decisions"][0]["sha256"] = "0" * 64
        try:
            architecture.validate_model(stale, project)
        except architecture.ArchitectureMapError as exc:
            if "missing or stale" not in str(exc):
                raise
        else:
            raise AssertionError("Architecture model accepted a stale ADR hash")

        intake_path = project / intake_module.CANONICAL_INTAKE
        intake_path.parent.mkdir(parents=True, exist_ok=True)
        blank_intake = {"artifacts": {}}
        write(intake_path, json.dumps(blank_intake) + "\n")
        changed = intake_module.changed_artifacts(project)
        if set(changed) != {path.as_posix() for path in intake_module.CANONICAL_ARTIFACTS.values()}:
            raise AssertionError(f"Changed-artifact detection is incomplete: {changed}")

    workflow = (root / "workflows/program-kit-bootstrap/workflow.yml").read_text(encoding="utf-8")
    if "initial_design" in workflow or "normalize-design" in workflow or "bootstrap-brief" in workflow:
        raise AssertionError("Workflow retained a temporal legacy adapter")
    if "bootstrap_intake" not in workflow or "validate-bootstrap-intake" not in workflow:
        raise AssertionError("Workflow does not consume the confirmed intake contract")

    print("Conversational intake, C4 model, ADR linkage, and one-line handoff are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
