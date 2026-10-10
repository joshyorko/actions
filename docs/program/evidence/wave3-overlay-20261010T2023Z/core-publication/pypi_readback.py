#!/usr/bin/env python3
"""Compare public actions-core PyPI bytes with a downloaded workflow manifest."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

parser = argparse.ArgumentParser()
parser.add_argument('--download-dir', type=Path, required=True)
parser.add_argument('--receipt', type=Path, required=True)
args = parser.parse_args()
manifest = Path(__file__).with_name('actions-core-manifest.sha256')
expected = {}
for line in manifest.read_text(encoding='utf-8').splitlines():
    digest, filename = line.split('  ', 1)
    expected[filename] = digest
with urlopen('https://pypi.org/pypi/actions-core/1.0.3/json', timeout=30) as response:
    data = json.load(response)
assert data['info']['name'] == 'actions-core'
assert data['info']['version'] == '1.0.3'
files = data['urls']
assert {item['filename'] for item in files} == set(expected)
args.download_dir.mkdir(parents=True, exist_ok=True)
verified = []
for item in files:
    filename = item['filename']
    assert item['yanked'] is False
    with urlopen(item['url'], timeout=60) as response:
        payload = response.read()
    actual = hashlib.sha256(payload).hexdigest()
    assert actual == item['digests']['sha256'] == expected[filename]
    (args.download_dir / filename).write_bytes(payload)
    verified.append({
        'filename': filename,
        'bytes': len(payload),
        'sha256': actual,
        'pypi_upload_time': item['upload_time_iso_8601'],
        'yanked': item['yanked'],
        'url': item['url'],
    })
receipt = {
    'observed_at': datetime.now(timezone.utc).isoformat(),
    'package': data['info']['name'],
    'version': data['info']['version'],
    'requires_python': data['info'].get('requires_python'),
    'workflow_manifest': manifest.name,
    'files': sorted(verified, key=lambda item: item['filename']),
    'result': 'PASS',
}
args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print('PASS: PyPI API version and downloaded wheel/sdist bytes match workflow manifest')
for item in receipt['files']:
    print(f"{item['filename']} {item['bytes']} bytes sha256={item['sha256']}")
