"""Exact historical mappings only; no restoration or fabricated raw bytes."""
import hashlib
import json
import os
import stat
from pathlib import Path

from historical_binding_v1 import verify_missing_original as verify_original_failed_receipt
from runner_contracts_v3 import need

TMP_MAPPING = {
    "path": "/workspace/engineering/root-B28-one-exact-TMP-relocation-owned/exact-original-path-to-new-physical-archive.json",
    "bytes": 1466,
    "sha256": "ce1450945a28a00611dff941ddcb0c414f281b7f32bbe004eb200435baa04f7f",
    "mode": "0o600",
}
TMP_ORIGINAL = {
    "path": "/tmp/actions-completed-scratch-recovery-batch3/dd09121ba364f685.tar.gz",
    "bytes": 248921681,
    "sha256": "28e391747a904f4162e01a0b95ea67ea43bc4db8159f21345af65889ab4680b5",
    "mode": "0o600",
}


def stream_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(row):
    path = Path(row["path"])
    meta = path.lstat()
    need(stat.S_ISREG(meta.st_mode) and not path.is_symlink(), "HISTORICAL_ALIAS_REGULAR")
    need(meta.st_size == row["bytes"] and stream_sha(path) == row["sha256"], "HISTORICAL_ALIAS_BODY")
    need(stat.S_IMODE(meta.st_mode) == int(str(row["mode"]), 8), "HISTORICAL_ALIAS_MODE")
    return meta


def verify_missing_original(row):
    if row.get("path") != TMP_ORIGINAL["path"]:
        return verify_original_failed_receipt(row)
    need(type(row) is dict and json.dumps(row, sort_keys=True) == json.dumps(TMP_ORIGINAL, sort_keys=True), "UNAPPROVED_TMP_ARCHIVE_ALIAS")
    need(not Path(row["path"]).exists() and not Path(row["path"]).is_symlink(), "OLD_TMP_ARCHIVE_MUST_REMAIN_ABSENT")
    check(TMP_MAPPING)
    mapping = json.loads(Path(TMP_MAPPING["path"]).read_text())
    need(mapping["schema"] == "EXACT_ONE_HISTORICAL_COMPRESSED_ARCHIVE_PHYSICAL_ALIAS"
         and mapping["original_index_unchanged"] is True
         and mapping["failed_history"] == "UNCHANGED_NO_ACCEPTANCE_UPGRADE", "TMP_ALIAS_HISTORY")
    old, physical = mapping["original"], mapping["new_physical"]
    need(old["path"] == TMP_ORIGINAL["path"]
         and old["bytes"] == physical["bytes"] == TMP_ORIGINAL["bytes"]
         and old["sha256"] == physical["sha256"] == TMP_ORIGINAL["sha256"]
         and old["mode"] == physical["mode"] == 0o600, "TMP_ALIAS_ORIGINAL_TUPLE")
    for key in ("uid", "gid", "mtime_ns"):
        need(old[key] == physical[key], "TMP_ALIAS_ORIGINAL_METADATA")
    meta = check(dict(physical, mode=oct(physical["mode"])))
    need(meta.st_uid == physical["uid"] == os.getuid()
         and meta.st_gid == physical["gid"] == os.getgid()
         and meta.st_mtime_ns == physical["mtime_ns"], "TMP_ALIAS_PHYSICAL_METADATA")
    check(mapping["original_index_binding"])
    return {"status": "EXACT_HISTORICAL_COMPRESSED_ARCHIVE_PHYSICAL_ALIAS_VERIFIED",
            "original": dict(TMP_ORIGINAL), "physical": physical,
            "failed_history": "UNCHANGED_NO_ACCEPTANCE_UPGRADE",
            "raw_body_returned": False}
