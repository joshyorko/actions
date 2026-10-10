"""Verify the fixed Linux frozen artifact used by catalog rollback acceptance."""

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

EXPECTED_BUILD_SOURCE = "056d32601563a213643436e7df14e6ca0ea50516"
EXPECTED_BUILD_TREE = "d2ef7229651b6120db5cfa5995c65942ef768da8"
EXPECTED_CANDIDATE = "31239cf99c7b264a0eab89660e93b391532ac305"
EXPECTED_CANDIDATE_TREE = "d2ef7229651b6120db5cfa5995c65942ef768da8"
EXPECTED_RUN = "38039806634"
EXPECTED_RUN_ATTEMPT = "1"
EXPECTED_TREE = "ee7cdb5eae9a04042bc476034bb9ed327d51fa705cce70abf8426454fe3d6e6f"
EXPECTED_BINARY = "0509dfc3c193ba8ca0221603a9f2444091a558aabbb886a957e89a22cf073dc3"
EXPECTED_WRAPPER = "28cf80cb1d2811236ed64595b8b9d03a54d1904d63497eb39f34fb9bd67978f3"
EXPECTED_MANIFEST = "7b75b64d160fa73ca14728437a2cc07aebdccf58d450d83b9745245001a33538"
EXPECTED_INVENTORY = "4e61388ef1ae7f2348391b28a42cf63427fdefcd3fbdda2703d6844c4fe6afca"


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
        if not isinstance(inventory, list):
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
        or manifest["artifacts"]["go-wrapper"].get("sha256") != EXPECTED_WRAPPER
    ):
        raise ValueError("frozen catalog artifact provenance does not match candidate")

    record = {
        "candidate_sha": EXPECTED_CANDIDATE,
        "candidate_tree": EXPECTED_CANDIDATE_TREE,
        "native_build_source_sha": EXPECTED_BUILD_SOURCE,
        "native_build_source_tree": EXPECTED_BUILD_TREE,
        "workflow_run_id": EXPECTED_RUN,
        "workflow_run_attempt": EXPECTED_RUN_ATTEMPT,
        "manifest_sha256": EXPECTED_MANIFEST,
        "inventory_sha256": EXPECTED_INVENTORY,
        "package_tree_sha256": manifest["artifacts"]["frozen"][
            "frozen_package_tree_sha256"
        ],
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
