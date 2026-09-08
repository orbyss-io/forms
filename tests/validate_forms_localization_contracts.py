from __future__ import annotations

import json
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


def require_graph(
    root: Path,
    relative: str,
    packages: set[str],
    projects: set[str],
) -> None:
    project = root / relative
    actual_packages = references(project, "PackageReference")
    actual_projects = references(project, "ProjectReference")
    if actual_packages != packages or actual_projects != projects:
        raise AssertionError(
            f"Unexpected package graph for {relative}: "
            f"packages={sorted(actual_packages)}, projects={sorted(actual_projects)}"
        )


def run_probe(root: Path, probe: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "dotnet",
            "run",
            "--project",
            str(probe),
            "--configuration",
            "Release",
            "--no-build",
            "--no-restore",
            *arguments,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    abstractions = root / "src/Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj"
    require_graph(root, str(abstractions.relative_to(root)), set(), set())
    source = "\n".join(path.read_text(encoding="utf-8") for path in abstractions.parent.glob("*.cs"))
    for forbidden in ("Microsoft.AspNetCore", "EntityFrameworkCore", "JsonForms", "CodeMirror", "Monaco", "CShells"):
        if forbidden in source:
            raise AssertionError(f"Forms semantic contracts leaked {forbidden}")

    require_graph(
        root,
        "src/Orbyss.Forms.Core/Orbyss.Forms.Core.csproj",
        set(),
        {"../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj"},
    )
    require_graph(
        root,
        "src/Orbyss.Forms.JsonForms/Orbyss.Forms.JsonForms.csproj",
        set(),
        {
            "../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj",
            "../Orbyss.Forms.Core/Orbyss.Forms.Core.csproj",
        },
    )
    require_graph(
        root,
        "src/Orbyss.Forms.Storage.Abstractions/Orbyss.Forms.Storage.Abstractions.csproj",
        set(),
        {"../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj"},
    )
    require_graph(
        root,
        "src/Orbyss.Forms.Storage.FileSystem/Orbyss.Forms.Storage.FileSystem.csproj",
        set(),
        {"../Orbyss.Forms.Storage.Abstractions/Orbyss.Forms.Storage.Abstractions.csproj"},
    )
    require_graph(
        root,
        "src/Orbyss.Forms.Localization/Orbyss.Forms.Localization.csproj",
        {"Orbyss.Localization.Abstractions"},
        {"../Orbyss.Forms.Abstractions/Orbyss.Forms.Abstractions.csproj"},
    )

    owned_localization = sorted(path.name for path in (root / "src").glob("Orbyss.Localization*"))
    if owned_localization:
        raise AssertionError(f"Forms must not own Localization source projects: {owned_localization}")
    for project in (root / "src").glob("Orbyss.Forms.*/*.csproj"):
        localization_projects = {
            reference for reference in references(project, "ProjectReference") if "Orbyss.Localization" in reference
        }
        if localization_projects:
            raise AssertionError(f"Forms project references Localization implementation source: {project}: {localization_projects}")

    package_versions = references(root / "Directory.Packages.props", "PackageVersion")
    if "Orbyss.Localization.Abstractions" not in package_versions:
        raise AssertionError("The Forms bridge must pin released Orbyss.Localization.Abstractions centrally")

    probe = root / "tests/dotnet/Orbyss.Forms.Localization.Contracts.Probe/Orbyss.Forms.Localization.Contracts.Probe.csproj"
    probe_result = run_probe(root, probe)
    if probe_result.returncode != 0:
        raise AssertionError(
            "Forms contracts and Localization bridge probe failed.\n"
            f"stdout:\n{probe_result.stdout}\nstderr:\n{probe_result.stderr}"
        )

    fixture_result = run_probe(root, probe, "--", "--print-frontend-fixture")
    if fixture_result.returncode != 0:
        raise AssertionError(f"Forms frontend fixture export failed.\n{fixture_result.stderr}")
    generated_fixture = json.loads(fixture_result.stdout)
    fixture_path = root / "src/typescript/tests/fixtures/dotnet-registration-release.json"
    committed_fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if generated_fixture != committed_fixture:
        raise AssertionError("The committed frontend release fixture drifted from the .NET compiler output.")

    print(probe_result.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
