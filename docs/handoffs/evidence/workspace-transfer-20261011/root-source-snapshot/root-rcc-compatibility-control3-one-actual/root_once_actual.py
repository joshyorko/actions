import hashlib,json,os,stat,subprocess,sys,time
from pathlib import Path
D=Path(__file__).parent;P=Path('/workspace/engineering/rcc-compatibility-actual-runner-readonly-preparation');O=P/'OWNERFINAL-current-b614-runnable-three-version-RCC-compatibility-proposal-v2.json';CFG=P/'FROZEN-control3-current-b614-actual-config-v2.json';OH='50bb3864ab95e6cfca705a8a0f6112e87b3fc56b0e513c19e12d856c3ea3a095';CH='8c5da5be25ebfcf86f286ee9f93ddad328c68b3243b0935ec5937c93376bb948'
def sh(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sh(p)}
def write(n,d):
 p=D/n;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w') as f:json.dump(d,f,indent=2);f.write('\n')
 return p
assert len(sys.argv)==4 and sys.argv[1]=='--root-execute-reviewed-one-control3'
IND=Path(sys.argv[2]);assert sh(IND)==sys.argv[3]
assert sh(O)==OH and sh(CFG)==CH
owner=json.loads(O.read_bytes());cfg=json.loads(CFG.read_bytes());W=Path(cfg['source_root'])
def guard():
 for row in owner['bindings']:
  p=Path(row['path']);assert sh(p)==row['sha256'] and p.stat().st_size==row['bytes']
  if 'mode' in row:assert stat.S_IMODE(p.stat().st_mode)==int(str(row['mode']),8)
 assert sh(O)==OH and sh(CFG)==CH and sh(IND)==sys.argv[3]
 assert subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip()==cfg['source']
 assert subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD^{tree}'],text=True).strip()==cfg['tree']
 assert not subprocess.check_output(['git','-C',str(W),'status','--porcelain'],text=True)
 for row in cfg['source_body_modes']:
  p=W/row['path'];s=p.lstat();b=os.fsencode(os.readlink(p)) if row['mode']=='120000' else p.read_bytes()
  assert hashlib.sha256(b).hexdigest()==row['sha256'] and stat.S_IMODE(s.st_mode)==row['fs_mode']
 for row in cfg['native_original_members']:
  p=Path(cfg['native_original_root'])/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
  if row['kind']=='file':assert not p.is_symlink() and sh(p)==row['content_sha256']
  elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
  else:assert p.is_symlink() and os.readlink(p)==row['link_target']
 assert {p.relative_to(cfg['native_original_root']).as_posix() for p in Path(cfg['native_original_root']).rglob('*')}=={r['path'] for r in cfg['native_original_members']}
 return {'bindings':len(owner['bindings']),'source_body_modes':len(cfg['source_body_modes']),'native_members':len(cfg['native_original_members']),'status':'PASS'}
def free(p):
 s=os.statvfs(p);return s.f_bavail*s.f_frsize
before=guard();capacity={'workspace_free_bytes':free('/workspace'),'devshm_free_bytes':free('/dev/shm'),'root_workspace_floor_bytes':1288490189,'root_devshm_floor_bytes':3865470567}
assert capacity['workspace_free_bytes']>=capacity['root_workspace_floor_bytes'] and capacity['devshm_free_bytes']>=capacity['root_devshm_floor_bytes']
assert not Path(cfg['owned_root']).exists()
write('root-fresh-preconditions.json',{'source':cfg['source'],'tree':cfg['tree'],'guard':before,'capacity':capacity,'independent_review':bind(IND),'transport_owner':bind(O),'no_other_heavy_or_devshm_mutations':True})
release=write('root-one-control3-release.json',owner['required_first_ROOT_release_body']);rh=sh(release)
argv=owner['planned_first_outer_launch']['argv'];argv=[str(release) if x=='ROOT_ONCE_OWNER_RELEASE_PATH_REQUIRED' else rh if x=='ROOT_ANNOUNCED_RELEASE_SHA256_REQUIRED' else x for x in argv]
activation='set -e\nsource /workspace/actions-cloud/activate.sh\nexport PYTEST_XDIST_AUTO_NUM_WORKERS=2\n/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python /workspace/engineering/rcc-compatibility-actual-runner-readonly-preparation/managed_metadata_only_preflight.py\nexec "$@"\n'
command=['bash','-c',activation,'root-one-control3',*argv]
write('root-one-attempt-consumed.json',{'release':bind(release),'command':command,'source':cfg['source'],'tree':cfg['tree'],'no_automatic_retry':True})
start=time.monotonic();rc=None;exception=None;post=None;post_error=None
log=D/'original-outer-launch.private.log'
with log.open('xb') as stream:
 os.chmod(log,0o600)
 try:
  cp=subprocess.run(command,cwd=W,stdout=stream,stderr=subprocess.STDOUT);rc=cp.returncode
 except BaseException as e:exception=type(e).__name__
 finally:
  try:post=guard()
  except BaseException as e:post_error=type(e).__name__
actual=Path(cfg['owned_root'])/'OWNERFINAL-one-version-actual-result.json'
result={'root_outer_returncode':rc,'root_exception_class':exception,'post_guard':post,'post_guard_error_class':post_error,'seconds':time.monotonic()-start,'log':bind(log),'actual_result':bind(actual) if actual.is_file() else None,'status':'PASS_TO_REVIEW' if rc==0 and post and actual.is_file() else 'FAIL_HOLD','release':bind(release),'independent_review':bind(IND),'remaining_versions':'NOT_RUN; distinct acceptance/config/review/release required','capacity_after':{'workspace_free_bytes':free('/workspace'),'devshm_free_bytes':free('/dev/shm')}}
t=write('OWNERFINAL-root-one-control3-terminal.json',result);print(json.dumps(bind(t)));sys.exit(0 if result['status']=='PASS_TO_REVIEW' else 1)
