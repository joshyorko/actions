import ast,collections,hashlib,json,os,re,stat,subprocess
from pathlib import Path
D=Path(__file__).parent;P=Path('/workspace/engineering/pr300-current74-managed-activation-root-successor');R=Path('/workspace/engineering/pr300')
def b(p):
 p=Path(p);z=p.read_bytes();return dict(path=str(p),bytes=len(z),sha256=hashlib.sha256(z).hexdigest())
def v(r):assert b(r['path'])==r,r['path']
f=P/'OWNERFINAL-current74-managed-source-full-and-retained-original-failure.json';x=json.loads(f.read_bytes());assert b(f)['sha256']=='5acb9c193f8924bb8215980636dda06e88fdeafaa242687f50b36cfc4eb7cb21'
rows={}
def walk(y):
 if isinstance(y,dict):
  if {'path','bytes','sha256'}<=y.keys() and str(y['path']).startswith('/'):
   row={k:y[k] for k in ['path','bytes','sha256']};v(row);rows[row['path']]=row
  for yy in y.values():walk(yy)
 elif isinstance(y,list):
  for yy in y:walk(yy)
walk(x)
assert len(x['all110_original_and_LIGHT_references'])==110
proof=json.loads(Path(x['complete1423_body_Git_FS_mode_inventory']['path']).read_bytes())
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a])
assert git('rev-parse','HEAD').decode().strip()==x['head'] and git('rev-parse','HEAD^{tree}').decode().strip()==x['tree'] and git('status','--porcelain')==b''
leaves={r.split(b'\t',1)[1].decode():r.split(b'\t',1)[0].split() for r in git('ls-tree','-r','-z','HEAD').split(b'\0') if r}
assert len(leaves)==len(proof['all1423'])==1423
for row in proof['all1423']:
 m,k,blob=leaves[row['path']];assert (m.decode(),blob.decode())==(row['mode'],row['blob']);p=R/row['path'];s=p.lstat()
 if row['mode']=='120000':assert stat.S_ISLNK(s.st_mode);z=os.readlink(p).encode()
 else:assert stat.S_ISREG(s.st_mode) and bool(s.st_mode&0o111)==(row['mode']=='100755');z=p.read_bytes()
 assert len(z)==row['bytes'] and hashlib.sha256(z).hexdigest()==row['sha256'];assert git('cat-file','blob',row['blob'])==z
prepared=json.loads(Path(x['prepared_inputs']['record']['path']).read_bytes());inputs=prepared['all30_current_inputs_exact_prepared_Git_bytes'];assert len(inputs)==30
for path,digest in inputs.items():assert hashlib.sha256((R/path).read_bytes()).hexdigest()==digest
configs=prepared['five_own_environment_configs'];assert len(configs)==5
for name,e in configs.items():
 assert hashlib.sha256((R/name/'.venv/pyvenv.cfg').read_bytes()).hexdigest()==e['config_sha256'];assert str((R/name/'.venv/bin/python').resolve())==e['python_resolved']
for row in x['prepared_inputs']['five_concrete_source_origins']:
 v(row);origin=json.loads(Path(row['path']).read_bytes());assert any(str(R/name/'src') in str(origin) for name in configs)
