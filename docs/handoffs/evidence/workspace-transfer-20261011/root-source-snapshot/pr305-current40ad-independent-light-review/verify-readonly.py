from pathlib import Path
import ast,collections,hashlib,itertools,json,os,stat,subprocess,yaml
D=Path('/workspace/engineering/pr305-actual309-refresh');O=Path('/workspace/engineering/pr305-current40ad-independent-light-review');R=Path('/workspace/engineering/pr305');O.chmod(0o700)
H='40ad3b14d264d0e6aa7843e7c26b9fa3855fc34b';T='2d58cc8e47a50bc6c09d597a56ed8153aa4f2f34';A='519a0beb7451cb6e4410f0bee18c826fc493086e';B='a0d258a16095b95b1bf9000cb1201cddfaff4779'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
checked={}
def check(row):
 q=bind(row['path']);assert all(q[k]==row[k] for k in ('path','bytes','sha256'))
 if 'mode' in row:assert oct(stat.S_IMODE(Path(row['path']).stat().st_mode))==row['mode']
 checked[q['path']]=q
 return q
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def tree(rev):
 out={}
 for rec in git('ls-tree','-rz',rev).split(b'\0'):
  if rec:
   a,p=rec.split(b'\t',1);out[p.decode()]=a.decode().split()
 return out
