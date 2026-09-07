from __future__ import annotations

import subprocess
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    forms = root / "src/dotnet/Orbyss.Forms.Storage.InMemory"
    localization = root / "src/dotnet/Orbyss.Localization.Storage.InMemory"
    for package in (forms, localization):
        source = "\n".join(path.read_text(encoding="utf-8") for path in package.rglob("*") if path.suffix in {".cs", ".csproj"})
        for forbidden in ("EntityFrameworkCore", "Microsoft.Data.Sqlite", "Azure.", "Amazon.", "IWebShellFeature", "InternalsVisibleTo"):
            if forbidden in source:
                raise AssertionError(f"{package.name} owns a provider, web boundary, or privileged test seam: {forbidden}")

    forms_source = "\n".join(path.read_text(encoding="utf-8") for path in forms.glob("*.cs"))
    for contract in ("IFormDefinitionStore", "IFormReleaseStore", "IFormReleaseRetirementStore", "IFormSubmissionStore", "IFormAttachmentStore", "IFormAttachmentContentStore"):
        if contract not in forms_source:
            raise AssertionError(f"The in-memory Forms reference adapter does not implement {contract}")
    localization_source = "\n".join(path.read_text(encoding="utf-8") for path in localization.glob("*.cs"))
    for contract in ("ILocalizationCatalogStore", "ILocalizationReleaseStore", "ILocalizationReleaseRetirementStore"):
        if contract not in localization_source:
            raise AssertionError(f"The in-memory Localization reference adapter does not implement {contract}")

    probe = root / "tests/dotnet/Orbyss.Forms.Storage.InMemory.Probe/Orbyss.Forms.Storage.InMemory.Probe.csproj"
    result = subprocess.run(
        ["dotnet", "run", "--project", str(probe), "-c", "Release", "--no-build", "--no-restore"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    if "storage probe passed" not in result.stdout:
        raise AssertionError("The in-memory storage probe did not report success")
    print("Orbyss Forms in-memory Forms and Localization persistence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
