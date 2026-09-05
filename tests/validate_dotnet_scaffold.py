from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "extensions/program-kit-dotnet/scripts/dotnet_sync.py"


def run(*arguments: str, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        env=environment,
    )


def snapshot(repository: Path) -> dict[str, bytes]:
    return {
        path.relative_to(repository).as_posix(): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }


def assert_profile(repository: Path, expected: str) -> None:
    state = json.loads((repository / ".program-kit/managed.json").read_text(encoding="utf-8"))
    assert state["schemaVersion"] == 2
    assert state["selections"]["web"] == expected
    shell = json.loads(
        (repository / ".program-kit/web-profile.shells.json").read_text(encoding="utf-8")
    )["CShells"]["Shells"]["default"]
    features = set(shell["Features"])
    if expected == "none":
        assert not any(feature.startswith("ProgramKit.Authentication") for feature in features)
        assert not (repository / "deploy/keycloak/program-kit-realm.json").exists()
    else:
        selected = (
            "ProgramKit.Authentication.BffCookie"
            if expected == "bff-cookie"
            else "ProgramKit.Authentication.SpaPkce"
        )
        alternative = (
            "ProgramKit.Authentication.SpaPkce"
            if expected == "bff-cookie"
            else "ProgramKit.Authentication.BffCookie"
        )
        assert selected in features and alternative not in features
        realm = json.loads(
            (repository / "deploy/keycloak/program-kit-realm.json").read_text(encoding="utf-8")
        )
        assert realm["loginTheme"] == "program-kit"
        selected_client = "program-kit-bff" if expected == "bff-cookie" else "program-kit-spa"
        client_ids = [client["clientId"] for client in realm["clients"]]
        assert client_ids == ["program-kit-api", selected_client]
        theme_paths = (
            "deploy/keycloak/themes/program-kit/login/theme.properties",
            "deploy/keycloak/themes/program-kit/login/webauthn-register.ftl",
            "deploy/keycloak/themes/program-kit/login/resources/css/program-kit.css",
            "deploy/keycloak/themes/program-kit/login/resources/img/program-kit-mark.svg",
        )
        for relative in theme_paths:
            assert (repository / relative).is_file(), relative
            assert state["files"][relative]["ownership"] == "configuration", relative
        identity_compose = (repository / "deploy/compose.identity.yml").read_text(encoding="utf-8")
        assert "./keycloak/themes:/opt/keycloak/themes:ro" in identity_compose
    spa_only = (
        ".program-kit/spa-pkce.json",
        ".program-kit/spa-pkce.schema.json",
        "eng/program-kit/verify_spa_profile.py",
        "eng/program-kit/web/spa-session.ts",
        "eng/program-kit/web/vite.security.mjs",
    )
    for relative in spa_only:
        assert (repository / relative).exists() == (expected == "spa-pkce"), relative
    assert (repository / "eng/program-kit/web/bff-session.ts").exists() == (expected == "bff-cookie")
    assert (repository / "eng/program-kit/web/tests/bff-session.spec.ts").exists() == (
        expected == "bff-cookie"
    )


