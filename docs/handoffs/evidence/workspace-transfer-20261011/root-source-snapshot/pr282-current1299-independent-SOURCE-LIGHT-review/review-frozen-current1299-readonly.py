from pathlib import Path
import ast,collections,copy,difflib,hashlib,json,os,stat,subprocess,xml.etree.ElementTree as ET
D=Path(__file__).parent;ROOT=Path('/workspace/engineering');R=ROOT/'pr282';O=ROOT/'pr282-current-a54-source-LIGHT'
H='1299cc4bb6586f467d36ca124faaaaa77362695f';T='afe2679cc93bf27fa5021c7698ee7ad3ee21a1b9';A='c35ee2e279eaefe55b16aecdb80da04c590aff7c';B='a54c982462d1e7ad011d8152bfc299d997503fb3';ORIGINAL='9c8f1c95caeded6495877280ed1465fd9850b254'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def load(p):return json.loads(Path(p).read_text())
def check(row):
 p=Path(row['path']);q=bind(p);assert q['sha256']==row['sha256']
 if 'bytes' in row:assert q['bytes']==row['bytes']
 if 'mode' in row:assert q['mode']==row['mode']
 return q
def git(*a,cwd=R):return subprocess.check_output(['git','-C',str(cwd),*a],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
def typed(s,paths=()):
 out={}
 for row in git('ls-tree','-rz',s,'--',*paths).split(b'\0'):
  if row:
   pre,p=row.split(b'\t');mode,kind,blob=pre.decode().split();assert kind=='blob';out[p.decode()]={'mode':mode,'kind':kind,'blob':blob}
 return out
owner=O/'OWNERFINAL-current1299-ordinary-a54-source-LIGHT-full-and-actual-HOLD.json';q=bind(owner);assert(q['bytes'],q['sha256'])==(20628,'241ed9898317e794178d48e8411eb8d38ada158732006007721eed73cdff8474')
light=load(owner);assert light['binding_count']==len(light['frozen_bindings'])==45;bindings=[check(x) for x in light['frozen_bindings']]
assert git('show','-s','--format=%H %T %P',H).decode().split()==[H,T,A,B] and git('rev-parse','HEAD').decode().strip()==H and not git('status','--porcelain')
a,b,c=typed(A),typed(B),typed(H);assert len(c)==1440 and set(c)==set(a)|set(b)
novel=[p for p,v in c.items() if v!=a.get(p) and v!=b.get(p)];assert novel==['.gitattributes','.github/workflows/_gen_workflows.py','.github/workflows/actions_runtime_tests.yml','docs/skills/repository-operations.md']
rows=load(O/'private-current-1299-complete-source-body-mode-inventory.json');assert len(rows)==1440
for row in rows:
 p=R/row['path'];raw=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();v=c[row['path']];assert(row['mode'],row['kind'],row['blob'])==(v['mode'],v['kind'],v['blob'])
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==v['blob'] and len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode']
 if v['mode']!='120000':assert bool(p.stat().st_mode&0o111)==(v['mode']=='100755')
owned=['action_server/tests/contract_tests/test_source_staging.py','action_server/tests/contract_tests/test_source_read.py','action_server/src/actions/server/deployments/source_read.py','action_server/src/actions/server/deployments/source_staging.py','action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py','action_server/tests/action_server_tests/mcp/test_canvas_query_template.py','action_server/tests/action_server_tests/test_canvas_query_results_fixture.py','action_server/tests/action_server_tests/test_browser_origin_acceptance.py']
for path in owned:assert c[path]==a[path]
for path in ['action_server/src/actions/server/_rcc_runtime_adapter.py','action_server/src/actions/server/_rcc.py']:assert c[path]==a[path]
# Whole original strict Canvas method and step without invoking generator/toolkit.
import yaml
GP='.github/workflows/_gen_workflows.py';WP='.github/workflows/actions_runtime_tests.yml'
def method(rev):return next(n for n in ast.walk(ast.parse(git('show',rev+':'+GP))) if isinstance(n,ast.FunctionDef) and n.name=='published_canvas_acceptance')
assert ast.dump(method(H),include_attributes=False)==ast.dump(method(ORIGINAL),include_attributes=False)
def step(rev):return next(s for s in yaml.safe_load(git('show',rev+':'+WP))['jobs']['build']['steps'] if s.get('name')=='Verify Canvas published-Core Runtime and browser acceptance')
assert step(H)==step(ORIGINAL)
mb=git('merge-base',A,B).decode().strip()
def funcs(rev):
 t=ast.parse(git('show',rev+':'+GP));out={}
 def walk(nodes,prefix=''):
  for n in nodes:
   if isinstance(n,ast.ClassDef):walk(n.body,prefix+n.name+'.')
   elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):out[prefix+n.name]=ast.dump(n,include_attributes=False)
 walk(t.body);return out,t
