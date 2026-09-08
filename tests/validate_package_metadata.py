from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REPOSITORY = "https://github.com/orbyss-io/forms"
RETIRED_IDS = {
    "Orbyss.Forms.Application",
    "Orbyss.Forms.Core",
    "Orbyss.Forms.Mcp.AspNetCore",
    "Orbyss.Forms.Tool",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child(parent: ElementTree.Element, name: str) -> ElementTree.Element:
    return next(item for item in parent if local_name(item.tag) == name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages", type=Path, default=ROOT / "artifacts/nuget")
    args = parser.parse_args()

    if (ROOT / "src/dotnet").exists() or (ROOT / "tests/dotnet").exists() or (ROOT / "eng").exists():
        raise AssertionError("Forms must keep .NET projects directly under src/ or tests/ and repository tooling under scripts/.")

    expected_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    expected_ids = {
        project.stem
        for project in (ROOT / "src").glob("Orbyss.Forms.*/*.csproj")
    }
    if len(expected_ids) != 15:
        raise AssertionError(f"Expected 15 Forms package projects, found {len(expected_ids)}.")

    found: set[str] = set()
    for package in sorted(args.packages.glob("*.nupkg")):
        with zipfile.ZipFile(package) as archive:
            nuspecs = [name for name in archive.namelist() if name.endswith(".nuspec")]
            if len(nuspecs) != 1:
                raise AssertionError(f"{package.name} must contain exactly one nuspec.")
            nuspec = archive.read(nuspecs[0])
            root = ElementTree.fromstring(nuspec)
        metadata = child(root, "metadata")
        package_id = child(metadata, "id").text or ""
        version = child(metadata, "version").text or ""
        repository = child(metadata, "repository")
        dependencies = {
            item.attrib.get("id", "")
            for item in metadata.iter()
            if local_name(item.tag) == "dependency"
        }
        if package_id not in expected_ids:
            raise AssertionError(f"Unexpected package ID: {package_id}")
        if version != expected_version:
            raise AssertionError(f"{package_id} has version {version}, expected {expected_version}.")
        if repository.attrib.get("url") != EXPECTED_REPOSITORY:
            raise AssertionError(f"{package_id} has the wrong repository URL.")
        if not package_id.startswith("Orbyss.Forms."):
            raise AssertionError(f"{package_id} is outside the Forms namespace.")
        if b"ProgramKit" in nuspec:
            raise AssertionError(f"{package_id} still exposes a ProgramKit package identity.")
        if dependencies & RETIRED_IDS:
            raise AssertionError(f"{package_id} depends on retired package identities: {sorted(dependencies & RETIRED_IDS)}")
        found.add(package_id)

    if found != expected_ids:
        raise AssertionError(f"Package set mismatch. Missing={sorted(expected_ids - found)}, extra={sorted(found - expected_ids)}")
    print("Exact 15-package Orbyss Forms NuGet metadata contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
