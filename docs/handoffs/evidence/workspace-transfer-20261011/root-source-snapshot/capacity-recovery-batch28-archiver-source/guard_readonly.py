"""Data-only guards: do not import repository code, execute tools, or mutate inputs."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def mode(value):
    return int(value, 8) if isinstance(value, str) else value


def exact_file(row):
    p = Path(row['path'])
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    assert s.st_size == row['bytes'] and digest(p) == row['sha256']
    assert stat.S_IMODE(s.st_mode) == mode(row['mode'])
    for key in ('uid', 'gid'):
        if key in row:
            assert getattr(s, 'st_' + key) == row[key]


def protected(config):
    root = Path(config['source_root'])
    output = subprocess.check_output(['git', '--no-optional-locks', '-C', str(root), 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines()
    assert output == [config['source_head'], config['source_tree']]
    assert not subprocess.check_output(['git', '--no-optional-locks', '-C', str(root), 'status', '--porcelain=v1'])
    tracked = subprocess.check_output(['git', '--no-optional-locks', '-C', str(root), 'ls-tree', '-rz', config['source_head']]).split(b'\0')
    typed = []
    for entry in tracked:
        if entry:
            left, path = entry.split(b'\t', 1)
            bits = left.decode().split()
            typed.append((bits[0], bits[2], path.decode()))
    assert len(typed) == 1426 and typed == [(r['mode'], r['oid'], r['path']) for r in config['source_rows']]
    for row in config['source_rows']:
        p = root / row['path']
        body = os.readlink(p).encode() if row['mode'] == '120000' else p.read_bytes()
        assert len(body) == row['bytes'] and hashlib.sha256(body).hexdigest() == row['sha256']
        assert stat.S_IMODE(p.lstat().st_mode) == row['fs_mode']
    for path, expected in config['prepared30'].items():
        assert digest(root / path) == expected
    assert len(config['prepared30']) == 30
    for row in config['immutable_files']:
        exact_file(row)
    native = Path(config['native_root'])
    assert len(config['native_members']) == 1192
    for row in config['native_members']:
        p = native / row['path']
        assert stat.S_IMODE(p.lstat().st_mode) == row['mode']
        if row['kind'] == 'file':
            assert p.is_file() and not p.is_symlink() and digest(p) == row['content_sha256']
        elif row['kind'] == 'directory':
            assert p.is_dir() and not p.is_symlink()
        else:
            assert p.is_symlink() and os.readlink(p) == row['link_target']
    assert {p.relative_to(native).as_posix() for p in native.rglob('*')} == {r['path'] for r in config['native_members']}
    historical = []
    aliases = []
    for row in config['qualified237_bindings']:
        p = Path(row['path'])
        if row['path'] == config['failed1_mapping']['original_binding']['path']:
            assert row == config['failed1_mapping']['original_binding']
            aliases.append(row)
        elif row['path'] == config['historical_fixture_path']:
            body = subprocess.check_output(['git', '--no-optional-locks', '-C', str(root), 'show', config['historical_fixture_source'] + ':' + p.relative_to(root).as_posix()])
            assert len(body) == row['bytes'] and hashlib.sha256(body).hexdigest() == row['sha256']
            historical.append(row)
        else:
            exact_file(row)
    assert len(config['qualified237_bindings']) == 237 and len(historical) == 1 and len(aliases) == 1
    alias = config['failed1_mapping']
    assert not Path(alias['original_binding']['path']).exists()
    found = False
    with tarfile.open(alias['archive']['path'], 'r|gz') as stream:
        for item in stream:
            if item.name == alias['member']:
                body = stream.extractfile(item).read()
                assert len(body) == alias['original_binding']['bytes']
                assert hashlib.sha256(body).hexdigest() == alias['original_binding']['sha256']
                assert (item.mode, item.uid, item.gid) == (0o600, 1000, 1000)
                assert json.loads(body)['status'] == 'FAIL'
                found = True
                break
    assert found and Path(config['failed563_existence_only']).exists()
    return {'status': 'PASS_DATA_ONLY_PROTECTED_INPUTS', 'source_head': config['source_head'],
            'source_leaves': len(typed), 'native_members': 1192, 'prepared_inputs': 30,
            'immutable_files': len(config['immutable_files']), 'qualified237': 237, 'historical_git_fixture': 1, 'historical_archive_alias': 1, 'failure_upgrade': False,
            'native_execution': 'NOT_RUN', 'universal_quiescence': 'UNKNOWN'}


def selected_roots(config):
    base = Path(config['base'])
    for name, expected in config['selected_snapshots'].items():
        root = base / name
        assert root.is_dir() and not root.is_symlink()
        assert (root / 'recycle.now').read_text().strip() == 'True'
        assert {'.'} | {p.relative_to(root).as_posix() for p in root.rglob('*')} == set(expected['rows'])
        for relative, wanted in expected['rows'].items():
            p = root if relative == '.' else root / relative
            s = p.lstat()
            fields = {'mode': stat.S_IMODE(s.st_mode), 'uid': s.st_uid, 'gid': s.st_gid,
                      'mtime_ns': s.st_mtime_ns, 'device': s.st_dev, 'inode': s.st_ino, 'nlink': s.st_nlink}
            for key, actual in fields.items():
                assert actual == wanted[key]
            kind = wanted['kind']
            if kind == 'file':
                assert stat.S_ISREG(s.st_mode) and s.st_size == wanted['bytes'] and digest(p) == wanted['sha256']
            elif kind == 'directory':
                assert stat.S_ISDIR(s.st_mode)
            elif kind == 'symlink':
                assert stat.S_ISLNK(s.st_mode) and os.readlink(p) == wanted['target']
            else:
                assert kind == 'fifo' and stat.S_ISFIFO(s.st_mode)
    return {'status': 'PASS_EXACT_SELECTED_COMPLETE_ORIGINALS', 'roots': len(config['selected_snapshots'])}
