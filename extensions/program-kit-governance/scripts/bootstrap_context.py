from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path


SCHEMA_VERSION = "2.0"
CONTEXT_DIRECTORY = Path(".specify/workflows/runs")
INTAKE_PATH = Path("docs/architecture/bootstrap-intake.json")
INTAKE_ARTIFACTS = (
    "docs/architecture/project-intent.md",
    "docs/architecture/architecture-map.json",
    "docs/architecture/workspace.dsl",
    INTAKE_PATH.as_posix(),
)

STAGE_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "research": (
        "docs/architecture/bootstrap-assessment.md",
        "docs/architecture/bootstrap-decisions.json",
        "docs/architecture/decision-backlog.md",
    ),
    "architecture": (
        ".specify/memory/constitution.md",
        ".specify/memory/constitution-ratification.json",
        ".specify/governance/bootstrap-assessment-approval.json",
        "docs/architecture/bootstrap-assessment.md",
        "docs/architecture/bootstrap-decisions.json",
        "docs/architecture/decision-backlog.md",
        "docs/architecture/tooling-evaluation.md",
    ),
    "tooling": (
        ".specify/memory/constitution.md",
        ".specify/memory/constitution-ratification.json",
        ".specify/governance/bootstrap-assessment-approval.json",
        "docs/architecture/bootstrap-decisions.json",
        "docs/architecture/decision-backlog.md",
        "docs/architecture/tooling-evaluation.md",
        "docs/architecture/architecture.md",
        "docs/architecture/quality-attributes.md",
        "docs/architecture/technology-radar.md",
        "docs/architecture/traceability.md",
        "docs/architecture/decisions/bootstrap-baseline.md",
    ),
    "roadmap": (
        ".specify/memory/constitution.md",
        ".specify/memory/constitution-ratification.json",
        ".specify/governance/bootstrap-assessment-approval.json",
        "docs/architecture/bootstrap-decisions.json",
        "docs/architecture/decision-backlog.md",
        "docs/architecture/tooling-evaluation.md",
        "docs/architecture/architecture.md",
        "docs/architecture/quality-attributes.md",
        "docs/architecture/quality-system.md",
        "docs/architecture/technology-radar.md",
        "docs/architecture/traceability.md",
        "docs/architecture/decisions/bootstrap-baseline.md",
    ),
    "readiness": (
        ".specify/memory/constitution.md",
        ".specify/memory/constitution-ratification.json",
        ".specify/governance/bootstrap-assessment-approval.json",
        ".specify/governance/bootstrap-approval.json",
        "docs/architecture/bootstrap-decisions.json",
        "docs/architecture/decision-backlog.md",
        "docs/architecture/tooling-evaluation.md",
        "docs/architecture/architecture.md",
        "docs/architecture/quality-attributes.md",
        "docs/architecture/quality-system.md",
        "docs/architecture/specification-roadmap.md",
        "docs/architecture/technology-radar.md",
        "docs/architecture/traceability.md",
        "docs/architecture/decisions/bootstrap-baseline.md",
    ),
}

STAGE_FULL_READS = {
    "research": (),
    "architecture": (".specify/memory/constitution.md",),
    "tooling": (".specify/memory/constitution.md",),
    "roadmap": (".specify/memory/constitution.md",),
    "readiness": (".specify/memory/constitution.md",),
}

STAGE_FOCUS = {
    "research": "Verify only selected technologies and capabilities; excluded surfaces are out of scope.",
    "architecture": "Define the smallest governed architecture that realizes the confirmed intake journeys.",
    "tooling": "Adopt only controls required by selected capabilities and accepted boundaries.",
    "roadmap": "Create outcome-oriented specification entries from confirmed journeys and accepted decisions.",
    "readiness": "Prove the first Ready entry has accepted authority, owned risks, and sufficient evidence.",
}

GOVERNANCE_CONFIGS = (
    Path(".specify/extensions/program-kit-governance/program-kit-governance-config.yml"),
    Path(".specify/extensions/program-kit-governance/program-kit-governance-config.local.yml"),
)