f0,t0=funcs(mb);fa,ta=funcs(A);fb,tb=funcs(B);fc,tc=funcs(H);assert set(fc)==set(fa)==set(fb)
da={p for p in fa if fa[p]!=f0.get(p)};db={p for p in fb if fb[p]!=f0.get(p)};assert not da&db
for p in fc:assert fc[p]==(fa[p] if p in da else fb[p] if p in db else f0[p])
def skeleton(t):
 t=copy.deepcopy(t)
 for n in ast.walk(t):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):n.body=[ast.Pass()]
 return ast.dump(t,include_attributes=False)
assert skeleton(tc)==skeleton(ta)==skeleton(tb)
wa=yaml.safe_load(git('show',A+':'+WP));wh=yaml.safe_load(git('show',H+':'+WP));wb=yaml.safe_load(git('show',B+':'+WP));assert wa['jobs']==wh['jobs'] and wh['on']==wb['on']
attrA=git('show',A+':.gitattributes').decode();attrH=git('show',H+':.gitattributes').decode();assert attrH.startswith(attrA)
# Producer/selectors are separate typed sets; never substitute old native receipt.
parsed=ast.parse(git('show',H+':action_server/scripts/verify_frozen_catalog_harness.py'));ip=ast.literal_eval(next(n.value for n in parsed.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='INPUT_PATHS' for t in n.targets)))
current,old=typed(H,ip),typed('92498aff',ip);selectors=['action_server/tests/action_server_tests/'+n for n in ['test_cli_mcp_catalog_rollback.py','test_cli_live_reload_multi_package.py','test_cli_successful_generation_drain.py','test_cli_multi_package_sync.py','test_cli_mcp_resource_history.py']]
assert len(current)==276 and len(old)==268 and sum(current.get(p)==v for p,v in old.items())==258 and sum(p in old and current[p]!=old[p] for p in current)==10 and len(set(current)-set(old))==8 and not set(old)-set(current)
assert typed(H,selectors)==typed('92498aff',selectors)
# Original scoped reports counted separately; initial empty selection remains failed.
def census(path):
 cases=ET.parse(path).findall('.//testcase');return len(cases),collections.Counter('SKIP' if n.find('skipped') is not None else 'FAIL' if n.find('failure') is not None else 'ERROR' if n.find('error') is not None else 'PASS' for n in cases)
