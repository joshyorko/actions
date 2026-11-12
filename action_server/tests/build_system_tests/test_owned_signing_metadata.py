from actions.server._build_common import process_call, signing


def test_windows_signing_uses_owned_description_without_live_signing(
    monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setattr(
        process_call, "run", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    monkeypatch.setattr(signing, "installed_azure_sign_tool", True)
    for key in (
        "VAULT_URL",
        "CLIENT_ID",
        "TENANT_ID",
        "CLIENT_SECRET",
        "CERTIFICATE_NAME",
    ):
        monkeypatch.setenv(key, "synthetic-" + key.lower())
    target = tmp_path / "owned.exe"
    signing._sign_windows_executable(target)
    assert len(calls) == 1
    command = calls[0][0][0]
    assert command[:2] == ["powershell", "-Command"]
    assert "--description-url https://github.com/joshyorko/actions" in command[2]
    assert "sema4.ai" not in command[2]
    assert "--timestamp-rfc3161 http://timestamp.digicert.com" in command[2]
    assert "--file-digest sha256" in command[2]
    assert str(target) in command[2]