OUTPUT_CONTRACTS = {
    "research": {
        "write_paths": [
            "docs/architecture/tooling-evaluation.md",
            "docs/architecture/bootstrap-decisions.json",
        ],
        "contract_references": [
            ".specify/extensions/program-kit-governance/references/bootstrap-decisions.schema.json"
        ],
        "validation_commands": [
            "python .specify/extensions/program-kit-governance/scripts/bootstrap_context.py validate-profile-pins --run-id <workflow-run-id>",
            "python .specify/extensions/program-kit-governance/scripts/governance_state.py validate-assessment"
        ],
    },
    "architecture": {
        "write_paths": [
            "docs/architecture/README.md",
            "docs/architecture/architecture.md",
            "docs/architecture/quality-attributes.md",
            "docs/architecture/technology-radar.md",
            "docs/architecture/traceability.md",
            "docs/architecture/architecture-map.json",
            "docs/architecture/workspace.dsl",
            "docs/architecture/decisions/README.md",
            "docs/architecture/decisions/bootstrap-baseline.md",
        ],
        "contract_references": [
            ".specify/extensions/program-kit-governance/references/architecture-map.schema.json"
        ],
        "validation_commands": [
            "python .specify/extensions/program-kit-governance/scripts/governance_state.py validate"
        ],
    },
    "tooling": {
        "write_paths": ["docs/architecture/quality-system.md"],
        "contract_references": [],
        "validation_commands": [],
    },
    "roadmap": {
        "write_paths": [
            "docs/architecture/specification-roadmap.md",
            "docs/architecture/architecture.md",
            "docs/architecture/traceability.md",
        ],
        "contract_references": [],
        "validation_commands": [
            "python .specify/extensions/program-kit-governance/scripts/governance_state.py validate-roadmap"
        ],
    },
    "readiness": {
        "write_paths": ["docs/architecture/readiness-report.md"],
        "contract_references": [],
        "validation_commands": [
            "python .specify/extensions/program-kit-governance/scripts/governance_state.py validate --require-roadmap --require-ready"
        ],
    },
}

ARTIFACT_BYTE_BUDGETS = {
    "docs/architecture/tooling-evaluation.md": 8 * 1024,
    "docs/architecture/architecture.md": 12 * 1024,
    "docs/architecture/architecture-map.json": 256 * 1024,
    "docs/architecture/workspace.dsl": 256 * 1024,
    "docs/architecture/quality-system.md": 12 * 1024,
    "docs/architecture/readiness-report.md": 4 * 1024,
}

AUTHORITY_JSON = {
    "docs/architecture/bootstrap-decisions.json": "assessment_decisions",
    ".specify/governance/bootstrap-assessment-approval.json": "assessment_approval",
    ".specify/memory/constitution-ratification.json": "constitution_ratification",
    ".specify/governance/bootstrap-approval.json": "bootstrap_approval",
}