for row,mode in [(x['prepared_inputs']['ignored_pinned_RCC'],0o711),(x['prepared_inputs']['managed_gateway'],0o700)]:
 p=R/row['path'] if not row['path'].startswith('/') else Path(row['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'];assert p.stat().st_size==row['bytes'];assert stat.S_IMODE(p.stat().st_mode)==mode
terminal=json.loads(Path(x['one_actual_full_terminal']['path']).read_bytes());auth=json.loads(Path(x['distinct_successor_authorization']['path']).read_bytes());post=json.loads(Path(x['postfull_complete_source_and_refs']['path']).read_bytes());contract=json.loads(Path(x['exact_original_configured_command']['path']).read_bytes())
assert terminal['returncode']==0 and terminal['authorization']==x['distinct_successor_authorization'] and terminal['log']==x['private_original_full_log'];assert post['terminal']==x['one_actual_full_terminal'] and post['all1423_source_Git_FS_modes_and_original_LIGHT_inputs_unchanged'] is True
assert auth['argv'][9:]==contract['argv'] and auth['full_attempts']==1 and auth['workspace_available_bytes']>=1200000000
assert auth['source_head']==x['head'] and auth['source_tree']==x['tree'] and auth['target']==x['target']
launcher=Path('/workspace/engineering/execute-current74-managed-activation-successor-once.py');oldlauncher=Path('/workspace/engineering/execute-one-current74-reviewed-configured-full.py')
assert b(launcher)['sha256']=='520531f235abc84211361215bdd918133afdec3349d0c8faf18cd7be81af2fc0'
review=json.loads(Path(x['independent_root_launcher_review']['path']).read_bytes());print('launcher review keys',list(review))
# Root adoption authenticates the original dependent guard script without executing its main.
adoption=json.loads(Path(x['root_immediate_adoption']['path']).read_bytes());walk(adoption)
log=Path(x['private_original_full_log']['path']).read_text(errors='replace');marker='PASS_MANAGED_ACTIVATION_CURRENT_SOURCE_CACHED_TOOLKIT_READONLY_PREFLIGHT'
assert log.count(marker)==1 and log.index(marker)<log.index('created: 2/2 workers')<log.index('2 workers [1338 items]')
assert re.search(r'1325 passed, 13 skipped, 15 warnings in 150\.09s',log)
node_results=re.findall(r'^\[(gw\d+)\]\s+\[\s*\d+%\]\s+(PASSED|SKIPPED|FAILED|ERROR)\s+(.+?)\s*$',log,re.M)
counts=collections.Counter(status for gw,status,node in node_results);assert counts=={'PASSED':1325,'SKIPPED':13};assert len({node for gw,status,node in node_results})==1338;assert {gw for gw,status,node in node_results}=={'gw0','gw1'}
transport=[(gw,s,n) for gw,s,n in node_results if 'run_outputs/test_transport.py::' in n];assert len(transport)==30 and all(s=='PASSED' for gw,s,n in transport)
old=x['retained_consumed_failed_original_attempt'];oldterminal=json.loads(Path(old['terminal']['path']).read_bytes());assert oldterminal['returncode']==4
oldlog=Path(old['raw']['path']).read_text(errors='replace');assert marker not in oldlog and not re.search(r'^\[gw\d+\]',oldlog,re.M)
for path in [P,Path(x['private_original_full_log']['path']),Path(x['one_actual_full_terminal']['path'])]:assert stat.S_IMODE(path.stat().st_mode)==(0o700 if path==P else 0o600)
patch=D/'canonical-count-workers-by-producing-phase-proposed.patch';patch.write_text('--- a/docs/skills/repository-operations.md\n+++ b/docs/skills/repository-operations.md\n@@\n+Bind worker counts to the producing phase: RCC solver parallelism is not\n+pytest concurrency. Use pytest worker-creation and joined node-result records\n+for suite admission, alongside the configured worker limit and final totals.\n');patch.chmod(0o600)
r={'schema':'independent-current74-completed-managed-source-full-review-v1','decision':'GO_CURRENT74_SOURCE_FULL_AND_ROOT_GUARDED_NORMAL_EXISTING_BRANCH_PUSH_ONLY','owner':b(f),'head':x['head'],'tree':x['tree'],'target':x['target'],'source_clean':True,'checks':{'complete_Git_FS_blob_mode_entries':1423,'original_plus_LIGHT_refs':110,'total_unique_bound_refs_reverified':len(rows),'prepared_inputs':30,'retained_concrete_origin_receipts':5,'five_config_hashes_and_interpreter_resolutions':True,'RCC_primary_mode':'0700','RCC_fixture_mode':'0711','same_managed_activation_and_preflight_before_pytest':True,'exact_contract_argv_suffix9':True,'only_guard_AST_from_original_launcher_no_original_main':True,'original_attempt_auth_and_failure_bytes_preserved':True,'actual_new_full_attempts':1,'reviewer_test_launcher_preflight_or_gate_executions':0},'actual_raw_suite_census':{'pass':1325,'skip':13,'failed':0,'errors':0,'unique_nodes':1338,'actual_pytest_workers':['gw0','gw1'],'created': '2/2','warnings':15,'pytest_seconds':150.09,'outer_seconds':terminal['elapsed_seconds'],'configured_transport_module_nodes':len(transport),'transport_all_pass':True,'RCC_solver_worker_lines':'Distinct producer scope; never evidence of pytest worker count'},'original_failed_attempt':{'authorization':old['authorization'],'terminal':old['terminal'],'raw':old['raw'],'returncode':4,'pytest_counts':'UNREPORTED','scope':'Failed outer gateway before pytest, retained unchanged and not upgraded by successor'},'source_push_requirements':['Root fresh exact existing PR branch/ref/head/base/target guards and expected-head normal push','Fresh current74/currenttarget hosted CI and original OS qualification remain required before integration'],'HOLD':['Actual ASGI/TCP/service/output acceptance; full86/HEADsupport/active stream revocation','Original Windows/API checkout and historical failure are distinct from this local source run','Native/provider/browser/private/release/publication/currentCI/full process reaping unqualified'],'bindings':list(rows.values()),'launcher':b(launcher),'original_guard_dependency':b(oldlauncher),'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md external exact3line worker-phase proposal; accepted ee804 activation and8895 assembled transport lessons retained','Durable_learning_captured':'Tool solver parallelism and pytest worker creation are separately measured producer phases.','Evidence':{'proposed_delta':b(patch),'raw_log':x['private_original_full_log'],'actual_worker_line':'created: 2/2 workers; 2 workers [1338 items]','joined_node_count':1338,'accepted_activation_delta':b('/workspace/engineering/pr300-current74-managed-activation-independent-review/canonical-managed-gateway-activation-exact-context-v2.patch')},'Stale_or_ambiguous_guidance_removed':'Solver4 cannot be relabeled pytest4; earlier gateway failure remains countsUNREPORTED rather than zero tests.','Remaining_uncertainty':'Configured local source full passed; no hosted/actual/native/private/publication/completecleanup claim. A schema-only exploratory read first assumed entries rather than all1423, failed before producing any gate receipt, and was corrected against immutable sourceproof shape.'},'Upstream_disposition':'none','constructor':b(__file__)}
out=D/'OWNERFINAL-independent-current74-managed-source-full-review.json'
with out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
out.chmod(0o600);print(json.dumps(b(out)))
