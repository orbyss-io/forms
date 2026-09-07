from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/Invoke-RepositoryVerification.ps1"
)
RESTORE_SOURCE = SOURCE.with_name("Restore.ps1")


def run(shell: str, script: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [shell, "-NoProfile", "-File", str(script), "-Mode", "CI"],
        capture_output=True,
        text=True,
        env=environment,
    )


def main() -> int:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        raise AssertionError("PowerShell is required to validate the repository verification hook")
    source_text = SOURCE.read_text(encoding="utf-8")
    if "Invoke-Expression" in source_text or "ConsumerVerificationPath" in source_text:
        raise AssertionError("consumer verification must use the fixed literal eng/verify.ps1 path")

    with tempfile.TemporaryDirectory(prefix="program-kit-verification-hook-") as value:
        repository = Path(value) / "consumer"
        managed = repository / ".program-kit/eng"
        managed.mkdir(parents=True)
        wrapper = managed / SOURCE.name
        shutil.copyfile(SOURCE, wrapper)
        shutil.copyfile(RESTORE_SOURCE, managed / RESTORE_SOURCE.name)
        shutil.copyfile(ROOT / "NuGet.config", repository / "NuGet.config")
        marker = repository / "verification.marker"
        environment = os.environ.copy()
        environment["PROGRAMKIT_TEST_VERIFICATION_MARKER"] = str(marker)
        (managed / "Build.ps1").write_text(
            "param([switch]$SkipRunnableHost, [switch]$LockedMode)\n"
            "Set-Content -LiteralPath $env:PROGRAMKIT_TEST_VERIFICATION_MARKER -Value 'fallback'\n",
            encoding="utf-8",
        )

        absent = run(shell, wrapper, environment)
        if absent.returncode != 0 or marker.read_text(encoding="utf-8").strip() != "fallback":
            raise AssertionError(f"absent consumer hook did not use managed fallback: {absent.stdout}{absent.stderr}")

        consumer = repository / "eng/verify.ps1"
        consumer.parent.mkdir(parents=True, exist_ok=True)
        consumer.write_text(
            "Set-Content -LiteralPath $env:PROGRAMKIT_TEST_VERIFICATION_MARKER -Value 'consumer'\n",
            encoding="utf-8",
        )
        marker.unlink()
        present = run(shell, wrapper, environment)
        if present.returncode != 0 or marker.read_text(encoding="utf-8").strip() != "consumer":
            raise AssertionError(f"consumer verification did not replace the fallback: {present.stdout}{present.stderr}")

        consumer.write_text("exit 23\n", encoding="utf-8")
        failed = run(shell, wrapper, environment)
        if failed.returncode == 0:
            raise AssertionError("consumer verification failure did not fail the managed entry point")

        consumer.unlink()
        consumer.mkdir()
        unsafe = run(shell, wrapper, environment)
        if unsafe.returncode == 0 or "regular repository file" not in (unsafe.stdout + unsafe.stderr):
            raise AssertionError("non-file consumer verification path was accepted")

    print("Managed repository verification hook absence, presence, failure, and path safety passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
