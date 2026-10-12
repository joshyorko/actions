import ast,hashlib,json,os,pathlib,stat,subprocess,tarfile,xml.etree.ElementTree as ET
BASE=pathlib.Path('/workspace/engineering/pr308-cache-current-e3c-source'); OUT=pathlib.Path('/workspace/engineering/pr308-currente4ff-independent-SOURCE-LIGHT-review'); REPO=pathlib.Path('/workspace/engineering/pr308')
HEAD='e4ff080375a8422bb656e52d218f198521dda078'; TREE='973ff38f49a17a896e4d90f829a72e2ea0ea15e8'; APP='6d92344c28a17a727944559fd52f28305ee8eff2'; TARGET='e3c29cde8878307912e55ed09b6436c0f91d06d5'; OLD='b614864ba9da55c13662894b6ef3c8515d9fdb25'
def sha(b):return hashlib.sha256(b).hexdigest()
def filehash(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_bytes())
def bind(p):
 p=pathlib.Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':filehash(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def verify(r):
 p=pathlib.Path(r['path']);assert p.stat().st_size==r['bytes'];assert filehash(p)==r['sha256'];assert oct(stat.S_IMODE(p.stat().st_mode))==r['mode'];return bind(p)
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(REPO),*args])
def leaves(ref):
 out={}
 for v in git('ls-tree','-rz',ref).split(b'\0'):
  if not v:continue
  a,p=v.split(b'\t',1);mode,kind,blob=a.decode().split();out[p.decode()]={'mode':mode,'kind':kind,'blob':blob}
 return out
ownerpath=BASE/'OWNERFINAL-current-e4ff-reviewed-cache-application-and-e3c-ordinary-source-LIGHT.json';owner=load(ownerpath);assert ownerpath.stat().st_size==13921 and filehash(ownerpath)=='e18d871d9daf93e21e0b34610af31e9d4198bc4a1c93431d8799464954d37c6c'
assert git('rev-parse','HEAD').decode().strip()==HEAD;assert git('rev-parse','HEAD^{tree}').decode().strip()==TREE;assert git('show','-s','--format=%P',HEAD).decode().strip().split()==[APP,TARGET];assert not git('status','--porcelain');assert git('show','-s','--format=%P',APP).decode().strip()==OLD
current=leaves(HEAD);application=leaves(APP);target=leaves(TARGET);old=leaves(OLD);assert len(current)==1423 and set(current)==set(application)|set(target)
novel=[p for p,r in current.items() if r!=application.get(p) and r!=target.get(p)];assert novel==['docs/skills/repository-operations.md']
rows=load(BASE/'private-current-e4ff-complete-source-body-mode-inventory.json');assert len(rows)==1423
for r in rows:
 p=REPO/r['path'];assert current[r['path']]=={k:r[k] for k in ('mode','kind','blob')};content=os.readlink(p).encode() if p.is_symlink() else p.read_bytes();assert len(content)==r['bytes'] and sha(content)==r['sha256'];assert stat.S_IMODE(p.lstat().st_mode)==r['fs_mode'];assert (bool(p.stat().st_mode&0o111)==(r['mode']=='100755')) if not p.is_symlink() else True
# Historical physical alias is separately archive-backed; no restoration.
map_path=pathlib.Path('/workspace/engineering/root-failed-control3-one-byte-preservation-v4/root-exact-historical-failed-member-archive-mapping.json');mapping=load(map_path);assert map_path.stat().st_size==1864 and filehash(map_path)=='cc73027ce86ea0965f3bdd88ed3398c322dcf012b337a4ca161966f19ffee6c7'
archive_records=[verify(mapping[k]) for k in ('archive','complete_index','expanded_removal','root_original_terminal')]
member_data=None
with tarfile.open(mapping['archive']['path'],'r|gz') as t:
 for m in t:
  if m.name==mapping['member']:
   assert m.isfile() and m.size==1696 and m.mode==0o600 and (m.uid,m.gid)==(1000,1000);member_data=t.extractfile(m).read();break
assert member_data is not None and sha(member_data)==mapping['original_binding']['sha256'];assert not pathlib.Path(mapping['original_binding']['path']).exists()
a= json.loads(member_data);assert a['status']=='FAIL' and a['admission_failure_code']=='OUTER_PRIMARY_OR_CLEANUP_FAILED';assert a['source']==OLD and a['tree']=='6fa4f5c1e9837a0d893868255575b355b3977fae';assert a['exception_class']=='ProcessTreeCleanupError'
verified=[];archive_aliases=0
for r in owner['frozen_bindings']:
 if r['path']==mapping['original_binding']['path']:
  assert r==mapping['original_binding'];archive_aliases+=1;verified.append(dict(r,resolution='EXACT_ARCHIVE_MEMBER_ORIGINAL_PATH_ABSENT'))
 else:verified.append(verify(r))
