from __future__ import annotations

import json
import importlib.util
from pathlib import Path
from unittest.mock import patch


THREAT_MODEL_ID = "program-kit-web-threat-model-v1"
EVIDENCE_ID = "program-kit-web-security-evidence-v1"
PROFILES = {"bff-cookie-v1", "spa-pkce-v1"}
REQUIRED_SOURCES = {
    "SRC-IETF-RFC9700",
    "SRC-IETF-BROWSER-APPS",
    "SRC-OIDC-CORE",
    "SRC-OIDC-RP-LOGOUT",
    "SRC-OIDC-BACKCHANNEL-LOGOUT",
    "SRC-NIST-800-63B-4",
    "SRC-NIST-800-63C-4",
    "SRC-FKS-OAUTH",
    "SRC-FKS-OIDC",
    "SRC-PK-LOCAL-POLICY",
}
REQUIRED_CONTROLS = {f"WEB-C{number:02d}" for number in range(1, 14)}
REQUIRED_DEFAULTS = {f"WEB-D{number:02d}" for number in range(1, 9)}
REQUIRED_VERIFICATION = {f"WEB-V{number}" for number in range(1, 5)}


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"Expected a JSON object in {path}")
    return value


def indexed(items: object, label: str) -> dict[str, dict]:
    if not isinstance(items, list) or not items:
        raise AssertionError(f"Security evidence has no {label}")
    result: dict[str, dict] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise AssertionError(f"Security evidence has an invalid {label} entry")
        item_id = item["id"]
        if item_id in result:
            raise AssertionError(f"Security evidence repeats {label} ID {item_id}")
        result[item_id] = item
    return result


def require_nonempty(item: dict, fields: tuple[str, ...], label: str) -> None:
    for field in fields:
        if field not in item or item[field] in (None, "", []):
            raise AssertionError(f"{label} has no {field}")


