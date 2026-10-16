"""Pure validation tests for explicitly supplied portable source entries."""

from __future__ import annotations

import pytest

from actions.server.deployments import source_manifest


def _file(
    path: str, content: bytes = b"data", mode: int = 0o600
) -> source_manifest.SuppliedSourceEntry:
    return source_manifest.SuppliedSourceEntry(path, "file", content, mode)


def test_inventory_is_order_independent_and_omits_directory_entries() -> None:
    first = source_manifest.validate_proposed_inventory(
        [
            source_manifest.SuppliedSourceEntry("empty", "directory"),
            source_manifest.SuppliedSourceEntry("src", "directory"),
            _file("src/main.py", b"print('ok')", 0o711),
            _file("package.yaml", b"name: sample", 0o644),
        ],
        protected_input_names=["package.yaml"],
    )
    second = source_manifest.validate_proposed_inventory(
        [
            _file("package.yaml", b"name: sample", 0o640),
            _file("src/main.py", b"print('ok')", 0o755),
        ],
        protected_input_names=["package.yaml"],
    )

    assert first == second
    assert [entry.path for entry in first.entries] == ["package.yaml", "src/main.py"]
    assert [entry.mode for entry in first.entries] == [0o644, 0o755]
    assert b'"path":"empty"' not in first.canonical_json
    assert first.canonical_json == (
        b'{"entries":[{"mode":420,"path":"package.yaml",'
        b'"sha256":"05110bd6bbf4d7069eb6cafbc5a189f286511f927895e8ae34091601780bb8d5",'
        b'"size":12},{"mode":493,"path":"src/main.py",'
        b'"sha256":"e651ef002de96727cf3b1f8533ebb5c1036d12d795ec486c4cbd4ed2872fde31",'
        b'"size":11}],"sourcePolicyVersion":1}'
    )


def test_empty_inventory_keeps_the_same_explicit_policy_version() -> None:
    result = source_manifest.validate_proposed_inventory([], protected_input_names=[])

    assert result.entries == ()
    assert result.canonical_json == b'{"entries":[],"sourcePolicyVersion":1}'


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/absolute.py",
        "C:/drive.py",
        "a\\b.py",
        "a/../b.py",
        "a/./b.py",
        "a//b.py",
        "CON.txt",
        "folder/name.",
        "bad:name",
        "bad\x00name",
        "e\u0301.py",
    ],
)
def test_rejects_unsafe_or_non_nfc_names(path: str) -> None:
    with pytest.raises(ValueError):
        source_manifest.validate_proposed_inventory(
            [_file(path)], protected_input_names=[]
        )


@pytest.mark.parametrize(
    "entries",
    [
        [_file("Pkg/a.py"), _file("pkg/b.py")],
        [_file("Pkg/a.py"), _file("pkg/A.py")],
        [_file("Straße/a.py"), _file("STRASSE/b.py")],
        [_file("node"), _file("node/child.py")],
        [_file("node/child.py"), _file("node")],
    ],
)
def test_rejects_prefix_case_collisions_and_file_directory_conflicts(entries) -> None:
    with pytest.raises(ValueError):
        source_manifest.validate_proposed_inventory(entries, protected_input_names=[])


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "device", "socket"])
def test_rejects_non_regular_entry_kinds(kind: str) -> None:
    with pytest.raises(ValueError, match="regular file or directory"):
        source_manifest.validate_proposed_inventory(
            [source_manifest.SuppliedSourceEntry("input", kind)],
            protected_input_names=[],
        )


def test_protected_input_must_be_a_selected_regular_file() -> None:
    entries = [source_manifest.SuppliedSourceEntry("config", "directory")]
    with pytest.raises(ValueError, match="protected input"):
        source_manifest.validate_proposed_inventory(
            entries, protected_input_names=["config"]
        )
    with pytest.raises(ValueError, match="protected input"):
        source_manifest.validate_proposed_inventory(
            [_file("other")], protected_input_names=["config"]
        )


@pytest.mark.parametrize("mode", [0o4755, 0o2755, 0o1755, 0o10000])
def test_rejects_privileged_or_non_permission_mode_bits(mode: int) -> None:
    with pytest.raises(ValueError, match="mode"):
        source_manifest.validate_proposed_inventory(
            [_file("script.py", mode=mode)], protected_input_names=[]
        )


