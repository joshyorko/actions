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
def main():
 assert len(sys.argv)==4 and sys.argv[3] in ('before','after') and sys.flags.optimize==0
 p=Path(sys.argv[1]);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink() and stat.S_IMODE(m.st_mode)==0o400
 assert digest(p)==sys.argv[2];c=json.loads(p.read_bytes());root=Path(c['source_root'])
 assert Path(sys.prefix).resolve()==Path(c['cached_prefix']).resolve()
 assert 'PYTHONOPTIMIZE' not in os.environ and 'PYTEST_ADDOPTS' not in os.environ
 for k,v in c['expected_activation'].items():assert os.environ[k]==v,k
 assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
 for k in c['forbidden_actual_operator_exports']:assert k not in os.environ,k
 for r in c['bindings']:exact(r)
 assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD','HEAD^{tree}'],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')).decode().splitlines()==[c['source'],c['tree']]
 assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain'],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
 rows=json.loads(Path(c['source_inventory']['path']).read_bytes());assert len(rows)==c['source_leaf_count']==1441
 for r in rows:
  p=root/r['path'];m=p.lstat()
  if r['mode']=='120000':assert stat.S_ISLNK(m.st_mode);b=os.readlink(p).encode();assert hashlib.sha256(b).hexdigest()==r['sha256']
  else:assert stat.S_ISREG(m.st_mode);assert digest(p)==r['sha256'];assert bool(m.st_mode&0o111)==(r['mode']=='100755')
  assert stat.S_IMODE(m.st_mode)==r['fs_mode']
 assert len(c['prepared30'])==30
 for n,h in c['prepared30'].items():assert digest(root/n)==h,n
 assert len(c['five_prefix_bindings'])==5
 for r in c['five_prefix_bindings']:exact(r)
 for package,module in c['origin_packages']:
  # Existence only here. ROOT-authorized package probes must establish actual prefixes/origins later.
  assert (root/package/'.venv/bin/python').is_file()
 baseline=json.loads(Path(c['native_baseline']['path']).read_bytes());members=baseline['native_original_members'];native=Path(baseline['native_original_root']);assert len(members)==1192
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
