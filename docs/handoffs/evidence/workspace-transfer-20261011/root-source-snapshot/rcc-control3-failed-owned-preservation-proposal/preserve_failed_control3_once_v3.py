"""Private, separately released byte preservation; NEVER qualifies cleanup.

Importing this file does nothing. Only the exact failed control3 directory can
be archived. Nothing runs RCC, a provider, a test, a signal, wait, or reap.
"""
import argparse
from collections import Counter
from decimal import Decimal
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tarfile

ROOT = Path('/dev/shm/actions-rcc-compatibility-actual-control3-20261011-1')
DEST = Path('/dev/shm/actions-failed-control3-original-preservation-20261011-1')
INPUTS = Path('/workspace/engineering/rcc-control3-failed-owned-preservation-proposal/frozen-preservation-inputs-v3.json')
MAX_ARCHIVE = 1000000000
RESERVE = 268435456


def need(ok, code):
    if not ok:
        raise RuntimeError(code)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def write_new(path, data):
    raw = (json.dumps(data, sort_keys=True, separators=(',', ':')) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def meta(info):
    return dict(mode=stat.S_IMODE(info.st_mode), uid=info.st_uid,
                gid=info.st_gid, mtime_ns=info.st_mtime_ns,
                dev=info.st_dev, ino=info.st_ino, nlink=info.st_nlink)


def inventory():
    need(ROOT.is_dir() and not ROOT.is_symlink(), 'EXACT_ROOT_REQUIRED')
    result = {'': dict(kind='directory', **meta(ROOT.lstat()))}
    for directory, dirs, files in os.walk(ROOT, followlinks=False,
                                         onerror=lambda _: need(False, 'WALK_ERROR')):
        for name in sorted(dirs + files):
            path = Path(directory) / name
            relative = path.relative_to(ROOT).as_posix()
            relative.encode('utf-8', errors='strict')
            before = path.lstat()
            row = meta(before)
            if stat.S_ISREG(before.st_mode):
                fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                with os.fdopen(fd, 'rb') as stream:
                    need(meta(os.fstat(stream.fileno())) == meta(before), 'FILE_OPEN_CHANGED')
                    h = hashlib.sha256()
                    size = 0
                    for block in iter(lambda: stream.read(1048576), b''):
                        h.update(block)
                        size += len(block)
                    need(meta(os.fstat(stream.fileno())) == meta(before), 'FILE_READ_CHANGED')
                need(size == before.st_size, 'FILE_SIZE_CHANGED')
                row.update(kind='file', bytes=size, sha256=h.hexdigest())
            elif stat.S_ISDIR(before.st_mode):
                row.update(kind='directory')
            elif stat.S_ISLNK(before.st_mode):
                row.update(kind='symlink', target=os.readlink(path))
            elif stat.S_ISFIFO(before.st_mode):
                row.update(kind='fifo')
            else:
                need(False, 'UNSUPPORTED_MEMBER_TYPE')
            need(meta(path.lstat()) == meta(before), 'MEMBER_CHANGED_DURING_READ')
            result[relative] = row
    groups = {}
    for relative, row in sorted(result.items()):
        if row['kind'] == 'file':
            groups.setdefault((row['dev'], row['ino']), []).append(relative)
    for paths in groups.values():
        for relative in paths:
            row = result[relative]
            need(row['nlink'] == len(paths), 'EXTERNAL_HARDLINK')
            row['hardlink_first'] = paths[0]
    return result


def task_identity(path):
    text = (path / 'stat').read_text()
    tail = text[text.rfind(')') + 2:].split()
    status = (path / 'status').read_text().splitlines()
    uids = [int(v) for v in next(v for v in status if v.startswith('Uid:')).split()[1:]]
    return dict(pid=int(path.name), uids=uids, state=tail[0], start_ticks=int(tail[19]))


def handle_scan():
    """Every live same-UID task, not just possibly-zombie group leaders."""
    rows = []
    unknown_other_uid = []
    scanned = set()
    matches = []
    for process in sorted(Path('/proc').iterdir()):
        if not process.name.isdigit():
            continue
        try:
            leader = task_identity(process)
        except FileNotFoundError:
            continue
        except Exception:
            need(False, 'PROCESS_UID_IDENTITY_UNKNOWN')
        own = os.geteuid() in leader['uids']
        try:
            tasks = sorted((process / 'task').iterdir())
        except Exception:
            if own:
                need(False, 'SAME_UID_TASK_SET_UNAVAILABLE')
            unknown_other_uid.append({'pid': leader['pid'], 'category': 'TASK_SET_UNAVAILABLE'})
            continue
        task_ids = [int(p.name) for p in tasks]
        for task in tasks:
            before = task_identity(task)
            key = (before['pid'], before['start_ticks'])
            if key in scanned:
                continue
            scanned.add(key)
            same_uid = os.geteuid() in before['uids']
            errors = []
            if before['state'] != 'Z':
                try:
                    links = [task / 'cwd', *sorted((task / 'fd').iterdir())]
                except Exception:
                    links = [task / 'cwd']
                    errors.append('FD_LIST_UNAVAILABLE')
                for link in links:
                    try:
                        target = os.readlink(link).removesuffix(' (deleted)')
                        if target == str(ROOT) or target.startswith(str(ROOT) + '/'):
                            matches.append({'pid': before['pid'], 'category': 'OWNED_PATH_HANDLE'})
                    except FileNotFoundError:
                        if link.name == 'cwd':
                            errors.append('LIVE_CWD_UNAVAILABLE')
                    except OSError:
                        errors.append('HANDLE_READ_UNAVAILABLE')
            after = task_identity(task)
            need(before == after, 'TASK_IDENTITY_STATE_CHANGED')
            if same_uid:
                need(not errors, 'LIVE_SAME_UID_HANDLE_UNAVAILABLE')
            else:
                unknown_other_uid.extend({'pid': before['pid'], 'category': e} for e in errors)
            rows.append({'before': before, 'after': after, 'same_uid': same_uid,
                         'classification': 'STABLE_Z_FILES_FS_RELEASED_NOT_REAPED'
                         if before['state'] == 'Z' else 'LIVE_ACCESSIBLE' if not errors else 'OTHER_UID_UNKNOWN'})
        need(task_identity(process) == leader, 'LEADER_IDENTITY_STATE_CHANGED')
        need([int(p.name) for p in sorted((process / 'task').iterdir())] == task_ids,
             'TASK_SET_CHANGED')
    need(not matches, 'OWNED_PATH_HANDLE_PRESENT')
    return {'rows': rows, 'other_uid_unknown': unknown_other_uid,
            'matched_owned_paths': matches, 'universal_quiescence': 'UNKNOWN',
            'original_cleanup': 'FAIL_UNCHANGED', 'zombie_reaping': 'NOT_CLAIMED'}


def bound(row):
    path = Path(row['path'])
    need(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'BOUND_BYTES_CHANGED')
    need(oct(stat.S_IMODE(path.stat().st_mode)) == row['mode'], 'BOUND_MODE_CHANGED')


def guard(inputs, archive=None):
    for row in inputs['bindings']:
        bound(row)
    need(os.uname().sysname == 'Linux' and os.uname().release == '6.18.44', 'KERNEL_CONTEXT_CHANGED')
    need(ROOT.parent == Path('/dev/shm') and ROOT.name == inputs['root_name'], 'ROOT_IDENTITY')
    need(os.geteuid() == inputs['owner_uid'], 'OWNER_UID_CHANGED')
    if ROOT.exists():
        need(ROOT.stat().st_uid == inputs['owner_uid'], 'ROOT_UID_CHANGED')
    need(json.loads(Path(inputs['root_terminal']['path']).read_bytes())['status'] == 'FAIL_HOLD', 'FAILURE_RELABELED')
    need(json.loads(Path('/workspace/engineering/root-rcc-compatibility-control3-one-actual/root900-original-process-terminal.json').read_bytes())['root900_returncode'] == 1,
         'ROOT900_ORIGINAL_NOT_TERMINAL_FAILURE')
    if archive is None:
        actual_raw = Path(inputs['actual_result']['path']).read_bytes()
    else:
        with tarfile.open(archive, 'r:gz') as saved:
            actual_raw = saved.extractfile(ROOT.name + '/OWNERFINAL-one-version-actual-result.json').read()
    need(hashlib.sha256(actual_raw).hexdigest() == inputs['actual_result']['sha256'], 'ACTUAL_FAILURE_BODY_CHANGED')
    need(json.loads(actual_raw)['status'] == 'FAIL', 'ACTUAL_FAILURE_RELABELED')
    config = json.loads(Path(inputs['transport_config']['path']).read_bytes())
    source = Path(config['source_root'])
    need(subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
         == config['source'], 'SOURCE_HEAD_CHANGED')
    need(subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
         == config['tree'], 'SOURCE_TREE_CHANGED')
    need(not subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True),
         'SOURCE_DIRTY')
    for row in config['source_body_modes']:
        p = source / row['path']
        digest = hashlib.sha256(os.readlink(p).encode()).hexdigest() if row['mode'] == '120000' else sha(p)
        need(digest == row['sha256'] and stat.S_IMODE(p.lstat().st_mode) == row['fs_mode'], 'SOURCE_BODY_MODE_CHANGED')
    for path, expected in config['prepared_inputs'].items():
        need(sha(source / path) == expected, 'PREPARED_INPUT_CHANGED')
    native = Path(config['native_original_root'])
    for row in config['native_original_members']:
        p = native / row['path']
        need(stat.S_IMODE(p.lstat().st_mode) == row['mode'], 'NATIVE_MODE_CHANGED')
        if row['kind'] == 'file':
            need(not p.is_symlink() and sha(p) == row['content_sha256'], 'NATIVE_BODY_CHANGED')
        elif row['kind'] == 'directory':
            need(p.is_dir() and not p.is_symlink(), 'NATIVE_DIRECTORY_CHANGED')
        else:
            need(p.is_symlink() and os.readlink(p) == row['link_target'], 'NATIVE_LINK_CHANGED')
    need({p.relative_to(native).as_posix() for p in native.rglob('*')}
         == {r['path'] for r in config['native_original_members']}, 'NATIVE_MEMBER_SET_CHANGED')