def test_rejects_directory_payload_and_non_bytes_file_content() -> None:
    with pytest.raises(ValueError, match="directory entries"):
        source_manifest.validate_proposed_inventory(
            [source_manifest.SuppliedSourceEntry("directory", "directory", b"")],
            protected_input_names=[],
        )
    with pytest.raises(ValueError, match="require supplied bytes"):
        source_manifest.validate_proposed_inventory(
            [
                source_manifest.SuppliedSourceEntry(
                    "file", "file", bytearray(b"x"), 0o644
                )
            ],
            protected_input_names=[],
        )


def test_accepts_immutable_bytes_and_integer_subclasses() -> None:
    class BytesSubclass(bytes):
        pass

    class ModeSubclass(int):
        pass

    result = source_manifest.validate_proposed_inventory(
        [
            source_manifest.SuppliedSourceEntry(
                "script.py", "file", BytesSubclass(b"ok"), ModeSubclass(0o744)
            )
        ],
        protected_input_names=[],
    )

    assert result.entries[0].mode == 0o755
    assert result.entries[0].size == 2


def test_rejects_boolean_file_mode() -> None:
    with pytest.raises(ValueError, match="mode"):
        source_manifest.validate_proposed_inventory(
            [source_manifest.SuppliedSourceEntry("script.py", "file", b"x", True)],
            protected_input_names=[],
        )


def test_enforces_entry_file_total_and_path_bounds(monkeypatch) -> None:
    monkeypatch.setattr(source_manifest, "MAX_ENTRIES", 1)
    with pytest.raises(ValueError, match="entry limit"):
        source_manifest.validate_proposed_inventory(
            [_file("one"), _file("two")], protected_input_names=[]
        )

    monkeypatch.setattr(source_manifest, "MAX_ENTRIES", 10)
    monkeypatch.setattr(source_manifest, "MAX_FILE_BYTES", 2)
    with pytest.raises(ValueError, match="file exceeds"):
        source_manifest.validate_proposed_inventory(
            [_file("large", b"123")], protected_input_names=[]
        )

    monkeypatch.setattr(source_manifest, "MAX_FILE_BYTES", 10)
    monkeypatch.setattr(source_manifest, "MAX_TOTAL_BYTES", 3)
    with pytest.raises(ValueError, match="total byte limit"):
        source_manifest.validate_proposed_inventory(
            [_file("a", b"12"), _file("b", b"34")], protected_input_names=[]
        )

    monkeypatch.setattr(source_manifest, "MAX_TOTAL_BYTES", 10)
    monkeypatch.setattr(source_manifest, "MAX_PATH_DEPTH", 2)
    with pytest.raises(ValueError, match="depth limit"):
        source_manifest.validate_proposed_inventory(
            [_file("a/b/c")], protected_input_names=[]
        )

    monkeypatch.setattr(source_manifest, "MAX_PATH_DEPTH", 64)
    monkeypatch.setattr(source_manifest, "MAX_COMPONENT_BYTES", 2)
    with pytest.raises(ValueError, match="component exceeds"):
        source_manifest.validate_proposed_inventory(
            [_file("long")], protected_input_names=[]
        )

    monkeypatch.setattr(source_manifest, "MAX_COMPONENT_BYTES", 255)
    monkeypatch.setattr(source_manifest, "MAX_PATH_BYTES", 4)
    with pytest.raises(ValueError, match="path exceeds"):
        source_manifest.validate_proposed_inventory(
            [_file("a/bcde")], protected_input_names=[]
        )


def test_rejects_oversized_lazy_entries_before_consuming_generator_tail(
    monkeypatch,
) -> None:
    monkeypatch.setattr(source_manifest, "MAX_FILE_BYTES", 1)

    def oversized_entry_then_tail():
        yield _file("large", b"12")
        raise AssertionError(
            "entry generator tail was consumed before file-size rejection"
        )

    with pytest.raises(ValueError, match="file exceeds"):
        source_manifest.validate_proposed_inventory(
            oversized_entry_then_tail(), protected_input_names=[]
        )


def test_rejects_cumulative_bytes_before_consuming_generator_tail(monkeypatch) -> None:
    monkeypatch.setattr(source_manifest, "MAX_TOTAL_BYTES", 3)

    def over_total_then_tail():
        yield _file("first", b"12")
        yield _file("second", b"34")
        raise AssertionError(
            "entry generator tail was consumed before total-size rejection"
        )

    with pytest.raises(ValueError, match="total byte limit"):
        source_manifest.validate_proposed_inventory(
            over_total_then_tail(), protected_input_names=[]
        )
