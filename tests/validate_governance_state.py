from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path


def load_validator(root: Path):
    path = root / "extensions/program-kit-governance/scripts/governance_state.py"
    spec = importlib.util.spec_from_file_location("program_kit_governance_state", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_error(module, action, contains: str) -> None:
    try:
        action()
    except module.GovernanceStateError as exc:
        if contains.lower() not in str(exc).lower():
            raise AssertionError(f"Expected error containing {contains!r}, got {exc!r}") from exc
    else:
        raise AssertionError(f"Expected GovernanceStateError containing {contains!r}")


def assert_review_packet(path: Path, stage: str) -> None:
    text = path.read_text(encoding="utf-8")
    if len(text.splitlines()) > 200:
        raise AssertionError(f"{stage} review packet exceeds the workflow gate display limit")
    expected = f"write-review --stage {stage}"
    if expected not in text:
        raise AssertionError(f"{stage} review packet has no rejection recovery command")


def write_installation(project: Path, version: str, *, workflow_version: str | None = None) -> None:
    workflow_version = workflow_version or version
    extension_manifest = project / ".specify/extensions/program-kit-governance/extension.yml"
    extension_manifest.parent.mkdir(parents=True, exist_ok=True)
    extension_manifest.write_text(
        f'schema_version: "1.0"\n\nextension:\n  id: "program-kit-governance"\n  version: "{version}"\n',
        encoding="utf-8",
    )
    dotnet_manifest = project / ".specify/extensions/program-kit-dotnet/extension.yml"
    dotnet_manifest.parent.mkdir(parents=True, exist_ok=True)
    dotnet_manifest.write_text(
        f'schema_version: "1.0"\n\nextension:\n  id: "program-kit-dotnet"\n  version: "{version}"\n',
        encoding="utf-8",
    )
    workflow_manifest = project / ".specify/workflows/program-kit-bootstrap/workflow.yml"
    workflow_manifest.parent.mkdir(parents=True, exist_ok=True)
    workflow_manifest.write_text(
        f'schema_version: "1.0"\n\nworkflow:\n  id: "program-kit-bootstrap"\n  version: "{workflow_version}"\n',
        encoding="utf-8",
    )
    preset_manifest = project / ".specify/presets/program-kit-governance-preset/preset.yml"
    preset_manifest.parent.mkdir(parents=True, exist_ok=True)
    preset_manifest.write_text(
        f'schema_version: "1.0"\n\npreset:\n  id: "program-kit-governance-preset"\n  version: "{version}"\n',
        encoding="utf-8",
    )
    preset_registry = {
        "schema_version": "1.0",
        "presets": {"program-kit-governance-preset": {"version": version}},
    }
    (project / ".specify/presets/.registry").write_text(
        json.dumps(preset_registry), encoding="utf-8"
    )
    registry = {
        "schema_version": "1.0",
        "workflows": {
            "program-kit-bootstrap": {
                "version": workflow_version,
                "source": "catalog",
            }
        },
    }
    registry_path = project / ".specify/workflows/workflow-registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    bundle_records = {
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
                ],
            }
        ],
    }
    records_path = project / ".specify/bundle-records.json"
    records_path.write_text(json.dumps(bundle_records), encoding="utf-8")
    integration = {
        "integration": "codex",
        "default_integration": "codex",
    }
    (project / ".specify/integration.json").write_text(
        json.dumps(integration), encoding="utf-8"
    )


def run_main(module, *arguments: str) -> int:
    original = sys.argv
    try:
        sys.argv = ["governance_state.py", *arguments]
        return module.main()
    finally:
        sys.argv = original


