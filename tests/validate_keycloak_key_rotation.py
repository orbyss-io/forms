from __future__ import annotations

import base64
import json
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import validate_keycloak_advanced_browser as advanced
import validate_keycloak_realm_import as realm_import
import validate_spa_browser_flow as spa


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "extensions/program-kit-dotnet/templates/dotnet"
KEY_PROVIDER_TYPE = "org.keycloak.keys.KeyProvider"


def decode_header(token: str) -> dict:
    encoded = token.split(".", 1)[0]
    return json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))


def token_request(identity_origin: str) -> str:
    request = urllib.request.Request(
        f"{identity_origin}/realms/program-kit/protocol/openid-connect/token",
        data=urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": "program-kit-machine",
                "client_secret": "local-machine-secret",
            }
        ).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read())
    token = payload.get("access_token")
    if not isinstance(token, str):
        raise AssertionError(f"Keycloak did not issue a machine access token: {payload}")
    return token


def jwks(identity_origin: str) -> dict[str, dict]:
    with urllib.request.urlopen(
        f"{identity_origin}/realms/program-kit/protocol/openid-connect/certs", timeout=15
    ) as response:
        payload = json.loads(response.read())
    return {
        key["kid"]: key
        for key in payload.get("keys", [])
        if isinstance(key, dict) and isinstance(key.get("kid"), str)
    }


def main() -> int:
    if shutil.which("docker") is None:
        raise AssertionError("Key-rotation acceptance requires Docker")
    identity_port = spa.free_port()
    health_port = spa.free_port()
    identity_origin = f"http://localhost:{identity_port}"
    container = f"program-kit-key-rotation-{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory(prefix="program-kit-key-rotation-") as value:
        fixture = Path(value)
        realm_path = fixture / "program-kit-realm.json"
        realm = json.loads(realm_import.rendered_realm("bff-cookie"))
        realm_path.write_text(json.dumps(realm, indent=2) + "\n", encoding="utf-8")
        started = subprocess.run(
            [
                "docker", "run", "--detach", "--name", container,
                "--publish", f"127.0.0.1:{identity_port}:8080",
                "--publish", f"127.0.0.1:{health_port}:9000",
                "--env", "KC_BOOTSTRAP_ADMIN_USERNAME=fixture-admin",
                "--env", "KC_BOOTSTRAP_ADMIN_PASSWORD=ephemeral-advanced-only",
                "--env", f"KC_HOSTNAME={identity_origin}",
                "--volume", f"{realm_path.resolve()}:/opt/keycloak/data/import/program-kit-realm.json:ro",
                spa.image_reference(), "start-dev", "--import-realm", "--health-enabled=true",
            ],
            capture_output=True,
            text=True,
        )
        if started.returncode != 0:
            raise AssertionError(f"Could not start key-rotation Keycloak fixture: {started.stderr}")
        try:
            spa.wait_keycloak(container, health_port)
            old_token = token_request(identity_origin)
            old_kid = decode_header(old_token).get("kid")
            before = jwks(identity_origin)
            if not isinstance(old_kid, str) or old_kid not in before:
                raise AssertionError("The original active signing key was absent from JWKS")

            token = advanced.admin_token(identity_origin)
            realm_representation = advanced.admin_request(identity_origin, token, "GET", "")
            if not isinstance(realm_representation, dict) or not realm_representation.get("id"):
                raise AssertionError("Could not resolve the imported realm ID")
            parent_id = str(realm_representation["id"])
            query = urllib.parse.urlencode({"parent": parent_id, "type": KEY_PROVIDER_TYPE})
            components = advanced.admin_request(
                identity_origin, token, "GET", f"components?{query}"
            )
            if not isinstance(components, list):
                raise AssertionError("Keycloak did not return its key-provider components")
            old_signers = [
                item
                for item in components
                if item.get("providerId") == "rsa-generated"
                and "RS256" in item.get("config", {}).get("algorithm", ["RS256"])
            ]
            if not old_signers:
                raise AssertionError(f"Could not identify the original RSA signer: {components}")

            advanced.admin_request(
                identity_origin,
                token,
                "POST",
                "components",
                {
                    "name": "program-kit-rotated-rsa",
                    "providerId": "rsa-generated",
                    "providerType": KEY_PROVIDER_TYPE,
                    "parentId": parent_id,
                    "config": {
                        "priority": ["200"],
                        "enabled": ["true"],
                        "active": ["true"],
                        "algorithm": ["RS256"],
                        "keySize": ["2048"],
                    },
                },
            )
            new_token = token_request(identity_origin)
            new_kid = decode_header(new_token).get("kid")
            overlap = jwks(identity_origin)
            if not isinstance(new_kid, str) or new_kid == old_kid:
                raise AssertionError("Adding the higher-priority provider did not rotate the active key")
            if old_kid not in overlap or new_kid not in overlap:
                raise AssertionError("The overlap JWKS did not publish both old and new signing keys")

            token = advanced.admin_token(identity_origin)
            for component in old_signers:
                advanced.admin_request(
                    identity_origin, token, "DELETE", f"components/{component['id']}"
                )
            retired = jwks(identity_origin)
            if old_kid in retired or new_kid not in retired:
                raise AssertionError("Retirement did not remove only the old signing key from JWKS")
            final_token = token_request(identity_origin)
            if decode_header(final_token).get("kid") != new_kid:
                raise AssertionError("Keycloak stopped signing with the promoted key after retirement")
        except Exception as error:
            logs = subprocess.run(
                ["docker", "logs", container], capture_output=True, text=True, check=False
            )
            raise AssertionError(f"{error}\nKeycloak output:\n{logs.stdout[-12000:]}{logs.stderr[-12000:]}") from error
        finally:
            subprocess.run(["docker", "rm", "--force", container], capture_output=True, check=False)
    print("Keycloak completed active-key promotion, overlap publication, and old-key retirement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