def validate_compose_topology_contract(root: Path) -> None:
    path = (
        root
        / "extensions/program-kit-dotnet/templates/dotnet/web-profiles/common/.program-kit/eng/compose_topology.py"
    )
    specification = importlib.util.spec_from_file_location("program_kit_compose_topology", path)
    if specification is None or specification.loader is None:
        raise AssertionError("Could not load the managed Compose topology validator")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)

    identity = {
        "networks": {"private": {"name": "program-kit-local"}},
        "services": {
            "keycloak": {
                "networks": {"private": {"aliases": ["program-kit-identity"]}}
            }
        },
    }
    application = {
        "networks": {
            "private": {"name": "program-kit-local"},
            "default": {"name": "consumer_default"},
        },
        "services": {
            "application": {
                "environment": {"AUTHORITY": "http://program-kit-identity:8080/realms/program-kit"},
                "networks": {"private": None},
            },
            "browser": {
                "environment": {"PROGRAMKIT_INTERNAL_ORIGIN": "http://application:8080"},
                "depends_on": {"application": {"condition": "service_started"}},
                "networks": {"default": None},
            },
        },
    }
    overlay = Path("deploy/compose.browser.yml")
    try:
        module.validate_desired({"identity": identity, "application": application}, overlay)
    except module.TopologyError as error:
        message = str(error)
        if "PKC001" not in message or str(overlay) not in message or "program-kit-local" not in message:
            raise AssertionError(f"Disconnected Compose diagnostic is incomplete: {message}") from error
    else:
        raise AssertionError("A consumer service isolated on the implicit default network was accepted")

    application["services"]["browser"]["networks"] = {"renamed-private-key": None}
    application["networks"]["renamed-private-key"] = {"name": "program-kit-local"}
    module.validate_desired({"identity": identity, "application": application}, overlay)

    def running(_docker, _compose, service_name, _repository):
        return {"consumer_default"} if service_name == "browser" else {"program-kit-local"}

    with patch.object(module, "inspect_running_networks", running):
        try:
            module.verify_running(
                "docker",
                {"identity": identity, "application": application},
                {"identity": [], "application": []},
                root,
            )
        except module.TopologyError as error:
            if "PKC002" not in str(error) or "force-recreated" not in str(error):
                raise AssertionError(f"Stale running-container diagnostic is incomplete: {error}") from error
        else:
            raise AssertionError("A stale running container attachment was accepted")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    validate_compose_topology_contract(root)
    references = root / "extensions/program-kit-dotnet/references"
    evidence_path = references / "web-security-evidence.json"
    threat_model_path = references / "web-security-threat-model.md"
    evidence = load_object(evidence_path)

    if evidence.get("schemaVersion") != 1 or evidence.get("id") != EVIDENCE_ID:
        raise AssertionError("Security evidence identity or schema is invalid")
    if evidence.get("threatModel") != THREAT_MODEL_ID:
        raise AssertionError("Security evidence does not bind the expected threat model")
    if set(evidence.get("profileContracts", [])) != PROFILES:
        raise AssertionError("Security evidence does not cover both authenticated profiles")
    require_nonempty(evidence, ("lastReviewed", "owner", "claim"), "Security evidence")
    if "do not certify" not in evidence["claim"]:
        raise AssertionError("Security evidence must bound its assurance claim")

    source_classes = set(evidence.get("sourceClasses", []))
    sources = indexed(evidence.get("sources"), "source")
    if not REQUIRED_SOURCES.issubset(sources):
        raise AssertionError("Security evidence is missing required standards or research sources")
    for source_id, source in sources.items():
        require_nonempty(source, ("title", "class", "status", "url"), source_id)
        if source["class"] not in source_classes:
            raise AssertionError(f"{source_id} uses an undeclared source class")
        if source["class"] != "program-kit-policy" and not source["url"].startswith("https://"):
            raise AssertionError(f"{source_id} must use an HTTPS primary-source URL")
    browser_source = sources["SRC-IETF-BROWSER-APPS"]
    if browser_source["class"] != "ietf-working-group-draft" or "not a final RFC" not in browser_source["status"]:
        raise AssertionError("The browser-app guidance must remain honestly classified as a draft")
    if sources["SRC-PK-LOCAL-POLICY"]["class"] != "program-kit-policy":
        raise AssertionError("Program Kit policy must not be represented as external evidence")

    threats = indexed(evidence.get("threats"), "threat")
    controls = indexed(evidence.get("controls"), "control")
    if set(controls) != REQUIRED_CONTROLS:
        raise AssertionError("Security evidence control catalogue is incomplete or unexpectedly renumbered")
    mapped_threats: set[str] = set()
    for control_id, control in controls.items():
        require_nonempty(
            control,
            ("decision", "classification", "threats", "sources", "verification"),
            control_id,
        )
        unknown_threats = set(control["threats"]) - set(threats)
        unknown_sources = set(control["sources"]) - set(sources)
        if unknown_threats:
            raise AssertionError(f"{control_id} maps unknown threats: {sorted(unknown_threats)}")
        if unknown_sources:
            raise AssertionError(f"{control_id} maps unknown sources: {sorted(unknown_sources)}")
        mapped_threats.update(control["threats"])
    if mapped_threats != set(threats):
        raise AssertionError(f"Uncontrolled threats: {sorted(set(threats) - mapped_threats)}")
    applicability = evidence.get("controlApplicability")
    if not isinstance(applicability, dict) or set(applicability) != PROFILES:
        raise AssertionError("Security evidence must declare control applicability for both profiles")
    for profile, identifiers in applicability.items():
        if (
            not isinstance(identifiers, list)
            or len(identifiers) != len(set(identifiers))
            or not set(identifiers).issubset(controls)
        ):
            raise AssertionError(f"{profile} has invalid or duplicate applicable control IDs")
    if {"WEB-C01", "WEB-C03", "WEB-C04"}.intersection(applicability["spa-pkce-v1"]):
        raise AssertionError("The SPA profile must not claim BFF-only cookie controls")

    defaults = indexed(evidence.get("configurableDefaults"), "configurable default")
    if set(defaults) != REQUIRED_DEFAULTS:
        raise AssertionError("Configurable-default evidence is incomplete or unexpectedly renumbered")
    for default_id, default in defaults.items():
        require_nonempty(
            default,
            ("setting", "default", "unit", "classification", "rationale", "overrideWhen", "requiredEvidence"),
            default_id,
        )
    indexed(evidence.get("residualRisks"), "residual risk")
    verification = indexed(evidence.get("verificationLevels"), "verification level")
    if set(verification) != REQUIRED_VERIFICATION:
        raise AssertionError("Security assurance levels are incomplete")
    review_triggers = indexed(evidence.get("reviewTriggers"), "review trigger")
    if len(review_triggers) < 5 or not any("Twelve months" in item["trigger"] for item in review_triggers.values()):
        raise AssertionError("Security evidence lacks the periodic review trigger")

    threat_model = threat_model_path.read_text(encoding="utf-8")
    for required in (
        THREAT_MODEL_ID,
        EVIDENCE_ID,
        "Attacker capabilities",
        "Trust boundaries",
        "Assumptions and out-of-scope risks",
        "do not prove absence of defects",
    ):
        if required not in threat_model:
            raise AssertionError(f"Threat model is missing {required!r}")
    for threat_id in threats:
        if threat_id not in threat_model:
            raise AssertionError(f"Threat model does not explain {threat_id}")

    for profile_directory, contract_id in (
        ("bff-cookie", "bff-cookie-v1"),
        ("spa-pkce", "spa-pkce-v1"),
    ):
        profile_root = root / "extensions/program-kit-dotnet/templates/dotnet/web-profiles" / profile_directory
        manifest = load_object(profile_root / "managed-files.json")
        files = {item["path"]: item for item in manifest["files"]}
        if ".program-kit/eng/web/persona-fixture.ts" not in files:
            raise AssertionError(f"{profile_directory} does not ship the validated persona-fixture loader")
        for destination, source in (
            (".program-kit/security/web-security-evidence.json", "web-security-evidence.json"),
            ("docs/architecture/program-kit/web-security-threat-model.md", "web-security-threat-model.md"),
        ):
            entry = files.get(destination)
            if not entry or entry.get("ownership") != "managed" or entry.get("source") != source:
                raise AssertionError(f"{profile_directory} does not ship managed {destination}")
        contract = load_object(profile_root / ".program-kit/eng/web/web-contract.json")
        if contract.get("profile") != contract_id:
            raise AssertionError(f"Unexpected profile contract in {profile_directory}")
        if contract.get("assurance") != {
            "threatModel": THREAT_MODEL_ID,
            "evidenceProfile": EVIDENCE_ID,
        }:
            raise AssertionError(f"{profile_directory} does not bind exact assurance IDs")
        profile_record = load_object(profile_root / ".program-kit/web-profile.json")
        if profile_record.get("threatModel") != THREAT_MODEL_ID or profile_record.get("securityEvidence") != EVIDENCE_ID:
            raise AssertionError(f"{profile_directory} profile record does not bind exact assurance IDs")
        shell_profile = load_object(profile_root / ".program-kit/web-profile.shells.json")
        shell = shell_profile["CShells"]["Shells"]["default"]
        web_settings = shell["Configuration"]["ProgramKit"]["Web"]
        if web_settings.get("PermissionClaim") != "permissions":
            raise AssertionError(f"{profile_directory} does not name the canonical permission claim")
        if web_settings.get("RolePermissions") != {} or web_settings.get("ScopePermissions") != {}:
            raise AssertionError(
                f"{profile_directory} must not invent application-specific provider mappings"
            )
        selected_feature = (
            "ProgramKit.Authentication.BffCookie"
            if profile_directory == "bff-cookie"
            else "ProgramKit.Authentication.SpaPkce"
        )
        alternative_feature = (
            "ProgramKit.Authentication.SpaPkce"
            if profile_directory == "bff-cookie"
            else "ProgramKit.Authentication.BffCookie"
        )
        if selected_feature not in shell["Features"] or alternative_feature in shell["Features"]:
            raise AssertionError(f"{profile_directory} does not activate only its selected auth feature")
        if (profile_root / "hostsettings.json").exists():
            raise AssertionError(f"{profile_directory} must not carry auth settings in hostsettings.json")

    base_host_settings = load_object(
        root / "extensions/program-kit-dotnet/templates/dotnet/files/hostsettings.json"
    )
    if "Web" in base_host_settings.get("ProgramKit", {}):
        raise AssertionError("ProgramKit hostsettings must remain free of web-profile configuration")

    host_root = root / "src/dotnet/ProgramKit.Host"
    host_source = "\n".join(path.read_text(encoding="utf-8") for path in host_root.rglob("*.cs"))
    for forbidden in (
        "ProgramKitWebBoundary",
        "AddAuthentication",
        "UseAuthentication",
        "UseExceptionHandler",
        "AddProblemDetails",
        "CorrelationAndSecurityHeadersMiddleware",
    ):
        if forbidden in host_source:
            raise AssertionError(f"ProgramKit.Host still owns web or authentication policy: {forbidden}")
    feature_roots = [
        root / "src/dotnet/ProgramKit.Authentication",
        root / "src/dotnet/ProgramKit.Authentication.BffCookie",
        root / "src/dotnet/ProgramKit.Authentication.SpaPkce",
        root / "src/dotnet/ProgramKit.WebDefaults",
        root / "src/dotnet/ProgramKit.Web.ProblemDetails",
        root / "src/dotnet/ProgramKit.Web.OpenApi",
    ]
    feature_source = "\n".join(
        path.read_text(encoding="utf-8")
        for feature_root in feature_roots
        for path in feature_root.glob("*.cs")
    )
    for required in (
        "PermissionClaimsTransformation",
        "PermissionPolicyProvider",
        'RequireClaim(webOptions.Value.PermissionClaim, permission)',
        "settings.RolePermissions",
        "settings.ScopePermissions",
        "permissions",
        "AntiforgeryFormField",
        "formFieldName = AntiforgeryFormField",
        '"authentication_callback_invalid"',
        '"identity_provider_unavailable"',
        "IWebShellFeature",
        "IMiddlewareShellFeature",
        "IAuthenticationErrorWriter",
        "TryAddSingleton<IAuthenticationErrorWriter, DefaultAuthenticationErrorWriter>",
        "settings.BackchannelAuthority",
        "options.MetadataAddress",
        "options.BackchannelTimeout",
    ):
        if required not in feature_source:
            raise AssertionError(f"CShells feature packages do not implement the web contract: {required}")
    web_profiles_root = root / "extensions/program-kit-dotnet/templates/dotnet/web-profiles"
    dev_script = (
        web_profiles_root / "common/.program-kit/eng/Dev.ps1"
    ).read_text(encoding="utf-8")
    for required in (
        "compose_topology.py",
        "no service was started",
        "--force-recreate",
        "--remove-orphans",
        "--verify-running",
    ):
        if required not in dev_script:
            raise AssertionError(f"Managed Dev.ps1 does not reconcile Compose topology: {required}")
    persona_fixture = web_profiles_root / "common/.program-kit/eng/web/persona-fixture.ts"
    persona_source = persona_fixture.read_text(encoding="utf-8")
    expected_realm = (
        persona_fixture.parent / "../../../deploy/keycloak/program-kit-realm.json"
    ).resolve()
    if "../../../deploy/keycloak/program-kit-realm.json" not in persona_source or not expected_realm.is_file():
        raise AssertionError("The managed persona loader does not resolve the realm from its shipped suite directory")
    if "../../../../deploy/keycloak/program-kit-realm.json" in persona_source:
        raise AssertionError("The managed persona loader still escapes one directory above the consumer repository")
    test_web = (web_profiles_root / "common/.program-kit/eng/Test-Web.ps1").read_text(encoding="utf-8")
    package = load_object(web_profiles_root / "common/.program-kit/eng/web/package.json")
    fixture_script = package.get("scripts", {}).get("test:fixture", "")
    if "../../../deploy/keycloak/program-kit-realm.json" not in fixture_script:
        raise AssertionError("The managed web suite has no executable persona-fixture regression")
    if "npm -- run test:fixture" not in test_web:
        raise AssertionError("Test-Web.ps1 does not execute the persona-fixture regression")
    identity_compose = (
        web_profiles_root / "common/deploy/compose.identity.yml"
    ).read_text(encoding="utf-8")
    for required in (
        "KC_HOSTNAME: http://localhost:8080",
        'KC_HOSTNAME_BACKCHANNEL_DYNAMIC: "true"',
        "program-kit-identity",
        "name: program-kit-local",
    ):
        if required not in identity_compose:
            raise AssertionError(f"The identity Compose topology is missing: {required}")
    for compose_path in (
        web_profiles_root / "common/deploy/compose.application.yml",
        web_profiles_root / "spa-pkce/deploy/compose.application.yml",
    ):
        application_compose = compose_path.read_text(encoding="utf-8")
        for required in (
            "BackchannelAuthority",
            "http://program-kit-identity:8080/realms/program-kit",
            "external: true",
            "name: program-kit-local",
        ):
            if required not in application_compose:
                raise AssertionError(
                    f"{compose_path} is missing private identity backchannel topology: {required}"
                )
        if "extra_hosts" in application_compose or "localhost:host-gateway" in application_compose:
            raise AssertionError(f"{compose_path} must not override container localhost")
    realm_fixture = web_profiles_root / "common/deploy/keycloak/program-kit-realm.json"
    realm = load_object(realm_fixture)
    if realm.get("attributes", {}).get("programKitFixture") != "local-non-production-only":
        raise AssertionError("The managed identity personas are not explicitly local/non-production")
    fixture_passwords = {
        credential["value"]
        for user in realm.get("users", [])
        for credential in user.get("credentials", [])
        if credential.get("type") == "password"
    }
    if len(fixture_passwords) != 3:
        raise AssertionError("The local identity fixture must define exactly three persona passwords")
    occurrences: dict[str, list[str]] = {password: [] for password in fixture_passwords}
    for path in root.rglob("*"):
        if (
            not path.is_file()
            or any(
                part in {".git", "artifacts", "bin", "obj", "node_modules", "__pycache__"}
                for part in path.relative_to(root).parts
            )
            or path.suffix.lower() not in {".json", ".md", ".py", ".ps1", ".ts", ".cs", ".yml", ".yaml"}
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for password in fixture_passwords:
            if password in text:
                occurrences[password].append(path.relative_to(root).as_posix())
    expected_fixture = realm_fixture.relative_to(root).as_posix()
    if any(paths != [expected_fixture] for paths in occurrences.values()):
        raise AssertionError(f"Managed local persona password escaped its authorized fixture: {occurrences}")
    browser_contract = "\n".join(
        path.read_text(encoding="utf-8")
        for pattern in ("*.ts", "*.ps1")
        for path in web_profiles_root.rglob(pattern)
    )
    if "PROGRAMKIT_PERMISSION_PROBE_PATH" not in browser_contract or "PROGRAMKIT_ROLE_PROBE_PATH" in browser_contract:
        raise AssertionError("The browser contract must probe application permissions, not provider roles")
    permission_probe = (
        web_profiles_root
        / "common/.program-kit/eng/web/tests/authentication.spec.ts"
    ).read_text(encoding="utf-8")
    if "../persona-fixture.js" not in permission_probe:
        raise AssertionError("The BFF browser contract does not load personas from the managed realm fixture")
    spa_probe = (
        web_profiles_root / "spa-pkce/.program-kit/eng/web/tests/authentication.spec.ts"
    ).read_text(encoding="utf-8")
    if "../persona-fixture.js" not in spa_probe:
        raise AssertionError("The SPA browser contract does not load personas from the managed realm fixture")
    for required in (
        "const authorizedResponse = await authorized.request.get(path);",
        "expect(authorizedResponse.ok()).toBeTruthy();",
        "const deniedResponse = await denied.request.get(path);",
        "expect(deniedResponse.status()).toBe(403);",
    ):
        if required not in permission_probe:
            raise AssertionError(f"The permission-probe browser contract is missing: {required}")
    if "authorized.request.get(path)).status()).toBe(200)" in permission_probe:
        raise AssertionError("The authorized permission probe must accept every successful 2xx response")
    for required in (
        "page.evaluate(async () =>",
        "form.method = 'post';",
        "field.name = formFieldName;",
        "form.submit();",
        "cross-site top-level logout form fails before session mutation",
        "provider navigation failure cannot restore local access",
    ):
        if required not in permission_probe:
            raise AssertionError(f"The real-browser BFF logout evidence is missing: {required}")

    bff_root = web_profiles_root / "bff-cookie"
    bff_manifest = load_object(bff_root / "managed-files.json")
    bff_files = {item["path"] for item in bff_manifest["files"]}
    if ".program-kit/eng/web/bff-session.ts" not in bff_files:
        raise AssertionError("The BFF profile does not ship its browser logout adapter")
    if ".program-kit/eng/web/tests/bff-session.spec.ts" not in bff_files:
        raise AssertionError("The BFF profile does not ship direct tests for its browser logout adapter")
    bff_contract = load_object(bff_root / ".program-kit/eng/web/web-contract.json")
    if bff_contract.get("schemaVersion") != 2:
        raise AssertionError("The browser-complete BFF contract must use schema version 2")
    routes = bff_contract.get("routes", {})
    if set(routes) != {
        "login", "user", "antiforgery", "logout", "signedOut", "accessDenied",
        "oidcCallback", "signedOutCallback", "remoteSignOut",
    }:
        raise AssertionError("The BFF contract does not close over every managed browser route")
    if routes["antiforgery"]["success"]["body"].get("formFieldName") != "__RequestVerificationToken":
        raise AssertionError("The BFF contract does not expose the browser form antiforgery field")
    if routes["logout"].get("browserInvocation") != "user-initiated-top-level-form-target":
        raise AssertionError("The BFF logout contract is not consumable as browser navigation")
    authenticated_body = routes["user"]["success"]["authenticatedBody"]
    if authenticated_body.get("issuer") != "non-empty-validated-uri-string":
        raise AssertionError("The BFF session projection does not expose its validated issuer")
    if authenticated_body.get("subject") != "non-empty-string":
        raise AssertionError("The BFF session projection still permits an authenticated null subject")
    if routes["user"]["success"].get("invalidIdentity", {}).get("code") != "authentication_identity_invalid":
        raise AssertionError("The BFF contract has no explicit failure for a malformed authenticated ticket")
    ownership = bff_contract.get("ownership", {})
    if ownership.get("featureOwnedPrefix") != "/api/" or "/bff/logout" not in ownership.get("managedExactPaths", []):
        raise AssertionError("The BFF contract confuses managed BFF routes with feature-owned APIs")

    tooling_command = (
        root / "extensions/program-kit-governance/commands/speckit.program-kit-governance.tooling.md"
    ).read_text(encoding="utf-8")
    for required in ("preserve their canonical meanings", "WEB-Qxx", "many-to-many"):
        if required not in tooling_command:
            raise AssertionError("Tooling guidance permits ambiguous reuse of canonical WEB-Cxx IDs")

    adr = (root / "docs/decisions/0005-secure-web-boundary-profiles.md").read_text(encoding="utf-8")
    contract = (references / "secure-web-profiles.md").read_text(encoding="utf-8")
    for document_name, document in (("ADR 0005", adr), ("secure web contract", contract)):
        for required in (THREAT_MODEL_ID, EVIDENCE_ID):
            if required not in document:
                raise AssertionError(f"{document_name} does not reference {required}")
    for required in ("any `2xx` response", "including `200` and `204`", "exactly `403`"):
        if required not in contract:
            raise AssertionError(f"The secure web contract does not define permission-probe behavior: {required}")
    if "not a final RFC" not in adr or "does not certify" not in adr:
        raise AssertionError("ADR 0005 overstates the strength of its security evidence")

    print("Web security assurance validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
