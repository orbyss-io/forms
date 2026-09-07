from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


OWNERSHIP = {"managed", "scaffold-once", "consumer-owned", "generated", "evidence"}
CLASSIFICATION = {"public", "internal", "confidential", "restricted", "secret"}
LIFECYCLE = {"source", "generated", "ephemeral", "retained", "replaced", "deployment"}
RUNTIME_PROJECT_ROLES = {"core", "helper", "implementation", "provider", "bridge", "composition", "test"}
ACTIVATABLE_PROJECT_ROLES = {"implementation", "provider", "bridge", "composition"}
CAPABILITY_IMPLEMENTATION_ROLES = {"implementation", "provider", "bridge"}
ALLOWED_ROLE_REFERENCES = {
    "core": {"core"},
    "helper": {"core", "helper"},
    "implementation": {"core", "helper"},
    "provider": {"core", "helper"},
    "bridge": {"core", "helper"},
    "composition": {"core", "helper", "implementation", "provider", "bridge", "composition"},
    "test": RUNTIME_PROJECT_ROLES,
}
LEGACY_PROJECT_MARKERS = {"feature", "domain", "contracts", "application", "infrastructure"}
FORBIDDEN_CORE_PACKAGE_PREFIXES = (
    "cshells",
    "nuplane",
    "microsoft.aspnetcore",
    "microsoft.entityframeworkcore",
    "microsoft.extensions.dependencyinjection",
    "newtonsoft.json",
    "npgsql",
    "microsoft.data.sqlclient",
    "system.text.json",
)
CONVENTIONS = {
    "program-kit": {"spec.md", "plan.md", "tasks.md", "research.md", "data-model.md", "quickstart.md"},
    "dotnet": {"*.sln", "*.slnx", "src/**/*.csproj", "tests/**/*.csproj", "Directory.Build.props", "Directory.Build.targets", "Directory.Packages.props"},
    "typescript-vite": {"vite.config.ts", "src/**/*.ts", "src/**/*.tsx", "tests/**/*.spec.ts"},
}
CANONICAL = {
    ".program-kit/evidence/runtime-closure.json",
    ".program-kit/evidence/host-image.json",
    ".program-kit/evidence/after-tasks-analysis.md",
    "docs/security/security-ledger.md",
    "tests/fixtures/program-kit/local-contract.json",
}
GOVERNANCE_CONTEXT = {
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
EXTERNAL_HOST_REQUIREMENTS = {
    "ProgramKitFeatureIdentity": "feature identity metadata",
    "shells.json": "shell activation",
    "hostsettings.json": "external-host configuration",
    "ProgramKit.Host": "the external Program Kit host",
}


def configure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def normalize(value: str) -> str:
    path = value.replace("\\", "/").removeprefix("./")
    if not path or path.startswith("/") or ".." in PurePosixPath(path).parts:
        raise ValueError(f"PKA001 path must be repository-relative without traversal: {value!r}")
    return path


def load_manifest(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise ValueError(f"PKA002 unsupported artifact ownership manifest: {path}")
    profiles = value.get("profiles")
    artifacts = value.get("artifacts")
    if not isinstance(profiles, list) or not isinstance(artifacts, list):
        raise ValueError("PKA003 manifest profiles and artifacts must be arrays.")
    seen: set[str] = set()
    for entry in artifacts:
        if not isinstance(entry, dict) or ("path" in entry) == ("pattern" in entry):
            raise ValueError("PKA004 each artifact declares exactly one path or pattern.")
        key = normalize(str(entry.get("path", entry.get("pattern"))))
        if key in seen:
            raise ValueError(f"PKA005 duplicate artifact declaration: {key}")
        seen.add(key)
        if entry.get("ownership") not in OWNERSHIP or entry.get("classification") not in CLASSIFICATION or entry.get("lifecycle") not in LIFECYCLE:
            raise ValueError(f"PKA006 invalid ownership/classification/lifecycle for {key}")
    return value


def matches(path: str, manifest: dict) -> dict | None:
    for entry in manifest["artifacts"]:
        if "path" in entry and normalize(entry["path"]) == path:
            return entry
        if "pattern" in entry and fnmatch.fnmatchcase(path, normalize(entry["pattern"])):
            return entry
    for profile in manifest["profiles"]:
        if any(fnmatch.fnmatchcase(path, pattern) for pattern in CONVENTIONS.get(profile, set())):
            return {"ownership": "consumer-owned", "profile": profile}
    return None


def negative_path_reference(line: str, start: int) -> bool:
    prefix = line[max(0, start - 120) : start]
    return re.search(
        r"(?:do\s+not|don't|must\s+not|never|without|instead\s+of|rather\s+than|"
        r"prohibit(?:ed)?|forbid(?:den)?|reject|absence\s+of|no\s+custom)\s+[^.;:]{0,80}$",
        prefix,
        re.IGNORECASE,
    ) is not None


def inline_paths(document: Path) -> list[tuple[int, str, str]]:
    result: list[tuple[int, str, str]] = []
    for line_number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
        for match in re.finditer(r"`([^`]+)`", line):
            token = match.group(1)
            if "://" in token or " " in token or token.startswith("--"):
                continue
            if negative_path_reference(line, match.start()):
                continue
            if "/" in token or re.search(r"\.(?:cs|csproj|json|md|py|ts|tsx|props|targets|yml|yaml)$", token):
                result.append((line_number, normalize(token), line))
    return result


def task_paths(tasks: Path) -> list[tuple[int, str, str]]:
    result: list[tuple[int, str, str]] = []
    for line_number, line in enumerate(tasks.read_text(encoding="utf-8").splitlines(), 1):
        if re.match(r"^\s*-\s*\[[ xX]\]", line) is None:
            continue
        for match in re.finditer(r"`([^`]+)`", line):
            token = match.group(1)
            if "://" in token or " " in token or token.startswith("--"):
                continue
            if negative_path_reference(line, match.start()):
                continue
            if "/" in token or re.search(
                r"\.(?:cs|csproj|json|md|py|ts|tsx|props|targets|yml|yaml)$", token
            ):
                result.append((line_number, normalize(token), line))
    return result


def extension_point(path: str) -> str:
    if path == ".program-kit/eng/Build.ps1":
        return "use consumer-owned Directory.Build.targets or a separate consumer build script"
    if path.startswith(".program-kit/eng/web/"):
        return "import the managed SPA adapter from consumer-owned vite.config and configure exact origins there"
    return "use root Directory.Build.props/targets or a feature-owned adapter after the managed import"


def validate_tasks(tasks: Path, manifest: dict, plan: Path | None) -> None:
    plan_text = plan.read_text(encoding="utf-8") if plan else ""
    errors: list[str] = []
    for line_number, path, line in task_paths(tasks):
        entry = matches(path, manifest)
        if entry is None:
            delta = f"STRUCTURE-DELTA: {path}"
            if delta not in line or delta not in plan_text:
                errors.append(
                    f"PKA007 {tasks}:{line_number} unknown path '{path}'; declare it, use an accepted profile convention, "
                    "or add the same explicit STRUCTURE-DELTA to plan and tasks before completion."
                )
            continue
        if entry.get("ownership") == "managed" and re.search(r"\b(add|create|edit|modify|update|delete|write)\b", line, re.IGNORECASE):
            errors.append(f"PKA008 {tasks}:{line_number} task edits managed path '{path}'; {extension_point(path)}.")
    if errors:
        raise ValueError("\n".join(errors))


def validate_governance_context(feature_dir: Path, include_tasks: bool) -> None:
    names = ("spec.md", "plan.md", "tasks.md") if include_tasks else ("spec.md", "plan.md")
    errors: list[str] = []
    for name in names:
        path = feature_dir / name
        if not path.is_file():
            errors.append(f"PKA010 required governed feature artifact is missing: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in GOVERNANCE_CONTEXT[name] if marker not in text]
        if missing:
            errors.append(
                f"PKA010 {path} is missing mandatory governance context: {', '.join(missing)}"
            )
    if errors:
        raise ValueError("\n".join(errors))


def repository_root(feature_dir: Path) -> Path:
    for candidate in (feature_dir, *feature_dir.parents):
        if (candidate / ".specify").is_dir() or (candidate / "docs/architecture/bootstrap-decisions.json").is_file():
            return candidate
    return feature_dir.parent


def external_program_kit_host_selected(feature_dir: Path, manifest: dict) -> bool:
    if "dotnet" not in {str(value).lower() for value in manifest.get("profiles", [])}:
        return False
    decisions_path = repository_root(feature_dir) / "docs/architecture/bootstrap-decisions.json"
    if not decisions_path.is_file():
        return True
    try:
        decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"PKA011 cannot inspect .NET host authority: {error}") from error
    dotnet = decisions.get("dotnet") if isinstance(decisions, dict) else None
    return not (isinstance(dotnet, dict) and dotnet.get("program_kit_host_opt_out") is True)


def is_custom_host_path(path: str) -> bool:
    normalized = normalize(path)
    lowered = normalized.lower()
    if lowered == "program.cs" or (lowered.startswith("src/") and lowered.endswith("/program.cs")):
        return True
    if not lowered.startswith("src/"):
        return False
    return any(
        segment == "host" or segment.endswith(".host")
        for segment in PurePosixPath(lowered).parts[1:]
    )


def planned_paths(feature_dir: Path, manifest: dict, include_tasks: bool) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for entry in manifest.get("artifacts", []):
        if isinstance(entry, dict):
            value = entry.get("path", entry.get("pattern"))
            if isinstance(value, str):
                result.append(("artifact-ownership.json", normalize(value)))
    names = ["plan.md", "quickstart.md"]
    if include_tasks:
        names.append("tasks.md")
    names.extend(
        path.relative_to(feature_dir).as_posix()
        for path in sorted((feature_dir / "contracts").glob("*.md"))
        if path.is_file()
    )
    for name in names:
        path = feature_dir / name
        if path.is_file():
            references = task_paths(path) if name == "tasks.md" else inline_paths(path)
            result.extend((f"{name}:{line}", value) for line, value, _ in references)
    return result


def validate_runtime_profile(feature_dir: Path, manifest: dict, include_tasks: bool) -> None:
    if not external_program_kit_host_selected(feature_dir, manifest):
        return
    paths = planned_paths(feature_dir, manifest, include_tasks)
    custom = sorted({f"{source} -> {path}" for source, path in paths if is_custom_host_path(path)})
    if custom:
        raise ValueError(
            "PKA011 external ProgramKit.Host profile forbids a repository-owned host project or "
            "Program.cs; create packable feature projects and external-host activation/release inputs instead: "
            + "; ".join(custom)
        )
    documents = [feature_dir / "plan.md", feature_dir / "quickstart.md"]
    if include_tasks:
        documents.append(feature_dir / "tasks.md")
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in documents if path.is_file()
    )
    has_dotnet_project = any(path.lower().endswith(".csproj") for _, path in paths)
    if not has_dotnet_project:
        return
    missing = [label for marker, label in EXTERNAL_HOST_REQUIREMENTS.items() if marker not in combined]
    if not re.search(r"(?:runnable_host\.py\s+stage|package[- ]closure\s+stag)", combined, re.IGNORECASE):
        missing.append("validated package-closure staging")
    if not any(
        marker in combined
        for marker in (".program-kit/evidence/host-image.json", "runnable-host.json", "digest-pinned")
    ):
        missing.append("digest-bound external-host release evidence")
    if missing:
        raise ValueError(
            "PKA012 .NET feature planning is incomplete for the external ProgramKit.Host profile; "
            "missing " + ", ".join(missing) + "."
        )
    validate_runtime_composition(feature_dir, manifest)


def direct_msbuild_references(project: Path, root: Path) -> tuple[set[str], set[str]]:
    try:
        document = ET.parse(project)
    except (ET.ParseError, OSError) as error:
        raise ValueError(f"PKA015 cannot inspect project references in {project}: {error}") from error
    project_references: set[str] = set()
    package_references: set[str] = set()
    for element in document.iter():
        kind = element.tag.rsplit("}", 1)[-1]
        include = element.attrib.get("Include")
        if not include:
            continue
        if kind == "ProjectReference":
            target = (project.parent / include.replace("\\", "/")).resolve()
            try:
                project_references.add(target.relative_to(root.resolve()).as_posix())
            except ValueError as error:
                raise ValueError(
                    f"PKA015 {project} references a project outside the repository: {include}"
                ) from error
        elif kind == "PackageReference":
            package_references.add(include)
    return project_references, package_references


def activated_feature_identities(root: Path) -> set[str]:
    path = root / "shells.json"
    if not path.is_file():
        return set()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        shells = value["CShells"]["Shells"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError(f"PKA015 cannot inspect activated feature identities in {path}: {error}") from error
    if not isinstance(shells, dict):
        raise ValueError(f"PKA015 {path} must use the CShells:Shells object schema")
    identities: set[str] = set()
    for shell in shells.values():
        features = shell.get("Features") if isinstance(shell, dict) else None
        if not isinstance(features, dict):
            raise ValueError(f"PKA015 {path} contains a shell without a Features object")
        identities.update(str(identity) for identity in features)
    return identities


def validate_runtime_composition(feature_dir: Path, manifest: dict) -> None:
    composition = manifest.get("runtimeComposition")
    if not isinstance(composition, dict):
        raise ValueError(
            "PKA015 external-host .NET planning must declare runtimeComposition in "
            "artifact-ownership.json; name the accepted authority, direct project/package graph, "
            "and the activated implementation of every semantic capability binding."
        )
    authorities = composition.get("authorities")
    projects = composition.get("projects")
    bindings = composition.get("bindings")
    core_references = composition.get("coreReferences")
    if (
        not isinstance(authorities, list)
        or not authorities
        or not isinstance(projects, list)
        or not isinstance(bindings, list)
        or not isinstance(core_references, list)
    ):
        raise ValueError(
            "PKA015 runtimeComposition requires non-empty authorities plus projects, bindings, "
            "and coreReferences arrays"
        )

    root = repository_root(feature_dir)
    errors: list[str] = []
    normalized_authorities: set[str] = set()
    for authority in authorities:
        try:
            authority_path = normalize(str(authority))
        except ValueError as error:
            errors.append(str(error).replace("PKA001", "PKA015", 1))
            continue
        if not (root / authority_path).is_file():
            errors.append(f"PKA015 runtime composition authority is missing: {authority_path}")
        normalized_authorities.add(authority_path)

    declared_artifact_projects = {
        normalize(str(entry["path"]))
        for entry in manifest.get("artifacts", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str) and str(entry["path"]).lower().endswith(".csproj")
    }
    declared_projects: dict[str, dict] = {}
    identities: dict[str, str] = {}
    capability_implementation_projects: set[str] = set()
    for project in projects:
        if not isinstance(project, dict):
            errors.append("PKA015 each runtimeComposition project must be an object")
            continue
        try:
            path = normalize(str(project.get("path", "")))
        except ValueError as error:
            errors.append(str(error).replace("PKA001", "PKA015", 1))
            continue
        if path in declared_projects:
            errors.append(f"PKA015 duplicate runtime composition project: {path}")
            continue
        if matches(path, manifest) is None:
            errors.append(f"PKA015 runtime composition project is not owned by the manifest: {path}")
        if project.get("role") not in RUNTIME_PROJECT_ROLES:
            errors.append(f"PKA015 {path} has an invalid runtime composition role: {project.get('role')!r}")
        project_name_parts = {part.lower() for part in Path(path).stem.split(".")}
        legacy_parts = sorted(project_name_parts & LEGACY_PROJECT_MARKERS)
        if legacy_parts:
            errors.append(
                f"PKA015 {path} uses layer-marker project name(s) {legacy_parts}; use a domain-specific "
                ".Core project or name the implementation, provider, protocol, bridge, helper, or composition capability"
            )
        project_refs = project.get("projectReferences")
        package_refs = project.get("packageReferences")
        if not isinstance(project_refs, list) or not isinstance(package_refs, list):
            errors.append(f"PKA015 {path} must declare projectReferences and packageReferences arrays")
            continue
        try:
            expected_project_refs = {normalize(str(value)) for value in project_refs}
        except ValueError as error:
            errors.append(str(error).replace("PKA001", "PKA015", 1))
            continue
        if len(expected_project_refs) != len(project_refs) or len({str(value) for value in package_refs}) != len(package_refs):
            errors.append(f"PKA015 {path} contains duplicate direct references")
        normalized_project = {
            **project,
            "path": path,
            "projectReferences": expected_project_refs,
            "packageReferences": {str(value) for value in package_refs},
        }
        declared_projects[path] = normalized_project
        role = str(project.get("role", ""))
        project_stem = Path(path).stem
        if role == "core" and not project_stem.endswith(".Core"):
            errors.append(f"PKA015 core project {path} must use the domain-specific .Core suffix")
        if role != "core" and project_stem.endswith(".Core"):
            errors.append(f"PKA015 non-core project {path} cannot use the .Core suffix")
        if role == "core":
            for package_reference in normalized_project["packageReferences"]:
                package_id = package_reference.lower()
                if package_id == "programkit.domainevents" or package_id.startswith(FORBIDDEN_CORE_PACKAGE_PREFIXES):
                    errors.append(
                        f"PKA015 Core project {path} references runtime/DI/transport/persistence/serialization "
                        f"package {package_reference}; move that concern to a named implementation/provider "
                        "and keep only deliberately lightweight abstractions in Core"
                    )
        if role in {"provider", "bridge"}:
            capability_implementation_projects.add(path)
        feature_identities = project.get("featureIdentities", [])
        if not isinstance(feature_identities, list):
            errors.append(f"PKA015 {path} featureIdentities must be an array")
            feature_identities = []
        if role in ACTIVATABLE_PROJECT_ROLES and not feature_identities:
            errors.append(f"PKA015 activatable {role} project {path} must declare featureIdentities")
        if role not in ACTIVATABLE_PROJECT_ROLES and feature_identities:
            errors.append(f"PKA015 non-activatable {role} project {path} cannot declare featureIdentities")
        if len({str(value) for value in feature_identities}) != len(feature_identities):
            errors.append(f"PKA015 {path} contains duplicate feature identities")
        for identity in feature_identities:
            identity_value = str(identity)
            if identity_value in identities:
                errors.append(f"PKA015 duplicate ProgramKitFeatureIdentity owner: {identity_value}")
            identities[identity_value] = path

    missing_projects = sorted(declared_artifact_projects - set(declared_projects))
    if missing_projects:
        errors.append(
            "PKA015 runtime composition omits planned project(s): " + ", ".join(missing_projects)
        )

    bound_implementations: set[str] = set()
    activated = activated_feature_identities(root)
    for binding in bindings:
        if not isinstance(binding, dict):
            errors.append("PKA015 each semantic capability binding must be an object")
            continue
        try:
            capability_project = normalize(str(binding.get("capabilityProject", "")))
            implementation_project = normalize(str(binding.get("implementationProject", "")))
        except ValueError as error:
            errors.append(str(error).replace("PKA001", "PKA015", 1))
            continue
        feature_identity = str(binding.get("featureIdentity", ""))
        if capability_project not in declared_projects or implementation_project not in declared_projects:
            errors.append(
                "PKA015 binding projects must all exist in runtimeComposition.projects: "
                f"{capability_project}, {implementation_project}"
            )
        capability = declared_projects.get(capability_project)
        if capability is not None and capability.get("role") != "core":
            errors.append(
                f"PKA015 semantic capability project {capability_project} must be classified core"
            )
        implementation = declared_projects.get(implementation_project)
        if implementation is not None and implementation.get("role") not in CAPABILITY_IMPLEMENTATION_ROLES:
            errors.append(
                f"PKA015 capability implementation {implementation_project} must be classified "
                "implementation, provider, or bridge"
            )
        elif implementation is not None:
            bound_implementations.add(implementation_project)
        if not feature_identity or identities.get(feature_identity) != implementation_project:
            errors.append(
                f"PKA015 binding featureIdentity {feature_identity!r} must be owned by "
                f"implementationProject {implementation_project}"
            )
        if feature_identity and feature_identity not in activated:
            errors.append(
                f"PKA015 semantic capability binding has no activated implementation in shells.json: {feature_identity}"
            )
        if implementation is not None and implementation_project != capability_project and capability_project not in implementation["projectReferences"]:
            errors.append(
                f"PKA015 capability implementation {implementation_project} has no declared direct path "
                f"to capability project {capability_project}"
            )
        if not str(binding.get("capability", "")).strip() or not str(binding.get("implementation", "")).strip() or not str(binding.get("registration", "")).strip():
            errors.append("PKA015 each binding must name its capability, implementation, and registration entry point")

    unbound = sorted(capability_implementation_projects - bound_implementations)
    if unbound:
        errors.append(
            "PKA015 selected provider or bridge project(s) have no explicit activated capability binding: "
            + ", ".join(unbound)
        )

    declared_core_edges: set[tuple[str, str]] = set()
    for core_reference in core_references:
        if not isinstance(core_reference, dict):
            errors.append("PKA015 each direct Core reference decision must be an object")
            continue
        try:
            source = normalize(str(core_reference.get("fromProject", "")))
            target = normalize(str(core_reference.get("toProject", "")))
            decision = normalize(str(core_reference.get("decision", "")))
            verification = normalize(str(core_reference.get("verification", "")))
        except ValueError as error:
            errors.append(str(error).replace("PKA001", "PKA015", 1))
            continue
        edge = (source, target)
        if edge in declared_core_edges:
            errors.append(f"PKA015 duplicate direct Core reference decision: {source} -> {target}")
        declared_core_edges.add(edge)
        source_project = declared_projects.get(source)
        target_project = declared_projects.get(target)
        if source_project is None or target_project is None:
            errors.append(f"PKA015 direct Core reference projects must be declared: {source}, {target}")
            continue
        if source_project.get("role") != "core" or target_project.get("role") != "core":
            errors.append(f"PKA015 direct Core reference decision must connect two core projects: {source} -> {target}")
        if target not in source_project["projectReferences"]:
            errors.append(f"PKA015 direct Core reference decision has no matching ProjectReference: {source} -> {target}")
        if decision not in normalized_authorities:
            errors.append(f"PKA015 direct Core reference decision is not a runtime composition authority: {decision}")
        if matches(verification, manifest) is None:
            errors.append(f"PKA015 direct Core reference verification is not owned by the manifest: {verification}")

    actual_core_edges: set[tuple[str, str]] = set()
    for path, project in declared_projects.items():
        role = str(project.get("role", ""))
        allowed = ALLOWED_ROLE_REFERENCES.get(role, set())
        for reference in project["projectReferences"]:
            target = declared_projects.get(reference)
            if target is None:
                errors.append(f"PKA015 {path} references undeclared runtime composition project {reference}")
                continue
            target_role = str(target.get("role", ""))
            if role == "core" and target_role == "core":
                actual_core_edges.add((path, reference))
            if target_role not in allowed:
                errors.append(
                    f"PKA015 forbidden {role}-to-{target_role} ProjectReference: {path} -> {reference}; "
                    "only composition projects may reference runtime implementations/providers/bridges"
                )

    undecided_core_edges = sorted(actual_core_edges - declared_core_edges)
    stale_core_decisions = sorted(declared_core_edges - actual_core_edges)
    for source, target in undecided_core_edges:
        errors.append(
            f"PKA015 direct Core-to-Core reference requires an accepted subdomain, published-language, "
            f"or shared-kernel decision and architecture-test evidence: {source} -> {target}"
        )
    for source, target in stale_core_decisions:
        errors.append(f"PKA015 stale direct Core reference decision has no graph edge: {source} -> {target}")

    for path, project in declared_projects.items():
        project_path = root / path
        if not project_path.is_file():
            continue
        actual_projects, actual_packages = direct_msbuild_references(project_path, root)
        if actual_projects != project["projectReferences"]:
            errors.append(
                f"PKA015 {path} direct ProjectReference graph differs from its accepted runtimeComposition entry; "
                f"expected {sorted(project['projectReferences'])}, actual {sorted(actual_projects)}"
            )
        if actual_packages != project["packageReferences"]:
            errors.append(
                f"PKA015 {path} direct PackageReference graph differs from its accepted runtimeComposition entry; "
                f"expected {sorted(project['packageReferences'])}, actual {sorted(actual_packages)}"
            )
    if errors:
        raise ValueError("\n".join(errors))


def validate_authorization_ownership(feature_dir: Path, manifest: dict, include_tasks: bool) -> None:
    profiles = {str(value).lower() for value in manifest.get("profiles", [])}
    if "dotnet" not in profiles:
        return
    root = repository_root(feature_dir)
    composition = manifest.get("runtimeComposition")
    projects = composition.get("projects", []) if isinstance(composition, dict) else []
    errors: list[str] = []
    provider_shape = re.compile(
        r"\bIsInRole\s*\(|\bClaimTypes\.Role\b|"
        r"\b(?:FindAll|FindFirst|FindFirstValue|HasClaim)\s*\([^;\n]*(?:roles|realm_access|resource_access)",
        re.IGNORECASE,
    )
    canonical_permission_parser = re.compile(
        r"\b(?:FindAll|FindFirst|FindFirstValue|HasClaim)\s*\([^;\n]*(?:permissions|PermissionClaim)",
        re.IGNORECASE,
    )
    for project in projects:
        if not isinstance(project, dict) or project.get("role") not in ACTIVATABLE_PROJECT_ROLES:
            continue
        try:
            project_path = root / normalize(str(project.get("path", "")))
        except ValueError:
            continue
        source_root = project_path.parent
        if not source_root.is_dir():
            continue
        for source in source_root.rglob("*.cs"):
            relative_parts = source.relative_to(source_root).parts
            if any(part in {"bin", "obj"} for part in relative_parts):
                continue
            text = source.read_text(encoding="utf-8")
            if provider_shape.search(text):
                errors.append(
                    f"PKA016 {source.relative_to(root).as_posix()} parses provider roles/token shapes; "
                    "the selected ProgramKit.Authentication feature must normalize them to canonical permissions"
                )
            if canonical_permission_parser.search(text):
                errors.append(
                    f"PKA016 {source.relative_to(root).as_posix()} reparses canonical permission claims; "
                    "use endpoint metadata such as RequireAuthorization(\"permission:<identity>\") and reserve "
                    "feature-owned handlers for genuine resource/state/effect rules"
                )
    documents = [feature_dir / "spec.md", feature_dir / "plan.md", feature_dir / "quickstart.md"]
    if include_tasks:
        documents.append(feature_dir / "tasks.md")
    combined = "\n".join(path.read_text(encoding="utf-8") for path in documents if path.is_file())
    no_effect_probe = re.search(
        r"(?:bodyless|no[- ]effect|without (?:a )?(?:business )?effect|access probe|permission probe)",
        combined,
        re.IGNORECASE,
    )
    invented_inner_policy = re.search(
        r"(?:AccessPermissionPolicy|inner (?:authorization|permission) policy|"
        r"application[- ]service authorization|parse canonical permission)",
        combined,
        re.IGNORECASE,
    )
    if no_effect_probe and invented_inner_policy:
        errors.append(
            "PKA016 a bodyless/no-effect access probe must use the managed endpoint permission policy only; "
            "do not invent an application service or second claim parser when there is no protected business effect"
        )
    if errors:
        raise ValueError("\n".join(errors))


def validate_npm_graph_evidence(feature_dir: Path, manifest: dict) -> None:
    profiles = {str(value).lower() for value in manifest.get("profiles", [])}
    if not profiles & {"typescript-vite", "typescript-web", "browser-web"}:
        return
    plan = feature_dir / "plan.md"
    if not plan.is_file():
        return
    plan_text = plan.read_text(encoding="utf-8")
    if not re.search(
        r"(?:\bnpm\b|openapi-typescript|devDependencies|dependency graph|client generator)",
        plan_text,
        re.IGNORECASE,
    ):
        return
    evidence_path = repository_root(feature_dir) / ".program-kit/evidence/npm-graph.json"
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            "PKA013 TypeScript/npm planning requires current strict peer-resolution evidence at "
            f"{evidence_path}: {error}"
        ) from error
    if not isinstance(evidence, dict) or evidence.get("satisfied") is not True:
        raise ValueError("PKA013 npm graph evidence does not record a successful strict resolution")
    package_json = Path(str(evidence.get("packageJson", "")))
    if not package_json.is_absolute():
        package_json = repository_root(feature_dir) / package_json
    try:
        package_json.resolve().relative_to(repository_root(feature_dir).resolve())
    except ValueError as error:
        raise ValueError("PKA013 npm candidate manifest must stay inside the repository") from error
    if not package_json.is_file():
        raise ValueError(f"PKA013 npm candidate manifest is missing: {package_json}")
    actual = hashlib.sha256(package_json.read_bytes()).hexdigest()
    if evidence.get("packageJsonSha256") != actual:
        raise ValueError("PKA013 npm graph evidence is stale for its candidate package manifest")


def validate_openapi_pipeline(feature_dir: Path, manifest: dict, include_tasks: bool) -> None:
    profiles = {str(value).lower() for value in manifest.get("profiles", [])}
    if "dotnet" not in profiles or not profiles & {"typescript-vite", "typescript-web", "browser-web"}:
        return
    documents = [feature_dir / "spec.md", feature_dir / "plan.md", feature_dir / "quickstart.md"]
    if include_tasks:
        documents.append(feature_dir / "tasks.md")
    combined = "\n".join(path.read_text(encoding="utf-8") for path in documents if path.is_file())
    if not re.search(r"\bopenapi\b", combined, re.IGNORECASE):
        return
    root = repository_root(feature_dir)
    tool_manifest_path = root / ".program-kit/eng/.config/dotnet-tools.json"
    try:
        tool_manifest = json.loads(tool_manifest_path.read_text(encoding="utf-8"))
        exporter_version = tool_manifest["tools"]["programkit.openapi.exporter"]["version"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError(
            f"PKA014 OpenAPI planning requires the managed exporter tool pin at {tool_manifest_path}: {error}"
        ) from error
    if not isinstance(exporter_version, str) or not exporter_version:
        raise ValueError("PKA014 managed ProgramKit.OpenApi.Exporter version pin is invalid")
    oasdiff_pin_path = root / ".oasdiff-version"
    try:
        oasdiff_version = oasdiff_pin_path.read_text(encoding="utf-8").strip().removeprefix("v")
    except OSError as error:
        raise ValueError(f"PKA014 managed oasdiff pin is missing at {oasdiff_pin_path}: {error}") from error
    if not oasdiff_version:
        raise ValueError("PKA014 managed oasdiff version pin is invalid")
    registry_path = root / ".program-kit/openapi-contracts.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"PKA014 OpenAPI planning requires a valid consumer registry at {registry_path}: {error}"
        ) from error
    contracts = registry.get("contracts") if isinstance(registry, dict) else None
    if not isinstance(registry, dict) or registry.get("schemaVersion") != 1 or not isinstance(contracts, list) or not contracts:
        raise ValueError("PKA014 OpenAPI registry must use schemaVersion 1 and register at least one contract")
    required = {
        "schemaVersion", "identity", "documentName", "shell", "producer", "features",
        "packageClosure", "rawDocument", "artifact", "baseline", "compatibility",
        "generator", "application",
    }
    identities: set[str] = set()
    for contract_value in contracts:
        try:
            contract_path = root / normalize(str(contract_value))
            contract_path.resolve().relative_to(root.resolve())
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(f"PKA014 cannot load registered OpenAPI contract {contract_value!r}: {error}") from error
        if not isinstance(contract, dict) or contract.get("schemaVersion") != 1:
            raise ValueError(f"PKA014 unsupported OpenAPI contract: {contract_path}")
        missing = sorted(required - set(contract))
        if missing:
            raise ValueError(f"PKA014 {contract_path} is missing: {', '.join(missing)}")
        identity = contract.get("identity")
        if not isinstance(identity, str) or not identity or identity in identities:
            raise ValueError(f"PKA014 contract identity must be non-empty and unique: {identity!r}")
        identities.add(identity)
        producer = contract.get("producer")
        if (
            not isinstance(producer, dict)
            or producer.get("kind") != "ProgramKit.OpenApi.Exporter"
            or producer.get("version") != exporter_version
        ):
            raise ValueError(
                "PKA014 OpenAPI plans must select the exact managed ProgramKit.OpenApi.Exporter producer"
            )
        features = contract.get("features")
        if not isinstance(features, list) or not features or any(not isinstance(item, str) or not item for item in features):
            raise ValueError("PKA014 every OpenAPI contract must name its contributing feature identities")
        untraced = sorted(feature for feature in set(features) if feature not in combined)
        if untraced:
            raise ValueError(
                "PKA014 OpenAPI contributing features are not traced in specification/plan/tasks: "
                + ", ".join(untraced)
            )
        package_closure = normalize(str(contract.get("packageClosure", "")))
        if package_closure != "artifacts/runnable-host/packages":
            raise ValueError(
                "PKA014 OpenAPI production must compose the validated artifacts/runnable-host/packages closure"
            )
        for stage_name, output_name in (("generator", "generatedTypes"), ("application", "tsconfig")):
            stage = contract.get(stage_name)
            required_stage = {"directory", "packageJson", "lockFile", "script", output_name}
            if not isinstance(stage, dict) or not required_stage.issubset(stage):
                raise ValueError(
                    f"PKA014 OpenAPI {stage_name} must declare directory, packageJson, lockFile, script, and {output_name}"
                )
            for field in required_stage - {"script"}:
                if not isinstance(stage[field], str) or not stage[field]:
                    raise ValueError(f"PKA014 OpenAPI {stage_name}.{field} must be a repository-relative path")
                normalize(stage[field])
        if normalize(str(contract["generator"]["directory"])) == normalize(str(contract["application"]["directory"])):
            raise ValueError(
                "PKA014 OpenAPI client generation dependencies must be isolated from the application TypeScript graph"
            )
        compatibility = contract.get("compatibility")
        if (
            not isinstance(compatibility, dict)
            or not isinstance(compatibility.get("oasdiffVersion"), str)
            or compatibility.get("oasdiffVersion") != oasdiff_version
            or "approval" not in compatibility
        ):
            raise ValueError(
                f"PKA014 OpenAPI compatibility must use managed oasdiff {oasdiff_version} and an approval artifact"
            )


def main() -> int:
    configure_utf8()
    parser = argparse.ArgumentParser(description="Validate Program Kit artifact ownership and task paths.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--tasks")
    parser.add_argument("--plan")
    args = parser.parse_args()
    try:
        manifest = load_manifest(Path(args.manifest))
        declared = {normalize(str(item.get("path", ""))) for item in manifest["artifacts"] if "path" in item}
        missing = sorted(CANONICAL - declared)
        if missing:
            raise ValueError("PKA009 manifest must predeclare canonical Program Kit artifacts: " + ", ".join(missing))
        feature_dir = Path(args.manifest).resolve().parent
        validate_governance_context(feature_dir, bool(args.tasks))
        validate_runtime_profile(feature_dir, manifest, bool(args.tasks))
        validate_authorization_ownership(feature_dir, manifest, bool(args.tasks))
        validate_npm_graph_evidence(feature_dir, manifest)
        validate_openapi_pipeline(feature_dir, manifest, bool(args.tasks))
        if args.tasks:
            validate_tasks(Path(args.tasks), manifest, Path(args.plan) if args.plan else None)
        print("artifact ownership and task paths are valid")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
