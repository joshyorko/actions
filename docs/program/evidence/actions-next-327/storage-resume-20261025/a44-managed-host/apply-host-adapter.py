"""Verify stock files before applying the disclosed local test-host adaptation."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
host=Path(sys.argv[1]).resolve()
entries=json.loads((root/'changed-file-hashes.json').read_text())
for name,entry in entries.items():
    target=host/name
    if entry['stock_sha256'] is None:
        assert not target.exists(), 'new adapter file already exists'
    else:
        assert hashlib.sha256(target.read_bytes()).hexdigest()==entry['stock_sha256'], name
    assert hashlib.sha256((root/'host-files'/name).read_bytes()).hexdigest()==entry['adapted_sha256'], name
for name in entries:
    target=host/name;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes((root/'host-files'/name).read_bytes())
print('Applied four verified test-host files; no install, credentials, grants or server launch.')