def constitution(
    *,
    placeholder: bool = False,
    pending: bool = True,
    metadata_layout: str = "row",
) -> str:
    principle = "[PRINCIPLE_NAME]" if placeholder else "I. Outcome-Oriented Delivery"
    ratified = "PENDING_RATIFICATION" if pending else "2026-08-25"
    if metadata_layout == "row":
        metadata = (
            f"**Version**: 1.0.0 | **Ratified**: {ratified} | "
            "**Last Amended**: 2026-08-25"
        )
    elif metadata_layout in {"lines", "spaced-lines"}:
        separator = "\n" if metadata_layout == "lines" else "\n\n"
        metadata = separator.join(
            (
                "**Version**: 1.0.0",
                f"**Ratified**: {ratified}",
                "**Last Amended**: 2026-08-25",
            )
        )
    else:
        raise ValueError(f"Unknown constitution metadata layout: {metadata_layout}")
    return f"""# Example Constitution

**Status**: Draft

## Core Principles

### {principle}
Every material change MUST deliver a verified outcome.

## Constraints

Architecture decisions require explicit evidence.

## Workflow

Specifications follow ratified governance and Accepted ADRs.

## Governance

Amendments require human approval and a migration note. Version changes follow semantic versioning.
Compliance is reviewed before each lifecycle gate.

{metadata}
"""


def decisions() -> dict:
    return {
        "schema_version": "1.0",
        "default_profile": {"id": "program-kit-standard", "version": "0.3.1"},
        "selected_profiles": ["dotnet", "typescript-web"],
        "dotnet": {
            "host_runtime": "ProgramKit.Host",
            "host_source": "program-kit-default",
            "program_kit_host_opt_out": False,
            "opt_out_reason": "",
        },
        "web": {
            "secure_profile": "bff-cookie-v1",
            "profile_source": "program-kit-default",
            "browser_ui": True,
            "override_reason": "",
            "threat_model": "program-kit-web-threat-model-v1",
            "security_evidence": "program-kit-web-security-evidence-v1",
        },
        "toolchain": {
            "source": "program-kit-default",
            "pins": {
                "dotnet-sdk": "10.0.202",
                "node": "24.20.0",
                "typescript": "7.0.2",
                "@types/node": "24.13.3",
                "@playwright/test": "1.62.1",
            },
            "override_reason": "",
        },
        "choices": [
            {
                "id": "runtime-host",
                "decision": "Use ProgramKit.Host as the .NET runtime",
                "source": "program-kit-default",
                "rationale": "It is the automatic Program Kit .NET baseline",
                "override": "Record an explicit intake opt-out or superseding ADR",
            },
            {
                "id": "secure-web-profile",
                "decision": "Use bff-cookie-v1 for the authenticated browser boundary",
                "source": "program-kit-default",
                "rationale": "It is the secure Program Kit browser baseline",
                "override": "Record explicit intake or a superseding ADR",
            }
        ],
        "overrides": [],
        "acknowledgements": [
            {
                "id": "program-kit-preview-dependencies",
                "summary": "The managed runtime uses pinned preview packages and sources",
            }
        ],
        "unresolved": [],
        "deferred": [],
    }


def write_assessment(module, project: Path) -> None:
    intake_path = project / module.BOOTSTRAP_INTAKE
    intake_path.parent.mkdir(parents=True, exist_ok=True)
    intake_path.write_text('{"schema_version":"1.0","status":"confirmed"}\n', encoding="utf-8")
    intent_path = project / module.PROJECT_INTENT
    intent_path.write_text("# Confirmed project intent\n", encoding="utf-8")
    for relative in (module.ASSESSMENT, module.DECISION_BACKLOG, module.TOOLING_EVALUATION):
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.stem}\n", encoding="utf-8")
    decision_path = project / module.BOOTSTRAP_DECISIONS
    decision_path.write_text(json.dumps(decisions()), encoding="utf-8")
    module.write_review("assessment")
    assert_review_packet(project / module.ASSESSMENT_REVIEW, "assessment")
    assessment_path = project / module.ASSESSMENT
    assessment_path.write_text("# bootstrap-assessment\n\nRevised after review.\n", encoding="utf-8")
    expect_error(module, lambda: module.accept_assessment("approve"), "review packet is stale")
    module.write_review("assessment")
    assert_review_packet(project / module.ASSESSMENT_REVIEW, "assessment")
    module.accept_assessment("approve")


