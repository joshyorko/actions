"""Keep POSIX operator API refusals covered on every platform."""

import os

import pytest


class NonPosixOSFacade:
    """A local OS view that exercises module guards without changing pathlib."""

    name = "nt"
    environ = os.environ

    def __getattr__(self, name):
        if name == "O_NOFOLLOW":
            raise AttributeError(name)
        return getattr(os, name)


def test_manifest_capture_refuses_missing_posix_capability_before_access(
    tmp_path, monkeypatch
):
    from actions.server import _datadir_restore

    source = tmp_path / "missing-backup"
    monkeypatch.setattr(_datadir_restore, "os", NonPosixOSFacade())

    with pytest.raises(ValueError, match="explicit offline POSIX backup required"):
        _datadir_restore.capture_offline_manifest(source, offline=True)

    assert not source.exists()


def test_local_authorization_refuses_non_posix_before_owned_state_access(
    tmp_path, monkeypatch
):
    from actions.server import _local_authorization

    datadir = tmp_path / "missing-datadir"
    request = tmp_path / "missing-request.json"
    monkeypatch.delenv("ACTION_SERVER_DATABASE_URL", raising=False)
    monkeypatch.setattr(_local_authorization, "os", NonPosixOSFacade())

    with pytest.raises(
        ValueError,
        match="offline authorization requires POSIX private ownership semantics",
    ):
        _local_authorization.run_local_authorization(str(datadir), str(request))

    assert not datadir.exists()
    assert not request.exists()
