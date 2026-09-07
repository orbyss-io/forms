from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PRODUCER_KIND = "ProgramKit.OpenApi.Exporter"
PLANNING_NAMES = ("spec.md", "plan.md", "tasks.md", "research.md", "quickstart.md", "data-model.md")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+-preview\.\d+$")


class ReconciliationError(ValueError):
    pass


def normalize_path(value: str) -> str:
    normalized = value.replace("\\", "/").removeprefix("./")
    if not normalized or normalized.startswith("/") or ".." in Path(normalized).parts:
        raise ReconciliationError(f"PKU110 unsafe registered OpenAPI contract path: {value!r}")
    return normalized


def relative_path(target: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(target.resolve()).as_posix()
    except ValueError as error:
        raise ReconciliationError(f"PKU110 path escapes the consuming repository: {path}") from error


def target_exporter_version(release: Path) -> str:
    path = release / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/.config/dotnet-tools.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        version = value["tools"]["programkit.openapi.exporter"]["version"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ReconciliationError(f"PKU110 cannot read the release exporter pin at {path}: {error}") from error
    if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
        raise ReconciliationError(f"PKU110 release exporter pin is unsupported: {version!r}")
    return version


def registered_contracts(target: Path) -> list[tuple[Path, dict]]:
    registry_path = target / ".program-kit/openapi-contracts.json"
    if not registry_path.is_file():
        return []
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReconciliationError(f"PKU110 cannot read the OpenAPI registry at {registry_path}: {error}") from error
    contracts = registry.get("contracts") if isinstance(registry, dict) else None
    if (
        not isinstance(registry, dict)
        or registry.get("schemaVersion") != 1
        or not isinstance(contracts, list)
    ):
        raise ReconciliationError(f"PKU110 unsupported OpenAPI registry at {registry_path}")
    result: list[tuple[Path, dict]] = []
    seen: set[str] = set()
    for entry in contracts:
        normalized = normalize_path(str(entry))
        if normalized in seen:
            raise ReconciliationError(f"PKU110 duplicate registered OpenAPI contract: {normalized}")
        seen.add(normalized)
        path = (target / normalized).resolve()
        relative_path(target, path)
        try:
            contract = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ReconciliationError(f"PKU110 cannot read registered OpenAPI contract {normalized}: {error}") from error
        if not isinstance(contract, dict):
            raise ReconciliationError(f"PKU110 registered OpenAPI contract is not an object: {normalized}")
        result.append((path, contract))
    return result


def manifest_contract_paths(feature_dir: Path) -> set[str]:
    path = feature_dir / "artifact-ownership.json"
    if not path.is_file():
        return set()
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReconciliationError(f"PKU110 cannot read {path}: {error}") from error
    artifacts = manifest.get("artifacts") if isinstance(manifest, dict) else None
    if not isinstance(artifacts, list):
        raise ReconciliationError(f"PKU110 artifact ownership manifest has no artifacts array: {path}")
    return {
        normalize_path(str(entry["path"]))
        for entry in artifacts
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def feature_identity(feature_dir: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "-", feature_dir.name)


def version_key(value: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)-preview\.(\d+)", value)
    if match is None:
        raise ReconciliationError(f"PKU110 unsupported Program Kit runtime version: {value!r}")
    return tuple(int(part) for part in match.groups())


def discover(target: Path, release: Path) -> dict | None:
    target = target.resolve()
    release = release.resolve()
    target_version = target_exporter_version(release)
    mismatches: list[dict] = []
    old_versions: set[str] = set()
    for path, contract in registered_contracts(target):
        producer = contract.get("producer")
        if not isinstance(producer, dict) or producer.get("kind") != PRODUCER_KIND:
            raise ReconciliationError(
                f"PKU110 registered contract {relative_path(target, path)} does not use {PRODUCER_KIND}; "
                "manual compatibility review is required."
            )
        current = producer.get("version")
        if current == target_version:
            continue
        if not isinstance(current, str) or not VERSION_PATTERN.fullmatch(current):
            raise ReconciliationError(
                f"PKU110 registered contract {relative_path(target, path)} has unsupported producer pin {current!r}; "
                "manual compatibility review is required."
            )
        if version_key(current) >= version_key(target_version):
            raise ReconciliationError(
                f"PKU110 registered contract {relative_path(target, path)} cannot be automatically "
                f"reconciled from {current} to non-newer {target_version}."
            )
        mismatches.append({"path": path, "contract": contract, "fromVersion": current})
        old_versions.add(current)
    if not mismatches:
        return None

    mismatch_paths = {relative_path(target, entry["path"]) for entry in mismatches}
    feature_dirs: list[Path] = []
    planning_paths: list[Path] = []
    review_paths: list[Path] = []
    specs = target / "specs"
    for feature_dir in sorted((path for path in specs.iterdir() if path.is_dir()), key=lambda path: path.name) if specs.is_dir() else []:
        documents = [feature_dir / name for name in PLANNING_NAMES if (feature_dir / name).is_file()]
        document_text = {document: document.read_text(encoding="utf-8") for document in documents}
        owns_contract = bool(manifest_contract_paths(feature_dir) & mismatch_paths)
        references_old_pin = any(
            "exporter" in text.casefold() and any(version in text for version in old_versions)
            for text in document_text.values()
        )
        if not owns_contract and not references_old_pin:
            continue
        feature_dirs.append(feature_dir)
        review_paths.extend(documents)
        planning_paths.extend(
            document
            for document in documents
            if any(version in document_text[document] for version in old_versions)
        )
    if not feature_dirs:
        rendered = ", ".join(sorted(mismatch_paths))
        raise ReconciliationError(
            "PKU110 cannot map stale OpenAPI producer contracts to a feature lifecycle: " + rendered
        )

    active_states: list[str] = []
    for feature_dir in feature_dirs:
        state_path = target / ".program-kit/lifecycle" / f"{feature_identity(feature_dir)}.json"
        if not state_path.is_file():
            continue
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ReconciliationError(f"PKU110 cannot read lifecycle state {state_path}: {error}") from error
        if isinstance(state, dict) and state.get("active"):
            active_states.append(relative_path(target, state_path))
    if active_states:
        raise ReconciliationError(
            "PKU110 OpenAPI producer reconciliation cannot alter planning while a lifecycle is active: "
            + ", ".join(active_states)
        )

    return {
        "targetVersion": target_version,
        "oldVersions": sorted(old_versions),
        "contracts": mismatches,
        "featureDirs": feature_dirs,
        "planningPaths": sorted(set(planning_paths), key=lambda path: relative_path(target, path)),
        "reviewPaths": sorted(set(review_paths), key=lambda path: relative_path(target, path)),
    }


def describe(target: Path, plan: dict) -> str:
    contract_paths = [relative_path(target, entry["path"]) for entry in plan["contracts"]]
    update_paths = contract_paths + [relative_path(target, path) for path in plan["planningPaths"]]
    review_paths = [relative_path(target, path) for path in plan["reviewPaths"]]
    return (
        f"managed exporter will change {', '.join(plan['oldVersions'])} -> {plan['targetVersion']}; "
        f"atomic updates: {', '.join(update_paths)}; lifecycle review: {', '.join(review_paths)}"
    )


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=False, ensure_ascii=False) + "\n").encode("utf-8")


def invalidated_state(target: Path, feature_dir: Path, plan: dict, changed_paths: list[str]) -> tuple[Path, bytes] | None:
    path = target / ".program-kit/lifecycle" / f"{feature_identity(feature_dir)}.json"
    if not path.is_file():
        return None
    state = json.loads(path.read_text(encoding="utf-8"))
    phases = state.get("phases") if isinstance(state, dict) else None
    previous = phases.get("afterTasksAnalysis") if isinstance(phases, dict) else None
    if not isinstance(previous, dict):
        return None
    phases.pop("afterTasksAnalysis")
    invalidations = state.setdefault("invalidations", [])
    if not isinstance(invalidations, list):
        raise ReconciliationError(f"PKU110 lifecycle invalidations are malformed: {path}")
    invalidations.append(
        {
            "phase": "afterTasksAnalysis",
            "reason": "program-kit-openapi-producer-pin-reconciliation",
            "invalidatedAtUtc": utc_now(),
            "fromVersions": plan["oldVersions"],
            "toVersion": plan["targetVersion"],
            "changedPaths": changed_paths,
            "previousReport": previous.get("report"),
            "previousReportSha256": previous.get("reportSha256"),
        }
    )
    return path, json_bytes(state)


def atomic_replace(changes: dict[Path, bytes]) -> None:
    originals = {path: path.read_bytes() for path in changes}
    replaced: list[Path] = []
    temporaries: dict[Path, Path] = {}
    try:
        for path, content in changes.items():
            descriptor, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
            temporary = Path(name)
            temporaries[path] = temporary
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        for path in sorted(changes, key=lambda item: item.as_posix()):
            os.replace(temporaries[path], path)
            replaced.append(path)
    except OSError as error:
        for path in reversed(replaced):
            descriptor, name = tempfile.mkstemp(prefix=path.name + ".rollback.", suffix=".tmp", dir=path.parent)
            rollback = Path(name)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(originals[path])
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(rollback, path)
        raise ReconciliationError(f"PKU110 atomic OpenAPI reconciliation failed and was rolled back: {error}") from error
    finally:
        for temporary in temporaries.values():
            if temporary.exists():
                temporary.unlink()


def apply(target: Path, plan: dict) -> list[str]:
    target = target.resolve()
    changes: dict[Path, bytes] = {}
    changed_paths: list[str] = []
    for entry in plan["contracts"]:
        contract = entry["contract"]
        contract["producer"]["version"] = plan["targetVersion"]
        changes[entry["path"]] = json_bytes(contract)
        changed_paths.append(relative_path(target, entry["path"]))
    for path in plan["planningPaths"]:
        text = path.read_text(encoding="utf-8")
        updated = text
        for old in plan["oldVersions"]:
            updated = updated.replace(old, plan["targetVersion"])
        if updated == text:
            raise ReconciliationError(f"PKU110 planned producer-pin update disappeared before apply: {path}")
        changes[path] = updated.encode("utf-8")
        changed_paths.append(relative_path(target, path))
    changed_paths = sorted(set(changed_paths))
    for feature_dir in plan["featureDirs"]:
        invalidation = invalidated_state(target, feature_dir, plan, changed_paths)
        if invalidation is not None:
            path, content = invalidation
            changes[path] = content
    atomic_replace(changes)
    return sorted(relative_path(target, path) for path in changes)
