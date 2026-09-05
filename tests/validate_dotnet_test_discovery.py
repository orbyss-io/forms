from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/eng/program-kit/Build.ps1"
RESTORE = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/eng/program-kit/Restore.ps1"


def write_fake_dotnet(tools: Path) -> None:
    (tools / "fake_dotnet.py").write_text(
        textwrap.dedent(
            r"""
            from __future__ import annotations

            import os
            import re
            import sys
            import xml.etree.ElementTree as ET
            from pathlib import Path


            args = sys.argv[1:]
            log = Path(os.environ["PROGRAM_KIT_DISCOVERY_LOG"])
            with log.open("a", encoding="utf-8") as stream:
                stream.write(" ".join(args) + "\n")

            if len(args) >= 3 and args[0] in {"sln", "solution"} and args[-1] == "list":
                solution = Path(args[1])
                if solution.name.startswith("BrokenDiscovery"):
                    print("deliberate solution enumeration failure", file=sys.stderr)
                    raise SystemExit(19)
                if solution.suffix.lower() == ".slnx":
                    document = ET.parse(solution)
                    projects = [
                        element.attrib["Path"]
                        for element in document.iter()
                        if element.tag.rsplit("}", 1)[-1] == "Project" and "Path" in element.attrib
                    ]
                else:
                    projects = re.findall(
                        r'^Project\("[^"]+"\)\s*=\s*"[^"]*",\s*"([^"]+\.(?:cs|fs|vb)proj)"',
                        solution.read_text(encoding="utf-8"),
                        flags=re.IGNORECASE | re.MULTILINE,
                    )
                print("Project(s)")
                print("----------")
                print("\n".join(projects))
                raise SystemExit(0)

            if args and args[0] == "msbuild" and any(
                value.lower() == "-getproperty:istestproject" for value in args
            ):
                project = Path(args[1])
                content = project.read_text(encoding="utf-8")
                if "<FailTestDiscovery>true</FailTestDiscovery>" in content:
                    print("deliberate project evaluation failure", file=sys.stderr)
                    raise SystemExit(23)
                match = re.search(
                    r"<IsTestProject>\s*(true|false)\s*</IsTestProject>",
                    content,
                    flags=re.IGNORECASE,
                )
                if match:
                    print(match.group(1).lower())
                raise SystemExit(0)

            raise SystemExit(0)
            """
        ).lstrip(),
        encoding="utf-8",
    )
    if os.name == "nt":
        (tools / "dotnet.cmd").write_text(
            "@echo off\r\n"
            f'"{sys.executable}" "%~dp0fake_dotnet.py" %*\r\n'
            "exit /b %ERRORLEVEL%\r\n",
            encoding="utf-8",
        )
    else:
        dotnet = tools / "dotnet"
        dotnet.write_text(
            "#!/bin/sh\n"
            f"exec {shlex.quote(sys.executable)} \"$(dirname \"$0\")/fake_dotnet.py\" \"$@\"\n",
            encoding="utf-8",
        )
        dotnet.chmod(0o755)


def write_project(path: Path, *, is_test: bool, fail_discovery: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    failure = "<FailTestDiscovery>true</FailTestDiscovery>" if fail_discovery else ""
    path.write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework>'
        f"<IsTestProject>{str(is_test).lower()}</IsTestProject>{failure}"
        "</PropertyGroup></Project>\n",
        encoding="utf-8",
    )