assert len(verified)==31 and archive_aliases==1
fixture='action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py';assert current[fixture]==application[fixture];assert current['.github/workflows/_gen_workflows.py']==old['.github/workflows/_gen_workflows.py']
patchpath=pathlib.Path('/workspace/engineering/pr308-owned-package-cache-private-source/owned-package-cache-two-path.patch');assert filehash(patchpath)=='aa2b0b1d008a717915764a4ddc97b8a60386b10afe63824ef23b4b487e2ece21'
import re
lines=patchpath.read_text().splitlines(keepends=True);sections=[]
for l in lines:
 if l.startswith('--- a/'):sections.append([])
 if sections:sections[-1].append(l)
changed=[]
for section in sections:
 path=next(l[6:].strip() for l in section if l.startswith('+++ b/'));oldlines=git('show',OLD+':'+path).decode().splitlines(keepends=True);out=[];cursor=0;i=0
 while i<len(section):
  m=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',section[i])
  if not m:i+=1;continue
  begin=int(m.group(1))-1;out+=oldlines[cursor:begin];cursor=begin;i+=1
  while i<len(section) and not section[i].startswith('@@ ') and not section[i].startswith('diff --git '):
   l=section[i]
   if l.startswith(' '):assert oldlines[cursor]==l[1:];out.append(l[1:]);cursor+=1
   elif l.startswith('-'):assert oldlines[cursor]==l[1:];cursor+=1
   elif l.startswith('+'):out.append(l[1:])
   elif l.startswith('\\'):raise AssertionError('unexpected no-newline patch marker')
   i+=1
 out+=oldlines[cursor:];assert ''.join(out).encode()==git('show',APP+':'+path);changed.append(path)
assert set(changed)=={fixture,'docs/skills/repository-operations.md'};assert {p for p in application if application[p]!=old.get(p)}==set(changed)
def top(ref):return ast.parse(git('show',ref+':'+fixture))
aold=top(OLD);anew=top(HEAD);funcs_old={n.name:n for n in aold.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};funcs_new={n.name:n for n in anew.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};mod=lambda a:ast.dump(ast.Module(body=[n for n in a.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))],type_ignores=[]),include_attributes=False)
assert len(funcs_old)==13 and len(funcs_new)==21 and mod(aold)==mod(anew)
expected={'test_published_artifact_details_preserves_one_rcc_identity_pair','test_staged_package_executes_in_managed_rcc_runtime'};modified=[]
for name,fn in funcs_old.items():
 new=funcs_new[name]
 if ast.dump(fn,include_attributes=False)!=ast.dump(new,include_attributes=False):
  modified.append(name);added=[n for n in new.body if isinstance(n,ast.If) and '_prepare_owned_rcc_test_package_cache' in ast.dump(n)];assert len(added)==1;assert 'os.environ' in ast.unparse(added[0]);new.body=[n for n in new.body if n is not added[0]];assert ast.dump(fn,include_attributes=False)==ast.dump(new,include_attributes=False)
