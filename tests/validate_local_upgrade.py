from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "scripts/upgrade_program_kit.py"


def load_updater():
    scripts = str(ROOT / "scripts")
    sys.path.insert(0, scripts)
    try:
        specification = importlib.util.spec_from_file_location("program_kit_upgrade", UPDATER)
        if specification is None or specification.loader is None:
            raise AssertionError("could not load release-owned updater")
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def validate_uv_launcher_bridge() -> None:
    if os.name != "nt":
        return
    updater = load_updater()
    with tempfile.TemporaryDirectory(prefix="program-kit-uv-launcher-") as value:
        root = Path(value)
        target = root / "consumer"
        target.mkdir()
        release = root / "release"
        bridge = release / "scripts/invoke_specify.py"
        bridge.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "scripts/invoke_specify.py", bridge)

        environment = root / "external-uv-tools/specify-cli"
        interpreter = environment / "Scripts/python.exe"
        interpreter.parent.mkdir(parents=True)
        interpreter.write_bytes(b"inaccessible uv Python launcher fixture")
        (environment / "pyvenv.cfg").write_text(
            "home = C:\\external\\uv\\python\nuv = 0.11.3\n", encoding="utf-8"
        )
        package = environment / "Lib/site-packages/specify_cli"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(
            "def main():\n"
            "    print('sandbox-compatible Specify fixture')\n"
            "    return 0\n",
            encoding="utf-8",
        )
        launcher = root / "external-bin/specify.exe"
        launcher.parent.mkdir()
        launcher.write_bytes(
            b"MZ-program-kit-invalid-executable-fixture\n#!"
            + str(interpreter).encode("utf-8")
            + b"\nfrom specify_cli import main\n"
        )
        before = sorted(path.relative_to(target).as_posix() for path in target.rglob("*"))
        original_probe = updater.run_specify_probe

        def probe(command, arguments, repository):
            if command == [str(launcher)]:
                return subprocess.CompletedProcess(
                    command + arguments,
                    101,
                    "",
                    f'Unable to create process using "{interpreter}" "{launcher}": Access is denied.',
                )
            return original_probe(command, arguments, repository)

        with patch.object(updater, "run_specify_probe", probe):
            resolved = updater.preflight_specify([str(launcher)], target, release)
        after = sorted(path.relative_to(target).as_posix() for path in target.rglob("*"))
        if before != after:
            raise AssertionError("uv launcher bridge preflight mutated the consumer repository")
        if resolved[:2] != [sys.executable, str(bridge.resolve())] or str(package.parent.resolve()) not in resolved:
            raise AssertionError(f"uv launcher did not resolve the release-owned bridge: {resolved}")
        probe = run(*resolved, "bundle", "install", "--help", cwd=target)
        require_success(probe, "sandbox-compatible uv Specify bridge")


def run(*command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, text=True, encoding="utf-8", errors="replace",
        capture_output=True, check=False,
    )


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        raise AssertionError(f"{label} failed:\n{result.stdout}{result.stderr}")


