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

EXPECTED_BUILD_SOURCE = "bf4f7dd180e3e408acff41fdb093b57eee8cc0f4"
EXPECTED_BUILD_TREE = "6cb691b44666347f3e0de68c9830bd6824a4a0a0"
EXPECTED_CANDIDATE = "f7c6ed61f24fd9e98d1465c83042c5446466311b"
EXPECTED_RUN = "38032640853"
EXPECTED_RUN_ATTEMPT = "1"
EXPECTED_TREE = "88c290b0e8377d6ae6a25ccf654b123a04774bd1d093dcc726cac4932b0621f0"
EXPECTED_BINARY = "ea4eadf5c05608a1b0ec8d17b63f94773b070e18dcc7466166b4bb68bd660342"
EXPECTED_WRAPPER = "373fe78e94fe28a43c5891fe22131a798501ed57640e24f90f2336efb1d4b6c0"
EXPECTED_MANIFEST = "498faf30d759e9ac24d334200f6b5d0448184c7ff2774f13a3e73f6a4081e279"
EXPECTED_INVENTORY = "d7a2de80761ad42cd84c90d0da2be0dedd8af621979a3954ace2749338b8d5a4"


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
        "candidate_tree": "6cb691b44666347f3e0de68c9830bd6824a4a0a0",
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
