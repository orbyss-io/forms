from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import yaml


ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
REPOSITORY = "https://github.com/orbyss-io/program-kit"
MAX_BUNDLE_ENTRIES = 512
BUNDLE_ROOT_FILES = {
    "LICENSE",
    "README.md",
    "RUNTIME_VERSION",
    "THIRD-PARTY-NOTICES.md",
    "VERSION",
    "bundle.yml",
}
BUNDLE_SOURCE_PREFIXES = (
    "extensions/program-kit-governance/",
    "extensions/program-kit-dotnet/",
    "presets/program-kit-governance-preset/",
    "workflows/program-kit-bootstrap/",
)
BUNDLE_RUNTIME_SCRIPTS = {
    "scripts/invoke_specify.py",
    "scripts/openapi_upgrade_reconciliation.py",
    "scripts/upgrade_program_kit.py",
}


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return value


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def require_equal(label: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, got {actual!r}")


def deterministic_zip(source: Path, destination: Path) -> None:
    files = sorted(
        (
            path
            for path in source.rglob("*")
            if path.is_file()
            and not path.is_symlink()
            and "__pycache__" not in path.parts
            and "node_modules" not in path.parts
            and "playwright-report" not in path.parts
            and "test-results" not in path.parts
            and ".auth" not in path.parts
            and path.suffix != ".pyc"
        ),
        key=lambda path: path.relative_to(source).as_posix(),
    )
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repository_source_files(root: Path) -> list[Path]:
    """Return tracked and intentional untracked source, excluding ignored build output."""
    repository = root.resolve()
    excludes = "" if os.name == "nt" else "/dev/null"
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={repository.as_posix()}",
            "-c",
            f"core.excludesFile={excludes}",
            "-C",
            str(repository),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        check=True,
        capture_output=True,
    )
    relative_paths = [
        Path(value)
        for value in result.stdout.decode("utf-8").split("\0")
        if value
    ]
    return sorted(
        (
            relative
            for relative in relative_paths
            if (repository / relative).is_file() and not (repository / relative).is_symlink()
        ),
        key=lambda path: path.as_posix(),
    )


def bundle_source_files(root: Path) -> list[Path]:
    """Return only install-time bundle assets; SDK sources publish through their own families."""
    return [
        relative
        for relative in repository_source_files(root)
        if relative.as_posix() in BUNDLE_ROOT_FILES
        or relative.as_posix() in BUNDLE_RUNTIME_SCRIPTS
        or relative.as_posix().startswith(BUNDLE_SOURCE_PREFIXES)
    ]


def build_bundle_from_source(root: Path, output: Path) -> None:
    """Build the composite bundle from source files, never local caches or build output."""
    with tempfile.TemporaryDirectory(prefix="program-kit-release-source-") as directory:
        staging = Path(directory)
        for relative in bundle_source_files(root):
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, destination)
        subprocess.run(
            [
                "specify",
                "bundle",
                "build",
                "--path",
                str(staging),
                "--output",
                str(output),
            ],
            check=True,
        )


