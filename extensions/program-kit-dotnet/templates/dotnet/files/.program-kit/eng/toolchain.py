from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import js_toolchain
import oasdiff_cli


def configure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def required_versions(repository: Path, include_openapi: bool = False) -> dict[str, str]:
    global_json = json.loads((repository / "global.json").read_text(encoding="utf-8"))
    dotnet = global_json.get("sdk", {}).get("version")
    node = (repository / ".nvmrc").read_text(encoding="utf-8").strip().removeprefix("v")
    npm = (repository / ".npm-version").read_text(encoding="utf-8").strip().removeprefix("v")
    if not isinstance(dotnet, str) or not dotnet or not node or not npm:
        raise ValueError("PKT001 managed global.json, .nvmrc, or .npm-version has no exact toolchain version.")
    required = {"dotnet": dotnet, "node": node, "npm": npm}
    if include_openapi:
        oasdiff = (repository / ".oasdiff-version").read_text(encoding="utf-8").strip().removeprefix("v")
        if not oasdiff:
            raise ValueError("PKT001 managed .oasdiff-version has no exact tool version.")
        required["oasdiff"] = oasdiff
    return required


def run_version(command: list[str], repository: Path) -> str | None:
    return js_toolchain.version(command, repository)


def oasdiff_version(command: Path, repository: Path) -> str | None:
    version, _ = oasdiff_cli.detect(command, repository)
    return version


def resolve_oasdiff(repository: Path, required: str, requested: str) -> tuple[Path | None, str | None]:
    names = ("oasdiff.exe", "oasdiff.cmd", "oasdiff.bat") if os.name == "nt" else ("oasdiff",)
    candidates = [repository / ".program-kit/tools/oasdiff" / required / name for name in names]
    requested_path = js_toolchain.executable(requested)
    if requested_path:
        candidates.append(requested_path)
    actual: str | None = None
    for candidate in candidates:
        if candidate.is_file():
            actual = oasdiff_version(candidate.resolve(), repository)
            if actual == required:
                return candidate.resolve(), actual
    return None, actual


def resolve(
    repository: Path,
    required: dict[str, str],
    dotnet_command: str,
    node_command: str,
    npm_command: str,
    manager: str,
    oasdiff_command: str,
) -> tuple[dict[str, str | None], dict[str, list[str]]]:
    dotnet = js_toolchain.executable(dotnet_command)
    dotnet_version = run_version([str(dotnet)], repository) if dotnet else None
    node, node_version = js_toolchain.resolve_node(repository, required["node"], node_command, manager)
    npm: list[str] | None = None
    npm_version: str | None = None
    if node:
        npm, npm_version = js_toolchain.resolve_npm(repository, node, required["npm"], npm_command)
    commands: dict[str, list[str]] = {}
    if dotnet:
        commands["dotnet"] = [str(dotnet)]
    if node:
        commands["node"] = [str(node)]
    else:
        requested_node = js_toolchain.executable(node_command)
        if requested_node:
            commands["node"] = [str(requested_node)]
            node_version = run_version(commands["node"], repository)
    if npm:
        commands["npm"] = npm
    elif node:
        candidates = js_toolchain.npm_candidates(node, npm_command)
        if candidates:
            commands["npm"] = candidates[0]
    installed: dict[str, str | None] = {
        "dotnet": dotnet_version,
        "node": node_version,
        "npm": npm_version,
    }
    if "oasdiff" in required:
        oasdiff, resolved_version = resolve_oasdiff(repository, required["oasdiff"], oasdiff_command)
        installed["oasdiff"] = resolved_version
        if oasdiff:
            commands["oasdiff"] = [str(oasdiff)]
    return installed, commands


def evidence_value(
    repository: Path, required: dict, installed: dict, commands: dict, satisfied: bool
) -> dict:
    cache = js_toolchain.cache_directory(repository)
    _, trust_mode, extra_ca = js_toolchain.trust_environment(repository, cache)
    return {
        "schemaVersion": 2,
        "required": required,
        "resolved": installed,
        "commands": commands,
        "environment": {
            "npmCache": str(cache),
            "trustMode": trust_mode,
            "extraCaCertificates": extra_ca,
            "strictSsl": True,
        },
        "satisfied": satisfied,
    }


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