assert census(O/'current-checkout-source-junit.xml')==(10,{'PASS':10})
assert census(O/'current-scoped-source-junit-v2.xml')==(304,{'PASS':303,'SKIP':1})
assert census(O/'current-staging-four-controls-junit-v2.xml')==(4,{'PASS':4})
assert census(O/'current-scoped-source-junit.xml')[0]==0
assert load(O/'current-source-LIGHT-terminal.json')['returncode']==1 and load(O/'current-source-LIGHT-continuation-v2-terminal.json')['returncode']==0
initial=(O/'current-source-LIGHT-original.private.log').read_text();continuation=(O/'current-source-LIGHT-continuation-v2-original.private.log').read_text();assert '179 passed' in initial and '10 passed' in initial and '303 passed, 1 skipped, 3 deselected' in continuation and '4 passed, 24 deselected' in continuation and 'Success: no issues found in 353 source files' in continuation
roundtrip=load(O/'current-generator8-allYAML30-roundtrip.json');assert roundtrip['generated_output_count']==8 and len(roundtrip['all30_bytes_sha256'])==30
for path,digest in roundtrip['all30_bytes_sha256'].items():assert sha(R/path)==digest==hashlib.sha256(git('show',H+':'+path)).hexdigest()
prepared=load(O/'own-current30-input-and-five-concrete-origins-Bootstrap-reuse.json');assert len(prepared['inputs'])==30 and len(prepared['origins'])==5
for path,digest in prepared['inputs'].items():assert sha(R/path)==digest
for rec in prepared['origins']:assert Path(rec['origin']).resolve().is_relative_to((Path(rec['prefix']).parent/'src').resolve()) and Path(rec['prefix']).resolve().is_relative_to(R.resolve())
# Verify exact imported parent guide text and original historical reference dispositions.
guides=['docs/skills/repository-operations.md','docs/skills/provenance-observability.md'];patch=O/'exact-imported-a54-canonical-guide-delta.patch';assert git('diff',A,H,'--',*guides)==patch.read_bytes();blocks=[]
for path in guides:
 ancestor=git('show',mb+':'+path).decode().splitlines(True);now=git('show',H+':'+path).decode()
 for parent in [A,B]:
  text=git('show',parent+':'+path).decode().splitlines(True)
  for tag,i,j,k,l in difflib.SequenceMatcher(a=ancestor,b=text,autojunk=False).get_opcodes():
   if tag in ('insert','replace') and l>k:
    delta=''.join(text[k:l]);assert delta in now;blocks.append({'path':path,'parent':parent,'lines':l-k,'sha256':hashlib.sha256(delta.encode()).hexdigest()})
history=load(ROOT/'pr282-actual309-refresh/FROZEN-before-source-original-e736-bindings.json');assert len(history['all_bound_refs_current_bytes_modes'])==441
curr=0;historic=[]
for row in history['all_bound_refs_current_bytes_modes']:
 q=bind(row['path'])
 if q==row:curr+=1
 else:
  assert row['path']=='/workspace/engineering/pr305/docs/skills/repository-operations.md';raw=git('show','40ad3b14d264d0e6aa7843e7c26b9fa3855fc34b:docs/skills/repository-operations.md',cwd=ROOT/'pr305');assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'];historic.append({'path':row['path'],'immutable_source':'40ad3b14d264d0e6aa7843e7c26b9fa3855fc34b','original_body_sha256':row['sha256'],'current_mutable_body_sha256':q['sha256']})
assert curr==440 and len(historic)==1
# Frozen native/helpers/browser/V5 proof payload recheck; source/module imports never run.
retention=load(O/'retained-native-helper-browser-and-V5-proof-postLIGHT.json');checked=[]
def nested(x):
 if isinstance(x,dict):
  if isinstance(x.get('path'),str) and x['path'].startswith('/') and isinstance(x.get('sha256'),str):checked.append(check(x))
  for v in x.values():nested(v)
 elif isinstance(x,list):
  for v in x:nested(v)
nested(retention)
for pair in retention['frozen_helper_original_and_snapshot_bindings'].values():assert stat.S_IMODE(Path(pair['snapshot']['path']).stat().st_mode)==0o444
baseline=load(ROOT/'rcc-compatibility-actual-runner-readonly-preparation/FROZEN-control3-current-b614-actual-config-v2.json');layout=Path(baseline['native_original_root']);members=baseline['native_original_members'];assert len(members)==1192 and {p.relative_to(layout).as_posix() for p in layout.rglob('*')}=={r['path'] for r in members}
for row in members:
 p=layout/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert not p.is_symlink() and sha(p)==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert os.readlink(p)==row['link_target']
