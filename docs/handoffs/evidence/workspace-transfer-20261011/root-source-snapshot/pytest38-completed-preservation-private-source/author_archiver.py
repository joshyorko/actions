import ast, pathlib, os
OUT=pathlib.Path(__file__).parent
p=pathlib.Path('/workspace/engineering/rcc-control3-failed-owned-preservation-proposal/preserve_failed_control3_once_v4.py')
s=p.read_text();t=ast.parse(s)
keep={'need','sha','write_new','meta','inventory','BoundedOutput','create_archive','verify_archive'}
blocks=[ast.get_source_segment(s,n) for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in keep]
header='''"""Private exact-root storage preservation. Import has no operation side effects.
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
ROOT = Path('/tmp/pytest-of-agent/pytest-38')
DEST = Path('/tmp/actions-completed-pytest38-preservation-one-owned')
STAGE = Path('/tmp/actions-completed-pytest38-preservation-one-owned-stage')
MAX_ARCHIVE = 335544320
RESERVE = 134217728
VOLUME = Path('/tmp')
'''
body='\n\n'.join(blocks).replace("os.statvfs('/dev/shm')",'os.statvfs(VOLUME)')
# Additional unique/path admission precedes any member dereference.
body=body.replace("names = [m.name for m in members]", "names = [m.name for m in members]\n        for name in names:\n            safe_name(name)")
body=body.replace("stream = archive.extractfile(member)","safe_name(member.linkname) if member.islnk() else None\n                stream = archive.extractfile(member)")
# Single gzip stream is checked in addition to the proven gzip CRC/ISIZE read.
body += '''

def safe_name(name):
    need(isinstance(name, str) and name != '' and '\\\\' not in name and '\\x00' not in name,
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


def global_guard(config):
    for row in config['retained_files']: binding(row)
    need(Path(config['failed563_existence_only']).is_dir(), 'FAILED563_EXISTENCE_ONLY')
    module = config['proven_guard_module']; binding(module)
    original = runpy.run_path(module['path'],run_name='readonly_guard_definitions')
    original['guard'](json.loads(Path(config['proven_guard_inputs']['path']).read_bytes()),
                      archive=Path(config['failed_archive']['path']))
    return dict(retained=len(config['retained_files']),original_source_native_guard='PASS',
                failed563='EXISTENCE_ONLY',original_failed_actual='FAIL_UNCHANGED')


def authorization(config, release, config_sha):
    need(release == dict(schema=1,status='ROOT_RELEASE_ONE_EXACT_PYTEST38_STORAGE_PRESERVATION',
         config_sha256=config_sha,script_sha256=sha(__file__),
         owner_proposal=config['owner_proposal'],independent_review=release.get('independent_review'),
         root=str(ROOT),destination=str(DEST),stage=str(STAGE),
         root_serialized_no_source_native_tmp_mutations=True,storage_origin='CORRELATION_ONLY',
         operation_seconds=600,kill_grace_seconds=10,outer_seconds=900,
         removal='ONLY_AFTER_COMPLETE_VERIFIED_INDEX'), 'EXACT_ROOT_ONCE_RELEASE')
    need(type(release['schema']) is int and release['root_serialized_no_source_native_tmp_mutations'] is True,
         'ROOT_RELEASE_TYPES')
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
    authorization(config,release,config_sha); global_guard(config)
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
    if args.operation:
        result=None; primary=None; secondary=[]
        def terminated(signum,frame): raise RuntimeError('OPERATION_DEADLINE_SIGNAL')
        signal.signal(signal.SIGTERM,terminated)
        try: result=operation(config,release,args.config_sha256)
        except BaseException as exc: primary=type(exc).__name__+':'+str(exc)
        finally:
            try: global_guard(config)
            except BaseException as exc: secondary.append(type(exc).__name__+':'+str(exc))
            write_new(STAGE/'private-operation-terminal.json',dict(result=result,primary=primary,
                       secondary=secondary,root_exists=ROOT.exists(),partial_outputs_retained=True))
        return 1 if primary or secondary else 0
    # Parent guards are attempted before and after every operation outcome, including timeout.
    need(not STAGE.exists() and not STAGE.is_symlink(),'ONCE_STAGE_ABSENT')
    STAGE.mkdir(mode=0o700)
    primary=None; secondary=[]; child=None; rc=None
    try:
        global_guard(config)
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
        try:global_guard(config)
        except BaseException as exc:secondary.append(type(exc).__name__+':'+str(exc))
        write_new(STAGE/'private-parent-terminal.json',dict(primary=primary,secondary=secondary,
            operation_returncode=rc,original_root_exists=ROOT.exists(),partial_outputs_retained=True,
            source_origin='CORRELATION_ONLY',universal_quiescence='UNKNOWN'))
    print(json.dumps(dict(status='PASS_STORAGE_ONLY' if primary is None and not secondary else 'FAIL_HOLD',
                         original_root_exists=ROOT.exists(),operation_returncode=rc)))
    return 1 if primary or secondary else 0


if __name__=='__main__': sys.exit(main())
'''
p=OUT/'preserve_exact_pytest38_once.py'; p.open('x').write(header+'\n'+body);p.chmod(0o600)
