import v9_entry_bootstrap
import sys
sys.path[:0] = ['/workspace/engineering/rcc-current8d49-private-V8-real-fixture-mode-successor', '/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation']
"""Root-released readonly pre/post identities; no product/native imports."""
import argparse
import os
import stat
import subprocess
from pathlib import Path

from actual_transport_v8 import SOURCE, TREE, content_sha, read_bound, require_release, verify_temporal_shared_outputs
from runner_contracts_v3 import need, parse_json_object


def guard(config):
    verify_temporal_shared_outputs(config['temporal_shared_outputs'])
    root = Path(config['source_root'])
    need(root == Path('/workspace/engineering/pr308'), 'CURRENT_GUARD_SOURCE_ROOT')
    for row in config['bindings']:
        read_bound(row)
    for key in ('source_FULL', 'source_independent', 'source_FULL_independent'):
        read_bound(config[key])
    for suffix, expected in [('HEAD', SOURCE), ('HEAD^{tree}', TREE)]:
        actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', suffix],
                                         text=True, timeout=10).strip()
        need(actual == expected, 'CURRENT_GUARD_GIT_SUBJECT')
    need(not subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'],
                                     text=True, timeout=10), 'CURRENT_GUARD_CLEAN')
    rows = config['source_body_modes']
    need(type(rows) is list and type(config.get('source_count')) is int and config['source_count'] == len(rows) == 1440 and len({row['path'] for row in rows}) == 1440,
         'CURRENT_GUARD_COMPLETE_SOURCE_COUNT')
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z'], timeout=10).decode().split('\0')
    need(set(tracked) - {''} == {row['path'] for row in rows}, 'CURRENT_GUARD_COMPLETE_SOURCE_SET')
    tracked_git = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '-z', SOURCE], timeout=10).split(b'\0')
    entries = {e.split(b'\t', 1)[1].decode(): e.split(b'\t', 1)[0].split(b' ') for e in tracked_git if e}
    need(set(entries) == {row['path'] for row in rows}, 'CURRENT_GUARD_COMPLETE_GIT_SET')
    for row in rows:
        mode, kind, obj = entries[row['path']]
        need(mode.decode() == row['mode'] and kind == b'blob' and obj.decode() == row['object'], 'CURRENT_GUARD_GIT_MODE_OBJECT')
        need(content_sha(subprocess.check_output(['git', '-C', str(root), 'cat-file', 'blob', obj.decode()], timeout=10)) == row['sha256'], 'CURRENT_GUARD_GIT_BODY')
        path = root / row['path']
        raw = os.readlink(path).encode() if row['mode'] == '120000' else path.read_bytes()
        need(content_sha(raw) == row['sha256'] and stat.S_IMODE(path.lstat().st_mode) == row['fs_mode'],
             'CURRENT_GUARD_SOURCE_BODY_MODE')
    need(len(config['prepared_inputs']) == 30 and len(config['concrete_own_origins']) == 5,
         'CURRENT_GUARD_PREPARED_SCOPE')
    for name, digest in config['prepared_inputs'].items():
        need(content_sha((root / name).read_bytes()) == digest, 'CURRENT_GUARD_PREPARED_HASH')
    native = Path(config['native_original_root'])
    members = config['native_original_members']
    need(len(members) == 1192 and {p.relative_to(native).as_posix() for p in native.rglob('*')}
         == {row['path'] for row in members}, 'CURRENT_GUARD_NATIVE_HISTORICAL_SET')
    for row in members:
        path = native / row['path']
        need(stat.S_IMODE(path.lstat().st_mode) == row['mode'], 'CURRENT_GUARD_NATIVE_MODE')
        if row['kind'] == 'file':
            need(not path.is_symlink() and content_sha(path.read_bytes()) == row['content_sha256'], 'CURRENT_GUARD_NATIVE_BODY')
        elif row['kind'] == 'directory':
            need(path.is_dir() and not path.is_symlink(), 'CURRENT_GUARD_NATIVE_DIRECTORY')
        else:
            need(path.is_symlink() and os.readlink(path) == row['link_target'], 'CURRENT_GUARD_NATIVE_LINK')


def main():
    parser = argparse.ArgumentParser()
    for key in ('config', 'config-sha256', 'release', 'release-sha256', 'label'):
        parser.add_argument('--' + key, required=True)
    args = parser.parse_args()
    raw = Path(args.config).read_bytes(); need(content_sha(raw) == args.config_sha256, 'GUARD_CONFIG_HASH')
    release = Path(args.release).read_bytes(); need(content_sha(release) == args.release_sha256, 'GUARD_ROOT_RELEASE_HASH')
    config = parse_json_object(raw)
    require_release(config, parse_json_object(release), args.config_sha256, args.label)
    guard(config)
    print('PASS_CURRENT_8D49_1440_PREPARED30_OWN5_AND_HISTORICAL1192_HASH_GUARD')


if __name__ == '__main__':
    main()
