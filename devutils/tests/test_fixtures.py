from pathlib import Path


def test_actions_executable_resolves_command_name_on_windows(monkeypatch, tmp_path):
    from devutils import fixtures

    poetry_launcher = tmp_path / "poetry" / "Scripts" / "actions.cmd"
    poetry_launcher.parent.mkdir(parents=True)
    poetry_launcher.touch()

    monkeypatch.setattr(fixtures.sys, "platform", "win32")
    monkeypatch.setattr(fixtures.sys, "executable", str(tmp_path / "uv" / "python.exe"))
    monkeypatch.setattr(
        fixtures.shutil,
        "which",
        lambda name: str(poetry_launcher) if name == "actions" else None,
    )

    assert fixtures._actions_executable() == Path(poetry_launcher)
