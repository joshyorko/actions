"""Prepared package interpreter entry; plugin loading never alters sys.path."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import subprocess
import sys
import tomllib
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--progress", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args, pytest_args = parser.parse_known_args()
    if sys.flags.optimize:
        raise RuntimeError("Optimized Python is unsupported")
    import actions.server
    package = args.source.resolve() / "action_server"
    expected = tomllib.loads((package / "pyproject.toml").read_text())["tool"]["poetry"]["version"]
    actual_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.source, text=True, timeout=15).strip()
    dirty = bool(subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=args.source, timeout=15))
    origin = Path(actions.server.__file__).resolve()
    versions = {name: importlib.metadata.version(name) for name in
                ("actions-runtime", "actions-core", "actions-work-items", "pytest", "mcp")}
    source_files = [package / "pyproject.toml", *sorted((package / "src").rglob("*.py")),
                    *sorted((package / "tests").rglob("*.py"))]
    fingerprint = hashlib.sha256()
    for path in source_files:
        fingerprint.update(str(path.relative_to(package)).encode() + b"\0")
        fingerprint.update(hashlib.sha256(path.read_bytes()).digest())
    receipt = {"source_sha": actual_sha, "expected_source_sha": args.source_sha,
               "pyproject_version": expected, "module_version": actions.server.__version__,
               "versions": versions, "runtime_origin": str(origin), "python": sys.executable,
               "source_tests_fingerprint": fingerprint.hexdigest(),
               "worktree_clean": not dirty, "status": "FAILED"}
    valid = (not dirty and actual_sha == args.source_sha and origin.is_relative_to(package / "src")
             and versions["actions-runtime"] == expected == actions.server.__version__)
    receipt["status"] = "PASS" if valid else "FAILED"
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    if not valid:
        raise RuntimeError("Runtime source/origin/installed metadata preflight mismatch; see receipt")
    if args.preflight_only:
        return 0
    import pytest
    path = Path(__file__).with_name("progress_plugin.py")
    spec = importlib.util.spec_from_file_location("actions327_progress_plugin", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt["plugin_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    return int(pytest.main(pytest_args, plugins=[module.Progress(args.progress)]))


if __name__ == "__main__":
    raise SystemExit(main())
