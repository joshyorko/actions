"""Metadata-only source freeze; no package imports, installs or tests."""
import ast, hashlib, json, os, stat, subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=Path('/workspace/engineering/pr307')
OLD='87e412f89b201c697d3e6bd4bd34031cdbd14df3';TARGET='e2c81adce7858d5a952991ba9a8b7f72e902038a'
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
def sha(b):return hashlib.sha256(b).hexdigest()
def bind(p):
 p=Path(p);m=p.lstat();b=p.read_bytes();assert stat.S_ISREG(m.st_mode) and not p.is_symlink();return {'path':str(p),'bytes':len(b),'sha256':sha(b),'mode':oct(stat.S_IMODE(m.st_mode))}
def save(n,j):
 p=BASE/n;assert not p.exists();p.write_text(json.dumps(j,indent=2,sort_keys=True)+'\n');p.chmod(0o400);return bind(p)
def tree(ref):
 out={}
 for row in git('ls-tree','-rz','--full-tree',ref).split(b'\0'):
  if row:
   meta,p=row.split(b'\t',1);mode,kind,blob=meta.decode().split();out[p.decode()]={'mode':mode,'kind':kind,'blob':blob}
 return out
head=git('rev-parse','HEAD').decode().strip();t=git('rev-parse','HEAD^{tree}').decode().strip();parents=git('show','-s','--format=%P','HEAD').decode().split();assert parents==[OLD,TARGET] and t=='2987ed3a23e560fb40e13aadbcd6bd613ead3f25';assert not git('status','--porcelain=v1')
a,b,c=tree(OLD),tree(TARGET),tree(head);assert set(c)==set(a)|set(b)
novel=[];fsrows=[]
for p,row in c.items():
 assert row['kind']=='blob'
 raw=git('cat-file','blob',row['blob']);file=ROOT/p;m=file.lstat()
 if row['mode']=='120000':assert stat.S_ISLNK(m.st_mode) and os.readlink(file).encode()==raw
 else:assert stat.S_ISREG(m.st_mode) and file.read_bytes()==raw and bool(m.st_mode&0o111)==(row['mode']=='100755')
 if row!=a.get(p) and row!=b.get(p):novel.append(p)
 fsrows.append({'path':p,**row,'bytes':len(raw),'sha256':sha(raw),'FS_body_and_exec_mode_exact':True})
assert sorted(novel)==['.github/workflows/_gen_workflows.py','docs/skills/repository-operations.md']
guards=['action_server/tasks.py','action_server/scripts/build_oauth2_config.py','action_server/tests/build_system_tests/test_oauth2_config_build.py','action_server/docs/CHANGELOG.md']
assert all(c[p]==a[p] for p in guards)
for p in ('action_server/tasks.py',):assert ast.dump(ast.parse(git('show',head+':'+p)),include_attributes=False)==ast.dump(ast.parse(git('show',OLD+':'+p)),include_attributes=False)
# Generator exact target AST except the accepted existing307 install-before-OAuth insertion.
def generator_nodes(ref):
 return {getattr(n,'name',f'{type(n).__name__}@{i}'):ast.dump(n,include_attributes=False) for i,n in enumerate(ast.parse(git('show',ref+':.github/workflows/_gen_workflows.py')).body)}
g0,g1=generator_nodes(TARGET),generator_nodes(head)
gendelta=[k for k in set(g0)|set(g1) if g0.get(k)!=g1.get(k)]
guid=git('show',head+':docs/skills/repository-operations.md').decode();prior=git('show',OLD+':docs/skills/repository-operations.md').decode()
start=prior.index('`inv build-oauth2-config`');end=prior.index('Recovery invokes the task',start)
lesson=prior[start:end];assert lesson in guid
oldprep=json.loads(Path('/workspace/engineering/pr302-actual310-source-refresh/own-bootstrap-reuse-complete-gateway-proof.json').read_bytes());fullprep=json.loads(Path('/workspace/engineering/pr310-current-refresh/bootstrap-reuse.json').read_bytes())
inputs=sorted(set(oldprep['all19inputs_exact'])|set(fullprep['inputs_sha256']));assert len(inputs)==30
inputrows=[]
for p in inputs:
 now=git('show',head+':'+p);before=git('show',OLD+':'+p)
 inputrows.append({'path':p,'bytes':len(now),'sha256':sha(now),'equal_original307_head':now==before})
