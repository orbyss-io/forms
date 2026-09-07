from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree


EVIDENCE = Path(".program-kit/evidence/runtime-closure.json")
SCHEMA = "../runtime-closure.schema.json"
CONFIGURATION = ("hostsettings.json", "shells.json", ".program-kit/web-profile.shells.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_identity(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".nuspec")]
        if len(names) != 1:
            raise ValueError(f"PKR021 staged package must contain exactly one nuspec: {path}")
        document = ElementTree.fromstring(archive.read(names[0]))
    metadata = next(item for item in document.iter() if item.tag.endswith("metadata"))
    package_id = next((item.text for item in metadata if item.tag.endswith("id")), None)
    version = next((item.text for item in metadata if item.tag.endswith("version")), None)
    if not package_id or not version:
        raise ValueError(f"PKR021 staged package identity is incomplete: {path}")
    return package_id, version


def relative(repository: Path, path: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(repository.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"PKR021 {label} must stay inside the repository: {path}") from error


def canonical_digest(version: str, packages: list[dict], configuration: list[dict]) -> str:
    value = json.dumps(
        {"programKitVersion": version, "packages": packages, "configuration": configuration},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        Path(temporary).replace(path)
    except BaseException:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass
        raise


def mark_in_progress(repository: Path, staged: Path, evidence: Path) -> None:
    relative(repository, evidence, "runtime closure evidence")
    atomic_write(
        evidence,
        {
            "$schema": SCHEMA,
            "schemaVersion": 1,
            "stagedRoot": relative(repository, staged, "staged runtime closure"),
            "reason": "stage-in-progress-or-failed",
            "satisfied": False,
        },
    )


def write_success(repository: Path, staged: Path, evidence: Path, version: str) -> dict:
    relative(repository, evidence, "runtime closure evidence")
    packages_root = staged / "packages"
    packages = []
    for package in sorted(packages_root.glob("*.nupkg"), key=lambda item: item.name.casefold()):
        package_id, package_version = package_identity(package)
        packages.append(
            {
                "id": package_id,
                "version": package_version,
                "file": package.relative_to(staged).as_posix(),
                "sha256": sha256(package),
            }
        )
    if not packages:
        raise ValueError("PKR021 staged runtime closure contains no packages")
    configuration = []
    for name in CONFIGURATION:
        path = staged / name
        if path.is_file():
            configuration.append({"file": name, "sha256": sha256(path)})
    if {item["file"] for item in configuration} < {"hostsettings.json", "shells.json"}:
        raise ValueError("PKR021 staged runtime closure is missing required configuration")
    value = {
        "$schema": SCHEMA,
        "schemaVersion": 1,
        "programKitVersion": version,
        "stagedRoot": relative(repository, staged, "staged runtime closure"),
        "packages": packages,
        "configuration": configuration,
        "closureDigest": canonical_digest(version, packages, configuration),
        "packageHashesAreRunScoped": True,
        "satisfied": True,
    }
    atomic_write(evidence, value)
    return value


def validate(repository: Path, staged: Path, evidence: Path, version: str) -> dict:
    relative(repository, evidence, "runtime closure evidence")
    try:
        value = json.loads(evidence.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"PKR022 cannot read runtime-closure evidence {evidence}: {error}") from error
    if (
        not isinstance(value, dict)
        or value.get("schemaVersion") != 1
        or value.get("satisfied") is not True
        or value.get("programKitVersion") != version
        or value.get("stagedRoot") != relative(repository, staged, "staged runtime closure")
    ):
        raise ValueError("PKR022 runtime-closure evidence is unsatisfied, stale, or targets another stage")
    expected = write_value(repository, staged, version)
    for key in ("packages", "configuration", "closureDigest"):
        if value.get(key) != expected[key]:
            raise ValueError(f"PKR022 runtime-closure evidence does not match staged {key}")
    return value


def write_value(repository: Path, staged: Path, version: str) -> dict:
    packages = []
    for package in sorted((staged / "packages").glob("*.nupkg"), key=lambda item: item.name.casefold()):
        package_id, package_version = package_identity(package)
        packages.append(
            {
                "id": package_id,
                "version": package_version,
                "file": package.relative_to(staged).as_posix(),
                "sha256": sha256(package),
            }
        )
    configuration = [
        {"file": name, "sha256": sha256(staged / name)}
        for name in CONFIGURATION
        if (staged / name).is_file()
    ]
    return {
        "packages": packages,
        "configuration": configuration,
        "closureDigest": canonical_digest(version, packages, configuration),
    }
