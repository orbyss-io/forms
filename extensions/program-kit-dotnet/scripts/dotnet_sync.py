from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

import reconciliation
import identity_fixture
import spa_profile


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def extension_version(extension_root: Path) -> str:
    content = (extension_root / "extension.yml").read_text(encoding="utf-8")
    match = re.search(r'^\s*version:\s*"([^"]+)"\s*$', content, re.MULTILINE)
    if match is None:
        raise ValueError("Could not read the Program Kit extension version.")
    return match.group(1)


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def canonical_json_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def remove_authenticated_json_value(document: object, operation: dict, migration_id: str) -> bool:
    pointer = operation.get("pointer")
    expected_hashes = operation.get("expectedValueHashes")
    if (
        not isinstance(pointer, str)
        or not pointer.startswith("/")
        or not isinstance(expected_hashes, list)
        or not all(isinstance(value, str) for value in expected_hashes)
    ):
        raise ValueError(f"migration {migration_id} has an invalid JSON removal")
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]
    parent = document
    for part in parts[:-1]:
        if not isinstance(parent, dict) or part not in parent:
            return False
        parent = parent[part]
    leaf = parts[-1]
    if not isinstance(parent, dict) or leaf not in parent:
        return False
    actual_hash = canonical_json_hash(parent[leaf])
    if actual_hash not in expected_hashes:
        raise ValueError(
            f"migration {migration_id} preserved {pointer}: value hash {actual_hash} is not an "
            "authenticated Program Kit baseline; migrate its settings explicitly before removal"
        )
    del parent[leaf]
    return True


def apply_structured_migrations(
    relative: str,
    content: bytes,
    migrations: list[dict],
) -> bytes:
    matching = [
        (migration, transform)
        for migration in migrations
        for transform in migration.get("jsonTransforms", [])
        if isinstance(transform, dict) and transform.get("path") == relative
    ]
    if not matching:
        return content
    document = json.loads(content.decode("utf-8"))
    changed = False
    for migration, transform in matching:
        removals = transform.get("remove")
        if not isinstance(removals, list):
            raise ValueError(f"migration {migration['id']} has no JSON removal list")
        for operation in removals:
            if not isinstance(operation, dict):
                raise ValueError(f"migration {migration['id']} has an invalid JSON removal")
            changed = remove_authenticated_json_value(document, operation, migration["id"]) or changed
    return (json.dumps(document, indent=2) + "\n").encode("utf-8") if changed else content


def consumer_nuget_routing_error(path: Path) -> str | None:
    """Validate the protected routes while allowing consumer-owned feed extensions."""
    try:
        root = ElementTree.parse(path).getroot()
    except (ElementTree.ParseError, OSError) as exc:
        return f"cannot parse consumer-owned NuGet configuration: {exc}"

    sources = {
        source.attrib.get("key", ""): source.attrib.get("value", "")
        for source in root.findall("./packageSources/add")
    }
    required_sources = {
        "nuget.org": "https://api.nuget.org/v3/index.json",
        "CShells Preview": "https://f.feedz.io/valence-works/cshells/nuget/index.json",
        "Nuplane Preview": "https://f.feedz.io/valence-works/nuplane/nuget/index.json",
    }
    for source, url in required_sources.items():
        if sources.get(source) != url:
            return f"{source} must retain its approved package-source URL"

    mappings = {
        source.attrib.get("key", ""): {
            package.attrib.get("pattern", "") for package in source.findall("package")
        }
        for source in root.findall("./packageSourceMapping/packageSource")
    }
    expected = {
        "CShells Preview": {"CShells", "CShells.*"},
        "Nuplane Preview": {"Nuplane", "Nuplane.*"},
    }
    if "*" not in mappings.get("nuget.org", set()):
        return "nuget.org must retain the default '*' public-package route"
    for source, patterns in expected.items():
        if mappings.get(source) != patterns:
            return f"{source} must retain only the protected patterns {sorted(patterns)}"
    for source, patterns in mappings.items():
        if source != "nuget.org" and "*" in patterns:
            return f"{source} must use namespace-specific patterns rather than a second '*' route"
        protected = {"CShells", "CShells.*", "Nuplane", "Nuplane.*"}
        if source not in expected and patterns.intersection(protected):
            return f"{source} must not duplicate a protected CShells or Nuplane route"
    return None


