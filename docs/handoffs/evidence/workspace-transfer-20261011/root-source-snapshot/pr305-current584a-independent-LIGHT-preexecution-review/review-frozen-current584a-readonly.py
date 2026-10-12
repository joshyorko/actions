from pathlib import Path
import json,hashlib,subprocess,stat,os,ast,difflib,collections,xml.etree.ElementTree as ET,re
D=Path(__file__).parent;ROOT=Path('/workspace/engineering');R=ROOT/'pr305';L=ROOT/'pr305-current-e3c-source-LIGHT';P=ROOT/'pr305-current584a-SOURCEFULL-preexecution'
H='584a7ed0cb7112fe6691103931c007b5cc0be5f3';T='5b4bd2f10c35d0bc7b9d85037f211fa55c47a282';OLD='40ad3b14d264d0e6aa7843e7c26b9fa3855fc34b';B='e3c29cde8878307912e55ed09b6436c0f91d06d5';CURRENT='a54c982462d1e7ad011d8152bfc299d997503fb3'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def load(p):return json.loads(Path(p).read_text())
def git(*a):return subprocess.check_output(['git','-C',str(R),*a],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
def check(row,mode=True):
 p=Path(row['path']);q=bind(p);assert q['sha256']==row['sha256'] and q['bytes']==row['bytes']
 if mode and 'mode' in row:assert q['mode']==row['mode']
 return q
lp=L/'OWNERFINAL-current584a-ordinary-e3-source-LIGHT-full-and-actual-HOLD.json';pp=P/'OWNERFINAL-current584a-managed-configured-SOURCEFULL-preexecution-proposal.json';q=bind(lp);assert (q['bytes'],q['sha256'])==(14931,'5835c7c1b57493d784ea39cf0c037253460b04b3b3c9c4fa48fb1db1a887c387');q=bind(pp);assert (q['bytes'],q['sha256'])==(8226,'2cd287244d83b2388449794bb4ea8205ca95329c8908af8ed288c91207097718')
light=load(lp);proposal=load(pp);cfg=load(P/'frozen-current-source-full-inputs.json');assert light['binding_count']==len(light['frozen_bindings'])==32
lightbindings=[check(x) for x in light['frozen_bindings']];prebindings=[check(x) for x in proposal['frozen_input_bindings']]
assert light['source']['commit']==proposal['source']==cfg['head']==H and light['source']['tree']==proposal['tree']==cfg['tree']==T
assert git('show','-s','--format=%H %T %P',H).decode().split()==[H,T,OLD,B]
assert git('rev-parse','HEAD').decode().strip()==H and not git('status','--porcelain')
def typed(s,paths=()):
 out={}
 for row in git('ls-tree','-rz',s,'--',*paths).split(b'\0'):
  if row:
   pre,p=row.split(b'\t');mode,kind,blob=pre.decode().split();assert kind=='blob';out[p.decode()]={'mode':mode,'kind':kind,'blob':blob}
 return out
a,b,c=typed(OLD),typed(B),typed(H);assert len(c)==1424 and set(c)==set(a)|set(b)
novel=[p for p,v in c.items() if v!=a.get(p) and v!=b.get(p)];assert novel==['docs/skills/repository-operations.md']
rows=load(L/'private-current-584a-complete-source-body-mode-inventory.json');assert len(rows)==1424
for row in rows:
 p=R/row['path'];raw=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();v=c[row['path']];assert (row['mode'],row['kind'],row['blob'])==(v['mode'],v['kind'],v['blob'])
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==v['blob'] and len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode']
 if v['mode']!='120000':assert bool(p.stat().st_mode&0o111)==(v['mode']=='100755')
for path in c:
 if path.startswith('.github/') or path in ['action_server/src/actions/server/_rcc_runtime_adapter.py','action_server/src/actions/server/_rcc.py']:assert c[path]==a[path]
owned=['action_server/tests/action_server_tests/mcp/test_canvas_runtime_admission.py','action_server/tests/action_server_tests/test_browser_origin_acceptance.py','action_server/tests/action_server_tests/mcp/test_mcp_apps_authoring.py','action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py']
for path in owned:assert c[path]==a[path]
verifier=ast.parse(git('show',H+':action_server/scripts/verify_frozen_catalog_harness.py'));inputpaths=ast.literal_eval(next(n.value for n in verifier.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='INPUT_PATHS' for t in n.targets)))
producer=typed(H,inputpaths);native=typed('92498aff',inputpaths);s5=['action_server/tests/action_server_tests/'+n for n in ['test_cli_mcp_catalog_rollback.py','test_cli_live_reload_multi_package.py','test_cli_successful_generation_drain.py','test_cli_multi_package_sync.py','test_cli_mcp_resource_history.py']]
assert len(producer)==275 and len(native)==268 and sum(producer.get(p)==v for p,v in native.items())==260
assert sum(p in native and producer[p]!=native[p] for p in producer)==8 and len(set(producer)-set(native))==7 and not set(native)-set(producer)
assert typed(H,s5)==typed('92498aff',s5)
actual=load(L/'typed-current-production-and-five-selector-inventory.json');assert actual['current']==producer and actual['original_native']==native
j=ET.parse(L/'current-scoped-source-junit.xml');cases=j.findall('.//testcase');counts=collections.Counter('SKIP' if n.find('skipped') is not None else 'FAIL' if n.find('failure') is not None else 'ERROR' if n.find('error') is not None else 'PASS' for n in cases);assert counts=={'PASS':265,'SKIP':1}
log=(L/'current-source-LIGHT-original.private.log').read_text();assert '96 passed' in log and '265 passed, 1 skipped, 7 deselected' in log and 'Success: no issues found in 352 source files' in log and 'SOURCE_LIGHT_COMPLETE_NO_ACTUAL_RCC' in log
terminal=load(L/'current-source-LIGHT-terminal.json');assert terminal.get('returncode',terminal.get('exit_code'))==0
roundtrip=load(L/'current-generator8-allYAML30-roundtrip.json');assert roundtrip['generated_output_count']==8 and len(roundtrip['all30_bytes_sha256'])==30
for path,digest in roundtrip['all30_bytes_sha256'].items():assert sha(R/path)==digest==hashlib.sha256(git('show',H+':'+path)).hexdigest()
prepared=load(L/'own-current30-input-and-five-concrete-origins-Bootstrap-reuse.json');assert len(prepared['inputs'])==30 and len(prepared['origins'])==5
for path,digest in prepared['inputs'].items():assert sha(R/path)==digest
assert sha(prepared['original_bootstrap_log'])==prepared['original_bootstrap_log_sha256']
for record in prepared['origins']:
 assert Path(record['prefix']).resolve().is_relative_to(R.resolve()) and Path(record['origin']).resolve().is_relative_to((Path(record['prefix']).parent/'src').resolve()) and Path(record['origin']).is_file()