assert all(r['equal_original307_head'] for r in inputrows)
venvs=[]
for package,module in [('actions','actions'),('actions-http-helper','actions_http'),('devutils','devutils.invoke_utils'),('work-items','actions.work_items'),('action_server','actions.server')]:
 prefix=ROOT/package/'.venv';cfg=prefix/'pyvenv.cfg';assert cfg.is_file() and (prefix/'bin/python').exists()
 venvs.append({'package':package,'module_for_future_origin_probe':module,'prefix':str(prefix),'pyvenv_config':bind(cfg),'python_resolved':str((prefix/'bin/python').resolve()),'actual_current_module_origin_probe':'NOT_RUN'})
oldreceipt=json.loads(Path('/workspace/engineering/pr307-guard-owned/successor-receipt.json').read_bytes())
retained=[]
for r in oldreceipt['evidence'].values():
 rr=bind(r['path']);assert rr['bytes']==r['size'] and rr['sha256']==r['sha256'];retained.append(rr)
plan=Path('/workspace/engineering/pr221-currente2-existing-PR307-guard-readonly-recontext/OWNERFINAL-existing-PR307-currente2-readonly-guard-reuse-and-normal-refresh-plan-NOTRUN.json')
proof=save('complete-current-ordinary-union-source-and-retained-evidence-proof.json',{'head':head,'tree':t,'parents':parents,'all_typed_count':len(c),'previous_count':len(a),'target_count':len(b),'no_deletions':True,'all_git_FS_body_and_exec_mode_exact':fsrows,'novel_two_parent_union_paths':sorted(novel),'retained_guard_task_helper_test_changelog':{p:c[p] for p in guards},'whole_task_AST_exact_old307':True,'generator_top_level_AST_delta_vs_target':sorted(gendelta),'source307_install_before_guard_reuse':'automatic existing generator union; no regeneration executed','prepared30_exact_original307_head':inputrows,'five_existing_venvs_config_only':venvs,'retained_original_evidence':retained,'original_source_plan':bind(plan),'guard_canonical_excerpt_sha256':sha(lesson.encode()),'canonical_excerpt_exact_in_current_guide':True})
# Actual commands are preparation; all output/retention/logger directories must be fresh/exclusive.
runroot='/workspace/engineering/pr307-actuale2-light-full-once-owned'
assert not Path(runroot).exists()
activation=bind('/workspace/actions-cloud/activate.sh'); managed=bind('/workspace/actions-cloud/bin/rcc')
lightfocus=['tests/build_system_tests/test_oauth2_config_build.py']
common=['--basetemp='+runroot+'/basetemp','-o','tmp_path_retention_policy=all','-o','tmp_path_retention_count=999999','--robocorp-log-output='+runroot+'/robot-output']
focuscode='import toolkit; toolkit.poetry("action_server", "run", "python", "-m", "pytest", "tests/build_system_tests/test_oauth2_config_build.py", "-n", "0", "-vv", "--basetemp='+runroot+'/light-basetemp", "-o", "tmp_path_retention_policy=all", "-o", "tmp_path_retention_count=999999", "--robocorp-log-output='+runroot+'/light-robot-output", "--junitxml='+runroot+'/light-junit.xml")'
fullcode='import toolkit; toolkit.poetry("action_server", "run", "invoke", "test-not-integration")'
fullopts=' '.join(common+['--junitxml='+runroot+'/full-junit.xml'])
proposal={'schema':'PR307_CURRENT_E2_LIGHT_FULL_PREPARATION_ONLY','status':'NOT_RUN_CAPACITY_AND_SERIALIZATION_AND_INDEPENDENT_REVIEW_REQUIRED','head':head,'tree':t,'parents':parents,'source_proof':proof,'cwd':str(ROOT),'owned_attempt_root':runroot,'attempt_root_absent':True,'activation':activation,'managed_RCC':managed,'toolkit_definition':bind(ROOT/'developer/toolkit.yaml'),'reject_inherited':['PYTHONOPTIMIZE','PYTEST_ADDOPTS'],'no_user_binary_override':['ACTIONS_RCC_TEST_BINARY_SELECTOR','ACTIONS_RCC_TEST_BINARY'],'light':{'parent_budget_seconds':300,'child_budget_seconds':180,'kill_grace_seconds':10,'doctor':['rcc','run','-r','developer/toolkit.yaml','--dev','-t','Doctor'],'own_prepared_reuse':'30current inputs exact old87;5configs exist; historical successful ownBootstraplog retained. Actual fresh ownPoetry sys.prefix/module origins must be measured before gate; no newBootstrap authorized','toolkit':['rcc','run','-r','developer/toolkit.yaml','--dev','-t','ToolkitTest'],'focus_gateway':['rcc','task','script','-r','developer/toolkit.yaml','--','python','-c',focuscode],'configured_static':'toolkit.poetry(action_server,run,invoke,lint); toolkit.poetry(action_server,run,invoke,typecheck); explicit unchanged build helper/test Ruff +helper Mypy required','generator':'source-pinned generator outputs into fresh owned directory;8 exact generated bodies plus all30GitHub YAML parse; no tracked writes','controlled_real_Invoke_gateway':'Reuse preserved original synthetic-gh gateway semantics under NEW owned paths only; old fixed output paths must not be rerun/overwritten. Recontextualized private runner needs separate immutable source review before execution; no real gh acquisition'},'full':{'outer_budget_seconds':900,'primary_budget_seconds':640,'child_budget_seconds':600,'kill_grace_seconds':10,'always_post_guard_budget_seconds':120,'workers':2,'env':{'PYTEST_XDIST_AUTO_NUM_WORKERS':'2','PYTEST_ADDOPTS':fullopts},'gateway':['timeout','--signal=TERM','--kill-after=10s','600s','rcc','task','script','-r','developer/toolkit.yaml','--','python','-c',fullcode],'admission':'complete unique node IDs/JUnit counts; no unexpected FAIL/ERROR; existing SKIPs remain unqualified; preserve raw stdout/stderr/private logging/current source full typed before/alwayspost','fresh_workspace_floor_bytes':1288490189,'fresh_tmp_floor_bytes':1200000000},'no_installs_or_native_or_services':'No newBootstrap/pip/Poetry installs/provider/native/browser/OAuth network inputs; no fake config/stubs/authority waiver','remaining_holds':['CurrentLIGHT/FULLNOT_RUN','Authoritative OAuth pair/revision/providers/fullrelease HOLD; retained original acquisition failures unchanged','Fresh hosted CI/sourcecheckout after independent review/rootnormalpush','No new native/currentproducer qualification'], 'documentation_improvement':{'canonical_file':'docs/skills/repository-operations.md','delta':'Ordinary merge imports accepted e2 knowledge and retains exact existing307 checked30s/strictUTF8/safeYAML/pairedatomic/sourceauthority block; no cosmetic extra child','evidence':proof,'stale_ambiguity_removed':'Old1173/41 tests remain historical, e2 now source union but not gated/adopted integration; rejected699d unchanged','remaining_uncertainty':'Fresh currentorigins/scoped/static/generated/full and authoritative OAuth content remain unqualified'},'upstream_disposition':'none'}
pb=save('OWNERFINAL-pr307-currente2-LIGHT-FULL-PREPARATION-NOTRUN.json',proposal)
owner={'schema':'OWNERFINAL_PR307_ORDINARY_CURRENT_E2_SOURCE_UNION_ONLY','status':'FROZEN_ORDINARY_SOURCE_REFRESH_NOT_TESTED_NOT_PUSHED','head':head,'tree':t,'ordered_parents':parents,'existing_branch':git('branch','--show-current').decode().strip(),'named_remote_verified_before_merge':{'existing_PR307':OLD,'integration':TARGET},'clean':not bool(git('status','--porcelain=v1')),'typed_union_count':len(c),'novel_union_paths':sorted(novel),'guard_helper_tests_changelog_unchanged':True,'proof':proof,'light_full_preparation':pb,'constructor':bind(__file__),'canonical_exact_existing_guard_lesson_retained':True,'no_push_or_install_or_test_or_native_execution':True,'upstream_disposition':'none'}
ob=save('OWNERFINAL-pr307-currente2-ordinary-source-union-checkpoint.json',owner);print(json.dumps({'owner':ob,'proposal':pb,'head':head,'tree':t,'count':len(c),'generator_AST_delta':sorted(gendelta)}))