def validate_metadata(root: Path, version: str) -> None:
    bundle = load_yaml(root / "bundle.yml")
    governance_extension = load_yaml(root / "extensions/program-kit-governance/extension.yml")
    dotnet_extension = load_yaml(root / "extensions/program-kit-dotnet/extension.yml")
    governance_preset = load_yaml(root / "presets/program-kit-governance-preset/preset.yml")
    workflow = load_yaml(root / "workflows/program-kit-bootstrap/workflow.yml")
    extensions_catalog = load_json(root / "catalogs/extensions.json")
    presets_catalog = load_json(root / "catalogs/presets.json")
    workflows_catalog = load_json(root / "catalogs/workflows.json")
    bundles_catalog = load_json(root / "catalogs/bundles.json")

    require_equal("bundle version", bundle["bundle"]["version"], version)
    require_equal("governance extension version", governance_extension["extension"]["version"], version)
    require_equal(".NET extension version", dotnet_extension["extension"]["version"], version)
    require_equal("governance preset version", governance_preset["preset"]["version"], version)
    require_equal("workflow version", workflow["workflow"]["version"], version)
    initializer_pins = {
        "Initialize-ProgramKit.cmd": f'set "PROGRAM_KIT_REF=v{version}"',
        "Initialize-ProgramKit.sh": f'PROGRAM_KIT_REF="v{version}"',
    }
    for initializer_name, expected_pin in initializer_pins.items():
        initializer = (root / initializer_name).read_text(encoding="utf-8")
        if expected_pin not in initializer:
            raise ValueError(
                f"{initializer_name} does not pin the current Program Kit release tag"
            )
    require_equal("governance extension repository", governance_extension["extension"]["repository"], REPOSITORY)
    require_equal(".NET extension repository", dotnet_extension["extension"]["repository"], REPOSITORY)
    require_equal("governance preset repository", governance_preset["preset"]["repository"], REPOSITORY)
    require_equal("bundle license", bundle["bundle"]["license"], "MIT")
    require_equal("governance extension license", governance_extension["extension"]["license"], "MIT")
    require_equal(".NET extension license", dotnet_extension["extension"]["license"], "MIT")
    require_equal("governance preset license", governance_preset["preset"]["license"], "MIT")

    governance_extension_entry = extensions_catalog["extensions"]["program-kit-governance"]
    dotnet_extension_entry = extensions_catalog["extensions"]["program-kit-dotnet"]
    preset_entry = presets_catalog["presets"]["program-kit-governance-preset"]
    workflow_entry = workflows_catalog["workflows"]["program-kit-bootstrap"]
    bundle_entry = bundles_catalog["bundles"]["program-kit"]
    require_equal("governance extension catalog version", governance_extension_entry["version"], version)
    require_equal(".NET extension catalog version", dotnet_extension_entry["version"], version)
    require_equal("governance preset catalog version", preset_entry["version"], version)
    require_equal("workflow catalog version", workflow_entry["version"], version)
    require_equal("bundle catalog version", bundle_entry["version"], version)
    require_equal("governance extension catalog license", governance_extension_entry["license"], "MIT")
    require_equal(".NET extension catalog license", dotnet_extension_entry["license"], "MIT")
    require_equal("governance preset catalog license", preset_entry["license"], "MIT")
    require_equal("workflow catalog license", workflow_entry["license"], "MIT")
    require_equal("bundle catalog license", bundle_entry["license"], "MIT")

    tag = f"v{version}"
    require_equal(
        "governance extension release URL",
        governance_extension_entry["download_url"],
        f"{REPOSITORY}/releases/download/{tag}/program-kit-governance-{version}.zip",
    )
    require_equal(
        ".NET extension release URL",
        dotnet_extension_entry["download_url"],
        f"{REPOSITORY}/releases/download/{tag}/program-kit-dotnet-{version}.zip",
    )
    require_equal(
        "governance preset release URL",
        preset_entry["download_url"],
        f"{REPOSITORY}/releases/download/{tag}/program-kit-governance-preset-{version}.zip",
    )
    require_equal(
        "workflow source URL",
        workflow_entry["url"],
        f"https://raw.githubusercontent.com/orbyss-io/program-kit/{tag}/workflows/program-kit-bootstrap/workflow.yml",
    )
    require_equal(
        "bundle release URL",
        bundle_entry["download_url"],
        f"{REPOSITORY}/releases/download/{tag}/program-kit-{version}.zip",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic Program Kit release assets.")
    parser.add_argument("--output", default="artifacts", help="Output directory inside the repository")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output = (root / args.output).resolve()
    try:
        output.relative_to(root)
    except ValueError as exc:
        raise ValueError("Release output must stay inside the repository") from exc

    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not version:
        raise ValueError("VERSION is empty")
    validate_metadata(root, version)

    output.mkdir(parents=True, exist_ok=True)
    expected = [
        output / f"program-kit-governance-{version}.zip",
        output / f"program-kit-dotnet-{version}.zip",
        output / f"program-kit-governance-preset-{version}.zip",
        output / f"program-kit-bootstrap-{version}.zip",
        output / f"program-kit-{version}.zip",
        output / f"Initialize-ProgramKit-{version}.cmd",
        output / f"Initialize-ProgramKit-{version}.sh",
        output / "SHA256SUMS",
    ]
    for path in expected:
        if path.exists() and path.is_file():
            path.unlink()

    deterministic_zip(root / "extensions/program-kit-governance", expected[0])
    deterministic_zip(root / "extensions/program-kit-dotnet", expected[1])
    deterministic_zip(root / "presets/program-kit-governance-preset", expected[2])
    deterministic_zip(root / "workflows/program-kit-bootstrap", expected[3])

    build_bundle_from_source(root, output)
    if not expected[4].is_file():
        raise FileNotFoundError(f"Spec Kit did not create {expected[4]}")
    with zipfile.ZipFile(expected[4], "r") as archive:
        entry_count = len(archive.namelist())
    if entry_count > MAX_BUNDLE_ENTRIES:
        raise ValueError(
            f"Program Kit bundle contains {entry_count} entries; Spec Kit permits at most "
            f"{MAX_BUNDLE_ENTRIES}."
        )
    shutil.copyfile(root / "Initialize-ProgramKit.cmd", expected[5])
    shutil.copyfile(root / "Initialize-ProgramKit.sh", expected[6])

    checksum_lines = [f"{sha256(path)}  {path.name}" for path in expected[:7]]
    expected[7].write_text("\n".join(checksum_lines) + "\n", encoding="utf-8", newline="\n")
    for path in expected:
        print(f"built {path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
