import ast,hashlib,json,os,re,stat,subprocess
from pathlib import Path
ROOT=Path('/workspace/engineering/pr308');BASE=Path('/workspace/engineering/pr308-rcc-compatibility-source');OUT=Path('/workspace/engineering/pr308-approved-compatibility-independent-source-light-review')
HEAD='b614864ba9da55c13662894b6ef3c8515d9fdb25';PARENT='0a6a9db57484a2bc6d9d49a55de5570aa12ae104';A0D='a0d258a16095b95b1bf9000cb1201cddfaff4779';D5='d5a3d2f53737f4f5380b6ecb7fb93d1a651f005d'
def git(*args):return subprocess.check_output(['git','--no-optional-locks',*args],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def bind(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def entries(rev):
 out={}
 for b in git('ls-tree','-rz',rev).split(b'\x00'):
  if not b:continue
  x,n=b.split(b'\t',1);m,k,h=x.decode().split();out[n.decode()]={'mode':m,'type':k,'blob':h}
 return out
def emit(n,d):
 p=OUT/n
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
 p.chmod(0o600);return bind(p)
owner=BASE/'OWNERFINAL-current-a0d-approved-RCC-compatibility-SOURCE-LIGHT.json';v=bind(owner);assert v['bytes']==25279 and v['sha256']=='336cfca277d8e3b08035af8057e77af580fc7a5cbeb54226ae2140abedb79bba'
d=json.loads(owner.read_bytes());assert len(d['frozen_bindings'])==d['binding_count']==71
for b in d['frozen_bindings']:assert bind(Path(b['path']))==b
assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain')
assert git('show','-s','--format=%T',HEAD).decode().strip()=='6fa4f5c1e9837a0d893868255575b355b3977fae'
assert git('show','-s','--format=%P',HEAD).decode().strip()==PARENT
assert git('show','-s','--format=%P',PARENT).decode().strip()==D5+' '+A0D
maps={r:entries(r) for r in [HEAD,PARENT,A0D,D5]};current=maps[HEAD];old=maps[PARENT];assert len(current)==len(old)==1421
scope=set(d['source']['changed_paths']);changed={n for n in current if current[n]!=old[n]};assert changed==scope and len(scope)==6 and set(current)==set(old)
assert all(current[n]==old[n] for n in current if n not in scope)
full=[]
for n,row in current.items():
 assert row['type']=='blob'
 raw=git('cat-file','blob',row['blob']);p=ROOT/n;mode=p.lstat().st_mode
 assert stat.S_ISREG(mode) and p.read_bytes()==raw
 assert bool(mode&0o111)==(row['mode']=='100755')
 full.append({'path':n,**row,'bytes':len(raw),'sha256':sha(raw),'FS_exec':bool(mode&0o111)})
# The ordinary union retains exact single-parent leaf choices; only the guide is a synthesized shared parent union.
union=[]
for n,row in old.items():
 if row not in [maps[A0D].get(n),maps[D5].get(n)]:union.append(n)
assert union==['docs/skills/repository-operations.md']
assert set(old)==set(maps[A0D])|set(maps[D5])
assert all(maps[A0D][n]==maps[D5][n]==old[n] for n in set(maps[A0D])&set(maps[D5]) if maps[A0D][n]==maps[D5][n])
for f in ['action_server/tests/action_server_tests/test_rcc_runtime_adapter.py','action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py']:
 assert (ROOT/f).read_bytes().startswith(git('show',PARENT+':'+f))
def nodes(raw):
 tree=ast.parse(raw);return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
ast_deltas={}
for f in [n for n in scope if n.endswith('.py')]:
 before=nodes(git('show',PARENT+':'+f));after=nodes((ROOT/f).read_bytes());assert set(before)<=set(after)
 ast_deltas[f]={'changed_existing':sorted(n for n in before if before[n]!=after[n]),'added':sorted(set(after)-set(before))}
assert ast_deltas['action_server/scripts/verify_dakota_rcc_acceptance.py']['changed_existing']==['_verify_rcc','child_environment']
assert ast_deltas['action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py']['changed_existing']==[]
assert ast_deltas['action_server/tests/action_server_tests/test_rcc_runtime_adapter.py']['changed_existing']==[]
assert ast_deltas['action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py']['changed_existing']==['test_published_artifact_details_preserves_one_rcc_identity_pair','test_staged_package_executes_in_managed_rcc_runtime']
assert ast_deltas['action_server/src/actions/server/_rcc_runtime_adapter.py']['changed_existing']==['RccRuntimeDescriptor','_publish_artifact_payload','acquire_artifact','build_exec_command','get_rcc_location','prepare_runtime','verify_rcc_version']
f='action_server/src/actions/server/_rcc_runtime_adapter.py';tree=ast.parse((ROOT/f).read_bytes());const={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['RCC_VERSION','_RCC_TEST_SURFACE','_RCC_ACQUISITION_SHA256','_APPROVED_RCC_TEST_TUPLES']}
assert const['RCC_VERSION']=='v18.19.3' and const['_RCC_ACQUISITION_SHA256']=='0da97bfc63a5e47de1c900e8d37ec55261d8b7ef6f68069a74167afc344c72ad'
assert const['_APPROVED_RCC_TEST_TUPLES']==(('released-18.19.5-linux-amd64','v18.19.5','d1aec7d0bb897a81274423c7a6bb747233f9c263',True,'1a617ad7c736fa67c605e20e5ebe3c7d54b02cd548f733e05c809cf49a48db1e'),('candidate-727-18.19.6-linux-amd64','v18.19.6','727c1ff8b679cdbbe12836e53c87734a1edb0071',False,'be55dadc391ae4ac7dd38356755a1698c595fdf41bd4a0141f8df7cc9d29f00e'))
for f in ['action_server/src/actions/server/_download_rcc.py','action_server/build.py','.github/workflows/_gen_workflows.py','.github/workflows/rcc_provider_rollback.yml']:
 if f in current:assert current[f]==old[f]
# Canonical actual diff is byte-identical to bound patch; no unrelated guide changes.
patch=BASE/'exact-canonical-RCC-compatibility-and-measured-worker-evidence.patch';diff=git('diff',PARENT,HEAD,'--','docs/skills/repository-operations.md');assert diff==patch.read_bytes()
lines=diff.decode().splitlines();add=[l[1:] for l in lines if l.startswith('+') and not l.startswith('+++')];remove=[l for l in lines if l.startswith('-') and not l.startswith('---')];assert len(add)==18 and not remove
# Parse current exact terminal and summaries; no product/pytest invocation in this review.
terminal=json.loads((BASE/'own-cached-final-fixture-GREEN-static-v2-terminal.json').read_bytes());assert all(c['returncode']==0 for c in terminal['commands']) and terminal['all30_inputs_unchanged'] is True and terminal['activation19_exports_verified_before_own_override'] is True
raw=(BASE/'own-cached-final-fixture-GREEN-static-v2-original.log').read_text();assert re.search(r'180 passed, 1 skipped, 3 deselected, 4 warnings',raw) and 'Success: no issues found in 349 source files' in raw
red=(BASE/'RED-root-release-original.log').read_text();assert re.search(r'28 failed, 2 passed, 137 deselected',red)
prepared=json.loads((BASE/'own-Bootstrap-reuse-inputs-and-origins.json').read_bytes());assert len(prepared['inputs_exact_prepared_git_bytes_sha256'])==30
for n,h in prepared['inputs_exact_prepared_git_bytes_sha256'].items():assert sha((ROOT/n).read_bytes())==h
for pkg,row in prepared['own5venvs_current_config_and_python'].items():assert sha((ROOT/pkg/'.venv/pyvenv.cfg').read_bytes())==row['config_sha256']
assert len(terminal['own5_origins'])==5
for o in terminal['own5_origins']:
 assert Path(o['prefix']).is_relative_to(ROOT) and Path(o['origin']).is_relative_to(ROOT) and Path(o['prefix']).is_dir() and Path(o['origin']).is_file()
ret1=json.loads((BASE/'before-source-retained-native-helper-browser-and-V5-proof.json').read_bytes());ret2=json.loads((BASE/'after-source-retained-native-helper-browser-and-V5-proof.json').read_bytes());assert ret1==ret2
assert all(bind(Path(b['path']))==b for b in d['frozen_bindings']) and not git('status','--porcelain')
private=emit('complete-independent-source-body-mode-and-AST-proof.json',{'owner':v,'head':HEAD,'tree':d['source']['tree'],'parents':[PARENT],'ordinary_parents':[D5,A0D],'all1421_complete':full,'ordinary_union_synthesized_paths':union,'six_changed_paths':sorted(scope),'AST_deltas':ast_deltas,'tuple_source_literals':const,'all71_refs_exact_prepost':True})
summary=emit('safe-independent-SOURCE-LIGHT-readback.json',{'status':'PASS_IMMUTABLE_SOURCE_LIGHT_BYTE_SCOPE_AND_RETAINED_GATES_ONLY','owner':v,'head':HEAD,'tree':d['source']['tree'],'parent':PARENT,'ordinary_union_parents':[D5,A0D],'typed_leaves':1421,'all_Git_FS_body_exec_bits_exact':True,'unchanged_nonscope':1415,'changed_paths':sorted(scope),'ordinary_union_synthesized_guide_only':True,'AST_deltas':ast_deltas,'original_adapter_and_public_tests_full_prefix_exact':True,'declared_control_and_default_pins_unchanged':True,'current_adjacent':{'passed':180,'skipped':1,'deselected':3,'warnings':4},'meaningful_initial_RED':{'failed':28,'passed':2,'deselected':137},'all71_bindings_exact_prepost':True,'prepared30_inputs_and_five_own_origins_retained':True,'native_helpers_browser_historical_V5_before_after_exact':True,'canonical_additions':18,'canonical_removals':0,'private_complete_proof':private,'no_test_execution_binary_invocation_source_or_ref_mutation':True})
print(json.dumps(summary))
