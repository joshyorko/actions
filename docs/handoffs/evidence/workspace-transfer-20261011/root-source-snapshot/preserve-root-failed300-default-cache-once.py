import ast
import datetime
import hashlib
import json
import os
import shutil
import stat
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path('/workspace/engineering/root-failed300-default-cache-preservation-actual')
SOURCE = Path('/home/agent/.robocorp/pkgs')
PARENT = Path('/dev/shm/actions-root-failed300-default-cache-preservation-20261011')
DEST = PARENT / 'pkgs'
BACKUP = Path('/home/agent/.robocorp/pkgs.actions-failed300-preserved-backup-20261011')
HELPER = Path('/workspace/engineering/root-failed300-default-cache-readonly-preparation/inspect-and-freeze.py')
FROZEN = Path('/tmp/root-failed300-default-cache-readonly-preparation-20261011/complete-source-inventory-and-observed-handles.json')
ROOT = SOURCE

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()

def exact(p, size, sha):
    assert p.stat().st_size == size and digest(p) == sha, str(p)

def record(p, value, mode=0o600):
    with p.open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')
    p.chmod(mode)
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': digest(p)}

exact(HELPER, 10140, 'b5eec63fe18573529e4f2f52e8b8f8c9b05323635cacef9250a731b3777c94ad')
exact(FROZEN, 329237, '60943726f5266defefd89dec0dcd7c604009251cf1e80dd5d211a11969e239b6')
proposal = Path('/workspace/engineering/root-failed300-default-cache-readonly-preparation/bounded-whole-default-cache-preservation-proposal-v2.json')
review = Path('/workspace/engineering/root-failed300-default-cache-independent-proposal-review/OWNERFINAL-independent-default-failed300-whole-cache-preservation-proposal-review.json')
exact(proposal, 5169, '8371a8691748c3af7a986f4ad59033569087a85a1f65f2850a79f176ae96a65e')
exact(review, 6506, '1b612ebfde312c0f50ace083a57aa66068926e581ac5767d57ae2169b9cab24f')
tree = ast.parse(HELPER.read_text())
funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('sha', 'info', 'inventory', 'handles')]
assert len(funcs) == 4
exec(compile(ast.Module(body=funcs, type_ignores=[]), str(HELPER) + ':readonly-functions-only', 'exec'), globals())

def inspect(p):
    global ROOT
    ROOT = p
    return inventory()

def observed(p):
    global ROOT
    ROOT = p
    row = handles()
    assert not row['matches'], 'Observed live cache handle: stop'
    return row

def norm(i):
    ignored = {'device', 'inode', 'allocated_bytes', 'nlink'}
    return {'root': {k: v for k, v in i['root'].items() if k not in ignored},
            'entries': {p: {k: v for k, v in r.items() if k not in ignored} for p, r in i['entries'].items()}}

def partitions(i):
    groups = defaultdict(list)
    for p, r in i['entries'].items():
        if r['kind'] == 'file':
            groups[(r['device'], r['inode'])].append(p)
    for paths in groups.values():
        assert all(i['entries'][p]['nlink'] == len(paths) for p in paths), 'external hardlink'
    return sorted(sorted(v) for v in groups.values() if len(v) > 1)

