import ast,hashlib,json,os,stat,subprocess
from pathlib import Path
import yaml
os.umask(0o077)
D=Path('/workspace/engineering/pr312-actual309-refresh');O=Path('/workspace/engineering/pr312-actual309-independent-light-review');R=Path('/workspace/engineering/runtime-checkout-eol')
def sha(b):return hashlib.sha256(b).hexdigest()
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
checked={}
def check(r):
 q=bind(r['path']);assert q=={k:r[k] for k in ['path','bytes','sha256']};checked[q['path']]=q
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def inv(ref):
 out={}
 for row in git('ls-tree','-rz',ref).split(b'\0'):
  if row:
   meta,p=row.split(b'\t');mode,typ,blob=meta.decode().split();out[p.decode()]={'mode':mode,'type':typ,'blob':blob}
 return out
p=D/'OWNERFINAL-pr312-actual309-refresh-LIGHT.json';assert bind(p)['sha256']=='7606ad32b0f85aa7ad835f0970aeebddf7c750908a7426d16fb0f219db4ecef0' and p.stat().st_size==13643;d=json.loads(p.read_bytes());assert d['head']=='77065131a0aee63d2b1f8621476374bdde3c7b65' and d['tree']=='edf1801e565692fb3f07b809b3a95b27981fe2fe'
for r in d['immutable_evidence_bindings']:check(r)
for key in ['prior_SOURCEFINAL','readonly_preparation','independent_actual309_GO']:check(d[key])
old=json.loads(Path(d['prior_SOURCEFINAL']['path']).read_bytes());assert len(old['immutable_evidence_bindings'])==62
for r in old['immutable_evidence_bindings']:check(r)
S=d['head'];A,B=d['ordered_parents'];assert git('rev-parse','HEAD').decode().strip()==S and git('rev-parse',S+'^{tree}').decode().strip()==d['tree'] and git('show','-s','--format=%P',S).decode().split()==[A,B] and not git('status','--porcelain')
a,b,m=inv(A),inv(B),inv(S);assert len(m)==1423 and set(m)==set(a)|set(b)
for path,row in m.items():
 fp=R/path;body=os.readlink(fp).encode() if row['mode']=='120000' else fp.read_bytes();assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==row['blob']
 if row['mode']!='120000':assert bool(fp.stat().st_mode&0o111)==(row['mode']=='100755')
 if not path.startswith('docs/'):assert row==a.get(path) or row==b.get(path)
pre=json.loads((D/'committed-complete-union-pre-light.json').read_bytes());post=json.loads((D/'committed-complete-union-post-light.json').read_bytes());assert pre['typed_leaves']==post['typed_leaves']==m and pre['selected207']==post['selected207'] and len(pre['selected207'])==207
for path in pre['selected207']:assert m[path]==a[path]
assert len([p for p in pre['selected207'] if p.endswith('.py')])==201
for path in ['action_server/tests/action_server_tests/test_auth_route_inventory.py','action_server/tests/action_server_tests/test_auth_route_enforcement.py']:assert m[path]==b[path]
for path in d['original7_delta_paths_retained']:
 if not path.startswith('docs/'):assert m[path]==a[path]
