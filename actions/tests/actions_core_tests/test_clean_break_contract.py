import json
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


def test_console_script_collects_and_executes_conventional_actions_py(tmp_path):
    action_file = tmp_path / "actions.py"
    action_file.write_text(
        "from actions import action\n"
        "@action\n"
        "def hello(name: str = 'world') -> str:\n"
        "    return f'Hello, {name}!'\n"
    )

    scripts_dir = Path(sys.executable).parent
    executable = scripts_dir / ("actions.exe" if sys.platform == "win32" else "actions")
    assert executable.exists(), f"Missing installed console script: {executable}"

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
