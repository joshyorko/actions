"""Bounded caller invokes this read-only source/data guard; no product imports."""
import hashlib,json,os,stat,subprocess,sys
from pathlib import Path

def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def exact(r):
 p=Path(r['path']);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink()
 assert m.st_size==r['bytes'] and digest(p)==r['sha256'] and oct(stat.S_IMODE(m.st_mode))==r['mode']
def verified_buffer(path, expected_sha, mode, owner=False, expected_bytes=None):
    p=Path(path);m=p.lstat()
    assert stat.S_ISREG(m.st_mode) and not p.is_symlink() and stat.S_IMODE(m.st_mode)==mode
    if owner:assert m.st_uid==os.getuid() and m.st_gid==os.getgid()
    raw=p.read_bytes()
    assert len(raw)==m.st_size
    if expected_bytes is not None:assert len(raw)==expected_bytes
    assert hashlib.sha256(raw).hexdigest()==expected_sha
    return raw

def main():
 assert len(sys.argv)==12 and sys.argv[3] in ('before','after') and sys.flags.optimize==0
 c=json.loads(verified_buffer(sys.argv[1],sys.argv[2],0o400));root=Path(c['source_root'])
 # Full authority closure revalidated before AND always-post, not only source input rows.
 def typed_json(path,sha,mode):
  return json.loads(verified_buffer(path,sha,mode,owner=True))
 auth=typed_json(sys.argv[4],sys.argv[5],0o600);pre=typed_json(sys.argv[6],sys.argv[7],0o400);src=typed_json(sys.argv[8],sys.argv[9],0o400)
 launcher=Path(sys.argv[10]);lm=launcher.lstat();assert stat.S_ISREG(lm.st_mode) and not launcher.is_symlink() and stat.S_IMODE(lm.st_mode)==0o444 and digest(launcher)==sys.argv[11]
 assert auth['decision']=='ROOT_RELEASE_ONE_CURRENT_2D86_PRIVATE_BOUNDED_LIGHT_ONLY' and auth['source']==c['source'] and auth['tree']==c['tree']
 assert auth['config_sha256']==sys.argv[2] and auth['launcher_sha256']==sys.argv[11]
 assert auth['independent_preexecution_review']=={'path':sys.argv[6],'sha256':sys.argv[7]} and auth['independent_source_review']=={'path':sys.argv[8],'sha256':sys.argv[9]}
 for v,decision in [(pre,'GO_CURRENT_2D86_PRIVATE_BOUNDED_LIGHT_PREEXECUTION'),(src,'GO_CURRENT_2D86_PRIVATE_BOUNDED_LIGHT_SOURCE_PREPARED_ONLY')]:
  assert v['decision']==decision and v['source']==c['source'] and v['tree']==c['tree'] and v['config_sha256']==sys.argv[2] and v['launcher_sha256']==sys.argv[11]
 exact(auth['external_all_outcome_parent_binding']);assert pre['external_all_outcome_parent_sha256']==auth['external_all_outcome_parent_binding']['sha256']
 assert Path(sys.prefix).resolve()==Path(c['cached_prefix']).resolve()
 assert 'PYTHONOPTIMIZE' not in os.environ and 'PYTEST_ADDOPTS' not in os.environ
 for k,v in c['expected_activation'].items():assert os.environ[k]==v,k
 assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
 for k in c['forbidden_actual_operator_exports']:assert k not in os.environ,k
 for r in c['bindings']:exact(r)
 assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD','HEAD^{tree}'],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')).decode().splitlines()==[c['source'],c['tree']]
 assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain'],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
 r=c['source_inventory'];rows=json.loads(verified_buffer(r['path'],r['sha256'],int(r['mode'],8),expected_bytes=r['bytes']));assert len(rows)==c['source_leaf_count']==1441
 for r in rows:
  p=root/r['path'];m=p.lstat()
  if r['mode']=='120000':assert stat.S_ISLNK(m.st_mode);b=os.readlink(p).encode();assert hashlib.sha256(b).hexdigest()==r['sha256']
  else:assert stat.S_ISREG(m.st_mode);assert digest(p)==r['sha256'];assert bool(m.st_mode&0o111)==(r['mode']=='100755')
  assert stat.S_IMODE(m.st_mode)==r['fs_mode']
 assert len(c['prepared30'])==30
 for n,h in c['prepared30'].items():assert digest(root/n)==h,n
 assert len(c['prefix_aliases'])==5
 for r in c['prefix_aliases']:
  q=Path(r['logical']);s=q.lstat();assert oct(stat.S_IMODE(s.st_mode))==r['mode'] and q.resolve()==Path(r['physical']).resolve()
  if r['kind']=='symlink':assert stat.S_ISLNK(s.st_mode) and os.readlink(q)==r['link_target']
  else:assert r['kind']=='directory' and stat.S_ISDIR(s.st_mode) and not q.is_symlink()
 assert len(c['five_prefix_bindings'])==5
 for r in c['five_prefix_bindings']:exact(r)
 for package,module in c['origin_packages']:
  # Existence only here. ROOT-authorized package probes must establish actual prefixes/origins later.
  assert (root/package/'.venv/bin/python').is_file()
 r=c['native_baseline'];baseline=json.loads(verified_buffer(r['path'],r['sha256'],int(r['mode'],8),expected_bytes=r['bytes']));members=baseline['native_original_members'];native=Path(baseline['native_original_root']);assert len(members)==1192
 for r in members:
  p=native/r['path'];m=p.lstat();assert stat.S_IMODE(m.st_mode)==r['mode']
  if r['kind']=='file':assert stat.S_ISREG(m.st_mode) and not p.is_symlink() and digest(p)==r['content_sha256']
  elif r['kind']=='directory':assert stat.S_ISDIR(m.st_mode) and not p.is_symlink()
  else:assert stat.S_ISLNK(m.st_mode) and os.readlink(p)==r['link_target']
 assert {p.relative_to(native).as_posix() for p in native.rglob('*')}=={r['path'] for r in members}
 for r in c['historical_Git_bodies']:
  b=subprocess.check_output(['git','-C',r['repository'],'show',r['source']+':'+r['Git_path']],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'));assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
 space=os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize
 if sys.argv[3]=='before':assert space>=c['workspace_floor_bytes'],'SOURCE_LIGHT_WORKSPACE_CAPACITY_HOLD'
 print(json.dumps({'status':'PASS','stage':sys.argv[3],'source':c['source'],'tree':c['tree'],'source_rows':1441,'prepared':30,'native_historical_members':1192,'five_prefix_metadata':'EXACT_NOT_FRESH_ORIGIN_PROBE','workspace_bytes':space,'native_qualification':'NOT_RUN'}))
if __name__=='__main__':main()
