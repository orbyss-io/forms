from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://api.nuget.org/v3/index.json"
CONFIRMATION = "unlist-forms-0.1.0-superseded"
SUPERSEDED_VERSION = "0.1.0"
SUPERSEDED = (
    "Orbyss.Forms.Application",
    "Orbyss.Forms.Core",
    "Orbyss.Forms.Mcp.AspNetCore",
    "Orbyss.Forms.Tool",
)
REPLACEMENTS = (
    "Orbyss.Forms.Abstractions",
    "Orbyss.Forms.JsonForms",
    "Orbyss.Forms.Localization",
    "Orbyss.Forms.Management",
    "Orbyss.Forms.Management.Mcp.AspNetCore",
    "Orbyss.Forms.Management.Tool",
    "Orbyss.Forms.Storage.Abstractions",
    "Orbyss.Forms.Storage.FileSystem",
    "Orbyss.Forms.Storage.InMemory",
    "Orbyss.Forms.Submissions",
    "Orbyss.Forms.Submissions.Mcp.AspNetCore",
    "Orbyss.Forms.Submissions.Tool",
    "Orbyss.Forms.Web.Management",
    "Orbyss.Forms.Web.Runtime",
    "Orbyss.Forms.Web.Submissions",
)


def available(package_id: str, version: str) -> bool:
    lower_id = package_id.lower()
    lower_version = version.lower()
    request = urllib.request.Request(
        f"https://api.nuget.org/v3-flatcontainer/{lower_id}/{lower_version}/{lower_id}.{lower_version}.nupkg",
        method="HEAD",
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status == 200
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise


def verify_replacements(version: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    pending = list(REPLACEMENTS)
    while pending:
        pending = [package_id for package_id in pending if not available(package_id, version)]
        if not pending:
            return
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "PKR002 replacement propagation timed out for: " + ", ".join(pending)
            )
        print("waiting for replacement packages: " + ", ".join(pending))
        time.sleep(15)


def listed(package_id: str, version: str) -> bool:
    request = urllib.request.Request(
        f"https://api.nuget.org/v3/registration5-semver1/{package_id.lower()}/index.json",
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        registration = json.load(response)
    for page in registration.get("items", []):
        items = page.get("items")
        if items is None:
            with urllib.request.urlopen(page["@id"], timeout=30) as response:
                items = json.load(response).get("items", [])
        for item in items:
            catalog = item.get("catalogEntry", {})
            if str(catalog.get("version", "")).lower() == version.lower():
                return catalog.get("listed", True) is not False
    raise ValueError(f"PKR005 package version was not found in registration: {package_id} {version}")


def verify_unlisted(timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    pending = list(SUPERSEDED)
    while pending:
        pending = [package_id for package_id in pending if listed(package_id, SUPERSEDED_VERSION)]
        if not pending:
            return
        if time.monotonic() >= deadline:
            raise TimeoutError("PKR006 unlisting propagation timed out for: " + ", ".join(pending))
        print("waiting for NuGet.org unlisting propagation: " + ", ".join(pending))
        time.sleep(15)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Locally retire only the four superseded Orbyss Forms 0.1.0 package identities."
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirmation")
    parser.add_argument("--verify-public", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()

    replacement_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if replacement_version == SUPERSEDED_VERSION:
        raise ValueError("PKR001 replacement version must be newer than the superseded version")
    if args.verify_public:
        verify_replacements(replacement_version, args.timeout_seconds)
        print(f"All {len(REPLACEMENTS)} replacement packages are public at {replacement_version}.")

    if not args.execute:
        print("Dry run; would unlist: " + ", ".join(f"{item} {SUPERSEDED_VERSION}" for item in SUPERSEDED))
        return 0
    if args.confirmation != CONFIRMATION:
        raise ValueError(f"PKR003 confirmation must equal {CONFIRMATION!r}")
    api_key = os.environ.get("NUGET_API_KEY")
    if not api_key:
        raise ValueError("PKR004 NUGET_API_KEY is required for execution")
    for package_id in SUPERSEDED:
        subprocess.run(
            [
                "dotnet",
                "nuget",
                "delete",
                package_id,
                SUPERSEDED_VERSION,
                "--source",
                SOURCE,
                "--api-key",
                api_key,
                "--non-interactive",
            ],
            check=True,
        )
    verify_unlisted(args.timeout_seconds)
    print("Unlisted exactly four superseded Orbyss Forms 0.1.0 packages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
