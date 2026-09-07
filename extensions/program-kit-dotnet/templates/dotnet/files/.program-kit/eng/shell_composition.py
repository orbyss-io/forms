from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


PROFILE_SHELLS = Path(".program-kit/web-profile.shells.json")
CONSUMER_SHELLS = Path("shells.json")


def load(path: Path, required: bool) -> dict:
    if not path.is_file():
        if required:
            raise ValueError(f"PKC001 required shell configuration is missing: {path}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        shells = value["CShells"]["Shells"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError(f"PKC002 {path} must use the CShells:Shells object schema: {error}") from error
    if not isinstance(value, dict) or not isinstance(shells, dict) or not shells:
        raise ValueError(f"PKC002 {path} must declare at least one named shell")
    for shell_name, shell in shells.items():
        features = shell.get("Features") if isinstance(shell, dict) else None
        if not isinstance(shell_name, str) or not shell_name or not isinstance(features, dict):
            raise ValueError(f"PKC003 {path} shell {shell_name!r} must declare a Features object")
        for identity, settings in features.items():
            if not isinstance(identity, str) or not identity or not (settings is False or isinstance(settings, dict)):
                raise ValueError(
                    f"PKC004 {path} shell {shell_name!r} feature {identity!r} must be an object or false"
                )
    return value


def merge_value(baseline: object, overlay: object) -> object:
    if not isinstance(baseline, dict) or not isinstance(overlay, dict):
        return deepcopy(overlay)
    result = deepcopy(baseline)
    for key, value in overlay.items():
        result[key] = merge_value(result[key], value) if key in result else deepcopy(value)
    return result


def compose(repository: Path) -> dict:
    repository = repository.resolve()
    profile = load(repository / PROFILE_SHELLS, required=False)
    consumer = load(repository / CONSUMER_SHELLS, required=True)
    effective = merge_value(profile, consumer)
    assert isinstance(effective, dict)
    # Validate the merged shape too. Consumer values intentionally override managed profile values,
    # including an explicit false used to deactivate an optional Program Kit feature.
    shells = effective.get("CShells", {}).get("Shells")
    if not isinstance(shells, dict) or not shells:
        raise ValueError("PKC005 effective shell composition contains no named shells")
    return effective


def write(repository: Path, output: Path) -> Path:
    value = compose(repository)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(value, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output


def activated_features(repository: Path) -> dict[str, set[str]]:
    shells = compose(repository)["CShells"]["Shells"]
    return {
        shell_name: {
            identity for identity, settings in shell["Features"].items() if settings is not False
        }
        for shell_name, shell in shells.items()
    }
