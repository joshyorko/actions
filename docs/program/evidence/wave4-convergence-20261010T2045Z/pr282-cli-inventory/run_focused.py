from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPOSITORY = Path("/workspace/work/actions-mk3-pr282-cli")
PACKAGE = REPOSITORY / "action_server"
PREPARED_VENV = Path("/workspace/work/actions-mk3-pr282/action_server/.venv")
PYTHON = PREPARED_VENV / "bin" / "python"

environment = os.environ.copy()
for name in (
    "VIRTUAL_ENV", "POETRY_ACTIVE", "CONDA_PREFIX", "CONDA_DEFAULT_ENV",
    "CONDA_PROMPT_MODIFIER", "CONDA_SHLVL", "CONDA_EXE", "_CE_CONDA", "_CE_M",
    "PYTHONHOME", "PYTHON_EXE", "ROBOT_ARTIFACTS", "ROBOT_ROOT",
):
    environment.pop(name, None)
environment["PYTHONPATH"] = os.pathsep.join(
    (str(PACKAGE / "src"), str(PACKAGE / "tests"))
)
environment["ACTIONS_RUNTIME_TEST_PYTHON"] = str(PYTHON)

probe = subprocess.run(
    [
        str(PYTHON), "-c",
        "import actions.server, sys; "
        "print('PYTHON=' + sys.executable); "
        "print('RUNTIME=' + str(actions.server.__file__))",
    ],
    cwd=PACKAGE,
    env=environment,
    check=True,
    text=True,
    capture_output=True,
)
print(probe.stdout, end="", flush=True)
runtime_path = Path(
    next(line.removeprefix("RUNTIME=") for line in probe.stdout.splitlines()
         if line.startswith("RUNTIME="))
).resolve()
expected = (PACKAGE / "src" / "actions" / "server" / "__init__.py").resolve()
if runtime_path != expected:
    raise SystemExit(f"Runtime import origin mismatch: {runtime_path} != {expected}")

if sys.argv[1:] == ["lint"]:
    command = [str(PREPARED_VENV / "bin" / "ruff"), "check", "tests/action_server_tests/test_cli.py"]
elif sys.argv[1:] == ["type"]:
    command = [
        str(PREPARED_VENV / "bin" / "mypy"), "--follow-imports=silent",
        "--show-column-numbers", "--namespace-packages",
        "--explicit-package-bases", "tests/action_server_tests/test_cli.py",
    ]
else:
    command = [
        str(PYTHON), "-m", "pytest", "-q",
        "tests/action_server_tests/test_cli.py::test_new_list_templates",
    ]
subprocess.run(command, cwd=PACKAGE, env=environment, check=True)