owner=D/'OWNERFINAL-current40ad-ordinary-a0d-source-LIGHT-full-and-actual-HOLD.json';q=bind(owner);assert q['bytes']==90785 and q['sha256']=='2d2771a4f0d44b0021c0233ae367b3957ebe4639e62396518229853fd5b5ec41';d=json.loads(owner.read_text());assert d['head']==H and d['tree']==T and d['ordered_parents']==[A,B]
for row in d['all112_distinct_previous_bound_refs_bytes_modes_unchanged']+d['evidence_files']:check(row)
for key in ['immutable_constructor','complete_source_pre_post_body_modes_exec_exact','accepted_nine_RCC_sample_unchanged']:check(d[key])
for row in d['prepared_environment'].values():
 if isinstance(row,dict) and 'path' in row:check(row)
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A,B] and not git('status','--porcelain') and git('branch','--show-current').decode().strip()==d['existing_branch']
a,b,m=tree(A),tree(B),tree(H);assert len(m)==1422 and set(m)==set(a)|set(b)
fs=[]
for p,row in m.items():
 mode,kind,blob=row;f=R/p;body=os.readlink(f).encode() if mode=='120000' else f.read_bytes();assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==blob
 if mode!='120000':assert bool(f.stat().st_mode&0o111)==(mode=='100755')
 fs.append({'path':p,'mode':mode,'blob':blob,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
 if not p.startswith('docs/'):assert row==a.get(p) or row==b.get(p)
assert fs==json.loads(Path(d['complete_source_pre_post_body_modes_exec_exact']['path']).read_text())['all1422']
assert fs==json.loads((D/'complete-staged-ordinary-union-before-commit.json').read_text())['all_complete_entries']
changed=git('diff','--name-only',A,H).decode().splitlines();assert changed==['action_server/tests/action_server_tests/test_auth_route_enforcement.py','action_server/tests/action_server_tests/test_auth_route_inventory.py','docs/skills/repository-operations.md']
for p,row in a.items():
 if p!='docs/skills/repository-operations.md':assert m[p]==row
for p in changed[:2]:assert m[p]==b[p]
for p,row in d['original_Canvas3_entire_bodies_modes_AST_exact'].items():assert m[p]==a[p]==row
for p,row in d['current_producer']['all_current_entries'].items():assert m[p]==a[p]==row
for p,row in d['selected_tests_separate'].items():assert m[p]==a[p]==row
assert len(d['current_producer']['all_current_entries'])==274 and len(d['selected_tests_separate'])==5
old=tree('92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e');prod=d['current_producer']['all_current_entries'];same=sum(old.get(p)==row for p,row in prod.items());added=sum(p not in old for p in prod);changedprod=sum(p in old and old[p]!=row for p,row in prod.items());assert (same,changedprod,added)==(261,7,6)
# Ordinary guide imports retain additions from BOTH parents relative to common source.
base=git('merge-base',A,B).decode().strip();patch=Path(d['documentation_improvement']['Exact_delta']['path']);check(d['documentation_improvement']['Exact_delta']);assert patch.read_bytes()==git('diff',A,H,'--','docs/skills')
blocks=[]
for path in ['docs/skills/repository-operations.md','docs/skills/provenance-observability.md']:
 current=git('show',H+':'+path).decode()
 for parent in [A,B]:
  diff=git('diff','--unified=0',base,parent,'--',path).decode();chunk=[]
  for line in diff.splitlines(True)+['END']:
   if line.startswith('+') and not line.startswith('+++'):chunk.append(line[1:])
   elif chunk:
    block=''.join(chunk);assert block in current;blocks.append({'file':path,'parent':parent,'added_lines':len(chunk),'sha256':hashlib.sha256(block.encode()).hexdigest()});chunk=[]
# No current full execution is admitted from inherited old launchers.
assert d['gates']['current_full_source']=='HELD_NOT_RUN'
for n,phrases in {'Toolkit.log':['96 passed in 22.27s'],'Canvas-scoped.log':['47 passed, 4 deselected in 2.34s'],'current-RCC-and-static.log':['112 passed, 1 skipped, 3 deselected, 4 warnings in 7.52s','314 files already formatted','Success: no issues found in 350 source files'],'auth-source.log':['76 passed in 10.84s']}.items():
 s=(D/n).read_text();assert all(p in s for p in phrases) and 'actual main robot run" was SUCCESS' in s
rd=json.loads((D/'generator-roundtrip.json').read_text());assert len(rd['generated_workflows'])==8 and rd['all_tracked_yaml_count']==30 and rd['workflow_plus_dependabot_count']==26 and rd['before']==rd['after']
for p,h in {**rd['after'],**rd['additional_yaml_parsed_and_bytes_preserved']}.items():assert sha(R/p)==h;yaml.load((R/p).read_bytes(),Loader=yaml.BaseLoader)
prep=json.loads(Path(d['prepared_environment']['own30_inputs_configs_and_five_concrete_module_origins_verified']['path']).read_text());assert len(prep['inputs_exact_prepared_git_bytes_sha256'])==30 and len(prep['own5actual_prefix_and_source_origin_assertions'])==5
for p,h in prep['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/p)==h
for pkg,row in prep['own5venvs_current_config_and_python'].items():assert sha(R/pkg/'.venv/pyvenv.cfg')==row['config_sha256'] and str((R/pkg/'.venv/bin/python').resolve())==row['python_resolved']
for row in prep['own5actual_prefix_and_source_origin_assertions']:assert Path(row['prefix']).resolve().is_relative_to(R) and Path(row['origin']).is_relative_to(R) and Path(row['origin']).is_file()
# Preserve complete prior actual artifact scopes without relabeling them to current head.
n1=json.loads((D/'retained-native-helper-browser-and-V5-proof-after.json').read_text());n2=json.loads((D/'retained-native-helper-browser-and-V5-proof-postLIGHT.json').read_text());assert all(n1[k]==n2[k] for k in n1 if k!='current_source_execution_status')
assert (D/'raw18-frozen50-Node-frontend-retained-after.json').read_bytes()==(D/'raw18-frozen50-Node-frontend-retained-postLIGHT.json').read_bytes()
for key in ['original_manifest','original_inventory','original_assets_zip','original_frozen_executable','browser','historical_V5_checkpoint','historical_V5_independent_review','immutable_proposal']:check(n2[key])
for group in n2['frozen_helper_original_and_snapshot_bindings'].values():
 for key in ('original','snapshot'):check(group[key])
 assert stat.S_IMODE(Path(group['snapshot']['path']).stat().st_mode)==0o444
proposal=json.loads(Path(n2['immutable_proposal']['path']).read_text());layout=Path(proposal['native']['layout'])/'dist/action-server';inventory=json.loads(Path(n2['original_inventory']['path']).read_text());assert len(inventory)==1192 and {p.relative_to(layout).as_posix() for p in layout.rglob('*')}=={r['path'] for r in inventory}
for row in inventory:
 p=layout/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert sha(p)==row['content_sha256'] and not p.is_symlink()
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert p.is_symlink() and os.readlink(p)==row['link_target']
v5=json.loads(Path(n2['historical_V5_checkpoint']['path']).read_text());assert len(v5['raw_receipts_private_do_not_commit'])==18 and len(v5['frozen_posthashes'])==50
for row in v5['raw_receipts_private_do_not_commit']:check(row)
cats=collections.Counter()
for row in v5['frozen_posthashes']:
 p=Path(row['path']);got=sha(p);assert row['sha256']==row['expected_sha256']
 if got==row['sha256']:cats['retained_external_bytes']+=1
 else:
  rel=p.relative_to(R).as_posix();assert hashlib.sha256(git('show','3ec9d0acbe30ad94d02e4c24fef2587127964495:'+rel)).hexdigest()==row['sha256'];cats['historical305Gitbody_retained_original3ec_current_union_changed']+=1
ret=json.loads((D/'raw18-frozen50-Node-frontend-retained-postLIGHT.json').read_text());assert dict(cats)==ret['frozen50_counts'];driver=proposal['driver'];assert sha(driver['frontend_lock']['path'])==driver['frontend_lock']['sha256'] and sha(driver['browser'])==driver['browser_sha256'] and sha(driver['node'])==ret['prepared_node_binary_sha256'] and Path(driver['prepared_node_modules']).is_dir()
# Pure AST/source qualification for configured n-auto inheritance. No environment import/function execution.
plugin=next((R/'action_server/.venv/lib').glob('python*/site-packages/xdist/plugin.py'));pb=plugin.read_bytes();fun=next(n for n in ast.parse(pb).body if isinstance(n,ast.FunctionDef) and n.name=='pytest_xdist_auto_num_workers');assert 'PYTEST_XDIST_AUTO_NUM_WORKERS' in ast.unparse(fun) and 'int(env_var)' in ast.unparse(fun)
code='\n'.join(['import os, subprocess','from pathlib import Path','import toolkit','r=Path("/workspace/engineering/pr305")','assert toolkit.REPOSITORY_ROOT.resolve()==r.resolve()','assert subprocess.check_output(["git","-C",str(r),"rev-parse","HEAD"]).decode().strip()=="'+H+'"','assert subprocess.check_output(["git","-C",str(r),"rev-parse","HEAD^{tree}"]).decode().strip()=="'+T+'"','assert not subprocess.check_output(["git","-C",str(r),"status","--porcelain"])','os.environ["PYTEST_XDIST_AUTO_NUM_WORKERS"]="2"','toolkit.poetry("action_server","run","invoke","test-not-integration")'])
argv=['env','PYTEST_XDIST_AUTO_NUM_WORKERS=2','timeout','--signal=TERM','--kill-after=10s','600s','/workspace/actions-cloud/bin/rcc','task','script','-r','developer/toolkit.yaml','--','python','-c',code]
pcontract={'schema':'actions-current40ad-configured-source-full-proposal/v1','status':'PROPOSAL_NOT_EXECUTED__ROOT_DISTINCT_SERIALIZATION_CAPACITY_RELEASE_REQUIRED','head':H,'tree':T,'cwd':str(R),'argv':argv,'worker_environment':{'PYTEST_XDIST_AUTO_NUM_WORKERS':'2'},'attempts_admitted':1,'timeout_TERM_seconds':600,'kill_after_seconds':10,'unchanged_gate':'toolkit.poetry(action_server,run,invoke,test-not-integration)','installed_own_xdist_plugin':{'path':str(plugin),'bytes':len(pb),'sha256':hashlib.sha256(pb).hexdigest(),'auto_worker_function_AST_sha256':hashlib.sha256(ast.dump(fun,include_attributes=False).encode()).hexdigest(),'env2_precedes_CPU_fallback_source_proof_only':True},'preexecution_requirements':['Current exact head/tree/clean own prepared30+5prefixes/RCC immutable inputs rechecked','Current heavy300 must finish; no concurrent heavy full/native/consumer','Fresh available workspace capacity at least1.2GB; captured684MB insufficient and not approval','Execute exact current-head command once; changed launcher/argv needs named immutable successor','No source push until current full and independent SOURCEFINAL GO; historical519 launcher cannot qualify40ad']}
pc=O/'proposed-current40ad-explicit-two-worker-configured-full-contract.json';pc.write_text(json.dumps(pcontract,indent=2)+'\n');pc.chmod(0o600)
out={'schema':'actions-independent-pr305-current40ad-LIGHT/v1','verdict':'GO_FROZEN_LIGHT_SOURCE_SCOPE_AND_CURRENT_HEAD_CONFIGURED_FULL_PROPOSAL_ONLY','owner_final':q,'head':H,'tree':T,'ordered_parents':[A,B],'existing_branch':d['existing_branch'],'complete_Git_FS_typed_body_exec_union':1422,'old112_bound_refs_bytes_modes_rehashed':112,'total_unique_bound_files_rehashed':len(checked),'application_semantics_changed':False,'target_auth_tests_preserved':2,'original_three_Canvas_bodies_modes_exact':True,'original39_strict_predicate_gate_receipt_bindings_unchanged':True,'accepted_nine_RCC_sample_rehashed':d['accepted_nine_RCC_sample_unchanged'],'producer':{'current':274,'old':268,'old_matching':261,'changed':7,'added':6,'qualification':'UNQUALIFIED old92498 and3ec V5; preserved source is not current actual evidence'},'selected_tests_separate':5,'combined_count':279,'LIGHT_gates':d['gates'],'preservation':{'original_native_inventory_body_modes':1192,'frozen_helper_mode0444':True,'original_private_V5_raw_files':18,'original_V5_frozen_scope':50,'historical_V5_source':'3ec9d0acbe30ad94d02e4c24fef2587127964495','historical_native_producer':'92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e','actual_current_native_browser_provider':'NOT_RUN'},'full_proposal':bind(pc),'full_execution_release':'HOLD currentheavy300, freshcapacity, root distinct serialization/current-ref prepared-input preflight. NO current full executed by reviewer; no historical launcher reuse','remaining_HOLD':d['remaining_HOLD'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md and provenance-observability.md; accepted exact automatic both-parent guide imports reused','Exact_delta':d['documentation_improvement']['Exact_delta'],'verified_parent_added_block_bindings':blocks,'Durable_learning_captured':'Preserve original Canvas/RCC bodies and full typed production inventories alongside actual assembled request authority; event/source CI and historical native receipts remain separate. Explicit worker2 must precede configured n-auto execution.','Evidence':'1422 complete union/fullprepost; all112 original bindings;274+5; original1192/raw18/frozen50 retention;47Canvas+112RCC+76auth/Toolkit96/gen8/YAML30/sourceAST xdistenvironment guard','Stale_or_ambiguous_guidance_removed':'Automatic target auth guide imports retain credential/registration boundaries and configured isort gate; old519 full/CI and original3ec native actual not transferred to40ad; no cosmetic child','Remaining_uncertainty':'Current full, fresh exact hosted CI/current distribution/native/browser/provider/private/release remain HOLD'},'Upstream_disposition':'none','read_only_no_tests_gateway_source_index_native_provider_download_push_merge':True,'review_script':bind(__file__)}
p=O/'OWNERFINAL-independent-pr305-current40ad-LIGHT-and-full-proposal-review.json';p.write_text(json.dumps(out,indent=2)+'\n');p.chmod(0o600);print(json.dumps(bind(p)))
