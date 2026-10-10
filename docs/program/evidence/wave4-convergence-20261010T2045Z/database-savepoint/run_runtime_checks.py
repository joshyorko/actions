"""Run configured Runtime checks through the existing RCC task environment."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/workspace/work/actions-mk3-db-savepoint").resolve()
PACKAGE = ROOT / "action_server"
SOURCE = PACKAGE / "src"
PYTHON = Path("/workspace/work/actions-mk3-canvas-proof/action_server/.venv/bin/python")
PREPARED_SOURCE = Path("/workspace/work/actions-mk3-canvas-proof/action_server/src")
EXPECTED_MANIFESTS = {
    "pyproject.toml": "be4011d3915e8838249546c70ae30420dadfb0d08c19b59970d8980332c7573f",
    "poetry.lock": "5d6acb65ba220211d1da020c78c51a5ea89465f2bbedc99aaf72319b862914e5",
}

for name, expected in EXPECTED_MANIFESTS.items():
    for package_root in (PACKAGE, Path("/workspace/work/actions-mk3-canvas-proof/action_server")):
        actual = hashlib.sha256((package_root / name).read_bytes()).hexdigest()
        assert actual == expected, f"prepared environment manifest mismatch: {package_root / name}: {actual}"
    assert hashlib.sha256((PREPARED_SOURCE.parent / name).read_bytes()).hexdigest() == expected

child_env = os.environ.copy()
child_env.pop("ACTIONS_RUNTIME_TEST_PYTHON", None)
child_env["PYTHONPATH"] = str(SOURCE)
child_env["PATH"] = os.pathsep.join((str(PYTHON.parent), child_env.get("PATH", "")))

origin_probe = subprocess.run(
    [str(PYTHON), "-c", "import actions.server._database as d, sys; print('package_python:', sys.executable); print('package_prefix:', sys.prefix); print('database_module:', d.__file__); assert str(d.__file__).startswith(sys.argv[1])", str(SOURCE)],
    cwd=PACKAGE,
    env=child_env,
    text=True,
    capture_output=True,
    check=True,
)
print("RCC wrapper Python:", sys.executable)
print("prepared package Python:", PYTHON)
print(origin_probe.stdout, end="")
print("manifest hashes:", EXPECTED_MANIFESTS)

commands = [
    (
        "focused-red-to-green",
        [
            str(PYTHON), "-m", "pytest", "-q",
            "tests/action_server_tests/test_database.py::test_nested_transaction_savepoint_start_failure_preserves_error_and_counter",
            "tests/action_server_tests/test_database.py::test_database_transactions_nested",
        ],
    ),
    (
        "database-tests",
        [str(PYTHON), "-m", "pytest", "-q", "tests/action_server_tests/test_database.py", "tests/action_server_tests/test_database_shared.py"],
    ),
    ("runtime-lint", [str(PYTHON), "-m", "invoke", "lint"]),
    ("runtime-typecheck", [str(PYTHON), "-m", "invoke", "typecheck"]),
    ("runtime-full-non-integration", [str(PYTHON), "-m", "invoke", "test-not-integration"]),
]
results = []
for name, command in commands:
    print(f"RUN {name}: {' '.join(command)}", flush=True)
    log = Path("/workspace/work/actions-mk3-evidence/database-savepoint") / f"{name}.log"
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.run(command, cwd=PACKAGE, env=child_env, stdout=stream, stderr=subprocess.STDOUT, check=False)
    results.append((name, process.returncode, str(log)))
    print(f"RESULT {name}: exit={process.returncode} log={log}", flush=True)

print("CHECK_RESULTS:")
for result in results:
    print(*result)
if any(code != 0 for _, code, _ in results):
    raise SystemExit(1)
