from __future__ import annotations

import importlib.util
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def install_loopback_http_only_opener() -> None:
    original_http_handler = urllib.request.HTTPHandler

    class LoopbackHTTPHandler(original_http_handler):
        def http_open(self, request):
            hostname = urllib.parse.urlsplit(request.full_url).hostname
            if hostname not in {"127.0.0.1", "::1", "localhost"}:
                raise urllib.error.URLError(
                    "Program Kit loopback setup rejected non-loopback HTTP"
                )
            return super().http_open(request)

    class DisabledHTTPSHandler(urllib.request.BaseHandler):
        def https_open(self, request):
            raise urllib.error.URLError(
                "Program Kit loopback setup disables HTTPS in this process"
            )

    urllib.request.HTTPHandler = LoopbackHTTPHandler
    urllib.request.HTTPSHandler = DisabledHTTPSHandler
    urllib.request.install_opener(urllib.request.build_opener())


def main() -> int:
    if len(sys.argv) < 5 or sys.argv[1] != "--site-packages":
        print(
            "Program Kit Specify bridge requires --site-packages <absolute-directory> "
            "[--loopback-http-only] -- <arguments>.",
            file=sys.stderr,
        )
        return 2
    argument_index = 3
    loopback_http_only = False
    if sys.argv[argument_index] == "--loopback-http-only":
        loopback_http_only = True
        argument_index += 1
    if argument_index >= len(sys.argv) or sys.argv[argument_index] != "--":
        print(
            "Program Kit Specify bridge requires --site-packages <absolute-directory> "
            "[--loopback-http-only] -- <arguments>.",
            file=sys.stderr,
        )
        return 2
    site_packages = Path(sys.argv[2])
    if not site_packages.is_absolute() or not site_packages.is_dir():
        print(f"Program Kit Specify bridge rejected site-packages: {site_packages}", file=sys.stderr)
        return 2
    site_packages = site_packages.resolve()
    sys.path.insert(0, str(site_packages))
    if loopback_http_only:
        install_loopback_http_only_opener()
    specification = importlib.util.find_spec("specify_cli")
    origin = Path(specification.origin).resolve() if specification and specification.origin else None
    if origin is None or not inside(site_packages, origin):
        print(
            f"Program Kit Specify bridge did not resolve specify_cli inside {site_packages}.",
            file=sys.stderr,
        )
        return 2
    from specify_cli import main as specify_main

    sys.argv = ["specify", *sys.argv[argument_index + 1 :]]
    result = specify_main()
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
