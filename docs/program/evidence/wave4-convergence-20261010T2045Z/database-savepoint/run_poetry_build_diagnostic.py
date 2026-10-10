from __future__ import annotations
import os, subprocess, sys
from pathlib import Path

package = Path('/workspace/work/actions-mk3-db-savepoint/action_server')
venv = Path('/workspace/work/actions-mk3-canvas-proof/action_server/.venv').resolve()
env = os.environ.copy()
for key in ('VIRTUAL_ENV', 'POETRY_ACTIVE', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV', 'CONDA_PROMPT_MODIFIER', 'CONDA_SHLVL', 'CONDA_EXE', '_CE_CONDA', '_CE_M', 'PYTHONHOME', 'PYTHONPATH', 'PYTHON_EXE', 'ROBOT_ARTIFACTS', 'ROBOT_ROOT'):
    env.pop(key, None)
env['VIRTUAL_ENV'] = str(venv)
env['PATH'] = os.pathsep.join((str(venv / 'bin'), env.get('PATH', '')))
env['POETRY_VIRTUALENVS_CREATE'] = 'true'
env['POETRY_VIRTUALENVS_IN_PROJECT'] = 'true'
env['POETRY_VIRTUALENVS_OPTIONS_SYSTEM_SITE_PACKAGES'] = 'false'
env['ACTIONS_RUNTIME_TEST_PYTHON'] = str(venv / 'bin/python')
# Mirror action_server/tests/contract_tests/test_active_contracts.py::_build_wheels.
build_env = env.copy()
build_env.pop('VIRTUAL_ENV', None)
build_env.pop('POETRY_ACTIVE', None)
build_env.pop('PYTHONPATH', None)
build_env['ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD'] = 'true'
out = Path('/workspace/work/actions-mk3-evidence/database-savepoint/poetry-build-out')
out.mkdir(exist_ok=True)
command = ['poetry', 'build', '-f', 'wheel', '-o', str(out)]
print('cwd:', package)
print('VIRTUAL_ENV removed:', 'VIRTUAL_ENV' not in build_env)
print('POETRY_ACTIVE removed:', 'POETRY_ACTIVE' not in build_env)
print('PYTHONPATH removed:', 'PYTHONPATH' not in build_env)
print('PATH[0]:', build_env['PATH'].split(os.pathsep)[0])
print('ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD:', build_env['ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD'])
print('command:', ' '.join(command))
print('poetry version:', subprocess.check_output(['poetry', '--version'], cwd=package, env=build_env, text=True).strip())
result = subprocess.run(command, cwd=package, env=build_env, text=True, capture_output=True, check=False)
print('exit:', result.returncode)
print('===== STDOUT =====')
print(result.stdout, end='')
print('===== STDERR =====')
print(result.stderr, end='')
raise SystemExit(0 if result.returncode == 0 else 1)
