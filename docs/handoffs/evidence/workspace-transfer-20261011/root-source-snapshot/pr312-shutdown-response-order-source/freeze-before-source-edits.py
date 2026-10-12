import hashlib,json,os,stat,subprocess
from pathlib import Path
D=Path(__file__).parent;R=Path('/workspace/engineering/runtime-checkout-eol')
def binding(p):
 p=Path(p);z=p.read_bytes();return dict(path=str(p),bytes=len(z),sha256=hashlib.sha256(z).hexdigest())
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a])
head=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip()
assert head=='77065131a0aee63d2b1f8621476374bdde3c7b65' and tree=='edf1801e565692fb3f07b809b3a95b27981fe2fe' and git('status','--porcelain')==b''
entries=[]
for row in git('ls-tree','-r','-z','HEAD').split(b'\0'):
 if not row:continue
 meta,name=row.split(b'\t');mode,kind,blob=meta.decode().split();name=name.decode();p=R/name;s=p.lstat()
 if mode=='120000':assert stat.S_ISLNK(s.st_mode);z=os.readlink(p).encode()
 else:assert stat.S_ISREG(s.st_mode) and bool(s.st_mode&0o111)==(mode=='100755');z=p.read_bytes()
 assert hashlib.sha1(b'blob '+str(len(z)).encode()+b'\0'+z).hexdigest()==blob
 entries.append(dict(path=name,mode=mode,blob=blob,bytes=len(z),sha256=hashlib.sha256(z).hexdigest()))
assert len(entries)==1423
refs={}
def walk(x):
 if isinstance(x,dict):
  if {'path','bytes','sha256'}<=x.keys() and str(x['path']).startswith('/'):
   r={k:x[k] for k in ('path','bytes','sha256')};assert binding(r['path'])==r,r['path'];refs[r['path']]=r
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for y in x:walk(y)
sourcefinal=Path('/workspace/engineering/pr312-actual309-refresh/OWNERFINAL-pr312-current-a0d-SOURCEFINAL.json');final=json.loads(sourcefinal.read_bytes())
assert binding(sourcefinal)['sha256']=='d922c435dd20c585f134bbc9bae76ede367ff2bd40f901c5952fd65ffc64c82b'
walk(final);refs[str(sourcefinal)]=binding(sourcefinal)
old=Path(final['original_SOURCEFINAL']['path']);walk(json.loads(old.read_bytes()))
ind=Path('/workspace/engineering/pr312-current-a0d-independent-sourcefinal-review/OWNERFINAL-independent-pr312-current-a0d-SOURCEFINAL-review.json');assert binding(ind)['sha256']=='9a3bb5b6aa00b01085f22861bfe2605ca2d968019c4920b49ed88d9b88c4237a';walk(json.loads(ind.read_bytes()));refs[str(ind)]=binding(ind)
for p in [Path('/workspace/engineering/pr312-current-a0d-original-Windows-owned/root-one-original-decoded-log-acquisition.json'),Path('/workspace/engineering/pr312-current-a0d-independent-Windows-diagnosis/OWNERFINAL-independent-original-PR312-Windows-shutdown-phase-diagnosis.json')]:
 refs[str(p)]=binding(p);walk(json.loads(p.read_bytes()))
prep=Path('/workspace/engineering/pr312-actual309-refresh/own-Bootstrap-reuse-inputs-and-origins.json');p=json.loads(prep.read_bytes());assert len(p['inputs_exact_prepared_git_bytes_sha256'])==30
for name,h in p['inputs_exact_prepared_git_bytes_sha256'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==h
for name,row in p['own5venvs_current_config_and_python'].items():assert hashlib.sha256((R/name/'.venv/pyvenv.cfg').read_bytes()).hexdigest()==row['config_sha256'] and str((R/name/'.venv/bin/python').resolve())==row['python_resolved']
for f in ['/workspace/actions-cloud/bin/rcc',str(R/'action_server/src/actions/server/bin/rcc-18.19.3')]:assert binding(f)['sha256']=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
for f in ['pre-edit-native1192-helper-browser-retained.json','pre-edit-raw18-frozen50-Node-frontend-retained.json']:refs[str(D/f)]=binding(D/f)
result={'status':'PASS_PRE_SOURCE_EDIT_COMPLETE_TYPED_AND_OLD_ACCEPTANCE_BYTES','head':head,'tree':tree,'branch':git('branch','--show-current').decode().strip(),'clean':True,'entries':entries,'distinct_preserved_refs':list(refs.values()),'ref_count':len(refs),'own30_and_five_configs_exact':True,'no_gate_or_installer_or_native_execution':True,'allowed_novel_paths':['action_server/src/actions/server/_server.py','action_server/tests/action_server_tests/test_shutdown_response_order.py','docs/skills/repository-operations.md'],'currentWindowsfailure_HOLD_unchanged':True,'constructor':binding(__file__),'Upstream_disposition':'none'}
out=D/'immutable-pre-edit-original770-all1423-and-source-final-CI-retention.json'
with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
out.chmod(0o600);print(json.dumps(binding(out)))
