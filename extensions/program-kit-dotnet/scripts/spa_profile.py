from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit


CONFIGURATION_PATH = ".program-kit/spa-pkce.json"


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"PKW100 expected a JSON object in {path}")
    return value


def exact_origin(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or "*" in value:
        raise ValueError(f"PKW101 {name} must be an exact HTTP(S) origin without wildcards")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError(f"PKW101 {name} must be an exact HTTP(S) origin: {value}")
    return f"{parsed.scheme}://{parsed.netloc}"


def exact_uri(value: object, name: str, origin: str) -> str:
    if not isinstance(value, str) or not value or "*" in value:
        raise ValueError(f"PKW102 {name} must contain exact HTTP(S) URIs without wildcards")
    parsed = urlsplit(value)
    actual_origin = f"{parsed.scheme}://{parsed.netloc}"
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not parsed.path.startswith("/")
        or parsed.path == "/"
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or actual_origin != origin
    ):
        raise ValueError(f"PKW102 {name} must be an exact route below {origin}: {value}")
    return value


def string_array(value: object, name: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(value) != len(set(value))
    ):
        raise ValueError(f"PKW103 {name} must be a non-empty array of unique strings")
    return value


def validate_configuration(value: dict) -> dict:
    required = {
        "$schema",
        "schemaVersion",
        "applicationOrigin",
        "apiOrigin",
        "identityOrigin",
        "identityAuthority",
        "clientId",
        "audience",
        "redirectUris",
        "postLogoutRedirectUris",
        "scopes",
        "silentRenewTimeoutSeconds",
        "session",
    }
    if value.get("$schema") != "./spa-pkce.schema.json" or value.get("schemaVersion") != 1 or set(value) != required:
        raise ValueError("PKW100 SPA-PKCE configuration must use schemaVersion 1 and the exact supported fields")
    application_origin = exact_origin(value["applicationOrigin"], "applicationOrigin")
    exact_origin(value["apiOrigin"], "apiOrigin")
    identity_origin = exact_origin(value["identityOrigin"], "identityOrigin")
    identity = value["identityAuthority"]
    if not isinstance(identity, str) or "*" in identity:
        raise ValueError("PKW101 identityAuthority must be an exact HTTP(S) URI")
    identity_uri = urlsplit(identity)
    if identity_uri.scheme not in {"http", "https"} or not identity_uri.netloc or identity_uri.query or identity_uri.fragment:
        raise ValueError("PKW101 identityAuthority must be an exact HTTP(S) URI")
    if f"{identity_uri.scheme}://{identity_uri.netloc}" != identity_origin:
        raise ValueError("PKW101 identityAuthority must be below identityOrigin")
    for name in ("clientId", "audience"):
        if not isinstance(value[name], str) or not value[name].strip():
            raise ValueError(f"PKW103 {name} must be a non-empty string")
    redirects = string_array(value["redirectUris"], "redirectUris")
    logout_redirects = string_array(value["postLogoutRedirectUris"], "postLogoutRedirectUris")
    for item in redirects:
        exact_uri(item, "redirectUris", application_origin)
    for item in logout_redirects:
        exact_uri(item, "postLogoutRedirectUris", application_origin)
    scopes = string_array(value["scopes"], "scopes")
    if "openid" not in scopes:
        raise ValueError("PKW103 scopes must include openid")
    renewal = value["silentRenewTimeoutSeconds"]
    if not isinstance(renewal, int) or isinstance(renewal, bool) or renewal < 1 or renewal > 60:
        raise ValueError("PKW104 silentRenewTimeoutSeconds must be between 1 and 60")
    session = value["session"]
    expected_session = {
        "idleMinutes",
        "absoluteMinutes",
        "absoluteDeadlineClaim",
        "tokenExpiryClaim",
        "crossTabCoordination",
        "providerLogoutFailure",
    }
    if not isinstance(session, dict) or set(session) != expected_session:
        raise ValueError("PKW105 session must contain the exact supported SPA session-policy fields")
    idle = session["idleMinutes"]
    absolute = session["absoluteMinutes"]
    if (
        not isinstance(idle, int)
        or isinstance(idle, bool)
        or not isinstance(absolute, int)
        or isinstance(absolute, bool)
        or idle < 1
        or absolute < idle
    ):
        raise ValueError("PKW105 SPA session lifetime must be positive and absolute must not be shorter than idle")
    fixed = {
        "absoluteDeadlineClaim": "auth_time",
        "tokenExpiryClaim": "exp",
        "crossTabCoordination": "required-no-token-payload",
        "providerLogoutFailure": "local-session-remains-cleared",
    }
    for name, expected in fixed.items():
        if session.get(name) != expected:
            raise ValueError(f"PKW105 session.{name} must be {expected!r}")
    return value


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def render_realm(source: bytes, configuration: dict) -> bytes:
    realm = json.loads(source.decode("utf-8"))
    session = configuration["session"]
    realm["ssoSessionIdleTimeout"] = session["idleMinutes"] * 60
    realm["ssoSessionMaxLifespan"] = session["absoluteMinutes"] * 60
    realm["clientSessionIdleTimeout"] = session["idleMinutes"] * 60
    realm["clientSessionMaxLifespan"] = session["absoluteMinutes"] * 60
    clients = [
        client for client in realm.get("clients", [])
        if client.get("clientId") != "program-kit-bff"
    ]
    realm["clients"] = clients
    audience = configuration["audience"]
    api = next((item for item in clients if item.get("clientId") == "program-kit-api"), None)
    if not isinstance(api, dict):
        raise ValueError("PKW106 managed Keycloak realm is missing program-kit-api")
    api["clientId"] = audience
    scopes = realm.get("clientScopes", [])
    api_scope = next((item for item in scopes if item.get("name") == "program-kit-api"), None)
    if not isinstance(api_scope, dict):
        raise ValueError("PKW106 managed Keycloak realm is missing program-kit-api scope")
    api_scope["name"] = audience
    for mapper in api_scope.get("protocolMappers", []):
        config = mapper.get("config", {})
        if "included.client.audience" in config:
            config["included.client.audience"] = audience
    spa = next((item for item in clients if item.get("clientId") == "program-kit-spa"), None)
    if not isinstance(spa, dict):
        raise ValueError("PKW106 managed Keycloak realm is missing program-kit-spa")
    spa["clientId"] = configuration["clientId"]
    spa["publicClient"] = True
    spa.pop("secret", None)
    spa["redirectUris"] = configuration["redirectUris"]
    spa.pop("postLogoutRedirectUris", None)
    attributes = spa.setdefault("attributes", {})
    if not isinstance(attributes, dict):
        raise ValueError("PKW106 managed Keycloak SPA client attributes must be an object")
    attributes["post.logout.redirect.uris"] = "##".join(configuration["postLogoutRedirectUris"])
    spa["webOrigins"] = [configuration["applicationOrigin"]]
    spa["defaultClientScopes"] = [
        "basic", "profile", "roles", "web-origins", "acr", audience
    ]
    return json_bytes(realm)


