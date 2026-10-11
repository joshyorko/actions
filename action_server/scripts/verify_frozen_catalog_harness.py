"""Bind the exact current-source harness to the immutable native artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

NATIVE_CANDIDATE_SHA = "ba85aac7324ea4463bfba8c5f8586e27706dc2fe"
NATIVE_CANDIDATE_TREE = "80e5c77513f6abf5d07005ee3aee47d49efd927f"
HARNESS_RUNTIME_TREE = "20dca119289b1d6e40bd1065fd06b0d82aad3098"
RESOURCE_TEST_PATH = (
    "action_server/tests/action_server_tests/test_cli_mcp_resource_history.py"
)
RESOURCE_TEST_BLOB = "534e51afbc75b4d3ce473dee37d7ac00d52dbc92"
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
    if actual != native:
        raise ValueError("harness inputs differ from the exact native candidate")


def _validate_tests(actual: GitEntries, native: GitEntries) -> None:
    if set(native) != set(TEST_PATHS):
        raise ValueError("native candidate does not contain the exact five test files")
    if actual != native:
        raise ValueError("harness test selector blobs differ from the native candidate")


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
        "harness_runtime_source_differences": [],
        "resource_history_test_blob": RESOURCE_TEST_BLOB,
        "all_selected_test_blobs_match_native_candidate": True,
        "native_candidate_sha": NATIVE_CANDIDATE_SHA,
        "native_candidate_tree": candidate_tree,
        "harness_runtime_equals_native_source": True,
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
