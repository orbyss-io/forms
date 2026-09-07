from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS_TOOLCHAIN = ROOT / "extensions/program-kit-dotnet/templates/dotnet/files/.program-kit/eng/js_toolchain.py"
NPM_GRAPH = ROOT / "extensions/program-kit-governance/scripts/npm_graph.py"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="program-kit-js-toolchain-") as value:
        repository = Path(value)
        managed = repository / ".program-kit/eng"
        managed.mkdir(parents=True)
        (managed / "js_toolchain.py").write_bytes(JS_TOOLCHAIN.read_bytes())
        exact = repository / "exact"
        wrong = repository / "wrong"
        exact.mkdir()
        wrong.mkdir()
        invocation_log = repository / "npm-invocations.txt"
        if os.name == "nt":
            node = exact / "node.cmd"
            npm = exact / "npm.cmd"
            wrong_node = wrong / "node.cmd"
            wrong_npm = wrong / "npm.cmd"
            node.write_text("@echo off\r\necho v24.20.0\r\n", encoding="utf-8")
            wrong_node.write_text("@echo off\r\necho v20.11.1\r\n", encoding="utf-8")
            wrong_npm.write_text("@echo off\r\necho wrong>\"%~dp0used.txt\"\r\n", encoding="utf-8")
            npm.write_text(
                "@echo off\r\n"
                "if \"%1\"==\"--version\" (echo 11.19.0& exit /b 0)\r\n"
                "if not \"%NPM_CONFIG_STRICT_SSL%\"==\"true\" exit /b 71\r\n"
                "echo %NODE_OPTIONS%| findstr /c:\"--use-system-ca\" >nul || exit /b 72\r\n"
                f"if not \"%NPM_CONFIG_CACHE%\"==\"{repository / '.program-kit/cache/npm'}\" exit /b 73\r\n"
                f"echo %*>\"{invocation_log}\"\r\n"
                "echo {}>package-lock.json\r\n"
                "exit /b 0\r\n",
                encoding="utf-8",
            )
        else:
            node = exact / "node"
            npm = exact / "npm"
            wrong_node = wrong / "node"
            wrong_npm = wrong / "npm"
            node.write_text("#!/bin/sh\nprintf 'v24.20.0\\n'\n", encoding="utf-8")
            wrong_node.write_text("#!/bin/sh\nprintf 'v20.11.1\\n'\n", encoding="utf-8")
            wrong_npm.write_text("#!/bin/sh\ntouch \"$(dirname \"$0\")/used.txt\"\n", encoding="utf-8")
            npm.write_text(
                "#!/bin/sh\n"
                "[ \"$1\" = --version ] && printf '11.19.0\\n' && exit 0\n"
                "[ \"$NPM_CONFIG_STRICT_SSL\" = true ] || exit 71\n"
                "case \" $NODE_OPTIONS \" in *' --use-system-ca '*) ;; *) exit 72;; esac\n"
                f"[ \"$NPM_CONFIG_CACHE\" = '{repository / '.program-kit/cache/npm'}' ] || exit 73\n"
                f"printf '%s\\n' \"$*\" > '{invocation_log}'\n"
                "printf '{}\\n' > package-lock.json\n"
                "exit 0\n",
                encoding="utf-8",
            )
            for path in (node, npm, wrong_node, wrong_npm):
                path.chmod(0o755)

        cache = repository / ".program-kit/cache/npm"
        evidence = repository / ".program-kit/evidence/toolchain.json"
        evidence.parent.mkdir(parents=True)
        evidence.write_text(
            json.dumps(
                {
                    "schemaVersion": 2,
                    "required": {"dotnet": "10.0.202", "node": "24.20.0", "npm": "11.19.0"},
                    "resolved": {"dotnet": "10.0.202", "node": "24.20.0", "npm": "11.19.0"},
                    "commands": {"dotnet": ["unused"], "node": [str(node.resolve())], "npm": [str(npm.resolve())]},
                    "environment": {
                        "npmCache": str(cache.resolve()),
                        "trustMode": "system",
                        "extraCaCertificates": "",
                        "strictSsl": True,
                    },
                    "satisfied": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["PATH"] = str(wrong) + os.pathsep + environment.get("PATH", "")
        environment["NPM_CONFIG_CACHE"] = str(repository / "unwritable-profile-cache")
        wrapper = subprocess.run(
            [
                sys.executable,
                str(managed / "js_toolchain.py"),
                "--repository",
                str(repository),
                "--evidence",
                str(evidence),
                "npm",
                "--",
                "test",
            ],
            cwd=repository,
            env=environment,
            capture_output=True,
            text=True,
        )
        if wrapper.returncode != 0 or (wrong / "used.txt").exists():
            raise AssertionError(f"exact npm wrapper did not isolate PATH/cache/system trust: {wrapper.stderr}")

        candidate = repository / "candidate-package.json"
        candidate.write_text(
            json.dumps({"name": "candidate", "version": "1.0.0", "dependencies": {"react": "19.2.4"}}),
            encoding="utf-8",
        )
        graph_evidence = repository / ".program-kit/evidence/npm-graph.json"
        graph = subprocess.run(
            [
                sys.executable,
                str(NPM_GRAPH),
                "--repository",
                str(repository),
                "--toolchain-evidence",
                str(evidence),
                "--package-json",
                str(candidate),
                "--evidence",
                str(graph_evidence),
            ],
            cwd=repository,
            env=environment,
            capture_output=True,
            text=True,
        )
        if graph.returncode != 0:
            raise AssertionError(f"strict npm graph did not use the pinned execution context: {graph.stdout}{graph.stderr}")
        invocation = invocation_log.read_text(encoding="utf-8")
        for required in ("--strict-ssl=true", "--strict-peer-deps", "--engine-strict"):
            if required not in invocation:
                raise AssertionError(f"strict npm graph omitted {required}: {invocation}")
        if json.loads(graph_evidence.read_text(encoding="utf-8"))["satisfied"] is not True:
            raise AssertionError("npm graph evidence was not satisfied")

    print("Exact Node/npm execution, repository cache, and system-CA trust validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