def version(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("  version:"):
            return line.split(":", 1)[1].strip().strip('"\'')
    raise AssertionError(f"No version in {path}")


def set_manifest_version(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    marker = f'  version: "{old}"'
    if marker not in text:
        raise AssertionError(f"Could not seed old version in {path}")
    path.write_text(text.replace(marker, f'  version: "{new}"', 1), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lifecycle_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    canonical = re.sub(r"(?m)^(\s*-\s+\[)[ xX](\]\s+)", r"\1 \2", text)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def seed_openapi_lifecycle(project: Path, old_runtime: str) -> Path:
    feature = project / "specs/001-openapi-upgrade"
    feature.mkdir(parents=True)
    spec = feature / "spec.md"
    plan = feature / "plan.md"
    tasks = feature / "tasks.md"
    research = feature / "research.md"
    spec.write_text(
        "# spec\n## Governance Traceability\n"
        "- **Specification roadmap entry**: SPC-001\n"
        "- **Architecture constraints**: accepted baseline\n"
        "- **Owned contracts and data**: Catalog.Api OpenAPI\n",
        encoding="utf-8",
    )
    plan.write_text(
        "# plan\n## Architecture Realization\n"
        "- **Roadmap entry and status transition**: SPC-001\n"
        "- **Vertical-slice path**: Catalog.Api OpenAPI to generated client\n"
        "- **Artifact ownership manifest**: artifact-ownership.json\n"
        f"Use ProgramKit.OpenApi.Exporter {old_runtime} for Catalog.Api OpenAPI.\n",
        encoding="utf-8",
    )
    tasks.write_text(
        "# tasks\n## Governance Completion Evidence\n"
        "- **Roadmap transition**: Delivered after evidence\n"
        "- **Path and ownership protection**: validated\n"
        f"- [ ] T001 Verify Catalog.Api OpenAPI exporter {old_runtime} with "
        "`contracts/openapi/catalog.contract.json`.\n",
        encoding="utf-8",
    )
    research.write_text(
        f"# Research\nUse ProgramKit.OpenApi.Exporter {old_runtime}.\n",
        encoding="utf-8",
    )
    canonical = {
        ".program-kit/evidence/runtime-closure.json",
        ".program-kit/evidence/host-image.json",
        ".program-kit/evidence/after-tasks-analysis.md",
        "docs/security/security-ledger.md",
        "tests/fixtures/program-kit/local-contract.json",
        "contracts/openapi/catalog.contract.json",
    }
    (feature / "artifact-ownership.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": feature.name,
                "profiles": ["program-kit", "dotnet", "typescript-vite"],
                "artifacts": [
                    {
                        "path": path,
                        "ownership": "consumer-owned" if path.endswith(".contract.json") else "evidence",
                        "classification": "internal",
                        "lifecycle": "source" if path.endswith(".contract.json") else "retained",
                    }
                    for path in sorted(canonical)
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    contract = project / "contracts/openapi/catalog.contract.json"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "identity": "catalog-v1",
                "documentName": "v1",
                "shell": "default",
                "producer": {"kind": "ProgramKit.OpenApi.Exporter", "version": old_runtime},
                "features": ["Catalog.Api"],
                "packageClosure": "artifacts/runnable-host/packages",
                "rawDocument": "artifacts/openapi/catalog.raw.json",
                "artifact": "contracts/openapi/catalog.json",
                "baseline": "contracts/openapi/catalog.baseline.json",
                "compatibility": {
                    "oasdiffVersion": "1.29.1",
                    "approval": "contracts/openapi/catalog.breaking-change.json",
                },
                "generator": {
                    "directory": "tools/openapi/catalog",
                    "packageJson": "tools/openapi/catalog/package.json",
                    "lockFile": "tools/openapi/catalog/package-lock.json",
                    "script": "generate",
                    "generatedTypes": "tools/openapi/catalog/generated/types.ts",
                },
                "application": {
                    "directory": "src/web",
                    "packageJson": "src/web/package.json",
                    "lockFile": "src/web/package-lock.json",
                    "script": "typecheck",
                    "tsconfig": "src/web/tsconfig.json",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project / ".program-kit/openapi-contracts.json").write_text(
        json.dumps({"schemaVersion": 1, "contracts": ["contracts/openapi/catalog.contract.json"]}) + "\n",
        encoding="utf-8",
    )
    candidate = feature / "npm-candidate.package.json"
    candidate.write_text('{"devDependencies":{"openapi-typescript":"7.13.0"}}\n', encoding="utf-8")
    npm_evidence = project / ".program-kit/evidence/npm-graph.json"
    npm_evidence.parent.mkdir(parents=True, exist_ok=True)
    npm_evidence.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "packageJson": candidate.relative_to(project).as_posix(),
                "packageJsonSha256": sha256(candidate),
                "satisfied": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    report = project / ".program-kit/evidence/after-tasks-analysis.md"
    report.write_text(
        "# Specification Analysis Report\n\n"
        "| ID | Category | Severity | Location(s) | Summary | Recommendation |\n"
        "|----|----------|----------|-------------|---------|----------------|\n"
        "| — | — | — | — | No findings | Proceed |\n",
        encoding="utf-8",
    )
    lifecycle = project / ".program-kit/lifecycle" / f"{feature.name}.json"
    lifecycle.parent.mkdir(parents=True, exist_ok=True)
    lifecycle.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": feature.name,
                "phases": {
                    "afterTasksAnalysis": {
                        "completedAtUtc": "2026-01-01T00:00:00Z",
                        "artifactHashes": {
                            "spec.md": sha256(spec),
                            "plan.md": sha256(plan),
                            "tasks.md": lifecycle_sha256(tasks),
                        },
                        "report": report.relative_to(project).as_posix(),
                        "reportSha256": sha256(report),
                        "severities": [],
                        "readyForImplementation": True,
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return feature


def main() -> int:
    validate_uv_launcher_bridge()
    expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    with tempfile.TemporaryDirectory(prefix="program-kit-local-upgrade-") as directory:
        project = Path(directory)
        initialized = run(
            "specify", "init", ".", "--force", "--non-interactive",
            "--integration", "codex", "--script", "py", "--ignore-agent-tools",
            cwd=project,
        )
        require_success(initialized, "Spec Kit initialization")
        primitive_commands = (
            ("specify", "workflow", "add", str(ROOT / "workflows/program-kit-bootstrap"), "--dev"),
            ("specify", "extension", "add", str(ROOT / "extensions/program-kit-governance"), "--dev", "--force"),
            ("specify", "extension", "add", str(ROOT / "extensions/program-kit-dotnet"), "--dev", "--force"),
            ("specify", "preset", "add", "--dev", str(ROOT / "presets/program-kit-governance-preset")),
        )
        for primitive in primitive_commands:
            require_success(run(*primitive, cwd=project), f"seed {' '.join(primitive[1:3])}")
        old = "0.0.0"
        manifests = (
            project / ".specify/extensions/program-kit-governance/extension.yml",
            project / ".specify/extensions/program-kit-dotnet/extension.yml",
            project / ".specify/presets/program-kit-governance-preset/preset.yml",
            project / ".specify/workflows/program-kit-bootstrap/workflow.yml",
        )
        for manifest in manifests:
            set_manifest_version(manifest, expected, old)
        workflow_registry_path = project / ".specify/workflows/workflow-registry.json"
        workflow_registry = json.loads(workflow_registry_path.read_text(encoding="utf-8"))
        workflow_registry["workflows"]["program-kit-bootstrap"]["version"] = old
        workflow_registry_path.write_text(json.dumps(workflow_registry), encoding="utf-8")
        preset_registry_path = project / ".specify/presets/.registry"
        preset_registry = json.loads(preset_registry_path.read_text(encoding="utf-8"))
        preset_registry["presets"]["program-kit-governance-preset"]["version"] = old
        preset_registry_path.write_text(json.dumps(preset_registry), encoding="utf-8")
        bundle_records = {
            "schema_version": "1.0",
            "bundles": [{
                "bundle_id": "program-kit",
                "version": old,
                "contributed_components": [
                    {"kind": "extensions", "id": "program-kit-governance", "version": old},
                    {"kind": "extensions", "id": "program-kit-dotnet", "version": old},
                    {"kind": "presets", "id": "program-kit-governance-preset", "version": old},
                ],
            }],
        }
        (project / ".specify/bundle-records.json").write_text(
            json.dumps(bundle_records), encoding="utf-8"
        )
        managed = project / ".program-kit/managed.json"
        managed.parent.mkdir(parents=True)
        managed.write_text(
            json.dumps({
                "schemaVersion": 1,
                "programKitVersion": old,
                "dotnetSdk": "10.0.202",
                "dotnetSdkSource": "program-kit-default",
                "webProfile": "none",
                "persistenceProfile": "none",
                "files": {},
            }),
            encoding="utf-8",
        )
        bootstrap_decisions = project / "docs/architecture/bootstrap-decisions.json"
        bootstrap_decisions.parent.mkdir(parents=True)
        bootstrap_decisions.write_text(
            json.dumps({
                "schema_version": "1.0",
                "default_profile": {"id": "program-kit-standard", "version": old},
                "selected_profiles": [],
                "dotnet": {
                    "host_runtime": "Custom.Host",
                    "host_source": "override",
                    "program_kit_host_opt_out": True,
                    "opt_out_reason": "Isolate the OpenAPI upgrade contract from host composition.",
                },
                "choices": [{
                    "id": "first-slice",
                    "decision": "Keep the accepted first slice",
                    "source": "explicit-intake",
                    "rationale": "It is the approved consumer outcome",
                    "override": "Use a later accepted decision",
                }],
                "overrides": [],
                "acknowledgements": [],
                "unresolved": [],
                "deferred": [],
            }),
            encoding="utf-8",
        )
        immutable_decisions = bootstrap_decisions.read_bytes()
        command = (
            sys.executable, str(UPDATER), "--release-root", str(ROOT),
            "--target", str(project), "--integration", "codex",
        )
        blocked_cli = project / "blocked_specify.py"
        blocked_cli.write_text(
            "import sys\nprint('sandbox denied the installed Specify interpreter', file=sys.stderr)\n"
            "raise SystemExit(101)\n",
            encoding="utf-8",
        )
        before_preflight = {
            path.relative_to(project).as_posix(): sha256(path)
            for path in project.rglob("*")
            if path.is_file()
        }
        blocked = run(
            *command,
            "--specify-command-json",
            json.dumps([sys.executable, str(blocked_cli)]),
            cwd=project,
        )
        after_preflight = {
            path.relative_to(project).as_posix(): sha256(path)
            for path in project.rglob("*")
            if path.is_file()
        }
        if blocked.returncode != 2 or "PKU112" not in blocked.stderr:
            raise AssertionError(f"inaccessible Specify launcher was not rejected:\n{blocked.stdout}{blocked.stderr}")
        if before_preflight != after_preflight or (project / ".specify/program-kit-upgrade.lock").exists():
            raise AssertionError("Specify executable preflight mutated the consumer repository")

        protected_skill = (
            project
            / ".agents/skills/speckit-program-kit-governance-bootstrap/SKILL.md"
        )
        original_mode = stat.S_IMODE(protected_skill.stat().st_mode)
        protected_skill.chmod(stat.S_IREAD)
        before_destination_preflight = {
            path.relative_to(project).as_posix(): sha256(path)
            for path in project.rglob("*")
            if path.is_file()
        }
        try:
            destination_blocked = run(*command, cwd=project)
        finally:
            protected_skill.chmod(original_mode | stat.S_IWRITE)
        after_destination_preflight = {
            path.relative_to(project).as_posix(): sha256(path)
            for path in project.rglob("*")
            if path.is_file()
        }
        if destination_blocked.returncode != 2 or "PKU115" not in destination_blocked.stderr:
            raise AssertionError(
                "protected integration destination was not rejected before mutation:\n"
                f"{destination_blocked.stdout}{destination_blocked.stderr}"
            )
        if "Resolve bundle composition record" in destination_blocked.stdout:
            raise AssertionError("destination permission preflight began component mutation")
        if before_destination_preflight != after_destination_preflight:
            raise AssertionError("destination permission preflight changed consumer file content")
        if "outside this sandbox" not in destination_blocked.stderr or "SKILL.md" not in destination_blocked.stderr:
            raise AssertionError("PKU115 omitted the blocked destination or copyable recovery route")

        partial_cli = project / "partial_specify.py"
        partial_cli.write_text(
            "import subprocess, sys\n"
            "args = sys.argv[1:]\n"
            "if args[:2] == ['extension', 'add'] and "
            "any(value.replace('\\\\', '/').endswith('/extensions/program-kit-governance') for value in args):\n"
            "    print('deliberate third-step failure', file=sys.stderr)\n"
            "    raise SystemExit(97)\n"
            "raise SystemExit(subprocess.run(['specify', *args], check=False).returncode)\n",
            encoding="utf-8",
        )
        partial = run(
            *command,
            "--specify-command-json",
            json.dumps([sys.executable, str(partial_cli)]),
            cwd=project,
        )
        if partial.returncode != 2 or "PKU105 Install governance extension" not in partial.stderr:
            raise AssertionError(f"partial sequential upgrade fixture did not fail at step three:\n{partial.stdout}{partial.stderr}")
        if "Resolve bundle composition record" not in partial.stdout or "Install bootstrap workflow" not in partial.stdout:
            raise AssertionError("partial sequential upgrade did not complete its first two mutations")
        partial_records = json.loads(
            (project / ".specify/bundle-records.json").read_text(encoding="utf-8")
        )["bundles"][0]
        if partial_records.get("version") != expected or version(manifests[0]) != old:
            raise AssertionError("partial upgrade fixture did not leave the expected mixed component state")

        installed = run(*command, cwd=project)
        require_success(installed, "local release upgrade")
        order = (
            "Resolve bundle composition record",
            "Install bootstrap workflow",
            "Install governance extension",
            "Install .NET extension",
            "Remove prior governance preset",
            "Install governance preset",
            "Resynchronize managed .NET baseline",
            "Verify managed .NET baseline convergence",
            "Validate cross-component version coherence",
            "Record accepted governed upgrade",
        )
        offsets = [installed.stdout.find(label) for label in order]
        if any(offset < 0 for offset in offsets) or offsets != sorted(offsets):
            raise AssertionError(f"Component mutations were not visibly sequential: {installed.stdout}")

        if {version(path) for path in manifests} != {expected}:
            raise AssertionError("Local release installation left mixed component manifests")
        state = json.loads(managed.read_text(encoding="utf-8"))
        if state.get("programKitVersion") != expected:
            raise AssertionError(f"Managed baseline did not advance to {expected}: {state}")
        final_records = json.loads(
            (project / ".specify/bundle-records.json").read_text(encoding="utf-8")
        )["bundles"][0]
        final_versions = {final_records["version"]} | {
            component["version"] for component in final_records["contributed_components"]
        }
        if final_versions != {expected}:
            raise AssertionError(f"Bundle record did not converge: {final_records}")
        if "Resynchronize managed .NET baseline" not in installed.stdout:
            raise AssertionError("Updater did not report managed baseline synchronization")
        if bootstrap_decisions.read_bytes() != immutable_decisions:
            raise AssertionError("Updater rewrote immutable bootstrap decisions")
        upgrade_state = json.loads(
            (project / ".specify/governance/program-kit-upgrades.json").read_text(
                encoding="utf-8"
            )
        )
        accepted = upgrade_state["upgrades"][-1]
        if (
            accepted.get("status") != "Accepted"
            or accepted.get("baseline_profile_version") != old
            or accepted.get("previous_installed_version") != old
            or accepted.get("installed_version") != expected
        ):
            raise AssertionError(f"Updater did not record governed version authority: {accepted}")

        old_runtime = "0.0.0-preview.1"
        target_runtime = (ROOT / "RUNTIME_VERSION").read_text(encoding="utf-8").strip()
        feature = seed_openapi_lifecycle(project, old_runtime)
        (project / "Program.slnx").write_text("<Solution />\n", encoding="utf-8")
        (project / "packages.lock.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "dependencies": {
                        "net10.0": {
                            "ProgramKit.Authentication": {
                                "type": "Direct",
                                "requested": f"[{old_runtime}, )",
                                "resolved": old_runtime,
                            }
                        }
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        contract_path = project / "contracts/openapi/catalog.contract.json"
        contract_before = contract_path.read_bytes()
        pending = run(*command, cwd=project)
        if pending.returncode != 2 or "PKU110" not in pending.stderr:
            raise AssertionError(f"stale consumer OpenAPI pin did not stop before upgrade:\n{pending.stdout}{pending.stderr}")
        if "Resolve bundle composition record" in pending.stdout or contract_path.read_bytes() != contract_before:
            raise AssertionError("OpenAPI reconciliation preflight mutated components or consumer contracts")
        for expected_path in (
            "contracts/openapi/catalog.contract.json",
            "specs/001-openapi-upgrade/spec.md",
            "specs/001-openapi-upgrade/plan.md",
            "specs/001-openapi-upgrade/tasks.md",
            "specs/001-openapi-upgrade/research.md",
        ):
            if expected_path not in pending.stderr:
                raise AssertionError(f"Reconciliation diagnostic omitted affected/review path: {expected_path}")

        accepted_command = (*command, "--accept-openapi-producer-pin-reconciliation")
        reconciled = run(*accepted_command, cwd=project)
        if (
            reconciled.returncode != 3
            or "PKU111" not in reconciled.stderr
            or "PKU113" not in reconciled.stderr
        ):
            raise AssertionError(
                f"explicit OpenAPI reconciliation did not require lifecycle renewal:\n"
                f"{reconciled.stdout}{reconciled.stderr}"
            )
        contract_value = json.loads(contract_path.read_text(encoding="utf-8"))
        if contract_value["producer"]["version"] != target_runtime:
            raise AssertionError("registered OpenAPI producer pin did not advance atomically")
        for name in ("plan.md", "tasks.md", "research.md"):
            text = (feature / name).read_text(encoding="utf-8")
            if old_runtime in text or target_runtime not in text:
                raise AssertionError(f"exact OpenAPI planning pin did not advance in {name}")
        lifecycle_path = project / ".program-kit/lifecycle/001-openapi-upgrade.json"
        lifecycle_value = json.loads(lifecycle_path.read_text(encoding="utf-8"))
        if "afterTasksAnalysis" in lifecycle_value["phases"]:
            raise AssertionError("producer-pin reconciliation retained stale implementation readiness")
        invalidation = lifecycle_value.get("invalidations", [])[-1]
        if (
            invalidation.get("reason") != "program-kit-openapi-producer-pin-reconciliation"
            or invalidation.get("fromVersions") != [old_runtime]
            or invalidation.get("toVersion") != target_runtime
        ):
            raise AssertionError(f"lifecycle invalidation audit is incomplete: {invalidation}")
        lock_renewal = json.loads(
            (project / ".program-kit/evidence/dotnet-lock-renewal.json").read_text(encoding="utf-8")
        )
        expected_commands = [
            "pwsh -NoProfile -File .program-kit/eng/Restore.ps1 -Subject Program.slnx -ForceEvaluate",
            "pwsh -NoProfile -File .program-kit/eng/Restore.ps1 -Subject Program.slnx -LockedMode",
        ]
        if (
            lock_renewal.get("targetRuntimeVersion") != target_runtime
            or lock_renewal.get("affectedLocks") != ["packages.lock.json"]
            or lock_renewal.get("renewalCommands") != expected_commands
            or lock_renewal.get("satisfied") is not False
        ):
            raise AssertionError(f"NuGet lock renewal evidence is incomplete: {lock_renewal}")

        sync = project / ".specify/extensions/program-kit-dotnet/scripts/dotnet_sync.py"
        require_success(
            run(
                sys.executable,
                str(sync),
                "--target",
                str(project),
                "--profile-selected",
                "--persistence-profile",
                "none",
                "--web-profile",
                "none",
                "--check",
                cwd=project,
            ),
            "post-reconciliation managed sync check",
        )
        ownership = project / ".specify/extensions/program-kit-governance/scripts/artifact_ownership.py"
        require_success(
            run(
                sys.executable,
                str(ownership),
                "--manifest",
                str(feature / "artifact-ownership.json"),
                "--plan",
                str(feature / "plan.md"),
                "--tasks",
                str(feature / "tasks.md"),
                cwd=project,
            ),
            "post-reconciliation artifact ownership",
        )
        preflight = project / ".specify/extensions/program-kit-governance/scripts/implementation_preflight.py"
        stale = run(
            sys.executable,
            str(preflight),
            "--repository",
            str(project),
            "--feature-dir",
            str(feature),
            cwd=project,
        )
        if stale.returncode != 11 or "PKL011" not in stale.stderr:
            raise AssertionError("implementation preflight did not block invalidated lifecycle readiness")
        lifecycle_script = project / ".specify/extensions/program-kit-governance/scripts/lifecycle_state.py"
        require_success(
            run(
                sys.executable,
                str(lifecycle_script),
                "--repository",
                str(project),
                "--feature-dir",
                str(feature),
                "begin",
                "analyze",
                cwd=project,
            ),
            "renewed analysis begin",
        )
        require_success(
            run(
                sys.executable,
                str(lifecycle_script),
                "--repository",
                str(project),
                "--feature-dir",
                str(feature),
                "complete-analysis",
                "--report",
                ".program-kit/evidence/after-tasks-analysis.md",
                cwd=project,
            ),
            "renewed analysis completion",
        )
        require_success(
            run(
                sys.executable,
                str(preflight),
                "--repository",
                str(project),
                "--feature-dir",
                str(feature),
                cwd=project,
            ),
            "full mandatory implementation preflight after renewal",
        )

        lock_value = json.loads((project / "packages.lock.json").read_text(encoding="utf-8"))
        dependency = lock_value["dependencies"]["net10.0"]["ProgramKit.Authentication"]
        dependency["requested"] = f"[{target_runtime}, )"
        dependency["resolved"] = target_runtime
        (project / "packages.lock.json").write_text(
            json.dumps(lock_value, indent=2) + "\n",
            encoding="utf-8",
        )
        require_success(run(*command, cwd=project), "upgrade convergence after lock renewal")
        satisfied_renewal = json.loads(
            (project / ".program-kit/evidence/dotnet-lock-renewal.json").read_text(encoding="utf-8")
        )
        if (
            satisfied_renewal.get("targetRuntimeVersion") != target_runtime
            or satisfied_renewal.get("reason") != "program-kit-runtime-locks-verified"
            or satisfied_renewal.get("satisfied") is not True
        ):
            raise AssertionError(f"NuGet lock renewal did not converge: {satisfied_renewal}")

        lock = project / ".specify/program-kit-upgrade.lock"
        lock.write_text("test lock\n", encoding="utf-8")
        locked = run(*command, cwd=project)
        if locked.returncode != 2 or "PKU106" not in locked.stderr:
            raise AssertionError("Concurrent component mutation lock was not rejected")
        if not lock.is_file():
            raise AssertionError("Updater removed a lock it did not own")

    print("Sequential offline/local Program Kit upgrade and coherence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
