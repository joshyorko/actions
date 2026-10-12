from pathlib import Path
import hashlib,json,os,stat,subprocess
O=Path(__file__).parent;R=Path('/workspace/engineering/pr308');S='396925cb3d6527af1768b7f5333f9653c005fc55';T='e2c81adce7858d5a952991ba9a8b7f72e902038a';TREE='929410b09fff3521c554cf935411c71f9e2e6b95'
def write(name,x,mode=0o444):
 b=x.encode() if isinstance(x,str) else (json.dumps(x,indent=2,sort_keys=True)+'\n').encode();p=O/name;fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
 with os.fdopen(fd,'wb') as f:f.write(b)
 return p
def binding(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
merge_guard='''"""Read-only guards for root's explicitly adopted ordinary merge; no gate execution."""
import subprocess,sys
R='/workspace/engineering/pr308';S='396925cb3d6527af1768b7f5333f9653c005fc55';T='e2c81adce7858d5a952991ba9a8b7f72e902038a';TREE='929410b09fff3521c554cf935411c71f9e2e6b95'
def git(*x):return subprocess.check_output(['git','-C',R,*x]).decode().strip()
assert sys.flags.optimize==0 and sys.argv[1] in ('before','merged-index','committed')
assert git('branch','--show-current')=='fix/rcc-candidate-wheel-identities-20261010'
assert git('rev-parse','refs/remotes/origin/integration/community-release-20261008')==T
if sys.argv[1]=='before':
 assert git('rev-parse','HEAD')==S and not git('status','--porcelain')
elif sys.argv[1]=='merged-index':
 assert git('rev-parse','HEAD')==S and git('rev-parse','MERGE_HEAD')==T
 assert git('write-tree')==TREE and not git('diff','--name-only')
else:
 assert git('show','-s','--format=%P','HEAD').split()==[S,T]
 assert git('rev-parse','HEAD^{tree}')==TREE and not git('status','--porcelain')
print('ROOT_ORDINARY_MERGE_GUARD_PASS',sys.argv[1])
'''
write('root_ordinary_merge_guards.py',merge_guard)
light='''"""UNBOUND preparation template. Requires separately adopted source-specific final config."""
import hashlib,json,os,stat,subprocess,sys
from pathlib import Path
assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE')
assert len(sys.argv)==2
cfg=json.loads(Path(sys.argv[1]).read_text())
assert cfg['status']=='ROOT_ADOPTED_CURRENT_SOURCE_LIGHT_ONCE', 'PREPARATION_NOT_EXECUTABLE'
assert cfg['source']['commit'] and len(cfg['source']['commit'])==40
assert cfg['source']['tree']=='929410b09fff3521c554cf935411c71f9e2e6b95'
assert cfg['accepted_B28_post_and_independent'] and cfg['root_LIGHT_execution_authorization']
assert 'PYTEST_ADDOPTS' not in os.environ,'INHERITED_PYTEST_ADDOPTS_REJECTED'
root=Path(cfg['source_root']);out=Path(cfg['owned_evidence_root'])
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[cfg['source']['commit'],cfg['source']['tree']]
assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain'])
# Independently frozen root-adopted pre/post guard must verify complete1440 Git/FS,
# activation19, prepared30/five origins, native1192 and237 originals/archive alias.
for stage in ('before',):subprocess.run(cfg['source_guard_argv']+[stage],check=True)
sys.path.insert(0,str(root/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==root
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
owned=Path(cfg['pytest_owned_parent']);assert owned.parent==Path('/tmp') and owned.name.startswith('actions-pr308-actuale2c-LIGHT-once-')
assert not owned.exists() and not owned.is_symlink();os.umask(0o077);owned.mkdir(mode=0o700)
def absent(name):
 p=owned/name;assert not p.exists() and not p.is_symlink(),'EXPLICIT_BASETEMP_MUST_BE_ABSENT';return p
try:
 toolkit.doctor()
 os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
 base=absent('toolkit-pytest')
 os.environ['PYTEST_ADDOPTS']='--basetemp='+str(base)+' -o tmp_path_retention_policy=all'
 try:toolkit.toolkit_test()
 finally:os.environ.pop('PYTEST_ADDOPTS',None)
 base=absent('scoped-runtime-pytest')
 toolkit.poetry('action_server','run','python','-m','pytest','-n0','-q',*cfg['Runtime_scoped_paths'],'-m','not integration_test','--tb=short','--basetemp='+str(base),'-o','tmp_path_retention_policy=all','--junitxml='+str(out/'current-scoped-junit.xml'))
 toolkit.poetry('action_server','run','invoke','lint')
 toolkit.poetry('action_server','run','invoke','typecheck')
 subprocess.run(cfg['generated_outputs_and_all_YAML_guard_argv'],check=True)
finally:
 subprocess.run(cfg['source_guard_argv']+['after'],check=True)
'''
write('run_current_e2c_template_LIGHT.py',light)
scoped=['tests/action_server_tests/test_rcc_runtime_adapter.py','tests/action_server_tests/test_dakota_rcc_acceptance.py','tests/action_server_tests/test_source_staging_rcc_consumer.py','tests/action_server_tests/run_outputs/test_transport.py','tests/action_server_tests/test_shutdown_response_order.py']
config={'status':'UNBOUND_READONLY_PREPARATION_NOT_EXECUTABLE','source':{'commit':None,'tree':TREE,'ordered_parents':[S,T],'typed_leaves':1440},'source_root':str(R),'cached_toolkit_prefix':'/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534','owned_evidence_root':None,'accepted_B28_post_and_independent':None,'root_committed_ordinary_merge_owner':None,'root_LIGHT_execution_authorization':None,'source_guard_argv':None,'generated_outputs_and_all_YAML_guard_argv':None,'Runtime_scoped_paths':scoped,'pytest_owned_parent':None,'per_invocation_absent_children':['toolkit-pytest','scoped-runtime-pytest'],'retention':'all','reject_inherited_PYTEST_ADDOPTS':True,'source_guard_requirements':{'source_rows':1440,'old_BINDINGS':237,'native_entries':1192,'original_source_binding':'retain e4/current396 Gitbody+exact authorized failed8dc archive alias separately; no physical-oldroot recreation','activation':'all19 including managed PATH/6478 script and primary3sha/ownmode0711','prepared_inputs':30,'five_concrete_origins':True,'capacity_floor_workspace_bytes':1288490189},'new_SOURCEFULL':'future independently accepted current sourceLIGHT+separate proposal/review/rootrelease;worker2configuredtask600TERM10/full640/whole900/prepost120;distinctABSENTonceparent fromallLIGHT pytestparents','private_V8_assembly':'onlyafternewcurrentSOURCEFULL+independentreview;deriveactualsourcecount/expectedlabel fromacceptedidentity,notold1423/396template;freshoncecacheROOTS;retainlegacy CONTROLc103 distinctexternal64SHA;5and7276requirepreviousversionactualPASS anddistinctrootrelease','binary_gate_or_old_FULL_carry':'NOT_AUTHORIZED'}
write('fresh-current-e2c-LIGHT-configuration-TEMPLATE.json',config,0o400)
commands=[['python',str(O/'root_ordinary_merge_guards.py'),'before'],['git','-C',str(R),'merge','--no-ff','--no-commit',T],['python',str(O/'root_ordinary_merge_guards.py'),'merged-index'],['git','-C',str(R),'commit','-m','Merge accepted Canvas source into RCC compatibility branch'],['python',str(O/'root_ordinary_merge_guards.py'),'committed']]
originals=[Path('/workspace/engineering/pr308-prospective-actual282-e2c-readonly/OWNERFINAL-readonly-current396-actuale2c-prospective-ordinary-refresh-plan.json'),Path('/workspace/engineering/rcc-current396925-private-V8-source-only/OWNERFINAL-private-current396925-V8-minimal-mode-and-source-context-SOURCE_ONLY-v2.json'),Path('/workspace/engineering/rcc-current396925-private-V8-independent-source-review/OWNERFINAL-independent-private-current396925-V8-source-only-review.json'),Path('/workspace/engineering/pr308-native-home-mode-current-a54-SOURCEFULL-preexecution/canonical-explicit-absent-isolated-pytest-basetemp-retention-proposed.patch'),Path('/workspace/engineering/pr308-prospective-actual282-e2c-readonly/canonical-automatic-generator-union-proposed.patch')]
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD']).decode().strip()==S
assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
owner={'status':'READONLY_PREPARATION_TEMPLATES_SOURCE_AND_GATES_NOT_ADOPTED','source_current':S,'source_target':T,'prospective_tree':TREE,'root_ordinary_merge_commands_only_after_B28_independent_post0':commands,'LIGHT_outer_command_template':['timeout','--signal=TERM','--kill-after=10s','720s','bash','-c','source /workspace/actions-cloud/activate.sh; export PATH=/workspace/actions-cloud/bin:/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin:$PATH; timeout --signal=TERM --kill-after=10s 480s /workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python '+str(O/'run_current_e2c_template_LIGHT.py')+' <NAMED_ROOT_ADOPTED_CURRENT_CONFIG>'],'unbound_fields':'Unknown actual merge commit/owner, B28 acceptance, guard/config hashes, once evidence and pytest parents remain null. Templates rejectexecution until namedfinal config reviewed/adopted.','gates_run':'NONE','product_source_worktree_refs_mutated':'NONE','bindings':[binding(p) for p in sorted(O.iterdir()) if p.is_file()]+[binding(p) for p in originals],'documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_reuse':'Accepted ff1283 uniqueABSENTbasetemp/ALL/rejectinheritedADDOPTS lesson plus proposedbe72 generatorAST/guideunion; applyafterroot source adoption ratherthan cosmetic preparation prose.','evidence':'ToolkitTest invokespytest directly with inheritedenv; explicit toolkit/scoped basetemps are distinct children and assertedabsent; read-only prospective1440 ASTunion proof.','stale_ambiguity_removed':'NONEretentiondoesnotdisablecleanup; one sharedADDOPTS basetemp acrosspytestinvocations can deleteearlier evidence. Conflict-free merge/newtree cannotcarryoldgates.','remaining_uncertainty':'New committedroot/qualification/actualsupportstillpending.'},'upstream_disposition':'none; no RCC125/118 workercomment sent'}
p=write('OWNERFINAL-readonly-e2c-ordinary-merge-fresh-LIGHT-and-V8-assembly-preparation.json',owner,0o400);print(json.dumps(binding(p)))
