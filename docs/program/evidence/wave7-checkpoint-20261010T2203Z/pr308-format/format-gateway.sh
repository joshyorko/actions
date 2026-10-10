#!/usr/bin/env bash
set -euo pipefail
cd /workspace/work/actions-mk3-rcc-candidate-version/action_server
exec /workspace/work/actions-mk3-pr302/action_server/.venv/bin/ruff format --config ../devutils/ruff.toml "$@" tests/action_server_tests/test_dakota_rcc_acceptance.py
