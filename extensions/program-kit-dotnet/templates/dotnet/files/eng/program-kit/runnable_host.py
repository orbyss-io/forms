from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import shell_composition
import runtime_closure
from program_kit_version import PROGRAM_KIT_VERSION


BUILT_IN_FEATURE_PACKAGES = {
    "ProgramKit.Authentication": "ProgramKit.Authentication",
    "ProgramKit.Authentication.Assurance": "ProgramKit.Authentication.Assurance",
    "ProgramKit.Authentication.BffCookie": "ProgramKit.Authentication.BffCookie",
    "ProgramKit.Authentication.ClientCredentials": "ProgramKit.Authentication.ClientCredentials",
    "ProgramKit.Authentication.DownstreamApi": "ProgramKit.Authentication.DownstreamApi",
    "ProgramKit.Authentication.DPoP": "ProgramKit.Authentication.DPoP",
    "ProgramKit.Authentication.SpaPkce": "ProgramKit.Authentication.SpaPkce",
    "ProgramKit.Authentication.TokenExchange": "ProgramKit.Authentication.TokenExchange",
    "ProgramKit.DomainEvents": "ProgramKit.DomainEvents",
    "ProgramKitTasks": "ProgramKit.Tasks",
    "ProgramKit.WebDefaults": "ProgramKit.WebDefaults",
    "ProgramKit.Web.OpenApi": "ProgramKit.Web.OpenApi",
    "ProgramKit.Web.ProblemDetails": "ProgramKit.Web.ProblemDetails",
}
IDENTITY_RUNTIME_PACKAGES = {
    ("Microsoft.Bcl.Cryptography", "10.0.2"),
    ("Microsoft.IdentityModel.Abstractions", "8.19.2"),
    ("Microsoft.IdentityModel.JsonWebTokens", "8.19.2"),
    ("Microsoft.IdentityModel.Logging", "8.19.2"),
    ("Microsoft.IdentityModel.Protocols", "8.19.2"),
    ("Microsoft.IdentityModel.Protocols.OpenIdConnect", "8.19.2"),
    ("Microsoft.IdentityModel.Tokens", "8.19.2"),
    ("System.IdentityModel.Tokens.Jwt", "8.19.2"),
}
BUILT_IN_FEATURE_RUNTIME_PACKAGES = {
    "ProgramKit.Authentication.BffCookie": IDENTITY_RUNTIME_PACKAGES
    | {("Microsoft.AspNetCore.Authentication.OpenIdConnect", "10.0.11")},
    "ProgramKit.Authentication.SpaPkce": IDENTITY_RUNTIME_PACKAGES
    | {("Microsoft.AspNetCore.Authentication.JwtBearer", "10.0.11")},
    "ProgramKit.Authentication.DPoP": IDENTITY_RUNTIME_PACKAGES
    | {("Microsoft.AspNetCore.Authentication.JwtBearer", "10.0.11")},
    "ProgramKit.Web.OpenApi": {
        ("Microsoft.AspNetCore.OpenApi", "10.0.11"),
        ("Microsoft.OpenApi", "2.7.5"),
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_commit(repository: Path) -> str:
    value = os.environ.get("GITHUB_SHA")
    if value:
        return value
    excludes = "" if os.name == "nt" else "/dev/null"
    safe_directory = repository.resolve().as_posix()
    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={safe_directory}",
                "-c",
                f"core.excludesFile={excludes}",
                "-C",
                str(repository),
                "rev-parse",
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"PKR020 cannot resolve the repository source commit safely: {error}") from error
    commit = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[a-fA-F0-9]{40,64}", commit):
        detail = (result.stderr or result.stdout).strip().splitlines()
        suffix = f" Detail: {detail[-1]}" if detail else ""
        raise ValueError(
            "PKR020 runnable-host evidence requires a Git repository with a resolvable HEAD."
            + suffix
        )
    return commit.lower()


def package_identity(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as archive:
        nuspecs = [name for name in archive.namelist() if name.lower().endswith(".nuspec")]
        if len(nuspecs) != 1:
            raise ValueError(f"Expected one nuspec in {path}")
        root = ElementTree.fromstring(archive.read(nuspecs[0]))
        metadata = next(element for element in root.iter() if element.tag.endswith("metadata"))
        package_id = next(element.text for element in metadata if element.tag.endswith("id"))
        version = next(element.text for element in metadata if element.tag.endswith("version"))
        if not package_id or not version:
            raise ValueError(f"Package identity is incomplete in {path}")
        return package_id, version


def package_dependencies(path: Path) -> set[tuple[str, str]]:
    """Read dependencies from the nearest net10-compatible group in a NuGet package."""
    with zipfile.ZipFile(path) as archive:
        nuspecs = [name for name in archive.namelist() if name.lower().endswith(".nuspec")]
        root = ElementTree.fromstring(archive.read(nuspecs[0]))
    groups = [element for element in root.iter() if element.tag.endswith("group")]
    by_framework = {
        group.attrib.get("targetFramework", "").replace(" ", "").casefold(): group
        for group in groups
    }
    selected = next(
        (
            by_framework[framework]
            for framework in (
                "net10.0",
                ".netcoreapp,version=v10.0",
                "net9.0",
                "net8.0",
                "net7.0",
                "net6.0",
                ".netstandard,version=v2.1",
                ".netstandard,version=v2.0",
                "netstandard2.1",
                "netstandard2.0",
            )
            if framework in by_framework
        ),
        None,
    )
    if groups and selected is None:
        return set()
    parent = selected if selected is not None else root
    result: set[tuple[str, str]] = set()
    for dependency in parent.iter():
        if not dependency.tag.endswith("dependency"):
            continue
        package_id = dependency.attrib.get("id", "").strip()
        raw_version = dependency.attrib.get("version", "").strip()
        version = raw_version.strip("[]() ").split(",", 1)[0].strip()
        if package_id and version:
            result.add((package_id, version))
    return result


def nuget_version_key(value: str) -> tuple[tuple[int, ...], int, str]:
    """Order the concrete versions emitted by the governed dependency graph."""
    release, separator, prerelease = value.partition("-")
    return tuple(int(part) for part in release.split(".")), 1 if not separator else 0, prerelease.casefold()


def is_runtime_package(path: Path) -> bool:
    with zipfile.ZipFile(path) as archive:
        nuspecs = [name for name in archive.namelist() if name.lower().endswith(".nuspec")]
        root = ElementTree.fromstring(archive.read(nuspecs[0]))
        metadata = next(element for element in root.iter() if element.tag.endswith("metadata"))
        development = next(
            (element.text for element in metadata if element.tag.endswith("developmentDependency")), None
        )
        package_types = {
            element.attrib.get("name", "").strip().lower()
            for element in metadata.iter()
            if element.tag.endswith("packageType")
        }
        return not (development and development.strip().lower() == "true") and not bool(
            package_types & {"analyzer", "dotnettool", "template"}
        )


def package_feature(path: Path) -> dict | None:
    with zipfile.ZipFile(path) as archive:
        if "program-kit/feature.json" not in archive.namelist():
            return None
        value = json.loads(archive.read("program-kit/feature.json").decode("utf-8"))
    package_id, _ = package_identity(path)
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise ValueError(f"PKR001 invalid feature metadata in package '{package_id}'.")
    if str(value.get("packageId", "")).casefold() != package_id.casefold():
        raise ValueError(f"PKR002 feature metadata packageId does not match package '{package_id}'.")
    return value


def validate_feature_closure(shells_path: Path, identities: dict[tuple[str, str], Path]) -> None:
    package_ids = {package_id.casefold() for package_id, _ in identities}
    descriptors: dict[str, tuple[dict, str]] = {}
    for (package_id, _), package_path in identities.items():
        descriptor = package_feature(package_path)
        if descriptor is None:
            continue
        identity = descriptor.get("identity")
        if not isinstance(identity, str) or not identity:
            raise ValueError(f"PKR006 feature identity is missing in package '{package_id}'.")
        if identity in descriptors:
            raise ValueError(
                f"PKR007 feature '{identity}' resolves to both '{descriptors[identity][1]}' and '{package_id}'."
            )
        descriptors[identity] = (descriptor, package_id)

    if shells_path.name == shell_composition.CONSUMER_SHELLS.name:
        shells = shell_composition.activated_features(shells_path.parent)
    else:
        value = shell_composition.load(shells_path, required=True)
        shells = {
            shell_name: {
                identity
                for identity, settings in shell["Features"].items()
                if settings is not False
            }
            for shell_name, shell in value["CShells"]["Shells"].items()
        }
    activated_anywhere = set().union(*shells.values())
    for shell_name, active in shells.items():
        routes: dict[str, str] = {}
        for identity in sorted(active, key=str.casefold):
            built_in = BUILT_IN_FEATURE_PACKAGES.get(identity)
            if built_in:
                if built_in.casefold() not in package_ids:
                    raise ValueError(
                        f"PKR008 shell '{shell_name}' activates '{identity}', but package '{built_in}' is absent."
                    )
                continue
            resolved = descriptors.get(identity)
            if resolved is None:
                raise ValueError(
                    f"PKR009 shell '{shell_name}' activates '{identity}', but exactly one runtime package is required."
                )
            descriptor, package_id = resolved
            for dependency in descriptor.get("runtimeDependencies", []):
                if str(dependency).casefold() not in package_ids:
                    raise ValueError(
                        f"PKR010 shell '{shell_name}', feature '{identity}', package '{package_id}' "
                        f"requires missing runtime package '{dependency}'."
                    )
            for dependency in descriptor.get("featureDependencies", []):
                if dependency not in active:
                    raise ValueError(
                        f"PKR011 shell '{shell_name}', feature '{identity}' requires inactive feature '{dependency}'."
                    )
            for route in descriptor.get("routes", []):
                previous = routes.setdefault(str(route).casefold(), identity)
                if previous != identity:
                    raise ValueError(
                        f"PKR012 shell '{shell_name}' has route collision '{route}' between '{previous}' and '{identity}'."
                    )
    for identity, (descriptor, package_id) in descriptors.items():
        if identity not in activated_anywhere and descriptor.get("dormant") is not True:
            raise ValueError(
                f"PKR013 feature '{identity}' from '{package_id}' is neither activated nor explicitly dormant."
            )


def register_package(identities: dict[tuple[str, str], Path], path: Path) -> None:
    identity = package_identity(path)
    conflicting = next(
        (existing for existing in identities if existing[0].casefold() == identity[0].casefold() and existing != identity),
        None,
    )
    if conflicting:
        raise ValueError(
            f"PKR014 runtime image contains multiple versions of {identity[0]}: "
            f"{conflicting[1]} and {identity[1]}."
        )
    identities[identity] = path


def runtime_dependencies(repository: Path, application_package_ids: set[str]) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for assets_path in repository.rglob("project.assets.json"):
        if "obj" not in assets_path.parts:
            continue
        assets = json.loads(assets_path.read_text(encoding="utf-8"))
        restore = assets.get("project", {}).get("restore", {})
        project_path_value = restore.get("projectPath") or restore.get("projectUniqueName")
        if not project_path_value:
            continue
        project_path = Path(project_path_value)
        if not project_path.is_absolute():
            project_path = repository / project_path
        package_id = restore.get("projectName") or project_path.stem
        if project_path.is_file():
            root = ElementTree.parse(project_path).getroot()
            package_id = next(
                (element.text for element in root.iter() if element.tag.endswith("PackageId") and element.text),
                package_id,
            )
        if package_id.casefold() not in application_package_ids:
            continue
        libraries = assets.get("libraries", {})
        direct: set[str] = set()
        for framework in assets.get("project", {}).get("frameworks", {}).values():
            for dependency_id, dependency in framework.get("dependencies", {}).items():
                if str(dependency.get("suppressParent", "")).casefold() != "all":
                    direct.add(dependency_id.casefold())
        for target in assets.get("targets", {}).values():
            keys = {
                key.rsplit("/", 1)[0].casefold(): key
                for key in target
                if "/" in key and libraries.get(key, {}).get("type") == "package"
            }
            pending, visited = list(direct), set()
            while pending:
                dependency_id = pending.pop()
                if dependency_id in visited:
                    continue
                visited.add(dependency_id)
                key = keys.get(dependency_id)
                if key is None:
                    continue
                value = target[key]
                if value.get("runtime") or value.get("runtimeTargets"):
                    result.add(tuple(key.rsplit("/", 1)))
                pending.extend(str(item).casefold() for item in value.get("dependencies", {}))
    return result


def package_sources(repository: Path) -> list[str]:
    root = ElementTree.parse(repository / "NuGet.config").getroot()
    return [
        element.attrib["value"]
        for section in root.findall("packageSources")
        for element in section.findall("add")
        if element.attrib.get("value")
    ]


def managed_package_versions(repository: Path) -> dict[str, str]:
    path = repository / "eng/program-kit/ProgramKit.Packages.props"
    root = ElementTree.parse(path).getroot()
    return {
        element.attrib["Include"]: element.attrib["Version"]
        for element in root.iter()
        if element.tag.endswith("PackageVersion")
        and element.attrib.get("Include")
        and element.attrib.get("Version")
    }


def package_base_addresses(sources: list[str]) -> list[str]:
    result: list[str] = []
    for source in sources:
        with urllib.request.urlopen(source, timeout=30) as response:
            index = json.load(response)
        address = next(
            (item["@id"] for item in index.get("resources", []) if str(item.get("@type", "")).startswith("PackageBaseAddress")),
            None,
        )
        if address:
            result.append(str(address).rstrip("/"))
    return result


def download_package(package_id: str, version: str, bases: list[str], destination: Path) -> None:
    for base in bases:
        url = f"{base}/{package_id.lower()}/{version.lower()}/{package_id.lower()}.{version.lower()}.nupkg"
        try:
            with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as output:
                shutil.copyfileobj(response, output)
            return
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    raise FileNotFoundError(f"Could not download {package_id} {version} from configured NuGet sources.")


def stage(repository: Path, package_output: Path, output: Path, evidence: Path | None = None) -> None:
    evidence = evidence or repository / runtime_closure.EVIDENCE
    runtime_closure.mark_in_progress(repository, output, evidence)
    active = set().union(*shell_composition.activated_features(repository).values())
    inactive_built_in_packages = {
        package_id.casefold()
        for identity, package_id in BUILT_IN_FEATURE_PACKAGES.items()
        if identity not in active
    }
    with tempfile.TemporaryDirectory(prefix="program-kit-runnable-host-") as temp_value:
        staging = Path(temp_value) / "runnable-host"
        staged_packages = staging / "packages"
        staged_packages.mkdir(parents=True)
        identities: dict[tuple[str, str], Path] = {}
        for package in sorted(package_output.glob("*.nupkg")):
            if not is_runtime_package(package):
                continue
            package_id, _ = package_identity(package)
            if package_id.casefold() in inactive_built_in_packages:
                continue
            destination = staged_packages / package.name
            shutil.copyfile(package, destination)
            register_package(identities, destination)
        required = runtime_dependencies(repository, {item[0].casefold() for item in identities})
        bases: list[str] = []
        built_ins = [identity for identity in sorted(active) if identity in BUILT_IN_FEATURE_PACKAGES]
        managed_versions = managed_package_versions(repository) if built_ins else {}
        for identity in built_ins:
            package_id = BUILT_IN_FEATURE_PACKAGES.get(identity)
            if package_id:
                version = managed_versions.get(package_id)
                if not version:
                    raise ValueError(
                        f"PKR019 built-in feature '{identity}' has no managed package pin for '{package_id}'."
                    )
                required.add((package_id, version))
            required.update(BUILT_IN_FEATURE_RUNTIME_PACKAGES.get(identity, set()))
        missing = sorted(required - set(identities), key=lambda item: (item[0].casefold(), item[1]))
        if missing:
            bases = package_base_addresses(package_sources(repository))
            for package_id, version in missing:
                destination = staged_packages / f"{package_id}.{version}.nupkg"
                download_package(package_id, version, bases, destination)
                register_package(identities, destination)
        while True:
            required_by_dependencies: dict[str, tuple[str, str]] = {}
            for package_path in identities.values():
                for package_id, version in package_dependencies(package_path):
                    key = package_id.casefold()
                    previous = required_by_dependencies.get(key)
                    if previous is None or nuget_version_key(version) > nuget_version_key(previous[1]):
                        required_by_dependencies[key] = (package_id, version)
            present = {package_id.casefold(): (package_id, version) for package_id, version in identities}
            missing_dependencies = sorted(
                (
                    dependency
                    for key, dependency in required_by_dependencies.items()
                    if key not in present
                    or nuget_version_key(dependency[1]) > nuget_version_key(present[key][1])
                ),
                key=lambda item: (item[0].casefold(), item[1]),
            )
            if not missing_dependencies:
                break
            if not bases:
                bases = package_base_addresses(package_sources(repository))
            for package_id, version in missing_dependencies:
                conflicting = present.get(package_id.casefold())
                if conflicting:
                    old_path = identities.pop(conflicting)
                    old_path.unlink()
                destination = staged_packages / f"{package_id}.{version}.nupkg"
                download_package(package_id, version, bases, destination)
                register_package(identities, destination)
        for name in ("hostsettings.json", "shells.json"):
            source = repository / name
            if not source.is_file():
                raise FileNotFoundError(f"PKR016 required runnable-host configuration is missing: {source}")
            shutil.copyfile(source, staging / name)
        profile_shells = repository / ".program-kit/web-profile.shells.json"
        if profile_shells.is_file():
            destination = staging / ".program-kit/web-profile.shells.json"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(profile_shells, destination)
        validate_feature_closure(staging / "shells.json", identities)
        if not identities:
            raise ValueError("PKR015 no runtime packages were produced for the runnable host image.")
        if output.exists():
            shutil.rmtree(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(staging, output)
    runtime_closure.write_success(repository, output, evidence, PROGRAM_KIT_VERSION)
    print(f"staged runnable host image inputs in {output}")


def reject_embedded_secrets(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            sensitive_container = key.casefold() in {"connectionstrings", "credentials"}
            sensitive_value = re.search(r"secret|password|token|apikey|privatekey", key, re.IGNORECASE)
            if (sensitive_container or sensitive_value) and child not in (None, "", [], {}):
                raise ValueError(f"PKR017 release descriptor cannot embed secret value at {child_path}.")
            reject_embedded_secrets(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_embedded_secrets(child, f"{path}[{index}]")


def describe(
    repository: Path,
    staged: Path,
    image: str,
    tag: str,
    digest: str,
    output: Path,
    closure_evidence: Path | None = None,
) -> None:
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("PKR018 image digest must be a lowercase sha256 digest.")
    closure_path = closure_evidence or repository / runtime_closure.EVIDENCE
    closure = runtime_closure.validate(
        repository,
        staged,
        closure_path,
        PROGRAM_KIT_VERSION,
    )
    hostsettings_path, shells_path = staged / "hostsettings.json", staged / "shells.json"
    profile_shells_path = staged / ".program-kit/web-profile.shells.json"
    hostsettings = json.loads(hostsettings_path.read_text(encoding="utf-8"))
    shells = json.loads(shells_path.read_text(encoding="utf-8"))
    reject_embedded_secrets(hostsettings)
    profile_shells = (
        json.loads(profile_shells_path.read_text(encoding="utf-8"))
        if profile_shells_path.is_file()
        else None
    )
    reject_embedded_secrets(profile_shells)
    payload = {
        "schemaVersion": 1,
        "application": {
            "id": repository.name,
            "version": (repository / "VERSION").read_text(encoding="utf-8").strip(),
            "sourceCommit": source_commit(repository),
            "programKitVersion": PROGRAM_KIT_VERSION,
        },
        "hostImage": {
            "repository": image,
            "tag": tag,
            "digest": digest,
            "reference": f"{image}@{digest}",
        },
        "runtimeClosure": {
            "evidence": runtime_closure.relative(repository, closure_path, "runtime closure evidence"),
            "digest": closure["closureDigest"],
            "packageCount": len(closure["packages"]),
            "packageHashesAreRunScoped": True,
        },
        "configuration": {
            "hostsettings": hostsettings,
            "hostsettingsSha256": sha256(hostsettings_path),
            "shells": shells,
            "shellsSha256": sha256(shells_path),
            "webProfileShells": profile_shells,
            "webProfileShellsSha256": sha256(profile_shells_path) if profile_shells_path.is_file() else None,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"described runnable host in {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage and describe a Program Kit runnable host release.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    stage_parser = subparsers.add_parser("stage")
    stage_parser.add_argument("--repository", default=".")
    stage_parser.add_argument("--packages", required=True)
    stage_parser.add_argument("--output", required=True)
    stage_parser.add_argument("--evidence", default=str(runtime_closure.EVIDENCE))
    describe_parser = subparsers.add_parser("describe")
    describe_parser.add_argument("--repository", default=".")
    describe_parser.add_argument("--staged", required=True)
    describe_parser.add_argument("--image", required=True)
    describe_parser.add_argument("--tag", required=True)
    describe_parser.add_argument("--digest", required=True)
    describe_parser.add_argument("--output", required=True)
    describe_parser.add_argument("--closure-evidence", default=str(runtime_closure.EVIDENCE))
    args = parser.parse_args()
    try:
        repository = Path(args.repository).resolve()
        if args.command == "stage":
            evidence = Path(args.evidence)
            if not evidence.is_absolute():
                evidence = repository / evidence
            stage(repository, Path(args.packages).resolve(), Path(args.output).resolve(), evidence.resolve())
        else:
            closure_evidence = Path(args.closure_evidence)
            if not closure_evidence.is_absolute():
                closure_evidence = repository / closure_evidence
            describe(
                repository,
                Path(args.staged).resolve(),
                args.image,
                args.tag,
                args.digest,
                Path(args.output).resolve(),
                closure_evidence.resolve(),
            )
        return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
