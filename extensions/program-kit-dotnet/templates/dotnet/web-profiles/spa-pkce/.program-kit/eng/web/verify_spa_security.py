from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED = {
    "Content-Security-Policy",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "X-Content-Type-Options",
}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="WEB-V1 check for the Program Kit SPA serving adapter.")
    parser.add_argument("--contract", default=".program-kit/eng/web/spa-security.json")
    parser.add_argument("--vite-config", required=True)
    args = parser.parse_args()
    try:
        contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
        headers = contract.get("headers", {})
        missing = sorted(REQUIRED - set(headers))
        if missing:
            raise ValueError(f"PKW001 SPA security contract is missing headers: {', '.join(missing)}")
        csp = str(headers["Content-Security-Policy"])
        for directive in ("default-src 'self'", "frame-ancestors 'none'", "object-src 'none'", "connect-src"):
            if directive not in csp:
                raise ValueError(f"PKW002 CSP is missing required directive: {directive}")
        if "unsafe-inline" in csp or re.search(r"(?:^|\s)\*(?:\s|;|$)", csp):
            raise ValueError("PKW003 production CSP cannot contain unsafe-inline or wildcard sources.")
        if "Strict-Transport-Security" in headers:
            raise ValueError("PKW004 the local Vite adapter must not claim HSTS ownership.")
        vite = Path(args.vite_config).read_text(encoding="utf-8")
        if "programKitSpaSecurity" not in vite:
            raise ValueError(
                "PKW005 consumer-owned vite.config must import and register programKitSpaSecurity; "
                "do not reimplement the header policy in feature code."
            )
        print("WEB-V1 SPA serving-security configuration is valid")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