assert len(d['original7_delta_paths_retained'])==7
attrs=git('show',S+':.gitattributes').decode();assert len([l for l in attrs.splitlines() if l.strip() and not l.startswith('#') and 'eol=lf' in l])>=7
lesson=pre['documentation_exact_imported_lesson'];assert len(lesson.splitlines())==16;guide=git('show',S+':docs/skills/repository-operations.md').decode();assert guide.count(lesson)==1 and guide.replace(lesson,'',1)==git('show',B+':docs/skills/repository-operations.md').decode()
for n in ['Doctor.log','Toolkit.log','own-light-scoped-static-generator.log']:assert 'actual main robot run" was SUCCESS' in (D/n).read_text()
assert '96 passed' in (D/'Toolkit.log').read_text();log=(D/'own-light-scoped-static-generator.log').read_text();assert all(x in log for x in ['10 passed in 6.75s','76 passed in 12.62s','313 files already formatted','Success: no issues found in 349 source files'])
roundtrip=json.loads((D/'generator-all-eight-roundtrip.json').read_bytes());assert roundtrip['generated_workflows']==8 and roundtrip['all_tracked_GitHub_YAML']==30 and len(roundtrip['all_tracked_GitHub_YAML_before_after_sha256'])==30
for path,h in roundtrip['all_tracked_GitHub_YAML_before_after_sha256'].items():assert sha((R/path).read_bytes())==h;yaml.load((R/path).read_bytes(),Loader=yaml.BaseLoader)
for path in ['.github/workflows/actions_runtime_tests.yml','.github/workflows/actions_runtime_pypi_release.yml']:
 wf=yaml.load((R/path).read_bytes(),Loader=yaml.BaseLoader);assert '.gitattributes' in wf['on']['pull_request']['paths']
reuse=json.loads((D/'own-Bootstrap-reuse-inputs-and-origins.json').read_bytes());assert reuse['measured_inputs']==30 and len(reuse['inputs_exact_prepared_git_bytes_sha256'])==30 and len(reuse['own5actual_prefix_and_source_origin_assertions'])==5
for path,h in reuse['inputs_exact_prepared_git_bytes_sha256'].items():assert sha((R/path).read_bytes())==h
pin=R/'action_server/src/actions/server/bin/rcc-18.19.3';assert sha(pin.read_bytes())==d['light_gate_outcomes']['ignored_RCC_SHA256'] and stat.S_IMODE(pin.stat().st_mode)==0o711
worker=json.loads((D/'worker-bound-mechanism-reuse-for-current-union.json').read_bytes());check(worker['original_installed_source_proof']);wp=json.loads(Path(worker['original_installed_source_proof']['path']).read_bytes())
for row in wp['installed_xdist']:
 content=Path(row['installed_plugin_path']).read_bytes();assert len(content)==row['installed_plugin_bytes'] and sha(content)==row['installed_plugin_sha256'];at=ast.parse(content);f=next(n for n in at.body if isinstance(n,ast.FunctionDef) and n.name=='pytest_xdist_auto_num_workers');assert sha(ast.dump(f,include_attributes=False).encode())==row['installed_auto_worker_function_AST_sha256'];assert 'PYTEST_XDIST_AUTO_NUM_WORKERS' in ast.unparse(f) and row['actual_installed_function_controlled_environment_result']==2
