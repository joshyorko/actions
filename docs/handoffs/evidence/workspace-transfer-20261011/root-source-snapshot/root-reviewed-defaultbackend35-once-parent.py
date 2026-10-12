"""ROOT exact one-shot parent for reviewed default-backend35 pure controls."""
import datetime,hashlib,json,os,stat,subprocess,sys,time
from pathlib import Path
assert not sys.flags.optimize
def binding(path, mode=None):
    path = Path(path)
    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode) and not path.is_symlink()
    assert metadata.st_uid == os.getuid() == 1000 and metadata.st_gid == os.getgid() == 1000
    if mode is not None:
        assert stat.S_IMODE(metadata.st_mode) == mode
    body = path.read_bytes()
    return {'path': str(path), 'bytes': len(body), 'mode': oct(stat.S_IMODE(metadata.st_mode)), 'sha256': hashlib.sha256(body).hexdigest()}

def save(path, value, mode=0o600):
    body = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return binding(path, mode)


review_path=Path('/workspace/engineering/rcc-current8d49-defaultbackend35-independent-PREEXEC-review/OWNERFINAL-independent-current8d49-defaultbackend35-concrete-PREEXECUTION-GO.json')
rb=binding(review_path,0o400)
assert rb['sha256']=='f458c9cbf1389310803535bc033316d7fee06d3f1aa7cf2275bbdd0d1cfb0abb'
review=json.loads(review_path.read_bytes())
assert review['schema']==1 and review['status']=='INDEPENDENT_DEFAULTBACKEND35_CONCRETE_PREEXECUTION_GO'
assert review['decision']=='GO_CURRENT8D49_DEFAULT_DESCRIPTOR35_CONCRETE_PURE_PREEXECUTION_ONLY'
assert review['source']=='8d49d0865ad5ad27b2d4e325ec135212080625e8' and review['tree']=='a80600809d373038ca76e445ba0b7b79bb7eeaa6'
for key in ('proposal_binding','config_binding','launcher_binding','contract_binding','controls_binding','expected_cases_binding'):
    assert binding(review[key]['path'],0o400)==review[key]
assert binding('/workspace/actions-cloud/activate.sh',0o600)['sha256']=='6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
release=review['ROOT_release_required_template']
release['independent_preexecution_review']=rb
release_path=Path(review['ROOT_release_path'])
assert not release_path.exists() and not release_path.is_symlink()
assert not Path(release['root']).exists() and not Path(release['root']).is_symlink()
os.umask(0o077)
root=Path('/workspace/engineering/root-defaultbackend35-reviewed-original-outer-once');root.mkdir(mode=0o700)
release_row=save(release_path,release)
argv=[release_row['sha256'] if part=='ROOT_REAL_DISTINCT_RELEASE_SHA256' else part for part in review['ROOT_exact_argv_template']]
assert argv[-1]==release_row['sha256'] and argv[-3]==release_row['path'] and review['ROOT_parent_seconds']==630
save(root/'exact-reviewed-outer-command.json',{'argv':argv,'parent_seconds':630,'review':rb,'release':release_row,'native':'NOT_RUN'})
result={'review':rb,'release':release_row,'source':review['source'],'tree':review['tree'],'native':'NOT_RUN','source_adoption':'NONE'}
started=time.monotonic()
with (root/'original.stdout.private').open('xb') as stdout,(root/'original.stderr.private').open('xb') as stderr:
    try:
        completed=subprocess.run(argv,cwd='/workspace/engineering/pr308/action_server',stdout=stdout,stderr=stderr,timeout=630)
        result['outer_returncode']=completed.returncode
    except BaseException as error:result['outer_exception_class']=type(error).__name__
    finally:
        stdout.flush();os.fsync(stdout.fileno());stderr.flush();os.fsync(stderr.fileno())
for row in (rb,release_row,review['config_binding'],review['launcher_binding']):assert binding(row['path'],int(row['mode'],8))==row
result['elapsed_seconds']=time.monotonic()-started;result['capture']=datetime.datetime.now(datetime.timezone.utc).isoformat()
row=save(root/'OWNERFINAL-root-one-original-reviewed-defaultbackend35-outer.json',result,0o400)
print(json.dumps({'owner':row,'returncode':result.get('outer_returncode'),'elapsed_seconds':result['elapsed_seconds']}))
raise SystemExit(0 if result.get('outer_returncode')==0 else 1)
