import errno
from pathlib import Path

import pytest

from actions.server import _directory_publication as publication


def test_native_publication_moves_complete_directory(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "nested").mkdir(parents=True)
    (source / "nested" / "payload").write_bytes(b"complete synthetic content")
    destination = tmp_path / "published"

    publication.rename_directory_no_replace(source, destination)

    assert not source.exists()
    assert (
        destination / "nested" / "payload"
    ).read_bytes() == b"complete synthetic content"


@pytest.mark.parametrize("kind", ["empty-directory", "nonempty-directory", "file"])
def test_native_collision_preserves_both_entries(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "payload").write_text("new")
    destination = tmp_path / "published"
    if kind == "file":
        destination.write_text("existing")
    else:
        destination.mkdir()
        if kind == "nonempty-directory":
            (destination / "payload").write_text("existing")
    identity = destination.stat().st_ino

    with pytest.raises(FileExistsError):
        publication.rename_directory_no_replace(source, destination)

    assert destination.stat().st_ino == identity
    assert (source / "payload").read_text() == "new"
    if kind == "file":
        assert destination.read_text() == "existing"
    elif kind == "nonempty-directory":
        assert (destination / "payload").read_text() == "existing"
    else:
        assert list(destination.iterdir()) == []


def test_unsupported_platform_fails_without_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    destination = tmp_path / "published"
    monkeypatch.setattr(publication.sys, "platform", "unsupported")
    with pytest.raises(OSError) as error:
        publication.rename_directory_no_replace(source, destination)
    assert error.value.errno == errno.ENOTSUP
    assert source.is_dir() and not destination.exists()


def test_missing_native_symbol_fails_without_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    destination = tmp_path / "published"
    monkeypatch.setattr(publication.sys, "platform", "linux")
    monkeypatch.setattr(publication.ctypes, "CDLL", lambda *args, **kwargs: object())
    with pytest.raises(OSError) as error:
        publication.rename_directory_no_replace(source, destination)
    assert error.value.errno == errno.ENOTSUP
    assert source.is_dir() and not destination.exists()


@pytest.mark.parametrize("failure", [errno.ENOSYS, errno.EOPNOTSUPP, errno.EXDEV])
def test_native_failure_never_falls_back_to_copy_or_replace(
    tmp_path: Path, monkeypatch, failure: int
) -> None:
    from types import SimpleNamespace

    source = tmp_path / "source"
    source.mkdir()
    (source / "payload").write_text("complete")
    destination = tmp_path / "published"

    def native_failure(*args):
        publication.ctypes.set_errno(failure)
        return -1

    monkeypatch.setattr(publication.sys, "platform", "linux")
    monkeypatch.setattr(
        publication.ctypes,
        "CDLL",
        lambda *args, **kwargs: SimpleNamespace(renameat2=native_failure),
    )
    with pytest.raises(OSError) as error:
        publication.rename_directory_no_replace(source, destination)
    assert error.value.errno == failure
    assert (source / "payload").read_text() == "complete"
    assert not destination.exists()
