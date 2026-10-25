import shutil
import sqlite3
from pathlib import Path

import pytest

from actions.server._datadir_restore import capture_offline_manifest, restore_offline


def snapshot(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    attachment = source / "work_item_files" / "item-1" / "report.txt"
    attachment.parent.mkdir(parents=True)
    attachment.write_bytes(b"retained report")
    with sqlite3.connect(source / "workitems.db") as db:
        db.execute("CREATE TABLE work_items (id TEXT PRIMARY KEY)")
        db.execute("INSERT INTO work_items VALUES ('item-1')")
        db.execute(
            "CREATE TABLE work_item_files (id TEXT PRIMARY KEY, work_item_id TEXT, "
            "name TEXT, original_name TEXT, file_path TEXT, created_at TEXT)"
        )
        db.execute(
            "INSERT INTO work_item_files VALUES (?, ?, ?, ?, ?, ?)",
            ("file-1", "item-1", "report.txt", "report.txt", str(attachment), "now"),
        )
    (source / "other.bin").write_bytes(b"other state")
    manifest = capture_offline_manifest(source, offline=True)
    return source, manifest


def test_relocated_restore_preserves_source_and_rebases_only_attachment(tmp_path):
    source, manifest = snapshot(tmp_path)
    original_db = (source / "workitems.db").read_bytes()
    target = tmp_path / "restored"
    receipt = restore_offline(manifest, target, offline=True)
    with sqlite3.connect(target / "workitems.db") as db:
        row = db.execute("SELECT file_path FROM work_item_files").fetchone()
    assert Path(row[0]) == target / "work_item_files/item-1/report.txt"
    assert Path(row[0]).read_bytes() == b"retained report"
    assert (source / "workitems.db").read_bytes() == original_db
    assert (target / "other.bin").read_bytes() == b"other state"
    assert receipt.rebased_attachments == 1
    assert capture_offline_manifest(source, offline=True) == manifest


@pytest.mark.parametrize("change", ["content", "extra", "missing", "symlink", "wal"])
def test_pinned_manifest_rejects_tampered_source(tmp_path, change):
    source, manifest = snapshot(tmp_path)
    path = source / "other.bin"
    if change == "content":
        path.write_bytes(b"changed")
    elif change == "extra":
        (source / "extra").write_bytes(b"new")
    elif change == "missing":
        path.unlink()
    elif change == "symlink":
        path.unlink()
        path.symlink_to(tmp_path)
    else:
        (source / "workitems.db-wal").write_bytes(b"pending")
    target = tmp_path / "restored"
    with pytest.raises(ValueError):
        restore_offline(manifest, target, offline=True)
    assert not target.exists()


@pytest.mark.parametrize("bad_path", ["/tmp/foreign", "../escape", "missing"])
def test_invalid_stored_attachment_never_changes_source(tmp_path, bad_path):
    source, _ = snapshot(tmp_path)
    with sqlite3.connect(source / "workitems.db") as db:
        db.execute("UPDATE work_item_files SET file_path=?", (bad_path,))
    manifest = capture_offline_manifest(source, offline=True)
    original = (source / "workitems.db").read_bytes()
    target = tmp_path / "restored"
    with pytest.raises(ValueError):
        restore_offline(manifest, target, offline=True)
    assert not target.exists()
    assert (source / "workitems.db").read_bytes() == original


def test_explicit_offline_and_absent_target_required(tmp_path):
    source, manifest = snapshot(tmp_path)
    with pytest.raises(ValueError):
        capture_offline_manifest(source, offline=False)
    with pytest.raises(ValueError):
        restore_offline(manifest, tmp_path / "unused", offline=False)
    with pytest.raises(ValueError):
        restore_offline(manifest, source, offline=True)
    assert (source / "other.bin").read_bytes() == b"other state"


def test_copy_failure_cleans_only_owned_target(tmp_path, monkeypatch):
    from actions.server import _datadir_restore as module

    source, manifest = snapshot(tmp_path)
    target = tmp_path / "restored"

    def fail(*args, **kwargs):
        raise OSError("synthetic copy failure")

    monkeypatch.setattr(module, "_copy_member", fail)
    with pytest.raises(OSError, match="synthetic"):
        restore_offline(manifest, target, offline=True)
    assert not target.exists()
    assert capture_offline_manifest(source, offline=True) == manifest


def test_mutation_during_copy_is_rejected(tmp_path, monkeypatch):
    from actions.server import _datadir_restore as module

    source, manifest = snapshot(tmp_path)
    copy = module._copy_member

    def mutate(*args, **kwargs):
        copy(*args, **kwargs)
        (source / "other.bin").write_bytes(b"concurrent writer")

    monkeypatch.setattr(module, "_copy_member", mutate)
    target = tmp_path / "restored"
    with pytest.raises(ValueError):
        restore_offline(manifest, target, offline=True)
    assert not target.exists()


def test_detached_backup_retains_original_root_binding(tmp_path):
    source, _ = snapshot(tmp_path)
    backup = tmp_path / "backup"
    shutil.copytree(source, backup)
    manifest = capture_offline_manifest(backup, offline=True, original_datadir=source)
    target = tmp_path / "restored"
    restore_offline(manifest, target, offline=True)
    with sqlite3.connect(target / "workitems.db") as db:
        stored = db.execute("SELECT file_path FROM work_item_files").fetchone()[0]
    assert Path(stored).read_bytes() == b"retained report"
    assert stored == str(target / "work_item_files/item-1/report.txt")


def test_target_symlink_parent_is_rejected(tmp_path):
    _, manifest = snapshot(tmp_path)
    parent = tmp_path / "alias"
    parent.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        restore_offline(manifest, parent / "restored", offline=True)
    assert not (tmp_path / "restored").exists()


def test_copied_bytes_are_verified_before_relocation(tmp_path, monkeypatch):
    from actions.server import _datadir_restore as module

    _, manifest = snapshot(tmp_path)
    copy = module._copy_member

    def corrupt(source, target, member):
        copy(source, target, member)
        if member.path == "other.bin":
            (target / member.path).write_bytes(b"bad copy")

    monkeypatch.setattr(module, "_copy_member", corrupt)
    target = tmp_path / "restored"
    with pytest.raises(ValueError, match="copied bytes"):
        restore_offline(manifest, target, offline=True)
    assert not target.exists()


@pytest.mark.parametrize("change", ["trigger", "schema", "missing-file", "traversal"])
def test_unsafe_attachment_metadata_rejects_entire_copy(tmp_path, change):
    source, _ = snapshot(tmp_path)
    with sqlite3.connect(source / "workitems.db") as db:
        if change == "trigger":
            db.execute(
                "CREATE TRIGGER unexpected AFTER UPDATE ON work_item_files "
                "BEGIN DELETE FROM work_items; END"
            )
        elif change == "schema":
            db.execute("ALTER TABLE work_item_files ADD COLUMN unknown TEXT")
        elif change == "traversal":
            db.execute("UPDATE work_item_files SET work_item_id='../escape'")
        else:
            (source / "work_item_files/item-1/report.txt").unlink()
    manifest = capture_offline_manifest(source, offline=True)
    target = tmp_path / "restored"
    with pytest.raises(ValueError):
        restore_offline(manifest, target, offline=True)
    assert not target.exists()
    assert capture_offline_manifest(source, offline=True) == manifest


def test_legacy_attachment_layout_relocates_without_schema_migration(tmp_path):
    source, _ = snapshot(tmp_path)
    with sqlite3.connect(source / "workitems.db") as db:
        db.execute("ALTER TABLE work_item_files RENAME TO current_files")
        db.execute(
            "CREATE TABLE work_item_files (work_item_id TEXT, filename TEXT, "
            "filepath TEXT, created_at TEXT)"
        )
        db.execute(
            "INSERT INTO work_item_files SELECT work_item_id,name,file_path,created_at "
            "FROM current_files"
        )
        db.execute("DROP TABLE current_files")
    manifest = capture_offline_manifest(source, offline=True)
    target = tmp_path / "restored"
    restore_offline(manifest, target, offline=True)
    with sqlite3.connect(target / "workitems.db") as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(work_item_files)")}
        stored = db.execute("SELECT filepath FROM work_item_files").fetchone()[0]
    assert columns == {"work_item_id", "filename", "filepath", "created_at"}
    assert Path(stored).read_bytes() == b"retained report"


def test_replaced_target_is_never_removed_on_failure(tmp_path, monkeypatch):
    from actions.server import _datadir_restore as module

    _, manifest = snapshot(tmp_path)
    target = tmp_path / "restored"

    def replace(*args):
        target.rename(tmp_path / "moved-owned-copy")
        target.mkdir()
        (target / "foreign.txt").write_bytes(b"preserve")
        raise OSError("target replaced")

    monkeypatch.setattr(module, "_copy_member", replace)
    with pytest.raises(OSError, match="target replaced"):
        restore_offline(manifest, target, offline=True)
    assert (target / "foreign.txt").read_bytes() == b"preserve"


def test_target_parent_must_be_private(tmp_path):
    _, manifest = snapshot(tmp_path)
    public = tmp_path / "shared"
    public.mkdir(mode=0o777)
    public.chmod(0o777)
    with pytest.raises(ValueError, match="private"):
        restore_offline(manifest, public / "restored", offline=True)
    assert not (public / "restored").exists()


def test_file_permissions_are_preserved_without_changing_source(tmp_path):
    source, _ = snapshot(tmp_path)
    (source / "other.bin").chmod(0o640)
    manifest = capture_offline_manifest(source, offline=True)
    target = tmp_path / "restored"
    restore_offline(manifest, target, offline=True)
    assert (target / "other.bin").stat().st_mode & 0o777 == 0o640
    assert (source / "other.bin").stat().st_mode & 0o777 == 0o640


def test_restored_attachment_passes_unchanged_sdk_containment(tmp_path):
    from actions.server._work_items_import import load_work_items_types

    adapter_type, _ = load_work_items_types()
    source = tmp_path / "source"
    source.mkdir()
    adapter = adapter_type(
        db_path=str(source / "workitems.db"),
        files_dir=str(source / "work_item_files"),
    )
    item = adapter.seed_input({"synthetic": True})
    adapter.add_file(item, "report.txt", "report.txt", b"verified SDK readback")
    manifest = capture_offline_manifest(source, offline=True)
    target = tmp_path / "restored"
    restore_offline(manifest, target, offline=True)
    restored = adapter_type(
        db_path=str(target / "workitems.db"),
        files_dir=str(target / "work_item_files"),
    )
    assert restored.get_file(item, "report.txt") == b"verified SDK readback"
    assert adapter.get_file(item, "report.txt") == b"verified SDK readback"
    assert capture_offline_manifest(source, offline=True) == manifest