def selected_web_profile(target: Path, requested: str) -> str:
    """Resolve an explicit profile or derive the secure default from reviewed bootstrap evidence."""
    if requested != "auto":
        return requested

    decision_path = target / "docs" / "architecture" / "bootstrap-decisions.json"
    if decision_path.is_file():
        decisions = load_json(decision_path, {})
        web = decisions.get("web")
        if isinstance(web, dict):
            selected = web.get("secure_profile")
            approved_profiles = {
                "none-v1": "none",
                "bff-cookie-v1": "bff-cookie",
                "spa-pkce-v1": "spa-pkce",
            }
            if selected in approved_profiles:
                return approved_profiles[selected]

    evidence_paths = [
        target / "docs" / "initial-design.md",
        target / "INITIAL_DESIGN.md",
        target / "initial_design.md",
    ]
    evidence = "\n".join(
        path.read_text(encoding="utf-8").lower() for path in evidence_paths if path.is_file()
    )
    browser_markers = ("browser", "react", "single-page", "single page", "spa", "typescript")
    return "bff-cookie" if any(marker in evidence for marker in browser_markers) else "none"


def selected_dotnet_sdk(target: Path, managed_global_json: Path) -> tuple[str, str]:
    """Return the governed SDK version and its authority source."""
    managed = load_json(managed_global_json, {})
    managed_version = managed.get("sdk", {}).get("version")
    if not isinstance(managed_version, str) or not managed_version.strip():
        raise ValueError("The Program Kit managed global.json has no exact SDK version.")

    decision_path = target / "docs" / "architecture" / "bootstrap-decisions.json"
    if not decision_path.is_file():
        return managed_version, "program-kit-default"
    decisions = load_json(decision_path, {})
    toolchain = decisions.get("toolchain")
    if not isinstance(toolchain, dict) or toolchain.get("source") != "override":
        return managed_version, "program-kit-default"
    reason = toolchain.get("override_reason")
    pins = toolchain.get("pins")
    overrides = decisions.get("overrides")
    override_ids = {
        item.get("id") for item in overrides if isinstance(item, dict)
    } if isinstance(overrides, list) else set()
    selected = pins.get("dotnet-sdk") if isinstance(pins, dict) else None
    if (
        not isinstance(reason, str)
        or not reason.strip()
        or "managed-toolchain-version" not in override_ids
        or not isinstance(selected, str)
        or not selected.strip()
    ):
        raise ValueError(
            "The .NET SDK override is incomplete; record a non-empty reason, an exact dotnet-sdk "
            "pin, and the managed-toolchain-version override decision."
        )
    return selected.strip(), "override"


def desired_content(
    source: Path,
    relative: str,
    dotnet_sdk: str,
    web_profile: str,
    spa_configuration: dict | None,
    template_root: Path,
) -> bytes:
    content = source.read_bytes()
    if relative == "global.json":
        value = load_json(source, {})
        sdk = value.get("sdk")
        if not isinstance(sdk, dict):
            raise ValueError("The Program Kit managed global.json has no sdk object.")
        sdk["version"] = dotnet_sdk
        return (json.dumps(value, indent=2) + "\n").encode("utf-8")
    if relative == identity_fixture.REALM_PATH and web_profile in {"bff-cookie", "spa-pkce"}:
        return identity_fixture.render_realm(
            content, template_root, web_profile, spa_configuration
        )
    if web_profile != "spa-pkce" or spa_configuration is None:
        return content
    renderers = {
        ".program-kit/web-profile.shells.json": spa_profile.render_shell_profile,
        ".program-kit/web-profile.json": spa_profile.render_profile,
        ".program-kit/eng/web/web-contract.json": spa_profile.render_web_contract,
    }
    renderer = renderers.get(relative)
    return renderer(content, spa_configuration) if renderer else content


