"""Read-only config/source/original-body check; never executes product or native code."""
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

CODE = Path('/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation')
sys.path.insert(0, str(CODE))
from actual_transport_v7 import BINARIES, SOURCE, TREE, read_bound, require_release
from owned_cache_policy_v1 import cache_plan, encoded, sha
from runner_contracts_v3 import AdmissionFailure, need

BASE = Path(__file__).parent
config_path = BASE/'FROZEN-current-e4ff-control3-owned-cache-SOURCE-QUALIFIED-v4.json'
raw = config_path.read_bytes()
config = json.loads(raw)
need(config['source'] == SOURCE and config['tree'] == TREE, 'SOURCE_IDENTITY')
need(len(config['source_body_modes']) == 1423 and len(config['native_original_members']) == 1192,
     'MEASURED_COUNTS')
need(len(config['prepared_inputs']) == 30 and len(config['concrete_own_origins']) == 5, 'PREPARED_SCOPE')
root = Path(config['source_root'])
need(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip() == SOURCE
     and subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=root).decode().strip() == TREE
     and not subprocess.check_output(['git', 'status', '--porcelain'], cwd=root), 'CURRENT_GIT_CLEAN')
for row in config['source_body_modes']:
    path = root/row['path']
    body = os.readlink(path).encode() if row['mode'] == '120000' else path.read_bytes()
    need(len(body) == row['bytes'] and sha(body) == row['sha256']
         and stat.S_IMODE(path.lstat().st_mode) == row['fs_mode'], 'CURRENT_COMPLETE_SOURCE_BYTES_MODE')
for row in config['bindings']:
    read_bound(row)
plan = cache_plan(config, 'control3', SOURCE, TREE, BINARIES)
need(not Path(config['owned_root']).exists() and not Path(config['owned_root']).is_symlink(),
     'ACTUAL_ONCE_ROOT_NOT_CREATED')
blocked = False
try:
    require_release(config, {}, sha(raw), 'control3')
except AdmissionFailure:
    blocked = True
need(blocked, 'ROOT_AND_CONFIG_REVIEW_STILL_REQUIRED')
result = {'status': 'CURRENT_CONFIG_SOURCE_QUALIFIED_NATIVE_NOT_RUN',
          'config': {'path': str(config_path), 'bytes': len(raw), 'sha256': sha(raw), 'mode': '0o600'},
          'source': SOURCE, 'tree': TREE, 'clean': True, 'source_body_mode_files': 1423,
          'config_bindings_reverified': len(config['bindings']), 'native_original_member_rows': 1192,
          'prepared_input_rows': 30, 'concrete_own_origins': 5, 'cache_plan_sha256': sha(encoded(plan)),
          'actual_once_root_absent': True, 'root_and_current_config_review_still_required': blocked,
          'operations': ['Git read-only', 'filesystem/body/SHA/mode reads', 'pure metadata validation'],
          'native_execution': 'NOT_RUN', 'product_imports': 'NONE', 'gateway': 'NOT_RUN'}
fd = os.open(BASE/'qualified-config-metadata-proof.json', os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    json.dump(result, stream, sort_keys=True, indent=2); stream.write('\n')
print(json.dumps(result, sort_keys=True))