# Read-only native member equivalence without importing the product or frozen helper.
baseline=load(cfg['original_native_config']);layout=Path(baseline['native_original_root']);members=baseline['native_original_members'];assert len(members)==1192
assert {p.relative_to(layout).as_posix() for p in layout.rglob('*')}=={r['path'] for r in members}
for row in members:
 p=layout/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert p.is_file() and not p.is_symlink() and sha(p)==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert p.is_symlink() and os.readlink(p)==row['link_target']
retention=load(L/'retained-native-helper-browser-and-V5-proof-postLIGHT.json');retention_checked=[]
def all_path_sha(x):
 if isinstance(x,dict):
  if isinstance(x.get('path'),str) and x['path'].startswith('/') and isinstance(x.get('sha256'),str) and 'bytes' in x:retention_checked.append(check(x,False))
  for v in x.values():all_path_sha(v)
 elif isinstance(x,list):
  for v in x:all_path_sha(v)
all_path_sha(retention)
for pair in retention['frozen_helper_original_and_snapshot_bindings'].values():assert stat.S_IMODE(Path(pair['snapshot']['path']).stat().st_mode)==0o444
v5=load(retention['historical_V5_checkpoint']['path']);raw18=v5['raw_receipts_private_do_not_commit'];assert len(raw18)==18
for row in raw18:check(row,False)
assert len(v5['frozen_posthashes'])==50
for row in v5['frozen_posthashes']:assert row['sha256']==row['expected_sha256']==sha(row['path'])
v5proposal=load(retention['immutable_proposal']['path']);driver=v5proposal['driver'];check(driver['frontend_lock'],False);assert sha(driver['browser'])==driver['browser_sha256'] and Path(driver['prepared_node_modules']).is_dir()
raw_report=load(L/'raw18-frozen50-Node-frontend-retained-postLIGHT.json');assert sha(driver['node'])==raw_report['prepared_node_binary_sha256']
# Exact owning-guide import and every newly added/replaced block from BOTH parents.
guides=['docs/skills/repository-operations.md','docs/skills/provenance-observability.md'];patch=L/'exact-imported-e3-canonical-guide-delta.patch';assert git('diff',OLD,H,'--',*guides)==patch.read_bytes()
mb=git('merge-base',OLD,B).decode().strip();blocks=[]
for path in guides:
 original=git('show',mb+':'+path).decode().splitlines(True);currentguide=git('show',H+':'+path).decode()
 for parent in [OLD,B]:
  parentguide=git('show',parent+':'+path).decode().splitlines(True)
  for tag,i1,i2,j1,j2 in difflib.SequenceMatcher(a=original,b=parentguide,autojunk=False).get_opcodes():
   if tag in ('insert','replace') and j2>j1:
    block=''.join(parentguide[j1:j2]);assert block in currentguide;blocks.append({'guide':path,'parent':parent,'lines':j2-j1,'sha256':hashlib.sha256(block.encode()).hexdigest()})
