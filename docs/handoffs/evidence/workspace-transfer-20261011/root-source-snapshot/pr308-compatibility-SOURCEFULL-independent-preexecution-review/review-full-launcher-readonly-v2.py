import ast,hashlib,json,stat,subprocess
from pathlib import Path
B=Path('/workspace/engineering/pr308-rcc-compatibility-SOURCEFULL-preexecution');R=Path('/workspace/engineering/pr308');O=Path('/workspace/engineering/pr308-compatibility-SOURCEFULL-independent-preexecution-review')
def bind(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
def git(*args):return subprocess.check_output(['git','--no-optional-locks',*args],cwd=R)
def emit(n,d):
 p=O/n
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
 p.chmod(0o600);return bind(p)
proposal=B/'OWNERFINAL-reviewed-inputs-current-b614-SOURCEFULL-preexecution-proposal-v2.json';pb=bind(proposal);assert pb['bytes']==7660 and pb['sha256']=='084faca6148648888627bfd7ffd0045d5b518b20ab6f77e5b8882adb404be32e'
p=json.loads(proposal.read_bytes());assert len(p['frozen_launcher_input_bindings'])==10
for row in p['frozen_launcher_input_bindings']:assert bind(Path(row['path']))==row
launcher=B/'launch-one-root-reviewed-source-full-v2.py';assert bind(launcher)['sha256']=='dd29d5a09d9477f48c4f30fdfc79201f2746d2bed20f23920191221a0a9ad83a'
old=(B/'launch-one-root-reviewed-source-full.py').read_text();new=launcher.read_text()
expected=old.replace('OWNERFINAL-reviewed-inputs-current-b614-SOURCEFULL-preexecution-proposal.json','OWNERFINAL-reviewed-inputs-current-b614-SOURCEFULL-preexecution-proposal-v2.json').replace('traceback.print_exc(file=stream)','stream.write(traceback.format_exc().encode("utf-8"))')
assert new==expected and old.count('traceback.print_exc(file=stream)')==2
assert "log.open('xb')" in new and "assert not log.exists() and not terminal.exists() and not marker.exists()" in new
assert "subprocess.run(argv,cwd=root,stdout=stream,stderr=subprocess.STDOUT,timeout=120)" in new
assert "if full_started:" in new and "primary_return=cp.returncode" in new and "post_return=10" in new
cfg=json.loads((B/'sourcefull-frozen-inputs.json').read_bytes());assert cfg['head']=='b614864ba9da55c13662894b6ef3c8515d9fdb25' and cfg['tree']=='6fa4f5c1e9837a0d893868255575b355b3977fae'
assert cfg['worker_count']==2 and cfg['capacity_floor_bytes']==p['required_capacity_before_full_bytes']==1200000000
assert len(cfg['expected_activation_exports'])==18 and cfg['expected_activation_exports']['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
activation=Path(cfg['activation']['path']);assert bind(activation)['sha256']==cfg['activation']['sha256']=='6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
# Parse only the reviewed literal exports, without sourcing the activation script.
env={}
for line in activation.read_text().splitlines():
 if line.startswith('export '):
  k,v=line[7:].split('=',1);v=v.strip('"')
  for prev,val in env.items():v=v.replace('${'+prev+'}',val).replace('$'+prev,val)
  if k!='PATH':env[k]=v
assert env==cfg['expected_activation_exports']
assert git('rev-parse','HEAD').decode().strip()==cfg['head'] and git('rev-parse','HEAD^{tree}').decode().strip()==cfg['tree'] and not git('status','--porcelain')
light=json.loads(Path(p['SOURCE_LIGHT']['path']).read_bytes());assert bind(Path(p['SOURCE_LIGHT']['path']))==p['SOURCE_LIGHT']
assert len(light['frozen_bindings'])==71
for row in light['frozen_bindings']:assert bind(Path(row['path']))==row
proof=json.loads(Path(light['complete_committed_body_mode_proof']['path']).read_bytes());assert len(proof['complete1421_Git_FS_body_mode_exact'])==1421
for n,row in proof['complete1421_Git_FS_body_mode_exact'].items():
 file=R/n;assert bind(file)['sha256']==row['sha256'] and stat.S_ISREG(file.lstat().st_mode) and bool(file.stat().st_mode&0o111)==(row['mode']=='100755')
prepared=json.loads(Path(cfg['prepared']).read_bytes());assert len(prepared['inputs_exact_prepared_git_bytes_sha256'])==30
for n,h in prepared['inputs_exact_prepared_git_bytes_sha256'].items():assert bind(R/n)['sha256']==h
for n,row in prepared['own5venvs_current_config_and_python'].items():assert bind(R/n/'.venv/pyvenv.cfg')['sha256']==row['config_sha256']
for file,mode in [(R/'action_server/src/actions/server/bin/rcc-18.19.3',0o711),(Path('/workspace/actions-cloud/bin/rcc'),0o700)]:assert bind(file)['sha256']=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428' and stat.S_IMODE(file.stat().st_mode)==mode
worker=json.loads((B/'installed-own-worker-env-and-unchanged-task-source-proof.json').read_bytes());source_refs=[]
for k,row in worker.items():
 if isinstance(row,dict) and 'path' in row and 'sha256' in row:
  file=Path(row['path']);actual=bind(file);assert actual['sha256']==row['sha256'];tree=ast.parse(file.read_text());methods={n.name:ast.get_source_segment(file.read_text(),n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
  assert all(methods[n]==s for n,s in row['relevant_functions_source'].items());source_refs.append(actual)
assert len(source_refs)==3
module=ast.parse((R/'developer/toolkit.py').read_text());removed=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='ACTIVE_ENVIRONMENT_VARIABLES');assert 'PYTEST_XDIST_AUTO_NUM_WORKERS' not in removed
child=(B/'run-one-configured-source-full.py').read_text();guard=(B/'verify-current-full-source-prepost.py').read_text()
assert "toolkit.poetry('action_server','run','invoke','test-not-integration')" in child and "os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')" in child
assert "assert os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'" in child and "'/workspace/actions-cloud/bin' in os.environ['PATH'].split(os.pathsep)" in child
assert "timeout=30,check=True" in guard and "if stage=='before':assert space>=cfg['capacity_floor_bytes']" in guard
assert "assert k not in os.environ,k" in child and "assert k not in os.environ,k" in guard
assert p['configured_full_argv']==['timeout','--signal=TERM','--kill-after=10s','600s','/workspace/actions-cloud/bin/rcc','task','script','-r','developer/toolkit.yaml','--','python',str(B/'run-one-configured-source-full.py')]
assert p['outer_launcher_argv']==['bash','--noprofile','--norc','-c','source /workspace/actions-cloud/activate.sh\nexec /workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python3.12 '+str(launcher)+' --execute-reviewed-proposal']
outputs=['SOURCEFULL-one-attempt-original.log','SOURCEFULL-one-attempt-terminal.json','SOURCEFULL-execution-attempt-consumed.json','before-full-source-prepost.json','after-full-source-prepost.json','before-full-original-native-helper-browser-V5-readback.json','after-full-original-native-helper-browser-V5-readback.json']
assert all(not (B/n).exists() for n in outputs)
rootargv=['timeout','--signal=TERM','--kill-after=10s','900s',*p['outer_launcher_argv']]
assert all(bind(Path(row['path']))==row for row in p['frozen_launcher_input_bindings']) and all(bind(Path(row['path']))==row for row in light['frozen_bindings']) and not git('status','--porcelain')
result={'status':'PASS_READONLY_PREEXECUTION_REVIEW_CONDITIONAL_ROOT_ADOPTION','proposal':pb,'launcher':bind(launcher),'source':cfg['head'],'tree':cfg['tree'],'all10_proposal_refs_and71_LIGHT_refs_exact_prepost':True,'all1421_Git_FS_execbodies_exact':True,'prepared30_and_five_config_hashes_exact':True,'activation18_exports_plus_PATH19_derived_exact':True,'installed_xdist_task_toolkit_source_refs':source_refs,'parent_root_adoption_argv':rootargv,'configured600TERM_plus10_unchanged':True,'preflight120_post120_separate':True,'component_max_seconds':850,'root_parent_TERM_seconds':900,'root_parent_KILL_grace_seconds':10,'one_attempt_outputs_absent':outputs,'original_ef74_TypeError_encoding_successor_preserved':True,'no_launcher_preflight_full_candidate_probe_source_edit_or_gate_executed':True,'fresh_capacity_release':'HOLD until root immediate available>=1200000000 and heavy slot clearance; preparation and review do not release execution'}
out=emit('safe-independent-frozen-full-launcher-readback.json',result);print(json.dumps(out))
