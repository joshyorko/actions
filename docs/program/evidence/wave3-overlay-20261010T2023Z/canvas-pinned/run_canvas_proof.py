"""Run the opt-in Runtime Canvas acceptance through the RCC toolchain."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

checkout = Path("/workspace/work/actions-mk3-canvas-proof")
evidence = Path("/workspace/work/actions-mk3-evidence/canvas-pinned")
path_entries = [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
# The source test treats any `chromium` found in PATH as an explicit override.
# Remove only directories that expose that name, retaining the rest of the RCC
# and package toolchain unchanged.
controlled_entries = [
    entry
    for entry in path_entries
    if not (Path(entry) / "chromium").exists()
    and Path(entry).resolve() not in {Path("/usr/bin"), Path("/bin")}
]
# Keep ordinary system tools available to subprocesses (`npm` needs `sh`) while
# withholding the one system-browser command that the source test auto-selects.
system_bin = evidence / "system-bin-without-chromium"
system_bin.mkdir(parents=True, exist_ok=True)
for entry in Path("/usr/bin").iterdir():
    if "chromium" in entry.name.lower() or entry.resolve() == Path("/usr/bin/chromium").resolve():
        continue
    destination = system_bin / entry.name
    if not destination.exists() and not destination.is_symlink():
        destination.symlink_to(entry)
controlled_entries.append(str(system_bin))
controlled_path = os.pathsep.join(controlled_entries)
if shutil.which("chromium", path=controlled_path):
    raise SystemExit("controlled PATH still exposes chromium; refusing non-pinned run")
required_tools = ("poetry", "uv", "npm", "node")
missing = [tool for tool in required_tools if shutil.which(tool, path=controlled_path) is None]
if missing:
    raise SystemExit(f"controlled PATH lost required RCC tools: {', '.join(missing)}")

env = os.environ.copy()
# Match developer/toolkit.py package_environment: RCC's CONDA variables cause
# Poetry to mistake the Holotree Python for the package interpreter unless
# they are cleared before launching the branch-owned venv.
for name in (
    "VIRTUAL_ENV", "POETRY_ACTIVE", "CONDA_PREFIX", "CONDA_DEFAULT_ENV",
    "CONDA_PROMPT_MODIFIER", "CONDA_SHLVL", "CONDA_EXE", "_CE_CONDA",
    "_CE_M", "PYTHONHOME", "PYTHONPATH", "PYTHON_EXE", "ROBOT_ARTIFACTS",
    "ROBOT_ROOT", "ACTIONS_RUNTIME_TEST_PYTHON",
):
    env.pop(name, None)
package_scripts = checkout / "action_server" / ".venv" / "bin"
controlled_path = os.pathsep.join((str(package_scripts), controlled_path))
env.update(
    {
        "PATH": controlled_path,
        "POETRY_VIRTUALENVS_CREATE": "true",
        "POETRY_VIRTUALENVS_IN_PROJECT": "true",
        "POETRY_VIRTUALENVS_OPTIONS_SYSTEM_SITE_PACKAGES": "false",
        "ACTIONS_CANVAS_RUNTIME_ACCEPTANCE": "1",
        "ACTIONS_HOME": str(evidence / "actions-home"),
        "TMPDIR": str(evidence / "tmp"),
        "PYTEST_ADDOPTS": "--basetemp=" + str(evidence / "pytest-tmp"),
    }
)
(evidence / "tmp").mkdir(parents=True, exist_ok=True)
(evidence / "actions-home").mkdir(parents=True, exist_ok=True)
command = [
    str(package_scripts / "python"),
    "-m",
    "pytest",
    "-m",
    "integration_test",
    "-q",
    "action_server_tests/mcp/test_mcp_apps_authoring.py",
    "-k",
    "canvas_view_calls_public_action_through_runtime_bridge",
]
print("Controlled PATH excludes every directory that exposes `chromium`.", flush=True)
print("Command:", " ".join(str(part) for part in command), flush=True)
print("Test Python:", package_scripts / "python", flush=True)
subprocess.run(command, cwd=checkout / "action_server" / "tests", env=env, check=True, timeout=1800)
