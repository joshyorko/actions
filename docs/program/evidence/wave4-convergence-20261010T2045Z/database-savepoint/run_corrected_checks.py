"""Run Runtime checks through RCC with the manifest-matched Poetry environment."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path('/workspace/work/actions-mk3-db-savepoint').resolve()
PACKAGE = ROOT / 'action_server'
SOURCE = PACKAGE / 'src'
PREPARED = Path('/workspace/work/actions-mk3-canvas-proof/action_server/.venv').resolve()
PYTHON = PREPARED / 'bin/python'
EXPECTED = {
    'pyproject.toml': 'be4011d3915e8838249546c70ae30420dadfb0d08c19b59970d8980332c7573f',
    'poetry.lock': '5d6acb65ba220211d1da020c78c51a5ea89465f2bbedc99aaf72319b862914e5',
}
ACTIVE_ENVIRONMENT_VARIABLES = (
    'VIRTUAL_ENV', 'POETRY_ACTIVE', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV',
    'CONDA_PROMPT_MODIFIER', 'CONDA_SHLVL', 'CONDA_EXE', '_CE_CONDA', '_CE_M',
    'PYTHONHOME', 'PYTHONPATH', 'PYTHON_EXE', 'ROBOT_ARTIFACTS', 'ROBOT_ROOT',
)
for name, digest in EXPECTED.items():
    assert hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() == digest
    assert hashlib.sha256((Path('/workspace/work/actions-mk3-canvas-proof/action_server') / name).read_bytes()).hexdigest() == digest

env = os.environ.copy()
for name in ACTIVE_ENVIRONMENT_VARIABLES:
    env.pop(name, None)
env.update({
    'VIRTUAL_ENV': str(PREPARED),
    'PATH': os.pathsep.join((str(PREPARED / 'bin'), env.get('PATH', ''))),
    'POETRY_VIRTUALENVS_CREATE': 'true',
    'POETRY_VIRTUALENVS_IN_PROJECT': 'true',
    'POETRY_VIRTUALENVS_OPTIONS_SYSTEM_SITE_PACKAGES': 'false',
    'PYTHONPATH': str(SOURCE),
    'ACTIONS_RUNTIME_TEST_PYTHON': str(PYTHON),
})
print('outer RCC Python:', sys.executable)
print('Poetry executable:', subprocess.check_output(['which', 'poetry'], env=env, text=True).strip())
print('manifest hashes:', EXPECTED)

probe = subprocess.run(
    ['poetry', 'run', 'python', '-c', "import sys, actions.server._database as d; print('python:', sys.executable); print('prefix:', sys.prefix); print('database_module:', d.__file__); assert str(sys.prefix).startswith(sys.argv[1]); assert str(d.__file__).startswith(sys.argv[2])", str(PREPARED), str(SOURCE)],
    cwd=PACKAGE, env=env, text=True, capture_output=True, check=True,
)
print('Poetry env path:', subprocess.check_output(['poetry', 'env', 'info', '--path'], cwd=PACKAGE, env=env, text=True).strip())
print(probe.stdout, end='')
print('Ruff:', subprocess.check_output(['poetry', 'run', 'ruff', '--version'], cwd=PACKAGE, env=env, text=True).strip())
print('ACTIONS_RUNTIME_TEST_PYTHON:', env['ACTIONS_RUNTIME_TEST_PYTHON'])

commands = [
    ('corrected-focused', ['poetry', 'run', 'python', '-m', 'pytest', '-q', 'tests/action_server_tests/test_database.py::test_nested_transaction_savepoint_start_failure_preserves_error_and_counter', 'tests/action_server_tests/test_database.py::test_database_transactions_nested']),
    ('corrected-inherited-failures', ['poetry', 'run', 'python', '-m', 'pytest', '-q', '-n', 'auto', 'tests/action_server_tests/test_package.py::test_package_metadata_oauth2_secrets', 'tests/action_server_tests/test_package.py::test_package_metadata_secrets', 'tests/action_server_tests/test_package.py::test_package_metadata_api', 'tests/action_server_tests/test_server.py::test_import_action_server_strategies[no-conda]', 'tests/action_server_tests/test_server.py::test_import_default_value', 'tests/contract_tests/test_active_contracts.py::test_runtime_clean_wheels_install_outside_checkout_in_both_uninstall_orders']),
    ('corrected-lint', ['poetry', 'run', 'invoke', 'lint']),
    ('corrected-typecheck', ['poetry', 'run', 'invoke', 'typecheck']),
]
results = []
for name, command in commands:
    log = Path('/workspace/work/actions-mk3-evidence/database-savepoint') / f'{name}.log'
    print('RUN', name, *command, flush=True)
    with log.open('w', encoding='utf-8') as stream:
        run = subprocess.run(command, cwd=PACKAGE, env=env, stdout=stream, stderr=subprocess.STDOUT, check=False)
    results.append((name, run.returncode, str(log)))
    print('RESULT', name, run.returncode, log, flush=True)
print('CHECK_RESULTS:')
for result in results:
    print(*result)
if any(code != 0 for _, code, _ in results):
    raise SystemExit(1)
