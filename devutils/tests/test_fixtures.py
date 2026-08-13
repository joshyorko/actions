def test_actions_executable_resolves_command_name(monkeypatch, tmp_path):
    from devutils import fixtures

    resolved_command = tmp_path / "opaque-launcher"
    lookup_names = []

    monkeypatch.setattr(
        fixtures.shutil,
        "which",
        lambda name: lookup_names.append(name) or str(resolved_command),
    )

    assert fixtures._actions_executable() == resolved_command
    assert lookup_names == ["actions"]


def test_actions_run_uses_resolved_command_and_preserves_tokens_on_non_windows(
    monkeypatch, tmp_path
):
    from devutils import fixtures

    resolved_command = tmp_path / "opaque-launcher"
    captured = {}

    def run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return fixtures.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(fixtures, "_actions_executable", lambda: resolved_command)
    monkeypatch.setattr(fixtures.sys, "platform", "linux")
    monkeypatch.setattr(fixtures.subprocess, "run", run)

    fixtures.actions_run(["run", "*.py|**/*.py"], "any", cwd=tmp_path, timeout=17)

    assert captured["args"] == [str(resolved_command), "run", "*.py|**/*.py"]
    assert captured["kwargs"]["cwd"] == tmp_path
    assert captured["kwargs"]["timeout"] == 17
    assert captured["kwargs"].get("shell", False) is False


def test_actions_run_uses_metadata_bootstrap_and_preserves_tokens_on_windows(
    monkeypatch, tmp_path
):
    from devutils import fixtures

    resolved_command = tmp_path / "opaque-launcher"
    captured = {}

    def run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return fixtures.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(fixtures, "_actions_executable", lambda: resolved_command)
    monkeypatch.setattr(fixtures.sys, "platform", "win32")
    monkeypatch.setattr(fixtures.subprocess, "run", run)

    fixtures.actions_run(["run", "*.py|**/*.py"], "any", cwd=tmp_path, timeout=17)

    args = captured["args"]
    assert args[0] == fixtures.sys.executable
    assert args[1] == "-c"
    assert args[3:] == ["run", "*.py|**/*.py"]
    assert args[2] == fixtures._ACTIONS_BOOTSTRAP
    assert 'distribution("actions-core")' in args[2]
    assert 'entry_point.group == "console_scripts"' in args[2]
    assert 'entry_point.name == "actions"' in args[2]
    assert 'entry_point.value != "actions.cli:main"' in args[2]
    assert "shell" not in captured["kwargs"]


def test_actions_run_bootstrap_has_no_shell_or_cmd_invocation():
    from devutils import fixtures

    assert "shell=True" not in fixtures._ACTIONS_BOOTSTRAP
    assert "cmd.exe" not in fixtures._ACTIONS_BOOTSTRAP
