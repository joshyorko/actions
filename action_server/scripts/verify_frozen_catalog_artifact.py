"""Verify the measured Linux frozen artifact used by catalog acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tarfile
from pathlib import Path, PurePosixPath

from archive_native_artifact_provenance import (
    INVENTORY_ARCHIVE_PATH,
    MANIFEST_ARCHIVE_PATH,
    TREE_ARCHIVE_PATH,
    _measure,
    _verify_tar,
)

EXPECTED_BUILD_SOURCE = "92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e"
EXPECTED_BUILD_TREE = "80e5c77513f6abf5d07005ee3aee47d49efd927f"
EXPECTED_CANDIDATE = "ba85aac7324ea4463bfba8c5f8586e27706dc2fe"
EXPECTED_CANDIDATE_TREE = "80e5c77513f6abf5d07005ee3aee47d49efd927f"
EXPECTED_RUN = "38098225250"
EXPECTED_RUN_ATTEMPT = "1"
EXPECTED_ARTIFACT_ID = "11686643166"
EXPECTED_ARCHIVE_SIZE = 59410740
EXPECTED_ARCHIVE_SHA256 = "0905c4734d6b636a5a465e0a958cf8bc4521b5047a68da473830b95821b7c8c0"
EXPECTED_MEASUREMENT_RECEIPT = "07b6799026a26ec985d0cf7835b3fddd2105304c09d4102ed69c51f9d5c8c2ff"
EXPECTED_TREE = "739838962d9d29f873932e13d2598d51ebba58b0f97c2c52fff8550004f06ae0"
EXPECTED_BINARY = "067a27c24b55690410beeb1b95e97fb098edf8e02779b36b69bbead2227433fb"
EXPECTED_EMBEDDED_FILES = "576d6cb8e5a8637dcfd82f675384d638736509541a0e10877420151b61c4786b"
EXPECTED_MANIFEST = "70405e6e831066a37631c7a63045010fcbc8b3c928a6a22ff5130467c3ad9d44"
EXPECTED_INVENTORY = "154aeb29249db79a32392124a3b71a8ac325c0bdaeda1bbc2e7445e96ffc7fdf"
EXPECTED_INVENTORY_ENTRIES = 1192
RESOURCE_HISTORY_TEST_BLOB = "534e51afbc75b4d3ce473dee37d7ac00d52dbc92"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(provenance_tar: Path, destination: Path, output: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(provenance_tar, "r:") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)):
            raise ValueError("native provenance archive contains duplicate paths")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or any(
                part in {"", ".", ".."} for part in path.parts
            ):
                raise ValueError("native provenance archive contains an unsafe path")
        by_name = {member.name: member for member in members}
        manifest_stream = archive.extractfile(by_name[MANIFEST_ARCHIVE_PATH])
        inventory_stream = archive.extractfile(by_name[INVENTORY_ARCHIVE_PATH])
        if manifest_stream is None or inventory_stream is None:
            raise ValueError("native provenance metadata is missing")
        manifest_bytes = manifest_stream.read()
        inventory_bytes = inventory_stream.read()
        if (
            hashlib.sha256(manifest_bytes).hexdigest() != EXPECTED_MANIFEST
            or hashlib.sha256(inventory_bytes).hexdigest() != EXPECTED_INVENTORY
        ):
            raise ValueError("native provenance metadata hashes do not match candidate")
        inventory = json.loads(inventory_bytes)
        if (
            not isinstance(inventory, list)
            or len(inventory) != EXPECTED_INVENTORY_ENTRIES
        ):
            raise ValueError("native provenance inventory is invalid")
        archive.extractall(destination, filter="data")

    tree = destination / TREE_ARCHIVE_PATH
    manifest_path = destination / MANIFEST_ARCHIVE_PATH
    inventory_path = destination / INVENTORY_ARCHIVE_PATH
    # Python's data extraction filter intentionally normalizes directory modes.
    # Restore the hash-bound inventory modes before the canonical tree verifier.
    for entry in inventory:
        if entry.get("kind") == "file":
            target = tree.joinpath(*PurePosixPath(str(entry["path"])).parts)
            os.chmod(target, int(entry["mode"]))
    for entry in sorted(
        (item for item in inventory if item.get("kind") == "directory"),
        key=lambda item: len(PurePosixPath(str(item["path"])).parts),
        reverse=True,
    ):
        target = tree.joinpath(*PurePosixPath(str(entry["path"])).parts)
        os.chmod(target, int(entry["mode"]))
    manifest, entries, manifest_bytes, inventory_bytes = _measure(
        tree, manifest_path, inventory_path
    )
    _verify_tar(
        provenance_tar,
        tree,
        manifest_path,
        inventory_path,
        entries,
        manifest_bytes,
        inventory_bytes,
    )
    if (
        manifest.get("source_sha") != EXPECTED_BUILD_SOURCE
        or manifest.get("workflow_run_id") != EXPECTED_RUN
        or manifest.get("workflow_run_attempt") != EXPECTED_RUN_ATTEMPT
        or manifest.get("platform") != "Linux"
        or manifest.get("architecture") != "x86_64"
        or _sha256(manifest_path) != EXPECTED_MANIFEST
        or _sha256(inventory_path) != EXPECTED_INVENTORY
        or _sha256(tree / "action-server") != EXPECTED_BINARY
        or manifest["artifacts"]["frozen"].get("frozen_package_tree_sha256")
        != EXPECTED_TREE
        or manifest["artifacts"]["frozen"].get("embedded_files_sha256")
        != EXPECTED_EMBEDDED_FILES
    ):
        raise ValueError("frozen catalog artifact provenance does not match candidate")

    record = {
        "candidate_sha": EXPECTED_CANDIDATE,
        "candidate_tree": EXPECTED_CANDIDATE_TREE,
        "native_build_source_sha": EXPECTED_BUILD_SOURCE,
        "native_build_source_tree": EXPECTED_BUILD_TREE,
        "workflow_run_id": EXPECTED_RUN,
        "workflow_run_attempt": EXPECTED_RUN_ATTEMPT,
        "native_artifact_id": EXPECTED_ARTIFACT_ID,
        "native_artifact_size": EXPECTED_ARCHIVE_SIZE,
        "native_artifact_sha256": EXPECTED_ARCHIVE_SHA256,
        "native_artifact_archive_hash_checked": True,
        "native_byte_verification_receipt_sha256": EXPECTED_MEASUREMENT_RECEIPT,
        "resource_history_test_blob": RESOURCE_HISTORY_TEST_BLOB,
        "manifest_sha256": EXPECTED_MANIFEST,
        "inventory_sha256": EXPECTED_INVENTORY,
        "package_tree_sha256": manifest["artifacts"]["frozen"][
            "frozen_package_tree_sha256"
        ],
        "embedded_files_sha256": EXPECTED_EMBEDDED_FILES,
        "binary_sha256": EXPECTED_BINARY,
        "binary_path": str((tree / "action-server").resolve()),
    }
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with Path(github_output).open("a", encoding="utf-8") as stream:
            stream.write(f"binary={record['binary_path']}\n")
    return tree / "action-server"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provenance-tar", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    binary = verify(args.provenance_tar, args.destination, args.output)
    print(f"Verified immutable frozen candidate binary: {binary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