for key,path in [('toolkit_source_sha256','developer/toolkit.py'),('configured_Runtime_task_source_sha256','action_server/tasks.py'),('Runtime_process_call_source_sha256','action_server/src/actions/server/_build_common/process_call.py')]:assert sha((R/path).read_bytes())==wp[key]
launcher=Path(d['next_full']['launcher']['path']);check(d['next_full']['launcher']);assert launcher.read_bytes()==Path('/workspace/engineering/runtime-checkout-eol-source/full-source-gates-explicit-worker-bound-v2.py').read_bytes();lt=ast.parse(launcher.read_bytes());assignment=next(i for i,n in enumerate(lt.body) if isinstance(n,ast.Assign));calls=[(i,n) for i,n in enumerate(lt.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)];assert len(calls)==2 and assignment<min(i for i,n in calls);assert [ast.literal_eval(a) for a in calls[0][1].value.args]==['devutils','run','python','-m','pytest','-q','tests','-n','2'];assert [ast.literal_eval(a) for a in calls[1][1].value.args]==['action_server','run','invoke','test-not-integration'];assert ast.literal_eval(lt.body[assignment].value)=='2'
argv=d['next_full']['argv'];assert argv==['env','PYTEST_XDIST_AUTO_NUM_WORKERS=2','timeout','--signal=TERM','--kill-after=10s','600s','/workspace/actions-cloud/bin/rcc','task','script','-r','developer/toolkit.yaml','--','python',str(launcher)] and d['next_full']['cwd']==str(R) and d['next_full']['attempt_count']==0
initial=json.loads((D/'initial-freeze-worker-task-path-inspection-failure.json').read_bytes());assert initial
for a1,a2 in [('raw18-frozen50-Node-frontend-retained-post-light.json','raw18-frozen50-Node-frontend-retained-root-released-pre.json'),('retained-native-helper-browser-and-V5-proof-post-light.json','retained-native-helper-browser-and-V5-proof-root-released-pre.json')]:assert (D/a1).read_bytes()==(D/a2).read_bytes()
free=os.statvfs(R).f_bavail*os.statvfs(R).f_frsize
out={'verdict':'GO_FROZEN_LIGHT_SOURCE_SCOPE_AND_EXPLICIT_WORKER_FULL_GATE_PROPOSAL_ONLY','owner':bind(p),'head':S,'tree':d['tree'],'ordered_parents':[A,B],'existing_branch':d['branch'],'complete_typed_Git_FS_body_exec_union':1423,'protected_source_inputs':{'total':207,'Python':201,'text_and_frontend':6,'seven_LF_rules_and_two_workflow_filters_original92e_bytes_preserved':True},'target_auth_test_files_preserved':2,'original_SOURCEFINAL_refs_verified':62,'all_unique_binding_files_rehashed':len(checked),'LIGHT_results':d['light_gate_outcomes'],'original_preservation':'Bound pre/post native/helper/browser/Node/frontend/V5 proof files identical; historical actual3ec and original92e full gates separate','full_gate_proposal':{'argv':argv,'cwd':str(R),'launcher':bind(launcher),'worker_bound_both_packages':2,'installed_xdist_AST_and_configured_task_hashes_verified':True,'unchanged_sequential_commands':d['next_full']['sequential_gates'],'outer_deadline_seconds':600,'TERM_kill_after_seconds':10,'attempts_completed_at_owner_freeze':0,'current_full_execution':'NOT_RUN_BY_REVIEWER','root_distinct_serialization_capacity_release_required':True,'required_workspace_bytes_at_release':1200000000,'free_bytes_readonly_review_observation':free,'capacity_observation_is_not_execution_authorization':True},'remaining_HOLDs':['ONE current full source result and independent final SOURCE review before normal existing-branch push','Fresh complete770/a0d hostedCI; original92e/618 gates historical','Current Windows generated bytes, semantic/compiler cause, native/private/OAuth authority/provider/coldconsumer/fullrelease not admitted'],'construction_history':'Initial wrong-task-hash inspector failure retained; corrected immutable task path/plugin proof checked; no source/test gate rerun by reviewer','Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; exact imported1306 16-line EOL lesson and accepteda113 worker-bound lesson reused','Exact_documentation_delta':'770 guide minus exactly one imported16-line source lesson equals complete actuala0d target guide; no cosmetic child','Durable_learning_captured':'Preserve all207 selected source bodies and owning filters independently of generated output semantics; bind explicit worker2 before both sequential gates and outer600TERM+10 timeout.','Evidence':'1423 complete typed/GitFS union,207 unchanged source entries,2 exactauthfiles;10 checkout/filter+76auth currentLIGHT;8generated30YAML; installedown xdist hashes/AST and launcher876a exact.','Stale_or_ambiguous_guidance_removed':'No old92e full/CI transferred to770; Runtime-nauto inherits explicit reviewed2 rather than assuming earlier devutils-n2 constrains it.','Remaining_uncertainty':'Current full/sourceFINAL/hosted/platform/private/native/release acceptance remains held; fresh capacity and root serialization release required.'},'Upstream_disposition':'none','review_script':bind(__file__)}
q=O/'OWNERFINAL-independent-pr312-current-a0d-LIGHT-and-full-gate-proposal-review.json';q.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(bind(q)))
