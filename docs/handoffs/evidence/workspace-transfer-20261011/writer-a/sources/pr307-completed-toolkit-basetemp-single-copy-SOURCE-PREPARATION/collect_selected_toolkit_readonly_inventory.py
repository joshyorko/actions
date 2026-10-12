"""Authorized data-only read-only inventory; no archive or selected-root mutation."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import xml.etree.ElementTree as ET

OUT = Path(__file__).parent
ROOTS = {f'once{n}-toolkit-basetemp': Path('/workspace/engineering') / f'pr307-current9760-token-light-once{n}-owned' / 'toolkit' / 'basetemp' for n in (4, 5, 6)}
DEADLINE = time.monotonic() + 120


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            assert time.monotonic() < DEADLINE
            h.update(block)
    return h.hexdigest()


def binding(p):
    s = p.lstat(); assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    return {'path': str(p), 'bytes': s.st_size, 'mode': oct(stat.S_IMODE(s.st_mode)), 'sha256': sha(p)}


def seal(name, data):
    raw = (json.dumps(data, sort_keys=True, separators=(',', ':')) + '\n').encode()
    p = OUT / name; fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(fd, 'wb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.chmod(p, 0o400)
    return binding(p)


def metadata(root):
    result = {}
    for p in [root] + sorted(root.rglob('*')):
        assert time.monotonic() < DEADLINE
        s = p.lstat()
        if stat.S_ISREG(s.st_mode): kind = 'file'
        elif stat.S_ISDIR(s.st_mode): kind = 'directory'
        elif stat.S_ISLNK(s.st_mode): kind = 'symlink'
        elif stat.S_ISFIFO(s.st_mode): kind = 'fifo'
        else: raise AssertionError('UNSUPPORTED_TYPE')
        row = {k: getattr(s, 'st_' + k) for k in ('uid', 'gid', 'mtime_ns', 'dev', 'ino', 'nlink', 'size', 'blocks')}
        row.update(mode=stat.S_IMODE(s.st_mode), kind=kind)
        if kind == 'symlink': row['target'] = os.readlink(p)
        result['.' if p == root else str(p.relative_to(root))] = row
    return result


def body_snapshot(root, before):
    entries = {}; identities = {}; groups = {}
    for rel, row in before.items():
        if rel == '.': continue
        e = {k: row[k] for k in ('mode', 'mtime_ns', 'uid', 'gid', 'kind')}
        if row['kind'] == 'file':
            e.update(bytes=row['size'], sha256=sha(root / rel)); groups.setdefault((row['dev'], row['ino']), []).append(rel)
        elif row['kind'] == 'symlink': e['target'] = row['target']
        entries[rel] = e; identities[rel] = [row['dev'], row['ino'], row['nlink']]
    for relatives in groups.values():
        assert all(before[r]['nlink'] == len(relatives) for r in relatives), 'EXTERNAL_HARDLINK'
    rt = before['.']; rootrow = {k: rt[k] for k in ('uid', 'gid', 'mtime_ns', 'dev', 'ino', 'nlink', 'mode')}
    return {'root': rootrow, 'entries': entries, 'identities': identities}


def process_observation():
    matches = []; unknown = 0; channels = 0
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit(): continue
        targets = []
        for channel in ('cwd', 'exe'):
            channels += 1
            try: targets.append((channel, os.readlink(proc / channel)))
            except OSError: unknown += 1
        for channel in ('cmdline', 'maps'):
            channels += 1
            try: targets.append((channel, (proc / channel).read_bytes().decode('utf-8', errors='replace')))
            except OSError: unknown += 1
        try:
            for fd in (proc / 'fd').iterdir():
                channels += 1
                try: targets.append(('fd', os.readlink(fd)))
                except OSError: unknown += 1
        except OSError: unknown += 1
        for channel, value in targets:
            for name, root in ROOTS.items():
                if str(root) in value: matches.append({'pid': int(proc.name), 'channel': channel, 'root': name})
    return {'accessible_matches': matches, 'unknown_or_racing_channels': unknown, 'checked_channels': channels,
            'historical_environment_observation_unknown944': 'Retained historical scope, not substituted for this fresh count.', 'universal_quiescence': 'UNKNOWN'}


def main():
    manifests = {}; rows = []; completion = []
    for name, root in ROOTS.items():
        assert root.is_dir() and not root.is_symlink() and root.resolve() == root
        before = metadata(root); assert before['.']['uid'] == before['.']['gid'] == 1000
        snap = body_snapshot(root, before); after = metadata(root); assert before == after
        identities = {(v['dev'], v['ino']): v['blocks'] * 512 for v in before.values()}
        toolkit = root.parent; terminal = binding(toolkit / 'terminal.json'); t = json.loads((toolkit / 'terminal.json').read_bytes())
        assert t['returncode'] == t['expected_returncode'] == 0 and t['command'] == ['rcc', 'run', '-r', 'developer/toolkit.yaml', '--dev', '-t', 'ToolkitTest']
        junit = binding(toolkit / 'junit.xml'); cases = list(ET.fromstring((toolkit / 'junit.xml').read_bytes()).iter('testcase'))
        ids = [str(c.get('classname')) + '::' + str(c.get('name')) for c in cases]
        assert len(cases) == len(set(ids)) == 179 and not any(c.find(k) is not None for c in cases for k in ('failure', 'error', 'skipped'))
        original = binding(toolkit.parent / 'original-terminal.json'); ot = json.loads((toolkit.parent / 'original-terminal.json').read_bytes())
        assert ot['before_passed'] is True and ot['post_guard'] == 'PASS' and ot['status'] in ('FAILED', 'PASSED_CURRENT9760_TOKEN_LIGHT_ONCE6_ONLY')
        assert max(v['mtime_ns'] for v in before.values()) <= Path(terminal['path']).stat().st_mtime_ns
        retained = [terminal, junit, original, binding(toolkit / 'stdout.bin'), binding(toolkit / 'stderr.bin')]
        assert sha(toolkit / 'stdout.bin') == t['stdout_sha256'] and sha(toolkit / 'stderr.bin') == t['stderr_sha256']
        inventory = seal(name + '-private-exact-full-body-and-two-metadata-snapshots.json', {'snapshot': snap, 'first_metadata': before, 'second_metadata': after})
        manifests[name] = inventory
        row = {'name': name, 'root': str(root), 'allocated_unique_bytes': sum(identities.values()), 'entries': len(snap['entries']), 'root_mode': oct(before['.']['mode']), 'external_hardlinks': 0,
               'root_lock_exists': (root / '.lock').exists(), 'inventory': inventory, 'logical_regular_bytes': sum(e['bytes'] for e in snap['entries'].values() if e['kind'] == 'file')}
        rows.append(row); completion.append({'root_name': name, 'Toolkit_cases': 179, 'Toolkit_passed': 179, 'Toolkit_fail_error_skip': 0, 'original_whole_status_retained': ot['status'], 'source': ot['source'], 'tree': ot['tree'], 'retained_outside_bindings': retained})
    observation = process_observation()
    assert not observation['accessible_matches']
    proof = seal('private-original-three-Toolkit-completion-full-inventory-and-observed-process-proof.json', {'roots': rows, 'completion': completion, 'process': observation, 'inventory_bindings': manifests,
        'all_selected_namespace_mutations': 'NONE_READ_ONLY', 'original_FAILED_gates_are_not_converted_to_GO': True})
    print(json.dumps({'proof': proof, 'selected_roots': len(rows), 'allocated_unique_total': sum(r['allocated_unique_bytes'] for r in rows), 'body_entries': sum(r['entries'] for r in rows), 'unknown_channels': observation['unknown_or_racing_channels'], 'observed_matches': len(observation['accessible_matches'])}))


if __name__ == '__main__': main()
