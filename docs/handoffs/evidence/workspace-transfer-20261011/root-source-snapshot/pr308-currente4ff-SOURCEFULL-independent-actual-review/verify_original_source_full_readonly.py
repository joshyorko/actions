import ast,collections,hashlib,json,os,pathlib,re,stat,subprocess,tarfile
D=pathlib.Path('/workspace/engineering/pr308-currente4ff-SOURCEFULL-independent-actual-review');R=pathlib.Path('/workspace/engineering/root-pr308-currente4ff-one-sourcefull-v2');HEAD='e4ff080375a8422bb656e52d218f198521dda078';TREE='973ff38f49a17a896e4d90f829a72e2ea0ea15e8';REPO=pathlib.Path('/workspace/engineering/pr308')
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_bytes())
def bind(p):
 p=pathlib.Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def verify(r):
 p=pathlib.Path(r['path']);assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
 if 'mode' in r:assert oct(stat.S_IMODE(p.stat().st_mode))==r['mode']
 return bind(p)
owner_path=R/'OWNERFINAL-root-currente4ff-configured-SOURCEFULL-PASS-v2.json';owner=load(owner_path);assert owner_path.stat().st_size==3589 and sha(owner_path)=='fb8a58b643957e72ba1d53d2216d4b73ac42b5e57235b2510f3159f667a2c1a0';assert owner['source']==HEAD and owner['tree']==TREE and owner['source_count']==1423;assert owner['native_execution']=='NOT_RUN' and owner['prodpins']=='18.19.3_UNCHANGED'
refs=[verify(owner[k]) for k in ('currente4ff_LIGHT','independent_LIGHT','preexecution','independent_preexecution','original_terminal','original_log','original_root_outer_terminal','complete_private_node_census','original_metadata_parser_FAIL')]
light=load(owner['currente4ff_LIGHT']['path']);indlight=load(owner['independent_LIGHT']['path']);assert indlight['decision']=='GO_CURRENT_E4FF_SOURCE_LIGHT_ONLY';verify(indlight['independent_proof']);assert indlight['source']['commit']==HEAD and indlight['source']['tree']==TREE
proposal=load(owner['preexecution']['path']);indpre=load(owner['independent_preexecution']['path']);assert indpre['status']=='GO_CONDITIONAL_NAMED_V2_CURRENT_E4FF_SOURCEFULL_PREEXECUTION_ONLY';assert indpre['owner']['sha256']==owner['preexecution']['sha256'];assert proposal['source']==HEAD and proposal['tree']==TREE
bindings=[verify(r) for r in proposal['frozen_input_bindings']];assert len(bindings)==23
config_path=next(pathlib.Path(r['path']) for r in proposal['frozen_input_bindings'] if pathlib.Path(r['path']).name=='frozen-current-source-full-inputs-v2.json');cfg=load(config_path);assert cfg['head']==HEAD and cfg['tree']==TREE and cfg['source_root']==str(REPO);assert len(cfg['expected_activation_exports'])==18;assert cfg['capacity_floor_bytes']==1288490188;assert len(cfg['concrete_origin_packages'])==5;assert len(cfg['forbidden_actual_operator_exports'])==6 and 'PYTHONOPTIMIZE' in cfg['forbidden_actual_operator_exports'];assert 'ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG' in cfg['forbidden_actual_operator_exports'];assert cfg['expected_activation_exports']['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
for r in cfg['implementation_bindings']+cfg['prepared_environment_and_RCC_bindings']:verify(r)
map_path=pathlib.Path(cfg['exact_historical_failed_receipt_mapping']['path']) if isinstance(cfg['exact_historical_failed_receipt_mapping'],dict) else pathlib.Path(cfg['exact_historical_failed_receipt_mapping']);mapping=load(map_path);assert sha(map_path)=='cc73027ce86ea0965f3bdd88ed3398c322dcf012b337a4ca161966f19ffee6c7';assert not pathlib.Path(mapping['original_binding']['path']).exists();assert cfg['historical_original_receipt_path']==mapping['original_binding']['path']
for k in ('archive','complete_index','expanded_removal','root_original_terminal'):verify(mapping[k])
member=None
with tarfile.open(mapping['archive']['path'],'r|gz') as t:
 for m in t:
  if m.name==mapping['member']:
   assert m.isfile() and m.mode==0o600 and (m.uid,m.gid)==(1000,1000);member=t.extractfile(m).read();break
assert member is not None and len(member)==1696 and hashlib.sha256(member).hexdigest()==mapping['original_binding']['sha256'];actual_old=json.loads(member);assert actual_old['status']=='FAIL' and actual_old['source']=='b614864ba9da55c13662894b6ef3c8515d9fdb25';assert actual_old['exception_class']=='ProcessTreeCleanupError'
lightrefs=[]
for r in light['frozen_bindings']:
 if r['path']==mapping['original_binding']['path']:assert r==mapping['original_binding'];lightrefs.append(dict(r,resolution='EXACT_ARCHIVE_ORIGINAL_MEMBER_PHYSICAL_ALIAS_ABSENT'))
 else:lightrefs.append(verify(r))
assert len(lightrefs)==31
terminal=load(owner['original_terminal']['path']);outer=load(owner['original_root_outer_terminal']['path']);assert terminal['status']=='PASS' and terminal['full_started'] is True and terminal['primary_returncode']==terminal['post_returncode']==0 and terminal['primary_error_class'] is terminal['post_error_class'] is None;assert terminal['records']==[{'returncode':0,'stage':'before'},{'returncode':0,'stage':'configured-full'},{'returncode':0,'stage':'after-always'}];assert terminal['one_attempt']=='CONSUMED_NO_RETRY' and terminal['native_or_new_RCC_actual']=='NOT_RUN';assert outer['returncode']==0 and outer['attempts']==1 and outer['source']==HEAD and outer['tree']==TREE;assert outer['native_new_Rcc']=='NOT_RUN';verify(outer['original_outer_output'])
releasepath=R/'root-one-distinct-current-sourcefull-authorization.json';release=load(releasepath);assert sha(releasepath)==outer['root_authorization_sha256'];assert release=={'schema':1,'status':'ROOT_RELEASE_ONE_SERIALIZED_CONFIGURED_SOURCE_FULL','proposal_sha256':owner['preexecution']['sha256'],'source':HEAD,'tree':TREE,'independent_source_and_preexecution_review_GO':True,'serialized_no_other_heavy_or_installer':True};assert type(release['schema']) is int
text=pathlib.Path(owner['original_log']['path']).read_text();rows=[{'worker':w,'outcome':o,'node':n} for w,o,n in re.findall(r'^\[(gw\d+)\]\s+\[\s*\d+%\]\s+(PASSED|SKIPPED|FAILED|ERROR)\s+(.+?)\s*$',text,re.M)];assert len(rows)==1440 and len({r['node'] for r in rows})==1440;assert set(r['worker'] for r in rows)=={'gw0','gw1'};assert collections.Counter(r['outcome'] for r in rows)=={'PASSED':1427,'SKIPPED':13};recorded=load(owner['complete_private_node_census']['path']);assert len(recorded)==1440 and {tuple(sorted(r.items())) for r in recorded}=={tuple(sorted(r.items())) for r in rows}
assert re.search(r'1427 passed, 13 skipped, 15 warnings in 103\.73s',text);assert owner['full']=={'passed':1427,'skipped':13,'failed':0,'error':0,'complete_unique_nodes':1440,'workers':['gw0','gw1'],'seconds':103.73,'warnings':15}
phases=[]
for line in text.splitlines():
 if line.startswith('{'):
  try:a=json.loads(line)
  except ValueError:continue
  if a.get('stage') in ('before','after'):phases.append(a)
assert [a['stage'] for a in phases]==['before','after']
for a in phases:assert a['status']=='PASS' and a['source']==HEAD and a['tree']==TREE and a['source_leaves']==1423 and a['native_original']==1192 and a['five_concrete_origins']==5
assert phases[0]['workspace_available_bytes']>=cfg['capacity_floor_bytes']
cache_rows=[r for r in rows if '::test_owned_rcc_package_cache_' in r['node']];assert len(cache_rows)==34 and all(r['outcome']=='PASSED' for r in cache_rows)
# Every complete recorded node is tied to a current immutable real source definition; parameter spaces retained.
modules={};method_count=0
for r in rows:
 parts=r['node'].split('[',1)[0].split('::');module=parts[0];name=parts[-1]
 if module not in modules:
  p=REPO/'action_server'/'tests'/module;assert p.is_file();a=ast.parse(p.read_bytes());modules[module]={n.name for n in ast.walk(a) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
 assert name in modules[module];method_count+=1
assert method_count==1440
oldparse=load(owner['original_metadata_parser_FAIL']['path']);assert oldparse['status']=='ROOT_CENSUS_METADATA_INSPECTOR_V1_FAIL_RETAINED_NO_SOURCE_RERUN'
# Current full source bodies, typed tree, executable bits and own prepared inputs are independently re-read, no helper import.
git=lambda *a:subprocess.check_output(['git','--no-optional-locks','-C',str(REPO),*a]);assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[HEAD,TREE];assert not git('status','--porcelain');tree={}
for r in git('ls-tree','-rz','HEAD').split(b'\0'):
 if r:
  m,p=r.split(b'\t',1);mode,kind,blob=m.decode().split();tree[p.decode()]={'mode':mode,'kind':kind,'blob':blob}
source=load(cfg['source_inventory']);assert len(source)==len(tree)==1423
for r in source:
 assert tree[r['path']]=={k:r[k] for k in ('mode','kind','blob')};p=REPO/r['path'];bb=os.readlink(p).encode() if p.is_symlink() else p.read_bytes();assert len(bb)==r['bytes'] and hashlib.sha256(bb).hexdigest()==r['sha256'];assert stat.S_IMODE(p.lstat().st_mode)==r['fs_mode']
reuse=load(REPO.parent/'pr308-cache-current-e3c-source/own-current30-input-and-five-concrete-origins-Bootstrap-reuse.json');assert len(reuse['inputs'])==30 and len(reuse['origins'])==5
for p,h in reuse['inputs'].items():assert sha(REPO/p)==h
native=load(cfg['original_native_config']);assert len(native['native_original_members'])==1192;nroot=pathlib.Path(native['native_original_root']);seen=set()
for r in native['native_original_members']:
 p=nroot/r['path'];seen.add(r['path']);assert stat.S_IMODE(p.lstat().st_mode)==r['mode']
 if r['kind']=='file':assert p.is_file() and not p.is_symlink() and sha(p)==r['content_sha256']
 elif r['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert p.is_symlink() and os.readlink(p)==r['link_target']
assert {p.relative_to(nroot).as_posix() for p in nroot.rglob('*')}==seen
bounds=proposal['execution_bounds'];assert bounds['outer_GNU_timeout_seconds']==900 and bounds['outer_KILL_grace_seconds']==10;assert bounds['parent_configured_subprocess_timeout_seconds']==640 and bounds['source_GNU_timeout_seconds']==600 and bounds['source_KILL_grace_seconds']==10 and bounds['always_post_guard_timeout_seconds']==60 and bounds['pre_guard_timeout_seconds']==60
canonical=next(pathlib.Path(r['path']) for r in proposal['frozen_input_bindings'] if pathlib.Path(r['path']).name=='canonical-exact-historical-receipt-archive-alias-proposed.patch')
assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain')
proof={'schema':1,'status':'PASS_ORIGINAL_CURRENT_E4FF_SOURCEFULL_DATA_REVIEW','owner':bind(owner_path),'actual_bindings':refs,'preexecution23_bindings':bindings,'current_LIGHT31_bindings':lightrefs,'current_source':{'head':HEAD,'tree':TREE,'complete_typed_git_FS_bytes_modes':1423,'clean':True},'root_release':bind(releasepath),'full':owner['full'],'original_before_primary_post_returncodes':[0,0,0],'original_rootouter_returncode':0,'original_parent_seconds':terminal['seconds'],'original_rootouter_seconds':outer['elapsed_seconds'],'actual_phase_guards':phases,'activation_proof':'18 exact exports plus PATH =19; xdist2 and6 prohibited exports including5 actual RCC controls+PYTHONOPTIMIZE','current_real_definition_module_count':len(modules),'all1440_nodes_tied_to_current_real_source_definitions':True,'parameterized_node_names_containing_spaces':sum(' ' in r['node'] for r in rows),'cache_guard_full_nodes':34,'own_Bootstrap30_inputs_rehashed':True,'five_concrete_origins':'actual before and after guard asserted through unchanged canonical own package interpreter probes; retained recording plus current prefix bindings','native1192_body_modes_links_and_exact_pathset':'PASS_DATA_ONLY_NOT_CURRENT_NATIVE_QUALIFICATION','historical_original_failed_result_archive_alias':'EXACT8dc25/1696/0600/UIDGID1000_originalFAIL; no restoration or upgrade','archive_map':bind(map_path),'independent_full_archive_member_scope':'needed member only plus compressed archive SHA; whole archive proof separately retained by preservation owner','root_initial_parser_failure':'Original token regex truncated space-containing parameters, undercounted uniqueness1426; immutable original metadataFAIL retained; complete-line parser1440 sameoriginal/no testsrerun','current_FULL_not_historical_b614_full':True,'new_RCC_actual':'NOT_RUN','production_Rcc_pin':'18.19.3_UNCHANGED','canonical_archive_alias_patch':bind(canonical),'upstream_disposition':'none'}
f=D/'independent-current-e4ff-original-sourcefull-proof.json';assert not f.exists();f.write_text(json.dumps(proof,indent=2)+'\n');f.chmod(0o600);print(json.dumps(bind(f)))