def seed_legacy_root_web_settings(repository: Path, profile: str) -> None:
    fixture = json.loads(
        (ROOT / f"tests/fixtures/legacy-{profile}-web.json").read_text(encoding="utf-8")
    )
    hostsettings_path = repository / "hostsettings.json"
    hostsettings = json.loads(hostsettings_path.read_text(encoding="utf-8"))
    hostsettings["ProgramKit"]["Web"] = fixture
    hostsettings_path.write_text(json.dumps(hostsettings, indent=2) + "\n", encoding="utf-8")
    state_path = repository / ".program-kit/managed.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["programKitVersion"] = "0.9.0"
    state["appliedMigrations"] = [
        migration
        for migration in state.get("appliedMigrations", [])
        if migration != "0.9.3-retire-legacy-root-web-settings"
    ]
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    template_root = ROOT / "extensions/program-kit-dotnet/templates/dotnet"
    neutral_realm = json.loads(
        (template_root / "web-profiles/common/deploy/keycloak/program-kit-realm.json")
        .read_text(encoding="utf-8")
    )
    assert [client["clientId"] for client in neutral_realm["clients"]] == ["program-kit-api"]
    assert neutral_realm["loginTheme"] == "program-kit"
    assert "offline_access" in {
        role["name"] for role in neutral_realm["roles"]["realm"]
    }
    assert all("offline_access" in user["realmRoles"] for user in neutral_realm["users"])
    for profile, selected_client in (
        ("bff-cookie", "program-kit-bff"),
        ("spa-pkce", "program-kit-spa"),
    ):
        contribution = json.loads(
            (template_root / f"web-profiles/{profile}/identity-client.json")
            .read_text(encoding="utf-8")
        )
        assert contribution["clientId"] == selected_client
    profile_reference = (
        ROOT / "extensions/program-kit-dotnet/references/secure-web-profiles.md"
    ).read_text(encoding="utf-8")
    assert "exactly one interactive client" in profile_reference
    assert "The unselected interactive client is absent" in profile_reference
    assert "confidential BFF client,\npublic SPA-PKCE client" not in profile_reference

    with tempfile.TemporaryDirectory(prefix="program-kit-dotnet-sync-") as value:
        target = Path(value)

        rejected = run("--target", str(target))
        assert rejected.returncode == 3, rejected.stderr
        assert not (target / "global.json").exists(), "The .NET scaffold ran without profile selection."

        runtime_unaccepted = run("--target", str(target), "--profile-selected")
        assert runtime_unaccepted.returncode == 4, runtime_unaccepted.stderr
        assert not (target / "global.json").exists(), "The .NET scaffold ran without an accepted runtime ADR."

        preview_unapproved = run(
            "--target", str(target), "--profile-selected", "--host-runtime-accepted"
        )
        assert preview_unapproved.returncode == 5, preview_unapproved.stderr
        assert not (target / "global.json").exists(), "The .NET scaffold ran without preview-source approval."

        missing_target = target / "missing"
        unchecked = run("--target", str(missing_target), "--profile-selected", "--check")
        assert unchecked.returncode == 1, unchecked.stderr
        assert not missing_target.exists(), "A read-only drift check changed the repository."

        approvals = ("--profile-selected", "--host-runtime-accepted", "--preview-sources-approved")
        installed = run("--target", str(target), *approvals)
        assert installed.returncode == 0, installed.stderr
        state = json.loads((target / ".program-kit/managed.json").read_text(encoding="utf-8"))
        assert state["programKitVersion"]
        assert state["dotnetSdk"] == "10.0.202"
        assert state["dotnetSdkSource"] == "program-kit-default"
        assert state["schemaVersion"] == 2
        none_shell_profile = json.loads(
            (target / ".program-kit/web-profile.shells.json").read_text(encoding="utf-8")
        )
        assert none_shell_profile["CShells"]["Shells"]["default"]["Features"] == {}
        assert (target / "eng/program-kit/ProgramKit.Build.props").is_file()
        assert (target / "Directory.Build.props").is_file()
        build_script = (target / "eng/program-kit/Build.ps1").read_text(encoding="utf-8")
        assert "[switch]$LockedMode" in build_script
        assert "Join-Path (Join-Path $artifacts 'packages') $version" in build_script
        runnable_builder = (target / "eng/program-kit/runnable_host.py").read_text(encoding="utf-8")
        assert "def is_runtime_package" in runnable_builder
        assert '"analyzer", "dotnettool", "template"' in runnable_builder
        application_ci = (target / ".github/workflows/application-ci.yml").read_text(encoding="utf-8")
        application_release = (target / ".github/workflows/application-release.yml").read_text(encoding="utf-8")
        assert "Invoke-RepositoryVerification.ps1 -Mode CI" in application_ci
        assert "Invoke-RepositoryVerification.ps1 -Mode Release" in application_release
        assert "Build.ps1 -LockedMode" in application_release
        assert "runnable-host.json" in application_release
        assert "containerimage.digest" in application_release
        disabled_openapi = subprocess.run(
            [
                sys.executable,
                str(target / "eng/program-kit/openapi_pipeline.py"),
                "--repository",
                str(target),
            ],
            capture_output=True,
            text=True,
        )
        assert disabled_openapi.returncode == 0, disabled_openapi.stderr
        assert "not configured" in disabled_openapi.stdout

        nuget_config = target / "NuGet.config"
        nuget_text = nuget_config.read_text(encoding="utf-8")
        assert '<package pattern="*" />' in nuget_text
        assert '<package pattern="CShells.*" />' in nuget_text
        assert '<package pattern="Nuplane.*" />' in nuget_text
        assert state["files"]["NuGet.config"]["ownership"] == "scaffold"

        consumer_verifier = target / "eng/verify.ps1"
        consumer_verifier.parent.mkdir(parents=True, exist_ok=True)
        consumer_verifier.write_text("Write-Host 'consumer aggregate gate'\n", encoding="utf-8")
        verifier_bytes = consumer_verifier.read_bytes()
        verifier_preserved = run("--target", str(target), *approvals)
        assert verifier_preserved.returncode == 0, verifier_preserved.stderr
        assert consumer_verifier.read_bytes() == verifier_bytes

        # A managed 0.9.0 schema upgrades atomically with its already-updated descriptor producer.
        runnable_schema_path = target / ".program-kit/runnable-host.schema.json"
        current_runnable_schema = json.loads(runnable_schema_path.read_text(encoding="utf-8"))
        legacy_runnable_schema = json.loads(json.dumps(current_runnable_schema))
        legacy_configuration = legacy_runnable_schema["properties"]["configuration"]
        legacy_configuration["required"] = [
            name for name in legacy_configuration["required"] if not name.startswith("webProfile")
        ]
        legacy_configuration["properties"].pop("webProfileShells")
        legacy_configuration["properties"].pop("webProfileShellsSha256")
        legacy_schema_bytes = (json.dumps(legacy_runnable_schema, indent=2) + "\n").encode("utf-8")
        runnable_schema_path.write_bytes(legacy_schema_bytes)
        schema_state_path = target / ".program-kit/managed.json"
        schema_state = json.loads(schema_state_path.read_text(encoding="utf-8"))
        schema_state["programKitVersion"] = "0.9.0"
        legacy_schema_hash = hashlib.sha256(legacy_schema_bytes).hexdigest()
        schema_state["files"][".program-kit/runnable-host.schema.json"]["lastWrittenHash"] = legacy_schema_hash
        schema_state["files"][".program-kit/runnable-host.schema.json"]["installedHash"] = legacy_schema_hash
        schema_state_path.write_text(json.dumps(schema_state, indent=2) + "\n", encoding="utf-8")
        schema_upgraded = run("--target", str(target), *approvals)
        assert schema_upgraded.returncode == 0, schema_upgraded.stderr
        assert json.loads(runnable_schema_path.read_text(encoding="utf-8")) == current_runnable_schema

        # Repositories installed before NuGet.config became consumer-owned receive the
        # routing correction once, but only while their managed copy is unmodified.
        legacy_nuget = nuget_text.replace(
            '<package pattern="*" />',
            '<package pattern="Microsoft.*" />\n      <package pattern="System.*" />',
        ).encode("utf-8")
        nuget_config.write_bytes(legacy_nuget)
        state_path = target / ".program-kit/managed.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["files"]["NuGet.config"] = {
            "ownership": "managed",
            "installedHash": hashlib.sha256(legacy_nuget).hexdigest(),
            "templateHash": hashlib.sha256(legacy_nuget).hexdigest(),
        }
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        ownership_migrated = run("--target", str(target), *approvals)
        assert ownership_migrated.returncode == 0, ownership_migrated.stderr
        assert "  ~ NuGet.config" in ownership_migrated.stdout
        assert nuget_config.read_text(encoding="utf-8") == nuget_text
        migrated_state = json.loads(state_path.read_text(encoding="utf-8"))
        assert migrated_state["files"]["NuGet.config"]["ownership"] == "scaffold"

        consumer_nuget = nuget_text.replace(
            "  </packageSources>",
            '    <add key="Consumer Feed" value="https://packages.example.invalid/v3/index.json" />\n  </packageSources>',
        ).replace(
            "  </packageSourceMapping>",
            '    <packageSource key="Consumer Feed">\n      <package pattern="Consumer.*" />\n    </packageSource>\n  </packageSourceMapping>',
        )
        nuget_config.write_text(consumer_nuget, encoding="utf-8")
        consumer_preserved = run("--target", str(target), *approvals)
        assert consumer_preserved.returncode == 0, consumer_preserved.stderr
        assert nuget_config.read_text(encoding="utf-8") == consumer_nuget

        unsafe_nuget = consumer_nuget.replace(
            '<package pattern="Consumer.*" />', '<package pattern="*" />'
        )
        nuget_config.write_text(unsafe_nuget, encoding="utf-8")
        unsafe_rejected = run("--target", str(target), *approvals)
        assert unsafe_rejected.returncode == 2, unsafe_rejected.stderr
        assert "must use namespace-specific patterns" in unsafe_rejected.stdout
        assert nuget_config.read_text(encoding="utf-8") == unsafe_nuget
        nuget_config.write_bytes(
            (ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/NuGet.config").read_bytes()
        )

        obsolete_content = b"managed by the previous Program Kit\n"
        state_path = target / ".program-kit/managed.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        for relative in (
            ".program-kit/application-bundle.schema.json",
            "eng/program-kit/create_application_bundle.py",
        ):
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(obsolete_content)
            state["files"][relative] = {
                "ownership": "managed",
                "installedHash": hashlib.sha256(obsolete_content).hexdigest(),
                "templateHash": hashlib.sha256(obsolete_content).hexdigest(),
            }
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        upgraded = run("--target", str(target), *approvals)
        assert upgraded.returncode == 0, upgraded.stderr
        assert not (target / ".program-kit/application-bundle.schema.json").exists()
        assert not (target / "eng/program-kit/create_application_bundle.py").exists()

        clean = run("--target", str(target), "--profile-selected", "--check")
        assert clean.returncode == 0, clean.stderr

        managed = target / "eng/program-kit/ProgramKit.Build.props"
        managed.write_text(managed.read_text(encoding="utf-8") + "<!-- consumer edit -->\n", encoding="utf-8")
        conflicted = run("--target", str(target), *approvals)
        assert conflicted.returncode == 2, conflicted.stderr
        assert "consumer edit" in managed.read_text(encoding="utf-8")

        obsolete_conflict = target / "obsolete-conflict"
        installed_conflict = run("--target", str(obsolete_conflict), *approvals)
        assert installed_conflict.returncode == 0, installed_conflict.stderr
        old_path = obsolete_conflict / "eng/program-kit/create_application_bundle.py"
        old_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.write_text("consumer-owned historical tool\n", encoding="utf-8")
        conflict_state_path = obsolete_conflict / ".program-kit/managed.json"
        conflict_state = json.loads(conflict_state_path.read_text(encoding="utf-8"))
        conflict_state["files"]["eng/program-kit/create_application_bundle.py"] = {
            "ownership": "managed",
            "installedHash": "0" * 64,
            "templateHash": "0" * 64,
        }
        conflict_state_path.write_text(json.dumps(conflict_state, indent=2) + "\n", encoding="utf-8")
        preserved = run("--target", str(obsolete_conflict), *approvals)
        assert preserved.returncode == 2, preserved.stderr
        assert old_path.read_text(encoding="utf-8") == "consumer-owned historical tool\n"

        browser_target = target / "browser-consumer"
        design = browser_target / "docs/initial-design.md"
        design.parent.mkdir(parents=True)
        design.write_text("# Design\n\nA React browser UI calls authenticated HTTP features.\n", encoding="utf-8")
        browser_installed = run("--target", str(browser_target), *approvals)
        assert browser_installed.returncode == 0, browser_installed.stderr
        browser_state = json.loads((browser_target / ".program-kit/managed.json").read_text(encoding="utf-8"))
        assert browser_state["webProfile"] == "bff-cookie"
        assert browser_state["webProfileContract"] == "bff-cookie-v1"
        assert browser_state["webThreatModel"] == "program-kit-web-threat-model-v1"
        assert browser_state["webSecurityEvidence"] == "program-kit-web-security-evidence-v1"
        bff_settings = json.loads((browser_target / "hostsettings.json").read_text(encoding="utf-8"))
        assert "Web" not in bff_settings["ProgramKit"]
        bff_shell = json.loads(
            (browser_target / ".program-kit/web-profile.shells.json").read_text(encoding="utf-8")
        )["CShells"]["Shells"]["default"]
        assert "ProgramKit.Authentication.BffCookie" in bff_shell["Features"]
        assert "ProgramKit.Authentication.SpaPkce" not in bff_shell["Features"]
        assert bff_shell["Configuration"]["ProgramKit"]["Web"]["ClientId"] == "program-kit-bff"
        assert (browser_target / "deploy/keycloak/program-kit-realm.json").is_file()
        bff_realm = json.loads(
            (browser_target / "deploy/keycloak/program-kit-realm.json").read_text(encoding="utf-8")
        )
        bff_client_ids = [client["clientId"] for client in bff_realm["clients"]]
        assert bff_client_ids == ["program-kit-api", "program-kit-bff"]
        bff_scope_names = {scope["name"] for scope in bff_realm["clientScopes"]}
        assert {
            "basic", "profile", "roles", "web-origins", "acr", "offline_access", "program-kit-api"
        }.issubset(bff_scope_names)
        bff_client = bff_realm["clients"][1]
        assert set(bff_client["defaultClientScopes"]).issubset(bff_scope_names)
        assert set(bff_client["optionalClientScopes"]).issubset(bff_scope_names)
        assert bff_client["attributes"]["post.logout.redirect.uris"] == (
            "http://localhost:5000/signout-callback-oidc"
        )
        assert (browser_target / "eng/program-kit/compose_topology.py").is_file()
        assert (browser_target / "eng/program-kit/web/bff-session.ts").is_file()
        assert (browser_target / "eng/program-kit/web/tests/bff-session.spec.ts").is_file()
        bff_contract = json.loads(
            (browser_target / "eng/program-kit/web/web-contract.json").read_text(encoding="utf-8")
        )
        authenticated_body = bff_contract["routes"]["user"]["success"]["authenticatedBody"]
        assert authenticated_body["issuer"] == "non-empty-validated-uri-string"
        assert authenticated_body["subject"] == "non-empty-string"
        assert bff_contract["routes"]["user"]["success"]["invalidIdentity"] == {
            "status": 401,
            "code": "authentication_identity_invalid",
            "localSession": "cleared",
        }
        bff_compose = (browser_target / "deploy/compose.application.yml").read_text(encoding="utf-8")
        assert "CShells__Shells__default__Configuration__ProgramKit__Web__ClientSecret" in bff_compose
        assert "CShells__Shells__default__Configuration__ProgramKit__Web__BackchannelAuthority" in bff_compose
        assert "program-kit-identity:8080/realms/program-kit" in bff_compose
        assert "extra_hosts" not in bff_compose and "localhost:host-gateway" not in bff_compose
        assert (browser_target / "eng/program-kit/web/package-lock.json").is_file()
        assert (browser_target / ".program-kit/security/web-security-evidence.json").is_file()
        assert (browser_target / "docs/architecture/program-kit/web-security-threat-model.md").is_file()

        # Valid consumer extension-point edits do not become Program Kit state drift.
        consumer_shells_path = browser_target / "shells.json"
        consumer_shells = json.loads(consumer_shells_path.read_text(encoding="utf-8"))
        consumer_shells["CShells"]["Shells"]["default"]["Features"]["PriceCalculator.Api"] = {}
        consumer_shells_path.write_text(json.dumps(consumer_shells, indent=2) + "\n", encoding="utf-8")
        consumer_hostsettings_path = browser_target / "hostsettings.json"
        consumer_hostsettings = json.loads(consumer_hostsettings_path.read_text(encoding="utf-8"))
        consumer_hostsettings["PriceCalculator"] = {"VerificationMode": "strict"}
        consumer_hostsettings_path.write_text(
            json.dumps(consumer_hostsettings, indent=2) + "\n", encoding="utf-8"
        )
        openapi_registry_path = browser_target / ".program-kit/openapi-contracts.json"
        openapi_registry = json.loads(openapi_registry_path.read_text(encoding="utf-8"))
        openapi_registry["contracts"] = [
            {
                "id": "price-calculator-api",
                "shell": "default",
                "features": ["PriceCalculator.Api"],
            }
        ]
        openapi_registry_path.write_text(
            json.dumps(openapi_registry, indent=2) + "\n", encoding="utf-8"
        )
        consumer_extension_check = run(
            "--target",
            str(browser_target),
            "--profile-selected",
            "--check",
            "--web-profile",
            "bff-cookie",
            "--persistence-profile",
            "none",
        )
        assert consumer_extension_check.returncode == 0, consumer_extension_check.stderr
        assert "created: 0" in consumer_extension_check.stdout
        assert "updated: 0" in consumer_extension_check.stdout
        assert "conflicts: 0" in consumer_extension_check.stdout
        assert "state changed: no" in consumer_extension_check.stdout
        permission_spec_relative = "eng/program-kit/web/tests/authentication.spec.ts"
        permission_spec = browser_target / permission_spec_relative
        current_permission_contract = permission_spec.read_bytes()
        assert b"expect(authorizedResponse.ok()).toBeTruthy();" in current_permission_contract
        assert b"expect(deniedResponse.status()).toBe(403);" in current_permission_contract

        # An unchanged managed file installed by 0.8.11 must upgrade in place. Consumers must not
        # need to edit the managed browser test to accept a legitimate 204 permission response.
        legacy_permission_contract = current_permission_contract.replace(
            b"  const authorizedResponse = await authorized.request.get(path);\n"
            b"  expect(authorizedResponse.ok()).toBeTruthy();",
            b"  expect((await authorized.request.get(path)).status()).toBe(200);",
        )
        assert legacy_permission_contract != current_permission_contract
        permission_spec.write_bytes(legacy_permission_contract)
        browser_state_path = browser_target / ".program-kit/managed.json"
        browser_state = json.loads(browser_state_path.read_text(encoding="utf-8"))
        legacy_hash = hashlib.sha256(legacy_permission_contract).hexdigest()
        browser_state["schemaVersion"] = 1
        for record in browser_state["files"].values():
            for name in ("baselineHash", "contribution", "lastWrittenHash", "lifecycle", "sourceIdentity"):
                record.pop(name, None)
        browser_state["files"][permission_spec_relative]["installedHash"] = legacy_hash
        browser_state["files"][permission_spec_relative]["templateHash"] = legacy_hash
        browser_state_path.write_text(json.dumps(browser_state, indent=2) + "\n", encoding="utf-8")
        browser_upgraded = run("--target", str(browser_target), *approvals)
        assert browser_upgraded.returncode == 0, browser_upgraded.stderr
        assert f"  ~ {permission_spec_relative}" in browser_upgraded.stdout
        assert permission_spec.read_bytes() == current_permission_contract

        mentioned_alternative = target / "mentioned-spa-alternative"
        alternative_design = mentioned_alternative / "INITIAL_DESIGN.md"
        alternative_design.parent.mkdir(parents=True)
        alternative_design.write_text(
            "# Design\n\nA React browser UI; spa-pkce-v1 is an alternative, not the selected design.\n",
            encoding="utf-8",
        )
        alternative_installed = run("--target", str(mentioned_alternative), *approvals)
        assert alternative_installed.returncode == 0, alternative_installed.stderr
        alternative_state = json.loads(
            (mentioned_alternative / ".program-kit/managed.json").read_text(encoding="utf-8")
        )
        assert alternative_state["webProfile"] == "bff-cookie"

        spa_target = target / "explicit-spa-consumer"
        spa_installed = run("--target", str(spa_target), *approvals, "--web-profile", "spa-pkce")
        assert spa_installed.returncode == 0, spa_installed.stderr
        spa_state = json.loads((spa_target / ".program-kit/managed.json").read_text(encoding="utf-8"))
        assert spa_state["webProfile"] == "spa-pkce"
        assert spa_state["webThreatModel"] == "program-kit-web-threat-model-v1"
        assert spa_state["webSecurityEvidence"] == "program-kit-web-security-evidence-v1"
        spa_settings = json.loads((spa_target / "hostsettings.json").read_text(encoding="utf-8"))
        assert "Web" not in spa_settings["ProgramKit"]
        spa_shell = json.loads(
            (spa_target / ".program-kit/web-profile.shells.json").read_text(encoding="utf-8")
        )["CShells"]["Shells"]["default"]
        assert "ProgramKit.Authentication.SpaPkce" in spa_shell["Features"]
        assert "ProgramKit.Authentication.BffCookie" not in spa_shell["Features"]
        spa_configuration_path = spa_target / ".program-kit/spa-pkce.json"
        spa_configuration = json.loads(spa_configuration_path.read_text(encoding="utf-8"))
        assert spa_state["files"][".program-kit/spa-pkce.json"]["ownership"] == "configuration"
        realm = json.loads((spa_target / "deploy/keycloak/program-kit-realm.json").read_text(encoding="utf-8"))
        assert not any(client["clientId"] == "program-kit-bff" for client in realm["clients"])
        spa_client = next(client for client in realm["clients"] if client["clientId"] == "program-kit-spa")
        assert set(spa_client["defaultClientScopes"]).issubset(
            {scope["name"] for scope in realm["clientScopes"]}
        )
        assert spa_client["publicClient"] is True and "secret" not in spa_client
        assert spa_client["redirectUris"] == [
            "http://localhost:5173/auth/callback",
            "http://localhost:5173/auth/renew-callback",
        ]
        assert spa_client["attributes"]["post.logout.redirect.uris"] == "http://localhost:5173/signed-out"
        assert "postLogoutRedirectUris" not in spa_client
        assert not any("*" in uri for uri in spa_client["redirectUris"])
        compose = (spa_target / "deploy/compose.application.yml").read_text(encoding="utf-8")
        assert "ClientSecret" not in compose and "local-program-kit-secret" not in compose
        assert "CShells__Shells__default__Configuration__ProgramKit__Web__BackchannelAuthority" in compose
        assert "program-kit-identity:8080/realms/program-kit" in compose
        assert "extra_hosts" not in compose and "localhost:host-gateway" not in compose
        playwright = (spa_target / "eng/program-kit/web/playwright.config.ts").read_text(encoding="utf-8")
        assert "trace: 'off'" in playwright and "screenshot: 'off'" in playwright and "video: 'off'" in playwright
        verifier = subprocess.run(
            [sys.executable, str(spa_target / "eng/program-kit/verify_spa_profile.py"),
             "--repository", str(spa_target)],
            capture_output=True,
            text=True,
        )
        assert verifier.returncode == 0, verifier.stderr

        spa_configuration["applicationOrigin"] = "http://localhost:4173"
        spa_configuration["redirectUris"] = [
            "http://localhost:4173/auth/callback",
            "http://localhost:4173/auth/renew-callback",
        ]
        spa_configuration["postLogoutRedirectUris"] = ["http://localhost:4173/signed-out"]
        spa_configuration["session"]["idleMinutes"] = 20
        spa_configuration_path.write_text(json.dumps(spa_configuration, indent=2) + "\n", encoding="utf-8")
        customized = run("--target", str(spa_target), *approvals, "--web-profile", "spa-pkce")
        assert customized.returncode == 0, customized.stderr
        customized_realm = json.loads(
            (spa_target / "deploy/keycloak/program-kit-realm.json").read_text(encoding="utf-8")
        )
        customized_client = next(
            client for client in customized_realm["clients"] if client["clientId"] == "program-kit-spa"
        )
        assert [client["clientId"] for client in customized_realm["clients"]] == [
            "program-kit-api",
            "program-kit-spa",
        ]
        assert customized_client["redirectUris"] == spa_configuration["redirectUris"]
        assert customized_client["attributes"]["post.logout.redirect.uris"] == "http://localhost:4173/signed-out"
        assert "postLogoutRedirectUris" not in customized_client
        assert customized_realm["ssoSessionIdleTimeout"] == 1200
        customized_shell = json.loads(
            (spa_target / ".program-kit/web-profile.shells.json").read_text(encoding="utf-8")
        )
        assert (
            customized_shell["CShells"]["Shells"]["default"]["Configuration"]["ProgramKit"]["Web"]
            ["AllowedOrigins"]
            == ["http://localhost:4173"]
        )
        clean_spa = run(
            "--target", str(spa_target), "--profile-selected", "--check", "--web-profile", "spa-pkce"
        )
        assert clean_spa.returncode == 0, clean_spa.stderr

        invalid_spa = target / "invalid-spa-consumer"
        invalid_spa.mkdir()
        invalid_configuration = dict(spa_configuration)
        invalid_configuration["redirectUris"] = ["http://localhost:4173/*"]
        invalid_configuration_path = invalid_spa / ".program-kit/spa-pkce.json"
        invalid_configuration_path.parent.mkdir()
        invalid_configuration_path.write_text(
            json.dumps(invalid_configuration, indent=2) + "\n", encoding="utf-8"
        )
        wildcard_rejected = run(
            "--target", str(invalid_spa), *approvals, "--web-profile", "spa-pkce"
        )
        assert wildcard_rejected.returncode != 0 and "without wildcards" in wildcard_rejected.stderr
        assert not (invalid_spa / "deploy/keycloak/program-kit-realm.json").exists()

        override_target = target / "explicit-local-sdk-override"
        override_decisions = override_target / "docs/architecture/bootstrap-decisions.json"
        override_decisions.parent.mkdir(parents=True)
        override_decisions.write_text(
            json.dumps(
                {
                    "toolchain": {
                        "source": "override",
                        "pins": {"dotnet-sdk": "9.0.100"},
                        "override_reason": "The user explicitly retained the local SDK",
                    },
                    "overrides": [
                        {
                            "id": "managed-toolchain-version",
                            "decision": "Retain .NET SDK 9.0.100",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        override_installed = run("--target", str(override_target), *approvals)
        assert override_installed.returncode == 0, override_installed.stderr
        overridden_global = json.loads(
            (override_target / "global.json").read_text(encoding="utf-8")
        )
        assert overridden_global["sdk"]["version"] == "9.0.100"
        override_state = json.loads(
            (override_target / ".program-kit/managed.json").read_text(encoding="utf-8")
        )
        assert override_state["dotnetSdk"] == "9.0.100"
        assert override_state["dotnetSdkSource"] == "override"

        invalid_override = target / "invalid-local-sdk-override"
        invalid_decisions = invalid_override / "docs/architecture/bootstrap-decisions.json"
        invalid_decisions.parent.mkdir(parents=True)
        invalid_decisions.write_text(
            json.dumps(
                {
                    "toolchain": {
                        "source": "override",
                        "pins": {"dotnet-sdk": "9.0.100"},
                        "override_reason": "",
                    },
                    "overrides": [],
                }
            ),
            encoding="utf-8",
        )
        invalid_result = run("--target", str(invalid_override), *approvals)
        assert invalid_result.returncode != 0
        assert "override is incomplete" in invalid_result.stderr

        # Every directed transition converges to only the selected profile contribution.
        for source_profile in ("none", "bff-cookie", "spa-pkce"):
            for destination_profile in ("none", "bff-cookie", "spa-pkce"):
                if source_profile == destination_profile:
                    continue
                transition = target / f"transition-{source_profile}-to-{destination_profile}"
                source_result = run(
                    "--target", str(transition), *approvals, "--web-profile", source_profile
                )
                assert source_result.returncode == 0, source_result.stderr
                assert_profile(transition, source_profile)
                destination_result = run(
                    "--target", str(transition), *approvals, "--web-profile", destination_profile
                )
                assert destination_result.returncode == 0, destination_result.stderr
                assert_profile(transition, destination_profile)
                converged = run(
                    "--target",
                    str(transition),
                    "--profile-selected",
                    "--check",
                    "--web-profile",
                    destination_profile,
                )
                assert converged.returncode == 0, converged.stderr

        # Structured field retirement removes authenticated legacy profile settings while
        # preserving the rest of scaffold-owned hostsettings across either profile direction.
        legacy_bff_to_spa = target / "legacy-hostsettings-bff-to-spa"
        assert run(
            "--target", str(legacy_bff_to_spa), *approvals, "--web-profile", "bff-cookie"
        ).returncode == 0
        seed_legacy_root_web_settings(legacy_bff_to_spa, "bff")
        migrated_to_spa = run(
            "--target", str(legacy_bff_to_spa), *approvals, "--web-profile", "spa-pkce"
        )
        assert migrated_to_spa.returncode == 0, migrated_to_spa.stderr
        assert "Web" not in json.loads(
            (legacy_bff_to_spa / "hostsettings.json").read_text(encoding="utf-8")
        )["ProgramKit"]
        assert_profile(legacy_bff_to_spa, "spa-pkce")

        legacy_spa_to_bff = target / "legacy-hostsettings-spa-to-bff"
        assert run(
            "--target", str(legacy_spa_to_bff), *approvals, "--web-profile", "spa-pkce"
        ).returncode == 0
        seed_legacy_root_web_settings(legacy_spa_to_bff, "spa")
        migrated_to_bff = run(
            "--target", str(legacy_spa_to_bff), *approvals, "--web-profile", "bff-cookie"
        )
        assert migrated_to_bff.returncode == 0, migrated_to_bff.stderr
        assert "Web" not in json.loads(
            (legacy_spa_to_bff / "hostsettings.json").read_text(encoding="utf-8")
        )["ProgramKit"]
        assert_profile(legacy_spa_to_bff, "bff-cookie")

        customized_legacy = target / "customized-legacy-hostsettings"
        assert run(
            "--target", str(customized_legacy), *approvals, "--web-profile", "bff-cookie"
        ).returncode == 0
        seed_legacy_root_web_settings(customized_legacy, "bff")
        customized_hostsettings_path = customized_legacy / "hostsettings.json"
        customized_hostsettings = json.loads(
            customized_hostsettings_path.read_text(encoding="utf-8")
        )
        customized_hostsettings["ProgramKit"]["Web"]["Authority"] = "https://identity.example.test"
        customized_hostsettings_path.write_text(
            json.dumps(customized_hostsettings, indent=2) + "\n", encoding="utf-8"
        )
        before_structured_conflict = snapshot(customized_legacy)
        structured_conflict = run(
            "--target", str(customized_legacy), *approvals, "--web-profile", "bff-cookie"
        )
        assert structured_conflict.returncode == 2, structured_conflict.stderr
        assert "migrate its settings explicitly before removal" in structured_conflict.stdout
        assert snapshot(customized_legacy) == before_structured_conflict

        # A versioned migration removes SPA files that 0.8.11 could lose from state while leaving
        # them on disk. Only the exact governed bytes are eligible for retirement.
        migration_catalog = json.loads(
            (ROOT / "extensions/program-kit-dotnet/templates/dotnet/migrations.json")
            .read_text(encoding="utf-8")
        )
        residue_migration = next(
            item for item in migration_catalog["migrations"]
            if item["id"] == "0.9.0-retire-lost-spa-profile-residue"
        )
        spa_template_root = ROOT / "extensions/program-kit-dotnet/templates/dotnet/web-profiles/spa-pkce"
        script_source = ROOT / "extensions/program-kit-dotnet/scripts/spa_profile.py"

        def seed_lost_spa_residue(repository: Path) -> None:
            for item in residue_migration["retire"]:
                relative = item["path"]
                source = script_source if relative == "eng/program-kit/verify_spa_profile.py" else spa_template_root / relative
                destination = repository / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
            managed_path = repository / ".program-kit/managed.json"
            managed = json.loads(managed_path.read_text(encoding="utf-8"))
            managed["programKitVersion"] = "0.8.11"
            managed["appliedMigrations"] = [
                value for value in managed.get("appliedMigrations", [])
                if value != residue_migration["id"]
            ]
            managed_path.write_text(json.dumps(managed, indent=2) + "\n", encoding="utf-8")

        legacy_residue = target / "legacy-lost-spa-residue"
        legacy_installed = run(
            "--target", str(legacy_residue), *approvals, "--web-profile", "bff-cookie"
        )
        assert legacy_installed.returncode == 0, legacy_installed.stderr
        seed_lost_spa_residue(legacy_residue)
        migrated = run(
            "--target", str(legacy_residue), *approvals, "--web-profile", "bff-cookie"
        )
        assert migrated.returncode == 0, migrated.stderr
        for item in residue_migration["retire"]:
            assert not (legacy_residue / item["path"]).exists(), item["path"]

        modified_residue = target / "modified-lost-spa-residue"
        modified_installed = run(
            "--target", str(modified_residue), *approvals, "--web-profile", "bff-cookie"
        )
        assert modified_installed.returncode == 0, modified_installed.stderr
        seed_lost_spa_residue(modified_residue)
        modified_path = modified_residue / ".program-kit/spa-pkce.json"
        modified_path.write_text(modified_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        before_migration_conflict = snapshot(modified_residue)
        blocked_migration = run(
            "--target", str(modified_residue), *approvals, "--web-profile", "bff-cookie"
        )
        assert blocked_migration.returncode == 2, blocked_migration.stderr
        assert snapshot(modified_residue) == before_migration_conflict

        # A consumer-modified retiring contribution blocks the complete plan before any mutation.
        conflict_transition = target / "transition-conflict-zero-mutation"
        installed_spa = run(
            "--target", str(conflict_transition), *approvals, "--web-profile", "spa-pkce"
        )
        assert installed_spa.returncode == 0, installed_spa.stderr
        spa_input = conflict_transition / ".program-kit/spa-pkce.json"
        spa_input.write_text(spa_input.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        before_conflict = snapshot(conflict_transition)
        blocked_transition = run(
            "--target", str(conflict_transition), *approvals, "--web-profile", "bff-cookie"
        )
        assert blocked_transition.returncode == 2, blocked_transition.stderr
        assert snapshot(conflict_transition) == before_conflict

        # An injected mid-apply failure rolls every file back; a clean retry then converges.
        interrupted = target / "interrupted-transaction"
        installed_bff = run(
            "--target", str(interrupted), *approvals, "--web-profile", "bff-cookie"
        )
        assert installed_bff.returncode == 0, installed_bff.stderr
        before_interruption = snapshot(interrupted)
        injected_environment = os.environ.copy()
        injected_environment["PROGRAMKIT_TEST_SYNC_FAIL_AFTER_ACTION"] = "2"
        failed_apply = run(
            "--target",
            str(interrupted),
            *approvals,
            "--web-profile",
            "spa-pkce",
            environment=injected_environment,
        )
        assert failed_apply.returncode == 2, failed_apply.stderr
        assert "rolled back" in failed_apply.stderr
        assert snapshot(interrupted) == before_interruption
        recovered_apply = run(
            "--target", str(interrupted), *approvals, "--web-profile", "spa-pkce"
        )
        assert recovered_apply.returncode == 0, recovered_apply.stderr
        assert_profile(interrupted, "spa-pkce")

    print("Program Kit .NET scaffold lifecycle passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
