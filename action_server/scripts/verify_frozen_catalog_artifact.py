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

EXPECTED_BUILD_SOURCE = "0045d91b2b5010b4b3706f777325e04b8eda805d"
EXPECTED_BUILD_TREE = "10e4b5fb3a3ee3d7c6b7c8ccbf5f6bfcdde70bc6"
EXPECTED_CANDIDATE = "a47dc616069afdb0488aaed651abf0ceb9a82035"
EXPECTED_CANDIDATE_TREE = "10e4b5fb3a3ee3d7c6b7c8ccbf5f6bfcdde70bc6"
EXPECTED_RUN = "38060994147"
EXPECTED_RUN_ATTEMPT = "1"
EXPECTED_ARTIFACT_ID = "11673805091"
EXPECTED_ARCHIVE_SIZE = 59391509
EXPECTED_ARCHIVE_SHA256 = "26a60e999d62009ea83d70aac949a3c3bbf09895ea90119a7a39b2a05306e2f8"
EXPECTED_MEASUREMENT_RECEIPT = "dc7725c13c273fbca186539f18b43bc2d3701f9e2704dc9b8b596de3112aa951"
EXPECTED_TREE = "f70b20cea354c33da89d4d52cb8d4f6e60c1401ef2992e75162265711df597bf"
EXPECTED_BINARY = "b4bfb975bc8b54cb6fc5408f3ea88e2a65bcb06324ffa72826d29a19d59f95a8"
EXPECTED_EMBEDDED_FILES = "b6f81872dc4aa8684209ce047fb7b47cd552f5e18153b2882df745dc63cc47aa"
EXPECTED_MANIFEST = "07aff6e9a0415397a9758163401a3342b0f066a7e6cd87a7f294dcc73f656b81"
EXPECTED_INVENTORY = "db3864c883dda15ba56de3b3009f9d15cf2fdad971cfefedb7523897936d6dac"
EXPECTED_INVENTORY_ENTRIES = 1191
RESOURCE_HISTORY_TEST_BLOB = "69e2a468916f9982206573e8f5b71c6f2db8c8e7"


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
