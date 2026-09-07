import shutil
import zipfile
from pathlib import Path

import pytest


class _FixedTemporaryDirectory:
    def __init__(self, path: Path):
        self.path = path

    def __enter__(self) -> str:
        self.path.mkdir()
        return str(self.path)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        shutil.rmtree(self.path)


def _write_zip(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def test_robot_zip_rejects_raw_parent_root_without_copying_parent_sentinel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server import _api_robots

    staging_parent = tmp_path / "staging-parent"
    staging = staging_parent / "staging"
    staging_parent.mkdir()
    robots_dir = tmp_path / "robots"
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots_dir)
    monkeypatch.setattr(
        _api_robots.tempfile,
        "TemporaryDirectory",
        lambda: _FixedTemporaryDirectory(staging),
    )

    (staging_parent / "robot.yaml").write_text(
        "name: seeded\ntasks:\n  run:\n    shell: echo seeded\n"
    )
    (staging_parent / "sentinel.txt").write_text("must stay outside staging")
    archive_path = tmp_path / "parent-root.zip"
    _write_zip(
        archive_path,
        {
            "../robot.yaml": "name: archive\ntasks:\n  run:\n    shell: echo archive\n",
            "../task.py": "print('archive')\n",
        },
    )

    success, message, imported_path = _api_robots._extract_zip_to_robots(
        archive_path, robot_name="imported"
    )

    assert success is False
    assert imported_path is None
    assert "root" in message.lower() or "path" in message.lower()
    assert not (robots_dir / "imported").exists()
    assert (staging_parent / "sentinel.txt").read_text() == "must stay outside staging"


@pytest.mark.parametrize(
    "members",
    [
        {
            "robot/robot.yaml": "name: ordinary\ntasks:\n  run:\n    shell: echo ok\n",
            "robot/task.py": "print('ok')\n",
        },
        {
            "robot.yaml": "name: rootless\ntasks:\n  run:\n    shell: echo ok\n",
            "task.py": "print('ok')\n",
        },
    ],
)
def test_robot_zip_accepts_ordinary_and_rootless_valid_packages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, members: dict[str, str]
) -> None:
    from actions.server import _api_robots

    robots_dir = tmp_path / "robots"
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", robots_dir)
    archive_path = tmp_path / "valid.zip"
    _write_zip(archive_path, members)

    success, message, imported_path = _api_robots._extract_zip_to_robots(
        archive_path, robot_name="valid"
    )

    assert success is True, message
    assert imported_path == robots_dir / "valid"
    assert (imported_path / "robot.yaml").exists()
