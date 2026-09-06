from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    package = root / "artifacts" / f"program-kit-governance-{version}.zip"
    with tempfile.TemporaryDirectory(prefix="program-kit-packaged-ui-") as temporary:
        consumer = Path(temporary) / "consumer"
        consumer.mkdir()
        installed = consumer / ".specify/extensions/program-kit-governance"
        with zipfile.ZipFile(package) as archive:
            for member in archive.infolist():
                path = PurePosixPath(member.filename)
                if path.is_absolute() or ".." in path.parts or "\\" in member.filename or ":" in member.filename:
                    raise AssertionError("Unsafe packaged path")
            archive.extractall(installed)
        for action in ("init", "validate", "build", "check"):
            result = subprocess.run([sys.executable, str(installed / "scripts/ui_profile.py"), action, "--target", str(consumer)],
                                    cwd=consumer, capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise AssertionError(f"Packaged UI {action} failed: {result.stdout}\n{result.stderr}")
        output = consumer / "web/generated/program-kit"
        resources = json.loads((output / "publication.json").read_text())["resources"]
        assert not any(resource["route"] == "/account" for resource in resources)
        assert (output / "acceptance/tests/package-lock.json").is_file()
        assert (output / "public/assets/icons/LICENSE.txt").is_file()
        assert (output / "integration/tokens.json").is_file()
    print("Packaged UI init/validate/build/check passed in a clean consumer without repository imports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
