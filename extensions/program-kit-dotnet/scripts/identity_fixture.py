from __future__ import annotations

import json
from pathlib import Path

import spa_profile


REALM_PATH = "deploy/keycloak/program-kit-realm.json"
PROFILE_CLIENT_PATH = "identity-client.json"
PROTOCOL_SCOPES = {"openid"}
BFF_REQUESTED_SCOPES = {"openid", "profile", "offline_access", "program-kit-api"}
BFF_SIGNED_OUT_CALLBACK = "http://localhost:5000/signout-callback-oidc"
GOVERNED_LOGIN_THEME = "program-kit"


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def _client_ids(realm: dict) -> list[str]:
    clients = realm.get("clients")
    if not isinstance(clients, list) or not all(isinstance(client, dict) for client in clients):
        raise ValueError("PKW113 managed Keycloak realm clients must be objects")
    identifiers = [client.get("clientId") for client in clients]
    if not all(isinstance(identifier, str) and identifier for identifier in identifiers):
        raise ValueError("PKW113 every managed Keycloak client must have a non-empty clientId")
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("PKW113 managed Keycloak client identifiers must be unique")
    return identifiers


def _profile_client(template_root: Path, web_profile: str) -> dict:
    path = template_root / "web-profiles" / web_profile / PROFILE_CLIENT_PATH
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"PKW113 expected one profile client object in {path}")
    redirects = value.pop("postLogoutRedirectUris", None)
    if (
        not isinstance(redirects, list)
        or not redirects
        or any(not isinstance(item, str) or not item for item in redirects)
    ):
        raise ValueError(f"PKW113 profile client {path} must declare exact postLogoutRedirectUris")
    attributes = value.setdefault("attributes", {})
    if not isinstance(attributes, dict):
        raise ValueError(f"PKW113 profile client {path} attributes must be an object")
    attributes["post.logout.redirect.uris"] = "##".join(redirects)
    return value


def render_realm(
    source: bytes,
    template_root: Path,
    web_profile: str,
    spa_configuration: dict | None,
) -> bytes:
    realm = json.loads(source.decode("utf-8"))
    identifiers = _client_ids(realm)
    if identifiers != ["program-kit-api"]:
        raise ValueError(
            "PKW113 the profile-neutral Keycloak realm must contain only the bearer-only API client"
        )
    realm["clients"].append(_profile_client(template_root, web_profile))
    rendered = json_bytes(realm)
    if web_profile == "spa-pkce":
        if spa_configuration is None:
            raise ValueError("PKW113 the SPA identity fixture requires its typed configuration")
        rendered = spa_profile.render_realm(rendered, spa_configuration)
    validate_realm(rendered, web_profile, spa_configuration)
    return rendered


def validate_realm(
    content: bytes,
    web_profile: str,
    spa_configuration: dict | None,
) -> None:
    realm = json.loads(content.decode("utf-8"))
    if realm.get("loginTheme") != GOVERNED_LOGIN_THEME:
        raise ValueError(
            f"PKW113 the managed Keycloak realm must select the governed {GOVERNED_LOGIN_THEME!r} login theme"
        )
    identifiers = _client_ids(realm)
    if web_profile == "bff-cookie":
        audience = "program-kit-api"
        selected = "program-kit-bff"
    elif web_profile == "spa-pkce" and spa_configuration is not None:
        audience = spa_configuration["audience"]
        selected = spa_configuration["clientId"]
    else:
        raise ValueError(f"PKW113 unsupported identity-fixture profile {web_profile!r}")
    expected = [audience, selected]
    if identifiers != expected:
        raise ValueError(
            "PKW113 the selected-profile Keycloak fixture must contain exactly the bearer-only "
            f"API client and the selected {web_profile} client; expected {expected!r}, got {identifiers!r}"
        )
    api = realm["clients"][0]
    if api.get("bearerOnly") is not True:
        raise ValueError("PKW113 the API audience must remain a bearer-only Keycloak client")
    profile_client = realm["clients"][1]
    client_scopes = realm.get("clientScopes")
    if not isinstance(client_scopes, list) or not all(
        isinstance(scope, dict) and isinstance(scope.get("name"), str) and scope["name"]
        for scope in client_scopes
    ):
        raise ValueError("PKW113 every managed Keycloak client scope must have a non-empty name")
    scope_names = [scope["name"] for scope in client_scopes]
    if len(scope_names) != len(set(scope_names)):
        raise ValueError("PKW113 managed Keycloak client scope names must be unique")
    referenced = {
        str(scope)
        for client in realm["clients"]
        for key in ("defaultClientScopes", "optionalClientScopes")
        for scope in client.get(key, [])
    }
    requested = (
        BFF_REQUESTED_SCOPES
        if web_profile == "bff-cookie"
        else set(spa_configuration["scopes"])
    )
    missing = sorted((referenced | requested) - set(scope_names) - PROTOCOL_SCOPES)
    if missing:
        raise ValueError(
            "PKW113 the managed Keycloak realm does not materialize referenced/requested client "
            "scopes: " + ", ".join(missing)
        )
    if "postLogoutRedirectUris" in profile_client:
        raise ValueError(
            "PKW113 Keycloak ClientRepresentation does not accept postLogoutRedirectUris; "
            "use the post.logout.redirect.uris client attribute"
        )
    logout_attribute = profile_client.get("attributes", {}).get("post.logout.redirect.uris")
    if not isinstance(logout_attribute, str) or not logout_attribute:
        raise ValueError("PKW113 the selected client has no exact Keycloak post-logout redirect attribute")
    if web_profile == "bff-cookie":
        if profile_client.get("publicClient") is not False or not profile_client.get("secret"):
            raise ValueError("PKW113 the selected BFF client must remain confidential")
        if logout_attribute != BFF_SIGNED_OUT_CALLBACK:
            raise ValueError(
                "PKW113 the BFF provider logout must return through the OIDC signed-out callback path"
            )
        realm_roles = {
            role.get("name")
            for role in realm.get("roles", {}).get("realm", [])
            if isinstance(role, dict)
        }
        if "offline_access" not in realm_roles:
            raise ValueError("PKW113 the BFF fixture must define the offline_access realm role")
        users = realm.get("users")
        if not isinstance(users, list) or not users:
            raise ValueError("PKW113 the BFF fixture must contain its local acceptance personas")
        missing_offline_access = sorted(
            str(user.get("username", "<unknown>"))
            for user in users
            if not isinstance(user, dict) or "offline_access" not in user.get("realmRoles", [])
        )
        if missing_offline_access:
            raise ValueError(
                "PKW113 every BFF acceptance persona must be eligible for the requested offline_access scope: "
                + ", ".join(missing_offline_access)
            )
    elif profile_client.get("publicClient") is not True or "secret" in profile_client:
        raise ValueError("PKW113 the selected SPA-PKCE client must remain public and secret-free")


def verify_repository(
    repository: Path,
    web_profile: str,
    spa_configuration: dict | None,
) -> None:
    validate_realm(
        (repository / REALM_PATH).read_bytes(),
        web_profile,
        spa_configuration,
    )
