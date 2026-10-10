#!/usr/bin/env bash
set -euo pipefail
# The first RCC attempt lacked psutil in the runner process. This wrapper
# explicitly re-enters the package venv after clearing RCC environment markers;
# its behavior inside an RCC task still requires a reviewed no-service preflight.
unset VIRTUAL_ENV POETRY_ACTIVE CONDA_PREFIX CONDA_DEFAULT_ENV CONDA_PROMPT_MODIFIER
unset CONDA_SHLVL CONDA_EXE _CE_CONDA _CE_M PYTHONHOME PYTHONPATH PYTHON_EXE
unset ROBOT_ARTIFACTS ROBOT_ROOT
exec /workspace/work/actions-mk3-pr302/action_server/.venv/bin/python "$@"
