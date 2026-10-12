"""Check the already reviewed managed activation before the one adopted launcher."""
import hashlib
import json
import os
import sys
from pathlib import Path

O=Path(__file__).resolve().parent
sys.path[:0]=[str(O),'/workspace/engineering/rcc-current8d49-private-V8-real-fixture-mode-successor','/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation']
from runner_contracts_v3 import need


def activation_guard():
    path=Path('/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/frozen-current8d49-source-LIGHT-inputs-v3.json')
    raw=path.read_bytes()
    need(hashlib.sha256(raw).hexdigest()=='81f52920b50e67619b3bb418a7c1034a2106ec52f4badd71b9d85e29b7376820','MANAGED_ACTIVATION_CONFIG_IDENTITY')
    cfg=json.loads(raw)
    need(len(cfg['expected_activation_exports'])==18 and all(os.environ.get(k)==v for k,v in cfg['expected_activation_exports'].items()),'MANAGED_ACTIVATION_EXPORTS18')
    need(os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin','MANAGED_ACTIVATION_PRIMARY_PATH')
    need('PYTEST_ADDOPTS' not in os.environ and not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE'),'MANAGED_NO_INHERITED_TEST_OR_OPTIMIZE')
    need(all(k not in os.environ for k in cfg['forbidden_actual_operator_exports']),'MANAGED_NO_OPERATOR_OVERRIDE')


if __name__=='__main__':
    activation_guard()
    from launch_one_version_v8 import main
    raise SystemExit(main())
