from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/Build.ps1"
RESTORE = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/Restore.ps1"


def main() -> int:
    for path in (
        ROOT / "global.json",
        ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/global.json",
    ):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("test", {}).get("runner") != "Microsoft.Testing.Platform":
            raise AssertionError(f"{path} does not select Microsoft.Testing.Platform")

    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        raise AssertionError("PowerShell is required to validate the managed Build.ps1 contract")
    with tempfile.TemporaryDirectory(prefix="program-kit-build-contract-") as value:
        repository = Path(value)
        managed = repository / ".program-kit/eng"
        managed.mkdir(parents=True)
        shutil.copyfile(BUILD, managed / "Build.ps1")
        shutil.copyfile(RESTORE, managed / "Restore.ps1")
        (repository / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        (repository / "Consumer.slnx").write_text(
            '<Solution><Project Path="Consumer.csproj" /></Solution>\n', encoding="utf-8"
        )
        (repository / "Consumer.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework>'
            '</PropertyGroup></Project>\n',
            encoding="utf-8",
        )
        nuget_config = repository / "NuGet.config"
        nuget_config.write_text("<configuration />\n", encoding="utf-8")
        log = repository / "dotnet.log"
        tools = repository / "tools"
        tools.mkdir()
        if os.name == "nt":
            dotnet = tools / "dotnet.cmd"
            dotnet.write_text(
                "@echo off\r\n"
                f"echo %*^|%NUGET_PACKAGES%^|%NUGET_HTTP_CACHE_PATH%^|%NUGET_SCRATCH%^|"
                f"%NUGET_PLUGINS_CACHE_PATH%^|%DOTNET_CLI_HOME%^|%APPDATA%^|%LOCALAPPDATA%>>\"{log}\"\r\n"
                "if \"%1\"==\"sln\" goto solution_list\r\n"
                "if \"%1\"==\"msbuild\" goto test_property\r\n"
                "exit /b 0\r\n"
                ":solution_list\r\n"
                "echo Project(s)\r\n"
                "echo ----------\r\n"
                "echo Consumer.csproj\r\n"
                "exit /b 0\r\n"
                ":test_property\r\n"
                "echo true\r\n"
                "exit /b 0\r\n",
                encoding="utf-8",
            )
        else:
            dotnet = tools / "dotnet"
            dotnet.write_text(
                "#!/bin/sh\n"
                f"printf '%s|%s|%s|%s|%s|%s|%s|%s\\n' \"$*\" \"$NUGET_PACKAGES\" "
                f"\"$NUGET_HTTP_CACHE_PATH\" \"$NUGET_SCRATCH\" \"$NUGET_PLUGINS_CACHE_PATH\" "
                f"\"$DOTNET_CLI_HOME\" \"$APPDATA\" \"$LOCALAPPDATA\" >> '{log}'\n"
                "if [ \"$1\" = sln ]; then printf 'Project(s)\\n----------\\nConsumer.csproj\\n'; fi\n"
                "if [ \"$1\" = msbuild ]; then printf 'true\\n'; fi\n",
                encoding="utf-8",
            )
            dotnet.chmod(0o755)
        environment = os.environ.copy()
        environment["PATH"] = str(tools) + os.pathsep + environment.get("PATH", "")
        hostile_profile = repository / "denied-roaming-profile/NuGet"
        hostile_profile.mkdir(parents=True)
        (hostile_profile / "NuGet.Config").write_text("<malformed", encoding="utf-8")
        environment["APPDATA"] = str(hostile_profile.parent)
        result = subprocess.run(
            [shell, "-NoProfile", "-File", str(managed / "Build.ps1"), "-SkipRunnableHost"],
            cwd=repository,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise AssertionError(f"managed Build.ps1 failed in restricted-profile fixture: {result.stdout}{result.stderr}")
        entries = log.read_text(encoding="utf-8").splitlines()
        restore = next((line for line in entries if line.startswith("restore ")), "")
        if "--configfile" not in restore or str(nuget_config) not in restore:
            raise AssertionError(f"restore did not bind the reviewed repository NuGet.config: {restore}")
        for expected in (
            repository / ".program-kit/cache/nuget/packages",
            repository / ".program-kit/cache/nuget/http",
            repository / ".program-kit/cache/nuget/scratch",
            repository / ".program-kit/cache/nuget/plugins",
            repository / ".program-kit/cache/dotnet-home",
        ):
            if str(expected) not in restore:
                raise AssertionError(f"restore did not use repository-owned NuGet cache {expected}: {restore}")
        if os.name == "nt":
            for expected in (
                repository / ".program-kit/cache/profile/roaming",
                repository / ".program-kit/cache/profile/local",
            ):
                if str(expected) not in restore:
                    raise AssertionError(f"restore did not isolate its Windows profile path {expected}: {restore}")
        test = next((line for line in entries if line.startswith("test ")), "")
        if "--solution" not in test or str(repository / "Consumer.slnx") not in test:
            raise AssertionError(f"managed Build.ps1 did not use MTP solution syntax: {test}")

        consumer = repository / "eng/verify.ps1"
        consumer.parent.mkdir(parents=True, exist_ok=True)
        consumer.write_text(
            f'"$env:APPDATA|$env:LOCALAPPDATA|$env:NUGET_PACKAGES" | Set-Content -LiteralPath "{repository / "consumer-environment.txt"}"\n',
            encoding="utf-8",
        )
        shutil.copyfile(
            ROOT
            / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/Invoke-RepositoryVerification.ps1",
            managed / "Invoke-RepositoryVerification.ps1",
        )
        verification = subprocess.run(
            [shell, "-NoProfile", "-File", str(managed / "Invoke-RepositoryVerification.ps1")],
            cwd=repository,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if verification.returncode != 0:
            raise AssertionError(
                f"managed verification wrapper did not isolate consumer commands: {verification.stdout}{verification.stderr}"
            )
        consumer_environment = (repository / "consumer-environment.txt").read_text(encoding="utf-8")
        for expected in (
            repository / ".program-kit/cache/nuget/packages",
            repository / ".program-kit/cache/profile/roaming" if os.name == "nt" else None,
            repository / ".program-kit/cache/profile/local" if os.name == "nt" else None,
        ):
            if expected is not None and str(expected) not in consumer_environment:
                raise AssertionError(
                    f"consumer verification did not inherit repository isolation {expected}: {consumer_environment}"
                )

        if os.name == "nt" and shutil.which("dotnet"):
            blocked_appdata = repository / "denied-roaming-profile"
            blocked_config = blocked_appdata / "NuGet/NuGet.Config"
            blocked_config.parent.mkdir(parents=True, exist_ok=True)
            blocked_config.write_text("<configuration />\n", encoding="utf-8")
            identity = subprocess.run(
                ["whoami", "/user", "/fo", "csv", "/nh"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            sid = next(csv.reader([identity]))[1]
            denied = subprocess.run(
                ["icacls", str(blocked_config), "/inheritance:r", "/deny", f"*{sid}:(R)"],
                capture_output=True,
                text=True,
            )
            if denied.returncode != 0:
                raise AssertionError(f"could not create restricted NuGet.Config fixture: {denied.stdout}{denied.stderr}")
            real_environment = os.environ.copy()
            real_environment["APPDATA"] = str(blocked_appdata)
            real_environment["LOCALAPPDATA"] = str(blocked_appdata)
            real_environment["DOTNET_CLI_HOME"] = str(repository / ".direct-dotnet-home")
            try:
                direct = subprocess.run(
                    [
                        "dotnet",
                        "restore",
                        str(repository / "Consumer.slnx"),
                        "--configfile",
                        str(nuget_config),
                    ],
                    cwd=repository,
                    env=real_environment,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if direct.returncode == 0 or "NuGet.Config" not in direct.stdout + direct.stderr:
                    raise AssertionError("restricted Windows profile fixture did not reproduce ambient NuGet access")
                isolated = subprocess.run(
                    [
                        shell,
                        "-NoProfile",
                        "-File",
                        str(managed / "Restore.ps1"),
                        "-Subject",
                        str(repository / "Consumer.slnx"),
                    ],
                    cwd=repository,
                    env=real_environment,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if isolated.returncode != 0:
                    raise AssertionError(
                        "repository-isolated restore did not survive inaccessible ambient NuGet configuration: "
                        + isolated.stdout
                        + isolated.stderr
                    )
            finally:
                subprocess.run(
                    ["icacls", str(blocked_config), "/remove:d", f"*{sid}"],
                    capture_output=True,
                    text=True,
                )
                subprocess.run(
                    ["icacls", str(blocked_config), "/grant:r", f"*{sid}:(F)", "/inheritance:e"],
                    capture_output=True,
                    text=True,
                )

    print("Restricted-profile NuGet restore and Microsoft.Testing.Platform build contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
