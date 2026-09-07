from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


IDENTITY = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


def configure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def values(raw: str) -> list[str]:
    return sorted({value.strip() for value in raw.split(";") if value.strip()}, key=str.casefold)


def emit(args: argparse.Namespace) -> int:
    if not IDENTITY.fullmatch(args.identity):
        raise ValueError(f"PKF001 invalid feature identity: {args.identity!r}")
    if not args.package_id.strip():
        raise ValueError("PKF002 package id is required.")
    routes = values(args.routes)
    invalid_route = next((route for route in routes if not route.startswith("/")), None)
    if invalid_route:
        raise ValueError(f"PKF003 route must be absolute: {invalid_route}")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "identity": args.identity,
                "packageId": args.package_id,
                "featureDependencies": values(args.feature_dependencies),
                "runtimeDependencies": values(args.runtime_dependencies),
                "routes": routes,
                "dormant": args.dormant.lower() == "true",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


def activate(args: argparse.Namespace) -> int:
    path = Path(args.shells)
    value = json.loads(path.read_text(encoding="utf-8"))
    try:
        shells = value["CShells"]["Shells"]
        shell = shells[args.shell]
        features = shell["Features"]
    except (KeyError, TypeError) as error:
        raise ValueError(
            f"PKF004 shells.json does not match the CShells:Shells:<name>:Features schema for shell '{args.shell}'."
        ) from error
    if not isinstance(features, dict):
        raise ValueError(f"PKF005 Features must be an object for shell '{args.shell}'.")
    if args.feature in features:
        raise ValueError(f"PKF006 feature '{args.feature}' is already activated in shell '{args.shell}'.")
    if not IDENTITY.fullmatch(args.feature):
        raise ValueError(f"PKF007 invalid feature identity: {args.feature!r}")
    features[args.feature] = {}
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"activated feature {args.feature} in shell {args.shell}")
    return 0


def main() -> int:
    configure_utf8()
    parser = argparse.ArgumentParser(description="Create Program Kit feature metadata or update CShells activation.")
    commands = parser.add_subparsers(dest="command", required=True)
    emit_parser = commands.add_parser("emit")
    emit_parser.add_argument("--output", required=True)
    emit_parser.add_argument("--identity", required=True)
    emit_parser.add_argument("--package-id", required=True)
    emit_parser.add_argument("--feature-dependencies", default="")
    emit_parser.add_argument("--runtime-dependencies", default="")
    emit_parser.add_argument("--routes", default="")
    emit_parser.add_argument("--dormant", choices=("true", "false"), default="false")
    activate_parser = commands.add_parser("activate")
    activate_parser.add_argument("--shells", default="shells.json")
    activate_parser.add_argument("--shell", required=True)
    activate_parser.add_argument("--feature", required=True)
    args = parser.parse_args()
    try:
        return emit(args) if args.command == "emit" else activate(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
