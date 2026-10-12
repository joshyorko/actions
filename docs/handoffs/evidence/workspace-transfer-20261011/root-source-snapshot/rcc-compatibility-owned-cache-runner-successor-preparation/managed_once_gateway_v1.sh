#!/bin/bash
set -euo pipefail
source /workspace/actions-cloud/activate.sh
export PYTEST_XDIST_AUTO_NUM_WORKERS=2
/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python /workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation/managed_metadata_only_preflight.py
exec /workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python /workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation/launch_one_version_v1.py "$@"