def render_shell_profile(source: bytes, configuration: dict) -> bytes:
    settings = json.loads(source.decode("utf-8"))
    web = settings["CShells"]["Shells"]["default"]["Configuration"]["ProgramKit"]["Web"]
    web["Authority"] = configuration["identityAuthority"]
    web["ClientId"] = configuration["clientId"]
    web["Audience"] = configuration["audience"]
    web["Scopes"] = configuration["scopes"]
    web["AllowedOrigins"] = [configuration["applicationOrigin"]]
    web["RemoteAuthenticationTimeoutSeconds"] = configuration["silentRenewTimeoutSeconds"]
    web["SessionIdleMinutes"] = configuration["session"]["idleMinutes"]
    web["SessionAbsoluteMinutes"] = configuration["session"]["absoluteMinutes"]
    return json_bytes(settings)


def render_profile(source: bytes, configuration: dict) -> bytes:
    profile = json.loads(source.decode("utf-8"))
    profile["configuration"] = CONFIGURATION_PATH
    profile["browserSessionAdapter"] = ".program-kit/eng/web/spa-session.ts"
    return json_bytes(profile)


def render_web_contract(source: bytes, configuration: dict) -> bytes:
    contract = json.loads(source.decode("utf-8"))
    contract["origins"] = {
        "application": configuration["applicationOrigin"],
        "api": configuration["apiOrigin"],
        "identity": configuration["identityOrigin"],
    }
    contract["client"].update(
        {
            "clientId": configuration["clientId"],
            "audience": configuration["audience"],
            "redirectUris": configuration["redirectUris"],
            "postLogoutRedirectUris": configuration["postLogoutRedirectUris"],
            "scopes": configuration["scopes"],
            "silentRenewTimeoutSeconds": configuration["silentRenewTimeoutSeconds"],
        }
    )
    contract["session"] = configuration["session"] | {
        "authoritativeEnforcement": ["keycloak-sso-session", "browser-spa-session-adapter", "api-token-lifetime"],
        "silentRenewRule": "preserve-original-auth_time-and-never-extend-absolute-deadline",
    }
    return json_bytes(contract)