def write_bootstrap_artifacts(module, project: Path) -> None:
    assessment_approval = json.loads(
        (project / module.ASSESSMENT_APPROVAL).read_text(encoding="utf-8")
    )
    decision_hash = assessment_approval["artifacts"][module.BOOTSTRAP_DECISIONS.as_posix()]
    contents = {
        "docs/architecture/README.md": "# Architecture navigation\n",
        "docs/architecture/architecture.md": (
            "# Architecture\n\nProgramKit.Host is the accepted runtime.\n\n"
            "The browser boundary inherits program-kit-web-threat-model-v1 and "
            "program-kit-web-security-evidence-v1.\n"
        ),
        "docs/architecture/quality-attributes.md": "# Quality attributes\n",
        "docs/architecture/technology-radar.md": "# Technology radar\n\nProgramKit.Host — Accepted\n",
        "docs/architecture/traceability.md": "# Traceability\n",
        "docs/architecture/quality-system.md": "# Quality system\n",
        "docs/architecture/decisions/README.md": "# Decisions\n",
        "docs/architecture/decisions/template.md": (
            "# ADR-TITLE: Decision title\n\n- Status: Proposed\n"
        ),
        "docs/architecture/decisions/bootstrap-baseline.md": (
            "# Bootstrap baseline\n\n- Status: Accepted\n\n"
            f"Profile: program-kit-standard 0.3.1\n\nDecision register: {decision_hash}\n\n"
            "runtime-host: ProgramKit.Host is adopted.\n\n"
            "secure-web-profile: bff-cookie-v1 is adopted.\n\n"
            "Security assurance: program-kit-web-threat-model-v1 and "
            "program-kit-web-security-evidence-v1 are inherited.\n\n"
            "program-kit-preview-dependencies is acknowledged.\n"
        ),
    }
    for relative, text in contents.items():
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def roadmap(required_adrs: str = "None", status: str = "Ready") -> str:
    return f"""# Specification roadmap

### SPEC-001: Deliver first observable outcome

- **User-visible outcome**: A user completes the first governed journey.
- **Scope**: One end-to-end vertical slice.
- **Non-goals**: Broad horizontal infrastructure.
- **Required Accepted ADRs**: {required_adrs}
- **Dependencies**: None
- **Owned public contracts**: First operation contract
- **Owned lifecycle portions**: Request through terminal outcome
- **Owned data**: First module data
- **Quality scenarios**: Authorized completion is observable
- **Verification responsibility**: Feature owner
- **Recommended sequence**: 1
- **Status**: {status}
"""