v5=load(retention['historical_V5_checkpoint']['path']);assert len(v5['raw_receipts_private_do_not_commit'])==18 and len(v5['frozen_posthashes'])==50
for row in v5['raw_receipts_private_do_not_commit']:check(row)
for row in v5['frozen_posthashes']:assert sha(row['path'])==row['sha256']==row['expected_sha256']
vp=load(retention['immutable_proposal']['path']);driver=vp['driver'];check(driver['frontend_lock']);assert sha(driver['browser'])==driver['browser_sha256'] and Path(driver['prepared_node_modules']).is_dir();assert sha(driver['node'])==load(O/'raw18-frozen50-Node-frontend-retained-postLIGHT.json')['prepared_node_binary_sha256']
proof={'source':H,'tree':T,'ordered_parents':[A,B],'all1440_complete_Git_FS_body_and_execmode_union':True,'combined_paths':novel,'generator_parent_method_changes_disjoint':{'source_parent':sorted(da),'target_parent':sorted(db),'no_new_method_or_module_skeleton_AST':True},'whole_original9c_Canvas_method_AST_and_workflow_step_exact':True,'source_old_Canvas_read_staging_RCC_bodies_exact':True,'generator30_workflows_source_hashes_exact':True,'historical441':{'current_exact':440,'immutable_original_Git_body_classification':historic,'UNAVAILABLE':history['historical_UNAVAILABLE_original_bindings']},'guide_changed_parent_blocks':blocks,'producer':{'original':268,'current':276,'match':258,'changed':10,'added':8,'five_selectors_separate':5,'selector_changes':0,'native_qualification':'UNQUALIFIED'},'original1192_members_and_raw18_frozen50_helper0444_Node_browser_readonly_exact':True}
p=D/'independent-current1299-source-union-and-preservation-proof.json';p.open('x').write(json.dumps(proof,indent=2)+'\n');p.chmod(0o600)
remaining=['CurrentSOURCEFULL NOT_RUN; named full-preexecution proposal not owner-announced and not reviewed here; distinct ROOT serialized release required','Fresh exact-head hostedCI/policy/actualcandidate/browser/native/provider/private/backend/full127/release acceptance remain HOLD','276producer258oldmatch10changed8added plus5separateunchangedselectors is UNQUALIFIED for92498; originalV5 stays3ec historical','Original441 includes440 current exact and one mutablePR305 guide retained as immutable40ad Git body; ten originalUNAVAILABLE records remain unavailable','Passing source EOL controls do not explain historical hostedEOL cause or qualify newWindows/distribution bytes','Original initial LIGHT selection FAIL before package cases remains FAIL, not a RED requirement or full source result; Toolkit179/checkout10 succeeded independently before it and were not repeated']
out={'schema':'actions-independent-current2821299-SOURCE-LIGHT/v1','decision':'GO_EXACT_CURRENT1299_ORDINARY_A54_SOURCE_LIGHT_ONLY_FULL_AND_ACTUAL_HOLD','owner':bind(owner),'source':light['source'],'complete_typed_Git_FS_union':bind(p),'all45_current_frozen_bindings_hash_size_modes_exact':bindings,'observed_current_LIGHT':{'Doctor':'PASS','Toolkit_PASS':179,'checkout_PASS':10,'package_PASS':303,'package_SKIP':1,'package_DESELECT':3,'focused_staging_PASS':4,'focused_staging_DESELECT':24,'Mypy_source_files_PASS':353,'configured_lint':'PASS317','all_generated_workflows':8,'all_YAML':30,'own_prepared_inputs':30,'five_original_concrete_import_origins':5},'construction_history_retained':light['construction_history'],'new_full_preexecution_scope':'NOT_OWNER_ANNOUNCED_NOT_REVIEWED_NOT_EXECUTED','remaining_HOLD':remaining,'Documentation_improvement':{'Canonical_file_changed_or_proposed':guides,'Exact_verified_imported_delta':bind(patch),'Durable_learning_captured':'Import checkout EOL and affected workflow path filters while retaining strict39Canvas controller semantics, independent reader ownership/transport response lifecycle and receipt-vs-Git identity scopes. Runtime source276 and5selected cases remain separate typed qualification sets.','Evidence':'Exact8802B/0fb4f0d guide import and independently recomputed bothparent blocks;1440 whole typed union; generator methods disjointparent AST and originalwholeCanvas method/step unchanged; source10+303+4 tests and fullnative1192 preservation metadata','Stale_or_ambiguous_guidance_removed':'Do not preserve false whole-oldgenerator equality after accepted EOL filter import; method/step preservation is exact. Current276 is not historical275/274. Historical mutable guide body is authenticated immutable40ad, not invented currentpath equality.','Remaining_uncertainty':remaining},'Upstream_disposition':'none','no_tests_source_or_branch_edits_full_gateway_native_browser_provider_download_install_push_or_merge':True,'review_script':bind(__file__)}
p=D/'OWNERFINAL-independent-current1299-SOURCE-LIGHT-review.json';p.open('x').write(json.dumps(out,indent=2)+'\n');p.chmod(0o400);print(json.dumps(bind(p)))
