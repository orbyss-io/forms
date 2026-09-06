from __future__ import annotations

import re
import subprocess
from pathlib import Path
from xml.etree import ElementTree


def references(project: Path, kind: str) -> set[str]:
    tree = ElementTree.parse(project)
    return {
        item.attrib["Include"].replace("\\", "/")
        for item in tree.iter()
        if item.tag.endswith(kind)
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    # Physical review rejected the optional management UI, not the governed backend.
    # Keep this list explicit so a future UI cleanup cannot silently remove drafts,
    # validation/compilation, releases, localization administration, or MCP access.
    required_backend_projects = (
        "src/dotnet/ProgramKit.Forms.Abstractions/ProgramKit.Forms.Abstractions.csproj",
        "src/dotnet/ProgramKit.Forms.Application/ProgramKit.Forms.Application.csproj",
        "src/dotnet/ProgramKit.Forms.Core/ProgramKit.Forms.Core.csproj",
        "src/dotnet/ProgramKit.Forms.JsonForms/ProgramKit.Forms.JsonForms.csproj",
        "src/dotnet/ProgramKit.Forms.Storage.Abstractions/ProgramKit.Forms.Storage.Abstractions.csproj",
        "src/dotnet/ProgramKit.Forms.Storage.InMemory/ProgramKit.Forms.Storage.InMemory.csproj",
        "src/dotnet/ProgramKit.Forms.Web.Management/ProgramKit.Forms.Web.Management.csproj",
        "src/dotnet/ProgramKit.Forms.Web.Runtime/ProgramKit.Forms.Web.Runtime.csproj",
        "src/dotnet/ProgramKit.Forms.Management.Tool/ProgramKit.Forms.Management.Tool.csproj",
        "src/dotnet/ProgramKit.Forms.Management.Mcp.AspNetCore/ProgramKit.Forms.Management.Mcp.AspNetCore.csproj",
        "src/dotnet/ProgramKit.Localization.Abstractions/ProgramKit.Localization.Abstractions.csproj",
        "src/dotnet/ProgramKit.Localization.Application/ProgramKit.Localization.Application.csproj",
        "src/dotnet/ProgramKit.Localization.Core/ProgramKit.Localization.Core.csproj",
        "src/dotnet/ProgramKit.Localization.Formats/ProgramKit.Localization.Formats.csproj",
        "src/dotnet/ProgramKit.Localization.Storage.Abstractions/ProgramKit.Localization.Storage.Abstractions.csproj",
        "src/dotnet/ProgramKit.Localization.Storage.InMemory/ProgramKit.Localization.Storage.InMemory.csproj",
        "src/dotnet/ProgramKit.Localization.Web.Management/ProgramKit.Localization.Web.Management.csproj",
        "src/dotnet/ProgramKit.Localization.Web.Runtime/ProgramKit.Localization.Web.Runtime.csproj",
        "src/dotnet/ProgramKit.Localization.Tool/ProgramKit.Localization.Tool.csproj",
        "src/dotnet/ProgramKit.Localization.Mcp.AspNetCore/ProgramKit.Localization.Mcp.AspNetCore.csproj",
        "src/dotnet/ProgramKit.Mcp.AspNetCore/ProgramKit.Mcp.AspNetCore.csproj",
    )
    solution = (root / "ProgramKit.slnx").read_text(encoding="utf-8").replace("\\", "/")
    for relative in required_backend_projects:
        if not (root / relative).is_file():
            raise AssertionError(f"Required management backend project was removed: {relative}")
        if relative not in solution:
            raise AssertionError(f"Required management backend project left the solution: {relative}")

    required_contracts = {
        "src/dotnet/ProgramKit.Forms.Abstractions/IFormAuthoring.cs": "ValidateAsync",
        "src/dotnet/ProgramKit.Forms.Abstractions/IFormReleaseLifecycle.cs": "CompileAsync",
        "src/dotnet/ProgramKit.Forms.Abstractions/IFormDraftOperations.cs": "SaveAsync",
        "src/dotnet/ProgramKit.Forms.Management.Tool/FormManagementTools.cs": "forms.management.create",
        "src/dotnet/ProgramKit.Localization.Tool/LocalizationManagementTools.cs": "localization.catalogs.create",
    }
    for relative, required in required_contracts.items():
        source = (root / relative).read_text(encoding="utf-8")
        if required not in source:
            raise AssertionError(f"Required management backend contract is missing {required}: {relative}")

    graphs = {
        "src/dotnet/ProgramKit.Forms.Application/ProgramKit.Forms.Application.csproj": (
            set(),
            {
                "../ProgramKit.Forms.Abstractions/ProgramKit.Forms.Abstractions.csproj",
                "../ProgramKit.Forms.Storage.Abstractions/ProgramKit.Forms.Storage.Abstractions.csproj",
            },
        ),
        "src/dotnet/ProgramKit.Forms.Web.Management/ProgramKit.Forms.Web.Management.csproj": (
            {"CShells.AspNetCore.Abstractions"},
            {"../ProgramKit.Forms.Abstractions/ProgramKit.Forms.Abstractions.csproj"},
        ),
        "src/dotnet/ProgramKit.Forms.Web.Runtime/ProgramKit.Forms.Web.Runtime.csproj": (
            {"CShells.AspNetCore.Abstractions"},
            {"../ProgramKit.Forms.Abstractions/ProgramKit.Forms.Abstractions.csproj"},
        ),
        "src/dotnet/ProgramKit.Forms.Management.Tool/ProgramKit.Forms.Management.Tool.csproj": (
            {"ModelContextProtocol"},
            {
                "../ProgramKit.Forms.Abstractions/ProgramKit.Forms.Abstractions.csproj",
                "../ProgramKit.Forms.Tool/ProgramKit.Forms.Tool.csproj",
            },
        ),
        "src/dotnet/ProgramKit.Forms.Management.Mcp.AspNetCore/ProgramKit.Forms.Management.Mcp.AspNetCore.csproj": (
            {"CShells.AspNetCore.Abstractions", "ModelContextProtocol.AspNetCore"},
            {
                "../ProgramKit.Forms.Management.Tool/ProgramKit.Forms.Management.Tool.csproj",
                "../ProgramKit.Mcp.AspNetCore/ProgramKit.Mcp.AspNetCore.csproj",
            },
        ),
        "src/dotnet/ProgramKit.Localization.Tool/ProgramKit.Localization.Tool.csproj": (
            {"ModelContextProtocol"},
            {"../ProgramKit.Localization.Abstractions/ProgramKit.Localization.Abstractions.csproj"},
        ),
        "src/dotnet/ProgramKit.Localization.Mcp.AspNetCore/ProgramKit.Localization.Mcp.AspNetCore.csproj": (
            {"CShells.AspNetCore.Abstractions", "ModelContextProtocol.AspNetCore"},
            {
                "../ProgramKit.Localization.Tool/ProgramKit.Localization.Tool.csproj",
                "../ProgramKit.Mcp.AspNetCore/ProgramKit.Mcp.AspNetCore.csproj",
            },
        ),
        "src/dotnet/ProgramKit.Mcp.AspNetCore/ProgramKit.Mcp.AspNetCore.csproj": (
            {"CShells.AspNetCore.Abstractions", "ModelContextProtocol.AspNetCore"},
            set(),
        ),
    }
    for relative, expected in graphs.items():
        packages = references(root / relative, "PackageReference")
        projects = references(root / relative, "ProjectReference")
        if packages != expected[0] or projects != expected[1]:
            raise AssertionError(
                f"Unexpected management package graph for {relative}: "
                f"packages={sorted(packages)}, projects={sorted(projects)}"
            )

    for relative in (
        "src/dotnet/ProgramKit.Forms.Web.Management/ProgramKitFormManagementFeature.cs",
        "src/dotnet/ProgramKit.Forms.Web.Runtime/ProgramKitFormRuntimeFeature.cs",
        "src/dotnet/ProgramKit.Mcp.AspNetCore/ProgramKitMcpFeature.cs",
    ):
        source = (root / relative).read_text(encoding="utf-8")
        if "IWebShellFeature" not in source or "IMiddlewareShellFeature" in source:
            raise AssertionError(f"{relative} must remain endpoint-only")
        for forbidden in ("UseExceptionHandler", "AddProblemDetails", "UseAuthentication", "AddAuthentication"):
            if forbidden in source:
                raise AssertionError(f"{relative} owns host behavior: {forbidden}")

    transport = (root / "src/dotnet/ProgramKit.Mcp.AspNetCore/ProgramKitMcpFeature.cs").read_text(encoding="utf-8")
    for required in ("Stateless = true", "MapMcp", "RequireAuthorization"):
        if required not in transport:
            raise AssertionError(f"Shared MCP transport is missing {required}")
    if "WithTools<" in transport or "WithToolsFromAssembly" in transport:
        raise AssertionError("Shared MCP transport must not own a bounded-context tool catalog")

    contributors = {
        "src/dotnet/ProgramKit.Forms.Management.Mcp.AspNetCore/ProgramKitFormManagementMcpFeature.cs": "WithTools<FormManagementTools>",
        "src/dotnet/ProgramKit.Localization.Mcp.AspNetCore/ProgramKitLocalizationMcpFeature.cs": "WithTools<LocalizationManagementTools>",
    }
    for relative, required in contributors.items():
        source = (root / relative).read_text(encoding="utf-8")
        if "IShellFeature" not in source or "DependsOn" not in source or required not in source:
            raise AssertionError(f"{relative} is not a shared-MCP tool contributor")
        for forbidden in ("IWebShellFeature", "MapMcp", "WithToolsFromAssembly", "AllowAnonymous"):
            if forbidden in source:
                raise AssertionError(f"{relative} contains unsafe transport behavior: {forbidden}")

    catalogs = {
        "src/dotnet/ProgramKit.Forms.Management.Tool/FormManagementTools.cs": 12,
        "src/dotnet/ProgramKit.Localization.Tool/LocalizationManagementTools.cs": 16,
    }
    names: list[str] = []
    for relative, expected_count in catalogs.items():
        source = (root / relative).read_text(encoding="utf-8")
        found = re.findall(r'McpServerTool\(Name = "([^"]+)"', source)
        if len(found) != expected_count or len(set(found)) != expected_count:
            raise AssertionError(f"Unexpected explicit tool catalog for {relative}: {found}")
        if "ClaimsPrincipal" not in source or "requestedAt" not in source:
            raise AssertionError(f"{relative} does not preserve trusted identity and exact replay inputs")
        names.extend(found)
    if len(names) != len(set(names)):
        raise AssertionError("Program Kit MCP contributors contain colliding tool names")

    application = (root / "src/dotnet/ProgramKit.Forms.Application/DefaultFormCatalogService.cs").read_text(encoding="utf-8")
    for required in ("ReplayAsync", "RequireExpectedVersion", "SubmitForReviewAsync", "WriteAsync(release", "RetireAsync"):
        if required not in application:
            raise AssertionError(f"Forms application lifecycle is missing {required}")
    store = (root / "src/dotnet/ProgramKit.Forms.Storage.FileSystem/FileSystemFormDefinitionStore.cs").read_text(encoding="utf-8")
    for required in ("WriteGates", "RequireConcurrency", "AuditTrail", "Commands", "failed content verification"):
        if required not in store:
            raise AssertionError(f"Forms filesystem aggregate store is missing {required}")

    host_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "src/dotnet/ProgramKit.Host").rglob("*")
        if path.suffix in {".cs", ".csproj"}
    )
    for forbidden in ("ProgramKit.Forms.Application", "ProgramKit.Forms.Web.Management", "ProgramKit.Forms.Web.Runtime", "ProgramKit.Mcp", "ProgramKit.Localization.Mcp"):
        if forbidden in host_source:
            raise AssertionError(f"ProgramKit.Host owns optional management behavior: {forbidden}")

    probe = root / "tests/dotnet/ProgramKit.Forms.Management.Probe/ProgramKit.Forms.Management.Probe.csproj"
    result = subprocess.run(
        ["dotnet", "run", "--project", str(probe), "--configuration", "Release", "--no-build"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Forms management/shared-MCP public-contract probe failed.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    print("Program Kit Forms management and shared MCP validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
