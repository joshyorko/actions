import datetime,difflib,hashlib,json,os,stat,subprocess
from pathlib import Path
ROOT=Path('/workspace/engineering/rcc-memory17-original-mode-admission-failure-independent-review');os.umask(0o077)
def row(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def put(name,v):
 p=ROOT/name
 if not isinstance(v,str):v=json.dumps(v,indent=2,sort_keys=True)+'\n'
 with p.open('x') as f:f.write(v);f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
old=Path('/workspace/engineering/root-memory17-reviewed-original-outer')
owner=old/'OWNERFINAL-root-one-original-reviewed-memory17-outer.json';assert row(owner)['sha256']=='277e37a3be16f8bd6c5bd8945c656bec37284ae7e2cda396b20a3142c809c650'
o=json.loads(owner.read_bytes());assert o['returncode']==1 and o['elapsed_seconds']<1
pre=json.loads((old/'verified-exact-ROOT-physical-preflight.json').read_bytes());assert pre['ROOT_adopts_preflight_and_releases_one_serialized_pure17_only'] is True and pre['root_and_children_absent'] is True
for r in pre['physical_files']+[pre['release'],pre['review'],pre['preflight_contract']]:assert row(r['path'])==r
stderr=(old/'original.stderr.private').read_text();assert stderr.rstrip().endswith('ValueError: MEMORY17_PRIMARY_RCC_PIN_NO_EXECUTION')
assert (old/'original.stdout.private').read_bytes()==b''
managed=Path('/workspace/actions-cloud/bin/rcc');fixture=Path('/workspace/engineering/pr308/action_server/src/actions/server/bin/rcc-18.19.3')
m=row(managed);f=row(fixture);assert m['sha256']==f['sha256']=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
assert m['mode']=='0o700' and f['mode']=='0o711' and m['bytes']==f['bytes']==22282402
ms=managed.lstat();fs=fixture.lstat();assert (ms.st_uid,ms.st_gid)==(fs.st_uid,fs.st_gid)==(1000,1000)
oldcfg=Path('/workspace/engineering/rcc-memory17-pure-controls-concrete-preexecution-NOTRUN/FROZEN-memory17-pure-control-config-NOTRUN-v2.json');cfg=json.loads(oldcfg.read_bytes())
oldlauncher=Path(cfg['launcher']['path']);assert row(oldlauncher)==cfg['launcher']
assert "stat.S_IMODE(rcc.stat().st_mode)==0o711" in oldlauncher.read_text()
for r in cfg['frozen_bindings']:assert row(r['path'])==r
assert not Path('/workspace/engineering/root-one-memory17-pure-controls-20261011-1').exists()
repo=Path('/workspace/engineering/pr308');qualified=json.loads(Path(cfg['source_guard_config']['path']).read_bytes())
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip()==cfg['source']
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD^{tree}']).decode().strip()==cfg['tree']
assert subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1'])==b''
entries={}
for b in subprocess.check_output(['git','-C',str(repo),'ls-tree','-rz','HEAD']).split(b'\0'):
 if b:
  head,name=b.split(b'\t',1);entries[name.decode()]=head.split(b' ')
assert len(entries)==len(qualified['source_body_modes'])==1440
for r in qualified['source_body_modes']:
 mode,kind,oid=entries[r['path']];assert mode.decode()==r['mode'] and kind==b'blob' and oid.decode()==r['object']
 p=repo/r['path'];raw=os.readlink(p).encode() if r['mode']=='120000' else p.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==r['sha256'] and stat.S_IMODE(p.lstat().st_mode)==r['fs_mode']
guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md');text=guide.read_text();anchor='Use separate owned before/after captures and refuse a reused capture path.\n';assert text.count(anchor)==1
paragraph='''
Permission modes belong to their measured owning paths, even when binary digests
match. The managed primary RCC and an ignored checkout fixture can legitimately
have different modes. Admit each exact regular, nonsymlink path with its own
owner, group, size, digest and mode before delegation; do not borrow the fixture
mode or chmod the managed binary to satisfy a mistaken guard. A failed admission
before the owned output root, source guards and tests still consumes that one
release. Preserve it and bind any correction to a fresh namespace and release.
'''
patch=put('canonical-measured-per-path-binary-mode-before-delegation-proposed.patch',''.join(difflib.unified_diff(text.splitlines(True),text.replace(anchor,anchor+paragraph).splitlines(True),fromfile='a/docs/skills/repository-operations.md',tofile='b/docs/skills/repository-operations.md')))
receipt={'schema':1,'decision':'HOLD_ORIGINAL_MEMORY17_PRE_TEST_MODE_ADMISSION_FAILED_NO_PURE_TEST_CENSUS','original_owner':row(owner),'original_raw_bindings':[row(p) for p in sorted(old.iterdir()) if p.is_file()],'original_release':o['release'],'prior_independent_PREEXEC':o['review'],'source':cfg['source'],'tree':cfg['tree'],'source_unchanged_current1440':'EXACT_COMPLETE_TYPED_GIT_OBJECT_SET_AND_CURRENT_FS_BODY_MODES_VERIFIED_READONLY','actual_returncode':1,'elapsed_seconds':o['elapsed_seconds'],'safe_error_category':'MEMORY17_PRIMARY_RCC_PIN_NO_EXECUTION','managed_primary':{**m,'uid':ms.st_uid,'gid':ms.st_gid,'type':'REGULAR_NONSYMLINK'},'ignored_fixture':{**f,'uid':fs.st_uid,'gid':fs.st_gid,'type':'REGULAR_NONSYMLINK'},'diagnosis':'Original launcher incorrectly applies fixture0711mode to managedprimary0700; exactSHA/size equal. Physical ROOTpreflight passed. Activation18/PATH2 checks precede this assertion and returned; no ownedroot/beforeguard/source-tests/native pipeline reached.','reviewer_correction':'Prior710c PREEXEC review missed path-specific managedmode mismatch; original review retained, not rewritten.','original_guards':'NOT_RUN_BECAUSE_ACTIVATION_ADMISSION_FAILED','own_five_origin_probes':'NOT_RUN','owned_output_root':'ABSENT','original_JUnit':'ABSENT','pure17_counts':'UNAVAILABLE_NOT_ZERO_OR_PASS','native':'NOT_RUN','policy_adoption':'NONE','release_consumption':'CONSUMED_ORIGINAL_ONCE_RELEASE_EVEN_THOUGH_OUTPUTROOT_ABSENT','required_correction':'Named launcher/config/root-once2/release/indreview; measuredmanagedpath700regularUIDGID1000sizeSHA; no chmod/modebypass/helpertestchange/oldrelease retry.','remaining_uncertainty':['Corrected pure17 controls NOT_RUN; no memory policy/native calibration.','Readonly source body preservation does not retroactively run skipped guards or native processes.'],'documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta':patch,'durable_learning':'Per-path mode admission before delegation; samebinarybytes do not require fixture/managedpermissions equal; failed admission consumes once release.','evidence':'Original managedRCCguard line69/ValueError; regularmanaged700andignoredfixture711 exactsame7e588sizeUIDGID measuredread-only; source1440 unchanged.','stale_or_ambiguous_guidance_removed':'Implicit managedmode==fixturemode; outputrootabsence does not authorize release reuse.','remaining_uncertainty':'Corrected bounded attempt andmemory17 outcomes await separate review andROOTrelease.'},'upstream_disposition':'none','capture':datetime.datetime.now(datetime.timezone.utc).isoformat()}
r=put('OWNERFINAL-independent-original-memory17-managed-mode-admission-FAIL-and-source-preservation.json',receipt)
print(json.dumps({'review':r,'canonical':patch}))