def failure_path(path: Path) -> Path:
    return path.with_name(path.stem + ".failure" + path.suffix)


def has_satisfied_evidence(path: Path) -> bool:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("satisfied") is True
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


def write_evidence(
    path: Path,
    repository: Path,
    required: dict,
    installed: dict,
    commands: dict,
    satisfied: bool,
) -> None:
    value = evidence_value(repository, required, installed, commands, satisfied)
    if satisfied:
        atomic_write(path, value)
        failure_path(path).unlink(missing_ok=True)
    elif has_satisfied_evidence(path):
        value["reason"] = "toolchain-resolution-failed"
        value["previousEvidencePreserved"] = True
        atomic_write(failure_path(path), value)
    else:
        atomic_write(path, value)


def mismatch(required: dict[str, str], installed: dict[str, str | None]) -> list[str]:
    return [name for name, expected in required.items() if installed.get(name) != expected]


def install_dotnet(version: str, installer: str) -> None:
    if not installer:
        raise ValueError(
            "PKT004 no approved .NET installer is available. Obtain Microsoft's dotnet-install script, "
            "review it, and pass --dotnet-installer; Program Kit will use side-by-side installation."
        )
    path = Path(installer).resolve()
    if not path.is_file():
        raise ValueError(f"PKT005 .NET installer is unavailable: {path}")
    command = ["powershell", "-NoProfile", "-File", str(path), "-Version", version] if path.suffix.lower() == ".ps1" else [str(path), "--version", version]
    if subprocess.run(command, check=False).returncode != 0:
        raise ValueError("PKT006 approved .NET side-by-side installation failed (offline or installer error).")


def node_manager(selected: str) -> tuple[str, str] | None:
    names = [selected] if selected != "auto" else ["fnm", "nvm", "volta"]
    for name in names:
        command = js_toolchain.executable(name)
        if command:
            return name, str(command)
    return None


def install_node(version: str, selected: str) -> None:
    resolved_manager = node_manager(selected)
    if resolved_manager is None:
        raise ValueError(
            "PKT007 no selected Node version manager is available. Install or select fnm, nvm, or volta; "
            "Program Kit does not replace the user's manager. On Windows prefer an official per-user "
            "fnm route (winget, Scoop, or the release binary); do not fall back to an elevation-bound "
            "Chocolatey install from a non-administrator shell."
        )
    manager, command = resolved_manager
    arguments = [command, "install", version if manager != "volta" else f"node@{version}"]
    if subprocess.run(arguments, check=False).returncode != 0:
        raise ValueError("PKT008 approved Node installation failed (offline or manager error).")


def install_npm(repository: Path, node: Path, required: str, requested: str) -> None:
    candidates = js_toolchain.npm_candidates(node, requested)
    cache = js_toolchain.cache_directory(repository)
    environment, _, _ = js_toolchain.trust_environment(repository, cache)
    environment["PATH"] = str(node.parent) + os.pathsep + environment.get("PATH", "")
    current = next(
        (command for command in candidates if js_toolchain.version(command, repository, environment)),
        None,
    )
    if current is None:
        raise ValueError("PKT018 pinned Node is installed but has no usable npm CLI for approved remediation.")
    result = subprocess.run(
        current + ["--strict-ssl=true", "install", "--global", f"npm@{required}"],
        cwd=repository,
        env=environment,
        check=False,
        timeout=300,
    )
    if result.returncode != 0:
        raise ValueError("PKT019 approved npm installation failed; inspect the visible TLS/cache diagnostic.")


def install_oasdiff(repository: Path, version: str, binary: str) -> None:
    if not binary:
        raise ValueError(
            "PKT020 no reviewed oasdiff binary was supplied. Download the official binary for the managed "
            f"{version} pin, verify its release provenance, and pass --oasdiff-binary."
        )
    source = Path(binary).resolve()
    if not source.is_file() or oasdiff_version(source, repository) != version:
        raise ValueError(f"PKT021 supplied oasdiff binary is missing or does not report version {version}")
    suffix = source.suffix.casefold() if os.name == "nt" else ""
    if os.name == "nt" and suffix not in {".exe", ".cmd", ".bat"}:
        raise ValueError("PKT021 supplied Windows oasdiff binary must be an .exe, .cmd, or .bat file")
    name = "oasdiff" + suffix if os.name == "nt" else "oasdiff"
    destination = repository / ".program-kit/tools/oasdiff" / version / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    if os.name != "nt":
        destination.chmod(0o755)


