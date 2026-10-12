import hashlib
import json
import shutil
from pathlib import Path

base = Path('/workspace/engineering')
previous = json.loads((base / 'existing-workspace-scratch-capacity-recovery-batch13.json').read_bytes())
private = Path('/dev/shm/actions-completed-scratch-recovery-batch14/private-complete-inventory-and-recovery.json')
records = json.loads(private.read_bytes())['records']
def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
assert len(records) == 2
assert [Path(r['original_namespace']).name for r in records] == ['6626d6008afef362', '1748c6a354c4f0e0']
archives = []
for record in records:
    assert not Path(record['original_namespace']).exists()
    actual = binding(Path(record['archive']))
    assert actual['bytes'] == record['archive_bytes'] and actual['sha256'] == record['archive_sha256']
    archives.append({k: record[k] for k in ('original_namespace', 'archive', 'archive_bytes', 'archive_sha256', 'verified_members')})
    archives[-1].update(archive_verified_before_original_removal=True, expanded_removed=True)
previous.update(archives=archives, private_inventory_binding=binding(private),
                recovery_script_binding=binding(Path('/tmp/actions-capacity-recovery-batch14.py')),
                terminal_log_binding=binding(Path('/tmp/actions-capacity-recovery-batch14.log')),
                recorded_members=sum(r['verified_members'] for r in records),
                workspace_free_bytes_after=shutil.disk_usage('/workspace').free,
                preserved='Prior31 archives+13 indices/V5 runner/failed563d baseline require separate independent reference check; no historical requalification',
                existing_mount_allocation='Two archives preserved on already existing /dev/shm mount; no infrastructure provisioned. Distinct unused /tmp staging directory.')
out = base / 'existing-workspace-scratch-capacity-recovery-batch14.json'
data = (json.dumps(previous, indent=2) + '\n').encode()
with out.open('xb') as stream:
    stream.write(data)
print(json.dumps(binding(out)))
