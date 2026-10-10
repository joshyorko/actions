from __future__ import annotations
import os, shutil, subprocess, sys
from pathlib import Path

venv = Path('/workspace/work/actions-mk3-canvas-proof/action_server/.venv').resolve()
root = Path('/workspace/work/actions-mk3-db-savepoint/action_server').resolve()
env = os.environ.copy()
for key in ('VIRTUAL_ENV', 'POETRY_ACTIVE', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV', 'CONDA_PROMPT_MODIFIER', 'CONDA_SHLVL', 'CONDA_EXE', '_CE_CONDA', '_CE_M', 'PYTHONHOME', 'PYTHONPATH', 'PYTHON_EXE', 'ROBOT_ARTIFACTS', 'ROBOT_ROOT'):
    env.pop(key, None)
env.update({
    'VIRTUAL_ENV': str(venv),
    'PATH': os.pathsep.join((str(venv / 'bin'), os.environ.get('PATH', ''))),
    'POETRY_VIRTUALENVS_CREATE': 'true',
    'POETRY_VIRTUALENVS_IN_PROJECT': 'true',
    'POETRY_VIRTUALENVS_OPTIONS_SYSTEM_SITE_PACKAGES': 'false',
    'ACTIONS_RUNTIME_TEST_PYTHON': str(venv / 'bin/python'),
    'PYTHONPATH': str(root / 'src'),
})
print('outer python:', sys.executable)
print('poetry executable:', shutil.which('poetry'))
for cmd in (
    ['poetry', '--version'],
    ['poetry', 'env', 'info', '--path'],
    ['poetry', 'run', 'python', '-c', 'import sys; print(sys.executable); print(sys.prefix); import actions.server._database as d; print(d.__file__)'],
    ['poetry', 'run', 'ruff', '--version'],
):
    run = subprocess.run(cmd, cwd=root, env=env, text=True, capture_output=True)
    print('COMMAND:', *cmd, 'EXIT:', run.returncode)
    print(run.stdout, end='')
    print(run.stderr, end='', file=sys.stderr)
    if run.returncode:
        raise SystemExit(run.returncode)