def main() -> int:
    configure_utf8()
    parser = argparse.ArgumentParser(description="Resolve and approval-gate the exact Program Kit toolchain.")
    parser.add_argument("--repository", default=".")
    parser.add_argument("--evidence", default=".program-kit/evidence/toolchain.json")
    parser.add_argument("--remediate", action="store_true")
    parser.add_argument("--approve", action="store_true", help="Explicit non-interactive approval for system/network changes")
    parser.add_argument("--decline", action="store_true")
    parser.add_argument("--dotnet-installer", default="")
    parser.add_argument("--node-manager", choices=("auto", "fnm", "nvm", "volta"), default="auto")
    parser.add_argument("--include-openapi", action="store_true")
    parser.add_argument("--oasdiff-binary", default="")
    parser.add_argument("--dotnet-command", default="dotnet", help=argparse.SUPPRESS)
    parser.add_argument("--node-command", default="node", help=argparse.SUPPRESS)
    parser.add_argument("--npm-command", default="", help=argparse.SUPPRESS)
    parser.add_argument("--oasdiff-command", default="oasdiff", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        repository = Path(args.repository).resolve()
        evidence = Path(args.evidence)
        if not evidence.is_absolute():
            evidence = repository / evidence
        required = required_versions(repository, args.include_openapi)
        installed, commands = resolve(
            repository, required, args.dotnet_command, args.node_command, args.npm_command,
            args.node_manager, args.oasdiff_command
        )
        missing = mismatch(required, installed)
        if not missing:
            write_evidence(evidence, repository, required, installed, commands, True)
            print("PKT000 exact managed toolchain commands are resolved and satisfied")
            return 0
        print(
            "PKT002 toolchain mismatch: "
            + ", ".join(
                f"{name} required={required[name]} executable={commands.get(name, 'missing')} actual={installed[name] or 'missing'}"
                for name in missing
            ),
            file=sys.stderr,
        )
        print(
            "PKT011 Program Kit managed pins remain authoritative. Install or upgrade to the exact "
            "required versions; do not rewrite them to match PATH without an explicit managed-toolchain-version override.",
            file=sys.stderr,
        )
        write_evidence(evidence, repository, required, installed, commands, False)
        if not args.remediate:
            print("Repository writes: evidence/cache only. System changes and downloads require approval.", file=sys.stderr)
            return 2
        if args.decline:
            print("PKT003 remediation declined; no installer was run.", file=sys.stderr)
            return 3
        approved = args.approve or input(
            "Install the exact missing SDK/Node/npm tools and/or stage the reviewed oasdiff binary? [y/N] "
        ).strip().lower() == "y"
        if not approved:
            print("PKT003 remediation declined; no installer was run.", file=sys.stderr)
            return 3
        if "dotnet" in missing:
            install_dotnet(required["dotnet"], args.dotnet_installer)
        if "node" in missing:
            install_node(required["node"], args.node_manager)
        if "oasdiff" in missing:
            install_oasdiff(repository, required["oasdiff"], args.oasdiff_binary)
        interim, interim_commands = resolve(
            repository, required, args.dotnet_command, args.node_command, args.npm_command,
            args.node_manager, args.oasdiff_command
        )
        if "npm" in mismatch(required, interim):
            node_values = interim_commands.get("node")
            if not node_values:
                raise ValueError("PKT009 installation completed, but the pinned Node executable cannot be resolved.")
            install_npm(repository, Path(node_values[0]), required["npm"], args.npm_command)
        resolved, resolved_commands = resolve(
            repository, required, args.dotnet_command, args.node_command, args.npm_command,
            args.node_manager, args.oasdiff_command
        )
        remaining = mismatch(required, resolved)
        write_evidence(evidence, repository, required, resolved, resolved_commands, not remaining)
        if remaining:
            raise ValueError("PKT009 installation completed, but exact command checks still fail: " + ", ".join(remaining))
        print("PKT010 approved toolchain remediation completed and exact commands were re-verified")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