assert len(blocks)==8
# Static launcher, task and installed worker selection authority only; never import/execute.
launcher=(P/'launch_current_source_full_once.py').read_text();body=(P/'current_source_full_body.py').read_text();guard=(P/'current_source_prepost_guard.py').read_text()
for p in [P/'launch_current_source_full_once.py',P/'current_source_full_body.py',P/'current_source_prepost_guard.py']:ast.parse(p.read_bytes())
assert proposal['configured_full_argv']==['timeout','--signal=TERM','--kill-after=10s','600s',cfg['cached_toolkit_prefix']+'/bin/python',str(P/'current_source_full_body.py')]
assert 'timeout=640' in launcher and 'timeout=60' in launcher and 'finally:' in launcher and "owned.mkdir(mode=0o700)" in launcher and "os.umask(0o077)" in launcher and "log.open('xb')" in launcher and "primary_error=type(error).__name__" in launcher and "post_error=type(error).__name__" in launcher
assert not (P/'one-configured-full-once-owned').exists() and not (P/'one-configured-full-once-owned').is_symlink()
assert "os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'" in body and "toolkit.poetry('action_server','run','invoke','test-not-integration')" in body
activate=Path('/workspace/actions-cloud/activate.sh').read_text();exports={}
for line in activate.splitlines():
 m=re.fullmatch(r'export (\w+)=(.*)',line)
 if m and m[1]!='PATH':exports[m[1]]=m[2].strip('"\'')
