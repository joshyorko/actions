import json
from pathlib import Path

import pytest

from actions.work_items import ExceptionType, FileAdapter, State


def _write_direct(path: Path, items: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items), encoding="utf-8")


def test_direct_file_mode_preserves_top_level_list_and_index_ids(tmp_path):
    input_path = tmp_path / "inputs.json"
    output_path = tmp_path / "missing" / "outputs.json"
    original = [{"payload": {"name": "seed"}, "files": {}}]
    _write_direct(input_path, original)

    adapter = FileAdapter(str(input_path), str(output_path))

    assert adapter.reserve_input() == "0"
    adapter.save_payload("0", {"name": "changed"})
    output_id = adapter.create_output("0", {"result": True})

    assert output_id == "1"
    assert json.loads(input_path.read_text(encoding="utf-8")) == [
        {"payload": {"name": "changed"}, "files": {}}
    ]
    assert json.loads(output_path.read_text(encoding="utf-8")) == [
        {"payload": {"result": True}, "files": {}}
    ]


def test_existing_directory_with_json_suffix_remains_legacy_mode(tmp_path):
    input_dir = tmp_path / "legacy.json"
    output_dir = tmp_path / "outputs"
    input_dir.mkdir()
    _write_direct(
        input_dir / "work-items.json",
        {"workItems": [{"id": "legacy-1", "payload": {"mode": "legacy"}, "files": []}]},
    )

    adapter = FileAdapter(str(input_dir), str(output_dir))

    assert adapter.reserve_input() == "legacy-1"
    adapter.save_payload("legacy-1", {"mode": "still-legacy"})
    saved = json.loads((input_dir / "work-items.json").read_text(encoding="utf-8"))
    assert saved["workItems"][0]["payload"] == {"mode": "still-legacy"}


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        (None, "file does not exist"),
        ("", "file is empty"),
        ("{", "Expecting property name"),
        (json.dumps({"workItems": []}), "expected a top-level list"),
        (json.dumps(["not-an-object"]), "every work item must be an object"),
        (json.dumps([]), "expected at least one work item"),
    ],
)
def test_direct_file_mode_rejects_invalid_input_with_path_context(tmp_path, contents, message):
    input_path = tmp_path / "inputs.json"
    if contents is not None:
        input_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        FileAdapter(str(input_path), str(tmp_path / "outputs.json"))

    assert str(input_path) in str(exc_info.value)
    assert message in str(exc_info.value)


def test_direct_file_mode_uses_sibling_attachments_and_metadata_only_removal(tmp_path):
    input_path = tmp_path / "inputs.json"
    output_path = tmp_path / "outputs.json"
    attachment = tmp_path / "source.txt"
    attachment.write_bytes(b"source")
    _write_direct(
        input_path,
        [{"payload": {}, "files": {"logical.txt": attachment.name}}],
    )
    adapter = FileAdapter(str(input_path), str(output_path))

    assert adapter.get_file("0", "logical.txt") == b"source"
    adapter.remove_file("0", "logical.txt")

    assert attachment.read_bytes() == b"source"
    assert json.loads(input_path.read_text(encoding="utf-8"))[0]["files"] == {}


def test_direct_file_mode_rejects_attachment_escape(tmp_path):
    input_path = tmp_path / "queue" / "inputs.json"
    _write_direct(
        input_path,
        [{"payload": {}, "files": {"secret": "../secret.txt"}}],
    )
    adapter = FileAdapter(str(input_path), str(tmp_path / "outputs.json"))

    with pytest.raises(ValueError, match="Unsafe attachment path"):
        adapter.get_file("0", "secret")


def test_file_adapter_accepts_compatible_add_and_release_call_forms(tmp_path):
    input_path = tmp_path / "inputs.json"
    output_path = tmp_path / "outputs.json"
    _write_direct(input_path, [{"payload": {}, "files": {}}])
    direct = FileAdapter(str(input_path), str(output_path))

    direct.add_file("0", "legacy.bin", b"legacy")
    direct.release_input(
        "0",
        State.FAILED,
        {"type": ExceptionType.APPLICATION, "code": "E1", "message": "failed"},
    )

    assert direct.get_file("0", "legacy.bin") == b"legacy"

    input_dir = tmp_path / "legacy-in"
    output_dir = tmp_path / "legacy-out"
    input_dir.mkdir()
    _write_direct(
        input_dir / "work-items.json",
        {"workItems": [{"id": "item-1", "payload": {}, "files": []}]},
    )
    legacy = FileAdapter(str(input_dir), str(output_dir))

    legacy.add_file("item-1", "legacy.bin", b"legacy")
    legacy.release_input(
        "item-1",
        State.FAILED,
        {"type": ExceptionType.APPLICATION, "code": "E1", "message": "failed"},
    )

    envelope = json.loads((input_dir / "work-items.json").read_text(encoding="utf-8"))
    assert envelope["workItems"][0]["exception"]["code"] == "E1"
    legacy.remove_file("item-1", "legacy.bin")
    assert not (input_dir / "1" / "legacy.bin").exists()
