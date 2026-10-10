"""Validate and extract the measured Linux Go-wrapper executable."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path

EXPECTED_CANDIDATE = "a47dc616069afdb0488aaed651abf0ceb9a82035"
EXPECTED_CANDIDATE_TREE = "10e4b5fb3a3ee3d7c6b7c8ccbf5f6bfcdde70bc6"
EXPECTED_BUILD_SOURCE = "0045d91b2b5010b4b3706f777325e04b8eda805d"
EXPECTED_RUN_ID = "38060994147"
EXPECTED_RUN_ATTEMPT = "1"
EXPECTED_ARTIFACT_ID = "11673147409"
EXPECTED_ARCHIVE_SIZE = 77810317
EXPECTED_ARCHIVE_SHA256 = (
    "5caa374143633ed8faeb27fbd9aa6daf20b704e46599434af373685d02026764"
)
EXPECTED_BINARY_PATH = "action-server"
EXPECTED_BINARY_SIZE = 82014050
EXPECTED_BINARY_COMPRESSED_SIZE = 77810177
EXPECTED_BINARY_MODE = 0o755
EXPECTED_BINARY_SHA256 = (
    "26307ec2df6dee352048d4326dd246ffaa2cbcfa0f1e8bfbb35af86f34d9f07e"
)
EXPECTED_FROZEN_BINARY_SHA256 = (
    "b4bfb975bc8b54cb6fc5408f3ea88e2a65bcb06324ffa72826d29a19d59f95a8"
)
EXPECTED_WRAPPER_SOURCE_SHA256 = (
    "dd0260b11a3fadf019058e55eb43fe96a2b85088793e1210c1d44835e343d293"
)
WRAPPER_SOURCE_FILES = (
    "go-wrapper/main.go",
    "go-wrapper/process.go",
    "go-wrapper/go.mod",
    "go-wrapper/go.sum",
)
EXPECTED_MEASUREMENT_RECEIPT_SHA256 = (
    "e05e37a1f3194c518dd9ea22e19d4e01cfce15f991feaaf00a655b167c840910"
)
EXPECTED_NATIVE_MEASUREMENT_RECEIPT_SHA256 = (
    "dc7725c13c273fbca186539f18b43bc2d3701f9e2704dc9b8b596de3112aa951"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wrapper_source_sha256(action_server_root: Path) -> str:
    digest = hashlib.sha256()
    for relative_path in WRAPPER_SOURCE_FILES:
        path = action_server_root / relative_path
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256(path)))
    return digest.hexdigest()


def verify(
    archive_path: Path, destination: Path, output: Path, source_root: Path
) -> Path:
    if destination.exists():
        raise ValueError("wrapper extraction destination already exists")
    source_sha256 = _wrapper_source_sha256(source_root)
    if source_sha256 != EXPECTED_WRAPPER_SOURCE_SHA256:
        raise ValueError("Go-wrapper source digest does not match measured artifact")
    if (
        archive_path.stat().st_size != EXPECTED_ARCHIVE_SIZE
        or _sha256(archive_path) != EXPECTED_ARCHIVE_SHA256
    ):
        raise ValueError("Go-wrapper archive size or digest does not match candidate")

    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            if len(members) != 1:
                raise ValueError("Go-wrapper archive must contain exactly one member")
            member = members[0]
            unix_mode = member.external_attr >> 16
            if (
                member.filename != EXPECTED_BINARY_PATH
                or member.is_dir()
                or member.create_system != 3
                or stat.S_IFMT(unix_mode) != stat.S_IFREG
                or stat.S_IMODE(unix_mode) != EXPECTED_BINARY_MODE
                or member.file_size != EXPECTED_BINARY_SIZE
                or member.compress_size != EXPECTED_BINARY_COMPRESSED_SIZE
                or member.flag_bits & 0x1
            ):
                raise ValueError("Go-wrapper archive member identity is invalid")

            destination.mkdir(parents=True, exist_ok=False)
            target = destination / EXPECTED_BINARY_PATH
            digest = hashlib.sha256()
            byte_count = 0
            temporary_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=destination, prefix=".wrapper-", delete=False
                ) as extracted:
                    temporary_path = Path(extracted.name)
                    with archive.open(member) as source:
                        for chunk in iter(lambda: source.read(1024 * 1024), b""):
                            extracted.write(chunk)
                            digest.update(chunk)
                            byte_count += len(chunk)
                if (
                    byte_count != EXPECTED_BINARY_SIZE
                    or digest.hexdigest() != EXPECTED_BINARY_SHA256
                ):
                    raise ValueError(
                        "Go-wrapper executable bytes do not match candidate"
                    )
                os.chmod(temporary_path, EXPECTED_BINARY_MODE)
                os.replace(temporary_path, target)
                temporary_path = None
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)
    except zipfile.BadZipFile as error:
        raise ValueError("Go-wrapper archive is corrupt") from error

    record = {
        "candidate_sha": EXPECTED_CANDIDATE,
        "candidate_tree": EXPECTED_CANDIDATE_TREE,
        "native_build_source_sha": EXPECTED_BUILD_SOURCE,
        "workflow_run_id": EXPECTED_RUN_ID,
        "workflow_run_attempt": EXPECTED_RUN_ATTEMPT,
        "wrapper_artifact_id": EXPECTED_ARTIFACT_ID,
        "wrapper_archive_size": EXPECTED_ARCHIVE_SIZE,
        "wrapper_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "wrapper_source_sha256": EXPECTED_WRAPPER_SOURCE_SHA256,
        "wrapper_source_sha256_checked": source_sha256,
        "wrapper_measurement_receipt_sha256": EXPECTED_MEASUREMENT_RECEIPT_SHA256,
        "native_measurement_receipt_sha256": EXPECTED_NATIVE_MEASUREMENT_RECEIPT_SHA256,
        "member_path": EXPECTED_BINARY_PATH,
        "member_mode": EXPECTED_BINARY_MODE,
        "member_size": EXPECTED_BINARY_SIZE,
        "binary_sha256": EXPECTED_BINARY_SHA256,
        "frozen_binary_sha256": EXPECTED_FROZEN_BINARY_SHA256,
        "archive_and_member_verified": True,
        "binary_path": str(target.resolve()),
    }
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with Path(github_output).open("a", encoding="utf-8") as stream:
            stream.write(f"binary={target.resolve()}\n")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    binary = verify(args.archive, args.destination, args.output, args.source_root)
    print(f"Verified measured Go-wrapper executable: {binary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
