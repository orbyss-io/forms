"""Regenerate the public-API producer output and check its committed byte-for-byte fixture."""
from pathlib import Path
import subprocess


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output = root / "artifacts/release-integration.json"
    output.parent.mkdir(exist_ok=True)
    subprocess.run([
        "dotnet", "run", "--project", "tests/Orbyss.Forms.ReleaseIntegration.Probe",
        "-c", "Release", "--no-build", "--no-restore", "--", "--output", str(output),
    ], cwd=root, check=True, timeout=180)
    expected = root / "src/typescript/tests/fixtures/published-product.json"
    if output.read_bytes() != expected.read_bytes():
        raise AssertionError("Published reference drifted. Regenerate with the documented producer command and review the change.")
    print("Catalog publication, conditional validation, compatibility and deterministic reference fixture passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