assert exports==cfg['expected_activation_exports'] and len(exports)==18 and exports['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2' and exports['GOMAXPROCS']=='2'
assert len(cfg['forbidden_actual_operator_exports'])==6 and 'PYTHONOPTIMIZE' in cfg['forbidden_actual_operator_exports']
for package,module in cfg['concrete_origin_packages']:assert (R/package/'.venv/pyvenv.cfg').is_file()
xdist=R/'action_server/.venv/lib/python3.12/site-packages/xdist/plugin.py';xtext=xdist.read_text();ast.parse(xtext);assert 'PYTEST_XDIST_AUTO_NUM_WORKERS' in xtext and 'return int(env_var)' in xtext
kit=(R/'developer/toolkit.py').read_text();tasks=(R/'action_server/tasks.py').read_text();proc=(R/'action_server/src/actions/server/_build_common/process_call.py').read_text();assert 'environment = os.environ.copy()' in kit and 'env=environment' in kit and 'env: Optional[Dict[str, str]] = None' in proc
assert cfg['capacity_floor_bytes']==proposal['current_capacity_observation']['minimum_workspace_before_full_bytes']==1288490188
proof={'source':H,'tree':T,'ordered_source_parents':[OLD,B],'complete_entries':1424,'non_doc_union_exact':True,'sole_combined_path':novel,'source_inventory_original':bind(L/'private-current-584a-complete-source-body-mode-inventory.json'),'producer':{'old':268,'current':275,'old_match':260,'changed':8,'added':7,'selectors_separate':5,'selector_changes':0,'native_qualification':'UNQUALIFIED'},'guide_blocks':blocks,'all32_LIGHT_and13_preexecution_bindings_hash_mode_exact':True,'original1192_members_modes_hashes_and_whole_set_exact':True,'original_snapshot0444_and_raw18_frozen50_Node_browser_readonly_reverified':True}
p=D/'independent-current584a-source-preservation-static-proposal-proof.json';p.open('x').write(json.dumps(proof,indent=2)+'\n');p.chmod(0o600)
remaining=['Source584a gates belong historical basee3. Actual targeta54 requires next ordinary union/source/full/fresh hosted CI review before normal integration; no stale carry','CurrentSOURCEFULL NOT_RUN; distinct ROOT release after current priority RCC3 plus fresh strictcapacity and serialized slot only','All originalV5/native92498 remain historical; 275producer260match8changed7added+5selectors is UNQUALIFIED','No actualbrowser/provider/native/private/full99/backend/release/issue closure acceptance','Frozen prepost launcher independently iterates1424 current source and1192 native members. Other raw18/frozen50/driver/snapshot preservation report contents require separately repeated actual post-outcome readback; hashing reports is not rehashing their payload paths','Hard OS kill cannot guarantee finally/postguard; primary/pre/post errors and actualcleanup remain separately reported']
out={'schema':'actions-independent-current305584a-LIGHT-and-configured-full-preexecution/v1','SOURCE_LIGHT_decision':'GO_EXACT_CURRENT584a_ORDINARY_E3_SOURCE_LIGHT_ONLY','SOURCEFULL_preexecution_decision':'GO_STATIC_FROZEN_PROPOSAL_CONDITIONAL_DISTINCT_ROOT_RELEASE_CAPACITY_SERIALIZATION_AND_OUTCOME_PRESERVATION','source':light['source'],'actual_current_integration_target':CURRENT,'head_tree_and_all1424_source_FS_body_modes_exact':True,'all32_LIGHT_bindings':lightbindings,'all_preexecution_bindings':prebindings,'current_LIGHT_observed':{'Toolkit_PASS':96,'scoped_PASS':265,'scoped_SKIP':1,'scoped_DESELECT':7,'Mypy_files_PASS':352,'configured_lint':'PASS','generated_workflow_roundtrip':8,'all_YAML_hashes_exact':30,'own_prepared_inputs':30,'five_concrete_origins':5},'original_retention_current_readonly_proof':bind(p),'execution_proposal':{'owner':bind(pp),'root_release_exact_required_schema':proposal['root_release_exact_required_schema'],'outer_cwd':str(R),'outer_managed_command':proposal['outer_managed_command'],'configured_full_argv':proposal['configured_full_argv'],'bounds':proposal['execution_bounds'],'managed_exports':18,'PATH_primary_binding':19,'worker_bound':'2 inherited to unchanged invoke test-not-integration -n auto via toolkit environment copy and process env=None','installed_worker_selector_source':bind(xdist),'output_directory_ABSENT':str(P/'one-configured-full-once-owned'),'fresh_minimum_capacity_bytes_conservative':1288490189,'single_attempt_and_all_outcome_records':True,'no_installs_new_envs_or_native_operators':True,'current_execution_status':'NOT_RUN_NO_ROOT_RELEASE_BY_REVIEWER','extra_original_payload_postguard_required_before_retention_acceptance':'Separate exact hashes for raw18/frozen50/browser/Node/other snapshot paths; frozen launcher hashes preservation reports but does not recursively verify their contents'},'preserved_old40ad_and_originalV5_scopes':'40ad86c4/2529 proposals and actual3ec/92498/28b/1848 unchanged historical; never carried into current584a execution','remaining_HOLD':remaining,'Documentation_improvement':{'Canonical_file_changed_or_proposed':guides,'Exact_delta':bind(patch),'Durable_learning_captured':'Both parent reader ownership/revocation, event transport, grant transaction, provenance and snapshot lessons were imported exactly; original Canvas/native/source/prepared environment scopes remain separate. A fresh report hash authenticates that report, not a recursive fresh recheck of its payload paths.','Evidence':'Eight independently recomputed parent insertion/replacement blocks, exact5462B sourceguide patch; 1424 Git/FS union, original39/controlworkflow byte preservation, 265 scoped cases and source launcher guard coverage','Stale_or_ambiguous_guidance_removed':'Old40ad preexecution and3ec actual receipts are historical; measured current275production is not forced to old274. Actuala54 is not accepted by currente3 source/gates.','Remaining_uncertainty':remaining},'Upstream_disposition':'none','no_source_tests_gateway_import_product_native_download_install_push_or_merge':True,'review_script':bind(__file__)}
p=D/'OWNERFINAL-independent-current584a-SOURCE-LIGHT-and-managed-full-preexecution-review.json';p.open('x').write(json.dumps(out,indent=2)+'\n');p.chmod(0o400);print(json.dumps(bind(p)))
