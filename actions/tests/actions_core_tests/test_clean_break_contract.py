import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import tomlkit

ROOT = Path(__file__).parents[2]


def test_actions_core_owns_public_namespace_and_absorbed_mcp():
    metadata = tomlkit.parse((ROOT / "pyproject.toml").read_text())

    assert metadata["tool"]["poetry"]["name"] == "actions-core"
    assert metadata["tool"]["poetry"]["version"] == "1.0.0"
    assert metadata["tool"]["poetry"]["packages"] == [
        {"include": "actions", "from": "src"}
    ]

    from actions import action
    from actions.mcp import tool

    assert callable(action)
    assert callable(tool)


def test_work_items_does_not_ship_root_actions_initializer():
    work_items_root = ROOT.parent / "work-items" / "src" / "actions"

    assert not (work_items_root / "__init__.py").exists()


def test_installed_console_script_collects_and_executes_conventional_actions_py(
    tmp_path,
):
    action_file = tmp_path / "actions.py"
    action_file.write_text(
        "from actions import action\n"
        "@action\n"
        "def hello(name: str = 'world') -> str:\n"
        "    return f'Hello, {name}!'\n"
    )

    distribution = importlib.metadata.distribution("actions-core")
    console_scripts = {
        entry_point.name: entry_point.value
        for entry_point in distribution.entry_points
        if entry_point.group == "console_scripts"
    }
    assert console_scripts.get("actions") == "actions.cli:main"

    scripts_dir = Path(sys.executable).parent
    executable = shutil.which("actions")
    if executable is None:
        candidates = [scripts_dir / "actions"]
        if sys.platform == "win32":
            candidates.append(scripts_dir / "actions.cmd")
        executable_path = next((path for path in candidates if path.exists()), None)
        executable = str(executable_path) if executable_path else None

    if executable is None:
        entry_points = distribution.read_text("entry_points.txt") or ""
        direct_url = distribution.read_text("direct_url.json") or ""
        scripts = sorted(path.name for path in scripts_dir.iterdir())
        raise AssertionError(
            "Installed actions launcher could not be resolved.\n"
            f"sys.executable={sys.executable}\n"
            f"sys.prefix={sys.prefix}\n"
            f"PATH={os.pathsep.join(os.environ.get('PATH', '').split(os.pathsep))}\n"
            f"which(actions)={shutil.which('actions')}\n"
            f"which(actions.cmd)={shutil.which('actions.cmd')}\n"
            f"scripts_dir={scripts_dir}\n"
            f"scripts_dir_filenames={scripts}\n"
            f"distribution_location={distribution.locate_file('')}\n"
            f"entry_points_summary={entry_points!r}\n"
            f"direct_url_summary={direct_url!r}"
        )

    executable = Path(executable)

    result = subprocess.run(
        [str(executable), "list", str(action_file), "--skip-lint"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    listed = json.loads(result.stdout)
    assert [entry["name"] for entry in listed] == ["hello"]

    output_file = tmp_path / "result.json"
    result = subprocess.run(
        [
            str(executable),
            "run",
            str(action_file),
            "-a",
            "hello",
            f"--json-output={output_file}",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(output_file.read_text()) == {
        "result": "Hello, world!",
        "message": "",
        "status": "PASS",
    }
