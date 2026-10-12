"""Future configured source full body; preparation only, not executed."""
import hashlib
import json
import os
import sys
from pathlib import Path
import toolkit

ROOT=Path('/workspace/engineering/captured-child-cleanup')
assert toolkit.REPOSITORY_ROOT==ROOT
sys.path.insert(0,'/workspace/engineering/pr313-actual300-refresh')
from verify_current_source_v2 import check,bind

OWNER=Path('/workspace/engineering/pr313-actual300-refresh/OWNERFINAL-pr313-current-actual300-ordinary-refresh-SOURCE_LIGHT.json')
assert bind(OWNER)['sha256']=='0171ef23a625807d6f09dabcc25b9695ee622ca570f8b8800a75433c7a1bcbbb'
for row in json.loads(OWNER.read_bytes())['bindings']:assert bind(row['path'])==row
check()
assert os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
assert os.environ.get('ACTIONS_REAL_RCC_ARTIFACT_TEST')!='1'
toolkit.poetry('action_server','run','invoke','test-not-integration')
