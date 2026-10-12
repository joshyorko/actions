"""Read-only historical Git and current Git/filesystem body/mode guards."""
import hashlib
import os
from pathlib import Path
import stat
import subprocess

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=60)

def snapshot(root, head):
    entries = git(root, 'ls-tree', '-rz', head).split(b'\0')
    rows = []
    for entry in entries:
        if not entry:
            continue
        header, path = entry.split(b'\t', 1)
        mode, kind, oid = header.decode('ascii').split()
        assert kind == 'blob'
        rows.append({'path': path.decode('utf-8'), 'mode': mode, 'oid': oid})
    data = subprocess.run(['git', '-C', str(root), 'cat-file', '--batch'],
                          input=b''.join((r['oid'] + '\n').encode() for r in rows),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=60, check=True).stdout
    pos = 0
    for row in rows:
        end = data.index(b'\n', pos)
        oid, kind, size = data[pos:end].decode('ascii').split()
        assert oid == row['oid'] and kind == 'blob'
        size = int(size)
        body = data[end + 1:end + 1 + size]
        assert len(body) == size and data[end + 1 + size:end + 2 + size] == b'\n'
        row['sha256'] = hashlib.sha256(body).hexdigest()
        row['bytes'] = size
        pos = end + 2 + size
    assert pos == len(data)
    return rows

def validate(config, progress):
    root = Path(config['source_root'])
    assert git(root, 'rev-parse', config['source'] + '^{tree}').decode().strip() == config['tree']
    historical = snapshot(root, config['source'])
    projection = lambda row: {k: row[k] for k in ('path', 'mode', 'sha256')}
    assert [projection(r) for r in historical] == [projection(r) for r in config['source_body_modes']]
    assert progress['source_root'] == str(root)
    assert progress['historical_head'] == config['source'] and progress['historical_tree'] == config['tree']
    assert git(root, 'rev-parse', 'HEAD').decode().strip() == progress['head']
    assert git(root, 'rev-parse', 'HEAD^{tree}').decode().strip() == progress['tree']
    assert not git(root, 'status', '--porcelain')
    subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', config['source'], progress['head']], check=True, timeout=60)
    current = snapshot(root, progress['head'])
    assert len(current) == progress['complete_count']
    assert current == [{k: r[k] for k in ('path', 'mode', 'oid', 'sha256', 'bytes')} for r in progress['body_modes']]
    for row in progress['body_modes']:
        path = root / row['path']
        info = path.lstat()
        assert stat.S_IMODE(info.st_mode) == row['fs_mode']
        if row['mode'] == '120000':
            assert stat.S_ISLNK(info.st_mode)
            body = os.readlink(path).encode()
        else:
            assert stat.S_ISREG(info.st_mode) and not path.is_symlink()
            body = path.read_bytes()
        assert len(body) == row['bytes'] and hashlib.sha256(body).hexdigest() == row['sha256']
