from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

repo = Path("/workspace/work/actions-mk3-rcc-candidate-version").resolve()
prepared_package = Path("/workspace/work/actions-mk3-pr302/action_server").resolve()
python = prepared_package / ".venv" / "bin" / "python"
source_roots = [
    repo / "action_server" / "src",
    repo / "actions" / "src",
    repo / "actions-http-helper" / "src",
    repo / "work-items" / "src",
    repo / "devutils" / "src",
]
temp_root = Path("/workspace/work/actions-mk3-evidence/runtime-rcc-candidate-version/prepared-suite-tmp")
temp_root.mkdir(parents=True, exist_ok=True)

env = {
    "HOME": str(temp_root / "home"),
    "TMPDIR": str(temp_root / "tmp"),
    "TEMP": str(temp_root / "tmp"),
    "TMP": str(temp_root / "tmp"),
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": os.pathsep.join((str(python.parent), "/usr/bin", "/bin")),
    "VIRTUAL_ENV": str(prepared_package / ".venv"),
    "PYTHONPATH": os.pathsep.join(map(str, source_roots)),
    "PYTHONNOUSERSITE": "1",
}
for key in ("HOME", "TMPDIR", "TEMP", "TMP"):
    Path(env[key]).mkdir(parents=True, exist_ok=True)

expected_imports = {
    "actions": str(repo / "actions" / "src" / "actions"),
    "actions.server._rcc_runtime_adapter": str(
        repo / "action_server" / "src" / "actions" / "server"
    ),
}
preflight_lines = [
    "import importlib, os, sys",
    f"expected = {expected_imports!r}",
    "for name, prefix in expected.items():",
    "    module = importlib.import_module(name)",
    "    origin = getattr(module, '__file__', None)",
    "    if origin is None or not os.path.realpath(origin).startswith(os.path.realpath(prefix)):",
    "        raise SystemExit(f'wrong target import: {name} -> {origin}')",
    "print('TARGET_PYTHON=' + sys.executable)",
    "print('TARGET_PREFIX=' + sys.prefix)",
    "print('TARGET_ACTIONS=' + importlib.import_module('actions').__file__)",
    "print('TARGET_RUNTIME_ADAPTER=' + importlib.import_module('actions.server._rcc_runtime_adapter').__file__)",
    "print('TARGET_PSUTIL=' + importlib.import_module('psutil').__file__)",
    "print('TARGET_PYTEST=' + importlib.import_module('pytest').__file__)",
]
preflight = "\n".join(preflight_lines)
print("Prepared Runtime manifest matched by pyproject.toml and poetry.lock SHA-256.", flush=True)
print("Prepared Python:", python, flush=True)
subprocess.run([str(python), "-c", preflight], cwd=repo / "action_server", env=env, check=True)
command = [
    str(python), "-m", "pytest", "--noconftest", "-c", "/dev/null",
    "-p", "no:cacheprovider", f"--basetemp={temp_root / 'pytest'}",
    "--disable-warnings", "-m", "not integration_test and not real_rcc",
    str(repo / "action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py"),
    "-q",
]
print("UNIT_COMMAND=" + json.dumps(command), flush=True)
subprocess.run(command, cwd=repo / "action_server", env=env, check=True)
