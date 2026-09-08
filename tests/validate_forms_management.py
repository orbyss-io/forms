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
    # validation/compilation, releases, or MCP access.
    required_backend_projects = (
        "src/Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj",
        "src/Orbyss.Forms.Application/Orbyss.Forms.Application.csproj",
        "src/Orbyss.Forms.Core/Orbyss.Forms.Core.csproj",
        "src/Orbyss.Forms.JsonForms/Orbyss.Forms.JsonForms.csproj",
        "src/Orbyss.Forms.Storage.Abstractions/Orbyss.Forms.Storage.Abstractions.csproj",
        "src/Orbyss.Forms.Storage.InMemory/Orbyss.Forms.Storage.InMemory.csproj",
        "src/Orbyss.Forms.Web.Management/Orbyss.Forms.Web.Management.csproj",
        "src/Orbyss.Forms.Web.Runtime/Orbyss.Forms.Web.Runtime.csproj",
        "src/Orbyss.Forms.Management.Tool/Orbyss.Forms.Management.Tool.csproj",
        "src/Orbyss.Forms.Management.Mcp.AspNetCore/Orbyss.Forms.Management.Mcp.AspNetCore.csproj",
    )
    solution = (root / "Orbyss.Forms.slnx").read_text(encoding="utf-8").replace("\\", "/")
    for relative in required_backend_projects:
        if not (root / relative).is_file():
            raise AssertionError(f"Required management backend project was removed: {relative}")
        if relative not in solution:
            raise AssertionError(f"Required management backend project left the solution: {relative}")

    required_contracts = {
        "src/Orbyss.Forms.Abstractions/IFormAuthoring.cs": "ValidateAsync",
        "src/Orbyss.Forms.Abstractions/IFormReleaseLifecycle.cs": "CompileAsync",
        "src/Orbyss.Forms.Abstractions/IFormDraftOperations.cs": "SaveAsync",
        "src/Orbyss.Forms.Management.Tool/FormManagementTools.cs": "forms.management.create",
    }
    for relative, required in required_contracts.items():
        source = (root / relative).read_text(encoding="utf-8")
        if required not in source:
            raise AssertionError(f"Required management backend contract is missing {required}: {relative}")

    graphs = {
        "src/Orbyss.Forms.Application/Orbyss.Forms.Application.csproj": (
            set(),
            {
                "../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj",
                "../Orbyss.Forms.Storage.Abstractions/Orbyss.Forms.Storage.Abstractions.csproj",
            },
        ),
        "src/Orbyss.Forms.Web.Management/Orbyss.Forms.Web.Management.csproj": (
            {"CShells.AspNetCore.Abstractions"},
            {"../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj"},
        ),
        "src/Orbyss.Forms.Web.Runtime/Orbyss.Forms.Web.Runtime.csproj": (
            {"CShells.AspNetCore.Abstractions"},
            {"../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj"},
        ),
        "src/Orbyss.Forms.Management.Tool/Orbyss.Forms.Management.Tool.csproj": (
            {"ModelContextProtocol"},
            {
                "../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj",
                "../Orbyss.Forms.Tool/Orbyss.Forms.Tool.csproj",
            },
        ),
        "src/Orbyss.Forms.Management.Mcp.AspNetCore/Orbyss.Forms.Management.Mcp.AspNetCore.csproj": (
            {"CShells.AspNetCore.Abstractions", "ModelContextProtocol.AspNetCore", "Orbyss.Foundation.Mcp.AspNetCore"},
            {
                "../Orbyss.Forms.Management.Tool/Orbyss.Forms.Management.Tool.csproj",
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
        "src/Orbyss.Forms.Web.Management/OrbyssFormManagementFeature.cs",
        "src/Orbyss.Forms.Web.Runtime/OrbyssFormRuntimeFeature.cs",
    ):
        source = (root / relative).read_text(encoding="utf-8")
        if "IWebShellFeature" not in source or "IMiddlewareShellFeature" in source:
            raise AssertionError(f"{relative} must remain endpoint-only")
        for forbidden in ("UseExceptionHandler", "AddProblemDetails", "UseAuthentication", "AddAuthentication"):
            if forbidden in source:
                raise AssertionError(f"{relative} owns host behavior: {forbidden}")

    if any((root / "src").glob("Orbyss.Foundation.*")):
        raise AssertionError("Forms must consume Foundation packages instead of owning Foundation source.")

    contributors = {
        "src/Orbyss.Forms.Management.Mcp.AspNetCore/OrbyssFormManagementMcpFeature.cs": "WithTools<FormManagementTools>",
    }
    for relative, required in contributors.items():
        source = (root / relative).read_text(encoding="utf-8")
        if "IShellFeature" not in source or "DependsOn" not in source or required not in source:
            raise AssertionError(f"{relative} is not a shared-MCP tool contributor")
        for forbidden in ("IWebShellFeature", "MapMcp", "WithToolsFromAssembly", "AllowAnonymous"):
            if forbidden in source:
                raise AssertionError(f"{relative} contains unsafe transport behavior: {forbidden}")

    catalogs = {
        "src/Orbyss.Forms.Management.Tool/FormManagementTools.cs": 12,
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

    application = (root / "src/Orbyss.Forms.Application/DefaultFormCatalogService.cs").read_text(encoding="utf-8")
    for required in ("ReplayAsync", "RequireExpectedVersion", "SubmitForReviewAsync", "WriteAsync(release", "RetireAsync"):
        if required not in application:
            raise AssertionError(f"Forms application lifecycle is missing {required}")
    store = (root / "src/Orbyss.Forms.Storage.FileSystem/FileSystemFormDefinitionStore.cs").read_text(encoding="utf-8")
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
    print("Orbyss Forms management and MCP validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
