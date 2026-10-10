from __future__ import annotations
import hashlib, os, subprocess, sys
from pathlib import Path

root = Path('/workspace/work/actions-mk3-db-savepoint')
package = root / 'action_server'
source = package / 'src'
venv = Path('/workspace/work/actions-mk3-canvas-proof/action_server/.venv').resolve()
python = venv / 'bin/python'
expected = {
    'pyproject.toml': 'be4011d3915e8838249546c70ae30420dadfb0d08c19b59970d8980332c7573f',
    'poetry.lock': '5d6acb65ba220211d1da020c78c51a5ea89465f2bbedc99aaf72319b862914e5',
}
for filename, digest in expected.items():
    assert hashlib.sha256((package / filename).read_bytes()).hexdigest() == digest

env = os.environ.copy()
for key in ('VIRTUAL_ENV', 'POETRY_ACTIVE', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV', 'CONDA_PROMPT_MODIFIER', 'CONDA_SHLVL', 'CONDA_EXE', '_CE_CONDA', '_CE_M', 'PYTHONHOME', 'PYTHONPATH', 'PYTHON_EXE', 'ROBOT_ARTIFACTS', 'ROBOT_ROOT'):
    env.pop(key, None)
env.update({
    'VIRTUAL_ENV': str(venv),
    'PATH': os.pathsep.join((str(venv / 'bin'), env.get('PATH', ''))),
    'POETRY_VIRTUALENVS_CREATE': 'true',
    'POETRY_VIRTUALENVS_IN_PROJECT': 'true',
    'POETRY_VIRTUALENVS_OPTIONS_SYSTEM_SITE_PACKAGES': 'false',
    'PYTHONPATH': str(source),
    'ACTIONS_RUNTIME_TEST_PYTHON': str(python),
})
probe = subprocess.run(['poetry', 'run', 'python', '-c', "import sys, actions.server._database as d; print(sys.executable); print(d.__file__); assert str(d.__file__).startswith(sys.argv[1])", str(source)], cwd=package, env=env, text=True, capture_output=True, check=True)
print('Runtime imports:'); print(probe.stdout, end='')
print('Poetry environment:', subprocess.check_output(['poetry', 'env', 'info', '--path'], cwd=package, env=env, text=True).strip())
print('ACTIONS_RUNTIME_TEST_PYTHON:', env['ACTIONS_RUNTIME_TEST_PYTHON'])
commands = [
    ('final-focused', ['poetry', 'run', 'python', '-m', 'pytest', '-q', 'tests/action_server_tests/test_database.py::test_nested_transaction_savepoint_start_failure_preserves_error_and_counter', 'tests/action_server_tests/test_database.py::test_database_transactions_nested']),
    ('final-database-suite', ['poetry', 'run', 'python', '-m', 'pytest', '-q', 'tests/action_server_tests/test_database.py', 'tests/action_server_tests/test_database_shared.py']),
    ('final-lint', ['poetry', 'run', 'invoke', 'lint']),
    ('final-typecheck', ['poetry', 'run', 'invoke', 'typecheck']),
]
results = []
for name, cmd in commands:
    log = Path('/workspace/work/actions-mk3-evidence/database-savepoint') / f'{name}.log'
    print('RUN', name, *cmd, flush=True)
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run(cmd, cwd=package, env=env, stdout=stream, stderr=subprocess.STDOUT, check=False)
    results.append((name, result.returncode, str(log)))
    print('RESULT', name, result.returncode, log, flush=True)
print('CHECK_RESULTS:')
for result in results:
    print(*result)
if any(code for _, code, _ in results):
    raise SystemExit(1)
