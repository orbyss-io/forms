from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


def load_module(root: Path):
    path = root / "extensions/program-kit-governance/scripts/bootstrap_context.py"
    spec = importlib.util.spec_from_file_location("bootstrap_context", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, value: dict) -> None:
    write(path, json.dumps(value, indent=2) + "\n")


def seed_project(project: Path, module, run_id: str) -> None:
    run = project / ".specify/workflows/runs" / run_id
    write(project / "docs/architecture/project-intent.md", "# Tiny application\n\n[E-001] A visitor sees a greeting.\n")
    architecture = {
        "schema_version": "1.0",
        "model_id": "tiny-application",
        "title": "Tiny application",
        "sources": [{
            "id": "project-intent",
            "path": "docs/architecture/project-intent.md",
            "sha256": module.sha256_file(project / "docs/architecture/project-intent.md"),
            "format": "program-kit-intent-markdown",
            "importer": {"id": "program-kit-intake", "version": "1.0"},
        }],
        "decisions": [],
        "documentation": [],
        "constraints": [],
        "elements": [
            {
                "id": "visitor", "type": "person", "name": "Visitor",
                "description": "Person who requests the greeting.", "status": "explicit",
                "ownership": "", "technology": "", "evidence": ["e-001"],
                "decision_refs": [], "tags": [], "properties": {}, "perspectives": [],
                "url": "", "group": "", "archetype": "",
            },
            {
                "id": "greeting-system", "type": "software-system", "name": "Greeting system",
                "description": "Shows the greeting.", "status": "explicit",
                "ownership": "Project", "technology": "", "evidence": ["e-001"],
                "decision_refs": [], "tags": [], "properties": {}, "perspectives": [],
                "url": "", "group": "", "archetype": "",
            },
            {
                "id": "greeting-context", "type": "bounded-context", "name": "Greeting",
                "description": "Candidate greeting capability boundary.", "status": "proposed",
                "ownership": "Project", "technology": "", "evidence": ["e-001"],
                "decision_refs": [], "tags": [], "properties": {}, "perspectives": [],
                "url": "", "group": "", "archetype": "",
            },
        ],
        "relationships": [{
            "id": "visitor-requests-greeting", "source": "visitor", "target": "greeting-system",
            "description": "Requests a greeting", "technology": "", "status": "explicit",
            "evidence": ["e-001"], "decision_refs": [], "tags": [], "properties": {},
            "perspectives": [], "url": "",
        }],
        "views": [
            {
                "key": "system-context", "type": "system-context", "title": "System Context",
                "description": "People and systems around the greeting system.", "scope": "greeting-system",
                "elements": ["visitor", "greeting-system"], "relationships": ["visitor-requests-greeting"],
                "decision_refs": [], "filters": [], "order": [], "layout": {"rankDirection": "lr"},
                "animations": [], "properties": {},
            },
            {
                "key": "domain-context", "type": "domain-context", "title": "Domain Context Map",
                "description": "Candidate greeting domain boundary.", "scope": "",
                "elements": ["greeting-system", "greeting-context"], "relationships": [],
                "decision_refs": [], "filters": [], "order": [], "layout": {"rankDirection": "lr"},
                "animations": [], "properties": {},
            },
        ],
        "configuration": {"styles": [], "themes": [], "terminology": {}, "branding": {}, "properties": {}},
        "extensions": [],
    }
    write_json(project / "docs/architecture/architecture-map.json", architecture)
    architecture_module = module._load_intake_module()._load_architecture_module()
    write(
        project / "docs/architecture/workspace.dsl",
        architecture_module.StructurizrDslExporter().export(architecture),
    )
    artifact_paths = {
        "project_intent": project / "docs/architecture/project-intent.md",
        "architecture_map": project / "docs/architecture/architecture-map.json",
        "c4_projection": project / "docs/architecture/workspace.dsl",
    }
    intake = {
        "schema_version": "1.0",
        "status": "confirmed",
        "project": {"name": "Tiny application", "summary": "A visitor sees a greeting."},
        "artifacts": {
            key: {
                "path": path.relative_to(project).as_posix(),
                "sha256": module.sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for key, path in artifact_paths.items()
        },
        "evidence": [{
            "id": "e-001", "source": "project_intent", "locator": "project-intent.md:3",
            "summary": "A visitor sees a greeting.",
        }],
        "facts": [{"id": "fact-greeting", "statement": "The application shows a greeting.", "evidence": ["e-001"]}],
        "scope": {"included": [], "excluded": [], "deferred": []},
        "actors": [{"id": "actor-visitor", "statement": "A visitor uses the application.", "evidence": ["e-001"]}],
        "journeys": [{"id": "journey-greeting", "statement": "A visitor sees a greeting.", "evidence": ["e-001"]}],
        "quality_requirements": [],
        "integrations": [],
        "choices": [],
        "capability_assessments": [{
            "id": "coverage-vertical-slice", "need": "Deliver the greeting as an observable journey.",
            "coverage": "guided", "program_kit_capability": "vertical-slicing",
            "disposition": "program-kit-default", "evidence": ["e-001"],
        }],
        "open_items": [],
        "candidate_slice_signals": [{
            "id": "slice-greeting", "statement": "Visitor requests and observes the greeting.", "evidence": ["e-001"]
        }],
        "routing": {
            "languages": [], "frameworks": [], "interfaces": ["command-line"],
            "included_surfaces": ["greeting"], "excluded_surfaces": [],
            "capabilities": ["vertical-slicing"],
        },
    }
    write_json(project / module.INTAKE_PATH, intake)
    write_json(run / "inputs.json", {"inputs": {"bootstrap_intake": module.INTAKE_PATH.as_posix()}})
    markdown = {
        ".specify/memory/constitution.md": "# Constitution\n\n**Status**: Ratified\n",
        "docs/architecture/bootstrap-assessment.md": "# Assessment\n\n## Actors\n\n- **Visitor** sees a greeting.\n",
        "docs/architecture/decision-backlog.md": "# Backlog\n\n## ADR-001\n\n**Status**: Deferred\n",
        "docs/architecture/tooling-evaluation.md": "# Tooling\n\n## Quality\n\n- **Decision**: built-in checks.\n",
        "docs/architecture/architecture.md": "# Architecture\n\n## Candidate slices\n\n- **SPC-001** greeting.\n",
        "docs/architecture/quality-attributes.md": "# Quality attributes\n\n## QA-001\n\n**Status**: Ready\n",
        "docs/architecture/quality-system.md": "# Quality system\n\n## Bootstrap gates\n",
        "docs/architecture/technology-radar.md": "# Technology radar\n\n## Accepted\n",
        "docs/architecture/traceability.md": "# Traceability\n\n| Design | SPC-001 |\n| --- | --- |\n",
        "docs/architecture/specification-roadmap.md": "# Roadmap\n\n### SPC-001: Greeting\n\n**Status**: Ready\n",
        "docs/architecture/decisions/bootstrap-baseline.md": "# Bootstrap baseline\n\n**Status**: Accepted\n",
        "docs/architecture/decisions/ADR-001.md": "# ADR-001: Boundary\n\n**Status**: Proposed\n",
    }
    for relative, text in markdown.items():
        write(project / relative, text)
    json_files = {
        "docs/architecture/bootstrap-decisions.json": {
            "schema_version": "1.0",
            "choices": [{"id": "greeting", "decision": "Static greeting"}],
        },
        ".specify/governance/bootstrap-assessment-approval.json": {"status": "Approved"},
        ".specify/memory/constitution-ratification.json": {"status": "Ratified"},
        ".specify/governance/bootstrap-approval.json": {"status": "Approved"},
    }
    for relative, value in json_files.items():
        write_json(project / relative, value)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    module = load_module(root)
    with tempfile.TemporaryDirectory(prefix="program-kit-context-test-") as directory:
        project = Path(directory)
        run_id = "context-test-1"
        seed_project(project, module, run_id)
        module.validate_intake(project, run_id)

        for stage in module.STAGE_ARTIFACTS:
            path, payload = module.build_context(project, run_id, stage)
            if not path.is_file() or payload["stage"] != stage:
                raise AssertionError(f"{stage} context was not written")
            if payload["bootstrap_intake"]["path"] != "docs/architecture/bootstrap-intake.json":
                raise AssertionError("Bootstrap-intake provenance is not canonical")
            if payload["intake"]["status"] != "confirmed":
                raise AssertionError("Stage context did not embed the confirmed intake")
            if payload["architecture_map"]["model_id"] != "tiny-application":
                raise AssertionError("Stage context did not embed the canonical architecture map")
            if payload["reading_policy"]["mode"] != "deny-by-default":
                raise AssertionError(f"{stage} context does not enforce deny-by-default reading")
            if "artifacts" in payload:
                raise AssertionError(f"{stage} stage brief embeds the evidence index")
            output_contract = payload["output_contract"]
            for artifact, budget in output_contract["artifact_byte_budgets"].items():
                if artifact not in output_contract["write_paths"] or budget <= 0:
                    raise AssertionError(
                        f"{stage} output contract contains an invalid artifact budget"
                    )
            evidence_path = project / payload["evidence_index"]["path"]
            if not evidence_path.is_file():
                raise AssertionError(f"{stage} evidence index was not written")
            module.validate_context(project, run_id, stage)

        roadmap_path = (
            project
            / ".specify/workflows/runs"
            / run_id
            / "program-kit-context/roadmap.json"
        )
        roadmap = json.loads(roadmap_path.read_text(encoding="utf-8"))
        if roadmap["authorities"]["assessment_approval"]["status"] != "Approved":
            raise AssertionError("Approved authority was not included in context")
        adr = next(item for item in roadmap["decisions"] if item["path"].endswith("ADR-001.md"))
        if adr["status"] != "Proposed":
            raise AssertionError("ADR status was not indexed")
        if roadmap_path.stat().st_size >= 32 * 1024:
            raise AssertionError("Compact stage brief exceeds its deterministic size ceiling")
        roadmap_budget = roadmap["output_contract"]["artifact_byte_budgets"].get(
            "docs/architecture/architecture.md"
        )
        if roadmap_budget != 12 * 1024:
            raise AssertionError("Roadmap did not inherit the final architecture byte budget")

        original = roadmap_path.read_bytes()
        write(
            project / "docs/architecture/quality-system.md",
            "# Quality system\n\n## Changed after context generation\n",
        )
        try:
            module.validate_context(project, run_id, "roadmap")
        except module.ContextError as exc:
            if "stale or invalid" not in str(exc):
                raise
        else:
            raise AssertionError("Context validation accepted a changed source")
        if roadmap_path.read_bytes() != original:
            raise AssertionError("Read-only context validation rewrote the stored context")

        local_config = (
            project
            / ".specify/extensions/program-kit-governance/program-kit-governance-config.local.yml"
        )
        write(
            local_config,
            """architecture:
  decisions: "governance/decisions"
  specification_roadmap: "governance/roadmap.md"
constitution:
  document: "governance/constitution.md"
  ratification: "governance/ratification.json"
""",
        )
        for source, destination in (
            ("docs/architecture/specification-roadmap.md", "governance/roadmap.md"),
            (".specify/memory/constitution.md", "governance/constitution.md"),
            (".specify/memory/constitution-ratification.json", "governance/ratification.json"),
            ("docs/architecture/decisions/bootstrap-baseline.md", "governance/decisions/bootstrap-baseline.md"),
            ("docs/architecture/decisions/ADR-001.md", "governance/decisions/ADR-001.md"),
        ):
            write(project / destination, (project / source).read_text(encoding="utf-8"))
        _, configured = module.build_context(project, run_id, "readiness")
        if configured["governance"]["paths"]["decisions"] != "governance/decisions":
            raise AssertionError("Compact context ignored the configured decisions path")
        if configured["reading_policy"]["required_full_reads"] != ["governance/constitution.md"]:
            raise AssertionError("Compact context ignored the configured constitution path")
        configured_evidence = json.loads(
            (project / configured["evidence_index"]["path"]).read_text(encoding="utf-8")
        )
        configured_paths = {item["path"] for item in configured_evidence["artifacts"]}
        if not {
            "governance/roadmap.md",
            "governance/constitution.md",
            "governance/ratification.json",
            "governance/decisions/bootstrap-baseline.md",
        }.issubset(configured_paths):
            raise AssertionError(f"Configured governance evidence is incomplete: {configured_paths}")
        module.validate_context(project, run_id, "readiness")

        managed_project = project / "managed-profile"
        managed_run_id = "managed-profile-test"
        seed_project(managed_project, module, managed_run_id)
        for relative in (
            module.DOTNET_SDK_MANIFEST,
            module.NODE_VERSION_MANIFEST,
            module.WEB_PACKAGE_MANIFEST,
            module.WEB_PACKAGE_LOCK,
        ):
            source = root / Path(
                relative.as_posix().replace(".specify/extensions/", "extensions/")
            )
            write(managed_project / relative, source.read_text(encoding="utf-8"))
        pins = {
            "dotnet-sdk": "10.0.202",
            "node": "24.20.0",
            "typescript": "7.0.2",
            "@types/node": "24.13.3",
            "@playwright/test": "1.62.1",
        }
        managed_decisions = {
            "selected_profiles": ["dotnet", "typescript-web"],
            "toolchain": {
                "source": "program-kit-default",
                "pins": dict(pins),
                "override_reason": "",
            },
            "overrides": [],
        }
        managed_decision_path = (
            managed_project / "docs/architecture/bootstrap-decisions.json"
        )
        write_json(managed_decision_path, managed_decisions)
        _, research = module.build_context(
            managed_project, managed_run_id, "research"
        )
        if research["managed_profile_pins"]["pins"] != pins:
            raise AssertionError("Research context did not expose exact selected-profile pins")
        if len(research["managed_profile_pins"]["sources"]) != 4:
            raise AssertionError("Research context did not bind every managed pin manifest")
        module.validate_profile_pin_decisions(managed_project, managed_run_id)

        managed_decisions["toolchain"]["pins"]["typescript"] = "6.0.0"
        write_json(managed_decision_path, managed_decisions)
        try:
            module.validate_profile_pin_decisions(managed_project, managed_run_id)
        except module.ContextError as exc:
            if "cannot replace" not in str(exc):
                raise
        else:
            raise AssertionError("A researched TypeScript candidate replaced the managed pin")

        managed_decisions["toolchain"] = {
            "source": "override",
            "pins": {**pins, "dotnet-sdk": "9.0.100"},
            "override_reason": "The user explicitly retained the local SDK",
        }
        managed_decisions["overrides"] = [
            {
                "id": "managed-toolchain-version",
                "decision": "Retain the local .NET SDK",
            }
        ]
        write_json(managed_decision_path, managed_decisions)
        module.validate_profile_pin_decisions(managed_project, managed_run_id)

        managed_decisions["toolchain"]["pins"]["typescript"] = "6.0.0"
        write_json(managed_decision_path, managed_decisions)
        try:
            module.validate_profile_pin_decisions(managed_project, managed_run_id)
        except module.ContextError as exc:
            if "other managed pins remain authoritative" not in str(exc):
                raise
        else:
            raise AssertionError("The local .NET exception also changed a managed package pin")

        try:
            module.safe_run_directory(project, "../escape")
        except module.ContextError:
            pass
        else:
            raise AssertionError("Unsafe workflow run ID was accepted")

    print("Bootstrap context generation and staleness checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