assert not OUT.exists() and not PARENT.exists() and not PARENT.is_symlink()
assert not BACKUP.exists() and not BACKUP.is_symlink()
OUT.mkdir(mode=0o700)
old = json.loads(FROZEN.read_bytes())['first_inventory']
assert partitions(old) == []
assert inspect(SOURCE) == old
pre_handles = observed(SOURCE)
free_before = shutil.disk_usage('/workspace').free
assert shutil.disk_usage('/dev/shm').free >= 1245375915
auth = record(OUT / 'root-exact-once-preservation-authorization.json', {
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'proposal': {'path': str(proposal), 'bytes': 5169, 'sha256': digest(proposal)},
    'independent_review': {'path': str(review), 'bytes': 6506, 'sha256': digest(review)},
    'source': str(SOURCE), 'destination': str(DEST), 'backup': str(BACKUP),
    'one_copy': True, 'known_team_default_cache_users': 'none; other gates on HOLD',
    'proc_scope': 'Observed accessible cwd/FD only; permissions/transient/external concurrency limits retained',
    'pre_handles': pre_handles, 'pre_overlay_free': free_before,
    'logical_path_gap': 'Quiescent rename then symlink, no atomic exchange claim',
    'preserve_all_existing_cache_bytes': True,
    'no_retry_or_install_or_other_cache_mutation': True,
}, 0o644)
events = []; renamed = False; switched = False; removed = False
started = time.monotonic()
try:
    PARENT.mkdir(mode=0o700)
    with (OUT / 'copy.stdout.private.log').open('xb') as stdout, (OUT / 'copy.stderr.private.log').open('xb') as stderr:
        command = ['timeout', '--signal=TERM', '--kill-after=10s', '600s', 'cp', '-a', '--preserve=all', '--no-dereference', str(SOURCE), str(DEST)]
        p = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=615)
    events.append({'copy_returncode': p.returncode, 'elapsed_seconds': time.monotonic() - started})
    assert p.returncode == 0, 'copy failed'
    before_switch = inspect(SOURCE)
    physical = inspect(DEST)
    assert before_switch == old
    assert norm(physical) == norm(old) and partitions(physical) == partitions(old)
    post_copy_handles = observed(SOURCE)
    SOURCE.rename(BACKUP); renamed = True
    SOURCE.symlink_to(DEST, target_is_directory=True); switched = True
    assert SOURCE.is_symlink() and os.readlink(SOURCE) == str(DEST)
    logical = inspect(SOURCE.resolve(strict=True))
    backup = inspect(BACKUP)
    assert norm(logical) == norm(old) and partitions(logical) == partitions(old)
    assert backup == old
    last_handles = {'logical': observed(SOURCE), 'backup': observed(BACKUP), 'physical': observed(DEST)}
    inventory_receipt = record(PARENT / 'complete-private-preservation-inventories.json', {
        'frozen_original': old, 'source_before_switch': before_switch, 'physical': physical,
        'logical': logical, 'backup_before_removal': backup, 'pre_handles': pre_handles,
        'post_copy_handles': post_copy_handles, 'last_handles': last_handles,
        'unchanged_fields': 'relative paths/types/body SHA256/size/mode/UID/GID/mtime_ns/symlink targets and internal hardlink partitions',
        'cross_mount_unqualified': 'devices/inodes/allocated blocks/atime/ctime/directory nlink and unrecorded ACL/xattr measurement',
    })
    # Remove only this verified renamed original; every byte remains at DEST.
    shutil.rmtree(BACKUP); removed = True
    assert not BACKUP.exists() and SOURCE.is_symlink() and os.readlink(SOURCE) == str(DEST)
    assert norm(inspect(SOURCE.resolve(strict=True))) == norm(old)
    result = {'status': 'PASS_ALL_CURRENT_CACHE_BYTES_PRESERVED_LOGICAL_PATH_RETAINED',
              'authorization': auth, 'private_complete_inventories': inventory_receipt,
              'source': str(SOURCE), 'physical_destination': str(DEST), 'removed_only_verified_expanded_backup': str(BACKUP),
              'files': 362, 'directories': 38, 'symlinks': 16, 'regular_bytes': 1132159923,
              'history_baseline': 'UNKNOWN; all current entries preserved without filtering',
              'copy_events': events, 'elapsed_seconds': time.monotonic() - started,
              'overlay_free_before': free_before, 'overlay_free_after': shutil.disk_usage('/workspace').free,
              'default_cache_preservation_does_not_authorize_any_gate': True,
              'observed_handle_limits': pre_handles['scope'], 'no_atomic_exchange_or_universal_quiescence_claim': True}
except BaseException as e:
    rollback = []
    if renamed and not removed:
        try:
            if SOURCE.is_symlink() and os.readlink(SOURCE) == str(DEST):
                SOURCE.unlink()
            assert not SOURCE.exists() and not SOURCE.is_symlink()
            BACKUP.rename(SOURCE)
            rollback.append('original exact directory name restored; physical copy retained')
        except BaseException as secondary:
            rollback.append({'secondary_error': type(secondary).__name__, 'message': str(secondary)})
    record(OUT / 'FAILED-primary-and-rollback-private.json', {'error': type(e).__name__, 'message': str(e), 'events': events, 'renamed': renamed, 'switched': switched, 'removed': removed, 'rollback': rollback})
    raise
final = record(OUT / 'OWNERFINAL-root-whole-default-cache-preservation-actual.json', result, 0o644)
print(json.dumps(final))
