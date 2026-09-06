from __future__ import annotations

import json
import subprocess
from pathlib import Path
from xml.etree import ElementTree


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    projects = [
        root / "src/dotnet/ProgramKit.Forms.Abstractions/ProgramKit.Forms.Abstractions.csproj",
        root / "src/dotnet/ProgramKit.Localization.Abstractions/ProgramKit.Localization.Abstractions.csproj",
    ]
    for project in projects:
        parsed = ElementTree.parse(project)
        references = [
            item.attrib["Include"]
            for item in parsed.iter()
            if item.tag.endswith("PackageReference") or item.tag.endswith("ProjectReference")
        ]
        if references:
            raise AssertionError(f"Semantic contract package leaked dependencies: {project}: {references}")
        source = "\n".join(path.read_text(encoding="utf-8") for path in project.parent.glob("*.cs"))
        for forbidden in ("Microsoft.AspNetCore", "EntityFrameworkCore", "JsonForms", "CodeMirror", "Monaco", "CShells"):
            if forbidden in source:
                raise AssertionError(f"Semantic contract package leaked {forbidden}: {project}")

    core_project = root / "src/dotnet/ProgramKit.Forms.Core/ProgramKit.Forms.Core.csproj"
    core_tree = ElementTree.parse(core_project)
    package_references = [
        item.attrib["Include"]
        for item in core_tree.iter()
        if item.tag.endswith("PackageReference")
    ]
    if package_references:
        raise AssertionError(f"Forms core leaked package dependencies: {package_references}")
    project_references = [
        item.attrib["Include"].replace("\\", "/")
        for item in core_tree.iter()
        if item.tag.endswith("ProjectReference")
    ]
    if project_references != ["../ProgramKit.Forms.Abstractions/ProgramKit.Forms.Abstractions.csproj"]:
        raise AssertionError(f"Forms core has an unexpected dependency graph: {project_references}")

    json_forms_project = root / "src/dotnet/ProgramKit.Forms.JsonForms/ProgramKit.Forms.JsonForms.csproj"
    json_forms_tree = ElementTree.parse(json_forms_project)
    json_forms_packages = [
        item.attrib["Include"]
        for item in json_forms_tree.iter()
        if item.tag.endswith("PackageReference")
    ]
    if json_forms_packages:
        raise AssertionError(f"JSON Forms compiler leaked package dependencies: {json_forms_packages}")
    json_forms_references = {
        item.attrib["Include"].replace("\\", "/")
        for item in json_forms_tree.iter()
        if item.tag.endswith("ProjectReference")
    }
    expected_json_forms_references = {
        "../ProgramKit.Forms.Abstractions/ProgramKit.Forms.Abstractions.csproj",
        "../ProgramKit.Forms.Core/ProgramKit.Forms.Core.csproj",
    }
    if json_forms_references != expected_json_forms_references:
        raise AssertionError(f"JSON Forms compiler has an unexpected dependency graph: {json_forms_references}")

    localization_core_project = root / "src/dotnet/ProgramKit.Localization.Core/ProgramKit.Localization.Core.csproj"
    localization_core_tree = ElementTree.parse(localization_core_project)
    localization_core_packages = [
        item.attrib["Include"]
        for item in localization_core_tree.iter()
        if item.tag.endswith("PackageReference")
    ]
    if localization_core_packages:
        raise AssertionError(f"Localization core leaked package dependencies: {localization_core_packages}")
    localization_core_references = [
        item.attrib["Include"].replace("\\", "/")
        for item in localization_core_tree.iter()
        if item.tag.endswith("ProjectReference")
    ]
    if localization_core_references != ["../ProgramKit.Localization.Abstractions/ProgramKit.Localization.Abstractions.csproj"]:
        raise AssertionError(f"Localization core has an unexpected dependency graph: {localization_core_references}")

    localization_application_project = root / "src/dotnet/ProgramKit.Localization.Application/ProgramKit.Localization.Application.csproj"
    localization_application_tree = ElementTree.parse(localization_application_project)
    localization_application_packages = [
        item.attrib["Include"]
        for item in localization_application_tree.iter()
        if item.tag.endswith("PackageReference")
    ]
    if localization_application_packages:
        raise AssertionError(f"Localization application orchestration leaked package dependencies: {localization_application_packages}")
    localization_application_references = {
        item.attrib["Include"].replace("\\", "/")
        for item in localization_application_tree.iter()
        if item.tag.endswith("ProjectReference")
    }
    expected_localization_application_references = {
        "../ProgramKit.Localization.Abstractions/ProgramKit.Localization.Abstractions.csproj",
        "../ProgramKit.Localization.Core/ProgramKit.Localization.Core.csproj",
        "../ProgramKit.Localization.Storage.Abstractions/ProgramKit.Localization.Storage.Abstractions.csproj",
    }
    if localization_application_references != expected_localization_application_references:
        raise AssertionError(f"Localization application orchestration has an unexpected dependency graph: {localization_application_references}")

    localization_formats_project = root / "src/dotnet/ProgramKit.Localization.Formats/ProgramKit.Localization.Formats.csproj"
    localization_formats_tree = ElementTree.parse(localization_formats_project)
    localization_formats_packages = [
        item.attrib["Include"]
        for item in localization_formats_tree.iter()
        if item.tag.endswith("PackageReference")
    ]
    if localization_formats_packages:
        raise AssertionError(f"Localization format adapters leaked package dependencies: {localization_formats_packages}")
    localization_formats_references = [
        item.attrib["Include"].replace("\\", "/")
        for item in localization_formats_tree.iter()
        if item.tag.endswith("ProjectReference")
    ]
    if localization_formats_references != ["../ProgramKit.Localization.Abstractions/ProgramKit.Localization.Abstractions.csproj"]:
        raise AssertionError(f"Localization format adapters have an unexpected dependency graph: {localization_formats_references}")

    localization_web_projects = {
        "src/dotnet/ProgramKit.Localization.Web.Management/ProgramKit.Localization.Web.Management.csproj": "ProgramKitLocalizationManagementFeature.cs",
        "src/dotnet/ProgramKit.Localization.Web.Runtime/ProgramKit.Localization.Web.Runtime.csproj": "ProgramKitLocalizationRuntimeFeature.cs",
    }
    for relative_project, feature_file in localization_web_projects.items():
        project = root / relative_project
        tree = ElementTree.parse(project)
        package_references = {
            item.attrib["Include"]
            for item in tree.iter()
            if item.tag.endswith("PackageReference")
        }
        if package_references != {"CShells.AspNetCore.Abstractions"}:
            raise AssertionError(f"Localization web feature has an unexpected package graph: {relative_project}: {package_references}")
        project_references = {
            item.attrib["Include"].replace("\\", "/")
            for item in tree.iter()
            if item.tag.endswith("ProjectReference")
        }
        if project_references != {"../ProgramKit.Localization.Abstractions/ProgramKit.Localization.Abstractions.csproj"}:
            raise AssertionError(f"Localization web feature has an unexpected project graph: {relative_project}: {project_references}")
        source = (project.parent / feature_file).read_text(encoding="utf-8")
        if "IWebShellFeature" not in source or "IMiddlewareShellFeature" in source:
            raise AssertionError(f"Localization endpoint composition must remain an endpoint-only CShells feature: {feature_file}")

    host_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "src/dotnet/ProgramKit.Host").rglob("*")
        if path.suffix in {".cs", ".csproj"}
    )
    if "ProgramKit.Localization.Web" in host_source:
        raise AssertionError("ProgramKit.Host must not own or reference localization web behavior.")

    storage_graphs = {
        "src/dotnet/ProgramKit.Forms.Storage.Abstractions/ProgramKit.Forms.Storage.Abstractions.csproj": {
            "../ProgramKit.Forms.Abstractions/ProgramKit.Forms.Abstractions.csproj"
        },
        "src/dotnet/ProgramKit.Forms.Storage.FileSystem/ProgramKit.Forms.Storage.FileSystem.csproj": {
            "../ProgramKit.Forms.Storage.Abstractions/ProgramKit.Forms.Storage.Abstractions.csproj"
        },
        "src/dotnet/ProgramKit.Localization.Storage.Abstractions/ProgramKit.Localization.Storage.Abstractions.csproj": {
            "../ProgramKit.Localization.Abstractions/ProgramKit.Localization.Abstractions.csproj"
        },
        "src/dotnet/ProgramKit.Localization.Storage.FileSystem/ProgramKit.Localization.Storage.FileSystem.csproj": {
            "../ProgramKit.Localization.Storage.Abstractions/ProgramKit.Localization.Storage.Abstractions.csproj"
        },
    }
    for relative_project, expected_references in storage_graphs.items():
        storage_tree = ElementTree.parse(root / relative_project)
        storage_packages = [
            item.attrib["Include"]
            for item in storage_tree.iter()
            if item.tag.endswith("PackageReference")
        ]
        if storage_packages:
            raise AssertionError(f"Storage adapter leaked package dependencies: {relative_project}: {storage_packages}")
        storage_references = {
            item.attrib["Include"].replace("\\", "/")
            for item in storage_tree.iter()
            if item.tag.endswith("ProjectReference")
        }
        if storage_references != expected_references:
            raise AssertionError(f"Storage adapter has an unexpected dependency graph: {relative_project}: {storage_references}")

    bridge_project = root / "src/dotnet/ProgramKit.Forms.Localization/ProgramKit.Forms.Localization.csproj"
    bridge_tree = ElementTree.parse(bridge_project)
    bridge_packages = [
        item.attrib["Include"]
        for item in bridge_tree.iter()
        if item.tag.endswith("PackageReference")
    ]
    if bridge_packages:
        raise AssertionError(f"Forms/localization bridge leaked package dependencies: {bridge_packages}")
    bridge_references = {
        item.attrib["Include"].replace("\\", "/")
        for item in bridge_tree.iter()
        if item.tag.endswith("ProjectReference")
    }
    expected_bridge_references = {
        "../ProgramKit.Forms.Abstractions/ProgramKit.Forms.Abstractions.csproj",
        "../ProgramKit.Localization.Abstractions/ProgramKit.Localization.Abstractions.csproj",
    }
    if bridge_references != expected_bridge_references:
        raise AssertionError(f"Forms/localization bridge has an unexpected dependency graph: {bridge_references}")

    probe = root / "tests/dotnet/ProgramKit.Forms.Localization.Contracts.Probe/ProgramKit.Forms.Localization.Contracts.Probe.csproj"
    result = subprocess.run(
        [
            "dotnet",
            "run",
            "--project",
            str(probe),
            "--configuration",
            "Release",
            "--no-build",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Forms/localization public-contract probe failed.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    fixture_result = subprocess.run(
        [
            "dotnet",
            "run",
            "--project",
            str(probe),
            "--configuration",
            "Release",
            "--no-build",
            "--",
            "--print-frontend-fixture",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if fixture_result.returncode != 0:
        raise AssertionError(f"Forms frontend fixture export failed.\n{fixture_result.stderr}")
    generated_fixture = json.loads(fixture_result.stdout)
    fixture_path = root / "src/typescript/tests/fixtures/dotnet-registration-release.json"
    committed_fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if generated_fixture != committed_fixture:
        raise AssertionError("The committed frontend release fixture drifted from the .NET compiler output.")
    web_probe = root / "tests/dotnet/ProgramKit.Localization.Web.Probe/ProgramKit.Localization.Web.Probe.csproj"
    web_result = subprocess.run(
        [
            "dotnet",
            "run",
            "--project",
            str(web_probe),
            "--configuration",
            "Release",
            "--no-build",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if web_result.returncode != 0:
        raise AssertionError(
            "Localization web composition probe failed.\n"
            f"stdout:\n{web_result.stdout}\n"
            f"stderr:\n{web_result.stderr}"
        )
    print(result.stdout.strip())
    print(web_result.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
