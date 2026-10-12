"""Curate exact safe source/owner checkpoint copies; no runtime adoption."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

base = Path('/workspace/engineering')
work = base / 'campaign-checkpoint'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=work, text=True).strip() == '843cb16dc071fc764f11f1e0b3b07432dcd04a7d'
destination = work / 'docs/handoffs/evidence/actions-swarm-mk3-20261011-control-memory-continuation'
destination.mkdir(mode=0o700)
folders = [
    'rcc-current8d49-control3-V8-original-import-failure-independent-review',
    'rcc-current8d49-qualified-V9-entry-bootstrap-preparation',
    'rcc-current8d49-V9-config-independent-PREEXECUTION-review',
    'rcc-current8d49-control3-V9-independent-actual-review',
    'rcc-current8d49-control3-V9-original-publish-failure-diagnosis-owned',
    'rcc-upstream-current-reviewed-pure-controls-coordination-20261011',
    'rcc-current8d49-V9-next-version-code-PREPARED-NOTRUN',
    'rcc-memory17-original-mode-admission-failure-independent-review',
    'rcc-memory17-managed700-once2-independent-ACTUAL-review',
    'pr308-corrected-nine-once2-independent-ACTUAL-review',
    'pr308-private-corrected-nine-source-independent-review',
    'pr308-known-nine18-original-ACTUALFAIL-independent-review',
    'pr308-known-nine18-once2-independent-ACTUAL-review',
    'rcc-current8d49-cgroup-reader-observer-independent-SOURCE-review',
    'rcc-current8d49-reader28-independent-ACTUAL-review',
    'completed8d49-five-root-storage-v5-independent-actual-review',
    'completed-current8d49-FULL-storage-original-FAIL-independent-review',
    'completed-current8d49-FULL-partial-relocation-independent-ACTUAL-review',
    'completed-current8d49-FULL-single-copy-independent-ACTUAL-review',
    'pr221-current-e2-sdist-producer-independent-review',
    'pr307-current2314-actual-LIGHT-independent-review',
    'pr307-current2314-fresh-CI-reconciliation',
    'pr307-current2314-OAuth-authority-readonly-proposal',
    'pr307-current7487-independent-source-and-plan-review',
    'pr307-currentc97e-configured-format-source',
    'pr307-currentc97e-original-TOKEN-LIGHT-ACTUALFAIL-independent-diagnosis',
    'obsolete-accepted-environments-four-checkout-readonly-preparation',
    'root-current-live-engineering-20261011-2120',
]
selected = []
for folder in folders:
    owners = sorted((base / folder).glob('OWNERFINAL*.json'))
    assert owners, folder
    selected.extend(owners)
selected += [
    base / 'rcc-current8d49-qualified-V9-entry-bootstrap-preparation/v9_entry_bootstrap.py',
    base / 'rcc-current8d49-qualified-V9-entry-bootstrap-preparation/owned_native_entry_v9.py',
    base / 'pr308-nine-real-private-catalog-lock-source-successor-final-v4-NOTRUN/test_current_managed_reload_sqlite_pool_barriers_successor_v2.py',
    base / 'rcc-next-native-cgroup-admission-source-PREPARED-NOTRUN/proposed_cgroup_memory_state_v1_NOTRUN.py',
    base / 'rcc-next-native-cgroup-admission-source-PREPARED-NOTRUN/test_proposed_cgroup_memory_state_NOTRUN.py',
    base / 'rcc-current8d49-cgroup-reader-observer-private-SOURCE-PREPARED-NOTRUN/cgroup_memory_reader_observer_v1_NOTRUN.py',
    base / 'rcc-current8d49-cgroup-reader-observer-private-SOURCE-PREPARED-NOTRUN/test_cgroup_memory_reader_observer_v1_NOTRUN.py',
]
rows = []
for index, path in enumerate(selected, 1):
    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode) and not path.is_symlink()
    assert metadata.st_uid == os.getuid() == 1000 and metadata.st_gid == os.getgid() == 1000
    body = path.read_bytes()
    assert len(body) < 100000, path
    assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|X-Amz-Signature=|sig=[A-Za-z0-9%]{32,})', body), path
    if path.suffix == '.json':
        json.loads(body)
    target = destination / (str(index).zfill(2) + '-' + path.name)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    assert target.read_bytes() == body
    rows.append({'source': str(path), 'source_mode': oct(stat.S_IMODE(metadata.st_mode)), 'path': str(target.relative_to(work)), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'scope': 'Exact original historical owner or private source checkpoint; no runtime adoption or evidence promotion'})
manifest = {'schema': 1, 'parent': '843cb16dc071fc764f11f1e0b3b07432dcd04a7d', 'copies': rows, 'files': len(rows), 'bytes': sum(row['bytes'] for row in rows), 'excluded': ['private configurations', 'raw stdout/stderr/JUnit/robolog', 'full inventories', 'binaries', 'archives', 'credential material'], 'historical_source_closure': 'All old84/wave1830/exact43 and13 source dependencies retained unchanged; this closure supplements them and is not an executable acceptance bundle'}
path = destination / 'exact-safe-original-source-and-owner-copy-manifest.json'
body = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
with path.open('xb') as stream:
    os.chmod(path, 0o600)
    stream.write(body)
    stream.flush()
    os.fsync(stream.fileno())
print(json.dumps({'manifest': str(path), 'files': len(rows), 'bytes': manifest['bytes'], 'manifest_sha256': hashlib.sha256(body).hexdigest()}))
