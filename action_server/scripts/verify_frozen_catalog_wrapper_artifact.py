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

EXPECTED_CANDIDATE = "ba85aac7324ea4463bfba8c5f8586e27706dc2fe"
EXPECTED_CANDIDATE_TREE = "80e5c77513f6abf5d07005ee3aee47d49efd927f"
EXPECTED_BUILD_SOURCE = "92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e"
EXPECTED_RUN_ID = "38098225250"
EXPECTED_RUN_ATTEMPT = "1"
EXPECTED_ARTIFACT_ID = "11686533628"
EXPECTED_ARCHIVE_SIZE = 77830730
EXPECTED_ARCHIVE_SHA256 = (
    "8386960d869d5a2be69ccf22a43064cb62550062e00aab200a70e06ab1547f7a"
)
EXPECTED_BINARY_PATH = "action-server"
EXPECTED_BINARY_SIZE = 82030442
EXPECTED_BINARY_COMPRESSED_SIZE = 77830590
EXPECTED_BINARY_MODE = 0o755
EXPECTED_BINARY_SHA256 = (
    "214548879a4eb74ccd94998dcd6250b712b2bdfe7a07ab803e2e2e37f679c04b"
)
EXPECTED_FROZEN_BINARY_SHA256 = (
    "067a27c24b55690410beeb1b95e97fb098edf8e02779b36b69bbead2227433fb"
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
    "07b6799026a26ec985d0cf7835b3fddd2105304c09d4102ed69c51f9d5c8c2ff"
)
EXPECTED_NATIVE_MEASUREMENT_RECEIPT_SHA256 = (
    "07b6799026a26ec985d0cf7835b3fddd2105304c09d4102ed69c51f9d5c8c2ff"
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
