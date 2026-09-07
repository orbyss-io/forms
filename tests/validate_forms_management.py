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
        "src/dotnet/Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj",
        "src/dotnet/Orbyss.Forms.Application/Orbyss.Forms.Application.csproj",
        "src/dotnet/Orbyss.Forms.Core/Orbyss.Forms.Core.csproj",
        "src/dotnet/Orbyss.Forms.JsonForms/Orbyss.Forms.JsonForms.csproj",
        "src/dotnet/Orbyss.Forms.Storage.Abstractions/Orbyss.Forms.Storage.Abstractions.csproj",
        "src/dotnet/Orbyss.Forms.Storage.InMemory/Orbyss.Forms.Storage.InMemory.csproj",
        "src/dotnet/Orbyss.Forms.Web.Management/Orbyss.Forms.Web.Management.csproj",
        "src/dotnet/Orbyss.Forms.Web.Runtime/Orbyss.Forms.Web.Runtime.csproj",
        "src/dotnet/Orbyss.Forms.Management.Tool/Orbyss.Forms.Management.Tool.csproj",
        "src/dotnet/Orbyss.Forms.Management.Mcp.AspNetCore/Orbyss.Forms.Management.Mcp.AspNetCore.csproj",
        "src/dotnet/Orbyss.Localization.Abstractions/Orbyss.Localization.Abstractions.csproj",
        "src/dotnet/Orbyss.Localization.Application/Orbyss.Localization.Application.csproj",
        "src/dotnet/Orbyss.Localization.Core/Orbyss.Localization.Core.csproj",
        "src/dotnet/Orbyss.Localization.Formats/Orbyss.Localization.Formats.csproj",
        "src/dotnet/Orbyss.Localization.Storage.Abstractions/Orbyss.Localization.Storage.Abstractions.csproj",
        "src/dotnet/Orbyss.Localization.Storage.InMemory/Orbyss.Localization.Storage.InMemory.csproj",
        "src/dotnet/Orbyss.Localization.Web.Management/Orbyss.Localization.Web.Management.csproj",
        "src/dotnet/Orbyss.Localization.Web.Runtime/Orbyss.Localization.Web.Runtime.csproj",
        "src/dotnet/Orbyss.Localization.Tool/Orbyss.Localization.Tool.csproj",
        "src/dotnet/Orbyss.Localization.Mcp.AspNetCore/Orbyss.Localization.Mcp.AspNetCore.csproj",
    )
    solution = (root / "Orbyss.Forms.slnx").read_text(encoding="utf-8").replace("\\", "/")
    for relative in required_backend_projects:
        if not (root / relative).is_file():
            raise AssertionError(f"Required management backend project was removed: {relative}")
        if relative not in solution:
            raise AssertionError(f"Required management backend project left the solution: {relative}")

    required_contracts = {
        "src/dotnet/Orbyss.Forms.Abstractions/IFormAuthoring.cs": "ValidateAsync",
        "src/dotnet/Orbyss.Forms.Abstractions/IFormReleaseLifecycle.cs": "CompileAsync",
        "src/dotnet/Orbyss.Forms.Abstractions/IFormDraftOperations.cs": "SaveAsync",
        "src/dotnet/Orbyss.Forms.Management.Tool/FormManagementTools.cs": "forms.management.create",
        "src/dotnet/Orbyss.Localization.Tool/LocalizationManagementTools.cs": "localization.catalogs.create",
    }
    for relative, required in required_contracts.items():
        source = (root / relative).read_text(encoding="utf-8")
        if required not in source:
            raise AssertionError(f"Required management backend contract is missing {required}: {relative}")

    graphs = {
        "src/dotnet/Orbyss.Forms.Application/Orbyss.Forms.Application.csproj": (
            set(),
            {
                "../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj",
                "../Orbyss.Forms.Storage.Abstractions/Orbyss.Forms.Storage.Abstractions.csproj",
            },
        ),
        "src/dotnet/Orbyss.Forms.Web.Management/Orbyss.Forms.Web.Management.csproj": (
            {"CShells.AspNetCore.Abstractions"},
            {"../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj"},
        ),
        "src/dotnet/Orbyss.Forms.Web.Runtime/Orbyss.Forms.Web.Runtime.csproj": (
            {"CShells.AspNetCore.Abstractions"},
            {"../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj"},
        ),
        "src/dotnet/Orbyss.Forms.Management.Tool/Orbyss.Forms.Management.Tool.csproj": (
            {"ModelContextProtocol"},
            {
                "../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj",
                "../Orbyss.Forms.Tool/Orbyss.Forms.Tool.csproj",
            },
        ),
        "src/dotnet/Orbyss.Forms.Management.Mcp.AspNetCore/Orbyss.Forms.Management.Mcp.AspNetCore.csproj": (
            {"CShells.AspNetCore.Abstractions", "ModelContextProtocol.AspNetCore", "Orbyss.Foundation.Mcp.AspNetCore"},
            {
                "../Orbyss.Forms.Management.Tool/Orbyss.Forms.Management.Tool.csproj",
            },
        ),
        "src/dotnet/Orbyss.Localization.Tool/Orbyss.Localization.Tool.csproj": (
            {"ModelContextProtocol"},
            {"../Orbyss.Localization.Abstractions/Orbyss.Localization.Abstractions.csproj"},
        ),
        "src/dotnet/Orbyss.Localization.Mcp.AspNetCore/Orbyss.Localization.Mcp.AspNetCore.csproj": (
            {"CShells.AspNetCore.Abstractions", "ModelContextProtocol.AspNetCore", "Orbyss.Foundation.Mcp.AspNetCore"},
            {
                "../Orbyss.Localization.Tool/Orbyss.Localization.Tool.csproj",
            },
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
        "src/dotnet/Orbyss.Forms.Web.Management/OrbyssFormManagementFeature.cs",
        "src/dotnet/Orbyss.Forms.Web.Runtime/OrbyssFormRuntimeFeature.cs",
    ):
        source = (root / relative).read_text(encoding="utf-8")
        if "IWebShellFeature" not in source or "IMiddlewareShellFeature" in source:
            raise AssertionError(f"{relative} must remain endpoint-only")
        for forbidden in ("UseExceptionHandler", "AddProblemDetails", "UseAuthentication", "AddAuthentication"):
            if forbidden in source:
                raise AssertionError(f"{relative} owns host behavior: {forbidden}")

    if any((root / "src/dotnet").glob("Orbyss.Foundation.*")):
        raise AssertionError("Forms must consume Foundation packages instead of owning Foundation source.")

    contributors = {
        "src/dotnet/Orbyss.Forms.Management.Mcp.AspNetCore/OrbyssFormManagementMcpFeature.cs": "WithTools<FormManagementTools>",
        "src/dotnet/Orbyss.Localization.Mcp.AspNetCore/OrbyssLocalizationMcpFeature.cs": "WithTools<LocalizationManagementTools>",
    }
    for relative, required in contributors.items():
        source = (root / relative).read_text(encoding="utf-8")
        if "IShellFeature" not in source or "DependsOn" not in source or required not in source:
            raise AssertionError(f"{relative} is not a shared-MCP tool contributor")
        for forbidden in ("IWebShellFeature", "MapMcp", "WithToolsFromAssembly", "AllowAnonymous"):
            if forbidden in source:
                raise AssertionError(f"{relative} contains unsafe transport behavior: {forbidden}")

    catalogs = {
        "src/dotnet/Orbyss.Forms.Management.Tool/FormManagementTools.cs": 12,
        "src/dotnet/Orbyss.Localization.Tool/LocalizationManagementTools.cs": 16,
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
        raise AssertionError("Orbyss Forms MCP contributors contain colliding tool names")

    application = (root / "src/dotnet/Orbyss.Forms.Application/DefaultFormCatalogService.cs").read_text(encoding="utf-8")
    for required in ("ReplayAsync", "RequireExpectedVersion", "SubmitForReviewAsync", "WriteAsync(release", "RetireAsync"):
        if required not in application:
            raise AssertionError(f"Forms application lifecycle is missing {required}")
    store = (root / "src/dotnet/Orbyss.Forms.Storage.FileSystem/FileSystemFormDefinitionStore.cs").read_text(encoding="utf-8")
    for required in ("WriteGates", "RequireConcurrency", "AuditTrail", "Commands", "failed content verification"):
        if required not in store:
            raise AssertionError(f"Forms filesystem aggregate store is missing {required}")

    probe = root / "tests/dotnet/Orbyss.Forms.Management.Probe/Orbyss.Forms.Management.Probe.csproj"
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
    print("Orbyss Forms management and shared MCP validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