assert set(modified)==expected
j=ET.parse(BASE/'current-scoped-source-junit.xml');cases=list(j.iter('testcase'));assert len(cases)==245;assert len({(r.get('classname'),r.get('name')) for r in cases})==245;passed=[r for r in cases if r.find('skipped') is None and r.find('failure') is None and r.find('error') is None];skipped=[r for r in cases if r.find('skipped') is not None];assert len(passed)==244 and len(skipped)==1;cache=[r for r in cases if 'package_cache' in r.get('name','')];assert len(cache)==34 and all(r in passed for r in cache)
reuse=load(BASE/'own-current30-input-and-five-concrete-origins-Bootstrap-reuse.json');assert len(reuse['inputs'])==30 and len(reuse['origins'])==5
for p,h in reuse['inputs'].items():assert filehash(REPO/p)==h
for o in reuse['origins']:assert pathlib.Path(o['prefix']).is_relative_to(REPO) and pathlib.Path(o['python']).exists();assert pathlib.Path(o['origin']).is_relative_to(REPO) and '/src/' in o['origin']
configpath=next(pathlib.Path(r['path']) for r in owner['frozen_bindings'] if pathlib.Path(r['path']).name=='FROZEN-control3-current-b614-actual-config-v2.json');cfg=load(configpath);assert len(cfg['native_original_members'])==1192;root=pathlib.Path(cfg['native_original_root'])
for r in cfg['native_original_members']:
 p=root/r['path'];assert stat.S_IMODE(p.lstat().st_mode)==r['mode']
 if r['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 elif r['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==r['link_target']
 else:assert p.is_file() and not p.is_symlink() and filehash(p)==r['content_sha256']
for p,m in [('/workspace/actions-cloud/bin/rcc',0o700),(str(REPO/'action_server/src/actions/server/bin/rcc-18.19.3'),0o711)]:assert filehash(p)=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428' and stat.S_IMODE(pathlib.Path(p).stat().st_mode)==m
prod=load(BASE/'typed-current-production-and-five-selector-inventory.json');assert len(prod['current'])==275 and len(prod['original_native'])==268
for p,r in prod['current'].items():assert current[p]==r
assert sum(prod['current'].get(p)==r for p,r in prod['original_native'].items())==260;assert len(prod['changed'])==8 and len(prod['added'])==7 and not prod['deleted'];assert prod['five_selectors_current']==prod['five_selectors_original'] and len(prod['five_selectors_current'])==5
for p,r in prod['five_selectors_current'].items():assert current[p]==r
rnd=load(BASE/'current-generator8-allYAML30-roundtrip.json');assert rnd['generated_output_count']==8 and rnd['tracked_YAML_total']==30 and len(rnd['all30_bytes_sha256'])==30
for p,h in rnd['all30_bytes_sha256'].items():assert filehash(REPO/p)==h
canonicalpath=pathlib.Path('/workspace/engineering/pr308-owned-package-cache-independent-private-patch-review/exact-accepted-owned-package-cache-canonical-delta.patch');assert filehash(canonicalpath)=='a68e716ce5cef554024ba6e031237fdeeda528add0bc6a72151245284e149886';canon=canonicalpath.read_text();added=''.join(l[1:] for l in canon.splitlines(keepends=True) if l.startswith('+') and not l.startswith('+++'));assert added in (REPO/'docs/skills/repository-operations.md').read_text()
assert not git('status','--porcelain');assert git('rev-parse','HEAD').decode().strip()==HEAD
proof={'schema':1,'status':'PASS_CURRENT_SOURCE_LIGHT_DATA_REVIEW','source':owner['source'],'complete_typed_git_and_FS_modes':1423,'application_exact_accepted_two_path_patch':True,'union_novel_paths':novel,'original13_functions_unchanged_except_two_optin_calls':True,'new_cache_functions':8,'scoped':{'pass':244,'skip':1,'unique':245,'cache_guards_pass':34,'deselect_recorded':3},'Toolkit_recorded_pass':96,'type_recorded_files':351,'generator_outputs':8,'tracked_YAML':30,'Bootstrap_reuse_inputs':30,'concrete_recorded_own_origins':5,'original_native_members_data_rehashed':1192,'producer':{'current':275,'original':268,'equal':260,'changed':8,'added':7,'five_selected_equal':5,'qualification':'UNQUALIFIED'},'owner':bind(ownerpath),'owner31_bindings':verified,'archive_mapping':bind(map_path),'archive_bound_files':archive_records,'needed_member_exact_sha256':sha(member_data),'needed_member_uid':1000,'needed_member_gid':1000,'needed_member_mode':'0o600','archive_member_scope':'only selected historical1696-byte member independently inspected; archive compressed hash verified, not all49132 members/gzipEOF independently admitted','original_actual_status':a['status'],'original_actual_final_failure_code':a['admission_failure_code'],'original_actual_exception_class':a['exception_class'],'original_capacity_primary':'CAPACITY_THRESHOLD retained separately by original fixture/owner evidence, not equal to final outer failure code','canonical_delta':bind(canonicalpath),'reviewer_inspection_correction':'Prior assertion incorrectly equated final outer failure code to primary capacity category; corrected from exact original member without modification. Not source/test/gate failure.','prohibited_operations_performed':False,'upstream_disposition':'none'}
p=OUT/'independent-current-e4ff-data-source-proof.json';p.write_text(json.dumps(proof,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'proof':bind(p),'status':proof['status']}))
