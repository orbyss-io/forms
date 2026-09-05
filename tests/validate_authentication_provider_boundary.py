from __future__ import annotations

import re
from pathlib import Path


PROVIDER_NAMES = ("keycloak", "auth0", "okta", "cognito", "identityserver", "entra")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    runtime = root / "src/dotnet"
    authentication_packages = sorted(
        path for path in runtime.iterdir() if path.is_dir() and path.name.startswith("ProgramKit.Authentication")
    )
    if not authentication_packages:
        raise AssertionError("No Program Kit authentication runtime packages were found")

    for package in authentication_packages:
        for path in package.rglob("*"):
            if not path.is_file() or "bin" in path.parts or "obj" in path.parts:
                continue
            if path.suffix.lower() not in {".cs", ".csproj", ".md", ".json"}:
                continue
            source = path.read_text(encoding="utf-8").lower()
            for provider in PROVIDER_NAMES:
                if re.search(rf"\b{re.escape(provider)}\b", source):
                    raise AssertionError(
                        f"Provider-specific name {provider!r} leaked into runtime authentication package {path}"
                    )

    identity_abstractions = runtime / "ProgramKit.Identity.Admin.Abstractions"
    for path in identity_abstractions.rglob("*"):
        if not path.is_file() or "bin" in path.parts or "obj" in path.parts:
            continue
        if path.suffix.lower() not in {".cs", ".csproj", ".md", ".json"}:
            continue
        source = path.read_text(encoding="utf-8").lower()
        for provider in PROVIDER_NAMES:
            if re.search(rf"\b{re.escape(provider)}\b", source):
                raise AssertionError(
                    f"Provider-specific name {provider!r} leaked into identity administration abstractions {path}"
                )

    validator = (
        runtime / "ProgramKit.Authentication/ProgramKitWebOptionsValidator.cs"
    ).read_text(encoding="utf-8")
    if "authority.IsLoopback" not in validator or 'Host.Equals("keycloak"' in validator:
        raise AssertionError("The local HTTP authority exception must be loopback-only and provider-neutral")

    contract = (
        root / "extensions/program-kit-dotnet/references/secure-web-profiles.md"
    ).read_text(encoding="utf-8")
    normalized_contract = " ".join(contract.split())
    for required in (
        "Provider-neutral capability boundary",
        "RFC 8693 token exchange",
        "DPoP sender constraint",
        "assurance/step-up (`acr`/`amr`)",
        "discovery/JWKS key rollover",
        "Keycloak is the built-in local identity adapter and conformance fixture",
        "A capability is not considered supported merely because the Keycloak fixture can perform it",
    ):
        if required not in normalized_contract:
            raise AssertionError(f"The authentication provider boundary is missing: {required}")

    print("Authentication runtime packages remain provider-neutral; Keycloak is confined to its adapter/fixture.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
