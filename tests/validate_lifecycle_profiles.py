from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

import yaml


ROOT = Path(__file__).resolve().parents[1]


def module(path: Path, name: str):
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {path}")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def analysis_report(rows: list[tuple[str, str, str, str, str, str]] | None = None) -> str:
    rendered = [
        "# Specification Analysis Report",
        "",
        "| ID | Category | Severity | Location(s) | Summary | Recommendation |",
        "|----|----------|----------|-------------|---------|----------------|",
    ]
    if rows is None:
        rendered.append("| — | — | — | — | No findings | Proceed |")
    else:
        rendered.extend("| " + " | ".join(row) + " |" for row in rows)
    rendered.extend(["", "## Metrics", "", "- Critical findings: 0", ""])
    return "\n".join(rendered)


def validate_hooks() -> None:
    manifest = yaml.safe_load(
        (ROOT / "extensions/program-kit-governance/extension.yml").read_text(encoding="utf-8")
    )
    expected = {
        "after_specify": ["speckit.clarify", "speckit.program-kit-governance.architecture-check"],
        "after_tasks": ["speckit.analyze", "speckit.program-kit-governance.architecture-check"],
    }
    for event, commands in expected.items():
        entries = manifest["hooks"][event]
        if [entry["command"] for entry in entries] != commands:
            raise AssertionError(f"{event} hook ordering is invalid")
        if [entry["priority"] for entry in entries] != [5, 10]:
            raise AssertionError(f"{event} priorities are invalid")
        for entry in entries:
            if entry.get("enabled") is not True or entry.get("optional") is not False or entry.get("condition", "missing") is not None:
                raise AssertionError(f"{event} hook is not unconditionally mandatory: {entry}")


