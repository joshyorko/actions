"""Bind refreshed test inputs separately from the immutable native artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

NATIVE_CANDIDATE_SHA = "a47dc616069afdb0488aaed651abf0ceb9a82035"
NATIVE_CANDIDATE_TREE = "10e4b5fb3a3ee3d7c6b7c8ccbf5f6bfcdde70bc6"
HARNESS_RUNTIME_TREE = "2aed50eae66abc2c85635a36c45a734429cfe905"
STAGING_PATH = "action_server/src/actions/server/deployments/source_staging.py"
STAGING_BLOB = "b475fd6688b7afc6606cde2cba9a1294d771a64c"
RESOURCE_TEST_PATH = (
    "action_server/tests/action_server_tests/test_cli_mcp_resource_history.py"
)
RESOURCE_TEST_BLOB = "5fe18b942ba66f339ac076fa26add1908d70305e"
INPUT_PATHS = (
    "action_server/src",
    "actions/src",
    "actions-http-helper/src",
    "action_server/pyproject.toml",
    "action_server/poetry.lock",
    "actions/pyproject.toml",
    "actions/poetry.lock",
    "actions-http-helper/pyproject.toml",
    "actions-http-helper/poetry.lock",
)
TEST_PATHS = tuple(
    "action_server/tests/action_server_tests/" + name
    for name in (
        "test_cli_mcp_catalog_rollback.py",
        "test_cli_live_reload_multi_package.py",
        "test_cli_successful_generation_drain.py",
        "test_cli_multi_package_sync.py",
        "test_cli_mcp_resource_history.py",
    )
)
GitEntries = dict[str, tuple[str, str, str]]


def _git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])


def _entries(root: Path, revision: str, paths: tuple[str, ...]) -> GitEntries:
    entries = {}
    for record in _git(root, "ls-tree", "-r", "-z", revision, "--", *paths).split(
        b"\0"
    ):
        if record:
            metadata, path = record.split(b"\t", 1)
            mode, kind, digest = metadata.decode("ascii").split()
            entries[path.decode("utf-8")] = (mode, kind, digest)
    return entries


def _validate_inputs(actual: GitEntries, native: GitEntries) -> None:
    expected = dict(native)
    if STAGING_PATH in expected:
        raise ValueError("native candidate unexpectedly contains the staging addition")
    expected[STAGING_PATH] = ("100644", "blob", STAGING_BLOB)
    if actual != expected:
        raise ValueError(
            "harness inputs differ from the native candidate plus exact staging blob"
        )


def _validate_tests(actual: GitEntries, native: GitEntries) -> None:
    expected = dict(native)
    if set(expected) != set(TEST_PATHS):
        raise ValueError("native candidate does not contain the exact five test files")
    expected[RESOURCE_TEST_PATH] = ("100644", "blob", RESOURCE_TEST_BLOB)
    if actual != expected:
        raise ValueError(
            "harness test selector blobs differ from the verified five-file set"
        )


def verify(root: Path) -> dict[str, object]:
    candidate_tree = (
        _git(root, "rev-parse", NATIVE_CANDIDATE_SHA + "^{tree}").decode().strip()
    )
    if candidate_tree != NATIVE_CANDIDATE_TREE:
        raise ValueError("native candidate tree differs from the immutable pin")
    runtime_tree = (
        _git(root, "rev-parse", "HEAD:action_server/src/actions/server")
        .decode()
        .strip()
    )
    if runtime_tree != HARNESS_RUNTIME_TREE:
        raise ValueError("refreshed harness Runtime subtree differs from its exact pin")
    _validate_inputs(
        _entries(root, "HEAD", INPUT_PATHS),
        _entries(root, NATIVE_CANDIDATE_SHA, INPUT_PATHS),
    )
    _validate_tests(
        _entries(root, "HEAD", TEST_PATHS),
        _entries(root, NATIVE_CANDIDATE_SHA, TEST_PATHS),
    )
    _git(root, "diff", "--exit-code", "HEAD", "--", *INPUT_PATHS, *TEST_PATHS)
    return {
        "control_sha": _git(root, "rev-parse", "HEAD").decode().strip(),
        "control_tree": _git(root, "rev-parse", "HEAD^{tree}").decode().strip(),
        "harness_runtime_source_tree": runtime_tree,
        "harness_runtime_reference_sha": NATIVE_CANDIDATE_SHA,
        "harness_runtime_source_differences": [
            {"path": STAGING_PATH, "mode": "100644", "blob": STAGING_BLOB}
        ],
        "resource_history_test_blob": RESOURCE_TEST_BLOB,
        "other_selected_test_blobs_match_native_candidate": True,
        "native_candidate_sha": NATIVE_CANDIDATE_SHA,
        "native_candidate_tree": candidate_tree,
        "harness_runtime_equals_native_source": False,
        "status": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = verify(args.source_root.resolve(strict=True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
