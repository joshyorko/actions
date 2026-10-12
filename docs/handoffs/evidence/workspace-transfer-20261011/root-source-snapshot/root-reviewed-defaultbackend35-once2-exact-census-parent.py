"""One accepted pure35 run, with independent bounded external guards on all outcomes."""
import datetime, hashlib, json, os, stat, subprocess, sys, time
from pathlib import Path
assert not sys.flags.optimize
REVIEW = Path('/workspace/engineering/rcc-defaultbackend35-once2-exact-census-independent-PREEXEC-review/OWNERFINAL-independent-defaultbackend35-once2-exact-census-SOURCE-PREEXEC-GO.json')
SHA = 'b309b76054718d5deecce80b482f012b0ebbf9f37bdb2ccf42673dbac3758b3e'
def binding(path, mode):
    p=Path(path); m=p.lstat()
    assert stat.S_ISREG(m.st_mode) and not p.is_symlink()
    assert m.st_uid==os.getuid()==1000 and m.st_gid==os.getgid()==1000
    assert stat.S_IMODE(m.st_mode)==mode
    raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),mode=oct(mode),sha256=hashlib.sha256(raw).hexdigest())
def save(p,value,mode=0o600):
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
    with os.fdopen(fd,'wb') as f: f.write(raw);f.flush();os.fsync(f.fileno())
    fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return binding(p,mode)
rb=binding(REVIEW,0o400);assert rb['sha256']==SHA
r=json.loads(REVIEW.read_bytes())
assert r['schema']==1 and r['decision']=='GO_DEFAULTBACKEND35_ONCE2_EXACT_CENSUS_SOURCE_AND_PREEXECUTION_ONLY'
assert r['status']=='INDEPENDENT_DEFAULTBACKEND35_ONCE2_EXACT_CENSUS_SOURCE_PREEXECUTION_GO'
assert r['source']=='8d49d0865ad5ad27b2d4e325ec135212080625e8'
assert r['tree']=='a80600809d373038ca76e445ba0b7b79bb7eeaa6'
cfg=json.loads(Path(r['config_binding']['path']).read_bytes())
assert len(cfg['frozen_bindings'])==83
for k in ('PYTEST_ADDOPTS','PYTHONOPTIMIZE',*cfg['forbidden_operator_exports']):assert not os.environ.get(k),k
rows=[rb]+[x for x in r.values() if isinstance(x,dict) and {'path','bytes','mode','sha256'}<=set(x)]+cfg['frozen_bindings']
for row in rows:assert binding(row['path'],int(row['mode'],8))==row
release=dict(r['ROOT_release_template']);release['independent_preexecution_review']=rb
assert type(release['schema']) is int and release['schema']==1
assert type(release['serialized_no_other_heavy_or_storage_mutations']) is bool and release['serialized_no_other_heavy_or_storage_mutations']
assert release['config_binding']==r['config_binding'] and release['launcher_binding']==r['launcher_binding']
assert release['source']==r['source'] and release['tree']==r['tree']
rp=Path(cfg['root_release_path']);attempt=Path(release['root'])
for p in (rp,attempt):assert not p.exists() and not p.is_symlink()
os.umask(0o077)
root=Path('/workspace/engineering/root-defaultbackend35-once2-exact-census-reviewed-outer');root.mkdir(mode=0o700)
rr=save(rp,release);rows += [rr,binding(__file__,0o400)]
def closure():
    for row in rows:assert binding(row['path'],int(row['mode'],8))==row
    assert json.loads(rp.read_bytes())==release
    return dict(status='PASS',exact_bindings=len(rows),release=rr,review=rb)
def argv(template):return [rr['sha256'] if x=='ROOT_REAL_DISTINCT_RELEASE_SHA256' else x for x in template]
outer=r['ROOT_external_parent_requirement'];assert outer['outermost_total_seconds']==930
guard=argv(outer['external_guard_argv_template']);child=argv(r['ROOT_exact_child_argv'])
save(root/'exact-reviewed-commands.json',dict(before=guard,primary=child,post=guard,parent_intervals=[135,630,135],total=930))
result=dict(source=r['source'],tree=r['tree'],review=rb,release=rr,native='NOT_RUN',source_adoption='NONE')
started=time.monotonic()
def run(name,command,budget):
    status=dict(argv=command,parent_seconds=budget)
    t=time.monotonic()
    with (root/(name+'.stdout.private')).open('xb') as out,(root/(name+'.stderr.private')).open('xb') as err:
        try:status['returncode']=subprocess.run(command,cwd='/workspace/engineering/pr308/action_server',stdout=out,stderr=err,timeout=budget).returncode
        except BaseException as e:status['exception_class']=type(e).__name__
        finally:
            for f in (out,err):f.flush();os.fsync(f.fileno())
    status['elapsed_seconds']=time.monotonic()-t
    save(root/(name+'.terminal.json'),status)
    return status
try:
    result['before_envelope']=save(root/'external-before-envelope.json',closure())
    result['external_before']=run('external-before',guard,135)
    assert result['external_before'].get('returncode')==0
    result['original_primary']=run('original-primary',child,630)
except BaseException as e:result['primary_exception_class']=type(e).__name__
finally:
    try:result['external_alwayspost']=run('external-alwayspost',guard,135)
    except BaseException as e:result['external_post_retention_exception_class']=type(e).__name__
    try:result['post_envelope']=save(root/'external-alwayspost-envelope.json',closure())
    except BaseException as e:result['external_post_envelope_exception_class']=type(e).__name__
result['elapsed_seconds']=time.monotonic()-started
result['capture']=datetime.datetime.now(datetime.timezone.utc).isoformat()
ok=all(result.get(k,{}).get('returncode')==0 for k in ('external_before','original_primary','external_alwayspost')) and 'post_envelope' in result
result['status']='PASS_PENDING_INDEPENDENT_ACTUAL' if ok else 'FAIL_OR_HOLD_NO_RETRY'
row=save(root/'OWNERFINAL-root-one-original-defaultbackend35-once2-exact-census-outer.json',result,0o400)
print(json.dumps(dict(owner=row,status=result['status'],elapsed_seconds=result['elapsed_seconds'])))
raise SystemExit(0 if ok else 1)