def validate_lifecycle() -> None:
    lifecycle = module(
        ROOT / "extensions/program-kit-governance/scripts/lifecycle_state.py", "lifecycle_state"
    )
    with tempfile.TemporaryDirectory(prefix="program-kit-lifecycle-") as value:
        repository = Path(value)
        feature = repository / "specs/SPC-001"
        feature.mkdir(parents=True)
        (feature / "spec.md").write_text(
            "# spec\n## Governance Traceability\n- **Specification roadmap entry**: SPC-001\n"
            "- **Architecture constraints**: accepted baseline\n- **Owned contracts and data**: none\nUnicode ✓\n",
            encoding="utf-8",
        )
        (feature / "plan.md").write_text(
            "# plan\n## Architecture Realization\n- **Roadmap entry and status transition**: SPC-001\n"
            "- **Vertical-slice path**: input to output\n- **Artifact ownership manifest**: artifact-ownership.json\n",
            encoding="utf-8",
        )
        (feature / "tasks.md").write_text(
            "# tasks\n## Governance Completion Evidence\n- **Roadmap transition**: Delivered after evidence\n"
            "- **Path and ownership protection**: validated\n- [ ] T001 Confirm governance evidence.\n",
            encoding="utf-8",
        )
        canonical = [
            {"path": path, "ownership": "evidence", "classification": "internal", "lifecycle": "retained"}
            for path in sorted(
                {
                    ".program-kit/evidence/runtime-closure.json",
                    ".program-kit/evidence/host-image.json",
                    ".program-kit/evidence/after-tasks-analysis.md",
                    "docs/security/security-ledger.md",
                    "tests/fixtures/program-kit/local-contract.json",
                }
            )
        ]
        (feature / "artifact-ownership.json").write_text(
            json.dumps({"schemaVersion": 1, "feature": "SPC-001", "profiles": ["program-kit"], "artifacts": canonical}),
            encoding="utf-8",
        )
        if lifecycle.begin(repository, feature, "clarify", False) != 0:
            raise AssertionError("clarification did not start")
        if lifecycle.begin(repository, feature, "clarify", False) != 4:
            raise AssertionError("reentrant clarification was not rejected")
        if lifecycle.begin(repository, feature, "clarify", True) != 0:
            raise AssertionError("interrupted clarification did not resume")
        if lifecycle.complete_clarify(repository, feature, "no-questions") != 0:
            raise AssertionError("no-question clarification did not complete")

        report = repository / ".program-kit/evidence/after-tasks-analysis.md"
        report.parent.mkdir(parents=True)
        report.write_text(
            "## Severity legend\n\nCRITICAL and HIGH findings block; MEDIUM and LOW findings do not.\n\n"
            + analysis_report(),
            encoding="utf-8",
        )
        if lifecycle.begin(repository, feature, "analyze", False) != 0:
            raise AssertionError("analysis did not start")
        if lifecycle.complete_analysis(repository, feature, report) != 0:
            raise AssertionError("clean analysis did not complete")
        clean_state = json.loads(lifecycle.state_path(repository, feature).read_text(encoding="utf-8"))
        clean_analysis = clean_state["phases"]["afterTasksAnalysis"]
        if clean_analysis["findingCount"] != 0 or clean_analysis["findings"] or clean_analysis["severities"]:
            raise AssertionError("zero metrics or severity prose produced false findings")
        if lifecycle.verify_before_implement(repository, feature) != 0:
            raise AssertionError("current analysis did not authorize implementation")

        report.write_text(
            analysis_report(
                [
                    ("T1", "Terminology", "MEDIUM", "spec.md:L10", "Term drift", "Align wording"),
                    ("S1", "Style", "LOW", "tasks.md:L20", "Minor wording", "Clarify"),
                ]
            ),
            encoding="utf-8",
        )
        if lifecycle.begin(repository, feature, "analyze", False) != 0:
            raise AssertionError("non-blocking analysis did not start")
        if lifecycle.complete_analysis(repository, feature, report) != 0:
            raise AssertionError("MEDIUM/LOW analysis did not remain implementation-ready")
        nonblocking_state = json.loads(lifecycle.state_path(repository, feature).read_text(encoding="utf-8"))
        nonblocking = nonblocking_state["phases"]["afterTasksAnalysis"]
        if nonblocking["severities"] != ["MEDIUM", "LOW"] or nonblocking["findingCount"] != 2:
            raise AssertionError("non-blocking findings were not recorded as structured evidence")
        (feature / "tasks.md").write_text(
            (feature / "tasks.md").read_text(encoding="utf-8").replace("- [ ] T001", "- [X] T001"),
            encoding="utf-8",
        )
        if lifecycle.verify_before_implement(repository, feature) != 0:
            raise AssertionError("checkbox-only implementation progress invalidated analysis readiness")
        (feature / "tasks.md").write_text(
            (feature / "tasks.md").read_text(encoding="utf-8") + "changed\n", encoding="utf-8"
        )
        if lifecycle.verify_before_implement(repository, feature) != 12:
            raise AssertionError("stale analysis was not rejected")

        blocked = repository / "specs/SPC-002"
        blocked.mkdir()
        for name in ("spec.md", "plan.md", "tasks.md", "artifact-ownership.json"):
            source = feature / name
            (blocked / name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        blocking_report = repository / ".program-kit/evidence/SPC-002-analysis.md"
        blocking_report.write_text(
            analysis_report(
                [
                    ("C1", "Constitution", "CRITICAL", "spec.md:L1", "MUST conflict", "Correct spec"),
                    ("A1", "Ownership", "HIGH", "plan.md:L4", "Ownership drift", "Correct plan"),
                ]
            ),
            encoding="utf-8",
        )
        lifecycle.begin(repository, blocked, "analyze", False)
        if lifecycle.complete_analysis(repository, blocked, blocking_report) != 9:
            raise AssertionError("HIGH/CRITICAL analysis did not block readiness")
        blocked_state = json.loads(lifecycle.state_path(repository, blocked).read_text(encoding="utf-8"))
        blocked_analysis = blocked_state["phases"]["afterTasksAnalysis"]
        if blocked_analysis["severities"] != ["CRITICAL", "HIGH"] or blocked_state.get("active"):
            raise AssertionError("valid blocking analysis was not completed deterministically")
        if lifecycle.verify_before_implement(repository, blocked) != 13:
            raise AssertionError("non-ready analysis authorized implementation")

        retryable = repository / "specs/SPC-004"
        retryable.mkdir()
        for name in ("spec.md", "plan.md", "tasks.md", "artifact-ownership.json"):
            source = feature / name
            (retryable / name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        malformed_report = repository / ".program-kit/evidence/SPC-004-analysis.md"
        malformed_report.write_text("# Analysis\nNo blocking findings.\n", encoding="utf-8")
        lifecycle.begin(repository, retryable, "analyze", False)
        if lifecycle.complete_analysis(repository, retryable, malformed_report) != 17:
            raise AssertionError("malformed analysis report did not fail explicitly")
        retry_state = json.loads(lifecycle.state_path(repository, retryable).read_text(encoding="utf-8"))
        if retry_state.get("active", {}).get("phase") != "analyze":
            raise AssertionError("malformed analysis report consumed the retryable active lifecycle")
        malformed_report.write_text(analysis_report(), encoding="utf-8")
        if lifecycle.complete_analysis(repository, retryable, malformed_report) != 0:
            raise AssertionError("corrected analysis report could not retry completion")
        ambiguous_report = repository / ".program-kit/evidence/ambiguous-analysis.md"
        ambiguous_report.write_text(analysis_report() + "\n" + analysis_report(), encoding="utf-8")
        try:
            lifecycle.analysis_findings(ambiguous_report)
        except ValueError as error:
            if "PKL017" not in str(error) or "ambiguous" not in str(error):
                raise
        else:
            raise AssertionError("ambiguous analysis report was silently classified")
        invalid_report = repository / ".program-kit/evidence/invalid-severity-analysis.md"
        invalid_report.write_text(
            analysis_report(
                [("A1", "Ambiguity", "NOTICE", "spec.md:L2", "Unclear phrase", "Clarify")]
            ),
            encoding="utf-8",
        )
        try:
            lifecycle.analysis_findings(invalid_report)
        except ValueError as error:
            if "PKL017" not in str(error) or "invalid severity 'NOTICE'" not in str(error):
                raise
        else:
            raise AssertionError("invalid finding severity was silently classified")
        malformed_row_report = repository / ".program-kit/evidence/malformed-row-analysis.md"
        malformed_row_report.write_text(
            "# Specification Analysis Report\n\n"
            "| ID | Category | Severity | Location(s) | Summary | Recommendation |\n"
            "|----|----------|----------|-------------|---------|----------------|\n"
            "| A1 | Ambiguity | HIGH | spec.md:L2 | Missing recommendation |\n",
            encoding="utf-8",
        )
        mixed_sentinel_report = repository / ".program-kit/evidence/mixed-sentinel-analysis.md"
        mixed_sentinel_report.write_text(
            analysis_report(
                [
                    ("—", "—", "—", "—", "No findings", "Proceed"),
                    ("A1", "Ambiguity", "HIGH", "spec.md:L2", "Unclear phrase", "Clarify"),
                ]
            ),
            encoding="utf-8",
        )
        for invalid_path, diagnostic in (
            (malformed_row_report, "has 5 cells"),
            (mixed_sentinel_report, "follows a no-findings sentinel"),
        ):
            try:
                lifecycle.analysis_findings(invalid_path)
            except ValueError as error:
                if "PKL017" not in str(error) or diagnostic not in str(error):
                    raise
            else:
                raise AssertionError(f"malformed report was silently classified: {invalid_path.name}")

        custom_host = repository / "specs/SPC-003"
        custom_host.mkdir()
        for name in ("spec.md", "plan.md", "tasks.md"):
            (custom_host / name).write_text((feature / name).read_text(encoding="utf-8"), encoding="utf-8")
        (custom_host / "plan.md").write_text(
            (custom_host / "plan.md").read_text(encoding="utf-8")
            + "\nCreate `src/Product.Host/Product.Host.csproj` and `src/Product.Host/Program.cs`.\n",
            encoding="utf-8",
        )
        invalid_manifest = json.loads((feature / "artifact-ownership.json").read_text(encoding="utf-8"))
        invalid_manifest["profiles"] = ["program-kit", "dotnet"]
        invalid_manifest["artifacts"].append(
            {
                "path": "src/Product.Host/Product.Host.csproj",
                "ownership": "consumer-owned",
                "classification": "internal",
                "lifecycle": "source",
            }
        )
        (custom_host / "artifact-ownership.json").write_text(
            json.dumps(invalid_manifest), encoding="utf-8"
        )
        custom_report = repository / ".program-kit/evidence/SPC-003-analysis.md"
        custom_report.write_text(analysis_report(), encoding="utf-8")
        lifecycle.begin(repository, custom_host, "analyze", False)
        if lifecycle.complete_analysis(repository, custom_host, custom_report) != 16:
            raise AssertionError("custom host plan was marked ready for implementation")
        if lifecycle.verify_before_implement(repository, custom_host) != 13:
            raise AssertionError("custom host analysis authorized implementation")


def validate_utf8() -> None:
    ensure = ROOT / "extensions/program-kit-governance/scripts/ensure_utf8.py"
    with tempfile.TemporaryDirectory(prefix="program-kit-utf8-") as value:
        repository = Path(value)
        scripts = repository / ".specify/scripts/python"
        scripts.mkdir(parents=True)
        probe = scripts / "setup_tasks.py"
        probe.write_text("print('Task template → ✓')\n", encoding="utf-8")
        subprocess.run([sys.executable, str(ensure), "--target", str(repository)], check=True)
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "0"
        environment["PYTHONIOENCODING"] = "cp1252"
        result = subprocess.run([sys.executable, str(probe)], env=environment, capture_output=True)
        if result.returncode != 0 or "Task template → ✓" not in result.stdout.decode("utf-8"):
            raise AssertionError(f"UTF-8 startup failed under cp1252: {result.stderr!r}")
        subprocess.run([sys.executable, str(ensure), "--target", str(repository), "--check"], check=True)


def validate_feature_activation() -> None:
    feature = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/feature_metadata.py"
    with tempfile.TemporaryDirectory(prefix="program-kit-feature-") as value:
        shells = Path(value) / "shells.json"
        shells.write_text(
            json.dumps({"CShells": {"Shells": {"default": {"Features": {"ProgramKitTasks": {}}}}}}),
            encoding="utf-8",
        )
        command = [sys.executable, str(feature), "activate", "--shells", str(shells), "--shell", "default", "--feature", "Orders"]
        subprocess.run(command, check=True)
        duplicate = subprocess.run(command, capture_output=True, text=True)
        if duplicate.returncode == 0 or "PKF006" not in duplicate.stderr:
            raise AssertionError("duplicate feature activation was not rejected")
        result = json.loads(shells.read_text(encoding="utf-8"))
        if set(result["CShells"]["Shells"]["default"]["Features"]) != {"ProgramKitTasks", "Orders"}:
            raise AssertionError("CShells feature activation shape drifted")


def validate_release_feature_closure() -> None:
    release = module(
        ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/runnable_host.py",
        "runnable_host",
    )
    with tempfile.TemporaryDirectory(prefix="program-kit-bundle-features-") as value:
        root = Path(value)

        def package(package_id: str, identity: str | None = None, **overrides) -> Path:
            path = root / f"{package_id}.1.0.0.nupkg"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    f"{package_id}.nuspec",
                    f"<package><metadata><id>{package_id}</id><version>1.0.0</version></metadata></package>",
                )
                if identity:
                    descriptor = {
                        "schemaVersion": 1,
                        "identity": identity,
                        "packageId": package_id,
                        "featureDependencies": [],
                        "runtimeDependencies": [],
                        "routes": [],
                        "dormant": False,
                        **overrides,
                    }
                    archive.writestr("program-kit/feature.json", json.dumps(descriptor))
            return path

        tasks = package("ProgramKit.Tasks")
        domain_events = package("ProgramKit.DomainEvents")
        orders = package("Orders.Feature", "Orders", routes=["/orders"])
        identities = {("ProgramKit.Tasks", "1.0.0"): tasks, ("Orders.Feature", "1.0.0"): orders}
        shells = root / "shells.json"
        shells.write_text(
            json.dumps({"CShells": {"Shells": {"default": {"Features": {"ProgramKitTasks": {}, "Orders": {}}}}}}),
            encoding="utf-8",
        )
        release.validate_feature_closure(shells, identities)

        missing_shells = root / "missing.json"
        missing_shells.write_text(
            json.dumps({"CShells": {"Shells": {"default": {"Features": {"Missing": {}}}}}}),
            encoding="utf-8",
        )
        try:
            release.validate_feature_closure(missing_shells, identities)
        except ValueError as error:
            if "PKR009" not in str(error) or "default" not in str(error) or "Missing" not in str(error):
                raise
        else:
            raise AssertionError("missing activated feature did not fail actionably")

        duplicate = package("Orders.Other", "Orders")
        try:
            release.validate_feature_closure(shells, {**identities, ("Orders.Other", "1.0.0"): duplicate})
        except ValueError as error:
            if "PKR007" not in str(error):
                raise
        else:
            raise AssertionError("duplicate feature identity was accepted")

        dependent = package(
            "Dependent.Feature", "Dependent", runtimeDependencies=["Missing.Runtime"]
        )
        dependency_shells = root / "dependency.json"
        dependency_shells.write_text(
            json.dumps({"CShells": {"Shells": {"default": {"Features": {"Dependent": {}}}}}}),
            encoding="utf-8",
        )
        try:
            release.validate_feature_closure(
                dependency_shells,
                {("Dependent.Feature", "1.0.0"): dependent},
            )
        except ValueError as error:
            if "PKR010" not in str(error) or "Missing.Runtime" not in str(error):
                raise
        else:
            raise AssertionError("missing runtime dependency was accepted")

        payments = package("Payments.Feature", "Payments", routes=["/orders"])
        collision_shells = root / "collision.json"
        collision_shells.write_text(
            json.dumps({"CShells": {"Shells": {"default": {"Features": {"Orders": {}, "Payments": {}}}}}}),
            encoding="utf-8",
        )
        try:
            release.validate_feature_closure(
                collision_shells,
                {**identities, ("Payments.Feature", "1.0.0"): payments},
            )
        except ValueError as error:
            if "PKR012" not in str(error):
                raise
        else:
            raise AssertionError("route collision was accepted")

        clean_repository = root / "clean-consumer"
        clean_repository.mkdir()
        (clean_repository / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        (clean_repository / "NuGet.config").write_text(
            '<configuration><packageSources><add key="test" value="https://example.invalid/v3/index.json" /></packageSources></configuration>\n',
            encoding="utf-8",
        )
        managed = clean_repository / ".program-kit/eng"
        managed.mkdir(parents=True)
        (managed / "ProgramKit.Packages.props").write_text(
            '<Project><ItemGroup>'
            '<PackageVersion Include="ProgramKit.Tasks" Version="1.0.0" />'
            '<PackageVersion Include="ProgramKit.DomainEvents" Version="1.0.0" />'
            '</ItemGroup></Project>\n',
            encoding="utf-8",
        )
        (clean_repository / "shells.json").write_text(
            json.dumps(
                {
                    "CShells": {
                        "Shells": {
                            "default": {
                                "Features": {"ProgramKitTasks": {}, "ProgramKit.DomainEvents": {}}
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        (clean_repository / "hostsettings.json").write_text("{}\n", encoding="utf-8")
        clean_packages = root / "clean-packages"
        clean_packages.mkdir()
        clean_output = clean_repository / "artifacts/runnable-host"
        original_bases = release.package_base_addresses
        original_download = release.download_package
        release.package_base_addresses = lambda sources: ["https://example.invalid/flat"]

        def seed_built_in(package_id: str, version: str, bases: list[str], destination: Path) -> None:
            if version != "1.0.0" or package_id not in {"ProgramKit.Tasks", "ProgramKit.DomainEvents"}:
                raise AssertionError(f"unexpected built-in package request: {package_id} {version}")
            source = tasks if package_id == "ProgramKit.Tasks" else domain_events
            shutil.copyfile(source, destination)

        release.download_package = seed_built_in
        try:
            release.stage(clean_repository, clean_packages, clean_output)
        finally:
            release.package_base_addresses = original_bases
            release.download_package = original_download
        if not (clean_output / "packages/ProgramKit.Tasks.1.0.0.nupkg").is_file():
            raise AssertionError("activated ProgramKitTasks was not seeded from its managed package pin")
        if not (clean_output / "packages/ProgramKit.DomainEvents.1.0.0.nupkg").is_file():
            raise AssertionError("activated ProgramKit.DomainEvents was not seeded from its managed package pin")
        closure_evidence = clean_repository / ".program-kit/evidence/runtime-closure.json"
        closure = json.loads(closure_evidence.read_text(encoding="utf-8"))
        if (
            closure.get("satisfied") is not True
            or closure.get("packageHashesAreRunScoped") is not True
            or len(closure.get("packages", [])) != 2
        ):
            raise AssertionError(f"same-run runtime closure evidence is incomplete: {closure}")
        valid_shells = (clean_repository / "shells.json").read_bytes()
        (clean_repository / "shells.json").write_text(
            json.dumps({"CShells": {"Shells": {"default": {"Features": {"Missing": {}}}}}}),
            encoding="utf-8",
        )
        try:
            release.stage(clean_repository, clean_packages, clean_output)
        except ValueError as error:
            if "PKR009" not in str(error):
                raise
        else:
            raise AssertionError("invalid runtime stage unexpectedly succeeded")
        failed_evidence = json.loads(closure_evidence.read_text(encoding="utf-8"))
        if failed_evidence.get("satisfied") is not False:
            raise AssertionError("a partial failed runtime stage retained satisfied closure evidence")
        (clean_repository / "shells.json").write_bytes(valid_shells)

        repository = root / "repository"
        repository.mkdir()
        (repository / "VERSION").write_text("1.2.3\n", encoding="utf-8")
        staged = repository / "artifacts/runnable-host"
        staged.mkdir(parents=True)
        hostsettings = {"Nuplane": {"Loading": {"Enabled": True}}}
        shells_value = {"CShells": {"Shells": {"default": {"Features": {}}}}}
        (staged / "hostsettings.json").write_text(json.dumps(hostsettings), encoding="utf-8")
        (staged / "shells.json").write_text(json.dumps(shells_value), encoding="utf-8")
        staged_packages = staged / "packages"
        staged_packages.mkdir()
        shutil.copyfile(tasks, staged_packages / tasks.name)
        descriptor_evidence = repository / ".program-kit/evidence/runtime-closure.json"
        release.runtime_closure.write_success(
            repository,
            staged,
            descriptor_evidence,
            release.PROGRAM_KIT_VERSION,
        )
        output = root / "runnable-host.json"
        previous_sha = os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"] = "a" * 40
        try:
            release.describe(
                repository,
                staged,
                "ghcr.io/example/application",
                "v1.2.3",
                "sha256:" + "b" * 64,
                output,
            )
            descriptor = json.loads(output.read_text(encoding="utf-8"))
            if descriptor["hostImage"]["reference"] != "ghcr.io/example/application@sha256:" + "b" * 64:
                raise AssertionError("runnable-host descriptor did not bind the immutable image")
            if descriptor["configuration"]["shells"] != shells_value:
                raise AssertionError("runnable-host descriptor did not capture CShells settings")
            original_shells = (staged / "shells.json").read_bytes()
            (staged / "shells.json").write_text('{"changed":true}\n', encoding="utf-8")
            try:
                release.describe(
                    repository,
                    staged,
                    "ghcr.io/example/application",
                    "v1.2.3",
                    "sha256:" + "b" * 64,
                    output,
                )
            except ValueError as error:
                if "PKR022" not in str(error):
                    raise
            else:
                raise AssertionError("release describe accepted stale runtime-closure evidence")
            (staged / "shells.json").write_bytes(original_shells)
            release.runtime_closure.write_success(
                repository,
                staged,
                descriptor_evidence,
                release.PROGRAM_KIT_VERSION,
            )
            (staged / "hostsettings.json").write_text(
                json.dumps({"ConnectionStrings": {"Password": "do-not-publish"}}), encoding="utf-8"
            )
            release.runtime_closure.write_success(
                repository,
                staged,
                descriptor_evidence,
                release.PROGRAM_KIT_VERSION,
            )
            try:
                release.describe(
                    repository,
                    staged,
                    "ghcr.io/example/application",
                    "v1.2.3",
                    "sha256:" + "b" * 64,
                    output,
                )
            except ValueError as error:
                if "PKR017" not in str(error):
                    raise
            else:
                raise AssertionError("runnable-host descriptor embedded a secret")
        finally:
            if previous_sha is None:
                os.environ.pop("GITHUB_SHA", None)
            else:
                os.environ["GITHUB_SHA"] = previous_sha

        inherited_github_sha = os.environ.pop("GITHUB_SHA", None)
        try:
            with patch.object(release.subprocess, "run") as run_git:
                run_git.return_value = subprocess.CompletedProcess(
                    ["git"], 0, stdout="c" * 40 + "\n", stderr=""
                )
                resolved = release.source_commit(repository.resolve())
                if resolved != "c" * 40:
                    raise AssertionError("sandbox-safe Git commit resolution lost the exact commit")
                command = run_git.call_args.args[0]
                if (
                    f"safe.directory={repository.resolve().as_posix()}" not in command
                    or not any(item.startswith("core.excludesFile=") for item in command)
                    or command[-3:] != [str(repository.resolve()), "rev-parse", "HEAD"]
                ):
                    raise AssertionError(f"source commit resolution is not repository-confined: {command}")

            try:
                release.source_commit(root / "not-a-git-repository")
            except ValueError as error:
                if "PKR020" not in str(error):
                    raise
            else:
                raise AssertionError("non-Git runnable-host evidence did not fail actionably")
        finally:
            if inherited_github_sha is not None:
                os.environ["GITHUB_SHA"] = inherited_github_sha


def validate_preflight_seams() -> None:
    preflight = ROOT / "extensions/program-kit-dotnet/templates/dotnet/web-profiles/common/.program-kit/eng/preflight.py"
    with tempfile.TemporaryDirectory(prefix="program-kit-preflight-") as value:
        tools = Path(value)
        if os.name == "nt":
            stopped = tools / "docker-stopped.cmd"
            stopped.write_text("@echo off\r\nexit /b 1\r\n", encoding="utf-8")
            slow = tools / "docker-slow.cmd"
            slow.write_text("@echo off\r\nping -n 3 127.0.0.1 >nul\r\necho \"10.0.0\"\r\n", encoding="utf-8")
            ready = tools / "docker-ready.cmd"
            ready.write_text("@echo off\r\necho \"10.0.0\"\r\n", encoding="utf-8")
        else:
            stopped = tools / "docker-stopped"
            stopped.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            slow = tools / "docker-slow"
            slow.write_text("#!/bin/sh\nsleep 2\nprintf '\"10.0.0\"\\n'\n", encoding="utf-8")
            ready = tools / "docker-ready"
            ready.write_text("#!/bin/sh\nprintf '\"10.0.0\"\\n'\n", encoding="utf-8")
            for path in (stopped, slow, ready):
                path.chmod(0o755)

        def run(command: str, timeout: str = "5") -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, str(preflight), "--docker-command", command, "--timeout-seconds", timeout],
                capture_output=True,
                text=True,
            )

        cases = [
            (run("program-kit-missing-docker"), 2, "PKP002"),
            (run(str(stopped)), 4, "PKP004"),
            (run(str(slow), "0.1"), 3, "PKP003"),
            (run(str(ready), "0"), 1, "PKP001"),
        ]
        for result, code, marker in cases:
            if result.returncode != code or marker not in result.stderr:
                raise AssertionError(f"preflight seam {marker} failed: {result.stdout}{result.stderr}")
        if run(str(ready)).returncode != 0:
            raise AssertionError("ready Docker seam did not pass")


def validate_toolchain_workflow() -> None:
    toolchain = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/toolchain.py"
    with tempfile.TemporaryDirectory(prefix="program-kit-toolchain-") as value:
        repository = Path(value)
        tools = repository / "tools"
        tools.mkdir()
        (repository / "global.json").write_text('{"sdk":{"version":"10.0.202"}}\n', encoding="utf-8")
        (repository / ".nvmrc").write_text("24.20.0\n", encoding="utf-8")
        (repository / ".npm-version").write_text("11.19.0\n", encoding="utf-8")
        marker = repository / "dotnet-installed"
        if os.name == "nt":
            dotnet = tools / "dotnet.cmd"
            dotnet.write_text(
                f"@echo off\r\nif exist \"{marker}\" (echo 10.0.202) else (echo 9.0.100)\r\n",
                encoding="utf-8",
            )
            node = tools / "node.cmd"
            node.write_text("@echo off\r\necho v24.20.0\r\n", encoding="utf-8")
            npm = tools / "npm.cmd"
            npm.write_text("@echo off\r\necho 11.19.0\r\n", encoding="utf-8")
            installer = repository / "dotnet-install.cmd"
            installer.write_text(f"@echo off\r\ntype nul > \"{marker}\"\r\n", encoding="utf-8")
            offline = repository / "offline.cmd"
            offline.write_text("@echo off\r\nexit /b 1\r\n", encoding="utf-8")
        else:
            dotnet = tools / "dotnet"
            dotnet.write_text(f"#!/bin/sh\n[ -f '{marker}' ] && echo 10.0.202 || echo 9.0.100\n", encoding="utf-8")
            node = tools / "node"
            node.write_text("#!/bin/sh\necho v24.20.0\n", encoding="utf-8")
            npm = tools / "npm"
            npm.write_text("#!/bin/sh\necho 11.19.0\n", encoding="utf-8")
            installer = repository / "dotnet-install.sh"
            installer.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
            offline = repository / "offline.sh"
            offline.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            for path in (dotnet, node, npm, installer, offline):
                path.chmod(0o755)
        environment = os.environ.copy()
        environment["PATH"] = str(tools) + os.pathsep + environment.get("PATH", "")

        def run(*arguments: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    sys.executable,
                    str(toolchain),
                    "--repository",
                    str(repository),
                    "--dotnet-command",
                    str(dotnet),
                    "--node-command",
                    str(node),
                    *arguments,
                ],
                # Exact command paths are test seams; production defaults remain dotnet/node from PATH.
                env=environment,
                capture_output=True,
                text=True,
            )

        declined = run("--remediate", "--decline")
        if (
            declined.returncode != 3
            or "PKT003" not in declined.stderr
            or "PKT011" not in declined.stderr
            or "managed pins remain authoritative" not in declined.stderr
        ):
            raise AssertionError("declined toolchain remediation changed state or returned the wrong code")
        unavailable = run("--remediate", "--approve")
        if unavailable.returncode != 4 or "PKT004" not in unavailable.stderr:
            raise AssertionError(f"unavailable installer path was not actionable: {unavailable.stdout}{unavailable.stderr}")
        offline_result = run("--remediate", "--approve", "--dotnet-installer", str(offline))
        if offline_result.returncode != 4 or "PKT006" not in offline_result.stderr:
            raise AssertionError("offline/failed installer path was not distinguished")
        approved = run("--remediate", "--approve", "--dotnet-installer", str(installer))
        if approved.returncode != 0 or "PKT010" not in approved.stdout:
            raise AssertionError(f"approved remediation did not re-verify: {approved.stdout}{approved.stderr}")
        satisfied = run()
        if satisfied.returncode != 0 or "PKT000" not in satisfied.stdout:
            raise AssertionError("already-satisfied toolchain did not avoid installation")
        (repository / ".oasdiff-version").write_text("1.29.1\n", encoding="utf-8")
        if os.name == "nt":
            reviewed_oasdiff = repository / "reviewed-oasdiff.cmd"
            reviewed_oasdiff.write_text(
                "@echo off\r\nif \"%1\"==\"version\" echo oasdiff version v1.29.1\r\nexit /b 0\r\n",
                encoding="utf-8",
            )
        else:
            reviewed_oasdiff = repository / "reviewed-oasdiff"
            reviewed_oasdiff.write_text(
                "#!/bin/sh\n[ \"$1\" = version ] && printf 'oasdiff version v1.29.1\\n'\nexit 0\n",
                encoding="utf-8",
            )
            reviewed_oasdiff.chmod(0o755)
        missing_oasdiff = run("--include-openapi", "--oasdiff-command", "missing-oasdiff")
        if missing_oasdiff.returncode != 2 or "oasdiff" not in missing_oasdiff.stderr:
            raise AssertionError("missing managed oasdiff was not reported")
        preserved = json.loads(
            (repository / ".program-kit/evidence/toolchain.json").read_text(encoding="utf-8")
        )
        failed = json.loads(
            (repository / ".program-kit/evidence/toolchain.failure.json").read_text(encoding="utf-8")
        )
        if preserved.get("satisfied") is not True or failed.get("previousEvidencePreserved") is not True:
            raise AssertionError("failed toolchain renewal destroyed previously satisfied evidence")
        installed_oasdiff = run(
            "--include-openapi", "--oasdiff-command", "missing-oasdiff", "--remediate", "--approve",
            "--oasdiff-binary", str(reviewed_oasdiff),
        )
        if installed_oasdiff.returncode != 0 or "PKT010" not in installed_oasdiff.stdout:
            raise AssertionError(
                f"reviewed oasdiff was not installed and re-verified: {installed_oasdiff.stdout}{installed_oasdiff.stderr}"
            )
        if (repository / ".program-kit/evidence/toolchain.failure.json").exists():
            raise AssertionError("successful toolchain renewal retained stale failure evidence")

    with tempfile.TemporaryDirectory(prefix="program-kit-fnm-recheck-") as value:
        repository = Path(value)
        tools = repository / "tools"
        tools.mkdir()
        (repository / "global.json").write_text('{"sdk":{"version":"10.0.202"}}\n', encoding="utf-8")
        (repository / ".nvmrc").write_text("24.20.0\n", encoding="utf-8")
        (repository / ".npm-version").write_text("11.19.0\n", encoding="utf-8")
        installed = repository / "node-installed"
        pinned = repository / "pinned"
        pinned.mkdir()
        if os.name == "nt":
            dotnet = tools / "dotnet.cmd"
            dotnet.write_text("@echo off\r\necho 10.0.202\r\n", encoding="utf-8")
            node = tools / "node.cmd"
            node.write_text("@echo off\r\necho v20.11.1\r\n", encoding="utf-8")
            pinned_node = pinned / "node.cmd"
            pinned_node.write_text("@echo off\r\necho v24.20.0\r\n", encoding="utf-8")
            pinned_npm = pinned / "npm.cmd"
            pinned_npm.write_text("@echo off\r\necho 11.19.0\r\n", encoding="utf-8")
            fnm = tools / "fnm.cmd"
            fnm.write_text(
                f"@echo off\r\nif \"%1\"==\"install\" (type nul > \"{installed}\" & exit /b 0)\r\n"
                f"if \"%1\"==\"exec\" (if exist \"{installed}\" (echo {pinned_node} & exit /b 0))\r\n"
                "exit /b 1\r\n",
                encoding="utf-8",
            )
        else:
            dotnet = tools / "dotnet"
            dotnet.write_text("#!/bin/sh\necho 10.0.202\n", encoding="utf-8")
            node = tools / "node"
            node.write_text("#!/bin/sh\necho v20.11.1\n", encoding="utf-8")
            pinned_node = pinned / "node"
            pinned_node.write_text("#!/bin/sh\necho v24.20.0\n", encoding="utf-8")
            pinned_npm = pinned / "npm"
            pinned_npm.write_text("#!/bin/sh\necho 11.19.0\n", encoding="utf-8")
            fnm = tools / "fnm"
            fnm.write_text(
                f"#!/bin/sh\n[ \"$1\" = install ] && touch '{installed}' && exit 0\n"
                f"[ \"$1\" = exec ] && [ -f '{installed}' ] && printf '%s\\n' '{pinned_node}' && exit 0\nexit 1\n",
                encoding="utf-8",
            )
            for path in (dotnet, node, pinned_node, pinned_npm, fnm):
                path.chmod(0o755)
        environment = os.environ.copy()
        environment["PATH"] = str(tools) + os.pathsep + environment.get("PATH", "")
        fnm_result = subprocess.run(
            [
                sys.executable,
                str(toolchain),
                "--repository",
                str(repository),
                "--dotnet-command",
                str(dotnet),
                "--node-command",
                str(node),
                "--remediate",
                "--approve",
                "--node-manager",
                "fnm",
            ],
            env=environment,
            capture_output=True,
            text=True,
        )
        if fnm_result.returncode != 0 or "PKT010" not in fnm_result.stdout:
            raise AssertionError(
                "fnm installation was not re-verified in the same command: "
                + fnm_result.stdout
                + fnm_result.stderr
            )
        evidence = json.loads(
            (repository / ".program-kit/evidence/toolchain.json").read_text(encoding="utf-8")
        )
        if (
            evidence["resolved"]["node"] != "24.20.0"
            or evidence["resolved"]["npm"] != "11.19.0"
            or evidence["commands"]["node"] != [str(pinned_node.resolve())]
            or evidence["satisfied"] is not True
        ):
            raise AssertionError(f"fnm re-verification evidence is incorrect: {evidence}")


def validate_managed_sources() -> None:
    template = ROOT / "extensions/program-kit-dotnet/templates/dotnet"
    manifest = json.loads((template / "managed-files.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        source = template / entry.get("sourceRoot", "files") / entry.get("source", entry["path"])
        if not source.is_file():
            raise AssertionError(f"managed source is missing: {source}")
        if source.suffix in {".props", ".targets"}:
            ElementTree.parse(source)

    targets = (template / "files/.program-kit/eng/ProgramKit.Build.targets").read_text(encoding="utf-8")
    for phrase in ("ProgramKitFeatureMetadata", "PKF101", "feature_metadata.py"):
        if phrase not in targets:
            raise AssertionError(f"managed build target is missing {phrase}")
    if "ProgramKitApiContracts" in targets or "ProgramKitOpenApiGeneratedDocument" in targets:
        raise AssertionError("legacy consumer-supplied OpenAPI document target remains active")
    pipeline = (template / "files/.program-kit/eng/openapi_pipeline.py").read_text(encoding="utf-8")
    for phrase in (
        "ProgramKit.OpenApi.Exporter",
        "artifacts/runnable-host/packages",
        "--strict-peer-deps",
        "generatedTypes",
        "application",
    ):
        if phrase not in pipeline:
            raise AssertionError(f"managed OpenAPI pipeline is missing {phrase}")
    pipeline_module = module(
        template / "files/.program-kit/eng/openapi_pipeline.py", "openapi_pipeline_environment"
    )
    observed_environment: dict[str, str] = {}

    def observe_toolchain(_repository: Path, _evidence: Path, environment: dict[str, str]) -> None:
        observed_environment.update(environment)

    original_appdata = os.environ.get("APPDATA")
    os.environ["APPDATA"] = "consumer-fnm-profile"
    try:
        with patch.object(pipeline_module, "ensure_openapi_toolchain", observe_toolchain), patch.object(
            pipeline_module.js_toolchain, "context", lambda *_: None
        ):
            pipeline_module.prepare_openapi_toolchain(Path.cwd(), Path("toolchain.json"))
    finally:
        if original_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = original_appdata
    if observed_environment.get("APPDATA") != "consumer-fnm-profile":
        raise AssertionError("OpenAPI toolchain discovery ran after NuGet profile isolation hid fnm")
    tool_manifest = json.loads(
        (template / "files/.program-kit/eng/.config/dotnet-tools.json").read_text(encoding="utf-8")
    )
    exporter = tool_manifest.get("tools", {}).get("programkit.openapi.exporter", {})
    if exporter.get("commands") != ["programkit-openapi-export"] or not exporter.get("version"):
        raise AssertionError("managed OpenAPI exporter tool pin is incomplete")
    runnable_schema = json.loads(
        (template / "files/.program-kit/runnable-host.schema.json").read_text(encoding="utf-8")
    )
    required = set(runnable_schema.get("required", []))
    if required != {"schemaVersion", "application", "hostImage", "runtimeClosure", "configuration"}:
        raise AssertionError("runnable-host schema does not close over image identity and configuration")
    host_image = runnable_schema["properties"]["hostImage"]
    if "digest" not in host_image.get("required", []) or "reference" not in host_image.get("required", []):
        raise AssertionError("runnable-host schema does not require immutable image identity")
    runtime_closure_schema = runnable_schema["properties"]["runtimeClosure"]
    if {"evidence", "digest", "packageCount"} - set(runtime_closure_schema.get("required", [])):
        raise AssertionError("runnable-host schema does not require runtime-closure identity")
    persistence = ROOT / "extensions/program-kit-dotnet/references/persistence-profiles.md"
    text = persistence.read_text(encoding="utf-8")
    for phrase in ("ef-postgresql", "ef-sqlserver", "ef-sqlite", "IEntityTypeConfiguration", "Testcontainers", "generic repository", "lazy-loading"):
        if phrase not in text:
            raise AssertionError(f"persistence guidance is missing {phrase}")


def validate_openapi_contracts() -> None:
    script = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/openapi_contracts.py"
    contracts = module(script, "openapi_contracts")
    with tempfile.TemporaryDirectory(prefix="program-kit-openapi-") as value:
        root = Path(value)
        generated = root / "obj/api.json"
        generated.parent.mkdir()
        artifact = root / "contracts/openapi.json"
        baseline = root / "contracts/baseline.json"
        document = {
            "openapi": "3.1.0",
            "info": {"title": "Consumer API", "version": "1.0.0"},
            "paths": {"/orders": {"get": {"operationId": "ListOrders", "responses": {"200": {"description": "OK"}}}}},
        }
        generated.write_text(json.dumps(document), encoding="utf-8")
        first = subprocess.run(
            [
                sys.executable,
                str(script),
                "--generated",
                str(generated),
                "--artifact",
                str(artifact),
                "--baseline",
                str(baseline),
                "--oasdiff-version",
                "1.29.1",
                "--write-generated",
                "--initialize-baseline",
            ],
            capture_output=True,
            text=True,
        )
        if first.returncode != 0 or artifact.read_bytes() != baseline.read_bytes():
            raise AssertionError(f"first OpenAPI baseline was not deterministic: {first.stdout}{first.stderr}")
        document["paths"]["/orders/{id}"] = {
            "get": {"operationId": "GetOrder", "responses": {"200": {"description": "OK"}}}
        }
        generated.write_text(json.dumps(document), encoding="utf-8")
        stale = subprocess.run(
            [
                sys.executable,
                str(script),
                "--generated",
                str(generated),
                "--artifact",
                str(artifact),
                "--baseline",
                str(baseline),
                "--oasdiff-version",
                "1.29.1",
            ],
            capture_output=True,
            text=True,
        )
        if stale.returncode == 0 or "PKO008" not in stale.stderr:
            raise AssertionError("stale generated OpenAPI output was accepted")
        document["paths"]["/orders/{id}"]["get"]["operationId"] = "ListOrders"
        try:
            contracts.validate_operation_identity(document)
        except ValueError as error:
            if "PKO005" not in str(error):
                raise
        else:
            raise AssertionError("duplicate OpenAPI operation identity was accepted")


def validate_openapi_initialization() -> None:
    script = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/openapi_init.py"
    with tempfile.TemporaryDirectory(prefix="program-kit-openapi-init-") as value:
        repository = Path(value)
        defaults = repository / ".program-kit/openapi-defaults.json"
        defaults.parent.mkdir(parents=True)
        defaults.write_text(
            json.dumps({
                "schemaVersion": 1,
                "compatibility": {"tool": "oasdiff", "version": "1.29.1"},
                "typescriptGenerator": {
                    "package": "openapi-typescript", "version": "7.13.0",
                    "isolation": "separate-package-and-lockfile",
                },
            }),
            encoding="utf-8",
        )
        manifest = repository / ".program-kit/eng/.config/dotnet-tools.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps({
                "tools": {"programkit.openapi.exporter": {"version": "0.9.9-preview.1"}}
            }),
            encoding="utf-8",
        )
        (repository / ".program-kit/openapi-contracts.json").write_text(
            json.dumps({"schemaVersion": 1, "contracts": []}), encoding="utf-8"
        )
        command = [
            sys.executable, str(script), "--repository", str(repository),
            "--identity", "catalog-v1", "--document-name", "v1", "--shell", "default",
            "--feature", "Catalog.Api", "--application-directory", "src/web",
            "--application-tsconfig", "src/web/tsconfig.json",
        ]
        initialized = subprocess.run(command, capture_output=True, text=True)
        if initialized.returncode != 0:
            raise AssertionError(f"OpenAPI initializer failed: {initialized.stdout}{initialized.stderr}")
        registry = json.loads((repository / ".program-kit/openapi-contracts.json").read_text(encoding="utf-8"))
        contract = json.loads((repository / registry["contracts"][0]).read_text(encoding="utf-8"))
        generator_package = json.loads(
            (repository / contract["generator"]["packageJson"]).read_text(encoding="utf-8")
        )
        if (
            contract["producer"]["version"] != "0.9.9-preview.1"
            or contract["compatibility"]["oasdiffVersion"] != "1.29.1"
            or contract["generator"]["directory"] == contract["application"]["directory"]
            or generator_package["devDependencies"] != {"openapi-typescript": "7.13.0"}
            or generator_package["scripts"]["generate"]
            != "openapi-typescript ../../../contracts/openapi/catalog-v1.json --output generated/types.ts"
            or "js_toolchain.py" not in initialized.stdout
        ):
            raise AssertionError("OpenAPI initializer did not scaffold the managed isolated generator")
        duplicate = subprocess.run(command, capture_output=True, text=True)
        if duplicate.returncode != 2 or "already exists" not in duplicate.stderr:
            raise AssertionError("OpenAPI initializer overwrote an existing contract")


def validate_npm_graph() -> None:
    script = ROOT / "extensions/program-kit-governance/scripts/npm_graph.py"
    with tempfile.TemporaryDirectory(prefix="program-kit-npm-graph-") as value:
        root = Path(value)
        package_json = root / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": "candidate",
                    "version": "1.0.0",
                    "private": True,
                    "devDependencies": {"typescript": "7.0.2", "openapi-typescript": "7.13.0"},
                }
            ),
            encoding="utf-8",
        )
        evidence = root / "evidence.json"
        if os.name == "nt":
            success_npm = root / "npm-success.cmd"
            success_npm.write_text(
                '@echo off\r\n>package-lock.json echo {"lockfileVersion":3}\r\nexit /b 0\r\n',
                encoding="utf-8",
            )
            failed_npm = root / "npm-failed.cmd"
            failed_npm.write_text(
                "@echo off\r\n>&2 echo npm ERR! ERESOLVE peer typescript@^^5.x\r\nexit /b 1\r\n",
                encoding="utf-8",
            )
        else:
            success_npm = root / "npm-success"
            success_npm.write_text(
                "#!/bin/sh\nprintf '{\"lockfileVersion\":3}\\n' > package-lock.json\n",
                encoding="utf-8",
            )
            failed_npm = root / "npm-failed"
            failed_npm.write_text(
                "#!/bin/sh\necho 'npm ERR! ERESOLVE peer typescript@^5.x' >&2\nexit 1\n",
                encoding="utf-8",
            )
            success_npm.chmod(0o755)
            failed_npm.chmod(0o755)

        success = subprocess.run(
            [
                sys.executable,
                str(script),
                "--package-json",
                str(package_json),
                "--evidence",
                str(evidence),
                "--npm-command",
                str(success_npm),
            ],
            capture_output=True,
            text=True,
        )
        if success.returncode != 0 or "PKN000" not in success.stdout:
            raise AssertionError(f"resolvable npm graph was rejected: {success.stdout}{success.stderr}")
        recorded = json.loads(evidence.read_text(encoding="utf-8"))
        if (
            recorded.get("satisfied") is not True
            or "--strict-peer-deps" not in recorded.get("command", [])
            or "--engine-strict" not in recorded.get("command", [])
        ):
            raise AssertionError(f"npm graph evidence is incomplete: {recorded}")

        failed = subprocess.run(
            [
                sys.executable,
                str(script),
                "--package-json",
                str(package_json),
                "--evidence",
                str(evidence),
                "--npm-command",
                str(failed_npm),
            ],
            capture_output=True,
            text=True,
        )
        if failed.returncode != 2 or "PKN002" not in failed.stderr or "ERESOLVE" not in failed.stderr:
            raise AssertionError(f"incompatible npm peer graph was accepted: {failed.stdout}{failed.stderr}")

        npm = shutil.which("npm")
        if npm:
            npm_environment = os.environ.copy()
            npm_environment["NPM_CONFIG_CACHE"] = str(root / "npm-cache")
            npm_environment["NPM_CONFIG_OFFLINE"] = "true"
            generator = root / "generator"
            typescript = root / "typescript"
            generator.mkdir()
            typescript.mkdir()
            (generator / "package.json").write_text(
                json.dumps(
                    {
                        "name": "openapi-typescript",
                        "version": "7.13.0",
                        "peerDependencies": {"typescript": "^5.x"},
                    }
                ),
                encoding="utf-8",
            )
            (typescript / "package.json").write_text(
                json.dumps({"name": "typescript", "version": "7.0.2"}), encoding="utf-8"
            )
            for package in (generator, typescript):
                packed = subprocess.run(
                    [npm, "pack", "--pack-destination", str(root)],
                    cwd=package,
                    capture_output=True,
                    text=True,
                    env=npm_environment,
                )
                if packed.returncode != 0:
                    raise AssertionError(f"could not build local npm metadata fixture: {packed.stderr}")
            generator_archive = root / "openapi-typescript-7.13.0.tgz"
            typescript_archive = root / "typescript-7.0.2.tgz"
            package_json.write_text(
                json.dumps(
                    {
                        "name": "real-peer-conflict",
                        "version": "1.0.0",
                        "private": True,
                        "devDependencies": {
                            "typescript": "file:" + typescript_archive.resolve().as_posix(),
                            "openapi-typescript": "file:" + generator_archive.resolve().as_posix(),
                        },
                    }
                ),
                encoding="utf-8",
            )
            real = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--package-json",
                    str(package_json),
                    "--evidence",
                    str(evidence),
                    "--npm-command",
                    npm,
                ],
                capture_output=True,
                text=True,
                env=npm_environment,
            )
            if real.returncode != 2 or "PKN002" not in real.stderr:
                raise AssertionError(
                    "real npm metadata did not reject the TypeScript 7/openapi-typescript ^5 peer conflict: "
                    + real.stdout
                    + real.stderr
                )


