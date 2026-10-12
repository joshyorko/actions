"""Private exact-root storage preservation. Import has no operation side effects.
Only a separately hashed ROOT release permits the parent to launch one operation.
Synthetic controls may replace globals; production CLI never accepts a source root.
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
import sys
import signal
import tarfile
import zlib
import runpy
INPUT_IDENTITY = None
ROOT = Path('/tmp/pytest-of-agent/pytest-38')
DEST = Path('/tmp/actions-completed-pytest38-preservation-one-owned')
STAGE = Path('/tmp/actions-completed-pytest38-preservation-one-owned-stage')
MAX_ARCHIVE = 335544320
RESERVE = 134217728
VOLUME = Path('/tmp')

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
    directory_fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory_fd)
    finally:os.close(directory_fd)

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

class BoundedOutput:
    def __init__(self, stream):
        self.stream = stream
    def write(self, raw):
        fs = os.statvfs(VOLUME)
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
        for name in names:
            safe_name(name)
        need(len(names) == len(set(names)), 'DUPLICATE_ARCHIVE_MEMBER')
        expected_names = {ROOT.name + ('/' + p if p else '') for p in entries}
        need(set(names) == expected_names, 'ARCHIVE_MEMBER_SET')
        for member in members:
            relative = member.name[len(ROOT.name):].lstrip('/')
            row = entries[relative]
            need(not PurePosixPath(member.name).is_absolute() and '..' not in PurePosixPath(member.name).parts,
                 'ARCHIVE_PATH_ESCAPE')
            need((member.mode, member.uid, member.gid) == (row['mode'], row['uid'], row['gid']), 'ARCHIVE_METADATA')
            need(Decimal(member.pax_headers['mtime']) * 1000000000 == row['mtime_ns'], 'ARCHIVE_EXACT_MTIME')
            if row['kind'] == 'file':
                first = row['hardlink_first']
                need(member.isfile() if relative == first else member.islnk(), 'ARCHIVE_HARDLINK_TYPE')
                if relative != first:
                    need(member.linkname == ROOT.name + '/' + first, 'ARCHIVE_HARDLINK_IDENTITY')
                safe_name(member.linkname) if member.islnk() else None
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

def safe_name(name):
    need(isinstance(name, str) and name != '' and '\\' not in name and '\x00' not in name,
         'UNSAFE_ARCHIVE_PATH')
    p = PurePosixPath(name)
    need(not p.is_absolute() and all(v not in ('', '.', '..') for v in name.split('/')),
         'UNSAFE_ARCHIVE_PATH')


def verify_single_gzip(path):
    decoder = zlib.decompressobj(31)
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            while block:
                decoder.decompress(block, 1048576)
                need(not decoder.unused_data, 'GZIP_TRAILING_DATA')
                block = decoder.unconsumed_tail
    need(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
         'GZIP_EOF_CRC_ISIZE')


def binding(row):
    p = Path(row['path'])
    s = p.lstat()
    need(stat.S_ISREG(s.st_mode) and not p.is_symlink(), 'BOUND_FILE_TYPE')
    need(s.st_size == row['bytes'] and stat.S_IMODE(s.st_mode) == int(row['mode'], 8)
         and sha(p) == row['sha256'], 'BOUND_FILE_BYTES_MODE')


def baseline_entries(path):
    original = json.loads(Path(path).read_bytes())
    need(original['exact_root'] == str(ROOT) and
         original['first_and_second_complete_body_metadata_snapshots_equal'] is True,
         'ORIGINAL_INVENTORY_IDENTITY')
    first = original['first']
    need(hashlib.sha256(json.dumps(first, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
         == original['second_canonical_snapshot_SHA256'], 'ORIGINAL_SECOND_SNAPSHOT_HASH')
    def convert(row):
        r = {k:v for k,v in row.items() if k not in ('allocated_bytes', 'device', 'inode')}
        r['dev'], r['ino'] = row['device'], row['inode']
        return r
    result = {'': dict(kind='directory', **convert(first['root_metadata']))}
    result.update({name:convert(row) for name,row in first['members'].items()})
    need(len(result) == 15684, 'ORIGINAL_MEMBER_COUNT')
    need(Counter(row['kind'] for name,row in result.items() if name) ==
         Counter(directory=3424,file=11756,symlink=495,fifo=8), 'ORIGINAL_TYPE_COUNTS')
    groups = {}
    for name,row in sorted(result.items()):
        if row['kind'] == 'file': groups.setdefault((row['dev'],row['ino']),[]).append(name)
    need(sum(len(paths)>1 for paths in groups.values()) == 4, 'ORIGINAL_HARDLINK_COUNT')
    for paths in groups.values():
        for name in paths:
            need(result[name]['nlink'] == len(paths), 'ORIGINAL_EXTERNAL_HARDLINK')
            result[name]['hardlink_first'] = paths[0]
    return result


def root_admission(expected):
    s = ROOT.lstat()
    need(ROOT.parent.is_dir() and not ROOT.parent.is_symlink(),'ROOT_PARENT_REAL')
    need(stat.S_ISDIR(s.st_mode) and not ROOT.is_symlink() and ROOT.parent == Path('/tmp/pytest-of-agent')
         and ROOT.name == 'pytest-38', 'EXACT_ROOT_ONLY')
    need(meta(s) == {k:v for k,v in expected.items() if k != 'kind'} and
         (stat.S_IMODE(s.st_mode),s.st_uid,s.st_gid) == (0o700,1000,1000), 'ROOT_IDENTITY')
    need({p.name for p in ROOT.iterdir()} == {'popen-gw0','popen-gw1'}, 'EXACT_WORKERS')
    for p in [ROOT,ROOT/'popen-gw0',ROOT/'popen-gw1']:
        need(not (p/'.lock').exists() and not (p/'.lock').is_symlink(), 'LOCK_PRESENT')


def accessible_handles():
    counts = dict(cwd=0,fd_dirs=0,fd_links=0,inaccessible_cwd=0,inaccessible_fd_dirs=0,
                  transient=0,matches=0)
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        links=[p/'cwd']
        try:
            links += list((p/'fd').iterdir()); counts['fd_dirs']+=1
        except FileNotFoundError: counts['transient']+=1
        except PermissionError: counts['inaccessible_fd_dirs']+=1
        for link in links:
            try:
                target=os.readlink(link).removesuffix(' (deleted)')
                counts['cwd' if link.name=='cwd' else 'fd_links']+=1
                if target==str(ROOT) or target.startswith(str(ROOT)+'/'): counts['matches']+=1
            except FileNotFoundError: counts['transient']+=1
            except PermissionError: counts['inaccessible_cwd' if link.name=='cwd' else 'inaccessible_fd_dirs']+=1
    need(counts['matches']==0,'ACCESSIBLE_HANDLE_MATCH')
    return dict(counts=counts,universal_quiescence='UNKNOWN',inaccessible_processes='UNKNOWN')


def git_rows(source, head):
    raw=subprocess.check_output(['git','-C',str(source),'ls-tree','-r','-z',head],timeout=30)
    result=[]
    for part in raw.split(b'\x00'):
        if not part:continue
        info,name=part.split(b'\t',1);mode,kind,oid=info.decode().split()
        need(kind=='blob','SOURCE_NONBLOB')
        result.append(dict(path=name.decode(),mode=mode,oid=oid))
    return result


def global_guard(config):
    if INPUT_IDENTITY is not None:
        for path,digest in INPUT_IDENTITY:need(sha(path)==digest,'INPUT_OR_RELEASE_CHANGED')
    for row in config['retained_files']: binding(row)
    need(Path(config['failed563_existence_only']).is_dir(), 'FAILED563_EXISTENCE_ONLY')
    source=Path(config['source_root'])
    for headkey,treekey in [('current_head','current_tree'),('historical_head','historical_tree')]:
        need(subprocess.check_output(['git','-C',str(source),'rev-parse',config[headkey]+'^{tree}'],timeout=10).decode().strip()==config[treekey],'SOURCE_TREE_IDENTITY')
    subprocess.run(['git','-C',str(source),'merge-base','--is-ancestor',config['historical_head'],config['current_head']],check=True,timeout=10)
    need(subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],timeout=10).decode().strip()
         ==config['current_head'],'CURRENT_SOURCE_HEAD')
    need(subprocess.check_output(['git','-C',str(source),'status','--porcelain'],timeout=10)==b'',
         'CURRENT_SOURCE_CLEAN')
    for headkey,rowkey in [('current_head','current_rows'),('historical_head','historical_rows')]:
        rows=config[rowkey]
        need(git_rows(source,config[headkey])==[{k:r[k] for k in ('path','mode','oid')} for r in rows],
             'COMPLETE_GIT_BODY_MODE_SET')
        raw=subprocess.check_output(['git','-C',str(source),'cat-file','--batch'],
              input=''.join(r['oid']+'\n' for r in rows).encode(),timeout=60)
        cursor=0
        for r in rows:
            end=raw.index(b'\n',cursor);oid,kind,size=raw[cursor:end].decode().split();size=int(size)
            body=raw[end+1:end+1+size];cursor=end+size+2
            need(oid==r['oid'] and kind=='blob' and len(body)==r['bytes'] and
                 hashlib.sha256(body).hexdigest()==r['sha256'],'GIT_BODY_HASH')
            if rowkey=='current_rows':
                p=source/r['path'];st=p.lstat()
                if r['mode']=='120000':
                    need(p.is_symlink() and hashlib.sha256(os.fsencode(os.readlink(p))).hexdigest()==r['sha256'],
                         'CURRENT_SOURCE_LINK')
                else:
                    need(stat.S_ISREG(st.st_mode) and not p.is_symlink() and sha(p)==r['sha256']
                         and stat.S_IMODE(st.st_mode)==r['fs_mode'],'CURRENT_SOURCE_BODY_MODE')
        need(cursor==len(raw),'GIT_BATCH_COMPLETE')
    for path,digest in config['prepared_inputs'].items():
        need(sha(source/path)==digest,'PREPARED_INPUT_BYTES')
    native=Path(config['native_root'])
    for row in config['native_members']:
        p=native/row['path'];need(stat.S_IMODE(p.lstat().st_mode)==row['mode'],'NATIVE_MODE')
        if row['kind']=='file':need(not p.is_symlink() and sha(p)==row['content_sha256'],'NATIVE_BODY')
        elif row['kind']=='directory':need(p.is_dir() and not p.is_symlink(),'NATIVE_DIRECTORY')
        else:need(p.is_symlink() and os.readlink(p)==row['link_target'],'NATIVE_LINK')
    need({p.relative_to(native).as_posix() for p in native.rglob('*')}==
         {r['path'] for r in config['native_members']},'NATIVE_COMPLETE_SET')
    wanted=config['failed_result_member']
    with tarfile.open(config['failed_archive']['path'],'r|gz') as t:
        for member in t:
            if member.name==wanted:
                need(member.isfile() and member.size==config['failed_result_bytes'],'FAILED_ORIGINAL_MEMBER')
                raw=t.extractfile(member).read()
                need(hashlib.sha256(raw).hexdigest()==config['failed_result_sha256'] and
                     json.loads(raw)['status']=='FAIL','FAILED_ACTUAL_UNCHANGED');break
        else:need(False,'FAILED_ORIGINAL_MEMBER_MISSING')
    return dict(retained=len(config['retained_files']),current_source_head=config['current_head'],
         current_source_count=len(config['current_rows']),current_source_qualification='HOLD',
         historical_source_count=len(config['historical_rows']),native_members=len(config['native_members']),
         failed563='EXISTENCE_ONLY',original_failed_actual='FAIL_UNCHANGED')


def authorization(config, release, config_sha):
    need(release == dict(schema=1,status='ROOT_RELEASE_ONE_EXACT_PYTEST38_STORAGE_PRESERVATION',
         config_sha256=config_sha,script_sha256=sha(__file__),
         owner_proposal=config['owner_proposal'],implementation_proposal=release.get('implementation_proposal'),
         independent_review=release.get('independent_review'),
         root=str(ROOT),destination=str(DEST),stage=str(STAGE),
         root_serialized_no_source_native_tmp_mutations=True,storage_origin='CORRELATION_ONLY',
         operation_seconds=600,kill_grace_seconds=10,outer_seconds=900,
         removal='ONLY_AFTER_COMPLETE_VERIFIED_INDEX'), 'EXACT_ROOT_ONCE_RELEASE')
    need(type(release['schema']) is int and release['root_serialized_no_source_native_tmp_mutations'] is True,
         'ROOT_RELEASE_TYPES')
    implementation=release['implementation_proposal'];binding(implementation)
    implementation_body=json.loads(Path(implementation['path']).read_bytes())
    need(implementation_body['script']['sha256']==sha(__file__) and
         implementation_body['configuration']['sha256']==config_sha,'IMPLEMENTATION_PROPOSAL_BINDING')
    review=release['independent_review']; binding(review)
    need(json.loads(Path(review['path']).read_bytes())['decision']=='GO_PREEXECUTION_ONLY',
         'INDEPENDENT_PREEXECUTION_GO')


def index_before_remove(path, entries, archive, revalidate, remove):
    need(not path.exists(), 'INDEX_ONCE')
    write_new(path, dict(schema=1,root=str(ROOT),inventory=entries,
         archive=dict(path=str(archive),bytes=archive.stat().st_size,sha256=sha(archive),mode='0o600'),
         verified_all_bodies_modes_types_UID_GID_links_PAX_ns_and_root=True,
         verified_gzip_CRC_ISIZE_EOF=True,expanded_removed=False,
         source_origin='CORRELATION_ONLY',universal_quiescence='UNKNOWN',
         ACL_xattr_original_inode_recreation='NOT_CLAIMED'))
    # Durably written complete index precedes the final guarded destructive step.
    revalidate()
    need(json.loads(path.read_bytes())['inventory']==entries,'INDEX_READBACK')
    need(stat.S_IMODE(path.lstat().st_mode)==0o600 and not path.is_symlink(),'INDEX_MODE')
    remove()


def operation(config,release,config_sha):
    need(STAGE.is_dir() and not STAGE.is_symlink() and stat.S_IMODE(STAGE.stat().st_mode)==0o700,
         'ONCE_PARENT_STAGE')
    need(not DEST.exists() and not DEST.is_symlink(),'ONCE_DESTINATION_ABSENT')
    need(shutil.disk_usage(VOLUME).free>=MAX_ARCHIVE+RESERVE,'FRESH_TMP_CAPACITY')
    baseline=baseline_entries(config['original_inventory']['path'])
    authorization(config,release,config_sha); initial_guard=global_guard(config)
    write_new(STAGE/'private-operation-before-guard.json',initial_guard)
    root_admission(baseline['']); before=accessible_handles()
    need(inventory()==baseline,'FIRST_COMPLETE_BASELINE')
    DEST.mkdir(mode=0o700)
    write_new(DEST/'private-prearchive-census.json',before)
    archive=DEST/(ROOT.name+'.tar.gz')
    create_archive(archive,baseline); verify_archive(archive,baseline); verify_single_gzip(archive)
    need(archive.lstat().st_size<=MAX_ARCHIVE and stat.S_IMODE(archive.lstat().st_mode)==0o600,
         'ARCHIVE_CAP_MODE')
    def revalidate():
        authorization(config,release,config_sha); global_guard(config)
        need(inventory()==baseline,'FINAL_COMPLETE_BASELINE')
        root_admission(baseline['']); after=accessible_handles()
        write_new(DEST/'private-pre-removal-census.json',after)
        need(shutil.disk_usage(VOLUME).free>=RESERVE,'FINAL_TMP_RESERVE')
    def remove():
        need(ROOT.parent==Path('/tmp/pytest-of-agent') and ROOT.name=='pytest-38','REMOVE_EXACT_ROOT_ONLY')
        root_admission(baseline[''])
        shutil.rmtree(ROOT)
        need(not ROOT.exists() and not ROOT.is_symlink(),'EXACT_EXPANDED_REMOVAL')
    index_before_remove(DEST/'private-complete-inventory-and-preservation.json',baseline,archive,revalidate,remove)
    write_new(DEST/'private-expanded-removal-final.json',dict(expanded_removed=True,
         root=str(ROOT),archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
         original_index_path=str(DEST/'private-complete-inventory-and-preservation.json')))
    return dict(status='STORAGE_ONLY_PRESERVED',members_including_root=len(baseline),
         archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),expanded_removed=True)


def checked_inputs(args):
    need(sha(args.config)==args.config_sha256,'CONFIG_HASH')
    config=json.loads(Path(args.config).read_bytes())
    binding(config['original_inventory']); binding(config['readonly_proposal'])
    need(sha(args.release)==args.release_sha256,'ROOT_RELEASE_HASH')
    release=json.loads(Path(args.release).read_bytes())
    authorization(config,release,args.config_sha256)
    return config,release


def main():
    parser=argparse.ArgumentParser()
    for name in ['config','config-sha256','release','release-sha256']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--operation',action='store_true')
    args=parser.parse_args(); config,release=checked_inputs(args)
    global INPUT_IDENTITY
    INPUT_IDENTITY=[(args.config,args.config_sha256),(args.release,args.release_sha256)]
    if args.operation:
        result=None; primary=None; secondary=[]
        def terminated(signum,frame): raise RuntimeError('OPERATION_DEADLINE_SIGNAL')
        signal.signal(signal.SIGTERM,terminated)
        try: result=operation(config,release,args.config_sha256)
        except BaseException as exc: primary=type(exc).__name__+':'+str(exc)
        finally:
            try:
                post_guard=global_guard(config)
                write_new(STAGE/'private-operation-after-guard.json',post_guard)
            except BaseException as exc: secondary.append(type(exc).__name__+':'+str(exc))
            write_new(STAGE/'private-operation-terminal.json',dict(result=result,primary=primary,
                       secondary=secondary,root_exists=ROOT.exists(),partial_outputs_retained=True))
        return 1 if primary or secondary else 0
    # Parent guards are attempted before and after every operation outcome, including timeout.
    def parent_terminated(signum,frame):raise RuntimeError('PARENT_OUTER_DEADLINE_SIGNAL')
    signal.signal(signal.SIGTERM,parent_terminated)
    need(not STAGE.exists() and not STAGE.is_symlink(),'ONCE_STAGE_ABSENT')
    STAGE.mkdir(mode=0o700)
    primary=None; secondary=[]; child=None; rc=None
    try:
        before_guard=global_guard(config)
        write_new(STAGE/'private-parent-before-guard.json',before_guard)
        need(not DEST.exists() and not DEST.is_symlink(),'ONCE_DESTINATION_ABSENT')
        need(shutil.disk_usage(VOLUME).free>=MAX_ARCHIVE+RESERVE,'PARENT_FRESH_TMP_CAPACITY')
        with (STAGE/'original-operation.private.log').open('xb') as log:
            os.chmod(log.name,0o600)
            argv=[sys.executable,__file__,*sys.argv[1:],'--operation']
            child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT)
            try: rc=child.wait(timeout=600)
            except subprocess.TimeoutExpired:
                primary='PARENT_OPERATION_TIMEOUT'; child.terminate()
                try:rc=child.wait(timeout=10)
                except subprocess.TimeoutExpired:child.kill();rc=child.wait()
            need(rc==0,'OPERATION_FAILED')
    except BaseException as exc:
        if primary is None:primary=type(exc).__name__+':'+str(exc)
        else:secondary.append(type(exc).__name__+':'+str(exc))
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:rc=child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();rc=child.wait()
        try:
            post_guard=global_guard(config)
            write_new(STAGE/'private-parent-after-guard.json',post_guard)
        except BaseException as exc:secondary.append(type(exc).__name__+':'+str(exc))
        write_new(STAGE/'private-parent-terminal.json',dict(primary=primary,secondary=secondary,
            operation_returncode=rc,original_root_exists=ROOT.exists(),partial_outputs_retained=True,
            source_origin='CORRELATION_ONLY',universal_quiescence='UNKNOWN'))
    print(json.dumps(dict(status='PASS_STORAGE_ONLY' if primary is None and not secondary else 'FAIL_HOLD',
                         original_root_exists=ROOT.exists(),operation_returncode=rc)))
    return 1 if primary or secondary else 0


if __name__=='__main__': sys.exit(main())
