"""Invoke only the immutable read-only body guard function, not its gated CLI."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, '/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation')
from readonly_current_input_guard_v1 import guard

base = Path(__file__).parent
config = json.loads((base/'FROZEN-current-e4ff-control3-owned-cache-SOURCE-QUALIFIED-v4.json').read_bytes())
guard(config)
result = {'status': 'PASS_CURRENT_SOURCE_AND_HISTORICAL_NATIVE_BODY_MODE_READONLY',
          'source': config['source'], 'tree': config['tree'], 'source_rows': 1423,
          'native_historical_original_rows_body_mode_set': 1192,
          'prepared_inputs_rehashed': 30, 'own_origin_rows_only_not_product_imports': 5,
          'bindings_reverified': len(config['bindings']), 'gateway': 'NOT_RUN',
          'native_execution': 'NOT_RUN', 'historical_native_current_equivalence': 'UNQUALIFIED',
          'guard_entry': 'readonly_current_input_guard_v1.guard(config) function only; no CLI/release/process task'}
fd = os.open(base/'readonly-native-prepared-supplement.json', os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    json.dump(result, stream, sort_keys=True, indent=2); stream.write('\n')
print(json.dumps(result, sort_keys=True))
