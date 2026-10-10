"""Compare inherited Runtime lint and full-suite failures at the exact base."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path('/workspace/work/actions-mk3-db-savepoint-base').resolve()
PACKAGE = ROOT / 'action_server'
SOURCE = PACKAGE / 'src'
PYTHON = Path('/workspace/work/actions-mk3-canvas-proof/action_server/.venv/bin/python')
EXPECTED = {
    'pyproject.toml': 'be4011d3915e8838249546c70ae30420dadfb0d08c19b59970d8980332c7573f',
    'poetry.lock': '5d6acb65ba220211d1da020c78c51a5ea89465f2bbedc99aaf72319b862914e5',
}
assert (ROOT / '.git').exists() or (ROOT / '.git').is_file()
for filename, digest in EXPECTED.items():
    assert hashlib.sha256((PACKAGE / filename).read_bytes()).hexdigest() == digest

env = os.environ.copy()
env.pop('ACTIONS_RUNTIME_TEST_PYTHON', None)
env['PYTHONPATH'] = str(SOURCE)
env['PATH'] = os.pathsep.join((str(PYTHON.parent), env.get('PATH', '')))
probe = subprocess.run(
    [str(PYTHON), '-c', "import actions.server._database as d, sys; print('python:', sys.executable); print('module:', d.__file__); assert str(d.__file__).startswith(sys.argv[1])", str(SOURCE)],
    cwd=PACKAGE, env=env, text=True, capture_output=True, check=True,
)
print('base:', ROOT)
print('head:', subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip())
print(probe.stdout, end='')

commands = [
    ('base-lint', [str(PYTHON), '-m', 'invoke', 'lint']),
    ('base-inherited-failures', [
        str(PYTHON), '-m', 'pytest', '-q', '-n', 'auto',
        'tests/action_server_tests/test_package.py::test_package_metadata_oauth2_secrets',
        'tests/action_server_tests/test_package.py::test_package_metadata_secrets',
        'tests/action_server_tests/test_package.py::test_package_metadata_api',
        'tests/action_server_tests/test_server.py::test_import_action_server_strategies[no-conda]',
        'tests/action_server_tests/test_server.py::test_import_default_value',
        'tests/contract_tests/test_active_contracts.py::test_runtime_clean_wheels_install_outside_checkout_in_both_uninstall_orders',
    ]),
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
