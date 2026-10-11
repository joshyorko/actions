#!/bin/bash
set -euo pipefail
REPO=/workspace/work/actions-mk3-wave9-pr310-typing
ENV=/workspace/work/actions-mk3-pr302/action_server/.venv
unset VIRTUAL_ENV CONDA_PREFIX POETRY_ACTIVE PYTHONHOME PYTHONPATH
export VIRTUAL_ENV="$ENV"
export PATH="$ENV/bin:/workspace/actions-cloud/bin:/usr/bin:/bin"
cd "$REPO/action_server"
python - <<'PY'
import pathlib, sys, mypy, pytest, ruff
print('python', sys.version.split()[0])
print('sys.prefix', sys.prefix)
for module in (mypy, pytest, ruff): print(module.__name__, pathlib.Path(module.__file__).resolve())
PY
python -m pytest tests/action_server_tests/test_dakota_workitems_native_ui_acceptance.py -k 'failed_authorization_denial_stage_is_failed_not_not_run or successful_authorization_denial_stage_clears_not_run or normal_stage_does_not_clear_authorization_denial_not_run' -q
python -m mypy --follow-imports=silent --show-column-numbers --namespace-packages --explicit-package-bases src tests
python -m ruff check src tests
python -m ruff format --check --config ruff.toml --exclude=_static_contents.py,_oauth2_config.py src tests
python -m isort --check src tests