def validate_sync_preservation() -> None:
    sync = ROOT / "extensions/program-kit-dotnet/scripts/dotnet_sync.py"
    with tempfile.TemporaryDirectory(prefix="program-kit-sync-") as value:
        repository = Path(value)
        command = [
            sys.executable,
            str(sync),
            "--target",
            str(repository),
            "--profile-selected",
            "--host-runtime-accepted",
            "--preview-sources-approved",
            "--persistence-profile",
            "ef-postgresql",
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        root_targets = repository / "Directory.Build.targets"
        original = root_targets.read_text(encoding="utf-8")
        consumer_value = original + "<!-- consumer extension survives -->\n"
        root_targets.write_text(consumer_value, encoding="utf-8")
        unrelated = repository / "consumer-owned.txt"
        unrelated.write_text("keep\n", encoding="utf-8")
        repeated = subprocess.run(command, capture_output=True, text=True)
        if (
            repeated.returncode != 0
            or root_targets.read_text(encoding="utf-8") != consumer_value
            or "preserved consumer files:" not in repeated.stdout
        ):
            raise AssertionError("scaffold-once consumer MSBuild extension was overwritten or not preserved")
        if unrelated.read_text(encoding="utf-8") != "keep\n":
            raise AssertionError("unrelated consumer file changed during synchronization")
        state = json.loads((repository / ".program-kit/managed.json").read_text(encoding="utf-8"))
        if state.get("persistenceProfile") != "ef-postgresql":
            raise AssertionError("selected persistence profile was not recorded")
        root_targets.write_bytes(original.encode("utf-8"))
        converged = subprocess.run(command, capture_output=True, text=True)
        if converged.returncode != 0 or "conflicts: 0" not in converged.stdout:
            raise AssertionError(f"repeated synchronization did not converge: {converged.stdout}{converged.stderr}")


def validate_artifact_ownership() -> None:
    ownership = module(
        ROOT / "extensions/program-kit-governance/scripts/artifact_ownership.py", "artifact_ownership"
    )
    with tempfile.TemporaryDirectory(prefix="program-kit-ownership-") as value:
        root = Path(value)
        artifacts = [
            {"path": path, "ownership": "evidence", "classification": "internal", "lifecycle": "retained"}
            for path in sorted(ownership.CANONICAL)
        ]
        artifacts.append(
            {"path": ".program-kit/eng/Build.ps1", "ownership": "managed", "classification": "internal", "lifecycle": "source"}
        )
        manifest = {"schemaVersion": 1, "feature": "SPC-001", "profiles": ["program-kit"], "artifacts": artifacts}
        path = root / "artifact-ownership.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        loaded = ownership.load_manifest(path)
        tasks = root / "tasks.md"
        tasks.write_text("- [ ] Update `.program-kit/eng/Build.ps1`\n", encoding="utf-8")
        try:
            ownership.validate_tasks(tasks, loaded, None)
        except ValueError as error:
            if "PKA008" not in str(error) or "consumer-owned" not in str(error):
                raise
        else:
            raise AssertionError("managed path edit was not rejected")

        wording = root / "wording.md"
        wording.write_text(
            "- [ ] Do not create `Program.cs`; use a feature adapter instead of `ProgramKit.Build.targets`.\n",
            encoding="utf-8",
        )
        if ownership.task_paths(wording):
            raise AssertionError("prohibited or comparison-only path wording was treated as an edit target")
        explanatory = root / "explanatory.md"
        explanatory.write_text(
            "**Input**: design documents from `specs/001-feature/`\n\n"
            "- [ ] T001 Create `src/Feature/Feature.csproj`\n",
            encoding="utf-8",
        )
        extracted = ownership.task_paths(explanatory)
        if [item[1] for item in extracted] != ["src/Feature/Feature.csproj"]:
            raise AssertionError(f"task path extraction included explanatory prose: {extracted}")

    with tempfile.TemporaryDirectory(prefix="program-kit-external-host-") as value:
        root = Path(value)
        feature = root / "specs/SPEC-101"
        feature.mkdir(parents=True)
        (root / ".specify").mkdir()
        (feature / "spec.md").write_text(
            "## Governance Traceability\n- **Specification roadmap entry**: SPEC-101\n"
            "- **Architecture constraints**: ProgramKit.Host\n- **Owned contracts and data**: API\n",
            encoding="utf-8",
        )
        (feature / "plan.md").write_text(
            "## Architecture Realization\n- **Roadmap entry and status transition**: SPEC-101\n"
            "- **Vertical-slice path**: request to response\n"
            "- **Artifact ownership manifest**: artifact-ownership.json\n"
            "Create `src/PriceCalculator.Host/PriceCalculator.Host.csproj` and `src/PriceCalculator.Host/Program.cs`.\n",
            encoding="utf-8",
        )
        (feature / "tasks.md").write_text(
            "## Governance Completion Evidence\n- **Roadmap transition**: Delivered\n"
            "- **Path and ownership protection**: validated\n",
            encoding="utf-8",
        )
        dotnet_artifacts = [
            {"path": item["path"], "ownership": item["ownership"], "classification": item["classification"], "lifecycle": item["lifecycle"]}
            for item in artifacts
        ]
        dotnet_artifacts.append(
            {"path": "src/PriceCalculator.Host/PriceCalculator.Host.csproj", "ownership": "consumer-owned", "classification": "internal", "lifecycle": "source"}
        )
        dotnet_manifest = {
            "schemaVersion": 1,
            "feature": "SPEC-101",
            "profiles": ["program-kit", "dotnet"],
            "artifacts": dotnet_artifacts,
        }
        (feature / "artifact-ownership.json").write_text(json.dumps(dotnet_manifest), encoding="utf-8")
        try:
            ownership.validate_runtime_profile(feature, dotnet_manifest, True)
        except ValueError as error:
            if "PKA011" not in str(error) or "Program.cs" not in str(error):
                raise
        else:
            raise AssertionError("repository-owned custom host passed the external-host profile")

        dotnet_manifest["artifacts"][-1]["path"] = "src/Catalog/Catalog.csproj"
        authority = root / "docs/architecture/module-capabilities.md"
        authority.parent.mkdir(parents=True)
        authority.write_text("# Module capabilities\n\nCatalog -> Catalog.Core\n", encoding="utf-8")
        (root / "shells.json").write_text(
            json.dumps({"CShells": {"Shells": {"default": {"Features": {"Catalog": {}}}}}}),
            encoding="utf-8",
        )
        dotnet_manifest["runtimeComposition"] = {
            "authorities": ["docs/architecture/module-capabilities.md"],
            "projects": [
                {
                    "path": "src/Catalog/Catalog.csproj",
                    "role": "implementation",
                    "featureIdentities": ["Catalog"],
                    "projectReferences": [],
                    "packageReferences": [],
                }
            ],
            "bindings": [],
            "coreReferences": [],
        }
        (feature / "plan.md").write_text(
            "## Architecture Realization\n- **Roadmap entry and status transition**: SPEC-101\n"
            "- **Vertical-slice path**: request to response\n"
            "- **Artifact ownership manifest**: artifact-ownership.json\n"
            "Pack `src/Catalog/Catalog.csproj` with ProgramKitFeatureIdentity; activate it in "
            "`shells.json`, configure `hostsettings.json`, run `.program-kit/eng/runnable_host.py stage` for "
            "package-closure staging, and publish digest-pinned ProgramKit.Host evidence to "
            "`.program-kit/evidence/host-image.json`.\n",
            encoding="utf-8",
        )
        ownership.validate_runtime_profile(feature, dotnet_manifest, True)

        (feature / "plan.md").write_text(
            "## Architecture Realization\n- **Roadmap entry and status transition**: SPEC-101\n"
            "- **Vertical-slice path**: request to response\n"
            "- **Artifact ownership manifest**: artifact-ownership.json\n"
            "Create `src/Catalog/Catalog.csproj`.\n",
            encoding="utf-8",
        )
        try:
            ownership.validate_runtime_profile(feature, dotnet_manifest, True)
        except ValueError as error:
            if "PKA012" not in str(error) or "shell activation" not in str(error):
                raise
        else:
            raise AssertionError("incomplete external-host closure passed planning validation")

        graph_paths = {
            "src/Catalog.Core/Catalog.Core.csproj": [],
            "src/Catalog.PostgreSql/Catalog.PostgreSql.csproj": [
                "../Catalog.Core/Catalog.Core.csproj"
            ],
            "src/Catalog.Api/Catalog.Api.csproj": [
                "../Catalog.Core/Catalog.Core.csproj",
                "../Catalog.PostgreSql/Catalog.PostgreSql.csproj",
            ],
        }
        for project_path, references in graph_paths.items():
            project = root / project_path
            project.parent.mkdir(parents=True, exist_ok=True)
            reference_xml = "".join(f'<ProjectReference Include="{value}" />' for value in references)
            project.write_text(
                f'<Project Sdk="Microsoft.NET.Sdk"><ItemGroup>{reference_xml}</ItemGroup></Project>',
                encoding="utf-8",
            )
            dotnet_manifest["artifacts"].append(
                {
                    "path": project_path,
                    "ownership": "consumer-owned",
                    "classification": "internal",
                    "lifecycle": "source",
                }
            )
        dotnet_manifest["runtimeComposition"] = {
            "authorities": ["docs/architecture/module-capabilities.md"],
            "projects": [
                {
                    "path": "src/Catalog/Catalog.csproj",
                    "role": "implementation",
                    "featureIdentities": ["Catalog"],
                    "projectReferences": [],
                    "packageReferences": [],
                },
                {
                    "path": "src/Catalog.Core/Catalog.Core.csproj",
                    "role": "core",
                    "projectReferences": [],
                    "packageReferences": [],
                },
                {
                    "path": "src/Catalog.PostgreSql/Catalog.PostgreSql.csproj",
                    "role": "provider",
                    "featureIdentities": ["Catalog.PostgreSql"],
                    "projectReferences": ["src/Catalog.Core/Catalog.Core.csproj"],
                    "packageReferences": [],
                },
                {
                    "path": "src/Catalog.Api/Catalog.Api.csproj",
                    "role": "implementation",
                    "featureIdentities": ["Catalog.Api"],
                    "projectReferences": ["src/Catalog.Core/Catalog.Core.csproj"],
                    "packageReferences": [],
                },
            ],
            "bindings": [
                {
                    "capability": "Catalog.Core.ICatalogRevisionLifecycle",
                    "capabilityProject": "src/Catalog.Core/Catalog.Core.csproj",
                    "implementation": "Catalog.PostgreSql.CatalogRevisionLifecycle",
                    "implementationProject": "src/Catalog.PostgreSql/Catalog.PostgreSql.csproj",
                    "featureIdentity": "Catalog.PostgreSql",
                    "registration": "AddCatalogPostgreSql",
                }
            ],
            "coreReferences": [],
        }
        (root / "shells.json").write_text(
            json.dumps(
                {
                    "CShells": {
                        "Shells": {
                            "default": {
                                "Features": {
                                    "Catalog": {},
                                    "Catalog.Api": {},
                                    "Catalog.PostgreSql": {},
                                }
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        (feature / "plan.md").write_text(
            "## Architecture Realization\n- **Roadmap entry and status transition**: SPEC-101\n"
            "- **Vertical-slice path**: request to response\n"
            "- **Artifact ownership manifest**: artifact-ownership.json\n"
            "Pack projects with ProgramKitFeatureIdentity; activate them in `shells.json`, configure "
            "`hostsettings.json`, run `.program-kit/eng/runnable_host.py stage` for package-closure staging, "
            "and publish digest-pinned ProgramKit.Host evidence to `.program-kit/evidence/host-image.json`.\n",
            encoding="utf-8",
        )
        try:
            ownership.validate_runtime_profile(feature, dotnet_manifest, True)
        except ValueError as error:
            if "PKA015" not in str(error) or "actual" not in str(error) or "Catalog.PostgreSql" not in str(error):
                raise
        else:
            raise AssertionError("unused forbidden ProjectReference passed runtime composition validation")

        api_entry = dotnet_manifest["runtimeComposition"]["projects"][3]
        api_entry["projectReferences"].append("src/Catalog.PostgreSql/Catalog.PostgreSql.csproj")
        try:
            ownership.validate_runtime_profile(feature, dotnet_manifest, True)
        except ValueError as error:
            if "PKA015" not in str(error) or "implementation-to-provider" not in str(error):
                raise
        else:
            raise AssertionError("declared endpoint-to-provider ProjectReference passed validation")
        api_entry["projectReferences"].remove("src/Catalog.PostgreSql/Catalog.PostgreSql.csproj")

        api_project = root / "src/Catalog.Api/Catalog.Api.csproj"
        api_project.write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><ItemGroup>'
            '<ProjectReference Include="../Catalog.Core/Catalog.Core.csproj" />'
            "</ItemGroup></Project>",
            encoding="utf-8",
        )
        ownership.validate_runtime_profile(feature, dotnet_manifest, True)

        pricing_core_path = "src/Pricing.Core/Pricing.Core.csproj"
        pricing_core = root / pricing_core_path
        pricing_core.parent.mkdir(parents=True, exist_ok=True)
        pricing_core.write_text('<Project Sdk="Microsoft.NET.Sdk" />', encoding="utf-8")
        core_decision_path = "docs/decisions/0001-catalog-pricing-language.md"
        core_decision = root / core_decision_path
        core_decision.parent.mkdir(parents=True, exist_ok=True)
        core_decision.write_text("# Accepted published language\n", encoding="utf-8")
        verification_path = "tests/architecture/catalog_pricing_test.py"
        dotnet_manifest["artifacts"].extend(
            [
                {
                    "path": pricing_core_path,
                    "ownership": "consumer-owned",
                    "classification": "internal",
                    "lifecycle": "source",
                },
                {
                    "path": verification_path,
                    "ownership": "consumer-owned",
                    "classification": "internal",
                    "lifecycle": "source",
                },
            ]
        )
        dotnet_manifest["runtimeComposition"]["authorities"].append(core_decision_path)
        dotnet_manifest["runtimeComposition"]["projects"].append(
            {
                "path": pricing_core_path,
                "role": "core",
                "projectReferences": [],
                "packageReferences": [],
            }
        )
        catalog_core_entry = dotnet_manifest["runtimeComposition"]["projects"][1]
        catalog_core_entry["packageReferences"].append("Npgsql")
        catalog_core_project = root / "src/Catalog.Core/Catalog.Core.csproj"
        catalog_core_project.write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><ItemGroup><PackageReference Include="Npgsql" />'
            "</ItemGroup></Project>",
            encoding="utf-8",
        )
        try:
            ownership.validate_runtime_profile(feature, dotnet_manifest, True)
        except ValueError as error:
            if "PKA015" not in str(error) or "Core project" not in str(error) or "Npgsql" not in str(error):
                raise
        else:
            raise AssertionError("persistence package passed the Core boundary validation")
        catalog_core_entry["packageReferences"].clear()
        catalog_core_project.write_text('<Project Sdk="Microsoft.NET.Sdk" />', encoding="utf-8")

        catalog_core_entry["projectReferences"].append(pricing_core_path)
        catalog_core_project.write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><ItemGroup>'
            '<ProjectReference Include="../Pricing.Core/Pricing.Core.csproj" />'
            "</ItemGroup></Project>",
            encoding="utf-8",
        )
        try:
            ownership.validate_runtime_profile(feature, dotnet_manifest, True)
        except ValueError as error:
            if "PKA015" not in str(error) or "Core-to-Core reference requires" not in str(error):
                raise
        else:
            raise AssertionError("undecided direct Core-to-Core reference passed validation")
        dotnet_manifest["runtimeComposition"]["coreReferences"].append(
            {
                "fromProject": "src/Catalog.Core/Catalog.Core.csproj",
                "toProject": pricing_core_path,
                "relationship": "published-language",
                "decision": core_decision_path,
                "verification": verification_path,
            }
        )
        ownership.validate_runtime_profile(feature, dotnet_manifest, True)

        dotnet_manifest["runtimeComposition"]["coreReferences"].clear()
        catalog_core_entry["projectReferences"].clear()
        dotnet_manifest["runtimeComposition"]["projects"].pop()
        dotnet_manifest["runtimeComposition"]["authorities"].pop()
        del dotnet_manifest["artifacts"][-2:]
        catalog_core_project.write_text('<Project Sdk="Microsoft.NET.Sdk" />', encoding="utf-8")

        (root / "shells.json").write_text(
            json.dumps(
                {
                    "CShells": {
                        "Shells": {
                            "default": {
                                "Features": {
                                    "Catalog": {},
                                    "Catalog.Api": {},
                                }
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        try:
            ownership.validate_runtime_profile(feature, dotnet_manifest, True)
        except ValueError as error:
            if "PKA015" not in str(error) or "no activated implementation" not in str(error):
                raise
        else:
            raise AssertionError("provider capability without an activated feature passed validation")

        typescript_manifest = {**dotnet_manifest, "profiles": ["program-kit", "typescript-vite"]}
        (feature / "plan.md").write_text(
            "## Architecture Realization\n- **Roadmap entry and status transition**: SPEC-101\n"
            "- **Vertical-slice path**: request to response\n"
            "- **Artifact ownership manifest**: artifact-ownership.json\n"
            "Adopt the exact npm dependency graph from `npm-candidate.package.json`.\n",
            encoding="utf-8",
        )
        try:
            ownership.validate_npm_graph_evidence(feature, typescript_manifest)
        except ValueError as error:
            if "PKA013" not in str(error):
                raise
        else:
            raise AssertionError("npm package graph passed without strict resolution evidence")
        candidate = feature / "npm-candidate.package.json"
        candidate.write_text('{"devDependencies":{"typescript":"7.0.2"}}\n', encoding="utf-8")
        evidence = root / ".program-kit/evidence/npm-graph.json"
        evidence.parent.mkdir(parents=True)
        evidence.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "packageJson": str(candidate),
                    "packageJsonSha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                    "satisfied": True,
                }
            ),
            encoding="utf-8",
        )
        ownership.validate_npm_graph_evidence(feature, typescript_manifest)

        openapi_manifest = {
            **dotnet_manifest,
            "profiles": ["program-kit", "dotnet", "typescript-vite"],
        }
        (feature / "plan.md").write_text(
            "## Architecture Realization\n- **Roadmap entry and status transition**: SPEC-101\n"
            "- **Vertical-slice path**: request to response\n"
            "- **Artifact ownership manifest**: artifact-ownership.json\n"
            "OpenAPI is produced from Catalog.Api through the managed exporter.\n",
            encoding="utf-8",
        )
        contract_path = feature / "openapi-contract.json"
        contract = {
            "schemaVersion": 1,
            "identity": "catalog-v1",
            "documentName": "v1",
            "shell": "default",
            "producer": {"kind": "ProgramKit.OpenApi.Exporter", "version": "0.9.9-preview.1"},
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
                "directory": "tools/openapi-generator",
                "packageJson": "tools/openapi-generator/package.json",
                "lockFile": "tools/openapi-generator/package-lock.json",
                "script": "generate",
                "generatedTypes": "tools/openapi-generator/generated/catalog.ts",
            },
            "application": {
                "directory": "src/web",
                "packageJson": "src/web/package.json",
                "lockFile": "src/web/package-lock.json",
                "script": "typecheck",
                "tsconfig": "src/web/tsconfig.json",
            },
        }
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        tool_manifest = root / ".program-kit/eng/.config/dotnet-tools.json"
        tool_manifest.parent.mkdir(parents=True)
        tool_manifest.write_text(
            json.dumps(
                {
                    "version": 1,
                    "isRoot": True,
                    "tools": {
                        "programkit.openapi.exporter": {
                            "version": "0.9.9-preview.1",
                            "commands": ["programkit-openapi-export"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        (root / ".oasdiff-version").write_text("1.29.1\n", encoding="utf-8")
        (root / ".program-kit/openapi-contracts.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "contracts": ["specs/SPEC-101/openapi-contract.json"],
                }
            ),
            encoding="utf-8",
        )
        ownership.validate_openapi_pipeline(feature, openapi_manifest, True)
        contract["producer"]["kind"] = "consumer-custom-host"
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        try:
            ownership.validate_openapi_pipeline(feature, openapi_manifest, True)
        except ValueError as error:
            if "PKA014" not in str(error) or "ProgramKit.OpenApi.Exporter" not in str(error):
                raise
        else:
            raise AssertionError("OpenAPI planning passed without the managed producer")


def validate_authorization_boundaries() -> None:
    ownership = module(
        ROOT / "extensions/program-kit-governance/scripts/artifact_ownership.py",
        "authorization_ownership",
    )
    with tempfile.TemporaryDirectory(prefix="program-kit-authorization-ownership-") as value:
        root = Path(value)
        (root / ".specify").mkdir()
        feature = root / "specs/001-access-probe"
        feature.mkdir(parents=True)
        project = root / "src/Access.Api/Access.Api.csproj"
        project.parent.mkdir(parents=True)
        project.write_text('<Project Sdk="Microsoft.NET.Sdk" />\n', encoding="utf-8")
        manifest = {
            "profiles": ["program-kit", "dotnet"],
            "runtimeComposition": {
                "projects": [
                    {
                        "path": "src/Access.Api/Access.Api.csproj",
                        "role": "implementation",
                        "featureIdentities": ["Access.Api"],
                    }
                ]
            },
        }
        (feature / "spec.md").write_text(
            "A bodyless access probe proves transport authorization without a business effect.\n",
            encoding="utf-8",
        )
        (feature / "plan.md").write_text(
            'Map GET /api/access/probe and call RequireAuthorization("permission:calculator-user").\n',
            encoding="utf-8",
        )
        endpoint = project.parent / "AccessFeature.cs"
        endpoint.write_text(
            'endpoints.MapGet("/api/access/probe", () => Results.NoContent())'
            '.RequireAuthorization("permission:calculator-user");\n',
            encoding="utf-8",
        )
        ownership.validate_authorization_ownership(feature, manifest, False)

        endpoint.write_text(
            'var allowed = user.HasClaim(ProgramKitWebOptions.PermissionClaim, requiredPermission);\n',
            encoding="utf-8",
        )
        try:
            ownership.validate_authorization_ownership(feature, manifest, False)
        except ValueError as error:
            if "PKA016" not in str(error) or "reparses canonical permission" not in str(error):
                raise
        else:
            raise AssertionError("duplicate canonical permission parser passed authorization ownership")

        endpoint.write_text('var allowed = user.IsInRole("provider-admin");\n', encoding="utf-8")
        try:
            ownership.validate_authorization_ownership(feature, manifest, False)
        except ValueError as error:
            if "PKA016" not in str(error) or "provider roles" not in str(error):
                raise
        else:
            raise AssertionError("provider-role parsing passed authorization ownership")

        (feature / "spec.md").write_text(
            "An identified quote adjustment changes protected pricing state.\n", encoding="utf-8"
        )
        endpoint.write_text(
            "public bool CanAdjust(Quote quote, ClaimsPrincipal user) => "
            "quote.OwnerSubject == user.Identity!.Name && quote.State == QuoteState.Draft;\n",
            encoding="utf-8",
        )
        ownership.validate_authorization_ownership(feature, manifest, False)

        (feature / "spec.md").write_text(
            "A bodyless access probe has no business effect.\n", encoding="utf-8"
        )
        (feature / "plan.md").write_text(
            "Create AccessPermissionPolicy as an inner authorization policy.\n", encoding="utf-8"
        )
        try:
            ownership.validate_authorization_ownership(feature, manifest, False)
        except ValueError as error:
            if "PKA016" not in str(error) or "no-effect access probe" not in str(error):
                raise
        else:
            raise AssertionError("synthetic no-effect probe service passed proportional authorization validation")


def main() -> int:
    validate_hooks()
    validate_lifecycle()
    validate_utf8()
    validate_feature_activation()
    validate_release_feature_closure()
    validate_preflight_seams()
    validate_toolchain_workflow()
    validate_managed_sources()
    validate_openapi_contracts()
    validate_openapi_initialization()
    validate_npm_graph()
    validate_sync_preservation()
    validate_artifact_ownership()
    validate_authorization_boundaries()
    print("Lifecycle, activation, profile, ownership, and UTF-8 contracts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
