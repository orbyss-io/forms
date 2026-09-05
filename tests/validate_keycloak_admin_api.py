from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import validate_keycloak_advanced_browser as advanced
import validate_spa_browser_flow as spa


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "extensions/program-kit-dotnet/templates/dotnet"
PROJECT = ROOT / "tests/dotnet/ProgramKit.Identity.Keycloak.Admin.Probe/ProgramKit.Identity.Keycloak.Admin.Probe.csproj"
ADMIN_SECRET = "disposable-keycloak-admin-probe-secret"


def configure_service_account(identity_origin: str) -> None:
    token = advanced.admin_token(identity_origin)
    advanced.admin_request(
        identity_origin,
        token,
        "POST",
        "clients",
        {
            "clientId": "program-kit-admin-probe",
            "name": "Disposable Program Kit Admin API acceptance",
            "enabled": True,
            "publicClient": False,
            "serviceAccountsEnabled": True,
            "standardFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "secret": ADMIN_SECRET,
            "protocol": "openid-connect",
        },
    )
    clients = advanced.admin_request(
        identity_origin, token, "GET", "clients?clientId=program-kit-admin-probe"
    )
    if not isinstance(clients, list) or len(clients) != 1:
        raise AssertionError(f"Could not resolve the disposable admin client: {clients}")
    client_id = clients[0]["id"]
    service_user = advanced.admin_request(
        identity_origin, token, "GET", f"clients/{client_id}/service-account-user"
    )
    management_clients = advanced.admin_request(
        identity_origin, token, "GET", "clients?clientId=realm-management"
    )
    if not isinstance(service_user, dict) or not isinstance(management_clients, list) or len(management_clients) != 1:
        raise AssertionError("Could not resolve Keycloak realm-management roles")
    management_id = management_clients[0]["id"]
    roles = advanced.admin_request(
        identity_origin, token, "GET", f"clients/{management_id}/roles"
    )
    required = {
        "manage-users",
        "query-users",
        "view-users",
        "manage-clients",
        "query-clients",
        "view-clients",
        "manage-realm",
        "view-realm",
    }
    selected = [role for role in roles if role.get("name") in required]
    if {role.get("name") for role in selected} != required:
        raise AssertionError("The disposable realm did not expose the expected realm-management roles")
    advanced.admin_request(
        identity_origin,
        token,
        "POST",
        f"users/{service_user['id']}/role-mappings/clients/{management_id}",
        selected,
    )


def main() -> int:
    missing = [command for command in ("docker", "dotnet") if shutil.which(command) is None]
    if missing:
        raise AssertionError("Keycloak Admin REST acceptance requires: " + ", ".join(missing))
    identity_port = spa.free_port()
    health_port = spa.free_port()
    identity_origin = f"http://localhost:{identity_port}"
    container = f"program-kit-admin-api-{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory(prefix="program-kit-admin-api-") as value:
        fixture = Path(value)
        realm = fixture / "program-kit-realm.json"
        advanced.render_realm(realm, "http://localhost:5173", identity_origin)
        started = subprocess.run(
            [
                "docker", "run", "--detach", "--name", container,
                "--publish", f"127.0.0.1:{identity_port}:8080",
                "--publish", f"127.0.0.1:{health_port}:9000",
                "--env", "KC_BOOTSTRAP_ADMIN_USERNAME=fixture-admin",
                "--env", "KC_BOOTSTRAP_ADMIN_PASSWORD=ephemeral-advanced-only",
                "--env", f"KC_HOSTNAME={identity_origin}",
                "--volume", f"{realm.resolve()}:/opt/keycloak/data/import/program-kit-realm.json:ro",
                "--volume", f"{(TEMPLATE / 'web-profiles/common/deploy/keycloak/themes').resolve()}:/opt/keycloak/themes:ro",
                spa.image_reference(), "start-dev", "--import-realm", "--health-enabled=true",
            ],
            capture_output=True,
            text=True,
        )
        if started.returncode != 0:
            raise AssertionError(f"Could not start Keycloak Admin REST fixture: {started.stderr}")
        try:
            spa.wait_keycloak(container, health_port)
            configure_service_account(identity_origin)
            environment = os.environ.copy()
            environment["PROGRAM_KIT_KEYCLOAK_ADMIN_URL"] = identity_origin
            environment["PROGRAM_KIT_KEYCLOAK_ADMIN_SECRET"] = ADMIN_SECRET
            completed = subprocess.run(
                ["dotnet", "run", "--project", str(PROJECT), "--configuration", "Release"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if completed.returncode != 0:
                raise AssertionError(f"The public Keycloak Admin adapter probe failed:\n{completed.stdout}\n{completed.stderr}")
            print(completed.stdout.strip())
        except Exception as error:
            logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True, check=False)
            raise AssertionError(f"{error}\nKeycloak output:\n{logs.stdout[-12000:]}{logs.stderr[-12000:]}") from error
        finally:
            subprocess.run(["docker", "rm", "--force", container], capture_output=True, check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
