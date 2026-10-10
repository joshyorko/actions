from __future__ import annotations
import os, subprocess, sys
from pathlib import Path

package = Path('/workspace/work/actions-mk3-db-savepoint/action_server').resolve()
venv = Path('/workspace/work/actions-mk3-canvas-proof/action_server/.venv').resolve()
env = os.environ.copy()
for key in ('VIRTUAL_ENV', 'POETRY_ACTIVE', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV', 'CONDA_PROMPT_MODIFIER', 'CONDA_SHLVL', 'CONDA_EXE', '_CE_CONDA', '_CE_M', 'PYTHONHOME', 'PYTHONPATH', 'PYTHON_EXE', 'ROBOT_ARTIFACTS', 'ROBOT_ROOT'):
    env.pop(key, None)
env.update({
    'VIRTUAL_ENV': str(venv),
    'PATH': os.pathsep.join((str(venv / 'bin'), env.get('PATH', ''))),
    'POETRY_VIRTUALENVS_CREATE': 'true',
    'POETRY_VIRTUALENVS_IN_PROJECT': 'true',
    'POETRY_VIRTUALENVS_OPTIONS_SYSTEM_SITE_PACKAGES': 'false',
    'PYTHONPATH': str(package / 'src'),
    'ACTIONS_RUNTIME_TEST_PYTHON': str(venv / 'bin/python'),
})
command = ['poetry', 'run', 'python', '-m', 'pytest', '-q', 'tests/contract_tests/test_active_contracts.py::test_runtime_clean_wheels_install_outside_checkout_in_both_uninstall_orders']
print('command:', ' '.join(command))
print('package:', package)
print('prepared venv:', subprocess.check_output(['poetry', 'env', 'info', '--path'], cwd=package, env=env, text=True).strip())
print('RCC module path:', package / 'src/actions/server/bin/rcc-18.19.3')
raise SystemExit(subprocess.run(command, cwd=package, env=env).returncode)
