import sys
from pathlib import Path
from unittest.mock import patch

import yaml

TOOLKIT_ROOT = Path(__file__).parents[1]
REPOSITORY_ROOT = TOOLKIT_ROOT.parent
sys.path.insert(0, str(TOOLKIT_ROOT))
import toolkit  # noqa: E402


def test_manifest_defines_cross_platform_developer_tasks() -> None:
    manifest = yaml.safe_load((TOOLKIT_ROOT / "toolkit.yaml").read_text())

    assert set(manifest["devTasks"]) == {
        "Doctor",
        "Bootstrap",
        "Test",
        "ToolkitTest",
        "Lint",
        "Typecheck",
        "Docs",
        "CheckAll",
        "FrontendTest",
        "BuildCommunity",
    }
    assert manifest["ignoreFiles"] == ["../.gitignore"]
    assert manifest["environmentConfigs"] == ["setup.yaml"]


def test_bootstrap_launchers_download_pinned_rcc_and_run_toolkit() -> None:
    shell = (REPOSITORY_ROOT / "devutils" / "bin" / "develop.sh").read_text()
    batch = (REPOSITORY_ROOT / "devutils" / "bin" / "develop.bat").read_text()

    for launcher in (shell, batch):
        assert "v18.18.1" in launcher
        assert "joshyorko/rcc/releases/download" in launcher
        assert "developer" in launcher
        assert "toolkit.yaml" in launcher
    assert "brew tap joshyorko/tools" in shell
    assert "brew install --cask joshyorko/tools/rcc" in shell
    assert "powershell.exe" in batch


def test_dispatcher_resolves_repository_root() -> None:
    assert toolkit.REPOSITORY_ROOT == REPOSITORY_ROOT
    assert toolkit.RCC_VERSION == "v18.18.1"
    assert toolkit.PACKAGES == (
        "actions",
        "actions-http-helper",
        "devutils",
        "work-items",
        "action_server",
    )
    assert toolkit.COMMANDS.keys() >= {
        "doctor",
        "bootstrap",
        "test",
        "toolkit-test",
        "lint",
        "typecheck",
        "docs",
        "check-all",
        "frontend-test",
        "build-community",
    }


def test_run_does_not_use_a_shell_or_inherit_virtual_env() -> None:
    with patch.dict(
        "os.environ",
        {"VIRTUAL_ENV": "/host/venv", "POETRY_ACTIVE": "1"},
    ), patch(
        "toolkit.subprocess.run"
    ) as run:
        toolkit.run(["python", "--version"])

    assert "shell" not in run.call_args.kwargs
    assert "VIRTUAL_ENV" not in run.call_args.kwargs["env"]
    assert "POETRY_ACTIVE" not in run.call_args.kwargs["env"]


def test_build_community_uses_public_invoke_contract() -> None:
    with patch.object(toolkit, "poetry") as poetry:
        toolkit.build_community()

    assert [call.args for call in poetry.call_args_list] == [
        ("action_server", "run", "invoke", "build-frontend"),
        ("action_server", "run", "invoke", "build-executable", "--go-wrapper"),
    ]
