from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files"


def load_module(path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("runnable_host_schema_probe", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {path}")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def validate(instance: object, schema: dict, path: str = "$") -> None:
    expected_type = schema.get("type")
    if expected_type is not None:
        names = expected_type if isinstance(expected_type, list) else [expected_type]
        checks = {
            "object": lambda value: isinstance(value, dict),
            "array": lambda value: isinstance(value, list),
            "string": lambda value: isinstance(value, str),
            "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
            "boolean": lambda value: isinstance(value, bool),
            "null": lambda value: value is None,
        }
        if not any(checks[name](instance) for name in names):
            raise AssertionError(f"{path} does not match JSON Schema type {names}")
    if "const" in schema and instance != schema["const"]:
        raise AssertionError(f"{path} does not match JSON Schema const")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise AssertionError(f"{path} is shorter than minLength")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise AssertionError(f"{path} does not match JSON Schema pattern")
    if isinstance(instance, dict):
        required = schema.get("required", [])
        missing = [name for name in required if name not in instance]
        if missing:
            raise AssertionError(f"{path} is missing required properties {missing}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            additional = sorted(set(instance) - set(properties))
            if additional:
                raise AssertionError(f"{path} has undeclared properties {additional}")
        for name, child in instance.items():
            if name in properties:
                validate(child, properties[name], f"{path}.{name}")
    if isinstance(instance, list) and isinstance(schema.get("items"), dict):
        for index, child in enumerate(instance):
            validate(child, schema["items"], f"{path}[{index}]")


def main() -> int:
    producer = load_module(TEMPLATE / ".program-kit/eng/runnable_host.py")
    schema = json.loads(
        (TEMPLATE / ".program-kit/runnable-host.schema.json").read_text(encoding="utf-8")
    )
    with tempfile.TemporaryDirectory(prefix="program-kit-runnable-schema-") as value:
        root = Path(value)
        repository = root / "consumer"
        staged = repository / "artifacts/staged"
        repository.mkdir()
        staged.mkdir(parents=True)
        (repository / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        (staged / "hostsettings.json").write_text("{}\n", encoding="utf-8")
        (staged / "shells.json").write_text(
            json.dumps({"CShells": {"Shells": {"default": {"Features": {}}}}}) + "\n",
            encoding="utf-8",
        )
        packages = staged / "packages"
        packages.mkdir()
        package = packages / "Example.Feature.1.0.0.nupkg"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr(
                "Example.Feature.nuspec",
                "<package><metadata><id>Example.Feature</id><version>1.0.0</version></metadata></package>",
            )
        closure_path = repository / ".program-kit/evidence/runtime-closure.json"
        previous_sha = os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"] = "a" * 40
        try:
            for profile_shells in (None, {"CShells": {"Shells": {"default": {"Features": {}}}}}):
                profile_path = staged / ".program-kit/web-profile.shells.json"
                if profile_shells is None:
                    profile_path.unlink(missing_ok=True)
                else:
                    profile_path.parent.mkdir(parents=True, exist_ok=True)
                    profile_path.write_text(json.dumps(profile_shells) + "\n", encoding="utf-8")
                output = root / "runnable-host.json"
                producer.runtime_closure.write_success(
                    repository,
                    staged,
                    closure_path,
                    producer.PROGRAM_KIT_VERSION,
                )
                producer.describe(
                    repository,
                    staged,
                    "ghcr.io/example/consumer",
                    "v1.0.0",
                    "sha256:" + "b" * 64,
                    output,
                )
                validate(json.loads(output.read_text(encoding="utf-8")), schema)
                closure_schema = json.loads(
                    (TEMPLATE / ".program-kit/runtime-closure.schema.json").read_text(encoding="utf-8")
                )
                validate(json.loads(closure_path.read_text(encoding="utf-8")), closure_schema)
        finally:
            if previous_sha is None:
                os.environ.pop("GITHUB_SHA", None)
            else:
                os.environ["GITHUB_SHA"] = previous_sha

    print("Runnable-host and runtime-closure producers validate against their shipped schemas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