def write_solution(path: Path, projects: list[Path]) -> None:
    relative = [project.relative_to(path.parent) for project in projects]
    if path.suffix.lower() == ".slnx":
        entries = "".join(f'<Project Path="{project.as_posix()}" />' for project in relative)
        path.write_text(f"<Solution>{entries}</Solution>\n", encoding="utf-8")
        return

    lines = ["Microsoft Visual Studio Solution File, Format Version 12.00"]
    for index, project in enumerate(relative, start=1):
        project_path = str(project).replace("/", "\\")
        lines.extend(
            [
                f'Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "Project{index}", '
                f'"{project_path}", "{{00000000-0000-0000-0000-{index:012d}}}"',
                "EndProject",
            ]
        )
    lines.extend(["Global", "EndGlobal"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_repository(value: str, solution_name: str, test_flags: tuple[bool, ...]) -> tuple[Path, Path]:
    repository = Path(value)
    managed = repository / "eng/program-kit"
    managed.mkdir(parents=True)
    shutil.copyfile(BUILD, managed / "Build.ps1")
    shutil.copyfile(RESTORE, managed / "Restore.ps1")
    (repository / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (repository / "NuGet.config").write_text("<configuration />\n", encoding="utf-8")
    projects = []
    for index, is_test in enumerate(test_flags, start=1):
        suffix = ".Tests" if is_test else ""
        project = repository / f"src/Project{index}{suffix}/Project{index}{suffix}.csproj"
        write_project(project, is_test=is_test)
        projects.append(project)
    write_solution(repository / solution_name, projects)
    tools = repository / "tools"
    tools.mkdir()
    write_fake_dotnet(tools)
    return repository, tools


def run_build(shell: str, repository: Path, tools: Path) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    log = repository / "dotnet.log"
    environment = os.environ.copy()
    environment["PATH"] = str(tools) + os.pathsep + environment.get("PATH", "")
    environment["PROGRAM_KIT_DISCOVERY_LOG"] = str(log)
    result = subprocess.run(
        [shell, "-NoProfile", "-File", str(repository / "eng/program-kit/Build.ps1"), "-SkipRunnableHost"],
        cwd=repository,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    entries = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
    return result, entries


def validate_topologies(shell: str) -> None:
    scenarios = (
        ("zero-slnx", "Consumer.slnx", (False,), 0),
        ("zero-sln", "Consumer.sln", (False,), 0),
        ("one-sln", "Consumer.sln", (False, True), 1),
        ("multiple-slnx", "Consumer.slnx", (False, True, True), 2),
    )
    for name, solution_name, flags, expected_test_count in scenarios:
        with tempfile.TemporaryDirectory(prefix=f"program-kit-build-{name}-") as value:
            repository, tools = create_repository(value, solution_name, flags)
            result, entries = run_build(shell, repository, tools)
            if result.returncode != 0:
                raise AssertionError(f"managed Build.ps1 failed for {name}: {result.stdout}{result.stderr}")
            probes = [line for line in entries if line.startswith("msbuild ")]
            if len(probes) != len(flags):
                raise AssertionError(f"{name} evaluated {len(probes)} projects instead of {len(flags)}: {entries}")
            tests = [line for line in entries if line.startswith("test ")]
            if expected_test_count == 0:
                if tests:
                    raise AssertionError(f"{name} invoked dotnet test for an empty test selection: {tests}")
                if "No .NET test projects are included" not in result.stdout:
                    raise AssertionError(f"{name} did not explain the successful test skip: {result.stdout}")
            elif len(tests) != 1 or "--solution" not in tests[0]:
                raise AssertionError(f"{name} did not invoke one solution-wide MTP test pass: {tests}")


def validate_discovery_failures(shell: str) -> None:
    with tempfile.TemporaryDirectory(prefix="program-kit-build-project-failure-") as value:
        repository, tools = create_repository(value, "Consumer.slnx", (True,))
        project = next(repository.glob("src/**/*.csproj"))
        write_project(project, is_test=True, fail_discovery=True)
        result, _ = run_build(shell, repository, tools)
        if result.returncode == 0 or "Could not evaluate IsTestProject" not in result.stdout + result.stderr:
            raise AssertionError(f"project evaluation failure did not fail closed: {result.stdout}{result.stderr}")

    with tempfile.TemporaryDirectory(prefix="program-kit-build-solution-failure-") as value:
        repository, tools = create_repository(value, "BrokenDiscovery.slnx", (False,))
        result, _ = run_build(shell, repository, tools)
        if result.returncode == 0 or "Could not enumerate projects" not in result.stdout + result.stderr:
            raise AssertionError(f"solution enumeration failure did not fail closed: {result.stdout}{result.stderr}")


def main() -> int:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        raise AssertionError("PowerShell is required to validate managed .NET test discovery")
    validate_topologies(shell)
    validate_discovery_failures(shell)
    print("Managed .NET test discovery passed for zero, one, and multiple test projects in .sln and .slnx.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
