from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPORTER = (
    ROOT
    / "src/dotnet/ProgramKit.OpenApi.Exporter/bin/Release/net10.0/ProgramKit.OpenApi.Exporter.dll"
)
PIPELINE = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/openapi_pipeline.py"


def run(
    command: list[str], cwd: Path, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, env=environment, capture_output=True, text=True, timeout=180
    )


def write_fixture(repository: Path) -> None:
    targets = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/ProgramKit.Build.targets"
    (repository / "WebFeature.csproj").write_text(
        f"""<Project Sdk=\"Microsoft.NET.Sdk\">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>true</IsPackable>
    <PackageId>ProgramKit.OpenApiFixture</PackageId>
    <AssemblyName>ProgramKit.OpenApiFixture</AssemblyName>
    <Version>1.0.0</Version>
    <ProgramKitFeatureIdentity>Fixture.Web</ProgramKitFeatureIdentity>
    <ProgramKitFeatureDependencies>ProgramKit.Authentication</ProgramKitFeatureDependencies>
    <ProgramKitFeatureRoutes>/orders</ProgramKitFeatureRoutes>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include=\"CShells.Abstractions\" Version=\"0.0.29-preview.147\" PrivateAssets=\"all\" />
    <PackageReference Include=\"CShells.AspNetCore.Abstractions\" Version=\"0.0.29-preview.147\" PrivateAssets=\"all\" />
    <PackageReference Include=\"Microsoft.AspNetCore.OpenApi\" Version=\"10.0.11\" PrivateAssets=\"all\" />
  </ItemGroup>
  <Import Project=\"{targets.as_posix()}\" />
</Project>
""",
        encoding="utf-8",
    )
    (repository / "FixtureWebFeature.cs").write_text(
        """using CShells.AspNetCore.Features;
using CShells.Features;
using CShells.Lifecycle;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace ProgramKit.OpenApiFixture;

[ShellFeature(name: "Fixture.Web", DisplayName = "Fixture Web")]
public sealed class FixtureWebFeature : IWebShellFeature
{
    public void ConfigureServices(IServiceCollection services)
    {
        services.AddOpenApi("v1");
        services.AddShellInitializer<ForbiddenInitializer>(LifecyclePhase.Start, order: 0);
    }

    public void MapEndpoints(IEndpointRouteBuilder endpoints, IHostEnvironment? environment) =>
        endpoints.MapGet("orders/{id}", (string id) => new OrderResponse(id)).WithName("GetOrder");
}

public sealed record OrderResponse(string Id);

public sealed class ForbiddenInitializer : IShellInitializer
{
    public Task InitializeAsync(CancellationToken cancellationToken)
    {
        File.WriteAllText("initializer-ran.txt", "unsafe");
        return Task.CompletedTask;
    }
}
""",
        encoding="utf-8",
    )
    shutil.copyfile(ROOT / "NuGet.config", repository / "NuGet.config")
    (repository / "hostsettings.json").write_text("{}\n", encoding="utf-8")
    consumer_shells = {
        "CShells": {
            "Shells": {
                "default": {
                    "Features": {
                        "ProgramKitTasks": {},
                        "Fixture.Web": {},
                        "ProgramKit.Web.ProblemDetails": False,
                    },
                    "Configuration": {
                        "WebRouting": {"Path": "", "RoutePrefix": "api/v1"}
                    },
                }
            }
        }
    }
    profile_shells = {
        "CShells": {
            "Shells": {
                "default": {
                    "Features": {
                        "ProgramKit.Authentication": {},
                        "ProgramKit.Authentication.BffCookie": {},
                        "ProgramKit.WebDefaults": {},
                        "ProgramKit.Web.OpenApi": {},
                        "ProgramKit.Web.ProblemDetails": {},
                    },
                    "Configuration": {
                        "ProgramKit": {
                            "Web": {
                                "Authority": "http://localhost:8080/realms/program-kit",
                                "ClientId": "program-kit-bff",
                                "ClientSecret": "fixture-secret",
                                "Audience": "fixture-api",
                                "Scopes": ["openid", "profile", "fixture-api"],
                                "AllowHttpForLocalDevelopment": True,
                            }
                        }
                    },
                }
            }
        }
    }
    (repository / "shells.json").write_text(
        json.dumps(consumer_shells, indent=2) + "\n", encoding="utf-8"
    )
    profile_path = repository / ".program-kit/web-profile.shells.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(json.dumps(profile_shells, indent=2) + "\n", encoding="utf-8")
    effective = json.loads(json.dumps(profile_shells))
    effective_shell = effective["CShells"]["Shells"]["default"]
    effective_shell["Features"].update(
        consumer_shells["CShells"]["Shells"]["default"]["Features"]
    )
    effective_shell["Configuration"].update(
        consumer_shells["CShells"]["Shells"]["default"]["Configuration"]
    )
    (repository / "direct-shells.json").write_text(
        json.dumps(
            effective,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (repository / "openapi-contract.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "identity": "fixture-api-v1",
                "documentName": "v1",
                "shell": "default",
                "producer": {
                    "kind": "ProgramKit.OpenApi.Exporter",
                    "version": "0.9.9-preview.1",
                },
                "features": ["Fixture.Web"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if not EXPORTER.is_file():
        raise AssertionError("Build ProgramKit.OpenApi.Exporter in Release before this test")
    with tempfile.TemporaryDirectory(prefix="program-kit-openapi-exporter-") as value:
        repository = Path(value)
        write_fixture(repository)
        packages = repository / "packages"
        environment = os.environ.copy()
        environment["NUGET_PACKAGES"] = str(repository / ".program-kit/cache/nuget/packages")
        environment["NUGET_HTTP_CACHE_PATH"] = str(repository / ".program-kit/cache/nuget/http")
        # Keep this repository test independent from an unreadable outer-agent Windows profile.
        environment["APPDATA"] = str(repository / ".program-kit/cache/profile/roaming")
        environment["LOCALAPPDATA"] = str(repository / ".program-kit/cache/profile/local")
        restored = run(
            [
                "dotnet",
                "restore",
                "WebFeature.csproj",
                "--configfile",
                str(repository / "NuGet.config"),
            ],
            repository,
            environment,
        )
        if restored.returncode != 0:
            raise AssertionError(f"fixture restore failed:\n{restored.stdout}{restored.stderr}")
        packed = run(
            [
                "dotnet",
                "pack",
                "WebFeature.csproj",
                "-c",
                "Release",
                "-o",
                str(packages),
                "--no-restore",
            ],
            repository,
            environment,
        )
        if packed.returncode != 0:
            raise AssertionError(f"fixture pack failed:\n{packed.stdout}{packed.stderr}")
        runtime_version = (ROOT / "RUNTIME_VERSION").read_text(encoding="utf-8").strip()
        for package_id in (
            "ProgramKit.Authentication",
            "ProgramKit.Authentication.BffCookie",
            "ProgramKit.WebDefaults",
            "ProgramKit.Web.OpenApi",
            "ProgramKit.Web.ProblemDetails",
            "ProgramKit.Tasks",
        ):
            source = ROOT / f"artifacts/nuget/{package_id}.{runtime_version}.nupkg"
            if not source.is_file():
                raise AssertionError(f"packed built-in feature is missing: {source}")
            shutil.copyfile(source, packages / source.name)

        raw = repository / "artifacts/openapi/fixture.raw.json"
        evidence = repository / ".program-kit/evidence/openapi-export.json"
        command = [
            "dotnet",
            str(EXPORTER),
            "--repository",
            str(repository),
            "--packages",
            str(packages),
            "--shells",
            str(repository / "direct-shells.json"),
            "--hostsettings",
            str(repository / "hostsettings.json"),
            "--contract",
            str(repository / "openapi-contract.json"),
            "--output",
            str(raw),
            "--evidence",
            str(evidence),
        ]
        exported = run(command, repository)
        if exported.returncode != 0:
            raise AssertionError(f"composed OpenAPI export failed:\n{exported.stdout}{exported.stderr}")
        document = json.loads(raw.read_text(encoding="utf-8"))
        if "/api/v1/orders/{id}" not in document.get("paths", {}):
            raise AssertionError(f"composed route is absent from OpenAPI: {document.get('paths')}")
        recorded = json.loads(evidence.read_text(encoding="utf-8"))
        if recorded.get("contractFeatures") != ["Fixture.Web"]:
            raise AssertionError(f"export evidence lost feature coverage: {recorded}")
        if recorded.get("composedFeatures") != ["Fixture.Web", "ProgramKit.Web.OpenApi"]:
            raise AssertionError(f"export evidence lost effective feature composition: {recorded}")
        side_effects = recorded.get("sideEffects", {})
        if any(
            side_effects.get(name)
            for name in ("listenerStarted", "consumerHostedServicesStarted", "shellInitializersRun")
        ):
            raise AssertionError(f"exporter claims a consumer runtime side effect: {recorded}")
        if side_effects.get("pipelineMaterialized") is not True:
            raise AssertionError(f"exporter did not record API Explorer initialization: {recorded}")
        if (repository / "initializer-ran.txt").exists():
            raise AssertionError("OpenAPI export ran a shell lifecycle initializer")

        mismatched_packages = repository / "mismatched-packages"
        feature_source = repository / "FixtureWebFeature.cs"
        feature_source.write_text(
            feature_source.read_text(encoding="utf-8").replace(
                '[ShellFeature(name: "Fixture.Web", DisplayName = "Fixture Web")]',
                '[ShellFeature(name: "Fixture.Clr", DisplayName = "Fixture Web")]',
            ),
            encoding="utf-8",
        )
        mismatched = run(
            [
                "dotnet",
                "pack",
                "WebFeature.csproj",
                "-c",
                "Release",
                "-o",
                str(mismatched_packages),
                "--no-restore",
            ],
            repository,
            environment,
        )
        if mismatched.returncode != 0:
            raise AssertionError(f"mismatched fixture pack failed:\n{mismatched.stdout}{mismatched.stderr}")
        for package in packages.glob("*.nupkg"):
            if "ProgramKit.OpenApiFixture" not in package.name:
                shutil.copyfile(package, mismatched_packages / package.name)
        mismatched_command = list(command)
        mismatched_command[mismatched_command.index("--packages") + 1] = str(mismatched_packages)
        rejected_identity = run(mismatched_command, repository)
        if rejected_identity.returncode != 2 or "does not declare the exact [ShellFeature] identity" not in rejected_identity.stderr:
            raise AssertionError("OpenAPI export accepted CLR/package feature-identity divergence")

        contract = json.loads((repository / "openapi-contract.json").read_text(encoding="utf-8"))
        contract["features"] = []
        (repository / "openapi-contract.json").write_text(
            json.dumps(contract, indent=2) + "\n", encoding="utf-8"
        )
        rejected = run(command, repository)
        if rejected.returncode != 2 or "feature coverage" not in rejected.stderr:
            raise AssertionError("incomplete activated-feature coverage was accepted")

        generator = repository / "tools/openapi-generator"
        application = repository / "src/web"
        generator.mkdir(parents=True)
        application.mkdir(parents=True)
        for directory in (generator, application):
            (directory / "package.json").write_text("{}\n", encoding="utf-8")
            (directory / "package-lock.json").write_text("{}\n", encoding="utf-8")
        (application / "tsconfig.json").write_text("{}\n", encoding="utf-8")
        tool_bin = repository / "tool-bin"
        tool_bin.mkdir()
        if os.name == "nt":
            fake_node = tool_bin / "node.cmd"
            fake_node.write_text("@echo off\r\necho v24.20.0\r\n", encoding="utf-8")
        else:
            fake_node = tool_bin / "node"
            fake_node.write_text("#!/bin/sh\nprintf 'v24.20.0\\n'\n", encoding="utf-8")
            fake_node.chmod(0o755)
        fake_npm = tool_bin / "fake_npm.py"
        fake_npm.write_text(
            """from pathlib import Path
import sys
if sys.argv[1:] == ["--version"]:
    print("11.19.0")
elif sys.argv[1:4] == ["--strict-ssl=true", "run", "generate"]:
    target = Path.cwd() / "generated/types.ts"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("export interface Order { id: string }\\n", encoding="utf-8")
raise SystemExit(0)
""",
            encoding="utf-8",
        )
        if os.name == "nt":
            fake_npm_command = tool_bin / "npm.cmd"
            fake_npm_command.write_text(
                f'@echo off\r\n"{Path(sys.executable).resolve()}" "{fake_npm.resolve()}" %*\r\n',
                encoding="utf-8",
            )
        else:
            fake_npm_command = tool_bin / "npm"
            fake_npm_command.write_text(
                f"#!/bin/sh\nexec '{Path(sys.executable).resolve()}' '{fake_npm.resolve()}' \"$@\"\n",
                encoding="utf-8",
            )
            fake_npm_command.chmod(0o755)
        if os.name == "nt":
            fake_oasdiff = tool_bin / "oasdiff.cmd"
            fake_oasdiff.write_text(
                "@echo off\r\nif \"%1\"==\"--version\" echo oasdiff version v1.29.1\r\nexit /b 0\r\n",
                encoding="utf-8",
            )
        else:
            fake_oasdiff = tool_bin / "oasdiff"
            fake_oasdiff.write_text(
                "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then printf 'oasdiff version v1.29.1\\n'; fi\nexit 0\n",
                encoding="utf-8",
            )
            fake_oasdiff.chmod(0o755)
        (repository / ".oasdiff-version").write_text("1.29.1\n", encoding="utf-8")
        staged_packages = repository / "artifacts/runnable-host/packages"
        staged_packages.mkdir(parents=True)
        for package in packages.glob("*.nupkg"):
            shutil.copyfile(package, staged_packages / package.name)
        staged_root = staged_packages.parent
        for name in ("hostsettings.json", "shells.json"):
            shutil.copyfile(repository / name, staged_root / name)
        staged_profile = staged_root / ".program-kit/web-profile.shells.json"
        staged_profile.parent.mkdir(parents=True)
        shutil.copyfile(repository / ".program-kit/web-profile.shells.json", staged_profile)
        managed = repository / ".program-kit/eng"
        (managed / ".config").mkdir(parents=True)
        shutil.copyfile(
            ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/openapi_contracts.py",
            managed / "openapi_contracts.py",
        )
        shutil.copyfile(
            ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/js_toolchain.py",
            managed / "js_toolchain.py",
        )
        for name in (
            "oasdiff_cli.py",
            "program_kit_version.py",
            "runtime_closure.py",
            "shell_composition.py",
            "toolchain.py",
        ):
            shutil.copyfile(
                ROOT / f"extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/{name}",
                managed / name,
            )
        for name in ("global.json", ".nvmrc", ".npm-version", "VERSION"):
            shutil.copyfile(
                ROOT / f"extensions/program-kit-dotnet/templates/dotnet/files/{name}",
                repository / name,
            )
        (repository / "VERSION").write_text("0.1.0\n", encoding="utf-8")
        sys.path.insert(0, str(managed))
        try:
            import runtime_closure

            runtime_closure.write_success(
                repository,
                staged_root,
                repository / runtime_closure.EVIDENCE,
                "0.9.9",
            )
        finally:
            sys.path.remove(str(managed))
        shutil.copyfile(
            ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/.config/dotnet-tools.json",
            managed / ".config/dotnet-tools.json",
        )
        contract.update(
            {
                "features": ["Fixture.Web"],
                "packageClosure": "artifacts/runnable-host/packages",
                "rawDocument": "artifacts/openapi/fixture.pipeline.raw.json",
                "artifact": "contracts/openapi/fixture.json",
                "baseline": "contracts/openapi/fixture.baseline.json",
                "compatibility": {
                    "oasdiffVersion": "1.29.1",
                    "approval": "contracts/openapi/fixture.breaking-change.json",
                },
                "generator": {
                    "directory": "tools/openapi-generator",
                    "packageJson": "tools/openapi-generator/package.json",
                    "lockFile": "tools/openapi-generator/package-lock.json",
                    "script": "generate",
                    "generatedTypes": "tools/openapi-generator/generated/types.ts",
                },
                "application": {
                    "directory": "src/web",
                    "packageJson": "src/web/package.json",
                    "lockFile": "src/web/package-lock.json",
                    "script": "typecheck",
                    "tsconfig": "src/web/tsconfig.json",
                },
            }
        )
        (repository / "openapi-contract.json").write_text(
            json.dumps(contract, indent=2) + "\n", encoding="utf-8"
        )
        registry = repository / ".program-kit/openapi-contracts.json"
        registry.parent.mkdir(exist_ok=True)
        registry.write_text(
            json.dumps({"schemaVersion": 1, "contracts": ["openapi-contract.json"]}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        dotnet = shutil.which("dotnet")
        if not dotnet:
            raise AssertionError("dotnet is required for the OpenAPI exporter validation")
        toolchain_evidence = repository / ".program-kit/evidence/toolchain.json"
        toolchain_evidence.parent.mkdir(parents=True, exist_ok=True)
        toolchain_evidence.write_text(
            json.dumps(
                {
                    "schemaVersion": 2,
                    "required": {
                        "dotnet": "10.0.202", "node": "24.20.0", "npm": "11.19.0", "oasdiff": "1.29.1"
                    },
                    "resolved": {
                        "dotnet": "10.0.202", "node": "24.20.0", "npm": "11.19.0", "oasdiff": "1.29.1"
                    },
                    "commands": {
                        "dotnet": [str(Path(dotnet).resolve())],
                        "node": [str(fake_node.resolve())],
                        "npm": [str(Path(sys.executable).resolve()), str(fake_npm.resolve())],
                        "oasdiff": [str(fake_oasdiff.resolve())],
                    },
                    "environment": {
                        "npmCache": str((repository / ".program-kit/cache/npm").resolve()),
                        "trustMode": "bundled",
                        "extraCaCertificates": "",
                        "strictSsl": True,
                    },
                    "satisfied": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        pipeline_environment = os.environ.copy()
        pipeline_environment["PATH"] = str(tool_bin) + os.pathsep + pipeline_environment.get("PATH", "")
        pipeline_environment["PROGRAMKIT_NODE_EXECUTABLE"] = str(fake_node.resolve())
        pipeline_environment["PROGRAMKIT_NPM_EXECUTABLE"] = str(fake_npm_command.resolve())
        pipelined = run(
            [
                sys.executable,
                str(PIPELINE),
                "--repository",
                str(repository),
                "--exporter",
                str(EXPORTER),
                "--initialize-baselines",
            ],
            repository,
            pipeline_environment,
        )
        if pipelined.returncode != 0:
            raise AssertionError(
                f"producer-first OpenAPI pipeline failed:\n{pipelined.stdout}{pipelined.stderr}"
            )
        pipeline_evidence = json.loads(
            (repository / ".program-kit/evidence/openapi/pipeline.json").read_text(encoding="utf-8")
        )
        if pipeline_evidence.get("satisfied") is not True:
            raise AssertionError(f"pipeline did not preserve satisfied evidence: {pipeline_evidence}")
        effective_value = json.loads(
            (repository / ".program-kit/cache/openapi/effective-shells.json").read_text(encoding="utf-8")
        )
        effective_default = effective_value["CShells"]["Shells"]["default"]
        if effective_default["Features"].get("ProgramKit.Authentication.BffCookie") != {}:
            raise AssertionError("profile-owned authentication feature was absent from effective shells")
        if effective_default["Features"].get("ProgramKit.Web.ProblemDetails") is not False:
            raise AssertionError("consumer false did not override the profile-owned optional feature")
        if (
            effective_default["Configuration"]
            .get("ProgramKit", {})
            .get("Web", {})
            .get("ClientId")
            != "program-kit-bff"
        ):
            raise AssertionError("deep shell composition discarded profile-owned configuration")
        if not (generator / "generated/types.ts").is_file():
            raise AssertionError("isolated client generation did not run")
        compared = run(
            [
                sys.executable,
                str(PIPELINE),
                "--repository",
                str(repository),
                "--exporter",
                str(EXPORTER),
            ],
            repository,
            pipeline_environment,
        )
        if compared.returncode != 0:
            raise AssertionError(f"pinned oasdiff compatibility path failed:\n{compared.stdout}{compared.stderr}")
        changed_package = next(staged_packages.glob("ProgramKit.OpenApiFixture.*.nupkg"))
        unchanged = changed_package.read_bytes()
        changed_package.write_bytes(unchanged + b"stale-after-stage")
        stale = run(
            [
                sys.executable,
                str(PIPELINE),
                "--repository",
                str(repository),
                "--exporter",
                str(EXPORTER),
            ],
            repository,
            pipeline_environment,
        )
        if stale.returncode != 2 or "PKR022" not in stale.stderr:
            raise AssertionError("OpenAPI export accepted a package changed after runtime staging")

    print("Side-effect-free composed OpenAPI producer and client pipeline validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
