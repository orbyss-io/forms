"""Run the reference producer as an isolated consumer of the packed NuGet family."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    packages = (root / args.packages).resolve()
    artifacts = (root / "artifacts").resolve()
    artifacts.mkdir(exist_ok=True)
    version = (root / "VERSION").read_text().strip()
    with tempfile.TemporaryDirectory(prefix="forms-release-consumer-", dir=artifacts) as temporary:
        consumer = Path(temporary).resolve()
        if not consumer.is_relative_to(artifacts):
            raise AssertionError("The disposable consumer must stay inside repository artifacts.")
        names = ["Orbyss.Forms.Management", "Orbyss.Forms.JsonForms", "Orbyss.Forms.Storage.InMemory", "Orbyss.Forms.Submissions"]
        references = "".join(f'<PackageReference Include="{name}" Version="{version}" />' for name in names)
        (consumer / "Consumer.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework>'
            '<OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable>'
            '<TreatWarningsAsErrors>true</TreatWarningsAsErrors><RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>'
            '</PropertyGroup><ItemGroup>' + references + '</ItemGroup></Project>', encoding="utf-8")
        (consumer / "Directory.Build.props").write_text("<Project />", encoding="utf-8")
        (consumer / "Directory.Packages.props").write_text("<Project />", encoding="utf-8")
        (consumer / "Program.cs").write_bytes((root / "tests/Orbyss.Forms.ReleaseIntegration.Probe/Program.cs").read_bytes())
        cache = consumer / "packages"
        config = ET.Element("configuration")
        sources = ET.SubElement(config, "packageSources")
        ET.SubElement(sources, "clear")
        ET.SubElement(sources, "add", key="packed", value=str(packages))
        ET.SubElement(sources, "add", key="released", value="https://api.nuget.org/v3/index.json")
        mapping = ET.SubElement(config, "packageSourceMapping")
        ET.SubElement(ET.SubElement(mapping, "packageSource", key="packed"), "package", pattern="Orbyss.Forms.*")
        ET.SubElement(ET.SubElement(mapping, "packageSource", key="released"), "package", pattern="*")
        ET.ElementTree(config).write(consumer / "NuGet.config", encoding="utf-8", xml_declaration=True)
        restore = ["dotnet", "restore", "Consumer.csproj", "--configfile", str(consumer / "NuGet.config"), "--packages", str(cache)]
        for command in [restore, restore + ["--locked-mode"], ["dotnet", "build", "-c", "Release", "--no-restore"], ["dotnet", "run", "-c", "Release", "--no-build", "--no-restore", "--", "--output", "output.json"]]:
            result = subprocess.run(command, cwd=consumer, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
            if result.returncode:
                raise AssertionError(result.stdout + "\n" + result.stderr)
        actual = json.loads((consumer / "output.json").read_text(encoding="utf-8"))
        expected = json.loads((root / "src/typescript/tests/fixtures/published-product.json").read_text(encoding="utf-8"))
        if actual != expected:
            raise AssertionError("The packed public API producer differs from the source-built reference.")
    print("Clean NuGet consumer reproduced publication and all conditional-validation vectors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
