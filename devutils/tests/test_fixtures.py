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
