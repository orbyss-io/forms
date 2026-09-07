from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def version(command: list[str], cwd: Path, environment: dict[str, str] | None = None) -> str | None:
    try:
        result = subprocess.run(
            command + ["--version"],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip().splitlines()[0].removeprefix("v")


def executable(value: str) -> Path | None:
    candidate = Path(value)
    if candidate.is_file():
        return candidate.resolve()
    resolved = shutil.which(value)
    return Path(resolved).resolve() if resolved else None


def known_node_candidates(required: str) -> list[Path]:
    roots: list[Path] = []
    configured = os.environ.get("FNM_DIR")
    if configured:
        roots.append(Path(configured))
    local = os.environ.get("LOCALAPPDATA")
    roaming = os.environ.get("APPDATA")
    if local:
        roots.append(Path(local) / "fnm")
    if roaming:
        roots.append(Path(roaming) / "fnm")
    home = Path.home()
    roots.extend([home / ".local/share/fnm", home / ".fnm"])
    result: list[Path] = []
    for root in roots:
        for label in (f"v{required}", required):
            installation = root / "node-versions" / label / "installation"
            result.extend([installation / "node.exe", installation / "bin/node"])
    explicit = os.environ.get("PROGRAMKIT_NODE_EXECUTABLE")
    if explicit:
        result.insert(0, Path(explicit))
    return result


def manager_node(required: str, selected: str) -> Path | None:
    names = [selected] if selected != "auto" else ["fnm", "volta", "nvm"]
    for name in names:
        manager = shutil.which(name)
        if not manager:
            continue
        if name == "fnm":
            command = [manager, "exec", f"--using={required}", "node", "-p", "process.execPath"]
        elif name == "volta":
            command = [manager, "run", "--node", required, "node", "-p", "process.execPath"]
        else:
            root = subprocess.run(
                [manager, "root"], capture_output=True, text=True, check=False, timeout=10
            ).stdout.strip()
            for candidate in (
                Path(root) / f"v{required}" / "node.exe",
                Path(root) / required / "node.exe",
                Path(root) / f"v{required}" / "bin/node",
            ):
                if candidate.is_file():
                    return candidate.resolve()
            continue
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, check=False, timeout=10
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        candidate = Path(result.stdout.strip())
        if result.returncode == 0 and candidate.is_file():
            return candidate.resolve()
    return None


def resolve_node(repository: Path, required: str, requested: str, manager: str) -> tuple[Path | None, str | None]:
    candidates: list[Path] = []
    direct = executable(requested)
    if direct:
        candidates.append(direct)
    if requested == "node":
        candidates.extend(known_node_candidates(required))
    managed = manager_node(required, manager)
    if managed:
        candidates.append(managed)
    seen: set[Path] = set()
    actual: str | None = None
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        actual = version([str(resolved)], repository)
        if actual == required:
            return resolved, actual
    return None, actual


def npm_candidates(node: Path, requested: str) -> list[list[str]]:
    result: list[list[str]] = []
    explicit = os.environ.get("PROGRAMKIT_NPM_EXECUTABLE") or requested
    if explicit:
        resolved = executable(explicit)
        if resolved:
            if resolved.suffix.casefold() == ".js":
                result.append([str(node), str(resolved)])
            elif resolved.parent == node.parent:
                result.append([str(resolved)])
    directory = node.parent
    if os.name == "nt":
        for candidate in (directory / "npm.cmd", directory / "npm.exe"):
            if candidate.is_file():
                result.append([str(candidate.resolve())])
    for candidate in (
        directory / "node_modules/npm/bin/npm-cli.js",
        directory.parent / "lib/node_modules/npm/bin/npm-cli.js",
    ):
        if candidate.is_file():
            result.append([str(node), str(candidate.resolve())])
    if os.name != "nt":
        candidate = directory / "npm"
        if candidate.is_file():
            result.append([str(candidate.resolve())])
    return result


def resolve_npm(repository: Path, node: Path, required: str, requested: str) -> tuple[list[str] | None, str | None]:
    actual: str | None = None
    environment = os.environ.copy()
    environment["PATH"] = str(node.parent) + os.pathsep + environment.get("PATH", "")
    for command in npm_candidates(node, requested):
        actual = version(command, repository, environment)
        if actual == required:
            return command, actual
    return None, actual


def require_writable_cache(cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    descriptor = -1
    probe: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".program-kit-write-probe-", dir=cache)
        probe = Path(name)
        os.close(descriptor)
        descriptor = -1
    except OSError as error:
        raise ValueError(f"PKT014 npm cache is not writable: {cache}: {error}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if probe is not None:
            try:
                probe.unlink()
            except OSError:
                pass
    return cache


def cache_directory(repository: Path) -> Path:
    configured = os.environ.get("PROGRAMKIT_NPM_CACHE")
    cache = Path(configured).expanduser() if configured else repository / ".program-kit/cache/npm"
    if not cache.is_absolute():
        cache = repository / cache
    return require_writable_cache(cache.resolve())


def trust_environment(
    repository: Path,
    cache: Path,
    selected_mode: str | None = None,
    selected_extra_ca: str | None = None,
) -> tuple[dict[str, str], str, str]:
    if os.environ.get("NPM_CONFIG_STRICT_SSL", "").casefold() == "false":
        raise ValueError("PKT015 NPM_CONFIG_STRICT_SSL=false is forbidden; configure system trust or an organization CA.")
    trust_mode = (
        selected_mode
        if selected_mode is not None
        else os.environ.get("PROGRAMKIT_NODE_TRUST_MODE", "system" if os.name == "nt" else "bundled")
    ).casefold()
    if trust_mode not in {"bundled", "system"}:
        raise ValueError("PKT015 PROGRAMKIT_NODE_TRUST_MODE must be bundled or system.")
    environment = os.environ.copy()
    environment["NPM_CONFIG_CACHE"] = str(cache)
    environment["NPM_CONFIG_STRICT_SSL"] = "true"
    if trust_mode == "system":
        existing = environment.get("NODE_OPTIONS", "").strip()
        if "--use-system-ca" not in existing.split():
            environment["NODE_OPTIONS"] = (existing + " --use-system-ca").strip()
    extra_ca = (
        selected_extra_ca
        if selected_extra_ca is not None
        else os.environ.get("PROGRAMKIT_NODE_EXTRA_CA_CERTS", "")
    ).strip()
    if extra_ca:
        path = Path(extra_ca)
        if not path.is_absolute():
            path = repository / path
        path = path.resolve()
        if not path.is_file():
            raise ValueError(f"PKT015 configured organization CA file is missing: {path}")
        environment["NODE_EXTRA_CA_CERTS"] = str(path)
        extra_ca = str(path)
    return environment, trust_mode, extra_ca


def context(repository: Path, evidence_path: Path) -> tuple[list[str], dict[str, str]]:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    required = evidence.get("required", {})
    resolved = evidence.get("resolved", {})
    commands = evidence.get("commands", {})
    npm = commands.get("npm") if isinstance(commands, dict) else None
    if (
        evidence.get("satisfied") is not True
        or not isinstance(npm, list)
        or not npm
        or resolved.get("node") != required.get("node")
        or resolved.get("npm") != required.get("npm")
    ):
        raise ValueError(
            "PKT016 exact Node/npm command evidence is missing or stale; run .program-kit/eng/toolchain.py first."
        )
    if any(not isinstance(item, str) or not item for item in npm):
        raise ValueError("PKT016 recorded npm command is invalid.")
    for index in range(min(2, len(npm))):
        if index == 1 and Path(npm[index]).suffix.casefold() != ".js":
            continue
        if not Path(npm[index]).is_file():
            raise ValueError(f"PKT016 recorded npm command path is missing: {npm[index]}")
    node_command = commands.get("node") if isinstance(commands, dict) else None
    if not isinstance(node_command, list) or len(node_command) != 1 or not Path(node_command[0]).is_file():
        raise ValueError("PKT016 recorded Node command is invalid or missing.")
    validation_environment = os.environ.copy()
    validation_environment["PATH"] = (
        str(Path(node_command[0]).parent) + os.pathsep + validation_environment.get("PATH", "")
    )
    actual_node = version(list(node_command), repository, validation_environment)
    actual_npm = version(list(npm), repository, validation_environment)
    if actual_node != required.get("node") or actual_npm != required.get("npm"):
        raise ValueError(
            "PKT017 pinned JavaScript runtime cannot be used: "
            f"node required={required.get('node')} executable={commands.get('node')} actual={actual_node or 'missing'}; "
            f"npm required={required.get('npm')} executable={npm} actual={actual_npm or 'missing'}."
        )
    recorded_environment = evidence.get("environment", {})
    cache_value = recorded_environment.get("npmCache") if isinstance(recorded_environment, dict) else None
    if not isinstance(cache_value, str) or not cache_value:
        raise ValueError("PKT016 recorded npm cache is missing.")
    cache = Path(cache_value)
    require_writable_cache(cache)
    environment, _, _ = trust_environment(
        repository,
        cache,
        str(recorded_environment.get("trustMode", "")),
        str(recorded_environment.get("extraCaCertificates", "")),
    )
    environment["PATH"] = str(Path(node_command[0]).parent) + os.pathsep + environment.get("PATH", "")
    return list(npm), environment


def run_npm(
    repository: Path,
    evidence_path: Path,
    arguments: list[str],
    cwd: Path,
    timeout: int,
    capture_stdout: bool = False,
) -> subprocess.CompletedProcess[str]:
    npm, environment = context(repository, evidence_path)
    command = npm + ["--strict-ssl=true"] + arguments
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE if capture_stdout else None,
        stderr=None,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run npm through Program Kit's exact resolved Node runtime.")
    parser.add_argument("--repository", default=".")
    parser.add_argument("--evidence", default=".program-kit/evidence/toolchain.json")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("command", choices=("npm",))
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        repository = Path(args.repository).resolve()
        evidence = Path(args.evidence)
        if not evidence.is_absolute():
            evidence = repository / evidence
        arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
        result = run_npm(repository, evidence, arguments, Path.cwd(), args.timeout_seconds)
        return result.returncode
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
