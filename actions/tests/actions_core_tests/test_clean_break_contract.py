import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import tomlkit

ROOT = Path(__file__).parents[2]


def _run_console(argv, cwd):
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as error:
        raise AssertionError(
            f"actions command timed out: argv={argv!r}, cwd={cwd}, "
            f"returncode=None, stdout={error.stdout!r}, stderr={error.stderr!r}"
        ) from error

    if result.returncode != 0:
        raise AssertionError(
            f"actions command failed: argv={argv!r}, cwd={cwd}, "
            f"returncode={result.returncode}, stdout={result.stdout!r}, "
            f"stderr={result.stderr!r}"
        )
    return result


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
        entry_points = distribution.read_text("entry_points.txt") or ""
        direct_url = distribution.read_text("direct_url.json") or ""
        scripts = sorted(path.name for path in scripts_dir.iterdir())
        raise AssertionError(
            "Installed actions launcher could not be resolved.\n"
            f"sys.executable={sys.executable}\n"
            f"sys.prefix={sys.prefix}\n"
            f"PATH={os.pathsep.join(os.environ.get('PATH', '').split(os.pathsep))}\n"
            f"which(actions)={shutil.which('actions')}\n"
            f"scripts_dir={scripts_dir}\n"
            f"scripts_dir_filenames={scripts}\n"
            f"distribution_location={distribution.locate_file('')}\n"
            f"entry_points_summary={entry_points!r}\n"
            f"direct_url_summary={direct_url!r}"
        )

    executable = Path(executable)
    assert executable.parent == scripts_dir

    result = _run_console(
        [str(executable), "list", str(action_file), "--skip-lint"], tmp_path
    )
    listed = json.loads(result.stdout)
    assert [entry["name"] for entry in listed] == ["hello"]

    output_file = tmp_path / "result.json"
    result = _run_console(
        [
            str(executable),
            "run",
            str(action_file),
            "-a",
            "hello",
            f"--json-output={output_file}",
        ],
        tmp_path,
    )
    assert json.loads(output_file.read_text()) == {
        "result": "Hello, world!",
        "message": "",
        "status": "PASS",
    }
