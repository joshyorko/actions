"""Exact historical mappings only; no restoration or fabricated raw bytes."""
import hashlib
import json
import os
import stat
import subprocess
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
HISTORICAL_FIXTURE = {
    "path": "/workspace/engineering/pr308/action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py",
    "bytes": 48314,
    "sha256": "af2f79ccd395c088076381f6681860cf8160f8fd0d9169e122634fe684c37c35",
    "mode": "0o600",
}
HISTORICAL_FIXTURE_CONFIG = {
    "path": "/workspace/engineering/rcc-compatibility-current-e4ff-qualified-config-successor/FROZEN-current-e4ff-control3-owned-cache-SOURCE-QUALIFIED-v4.json",
    "bytes": 797131,
    "sha256": "1411879501e1ef2bd5aec7fbf9627457aa840badc8e86be980c25b207ee9d5dc",
    "mode": "0o600",
}
HISTORICAL_FIXTURE_SOURCE = "e4ff080375a8422bb656e52d218f198521dda078"
HISTORICAL_FIXTURE_TREE = "973ff38f49a17a896e4d90f829a72e2ea0ea15e8"
HISTORICAL_FIXTURE_GIT_PATH = "action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py"
HISTORICAL_FIXTURE_SNAPSHOT = {
    "path": str(Path(__file__).resolve().parent / "historical-e4ff-staged-fixture-exact-Git-blob.snapshot.py"),
    "bytes": 48314,
    "sha256": "af2f79ccd395c088076381f6681860cf8160f8fd0d9169e122634fe684c37c35",
    "mode": "0o400",
}


def matches_historical_fixture(row):
    return type(row) is dict and json.dumps(row, sort_keys=True) == json.dumps(HISTORICAL_FIXTURE, sort_keys=True)


def verify_historical_fixture(row):
    need(matches_historical_fixture(row), "UNAPPROVED_HISTORICAL_FIXTURE")
    check(HISTORICAL_FIXTURE_CONFIG)
    old = json.loads(Path(HISTORICAL_FIXTURE_CONFIG["path"]).read_text())
    need(old["source"] == HISTORICAL_FIXTURE_SOURCE and old["tree"] == HISTORICAL_FIXTURE_TREE,
         "HISTORICAL_FIXTURE_SOURCE")
    originals = [entry for entry in old["bindings"] if entry["path"] == HISTORICAL_FIXTURE["path"]]
    need(len(originals) == 1 and originals[0] == HISTORICAL_FIXTURE, "HISTORICAL_FIXTURE_ORIGINAL_ROW")
    check(HISTORICAL_FIXTURE_SNAPSHOT)
    repository = str(Path(HISTORICAL_FIXTURE["path"]).parents[3])
    tree = subprocess.check_output(["git", "-C", repository, "rev-parse", HISTORICAL_FIXTURE_SOURCE + "^{tree}"], text=True).strip()
    need(tree == HISTORICAL_FIXTURE_TREE, "HISTORICAL_FIXTURE_GIT_TREE")
    git_row = subprocess.check_output(["git", "-C", repository, "ls-tree", HISTORICAL_FIXTURE_SOURCE, "--", HISTORICAL_FIXTURE_GIT_PATH], text=True).strip()
    need(git_row.startswith("100644 blob ") and git_row.split("\t", 1)[1] == HISTORICAL_FIXTURE_GIT_PATH,
         "HISTORICAL_FIXTURE_GIT_MODE_PATH")
    raw = subprocess.check_output(["git", "-C", repository, "show", HISTORICAL_FIXTURE_SOURCE + ":" + HISTORICAL_FIXTURE_GIT_PATH])
    need(len(raw) == HISTORICAL_FIXTURE["bytes"] and hashlib.sha256(raw).hexdigest() == HISTORICAL_FIXTURE["sha256"],
         "HISTORICAL_FIXTURE_GIT_BODY")
    return {"status": "EXACT_HISTORICAL_FIXTURE_GIT_SNAPSHOT_VERIFIED",
            "original": dict(HISTORICAL_FIXTURE), "source": HISTORICAL_FIXTURE_SOURCE,
            "tree": HISTORICAL_FIXTURE_TREE, "snapshot": dict(HISTORICAL_FIXTURE_SNAPSHOT),
            "physical_mode_scope": "Original0600 retained in original binding; current snapshot0400 separately measured",
            "current_live_fixture": "SEPARATE_BINDING_REQUIRED", "raw_body_returned": False}


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