def version_key(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    if match is None:
        raise ValueError(f"Unsupported Program Kit version: {value}")
    return tuple(int(part) for part in match.groups())


def lifecycle_for(relative: str, ownership: str, rendered: bool) -> str:
    if rendered:
        return "derived"
    if relative.startswith(".program-kit/security/") or "threat-model" in relative:
        return "evidence"
    return ownership


def recorded_consumer_hash(previous: object, fallback: str) -> str:
    if isinstance(previous, dict):
        for name in ("installedHash", "baselineHash", "templateHash"):
            value = previous.get(name)
            if isinstance(value, str):
                return value
    return fallback


def profile_paths(template_root: Path, profile: object) -> set[str]:
    if not isinstance(profile, str):
        return set()
    manifest_path = template_root / "web-profiles" / profile / "managed-files.json"
    if not manifest_path.is_file():
        return set()
    entries = load_json(manifest_path, {}).get("files")
    if not isinstance(entries, list):
        raise ValueError(f"The {profile} profile manifest has no files list.")
    return {entry["path"] for entry in entries}


def stable_plan_digest(value: dict) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def prune_retired_program_kit_directories(target: Path) -> list[str]:
    """Remove only empty directories from the retired eng/program-kit tree."""
    legacy_root = target / "eng" / "program-kit"
    if not legacy_root.is_dir():
        return []
    candidates = sorted(
        (path for path in legacy_root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    candidates.extend((legacy_root, legacy_root.parent))
    removed: list[str] = []
    for path in candidates:
        try:
            path.rmdir()
        except OSError:
            continue
        removed.append(path.relative_to(target).as_posix())
    return removed


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Synchronize the Program Kit .NET repository baseline.")
    parser.add_argument("--target", default=".", help="Consuming repository root")
    parser.add_argument("--check", action="store_true", help="Preview drift without writing")
    parser.add_argument("--json", action="store_true", help="Emit the reconciliation plan as JSON")
    parser.add_argument("--plan-digest", help="Apply only when the recomputed plan has this SHA-256 digest")
    parser.add_argument("--recover", action="store_true", help="Roll back an interrupted reconciliation before planning")
    parser.add_argument(
        "--web-profile",
        choices=("auto", "none", "bff-cookie", "spa-pkce"),
        default="auto",
        help="Secure web boundary profile; auto adopts BFF for a detected browser UI",
    )
    parser.add_argument(
        "--profile-selected",
        action="store_true",
        help="Confirms that the consuming repository accepted the .NET technology profile",
    )
    parser.add_argument(
        "--host-runtime-accepted",
        action="store_true",
        help="Confirms that the approved bootstrap baseline or a later Accepted override selects ProgramKit.Host",
    )
    parser.add_argument(
        "--preview-sources-approved",
        action="store_true",
        help="Confirms explicit approval to add the Program Kit preview packages and NuGet sources",
    )
    parser.add_argument(
        "--persistence-profile",
        choices=("none", "ef-postgresql", "ef-sqlserver", "ef-sqlite"),
        default="none",
        help="Explicit governed persistence profile; none keeps all providers inactive",
    )
    args = parser.parse_args()

    if not args.profile_selected:
        print("Refusing to scaffold: the .NET technology profile was not explicitly selected.", file=sys.stderr)
        return 3
    if not args.check and not args.host_runtime_accepted:
        print(
            "Refusing to scaffold: the Program Kit host/runtime choice is not confirmed by the approved "
            "bootstrap baseline or a later Accepted override.",
            file=sys.stderr,
        )
        return 4
    if not args.check and not args.preview_sources_approved:
        print(
            "Refusing to scaffold: adding preview packages and NuGet sources was not explicitly approved.",
            file=sys.stderr,
        )
        return 5

    extension_root = Path(__file__).resolve().parents[1]
    template_root = extension_root / "templates" / "dotnet"
    target = Path(args.target).resolve()
    pending = reconciliation.pending_transactions(target)
    if pending and not args.recover:
        print(
            "PKS200 interrupted Program Kit reconciliation requires explicit --recover before sync: "
            + ", ".join(path.name for path in pending),
            file=sys.stderr,
        )
        return 6
    if args.recover:
        try:
            recovered = reconciliation.recover_transactions(target)
        except (OSError, ValueError, json.JSONDecodeError, reconciliation.ReconciliationError) as error:
            print(f"PKS201 reconciliation recovery failed: {error}", file=sys.stderr)
            return 2
        for transaction_id in recovered:
            print(f"recovered transaction: {transaction_id}")

    template_manifest = load_json(template_root / "managed-files.json", {})
    base_entries = template_manifest.get("files")
    if not isinstance(base_entries, list):
        raise ValueError("The .NET template manifest has no files list.")
    obsolete_files = template_manifest.get("obsoleteFiles", [])
    if not isinstance(obsolete_files, list) or not all(isinstance(path, str) for path in obsolete_files):
        raise ValueError("The .NET template manifest has an invalid obsoleteFiles list.")

    dotnet_sdk, dotnet_sdk_source = selected_dotnet_sdk(
        target, template_root / "files" / "global.json"
    )
    web_profile = selected_web_profile(target, args.web_profile)
    spa_configuration: dict | None = None
    if web_profile == "spa-pkce":
        configuration_source = target / spa_profile.CONFIGURATION_PATH
        if not configuration_source.is_file():
            configuration_source = template_root / "web-profiles/spa-pkce" / spa_profile.CONFIGURATION_PATH
        spa_configuration = spa_profile.validate_configuration(spa_profile.load_object(configuration_source))

    entries = [dict(entry, contribution="base") for entry in base_entries]
    profile_manifest_path = template_root / "web-profiles" / web_profile / "managed-files.json"
    if profile_manifest_path.is_file():
        profile_entries = load_json(profile_manifest_path, {}).get("files")
        if not isinstance(profile_entries, list):
            raise ValueError(f"The {web_profile} profile manifest has no files list.")
        profile_destinations = {entry["path"] for entry in profile_entries}
        entries = [entry for entry in entries if entry["path"] not in profile_destinations]
        entries.extend(dict(entry, contribution=f"web:{web_profile}") for entry in profile_entries)

    state_path = target / ".program-kit/managed.json"
    state = load_json(state_path, {"schemaVersion": 1, "files": {}})
    old_files = state.get("files")
    if not isinstance(old_files, dict):
        raise ValueError(f"Invalid managed-file state in {state_path}")
    previous_profile = state.get("webProfile")
    previous_profile_paths = profile_paths(template_root, previous_profile)
    migration_catalog = load_json(
        template_root / "migrations.json", {"schemaVersion": 1, "migrations": []}
    )
    migrations = migration_catalog.get("migrations")
    if not isinstance(migrations, list):
        raise ValueError("The .NET migration catalog has no migrations list.")
    applied_migrations = list(state.get("appliedMigrations", []))
    current_version = str(state.get("programKitVersion", "0.0.0"))
    applicable_migrations: list[dict] = []
    for migration in migrations:
        migration_id = migration.get("id")
        if not isinstance(migration_id, str) or migration_id in applied_migrations:
            continue
        through = migration.get("throughVersion")
        unless_profile = migration.get("unlessWebProfile")
        if (
            isinstance(through, str)
            and version_key(current_version) <= version_key(through)
            and web_profile != unless_profile
        ):
            applicable_migrations.append(migration)
            applied_migrations.append(migration_id)

    desired_by_path: dict[str, dict] = {}
    for entry in entries:
        relative = entry["path"]
        if relative in desired_by_path:
            raise ValueError(f"Duplicate managed destination: {relative}")
        source_root = template_root / entry.get("sourceRoot", "files")
        source_relative = entry.get("source", relative)
        source = source_root / source_relative
        rendered = (
            relative == identity_fixture.REALM_PATH
            and web_profile in {"bff-cookie", "spa-pkce"}
        ) or (
            web_profile == "spa-pkce"
            and relative in {
                ".program-kit/web-profile.shells.json",
                ".program-kit/web-profile.json",
                ".program-kit/eng/web/web-contract.json",
            }
        )
        content = desired_content(
            source, relative, dotnet_sdk, web_profile, spa_configuration, template_root
        )
        desired_by_path[relative] = {
            **entry,
            "sourceIdentity": source.relative_to(template_root).as_posix(),
            "rendered": rendered,
            "content": content,
            "hash": sha256_bytes(content),
        }

    created: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []
    preserved: list[str] = []
    removed: list[str] = []
    conflicts: list[str] = []
    conflict_details: dict[str, str] = {}
    actions: list[dict] = []
    next_files: dict[str, dict] = {}

    for relative, desired_entry in desired_by_path.items():
        ownership = desired_entry["ownership"]
        destination = target / relative
        desired = desired_entry["content"]
        desired_hash = desired_entry["hash"]
        previous = old_files.get(relative)
        previous_contribution = None
        if isinstance(previous, dict):
            previous_contribution = previous.get("contribution")
            if not isinstance(previous_contribution, str):
                previous_contribution = (
                    f"web:{previous_profile}" if relative in previous_profile_paths else "base"
                )
        contribution_changed = (
            previous_contribution is not None
            and previous_contribution != desired_entry["contribution"]
        )
        baseline_hash = (
            previous.get("baselineHash", previous.get("templateHash"))
            if isinstance(previous, dict)
            else None
        )
        last_written_hash = (
            previous.get("lastWrittenHash", previous.get("installedHash"))
            if isinstance(previous, dict)
            else None
        )

        if not destination.is_file():
            created.append(relative)
            actions.append({"kind": "create", "path": relative, "content": desired})
            final_hash = desired_hash
            final_baseline = desired_hash
            final_written = desired_hash
        else:
            current_content = destination.read_bytes()
            current_hash = sha256_bytes(current_content)
            final_hash = current_hash
            final_baseline = baseline_hash or desired_hash
            final_written = last_written_hash
            try:
                migrated_content = apply_structured_migrations(
                    relative, current_content, applicable_migrations
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                conflicts.append(relative)
                conflict_details[relative] = str(error)
                migrated_content = current_content
            if migrated_content != current_content:
                updated.append(relative)
                actions.append({"kind": "update", "path": relative, "content": migrated_content})
                final_hash = sha256_bytes(migrated_content)
                final_baseline = desired_hash
                final_written = final_hash
            elif relative in conflict_details:
                pass
            elif current_hash == desired_hash:
                unchanged.append(relative)
                final_written = desired_hash if ownership == "managed" else (last_written_hash or desired_hash)
            elif contribution_changed and current_hash == baseline_hash:
                updated.append(relative)
                actions.append({"kind": "update", "path": relative, "content": desired})
                final_hash = desired_hash
                final_baseline = desired_hash
                final_written = desired_hash
            elif (
                isinstance(previous, dict)
                and current_hash == last_written_hash
                and (ownership == "managed" or previous.get("ownership") == "managed")
            ):
                updated.append(relative)
                actions.append({"kind": "update", "path": relative, "content": desired})
                final_hash = desired_hash
                if contribution_changed:
                    final_baseline = desired_hash
                final_written = desired_hash
            elif ownership == "scaffold" and relative == "NuGet.config":
                routing_error = consumer_nuget_routing_error(destination)
                if routing_error is None:
                    preserved.append(relative)
                    final_hash = recorded_consumer_hash(previous, desired_hash)
                else:
                    conflicts.append(relative)
                    conflict_details[relative] = routing_error
            elif ownership in {"scaffold", "configuration"} and not contribution_changed:
                preserved.append(relative)
                # Consumer-owned bytes are deliberately outside Program Kit desired state. Keep
                # the last governed baseline instead of turning every legitimate edit into state drift.
                final_hash = recorded_consumer_hash(previous, desired_hash)
            else:
                conflicts.append(relative)
                conflict_details[relative] = (
                    "current bytes do not match the last Program Kit write or the prior contribution baseline"
                )

        next_files[relative] = {
            "ownership": ownership,
            "lifecycle": lifecycle_for(relative, ownership, desired_entry["rendered"]),
            "contribution": desired_entry["contribution"],
            "sourceIdentity": desired_entry["sourceIdentity"],
            "templateHash": desired_hash,
            "baselineHash": final_baseline,
            "lastWrittenHash": final_written,
            "installedHash": final_hash,
        }

    retirement_candidates: dict[str, dict] = {}
    for relative, previous in old_files.items():
        if relative not in desired_by_path:
            retirement_candidates[relative] = {"previous": previous, "migration": None}
    for relative in obsolete_files:
        if relative not in desired_by_path:
            retirement_candidates.setdefault(relative, {"previous": old_files.get(relative), "migration": None})

    for migration in applicable_migrations:
        migration_id = migration["id"]
        retire = migration.get("retire", [])
        if not isinstance(retire, list):
            raise ValueError(f"Migration {migration_id} has an invalid retire list.")
        for item in retire:
            relative = item.get("path")
            hashes = item.get("expectedHashes")
            if not isinstance(relative, str) or not isinstance(hashes, list):
                raise ValueError(f"Migration {migration_id} has an invalid retirement entry.")
            if relative not in desired_by_path:
                retirement_candidates.setdefault(
                    relative,
                    {"previous": None, "migration": {**item, "id": migration_id}},
                )

    for relative, candidate in retirement_candidates.items():
        destination = target / relative
        if not destination.is_file():
            continue
        current_hash = sha256_bytes(destination.read_bytes())
        previous = candidate["previous"]
        migration = candidate["migration"]
        safe_hashes: set[str] = set()
        if isinstance(previous, dict):
            previous_ownership = previous.get("ownership")
            if previous_ownership == "managed":
                value = previous.get("lastWrittenHash", previous.get("installedHash"))
            else:
                value = previous.get("baselineHash", previous.get("templateHash"))
            if isinstance(value, str):
                safe_hashes.add(value)
        if isinstance(migration, dict):
            safe_hashes.update(value for value in migration["expectedHashes"] if isinstance(value, str))
        if current_hash in safe_hashes:
            removed.append(relative)
            actions.append({"kind": "remove", "path": relative, "content": None})
        else:
            conflicts.append(relative)
            conflict_details[relative] = (
                "retired Program Kit contribution was preserved because its bytes are not authenticated "
                "by prior state or a versioned migration"
            )

    manifest_rows = [
        {
            "path": relative,
            "ownership": entry["ownership"],
            "lifecycle": lifecycle_for(relative, entry["ownership"], entry["rendered"]),
            "contribution": entry["contribution"],
            "sourceIdentity": entry["sourceIdentity"],
            "templateHash": entry["hash"],
        }
        for relative, entry in sorted(desired_by_path.items())
    ]
    plan_core = {
        "schemaVersion": 1,
        "programKitVersion": extension_version(extension_root),
        "from": {
            "programKitVersion": state.get("programKitVersion"),
            "webProfile": previous_profile,
            "persistenceProfile": state.get("persistenceProfile"),
        },
        "to": {"webProfile": web_profile, "persistenceProfile": args.persistence_profile},
        "actions": [
            {
                "kind": action["kind"],
                "path": action["path"],
                "desiredHash": sha256_bytes(action["content"]) if action["content"] is not None else None,
            }
            for action in actions
        ],
        "preserved": sorted(preserved),
        "conflicts": [
            {"path": path, "reason": conflict_details.get(path, "unclassified conflict")}
            for path in sorted(set(conflicts))
        ],
        "appliedMigrations": applied_migrations,
        "desiredManifestDigest": stable_plan_digest({"files": manifest_rows}),
    }
    legacy_root = target / "eng" / "program-kit"
    cleanup_directories = bool(
        any(path == "eng/program-kit" or path.startswith("eng/program-kit/") for path in removed)
        or (
            legacy_root.is_dir()
            and not any(path.is_file() for path in legacy_root.rglob("*"))
        )
    )
    plan_core["cleanupDirectories"] = ["eng/program-kit"] if cleanup_directories else []
    plan_digest = stable_plan_digest(plan_core)
    plan = {**plan_core, "planDigest": plan_digest}
    if args.plan_digest and args.plan_digest != plan_digest:
        print(
            f"PKS202 plan digest changed: expected {args.plan_digest}, actual {plan_digest}",
            file=sys.stderr,
        )
        return 7

    next_state_value = {
        "schemaVersion": 2,
        "programKitVersion": extension_version(extension_root),
        "dotnetSdk": dotnet_sdk,
        "dotnetSdkSource": dotnet_sdk_source,
        "selections": {"web": web_profile, "persistence": args.persistence_profile},
        "webProfile": web_profile,
        "webProfileContract": f"{web_profile}-v1",
        "webThreatModel": "program-kit-web-threat-model-v1" if web_profile != "none" else "none",
        "webSecurityEvidence": "program-kit-web-security-evidence-v1" if web_profile != "none" else "none",
        "persistenceProfile": args.persistence_profile,
        "desiredManifestDigest": plan_core["desiredManifestDigest"],
        "appliedMigrations": applied_migrations,
        "files": next_files,
    }
    next_state = (json.dumps(next_state_value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    state_changed = not state_path.is_file() or state_path.read_bytes() != next_state
    plan["stateChanged"] = state_changed

    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(f"selected .NET SDK: {dotnet_sdk} ({dotnet_sdk_source})")
        print(f"selected web profile: {web_profile}")
        print(f"selected persistence profile: {args.persistence_profile}")
        for label, marker, paths in (
            ("created", "+", created),
            ("updated", "~", updated),
            ("preserved consumer files", "=", preserved),
            ("conflicts", "!", sorted(set(conflicts))),
            ("removed retired Program Kit files", "-", removed),
        ):
            print(f"{label}: {len(paths)}")
            for path in paths:
                detail = conflict_details.get(path)
                print(f"  {marker} {path}" + (f": {detail}" if detail else ""))
        if cleanup_directories:
            print("empty retired Program Kit directories to remove: 1")
            print("  - eng/program-kit")
        print(f"unchanged: {len(unchanged)}")
        print(f"state changed: {'yes' if state_changed else 'no'}")
        print(f"plan digest: {plan_digest}")

    if conflicts:
        print("Resolve conflicts explicitly; reconciliation made no consumer-file changes.", file=sys.stderr)
        return 2
    if args.check:
        return 1 if actions or state_changed or cleanup_directories else 0
    if web_profile in {"bff-cookie", "spa-pkce"}:
        # Validate identity desired-state semantics against staged bytes before commit.
        realm = desired_by_path.get(identity_fixture.REALM_PATH)
        if realm is None:
            raise ValueError(f"{web_profile} desired state is missing {identity_fixture.REALM_PATH}")
        identity_fixture.validate_realm(realm["content"], web_profile, spa_configuration)
    target.mkdir(parents=True, exist_ok=True)
    try:
        transaction_id = reconciliation.apply_plan(target, actions, next_state)
    except (OSError, ValueError, reconciliation.ReconciliationError) as error:
        print(f"PKS203 reconciliation rolled back: {error}", file=sys.stderr)
        return 2
    print(f"committed reconciliation transaction: {transaction_id}")
    for relative in prune_retired_program_kit_directories(target):
        print(f"removed empty retired Program Kit directory: {relative}")
    if web_profile in {"bff-cookie", "spa-pkce"}:
        identity_fixture.verify_repository(target, web_profile, spa_configuration)
    if web_profile == "spa-pkce" and spa_configuration is not None:
        spa_profile.verify_outputs(target, spa_configuration)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
