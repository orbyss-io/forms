from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files"


def main() -> int:
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        raise RuntimeError("dotnet is required for the consumer package-source restore test")

    with tempfile.TemporaryDirectory(prefix="program-kit-consumer-restore-") as value:
        repository = Path(value)
        managed = repository / ".program-kit/eng"
        managed.mkdir(parents=True)
        shutil.copyfile(
            TEMPLATE / ".program-kit/eng/ProgramKit.Packages.props",
            managed / "ProgramKit.Packages.props",
        )
        shutil.copyfile(TEMPLATE / "global.json", repository / "global.json")
        (repository / "Directory.Packages.props").write_text(
            """<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
    <CentralPackageTransitivePinningEnabled>true</CentralPackageTransitivePinningEnabled>
  </PropertyGroup>
  <Import Project=".program-kit/eng/ProgramKit.Packages.props" />
  <ItemGroup>
    <PackageVersion Include="Testcontainers.PostgreSql" Version="4.14.0" />
    <PackageVersion Include="TngTech.ArchUnitNET" Version="0.13.4" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        project = repository / "Consumer.Tests.csproj"
        project.write_text(
            """<Project Sdk="MSTest.Sdk/4.3.3">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <Nullable>enable</Nullable>
    <NoWarn>$(NoWarn);NU1510</NoWarn>
  </PropertyGroup>
  <ItemGroup>
    <FrameworkReference Include="Microsoft.AspNetCore.App" />
    <PackageReference Include="Microsoft.Extensions.DependencyInjection.Abstractions" />
    <PackageReference Include="Microsoft.Extensions.Logging.Abstractions" />
    <PackageReference Include="Testcontainers.PostgreSql" />
    <PackageReference Include="TngTech.ArchUnitNET" />
  </ItemGroup>
</Project>
""",
            encoding="utf-8",
        )
        (repository / "ConsumerTests.cs").write_text(
            """using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using Testcontainers.PostgreSql;

namespace Consumer.Tests;

[TestClass]
public sealed class ConsumerTests
{
    [TestMethod]
    public void PlatformLoggingAndPostgreSqlFixtureCompose()
    {
        ILogger logger = NullLogger.Instance;
        IServiceProviderIsService? serviceProbe = null;
        var builder = new PostgreSqlBuilder("postgres:18.3-alpine");

        Assert.IsNotNull(logger);
        Assert.IsNull(serviceProbe);
        Assert.IsNotNull(builder);
    }
}
""",
            encoding="utf-8",
        )
        solution = repository / "Consumer.slnx"
        solution.write_text(
            '<Solution><Project Path="Consumer.Tests.csproj" /></Solution>\n', encoding="utf-8"
        )
        packages = repository / ".packages"
        environment = os.environ.copy()
        environment["NUGET_PACKAGES"] = str(packages)
        environment["NUGET_HTTP_CACHE_PATH"] = str(repository / ".http-cache")
        result = subprocess.run(
            [
                dotnet,
                "restore",
                str(solution),
                "--configfile",
                str(TEMPLATE / "NuGet.config"),
                "--force-evaluate",
            ],
            cwd=repository,
            env=environment,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError("Consumer restore failed:\n" + result.stdout + result.stderr)
        lock = repository / "packages.lock.json"
        if not lock.is_file():
            raise AssertionError("Consumer restore did not emit dependency lock evidence")
        lock_text = lock.read_text(encoding="utf-8")
        if not (packages / "mstest.sdk" / "4.3.3").is_dir():
            raise AssertionError("Consumer restore did not resolve MSTest.Sdk 4.3.3")
        for package in (
            "Testcontainers.PostgreSql",
            "Docker.DotNet.Enhanced",
            "SSH.NET",
            "TngTech.ArchUnitNET",
            "CycleDetection",
            "Mono.Cecil",
        ):
            if f'"{package}"' not in lock_text:
                raise AssertionError(f"Consumer dependency closure is missing {package}")
        dependencies = json.loads(lock_text)["dependencies"]["net10.0"]
        for package in (
            "Microsoft.Extensions.DependencyInjection.Abstractions",
            "Microsoft.Extensions.Logging.Abstractions",
        ):
            if dependencies.get(package, {}).get("resolved") != "10.0.11":
                raise AssertionError(
                    f"managed transitive pin did not converge {package}: {dependencies.get(package)}; "
                    f"resolved packages: {sorted(dependencies)}"
                )

        build = subprocess.run(
            [dotnet, "build", str(solution), "-c", "Release", "--no-restore"],
            cwd=repository,
            env=environment,
            capture_output=True,
            text=True,
        )
        if build.returncode != 0 or "MSB3277" in build.stdout + build.stderr:
            raise AssertionError(
                "net10/Testcontainers graph did not build cleanly:\n" + build.stdout + build.stderr
            )
        test = subprocess.run(
            [
                dotnet,
                "test",
                "--solution",
                str(solution),
                "-c",
                "Release",
                "--no-build",
                "--no-restore",
            ],
            cwd=repository,
            env=environment,
            capture_output=True,
            text=True,
        )
        if test.returncode != 0 or "Passed!" not in test.stdout + test.stderr:
            raise AssertionError(
                "managed MTP dotnet test experience failed:\n" + test.stdout + test.stderr
            )

    print("Consumer package graph, net10 abstractions, and MTP test experience are coherent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
