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
    graphs = {
        "src/Orbyss.Forms.Submissions/Orbyss.Forms.Submissions.csproj": (
            {"CShells.Abstractions", "Microsoft.Extensions.DependencyInjection.Abstractions"},
            {
                "../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj",
                "../Orbyss.Forms.Storage.Abstractions/Orbyss.Forms.Storage.Abstractions.csproj",
            },
        ),
        "src/Orbyss.Forms.Web.Submissions/Orbyss.Forms.Web.Submissions.csproj": (
            {"CShells.AspNetCore.Abstractions"},
            {"../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj"},
        ),
        "src/Orbyss.Forms.Submissions.Tool/Orbyss.Forms.Submissions.Tool.csproj": (
            {"ModelContextProtocol"},
            {"../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj"},
        ),
        "src/Orbyss.Forms.Submissions.Mcp.AspNetCore/Orbyss.Forms.Submissions.Mcp.AspNetCore.csproj": (
            {"CShells.AspNetCore.Abstractions", "ModelContextProtocol.AspNetCore", "Orbyss.Foundation.Mcp.AspNetCore"},
            {
                "../Orbyss.Forms.Submissions.Tool/Orbyss.Forms.Submissions.Tool.csproj",
            },
        ),
    }
    for relative, (expected_packages, expected_projects) in graphs.items():
        project = root / relative
        packages = references(project, "PackageReference")
        projects = references(project, "ProjectReference")
        if packages != expected_packages or projects != expected_projects:
            raise AssertionError(
                f"Unexpected operational package graph for {relative}: "
                f"packages={sorted(packages)}, projects={sorted(projects)}"
            )

    central = (root / "Directory.Packages.props").read_text(encoding="utf-8")
    for package in ("ModelContextProtocol", "ModelContextProtocol.AspNetCore"):
        if f'PackageVersion Include="{package}" Version="2.2.0"' not in central:
            raise AssertionError(f"The official {package} SDK version is not centrally pinned")

    web_source = (
        root
        / "src/Orbyss.Forms.Web.Submissions/OrbyssFormSubmissionsFeature.cs"
    ).read_text(encoding="utf-8")
    if "IWebShellFeature" not in web_source or "IMiddlewareShellFeature" in web_source:
        raise AssertionError("Form submission HTTP composition must remain endpoint-only")
    if "UseExceptionHandler" in web_source or "AddProblemDetails" in web_source:
        raise AssertionError("The submission feature must not impose global response behavior")

    mcp_source = (
        root
        / "src/Orbyss.Forms.Submissions.Mcp.AspNetCore/OrbyssFormSubmissionsMcpFeature.cs"
    ).read_text(encoding="utf-8")
    for required in ("IShellFeature", "DependsOn", "WithTools<FormOperationsTools>"):
        if required not in mcp_source:
            raise AssertionError(f"The form MCP contributor is missing: {required}")
    for forbidden in ("WithToolsFromAssembly", "IWebShellFeature", "MapMcp", "AllowAnonymous"):
        if forbidden in mcp_source:
            raise AssertionError(f"The form MCP contributor contains unsafe composition: {forbidden}")

    if any((root / "src").glob("Orbyss.Foundation.*")):
        raise AssertionError("Forms must consume Foundation packages instead of owning Foundation source.")

    tool_source = (
        root / "src/Orbyss.Forms.Submissions.Tool/FormOperationsTools.cs"
    ).read_text(encoding="utf-8")
    names = re.findall(r'McpServerTool\(Name = "([^"]+)"', tool_source)
    if len(names) != 11 or len(set(names)) != len(names):
        raise AssertionError(f"The form MCP tool catalog must contain 11 unique explicit names: {names}")
    for forbidden in (
        "IFormSubmissionReview",
        "UploadAsync(",
        "OpenReadAsync(",
        "ScanAsync(",
        "CanAccessAll",
    ):
        if forbidden in tool_source:
            raise AssertionError(f"The owner MCP surface exposes privileged or binary capability: {forbidden}")
    if "ClaimsPrincipal" not in tool_source or "IFormToolActorProvider" not in tool_source:
        raise AssertionError("MCP tools must derive identity from the transport-owned principal")
    if tool_source.count("DateTimeOffset requestedAt") < 6 or "DateTimeOffset.UtcNow" in tool_source:
        raise AssertionError("Operational mutation tools must accept repeatable timestamps for exact replay")
    if 'McpServerTool(Name = "forms.drafts.migrate"' not in tool_source or "IFormDraftMigrationOperations" not in tool_source:
        raise AssertionError("The operational MCP surface must expose governed draft migration")

    submission_source = (
        root / "src/Orbyss.Forms.Submissions/DefaultFormSubmissionService.cs"
    ).read_text(encoding="utf-8")
    for required in (
        "IFormDraftMigrationOperations",
        "IFormCompatibilityAnalyzer",
        "IFormDraftDataMigration",
        "AnalyzeAsync",
        "FormDataCodec.Create",
        "RequireValidAsync",
    ):
        if required not in submission_source:
            raise AssertionError(f"The governed draft migration path is missing: {required}")

    probe = root / "tests/Orbyss.Forms.Operations.Probe/Orbyss.Forms.Operations.Probe.csproj"
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
            "Form operations public-contract probe failed.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    print("Orbyss Forms form operational capability validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