DOTNET_SDK_MANIFEST = Path(
    ".specify/extensions/program-kit-dotnet/templates/dotnet/files/global.json"
)
NODE_VERSION_MANIFEST = Path(
    ".specify/extensions/program-kit-dotnet/templates/dotnet/files/.nvmrc"
)
WEB_PACKAGE_MANIFEST = Path(
    ".specify/extensions/program-kit-dotnet/templates/dotnet/web-profiles/common/eng/program-kit/web/package.json"
)
WEB_PACKAGE_LOCK = Path(
    ".specify/extensions/program-kit-dotnet/templates/dotnet/web-profiles/common/eng/program-kit/web/package-lock.json"
)
TOOLCHAIN_OVERRIDE_ID = "managed-toolchain-version"
UI_PACKAGE_MANIFEST = Path(
    ".specify/extensions/program-kit-governance/templates/ui-experience/acceptance/package.json"
)
UI_PACKAGE_LOCK = UI_PACKAGE_MANIFEST.with_name("package-lock.json")

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SIGNAL = re.compile(
    r"(^\s*[-*]\s+\*\*|^\s*\*\*[^*]+\*\*\s*:|^\s*\|.*\|\s*$|"
    r"\b(?:Accepted|Proposed|Unresolved|Deferred|Blocked|Ready|Candidate)\b|"
    r"\b(?:ADR|SPC|SPEC|QA|WEB-C|WEB-V)-?[A-Z0-9-]*\b)",
    re.IGNORECASE,
)
class ContextError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContextError(f"Cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContextError(f"Expected a JSON object in {path}")
    return value


def _source_record(project_root: Path, relative: Path) -> dict:
    path = project_root / relative
    if not path.is_file():
        raise ContextError(
            f"Selected Program Kit profile pin source is missing: {relative.as_posix()}"
        )
    return {
        "path": relative.as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def managed_profile_pin_authority(project_root: Path, decisions: dict) -> dict:
    selected = decisions.get("selected_profiles", [])
    if not isinstance(selected, list) or not all(
        isinstance(value, str) and value.strip() for value in selected
    ):
        raise ContextError("Bootstrap selected_profiles must be a list of non-empty strings")
    profiles = {value.strip().casefold() for value in selected}
    pins: dict[str, str] = {}
    sources: list[dict] = []

    if "dotnet" in profiles:
        global_path = project_root / DOTNET_SDK_MANIFEST
        global_json = load_json(global_path)
        sdk = global_json.get("sdk")
        version = sdk.get("version") if isinstance(sdk, dict) else None
        if not isinstance(version, str) or not version.strip():
            raise ContextError(
                f"Managed .NET SDK manifest has no exact sdk.version: {DOTNET_SDK_MANIFEST.as_posix()}"
            )
        pins["dotnet-sdk"] = version.strip()
        source = _source_record(project_root, DOTNET_SDK_MANIFEST)
        source["profile"] = "dotnet"
        source["provides"] = ["dotnet-sdk"]
        source["settings"] = {
            key: sdk[key] for key in ("rollForward", "allowPrerelease") if key in sdk
        }
        sources.append(source)
        node_path = project_root / NODE_VERSION_MANIFEST
        if not node_path.is_file():
            raise ContextError(
                f"Selected Program Kit profile pin source is missing: {NODE_VERSION_MANIFEST.as_posix()}"
            )
        node_version = node_path.read_text(encoding="utf-8").strip().removeprefix("v")
        if not node_version:
            raise ContextError("Managed Node version manifest is empty")
        pins["node"] = node_version
        node_source = _source_record(project_root, NODE_VERSION_MANIFEST)
        node_source["profile"] = "dotnet"
        node_source["provides"] = ["node"]
        sources.append(node_source)

    browser_selected = bool({"typescript-web", "browser-web"} & profiles)
    if "dotnet" in profiles and browser_selected:
        package_json = load_json(project_root / WEB_PACKAGE_MANIFEST)
        dependencies = package_json.get("devDependencies")
        if not isinstance(dependencies, dict) or not dependencies:
            raise ContextError("Managed web package manifest has no devDependencies")
        required_packages = ("typescript", "@types/node", "@playwright/test")
        for package in required_packages:
            version = dependencies.get(package)
            if not isinstance(version, str) or not version.strip():
                raise ContextError(f"Managed web package manifest has no exact {package} pin")
            pins[package] = version.strip()

        lock_json = load_json(project_root / WEB_PACKAGE_LOCK)
        packages = lock_json.get("packages")
        root_package = packages.get("") if isinstance(packages, dict) else None
        locked = root_package.get("devDependencies") if isinstance(root_package, dict) else None
        if not isinstance(locked, dict):
            raise ContextError("Managed web package lock has no root devDependencies")
        mismatches = {
            package: {"manifest": dependencies[package], "lock": locked.get(package)}
            for package in required_packages
            if locked.get(package) != dependencies[package]
        }
        if mismatches:
            raise ContextError(
                f"Managed web package manifest and lock disagree: {mismatches}"
            )
        package_source = _source_record(project_root, WEB_PACKAGE_MANIFEST)
        package_source["profile"] = "dotnet-typescript-web"
        package_source["provides"] = list(required_packages)
        sources.append(package_source)
        lock_source = _source_record(project_root, WEB_PACKAGE_LOCK)
        lock_source["profile"] = "dotnet-typescript-web"
        lock_source["verifies"] = WEB_PACKAGE_MANIFEST.as_posix()
        sources.append(lock_source)

    if "ui-experience-v1" in profiles:
        package = load_json(project_root / UI_PACKAGE_MANIFEST)
        locked = load_json(project_root / UI_PACKAGE_LOCK).get("packages", {}).get("", {})
        if package.get("devDependencies") != locked.get("devDependencies") or package.get("engines") != locked.get("engines"):
            raise ContextError("UI acceptance package/lock graph mismatch")
        selected = {**package["engines"], **package["devDependencies"]}
        for name, value in selected.items():
            if name in pins and pins[name] != value:
                raise ContextError(f"UI acceptance conflicts with managed pin {name}")
            pins[name] = value
        for path in (UI_PACKAGE_MANIFEST, UI_PACKAGE_LOCK):
            record = _source_record(project_root, path)
            record["profile"] = "ui-experience-v1"
            record["provides"] = list(selected)
            sources.append(record)

    return {
        "precedence": "program-kit-managed-profile-before-local-environment-or-current-candidate",
        "selected_profiles": sorted(profiles),
        "pins": dict(sorted(pins.items())),
        "sources": sources,
        "local_environment_policy": (
            "A missing or older local tool is a remediation requirement, not a version-selection "
            "input. Recommend installing or upgrading to the Program Kit pin. Retain a different "
            "local version only through an explicitly approved managed-toolchain-version override."
        ),
    }


def validate_profile_pin_decisions(project_root: Path, run_id: str) -> dict:
    validate_intake(project_root, run_id)
    decisions = load_json(project_root / "docs/architecture/bootstrap-decisions.json")
    authority = managed_profile_pin_authority(project_root, decisions)
    expected = authority["pins"]
    toolchain = decisions.get("toolchain")
    if not expected:
        if toolchain is not None:
            raise ContextError(
                "Bootstrap toolchain authority is present although no selected managed profile supplies pins"
            )
        return authority
    if not isinstance(toolchain, dict) or set(toolchain) != {
        "source",
        "pins",
        "override_reason",
    }:
        raise ContextError(
            "Selected managed profiles require toolchain with exactly source, pins, and override_reason"
        )
    recorded = toolchain.get("pins")
    if not isinstance(recorded, dict) or set(recorded) != set(expected) or not all(
        isinstance(value, str) and value.strip() for value in recorded.values()
    ):
        raise ContextError(
            f"Bootstrap toolchain pins must contain exactly the managed keys: {sorted(expected)}"
        )
    source = toolchain.get("source")
    reason = toolchain.get("override_reason")
    if source == "program-kit-default":
        if recorded != expected:
            raise ContextError(
                "Bootstrap toolchain versions do not match the authoritative Program Kit profile pins; "
                "a local installation or researched current candidate cannot replace them"
            )
        if reason not in ("", None):
            raise ContextError("Program Kit default toolchain pins must not claim an override reason")
    elif source == "override":
        if not isinstance(reason, str) or not reason.strip():
            raise ContextError("A managed toolchain version override requires an explicit reason")
        overrides = decisions.get("overrides", [])
        override_ids = {
            item.get("id") for item in overrides if isinstance(item, dict)
        } if isinstance(overrides, list) else set()
        if TOOLCHAIN_OVERRIDE_ID not in override_ids:
            raise ContextError(
                f"A managed toolchain version override requires the approved {TOOLCHAIN_OVERRIDE_ID!r} override record"
            )
        non_dotnet_differences = {
            key: {"managed": expected[key], "recorded": recorded[key]}
            for key in expected
            if key != "dotnet-sdk" and recorded[key] != expected[key]
        }
        if non_dotnet_differences:
            raise ContextError(
                "The managed-toolchain-version override may retain a user-selected local .NET SDK "
                f"only; other managed pins remain authoritative: {non_dotnet_differences}"
            )
    else:
        raise ContextError(
            "Bootstrap toolchain source must be program-kit-default or an explicit override"
        )
    return authority


def safe_run_directory(project_root: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ContextError("Workflow run ID must contain only letters, digits, '-' or '_'")
    runs_root = (project_root / CONTEXT_DIRECTORY).resolve()
    run_directory = (runs_root / run_id).resolve()
    try:
        run_directory.relative_to(runs_root)
    except ValueError as exc:
        raise ContextError("Workflow run directory escaped the project") from exc
    return run_directory


def _load_intake_module():
    path = Path(__file__).with_name("bootstrap_intake.py")
    spec = importlib.util.spec_from_file_location("program_kit_bootstrap_intake", path)
    if spec is None or spec.loader is None:
        raise ContextError(f"Cannot load bootstrap intake support from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_intake(
    project_root: Path,
    run_id: str,
    allow_architecture_evolution: bool = False,
) -> dict:
    try:
        module = _load_intake_module()
        _, intake = module.intake_from_run(
            project_root,
            run_id,
            allow_architecture_evolution=allow_architecture_evolution,
        )
    except Exception as exc:
        if exc.__class__.__name__ != "IntakeError":
            raise
        raise ContextError(str(exc)) from exc
    return intake


def intake_record(project_root: Path, run_id: str) -> dict:
    path = project_root / INTAKE_PATH
    return {
        "path": INTAKE_PATH.as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def markdown_index(text: str) -> tuple[list[dict], list[dict]]:
    headings: list[dict] = []
    signals: list[dict] = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        match = HEADING.match(line)
        if match and len(headings) < 64:
            headings.append({"line": line_number, "level": len(match.group(1)), "title": match.group(2)})
            continue
        if line and SIGNAL.search(line) and len(signals) < 24:
            signals.append({"line": line_number, "text": line[:320]})
    return headings, signals


def artifact_record(
    project_root: Path, relative_path: str, authority_name: str | None = None
) -> tuple[dict, tuple[str, dict] | None]:
    path = project_root / relative_path
    if not path.is_file():
        raise ContextError(f"Required {relative_path} is missing")
    data = path.read_bytes()
    record: dict = {"path": relative_path, "sha256": sha256_bytes(data), "bytes": len(data)}
    authority: tuple[str, dict] | None = None
    if path.suffix.lower() == ".json":
        payload = load_json(path)
        record["kind"] = "json"
        record["keys"] = sorted(payload)
        authority_name = authority_name or AUTHORITY_JSON.get(relative_path)
        if authority_name:
            authority = authority_name, payload
    else:
        headings, signals = markdown_index(data.decode("utf-8"))
        record.update({"kind": "markdown", "headings": headings, "signals": signals})
    return record, authority


def compact_authority(name: str, payload: dict) -> dict:
    if name == "assessment_decisions":
        keys = (
            "schema_version", "default_profile", "selected_profiles", "dotnet", "web",
            "toolchain", "choices", "overrides", "acknowledgements", "unresolved", "deferred",
        )
        return {key: payload[key] for key in keys if key in payload}
    keys = (
        "schema_version", "status", "constitution", "gate_verdict", "approval_mode",
        "artifacts", "approval_source",
    )
    return {key: payload[key] for key in keys if key in payload}


def replace_governance_path(relative_path: str, paths: dict[str, str]) -> str:
    exact = {
        "docs/architecture/specification-roadmap.md": paths["specification_roadmap"],
        ".specify/memory/constitution.md": paths["constitution_document"],
        ".specify/memory/constitution-ratification.json": paths["constitution_ratification"],
    }
    if relative_path in exact:
        return exact[relative_path]
    default_decisions = "docs/architecture/decisions"
    if relative_path == default_decisions or relative_path.startswith(default_decisions + "/"):
        suffix = relative_path[len(default_decisions) :]
        return paths["decisions"].rstrip("/") + suffix
    return relative_path


def decision_records(project_root: Path, decisions_path: str) -> list[dict]:
    directory = project_root / decisions_path
    if not directory.is_dir():
        return []
    result: list[dict] = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = next((match.group(2) for line in text.splitlines() if (match := HEADING.match(line))), path.stem)
        status_match = re.search(r"(?im)^\s*(?:[-*]\s+)?(?:\*\*)?Status(?:\*\*)?\s*:\s*(.+?)\s*$", text)
        result.append({
            "path": path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(path),
            "title": title,
            "status": status_match.group(1).strip() if status_match else "Unspecified",
        })
    return result


def governance_contract(project_root: Path) -> dict:
    values = {
        "decisions": "docs/architecture/decisions",
        "specification_roadmap": "docs/architecture/specification-roadmap.md",
        "constitution_document": ".specify/memory/constitution.md",
        "constitution_ratification": ".specify/memory/constitution-ratification.json",
    }
    sources: list[dict] = []
    key_map = {
        ("architecture", "decisions"): "decisions",
        ("architecture", "specification_roadmap"): "specification_roadmap",
        ("constitution", "document"): "constitution_document",
        ("constitution", "ratification"): "constitution_ratification",
    }
    for relative in GOVERNANCE_CONFIGS:
        path = project_root / relative
        record: dict = {"path": relative.as_posix(), "exists": path.is_file()}
        if path.is_file():
            record["sha256"] = sha256_file(path)
            section: str | None = None
            for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                line = raw_line.split("#", 1)[0].rstrip()
                if not line:
                    continue
                top = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*):\s*", line)
                nested = re.fullmatch(r"  ([A-Za-z][A-Za-z0-9_-]*):\s*['\"]?([^'\"]+)['\"]?\s*", line)
                if top:
                    section = top.group(1)
                elif nested and section:
                    destination = key_map.get((section, nested.group(1)))
                    if destination:
                        candidate = Path(nested.group(2).strip())
                        if candidate.is_absolute() or ".." in candidate.parts:
                            raise ContextError(
                                f"Unsafe governance path in {relative.as_posix()}:{number}"
                            )
                        values[destination] = candidate.as_posix()
        sources.append(record)
    return {"paths": values, "configuration_sources": sources}


def resolved_output_contract(stage: str, paths: dict[str, str]) -> dict:
    contract = OUTPUT_CONTRACTS[stage]
    write_paths = [replace_governance_path(path, paths) for path in contract["write_paths"]]
    return {
        "write_paths": write_paths,
        "contract_references": list(contract["contract_references"]),
        "validation_commands": list(contract["validation_commands"]),
        "artifact_byte_budgets": {
            replace_governance_path(path, paths): ARTIFACT_BYTE_BUDGETS[path]
            for path in contract["write_paths"]
            if path in ARTIFACT_BYTE_BUDGETS
        },
    }


def context_path(run_directory: Path, stage: str) -> Path:
    return run_directory / "program-kit-context" / f"{stage}.json"


def evidence_path(run_directory: Path, stage: str) -> Path:
    return run_directory / "program-kit-context" / f"{stage}.evidence.json"


def create_documents(project_root: Path, run_id: str, stage: str) -> tuple[Path, dict, Path, dict]:
    run_directory = safe_run_directory(project_root, run_id)
    if not (run_directory / "inputs.json").is_file():
        raise ContextError(f"Spec Kit workflow inputs are missing for run {run_id}")
    intake = validate_intake(
        project_root,
        run_id,
        allow_architecture_evolution=stage in {"tooling", "roadmap", "readiness"},
    )
    architecture_map = load_json(project_root / "docs/architecture/architecture-map.json")
    governance = governance_contract(project_root)
    governance_paths = governance["paths"]
    stage_artifacts = INTAKE_ARTIFACTS + tuple(
        replace_governance_path(path, governance_paths) for path in STAGE_ARTIFACTS[stage]
    )
    artifacts: list[dict] = []
    authorities: dict[str, dict] = {}
    authority_paths = dict(AUTHORITY_JSON)
    authority_paths[governance_paths["constitution_ratification"]] = "constitution_ratification"
    for relative_path in stage_artifacts:
        record, authority = artifact_record(
            project_root, relative_path, authority_paths.get(relative_path)
        )
        artifacts.append(record)
        if authority:
            authorities[authority[0]] = compact_authority(authority[0], authority[1])
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "stage": stage,
        "artifacts": artifacts,
    }
    evidence_destination = evidence_path(run_directory, stage)
    evidence_bytes = (json.dumps(evidence, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "stage": stage,
        "stage_focus": STAGE_FOCUS[stage],
        "bootstrap_intake": intake_record(project_root, run_id),
        "intake": intake,
        "architecture_map": architecture_map,
        "authorities": authorities,
        "managed_profile_pins": managed_profile_pin_authority(
            project_root, authorities.get("assessment_decisions", {})
        ),
        "decisions": decision_records(project_root, governance_paths["decisions"]),
        "governance": governance,
        "output_contract": resolved_output_contract(stage, governance_paths),
        "evidence_index": {
            "path": evidence_destination.relative_to(project_root).as_posix(),
            "sha256": sha256_bytes(evidence_bytes),
            "bytes": len(evidence_bytes),
        },
        "reading_policy": {
            "mode": "deny-by-default",
            "required_full_reads": [
                replace_governance_path(path, governance_paths) for path in STAGE_FULL_READS[stage]
            ],
            "allowed_sources": list(stage_artifacts),
            "rules": [
                "Read this stage brief in full.",
                "Do not print or read the evidence index in full; query one artifact and heading range at a time.",
                "Do not open an allowed source unless this brief lacks a fact required for the current output.",
                "Excluded intake routing surfaces are out of scope unless contradictory evidence is cited.",
                "Report counts and paths after writes; do not print complete generated artifacts or repository-wide diffs.",
            ],
            "provenance": "The evidence index binds optional source sections to paths and SHA-256 values.",
        },
    }
    return context_path(run_directory, stage), payload, evidence_destination, evidence


def build_context(project_root: Path, run_id: str, stage: str) -> tuple[Path, dict]:
    destination, payload, evidence_destination, evidence = create_documents(project_root, run_id, stage)
    destination.parent.mkdir(parents=True, exist_ok=True)
    evidence_destination.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return destination, payload


def validate_context(project_root: Path, run_id: str, stage: str) -> tuple[Path, dict]:
    run_directory = safe_run_directory(project_root, run_id)
    destination = context_path(run_directory, stage)
    evidence_destination = evidence_path(run_directory, stage)
    actual = load_json(destination)
    actual_evidence = load_json(evidence_destination)
    _, expected, _, expected_evidence = create_documents(project_root, run_id, stage)
    if actual != expected or actual_evidence != expected_evidence:
        raise ContextError(f"Bootstrap context is stale or invalid: {destination}")
    return destination, actual


def result_payload(project_root: Path, path: Path, payload: dict) -> dict:
    index = payload["evidence_index"]
    return {
        "path": path.relative_to(project_root).as_posix(),
        "sha256": sha256_file(path),
        "stage": payload["stage"],
        "bytes": path.stat().st_size,
        "evidence_path": index["path"],
        "evidence_bytes": index["bytes"],
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Build compact Program Kit bootstrap stage handoffs.")
    parser.add_argument(
        "command", choices=("build", "validate", "validate-intake", "validate-profile-pins")
    )
    parser.add_argument("--stage", choices=tuple(STAGE_ARTIFACTS))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    try:
        if args.command == "validate-intake":
            payload = validate_intake(project_root, args.run_id)
            result = {
                "path": INTAKE_PATH.as_posix(),
                "bytes": (project_root / INTAKE_PATH).stat().st_size,
                "fact_count": len(payload["facts"]),
                "journey_count": len(payload["journeys"]),
                "capability_count": len(payload["capability_assessments"]),
                "open_item_count": len(payload["open_items"]),
            }
        elif args.command == "validate-profile-pins":
            authority = validate_profile_pin_decisions(project_root, args.run_id)
            result = {
                "selected_profiles": authority["selected_profiles"],
                "pins": authority["pins"],
                "source_count": len(authority["sources"]),
            }
        else:
            if not args.stage:
                raise ContextError(f"--stage is required for {args.command}")
            if args.command == "build":
                path, payload = build_context(project_root, args.run_id, args.stage)
            else:
                path, payload = validate_context(project_root, args.run_id, args.stage)
            result = result_payload(project_root, path, payload)
    except (ContextError, OSError, UnicodeError) as exc:
        print(f"Program Kit bootstrap context failed: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result))
    elif args.command == "validate-intake":
        print(f"Program Kit confirmed bootstrap intake is valid: {result['path']}")
    elif args.command == "validate-profile-pins":
        print(
            "Program Kit selected-profile pins are valid: "
            f"{len(result['pins'])} managed pin(s)"
        )
    else:
        print(f"Program Kit {args.stage} context is valid: {result['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