def placeholder_roadmap() -> str:
    return roadmap().replace("A user completes", "[USER_OUTCOME]")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    module = load_validator(root)
    for status_line in (
        "Status: Accepted",
        "- Status: Accepted",
        "- **Status**: Accepted",
        "- **Status:** Accepted",
    ):
        if not module._has_decision_status(status_line, "Accepted"):
            raise AssertionError(f"Decision status syntax was rejected: {status_line}")
    original = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="program-kit-governance-test-") as directory:
        try:
            project = Path(directory)
            os.chdir(project)

            write_installation(project, "0.3.1", workflow_version="0.3.0")
            expect_error(module, module.validate_installation, "version-incoherent")
            expect_error(module, module.validate_installation, "upgrade_program_kit.py")
            if run_main(module, "begin") != 1:
                raise AssertionError("A mixed-version installation must fail before begin")
            if (project / module.RATIFICATION).exists():
                raise AssertionError("Mixed-version preflight wrote governance state")

            write_installation(project, "0.3.1")
            versions = module.validate_installation()
            if set(versions.values()) != {"0.3.1"}:
                raise AssertionError(f"Unexpected coherent versions: {versions}")
            preset_registry_path = project / module.PRESET_REGISTRY
            preset_registry = json.loads(preset_registry_path.read_text(encoding="utf-8"))
            preset_registry["presets"]["program-kit-governance-preset"]["version"] = "0.3.0"
            preset_registry_path.write_text(json.dumps(preset_registry), encoding="utf-8")
            expect_error(module, module.validate_installation, "preset registry=0.3.0")
            preset_registry["presets"]["program-kit-governance-preset"]["version"] = "0.3.1"
            preset_registry_path.write_text(json.dumps(preset_registry), encoding="utf-8")
            records_path = project / module.BUNDLE_RECORDS
            bundle_records = json.loads(records_path.read_text(encoding="utf-8"))
            bundle_records["bundles"][0]["version"] = "0.3.2"
            records_path.write_text(json.dumps(bundle_records), encoding="utf-8")
            expect_error(module, module.validate_installation, "bundle record=0.3.2")
            bundle_records["bundles"][0]["version"] = "0.3.1"
            records_path.write_text(json.dumps(bundle_records), encoding="utf-8")
            managed = project / module.MANAGED_BASELINE
            managed.parent.mkdir(parents=True, exist_ok=True)
            managed.write_text(
                json.dumps({"schemaVersion": 1, "programKitVersion": "0.3.0"}),
                encoding="utf-8",
            )
            expect_error(module, module.validate_installation, "managed .NET baseline=0.3.0")
            managed.write_text(
                json.dumps({"schemaVersion": 1, "programKitVersion": "0.3.1"}),
                encoding="utf-8",
            )
            versions = module.validate_installation()
            if versions.get("managed .NET baseline") != "0.3.1":
                raise AssertionError("Managed baseline version was not included in coherence validation")

            expect_error(module, module.validate_ratification, "governance state file")

            bootstrap_decisions = project / module.BOOTSTRAP_DECISIONS
            bootstrap_decisions.parent.mkdir(parents=True, exist_ok=True)
            alternate_without_opt_out = decisions()
            alternate_without_opt_out["dotnet"]["host_runtime"] = "Custom.Host"
            bootstrap_decisions.write_text(
                json.dumps(alternate_without_opt_out), encoding="utf-8"
            )
            expect_error(
                module,
                module.validate_bootstrap_decisions,
                "automatic .NET default",
            )
            explicit_opt_out = decisions()
            explicit_opt_out["dotnet"] = {
                "host_runtime": "Custom.Host",
                "host_source": "override",
                "program_kit_host_opt_out": True,
                "opt_out_reason": "The initial design mandates an existing proprietary host",
            }
            module_choice = explicit_opt_out["choices"][0]
            module_choice["decision"] = "Use the intake-mandated Custom.Host runtime"
            module_choice["source"] = "override"
            bootstrap_decisions.write_text(json.dumps(explicit_opt_out), encoding="utf-8")
            module.validate_bootstrap_decisions()

            acknowledgement_with_extra_field = decisions()
            acknowledgement_with_extra_field["acknowledgements"][0]["risk"] = "Extra prose"
            bootstrap_decisions.write_text(
                json.dumps(acknowledgement_with_extra_field), encoding="utf-8"
            )
            expect_error(
                module,
                module.validate_bootstrap_decisions,
                "unexpected fields",
            )

            missing_assurance = decisions()
            del missing_assurance["web"]["security_evidence"]
            bootstrap_decisions.write_text(json.dumps(missing_assurance), encoding="utf-8")
            expect_error(
                module,
                module.validate_bootstrap_decisions,
                "web.security_evidence",
            )

            missing_toolchain_override = decisions()
            missing_toolchain_override["toolchain"]["source"] = "override"
            missing_toolchain_override["toolchain"]["override_reason"] = (
                "Retain the explicitly selected local SDK"
            )
            bootstrap_decisions.write_text(
                json.dumps(missing_toolchain_override), encoding="utf-8"
            )
            expect_error(
                module,
                module.validate_bootstrap_decisions,
                "managed-toolchain-version",
            )

            explicit_toolchain_override = decisions()
            explicit_toolchain_override["toolchain"]["source"] = "override"
            explicit_toolchain_override["toolchain"]["pins"]["dotnet-sdk"] = "9.0.100"
            explicit_toolchain_override["toolchain"]["override_reason"] = (
                "The user explicitly retained the locally installed SDK"
            )
            explicit_toolchain_override["overrides"].append(
                {
                    "id": "managed-toolchain-version",
                    "decision": "Retain .NET SDK 9.0.100 instead of the Program Kit pin",
                }
            )
            bootstrap_decisions.write_text(
                json.dumps(explicit_toolchain_override), encoding="utf-8"
            )
            module.validate_bootstrap_decisions()

            write_assessment(module, project)
            assessment_record = json.loads(
                (project / module.ASSESSMENT_APPROVAL).read_text(encoding="utf-8")
            )
            if assessment_record.get("approval_mode") != "interactive":
                raise AssertionError("Interactive assessment approval was not recorded")

            immutable_decisions = bootstrap_decisions.read_bytes()
            write_installation(project, "0.3.2")
            managed.write_text(
                json.dumps({"schemaVersion": 1, "programKitVersion": "0.3.2"}),
                encoding="utf-8",
            )
            expect_error(
                module,
                module.validate_bootstrap_decisions,
                "no Accepted Program Kit upgrade evidence",
            )
            module.record_program_kit_upgrade("0.3.1", "0.3.2")
            if bootstrap_decisions.read_bytes() != immutable_decisions:
                raise AssertionError("Governed upgrade rewrote the hash-bound bootstrap decisions")
            module.validate_bootstrap_decisions()
            upgrade_path = project / module.PROGRAM_KIT_UPGRADES
            upgrade_state = json.loads(upgrade_path.read_text(encoding="utf-8"))
            record = upgrade_state["upgrades"][-1]
            if (
                record.get("baseline_profile_version") != "0.3.1"
                or record.get("previous_installed_version") != "0.3.1"
                or record.get("installed_version") != "0.3.2"
                or record.get("status") != "Accepted"
            ):
                raise AssertionError(f"Unexpected governed upgrade record: {record}")
            record["installed_version"] = "0.3.3"
            upgrade_path.write_text(json.dumps(upgrade_state), encoding="utf-8")
            expect_error(
                module,
                module.validate_bootstrap_decisions,
                "without Accepted upgrade evidence",
            )
            record["installed_version"] = "0.3.2"
            upgrade_path.write_text(json.dumps(upgrade_state), encoding="utf-8")

            constitution_path = project / module.CONSTITUTION
            constitution_path.parent.mkdir(parents=True)
            constitution_path.write_text(constitution(placeholder=True), encoding="utf-8")
            module.begin()
            expect_error(module, module.validate_ratification, "completed ratification")
            expect_error(module, module.validate_constitution_draft, "template placeholders")
            expect_error(
                module,
                lambda: module.write_review("constitution"),
                "template placeholders",
            )
            if (project / module.CONSTITUTION_REVIEW).exists():
                raise AssertionError("Constitution gate packet appeared before a valid draft")

            constitution_path.write_text(
                constitution(metadata_layout="lines"), encoding="utf-8"
            )
            module.validate_constitution_draft()
            constitution_path.write_text(
                constitution(metadata_layout="spaced-lines"), encoding="utf-8"
            )
            module.validate_constitution_draft()
            constitution_path.write_text(constitution(), encoding="utf-8")
            module.validate_constitution_draft()
            module.write_review("constitution")
            assert_review_packet(project / module.CONSTITUTION_REVIEW, "constitution")
            reviewed_constitution = constitution_path.read_bytes()
            expected_final_constitution = reviewed_constitution.replace(
                b"**Status**: Draft", b"**Status**: Ratified", 1
            ).replace(
                b"**Ratified**: PENDING_RATIFICATION",
                f"**Ratified**: {module.date.today().isoformat()}".encode("utf-8"),
                1,
            )
            expect_error(
                module,
                lambda: module.ratify("approve"),
                "verdict 'ratify'",
            )
            if "**Status**: Draft" not in constitution_path.read_text(encoding="utf-8"):
                raise AssertionError("A non-ratify verdict changed the constitution draft")
            module.ratify("ratify", "automatic")
            if constitution_path.read_bytes() != expected_final_constitution:
                raise AssertionError(
                    "Ratification changed reviewed constitution bytes outside the two permitted substitutions"
                )
            module.validate_ratification()
            ratification_record = json.loads(
                (project / module.RATIFICATION).read_text(encoding="utf-8")
            )
            if ratification_record.get("approval_mode") != "automatic":
                raise AssertionError("Automatic constitution ratification was not recorded")
            finalization = ratification_record.get("finalization", {})
            if (
                finalization.get("reviewed_sha256") != module.hashlib.sha256(reviewed_constitution).hexdigest()
                or finalization.get("expected_final_sha256")
                != module.hashlib.sha256(expected_final_constitution).hexdigest()
            ):
                raise AssertionError("Ratification evidence did not bind the reviewed and expected final bytes")
            module.begin()
            recovery_state = json.loads(
                (project / module.RATIFICATION).read_text(encoding="utf-8")
            )
            if recovery_state.get("previous_ratification") != ratification_record:
                raise AssertionError("Recovery draft did not preserve prior ratification evidence")
            if constitution_path.read_bytes() != expected_final_constitution:
                raise AssertionError("Beginning recovery unexpectedly changed constitution bytes")
            (project / module.RATIFICATION).write_text(
                json.dumps(ratification_record), encoding="utf-8"
            )
            ratification_record["approval_mode"] = "unknown"
            (project / module.RATIFICATION).write_text(
                json.dumps(ratification_record), encoding="utf-8"
            )
            expect_error(module, module.validate_ratification, "invalid approval mode")
            ratification_record["approval_mode"] = "automatic"
            (project / module.RATIFICATION).write_text(
                json.dumps(ratification_record), encoding="utf-8"
            )
            finalized = constitution_path.read_text(encoding="utf-8")
            if "**Status**: Ratified" not in finalized or "PENDING_RATIFICATION" in finalized:
                raise AssertionError("Ratification did not finalize status and pending date")

            expect_error(module, lambda: module.validate_roadmap(True), "roadmap is missing")
            roadmap_path = project / module.ROADMAP
            roadmap_path.parent.mkdir(parents=True, exist_ok=True)
            roadmap_path.write_text(placeholder_roadmap(), encoding="utf-8")
            expect_error(module, lambda: module.validate_roadmap(True), "template placeholders")
            roadmap_path.write_text(roadmap("ADR-0042"), encoding="utf-8")
            expect_error(module, lambda: module.validate_roadmap(True), "unresolved ADRs")

            hidden_gate = roadmap().replace(
                "- **Dependencies**: None",
                "- **Dependencies**: Before implementation, proposed test tooling requires an Accepted tooling ADR.",
            )
            roadmap_path.write_text(hidden_gate, encoding="utf-8")
            expect_error(
                module,
                lambda: module.validate_roadmap(True),
                "hides an unresolved implementation decision",
            )

            decision = project / module.DECISIONS / "0042-first-boundary.md"
            decision.parent.mkdir(parents=True)
            decision.write_text("# ADR-0042\n\n- Status: Accepted\n", encoding="utf-8")
            roadmap_path.write_text(roadmap("ADR-0042"), encoding="utf-8")
            module.validate_roadmap(True)

            write_bootstrap_artifacts(module, project)
            baseline_path = project / "docs/architecture/decisions/bootstrap-baseline.md"
            baseline_text = baseline_path.read_text(encoding="utf-8")
            approval = json.loads(
                (project / module.ASSESSMENT_APPROVAL).read_text(encoding="utf-8")
            )
            approved_hash = approval["artifacts"][module.BOOTSTRAP_DECISIONS.as_posix()]
            baseline_path.write_text(
                baseline_text.replace(approved_hash, "0" * 64), encoding="utf-8"
            )
            expect_error(
                module,
                lambda: module.validate_bootstrap(False, True),
                "exact approved decision-register hash",
            )
            baseline_path.write_text(baseline_text, encoding="utf-8")
            architecture_path = project / module.ARCHITECTURE
            traceability_path = project / module.TRACEABILITY
            architecture_path.write_text(
                architecture_path.read_text(encoding="utf-8")
                + "\n| Slice | Status |\n| --- | --- |\n| SPEC-001 | Candidate |\n",
                encoding="utf-8",
            )
            traceability_path.write_text(
                traceability_path.read_text(encoding="utf-8")
                + "\nSPEC-001: no roadmap record exists; Created later by roadmap.\n",
                encoding="utf-8",
            )
            module.synchronize_roadmap_views()
            expect_error(
                module,
                module.validate_bootstrap_consistency,
                "duplicates authoritative status",
            )
            architecture_path.write_text(
                "# Architecture\n\nProgramKit.Host is the accepted runtime.\n\n"
                "The browser boundary inherits program-kit-web-threat-model-v1 and "
                "program-kit-web-security-evidence-v1.\n",
                encoding="utf-8",
            )
            traceability_path.write_text("# Traceability\n", encoding="utf-8")
            module.synchronize_roadmap_views()
            module.validate_bootstrap_consistency()
            module.validate_bootstrap(False, True)
            module.write_review("bootstrap")
            assert_review_packet(project / module.BOOTSTRAP_REVIEW, "bootstrap")
            review_text = (project / module.BOOTSTRAP_REVIEW).read_text(encoding="utf-8")
            if "- Accepted ADRs: 2" not in review_text:
                raise AssertionError("Bootstrap review did not count actual Accepted ADRs")
            if "- Proposed ADRs requiring separate later decisions: 0" not in review_text:
                raise AssertionError("Bootstrap review counted the ADR template as a decision")
            module.accept_bootstrap("approve", "automatic")
            bootstrap_approval = json.loads(
                (project / module.BOOTSTRAP_APPROVAL).read_text(encoding="utf-8")
            )
            if bootstrap_approval.get("approval_mode") != "automatic":
                raise AssertionError("Automatic bootstrap approval was not recorded")
            readiness = project / module.READINESS_REPORT
            readiness.write_text("**Status**: READY\n\n# Readiness\n", encoding="utf-8")
            module.complete_bootstrap()
            module.validate_completion()
            completion = json.loads((project / module.BOOTSTRAP_COMPLETION).read_text(encoding="utf-8"))
            if completion.get("status") != "Completed":
                raise AssertionError("Bootstrap completion evidence was not written")

            roadmap_path.write_text(roadmap("ADR-0042", status="Active"), encoding="utf-8")
            module.synchronize_roadmap_views()
            expect_error(
                module,
                lambda: module.validate_bootstrap(True, False),
                "changed after human approval",
            )
            module.validate_roadmap(False)
            expect_error(module, lambda: module.validate_roadmap(True), "no Ready entry")

            constitution_path.write_text(finalized + "\nAmended after gate.\n", encoding="utf-8")
            expect_error(module, module.validate_ratification, "changed after ratification")

            configuration = project / ".specify/extensions/program-kit-governance/program-kit-governance-config.yml"
            configuration.parent.mkdir(parents=True, exist_ok=True)
            configuration.write_text(
                "architecture:\n"
                "  decisions: governance/decisions\n"
                "  specification_roadmap: governance/roadmap.md\n"
                "constitution:\n"
                "  document: governance/constitution.md\n"
                "  ratification: governance/ratification.json\n",
                encoding="utf-8",
            )
            module.configure_paths()
            if module.CONSTITUTION != Path("governance/constitution.md"):
                raise AssertionError("Installed governance configuration did not set constitution path")
            local_configuration = configuration.with_name("program-kit-governance-config.local.yml")
            local_configuration.write_text(
                "architecture:\n  specification_roadmap: local/roadmap.md\n",
                encoding="utf-8",
            )
            module.configure_paths()
            if module.ROADMAP != Path("local/roadmap.md"):
                raise AssertionError("Local governance configuration must override installed configuration")
            configured_artifacts = module.bootstrap_artifacts()
            if Path("local/roadmap.md") not in configured_artifacts:
                raise AssertionError("Bootstrap validation did not adopt the configured roadmap path")
            if Path("governance/decisions/bootstrap-baseline.md") not in configured_artifacts:
                raise AssertionError("Bootstrap validation did not adopt the configured decisions path")
        finally:
            os.chdir(original)

    print("Governance-state negative and positive contract tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
