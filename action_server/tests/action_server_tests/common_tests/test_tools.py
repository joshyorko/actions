"""Tool contracts use owned fixtures, never download or execute vendor binaries."""

from pathlib import Path

import pytest

from actions.server._common.tools import ActionServerTool, AgentCliTool, RccTool


@pytest.mark.parametrize("tool_class", [ActionServerTool, AgentCliTool])
@pytest.mark.parametrize("entrypoint", ["instance", "default"])
def test_retired_vendor_download_has_no_side_effects(
    monkeypatch, tmp_path, tool_class, entrypoint
):
    def forbidden(*args, **kwargs):
        pytest.fail("Retired download attempted a side effect")

    import actions_http

    from actions.server._common import locations, tools

    monkeypatch.setattr(actions_http, "download_with_resume", forbidden)
    monkeypatch.setattr(locations, "get_default_executable_path", forbidden)
    monkeypatch.setattr(tools, "_verify_tool_downloaded_ok", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    with pytest.raises(RuntimeError, match="retired"):
        if entrypoint == "instance":
            tool_class(str(tmp_path / "unused"), "legacy-version").download()
        else:
            tool_class.get_default_executable(version="legacy-version", download=True)


@pytest.mark.parametrize("tool_class", [ActionServerTool, AgentCliTool])
def test_explicit_legacy_tool_path_and_verification_remain(
    monkeypatch, tmp_path, tool_class
):
    from actions.server._common import locations, tools

    target = tmp_path / tool_class.executable_name
    monkeypatch.setattr(
        locations, "get_default_executable_path", lambda **kwargs: target
    )
    assert tool_class.get_default_executable(version="legacy-version") == target
    tool = tool_class(str(target), "legacy-version")
    observed = []
    monkeypatch.setattr(tools, "_get_tool_version", lambda *args: observed.append(args))
    assert not tool.verify()
    target.write_text("owned fixture")
    target.chmod(0o700)
    tool.make_run_check = False
    assert tool.verify()
    assert not observed
    tool.force_sys_platform = "darwin"
    tool.force_machine = "arm64"
    expected = "macos-arm64" if tool.available_in_mac_os_arm64 else "macos64"
    assert tool._get_release_artifact_relative_path(tool.executable_name).startswith(
        expected + "/"
    )


@pytest.mark.parametrize(
    "platform,machine,asset",
    [
        ("linux", "x86_64", "rcc-linux64"),
        ("darwin", "arm64", "rcc-macosarm64"),
        ("win32", "AMD64", "rcc-windows64.exe"),
    ],
)
def test_rcc_download_uses_owned_release(
    monkeypatch, tmp_path, platform, machine, asset
):
    import actions_http

    target = tmp_path / "rcc"
    calls = []

    def download(url, path, **kwargs):
        calls.append((url, path, kwargs))
        path.write_text("owned fixture, never executed")
        path.chmod(0o700)

    monkeypatch.setattr(actions_http, "download_with_resume", download)
    tool = RccTool(str(target), "v18.19.3")
    tool.force_sys_platform = platform
    tool.force_machine = machine
    tool.make_run_check = False
    tool.download()
    tool.download()
    assert calls == [
        (
            f"https://github.com/joshyorko/rcc/releases/download/v18.19.3/{asset}",
            target,
            {"make_executable": True},
        )
    ]