class BoundedOutput:
    def __init__(self, stream):
        self.stream = stream
    def write(self, raw):
        fs = os.statvfs('/dev/shm')
        need(self.stream.tell() + len(raw) <= MAX_ARCHIVE, 'ARCHIVE_SIZE_BOUND')
        need(fs.f_bavail * fs.f_frsize >= RESERVE + len(raw), 'ARCHIVE_FREE_SPACE_BOUND')
        return self.stream.write(raw)
    def flush(self):
        return self.stream.flush()


def create_archive(path, entries):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as raw:
        with gzip.GzipFile(fileobj=BoundedOutput(raw), mode='wb', compresslevel=1, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w|', format=tarfile.PAX_FORMAT) as archive:
                for relative, row in sorted(entries.items()):
                    name = ROOT.name + ('/' + relative if relative else '')
                    member = tarfile.TarInfo(name)
                    member.mode, member.uid, member.gid = row['mode'], row['uid'], row['gid']
                    member.mtime = row['mtime_ns'] // 1000000000
                    member.pax_headers['mtime'] = str(Decimal(row['mtime_ns']) / Decimal(1000000000))
                    if row['kind'] == 'directory':
                        member.type = tarfile.DIRTYPE
                    elif row['kind'] == 'symlink':
                        member.type, member.linkname = tarfile.SYMTYPE, row['target']
                    elif row['kind'] == 'fifo':
                        member.type = tarfile.FIFOTYPE
                    elif relative != row['hardlink_first']:
                        member.type, member.linkname = tarfile.LNKTYPE, ROOT.name + '/' + row['hardlink_first']
                    else:
                        member.type, member.size = tarfile.REGTYPE, row['bytes']
                        with (ROOT / relative).open('rb') as stream:
                            archive.addfile(member, stream)
                        continue
                    archive.addfile(member)
        raw.flush()
        os.fsync(raw.fileno())


def verify_archive(path, entries):
    with tarfile.open(path, 'r:gz') as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        need(len(names) == len(set(names)), 'DUPLICATE_ARCHIVE_MEMBER')
        expected_names = {ROOT.name + ('/' + p if p else '') for p in entries}
        need(set(names) == expected_names, 'ARCHIVE_MEMBER_SET')
        for member in members:
            relative = member.name[len(ROOT.name):].lstrip('/')
            row = entries[relative]
            need(not PurePosixPath(member.name).is_absolute() and '..' not in PurePosixPath(member.name).parts,
                 'ARCHIVE_PATH_ESCAPE')
            need((member.mode, member.uid, member.gid) == (row['mode'], row['uid'], row['gid']), 'ARCHIVE_METADATA')
            need(int(Decimal(member.pax_headers['mtime']) * 1000000000) == row['mtime_ns'], 'ARCHIVE_EXACT_MTIME')
            if row['kind'] == 'file':
                first = row['hardlink_first']
                need(member.isfile() if relative == first else member.islnk(), 'ARCHIVE_HARDLINK_TYPE')
                if relative != first:
                    need(member.linkname == ROOT.name + '/' + first, 'ARCHIVE_HARDLINK_IDENTITY')
                stream = archive.extractfile(member)
                h, size = hashlib.sha256(), 0
                for block in iter(lambda: stream.read(1048576), b''):
                    h.update(block)
                    size += len(block)
                need(size == row['bytes'] and h.hexdigest() == row['sha256'], 'ARCHIVE_RESOLVED_BODY')
            elif row['kind'] == 'directory':
                need(member.isdir(), 'ARCHIVE_DIRECTORY')
            elif row['kind'] == 'symlink':
                need(member.issym() and member.linkname == row['target'], 'ARCHIVE_SYMLINK')
            else:
                need(member.isfifo(), 'ARCHIVE_FIFO')
    # TAR end markers alone do not require reading gzip's CRC/ISIZE trailer.
    with gzip.open(path, 'rb') as stream:
        while stream.read(1048576):
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs-sha256', required=True)
    parser.add_argument('--release', required=True)
    parser.add_argument('--release-sha256', required=True)
    parser.add_argument('--mode', choices=['COPY_ONLY', 'ARCHIVE_VERIFY_REMOVE'], required=True)
    args = parser.parse_args()
    need(sha(INPUTS) == args.inputs_sha256, 'INPUTS_HASH')
    inputs = json.loads(INPUTS.read_bytes())
    need(sha(args.release) == args.release_sha256, 'ROOT_RELEASE_HASH')
    release = json.loads(Path(args.release).read_bytes())
    need(release == {'schema': 1, 'status': 'ROOT_RELEASE_ONE_FAILED_OWNED_BYTE_PRESERVATION',
                     'inputs_sha256': args.inputs_sha256, 'script_sha256': sha(__file__),
                     'root': str(ROOT), 'destination': str(DEST), 'mode': args.mode,
                     'original_status': 'FAIL_HOLD_UNCHANGED', 'serialized_failed_root_and_devshm': True},
         'EXACT_ROOT_RELEASE_REQUIRED')
    need(release['serialized_failed_root_and_devshm'] is True and type(release['schema']) is int,
         'ROOT_RELEASE_TYPES')
    guard(inputs)
    need(not DEST.exists() and not DEST.is_symlink(), 'ONCE_DESTINATION_ABSENT')
    fs = os.statvfs('/dev/shm')
    need(fs.f_bavail * fs.f_frsize >= 2000000000, 'FRESH_ARCHIVE_STAGING_CAPACITY')
    first = handle_scan()
    entries = inventory()
    baseline = json.loads(Path(inputs['inventory']['path']).read_bytes())
    need(entries == baseline, 'CURRENT_BYTES_OR_INODE_BASELINE_CHANGED')
    DEST.mkdir(mode=0o700)
    write_new(DEST / 'private-prearchive-inventory-and-census.json', {'inventory': entries, 'census': first})
    archive = DEST / (ROOT.name + '.tar.gz')
    create_archive(archive, entries)
    verify_archive(archive, entries)
    need(inventory() == entries, 'SECOND_COMPLETE_INVENTORY_CHANGED')
    second = handle_scan()
    guard(inputs)
    record = {'original_root': str(ROOT), 'original_status': 'FAIL_HOLD_UNCHANGED',
              'archive': str(archive), 'archive_bytes': archive.stat().st_size,
              'archive_sha256': sha(archive), 'archive_CRC_EOF_and_complete_member_verification': True,
              'inventory': entries, 'first_census': first, 'second_census': second,
              'expanded_removed': False, 'mode': args.mode,
              'universal_quiescence': 'UNKNOWN', 'original_cleanup': 'FAIL_UNCHANGED',
              'restore': 'Verify this complete archive/index, then restore ONLY into a separately authorized empty directory. Retain private original-root references; never overwrite other namespaces. UID/GID restoration needs actual account permissions. ACL/xattr/original inode numbers not preserved.'}
    write_new(DEST / 'private-complete-inventory-and-preservation.json', record)
    if args.mode == 'ARCHIVE_VERIFY_REMOVE':
        need(ROOT.parent == Path('/dev/shm') and ROOT.name == inputs['root_name'], 'REMOVE_EXACT_ROOT_ONLY')
        need(dict(kind='directory', **meta(ROOT.lstat())) == entries[''], 'ROOT_INODE_OR_METADATA_CHANGED')
        shutil.rmtree(ROOT)
        need(not ROOT.exists() and not ROOT.is_symlink(), 'EXPANDED_REMOVAL_INCOMPLETE')
        record = {k: v for k, v in record.items() if k != 'inventory'}
        record['expanded_removed'] = True
        fs = os.statvfs('/dev/shm')
        record['devshm_free_after_bytes'] = fs.f_bavail * fs.f_frsize
        record['successor_capacity_floor_met'] = record['devshm_free_after_bytes'] >= 3865470567
        write_new(DEST / 'private-expanded-removal-final.json', record)
        need(record['successor_capacity_floor_met'], 'SUCCESSOR_CAPACITY_FLOOR_STILL_HOLD')
    guard(inputs, archive=archive)
    print(json.dumps({'status': 'FAILED_ORIGINAL_BYTES_PRESERVED_NOT_QUALIFIED',
                      'member_count_including_root': len(entries), 'mode': args.mode,
                      'expanded_removed': args.mode == 'ARCHIVE_VERIFY_REMOVE',
                      'archive_bytes': archive.stat().st_size, 'archive_sha256': sha(archive),
                      'original_status': 'FAIL_HOLD_UNCHANGED'}), flush=True)


if __name__ == '__main__':
    main()
