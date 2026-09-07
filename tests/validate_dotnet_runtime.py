from __future__ import annotations

import json
import re
from pathlib import Path
from xml.etree import ElementTree


def validate_package_source_routing(path: Path) -> None:
    root = ElementTree.parse(path).getroot()
    mappings = {
        source.attrib["key"]: {package.attrib["pattern"] for package in source}
        for source in root.findall("./packageSourceMapping/packageSource")
    }
    if mappings.get("nuget.org") != {"*"}:
        raise AssertionError(f"{path} must route all non-protected public packages to nuget.org")
    if mappings.get("CShells Preview") != {"CShells", "CShells.*"}:
        raise AssertionError(f"{path} does not exclusively protect the CShells namespace")
    if mappings.get("Nuplane Preview") != {"Nuplane", "Nuplane.*"}:
        raise AssertionError(f"{path} does not exclusively protect the Nuplane namespace")
    if any("*" in patterns for key, patterns in mappings.items() if key != "nuget.org"):
        raise AssertionError(f"{path} maps arbitrary consumer packages to a preview feed")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    privileged_friend_assemblies = []
    for search_root in (root / "src", root / "tests", root / "extensions"):
        for path in search_root.rglob("*"):
            if not path.is_file() or "bin" in path.parts or "obj" in path.parts:
                continue
            if path.suffix.lower() not in {".cs", ".csproj", ".props", ".targets"}:
                continue
            if "InternalsVisibleTo" in path.read_text(encoding="utf-8"):
                privileged_friend_assemblies.append(str(path.relative_to(root)))
    if privileged_friend_assemblies:
        raise AssertionError(
            "InternalsVisibleTo is forbidden; validate through public contracts instead: "
            + ", ".join(privileged_friend_assemblies)
        )

    program_version = (root / "VERSION").read_text(encoding="utf-8").strip()
    runtime_version = (root / "RUNTIME_VERSION").read_text(encoding="utf-8").strip()
    if program_version != "0.9.11":
        raise AssertionError(f"Unexpected Program Kit version: {program_version}")
    if runtime_version != "0.9.9-preview.1":
        raise AssertionError(f"Unexpected runtime artifact version: {runtime_version}")

    validate_package_source_routing(root / "NuGet.config")
    validate_package_source_routing(
        root / "extensions/program-kit-dotnet/templates/dotnet/files/NuGet.config"
    )
    manifest = json.loads(
        (root / "extensions/program-kit-dotnet/templates/dotnet/managed-files.json").read_text(
            encoding="utf-8"
        )
    )
    nuget_entry = next(item for item in manifest["files"] if item["path"] == "NuGet.config")
    if nuget_entry["ownership"] != "scaffold":
        raise AssertionError("Consumer NuGet.config must remain consumer-owned after scaffolding")

    version_props = (root / "eng/ProgramKit.Version.props").read_text(encoding="utf-8")
    if f"<ProgramKitVersion>{runtime_version}</ProgramKitVersion>" not in version_props:
        raise AssertionError("Runtime project version does not match RUNTIME_VERSION")

    exporter_source = (
        root / "src/dotnet/ProgramKit.OpenApi.Exporter/Exporter.cs"
    ).read_text(encoding="utf-8")
    exporter_manifest = json.loads(
        (
            root
            / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/.config/dotnet-tools.json"
        ).read_text(encoding="utf-8")
    )
    exporter_version = exporter_manifest["tools"]["programkit.openapi.exporter"]["version"]
    if exporter_version != runtime_version or f'ToolVersion = "{runtime_version}"' not in exporter_source:
        raise AssertionError("OpenAPI exporter binary and managed tool manifest do not match RUNTIME_VERSION")

    consumer_versions = (
        root
        / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/ProgramKit.Packages.props"
    ).read_text(encoding="utf-8")
    managed_versions = {
        "ProgramKit.Analyzers": runtime_version,
        "ProgramKit.Authentication": runtime_version,
        "ProgramKit.Authentication.Assurance": runtime_version,
        "ProgramKit.Authentication.BffCookie": runtime_version,
        "ProgramKit.Authentication.ClientCredentials": runtime_version,
        "ProgramKit.Authentication.DownstreamApi": runtime_version,
        "ProgramKit.Authentication.DPoP": runtime_version,
        "ProgramKit.Authentication.SpaPkce": runtime_version,
        "ProgramKit.Authentication.TokenExchange": runtime_version,
        "ProgramKit.DomainEvents.Abstractions": runtime_version,
        "ProgramKit.DomainEvents": runtime_version,
        "ProgramKit.Forms.Abstractions": runtime_version,
        "ProgramKit.Forms.Application": runtime_version,
        "ProgramKit.Forms.Core": runtime_version,
        "ProgramKit.Forms.JsonForms": runtime_version,
        "ProgramKit.Forms.Localization": runtime_version,
        "ProgramKit.Forms.Management.Tool": runtime_version,
        "ProgramKit.Forms.Management.Mcp.AspNetCore": runtime_version,
        "ProgramKit.Forms.Submissions": runtime_version,
        "ProgramKit.Forms.Tool": runtime_version,
        "ProgramKit.Forms.Mcp.AspNetCore": runtime_version,
        "ProgramKit.Forms.Web.Submissions": runtime_version,
        "ProgramKit.Forms.Web.Management": runtime_version,
        "ProgramKit.Forms.Web.Runtime": runtime_version,
        "ProgramKit.Forms.Storage.Abstractions": runtime_version,
        "ProgramKit.Forms.Storage.FileSystem": runtime_version,
        "ProgramKit.Forms.Storage.InMemory": runtime_version,
        "ProgramKit.Identity.Admin.Abstractions": runtime_version,
        "ProgramKit.Identity.Keycloak.Admin": runtime_version,
        "ProgramKit.Localization.Abstractions": runtime_version,
        "ProgramKit.Localization.Application": runtime_version,
        "ProgramKit.Localization.Core": runtime_version,
        "ProgramKit.Localization.Formats": runtime_version,
        "ProgramKit.Localization.Tool": runtime_version,
        "ProgramKit.Localization.Mcp.AspNetCore": runtime_version,
        "ProgramKit.Localization.Storage.Abstractions": runtime_version,
        "ProgramKit.Localization.Storage.FileSystem": runtime_version,
        "ProgramKit.Localization.Storage.InMemory": runtime_version,
        "ProgramKit.Localization.Web.Management": runtime_version,
        "ProgramKit.Localization.Web.Runtime": runtime_version,
        "ProgramKit.Mcp.AspNetCore": runtime_version,
        "ProgramKit.Tasks.Abstractions": runtime_version,
        "ProgramKit.Tasks": runtime_version,
        "ProgramKit.WebDefaults": runtime_version,
        "ProgramKit.Web.OpenApi": runtime_version,
        "ProgramKit.Web.Discovery": runtime_version,
        "ProgramKit.Web.Discovery.Abstractions": runtime_version,
        "ProgramKit.Web.ProblemDetails": runtime_version,
        "Microsoft.Extensions.DependencyInjection.Abstractions": "10.0.11",
        "Microsoft.Extensions.Logging.Abstractions": "10.0.11",
    }
    for package, expected_version in managed_versions.items():
        pattern = rf'Include="{re.escape(package)}" Version="{re.escape(expected_version)}"'
        if re.search(pattern, consumer_versions) is None:
            raise AssertionError(f"Consumer template does not pin {package} to {runtime_version}")

    analyzer = (root / "src/dotnet/ProgramKit.Analyzers/ProgramKitAnalyzer.cs").read_text(encoding="utf-8")
    for rule_id in ("PK1001", "PK1002", "PK1003", "PK1004", "PK1005", "PK1006"):
        if rule_id not in analyzer:
            raise AssertionError(f"Program Kit analyzer does not declare {rule_id}")
    editorconfig = (
        root / "extensions/program-kit-dotnet/templates/dotnet/files/.editorconfig"
    ).read_text(encoding="utf-8")
    for rule_id in ("PK1003", "PK1004", "PK1005", "PK1006"):
        if f"dotnet_diagnostic.{rule_id}.severity = error" not in editorconfig:
            raise AssertionError(f"Consumer template does not enforce {rule_id}")
    engineering = (
        root / "extensions/program-kit-dotnet/references/dotnet-engineering.md"
    ).read_text(encoding="utf-8")
    for phrase in ("Validate inputs", "Prepare the operation state", "one named type", "XML documentation"):
        if phrase not in engineering:
            raise AssertionError(f".NET engineering guidance is missing: {phrase}")

    host_workflow = (root / ".github/workflows/publish-host-image.yml").read_text(encoding="utf-8")
    if "< RUNTIME_VERSION" not in host_workflow or "steps.runtime_version.outputs.value" not in host_workflow:
        raise AssertionError("Host workflow does not derive its image tag from RUNTIME_VERSION")
    nuget_workflow = (root / ".github/workflows/publish-nuget.yml").read_text(encoding="utf-8")
    release_workflow = (root / ".github/workflows/release.yml").read_text(encoding="utf-8")
    for name, workflow in (("NuGet", nuget_workflow), ("host-image", host_workflow)):
        trigger = workflow.split("permissions:", maxsplit=1)[0]
        if "workflow_call:" not in trigger or "push:" in trigger:
            raise AssertionError(
                f"{name} publication must be callable only after release validation, not from a stable tag"
            )
    pack_command = "dotnet pack ProgramKit.slnx -c Release --no-build"
    openapi_command = "python tests/validate_openapi_exporter.py"
    if pack_command not in release_workflow or release_workflow.index(pack_command) > release_workflow.index(openapi_command):
        raise AssertionError("Release must pack built-in features before OpenAPI integration validation")
    for publication_workflow in ("publish-nuget.yml", "publish-host-image.yml"):
        if f"uses: ./.github/workflows/{publication_workflow}" not in release_workflow:
            raise AssertionError(f"Release does not call {publication_workflow} after validation")
    publication_order = (
        "publish-frontend:\n    needs: release",
        "publish-nuget:\n    needs: [release, publish-frontend]",
        "publish-host-image:\n    needs: [release, publish-frontend, publish-nuget]",
    )
    for marker in publication_order:
        if marker not in release_workflow:
            raise AssertionError(
                "Registry publication jobs must be serialized after the validated release job"
            )
    runtime_gate = "if: ${{ needs.release.outputs.publish_runtime == 'true' }}"
    if release_workflow.count(runtime_gate) != 3:
        raise AssertionError(
            "Frontend, NuGet, and host-image publication must share the runtime-version change gate"
        )
    if "packages: write" not in release_workflow:
        raise AssertionError("Release must grant its called host-image workflow package publication access")

    global_json = (root / "global.json").read_text(encoding="utf-8")
    if '"version": "10.0.202"' not in global_json or '"rollForward": "disable"' not in global_json:
        raise AssertionError("The .NET SDK feature band and patch policy are not pinned")
    dockerfile = (root / "src/dotnet/ProgramKit.Host/Dockerfile").read_text(encoding="utf-8")
    if (
        dockerfile.count("@sha256:") < 3
        or "dotnet restore ProgramKit.slnx --locked-mode --configfile NuGet.config" not in dockerfile
    ):
        raise AssertionError("Host image inputs must be digest-pinned and restored in locked mode")
    if "HEALTHCHECK" in dockerfile or "PROGRAMKIT_BUNDLE" in dockerfile:
        raise AssertionError("The application-neutral host image must not own application health or release-bundle policy")
    host_root = root / "src/dotnet/ProgramKit.Host"
    project = ElementTree.parse(host_root / "ProgramKit.Host.csproj")
    packages = {item.attrib["Include"] for item in project.iter() if item.tag.endswith("PackageReference")}
    allowed = {
        "CShells.AspNetCore",
        "Nuplane",
        "Nuplane.Loading",
        "Nuplane.Sources.Directory",
    }
    if packages != allowed:
        raise AssertionError(f"ProgramKit.Host has an unexpected runtime dependency set: {sorted(packages - allowed)}")
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in host_root.rglob("*.cs")
        if "obj" not in path.parts
    )
    for forbidden in (
        "Npgsql",
        "ApplicationBundle",
        "health/ready",
        "AddAuthentication",
        "UseAuthentication",
        "UseExceptionHandler",
        "AddProblemDetails",
        "ProgramKitWebBoundary",
    ):
        if forbidden in source:
            raise AssertionError(f"ProgramKit.Host contains application/release concern: {forbidden}")
    for required in (
        "AddNuplane",
        "AutoloadPackages",
        "AddCShellsAspNetCore",
        ".program-kit/web-profile.shells.json",
        "MapShells",
    ):
        if required not in source:
            raise AssertionError(f"ProgramKit.Host is missing application-neutral runtime plumbing: {required}")
    domain_event_abstractions = ElementTree.parse(
        root
        / "src/dotnet/ProgramKit.DomainEvents.Abstractions/ProgramKit.DomainEvents.Abstractions.csproj"
    )
    abstraction_packages = {
        item.attrib["Include"]
        for item in domain_event_abstractions.iter()
        if item.tag.endswith("PackageReference")
    }
    if abstraction_packages:
        raise AssertionError(
            "ProgramKit.DomainEvents.Abstractions must stay free of runtime, DI, transport, and broker dependencies"
        )
    abstraction_readme = (
        root / "src/dotnet/ProgramKit.DomainEvents.Abstractions/README.md"
    ).read_text(encoding="utf-8")
    if "do not reference the concrete dispatcher package" not in abstraction_readme:
        raise AssertionError("Domain-event handlers must remain independent of the concrete dispatcher package")
    for project in (
        "ProgramKit.Host",
        "ProgramKit.Authentication",
        "ProgramKit.Authentication.Assurance",
        "ProgramKit.Authentication.BffCookie",
        "ProgramKit.Authentication.ClientCredentials",
        "ProgramKit.Authentication.DownstreamApi",
        "ProgramKit.Authentication.DPoP",
        "ProgramKit.Authentication.SpaPkce",
        "ProgramKit.Authentication.TokenExchange",
        "ProgramKit.DomainEvents",
        "ProgramKit.DomainEvents.Abstractions",
        "ProgramKit.Forms.Abstractions",
        "ProgramKit.Forms.Application",
        "ProgramKit.Forms.Core",
        "ProgramKit.Forms.JsonForms",
        "ProgramKit.Forms.Localization",
        "ProgramKit.Forms.Management.Tool",
        "ProgramKit.Forms.Management.Mcp.AspNetCore",
        "ProgramKit.Forms.Submissions",
        "ProgramKit.Forms.Tool",
        "ProgramKit.Forms.Mcp.AspNetCore",
        "ProgramKit.Forms.Web.Submissions",
        "ProgramKit.Forms.Web.Management",
        "ProgramKit.Forms.Web.Runtime",
        "ProgramKit.Forms.Storage.Abstractions",
        "ProgramKit.Forms.Storage.FileSystem",
        "ProgramKit.Forms.Storage.InMemory",
        "ProgramKit.Identity.Admin.Abstractions",
        "ProgramKit.Identity.Keycloak.Admin",
        "ProgramKit.Localization.Abstractions",
        "ProgramKit.Localization.Application",
        "ProgramKit.Localization.Core",
        "ProgramKit.Localization.Formats",
        "ProgramKit.Localization.Tool",
        "ProgramKit.Localization.Mcp.AspNetCore",
        "ProgramKit.Localization.Storage.Abstractions",
        "ProgramKit.Localization.Storage.FileSystem",
        "ProgramKit.Localization.Storage.InMemory",
        "ProgramKit.Localization.Web.Management",
        "ProgramKit.Localization.Web.Runtime",
        "ProgramKit.Mcp.AspNetCore",
        "ProgramKit.Tasks",
        "ProgramKit.Tasks.Abstractions",
        "ProgramKit.WebDefaults",
        "ProgramKit.Web.OpenApi",
        "ProgramKit.Web.ProblemDetails",
        "ProgramKit.Analyzers",
        "ProgramKit.OpenApi.Exporter",
    ):
        if not (root / "src/dotnet" / project / "packages.lock.json").is_file():
            raise AssertionError(f"Missing dependency lock for {project}")

    print("Program Kit .NET runtime versions are coherent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