def verify_outputs(repository: Path, configuration: dict) -> None:
    expected = {
        "Authority": configuration["identityAuthority"],
        "ClientId": configuration["clientId"],
        "Audience": configuration["audience"],
        "Scopes": configuration["scopes"],
        "AllowedOrigins": [configuration["applicationOrigin"]],
        "RemoteAuthenticationTimeoutSeconds": configuration["silentRenewTimeoutSeconds"],
        "SessionIdleMinutes": configuration["session"]["idleMinutes"],
        "SessionAbsoluteMinutes": configuration["session"]["absoluteMinutes"],
    }
    shell_profile = load_object(repository / ".program-kit/web-profile.shells.json")
    shell_web = (
        shell_profile.get("CShells", {})
        .get("Shells", {})
        .get("default", {})
        .get("Configuration", {})
        .get("ProgramKit", {})
        .get("Web", {})
    )
    for name, expected_value in expected.items():
        if shell_web.get(name) != expected_value:
            raise ValueError(
                f"PKW107 shell ProgramKit:Web:{name} does not match {CONFIGURATION_PATH}"
            )
    features = (
        shell_profile.get("CShells", {}).get("Shells", {}).get("default", {}).get("Features", {})
    )
    if "ProgramKit.Authentication.SpaPkce" not in features or "ProgramKit.Authentication.BffCookie" in features:
        raise ValueError("PKW108 the shell must activate only the selected SPA-PKCE authentication feature")

    realm = load_object(repository / "deploy/keycloak/program-kit-realm.json")
    spa = next((item for item in realm.get("clients", []) if item.get("clientId") == configuration["clientId"]), None)
    if not isinstance(spa, dict) or spa.get("publicClient") is not True or "secret" in spa:
        raise ValueError("PKW108 the SPA must be a public Keycloak client without a secret")
    if any(item.get("clientId") == "program-kit-bff" for item in realm.get("clients", [])):
        raise ValueError("PKW108 the SPA fixture must not enable the alternative confidential BFF client")
    if (
        spa.get("redirectUris") != configuration["redirectUris"]
        or spa.get("attributes", {}).get("post.logout.redirect.uris")
        != "##".join(configuration["postLogoutRedirectUris"])
        or "postLogoutRedirectUris" in spa
    ):
        raise ValueError("PKW109 Keycloak exact redirect registrations do not match the SPA-PKCE input")
    session = configuration["session"]
    for name, expected_value in {
        "ssoSessionIdleTimeout": session["idleMinutes"] * 60,
        "ssoSessionMaxLifespan": session["absoluteMinutes"] * 60,
        "clientSessionIdleTimeout": session["idleMinutes"] * 60,
        "clientSessionMaxLifespan": session["absoluteMinutes"] * 60,
    }.items():
        if realm.get(name) != expected_value:
            raise ValueError(f"PKW110 Keycloak {name} does not match the SPA session policy")

    compose = (repository / "deploy/compose.application.yml").read_text(encoding="utf-8")
    if "ClientSecret" in compose or "local-program-kit-secret" in compose:
        raise ValueError("PKW108 SPA application composition must not receive a confidential-client secret")
    playwright = (repository / ".program-kit/eng/web/playwright.config.ts").read_text(encoding="utf-8")
    for secure_default in ("trace: 'off'", "screenshot: 'off'", "video: 'off'"):
        if secure_default not in playwright:
            raise ValueError(f"PKW111 authentication evidence must configure {secure_default}")
    contract = load_object(repository / ".program-kit/eng/web/web-contract.json")
    client = contract.get("client", {})
    if (
        client.get("redirectUris") != configuration["redirectUris"]
        or client.get("postLogoutRedirectUris") != configuration["postLogoutRedirectUris"]
        or contract.get("session", {}).get("absoluteDeadlineClaim") != "auth_time"
        or not (repository / ".program-kit/eng/web/spa-session.ts").is_file()
    ):
        raise ValueError("PKW112 browser runtime contract does not match the SPA-PKCE configuration")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Validate the synchronized Program Kit SPA-PKCE profile.")
    parser.add_argument("--repository", default=".")
    args = parser.parse_args()
    try:
        repository = Path(args.repository).resolve()
        configuration = validate_configuration(load_object(repository / CONFIGURATION_PATH))
        verify_outputs(repository, configuration)
        print("WEB-V1 SPA-PKCE configuration, provider registration, and evidence retention are valid")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
