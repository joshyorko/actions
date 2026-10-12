import hashlib
import json
from pathlib import Path

OUT = Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned')


def bind(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


predecessor = OUT / 'OWNERFINAL-original-cleanup-deterministic-control.json'
result = json.loads(predecessor.read_bytes())
active_log = OUT / 'freeze-original.private.log'
original_binding = next(item for item in result['bindings'] if item['path'] == str(active_log))
assert original_binding['bytes'] == 0
assert original_binding['sha256'] == hashlib.sha256(b'').hexdigest()
for item in result['bindings']:
    if item['path'] != str(active_log):
        assert bind(Path(item['path'])) == item
result['schema'] = 'original-cleanup-private-deterministic-control-v2'
result['bindings'] = [item for item in result['bindings'] if item['path'] != str(active_log)]
result['bindings'] += [bind(active_log), bind(predecessor), bind(Path(__file__))]
result['construction_draft_disposition'] = {
    'predecessor': bind(predecessor),
    'status': 'RETAINED_UNANNOUNCED_DRAFT_INVALID_ACTIVE_CONSTRUCTOR_LOG_BINDING',
    'original_active_log_binding': original_binding,
    'reason': 'Constructor bound its zero-byte redirected output before printing the final result; the immutable successor binds the now terminal log. No target function or test was rerun, no source/log bytes rewritten.',
    'focused_control_executions_unchanged': 1,
}
for item in result['bindings']:
    assert bind(Path(item['path'])) == item
final = OUT / 'OWNERFINAL-original-cleanup-deterministic-control-v2.json'
with final.open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
final.chmod(0o600)
print(json.dumps(bind(final)))
