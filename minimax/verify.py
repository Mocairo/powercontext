"""Run the submitted module tests in a credential-free process.

This is a recheck entry for reviewers. It deliberately does not import the
live-model workflow or read the operator's MiniMax configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    paths = []
    for directory in ("src", "tests", "demo"):
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    return {path.relative_to(ROOT).as_posix(): sha256(path) for path in sorted(paths)}


def main() -> int:
    parser = argparse.ArgumentParser(description="credential-free MiniMax module verification")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/module-recheck")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        print(f"Refusing to overwrite evidence directory: {output}", file=sys.stderr)
        return 2
    output.mkdir(parents=True)
    env = {key: value for key, value in os.environ.items() if not key.startswith("MINIMAX_")}
    env.update({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    command = [sys.executable, "-m", "pytest", "-q", "tests"]
    process = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False, timeout=180)
    (output / "tests.log").write_text(process.stdout + process.stderr, encoding="utf-8")
    match = re.search(r"(?P<count>\d+) passed", process.stdout + process.stderr)
    packages = {}
    for package in ("powercontext", "pylibseekdb", "PyMySQL", "httpx", "pytest"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    report = {
        "command": command,
        "cwd": str(ROOT),
        "exit_code": process.returncode,
        "tests_passed": int(match.group("count")) if match else 0,
        "source_sha256": source_hashes(),
        "dependencies": packages,
        "live_minimax_requests": 0,
        "official_score": None,
    }
    (output / "tests.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"exit_code": process.returncode, "tests_passed": report["tests_passed"], "output": str(output)}, ensure_ascii=False))
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
