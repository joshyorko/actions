from pathlib import Path
import ast,datetime,hashlib,json,os,re,stat,subprocess,yaml
D=Path('/workspace/engineering/pr300-current74-owner-full-contract-adoption');O=Path('/workspace/engineering/pr300-current74-managed-activation-independent-review');R=Path('/workspace/engineering/pr300');O.chmod(0o700)
H='74beef4d220c3a1e8f983cecd42b9bb84ac75e79';T='2238ed312babba9fd5ad89a3a1cc581ca6ad2dcf';BASE='a0d258a16095b95b1bf9000cb1201cddfaff4779';C=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
checked={}
def check(row):
 q=bind(row['path']);assert all(q[k]==row[k] for k in ('path','bytes','sha256'));checked[q['path']]=q
 if 'mode' in row:assert oct(stat.S_IMODE(Path(row['path']).stat().st_mode))==row['mode']
 return q
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def save(name,x):
 p=O/name;assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n');p.chmod(0o600);return bind(p)
raw=D/'current74-one-reviewed-configured-full.log';assert bind(raw)['bytes']==80268 and sha(raw)=='38029425f98c3416b3dd8ad82a90f9ca96ba2e2f1818e9024286854a61bdf684';s=raw.read_text();assert 'No space left on device' in s and '/home/agent/.robocorp' in s and '/workspace/actions-cloud/robocorp' not in s
assert not re.search(r'pytest(?: |\s+-)',s) and not re.search(r'\d+ passed(?:,| in )',s) and 'bringing up nodes' not in s and not re.search(r'\d+ workers \[',s)
terminal=D/'current74-one-reviewed-configured-full-terminal.json';assert bind(terminal)['bytes']==464 and sha(terminal)=='27fcafcea7a3c1942717517ab97812b8586762bfa6cbeed701f7e12c549688fc';t=json.loads(terminal.read_text());assert t['returncode']==4 and t['elapsed_seconds']==18.849684864995652 and t['head']==H and t['tree']==T
owner=D/'OWNERFINAL-current74-reviewed-full-command-adoption-and-execution-HOLD.json';assert sha(owner)=='17c61faa68cbdfe2daf6915335cc2a93ccd67328dbdf34c2cb2455963ad35eca';d=json.loads(owner.read_text());assert d['head']==H and d['tree']==T and d['current_full_execution_attempts']==0
assert len(d['all_distinct_original_and_LIGHT_reference_bindings_verified'])==110 and d['original_reference_count']==68 and d['owner_evidence_reference_count']==42
for row in d['all_distinct_original_and_LIGHT_reference_bindings_verified']:check(row)
for key in ['exact_contract','immutable_constructor','old784_launcher_preserved','preexecution_source1423_Git_FS_body_exec_verified']:check(d[key])
for row in d['independent_current74_reviews']:check(row)
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and not git('status','--porcelain')
rows=[]
for rec in git('ls-tree','-rz',H).split(b'\0'):
 if not rec:continue
 a,p=rec.split(b'\t',1);mode,kind,blob=a.decode().split();path=p.decode();f=R/path;body=os.readlink(f).encode() if mode=='120000' else f.read_bytes();assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==blob
 if mode!='120000':assert bool(f.stat().st_mode&0o111)==(mode=='100755')
 rows.append({'path':path,'mode':mode,'blob':blob,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
assert len(rows)==1423
proof=json.loads(Path(d['preexecution_source1423_Git_FS_body_exec_verified']['path']).read_text());assert rows==proof['all1423']
prep=json.loads(Path(d['prepared_inputs']['record']['path']).read_text());check(d['prepared_inputs']['record']);assert prep['measured_input_count']==30
for path,h in prep['all30_current_inputs_exact_prepared_Git_bytes'].items():assert sha(R/path)==h
for pkg,row in prep['five_own_environment_configs'].items():assert sha(R/pkg/'.venv/pyvenv.cfg')==row['config_sha256'] and str((R/pkg/'.venv/bin/python').resolve())==row['python_resolved']
assert len(prep['five_actual_concrete_module_origins_and_prefixes'])==5
for row in prep['five_actual_concrete_module_origins_and_prefixes']:assert Path(row['prefix']).resolve().is_relative_to(R) and Path(row['origin']).is_relative_to(R) and Path(row['origin']).is_file()
for row in d['prepared_inputs']['five_concrete_source_origins']:check(row)
pin=R/d['prepared_inputs']['ignored_pinned_RCC']['path'];assert sha(pin)=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428' and stat.S_IMODE(pin.stat().st_mode)==0o711
check(d['prepared_inputs']['managed_gateway'])
auth=D/'root-one-reviewed-current74-full-authorization.json';assert sha(auth)=='e6de8234f7629fc58d5831b3405da9c35e8c8fa81135949199c0643a2acf485c';a=json.loads(auth.read_text());assert a['head']==H and a['tree']==T
post=D/'root-current74-postfull-complete-source-and-reference-readback.json';assert sha(post)=='f0ce571d524f4ab266c590e97d87fa787ba7cefee78bf2c0e9b9ceccc70a4272';postd=json.loads(post.read_text());assert postd['tracked_count']==1423 and postd['head']==H
activate=Path('/workspace/actions-cloud/activate.sh');ab=activate.read_bytes();assert len(ab)==987 and hashlib.sha256(ab).hexdigest()=='6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
assert all(line.startswith('export ') for line in ab.decode().splitlines() if line.strip())
expected={}
for line in ab.decode().splitlines():
 name,value=line.removeprefix('export ').split('=',1);value=value.strip('"');value=value.replace('$ACTIONS_CLOUD_ROOT','/workspace/actions-cloud');expected[name]=value
assert expected['ROBOCORP_HOME']=='/workspace/actions-cloud/robocorp' and expected['XDG_CACHE_HOME']=='/workspace/actions-cloud/cache' and expected['POETRY_CACHE_DIR']=='/workspace/actions-cloud/cache/pypoetry' and expected['GOMAXPROCS']==expected['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
# Existing cached Toolkit only; no RCC invocation, installer or execution here.
assert C.is_dir() and yaml.safe_load((C/'identity.yaml').read_bytes())==yaml.safe_load((R/'developer/setup.yaml').read_bytes())
cachebindings=[bind(C/p) for p in ['identity.yaml','rcc_plan.log','bin/python3.12','bin/poetry']]
assert (C/'bin/python').is_symlink() and (C/'bin/python').resolve()==C/'bin/python3.12' and os.access(C/'bin/python',os.X_OK) and os.access(C/'bin/poetry',os.X_OK)
for p in [R/'developer/toolkit.py',R/'action_server/tasks.py',R/'action_server/src/actions/server/_build_common/process_call.py']:assert p.is_file()
contract=json.loads(Path(d['exact_contract']['path']).read_text());original_argv=contract['argv'];assert original_argv==d['exact_argv'] and original_argv[:6]==['env','PYTEST_XDIST_AUTO_NUM_WORKERS=2','timeout','--signal=TERM','--kill-after=10s','600s']
# Freeze standalone metadata-only preflight proposal; deliberately NOT executed here.
preflight=O/'proposed-managed-activation-preflight.py';assert not preflight.exists()
precode='''from pathlib import Path
import hashlib,json,os,subprocess,sys,yaml
R=Path("/workspace/engineering/pr300")
C=Path("/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534")
assert Path.cwd().resolve()==R
assert subprocess.check_output(["git","-C",str(R),"rev-parse","HEAD"]).decode().strip()=="'''+H+'''"
assert subprocess.check_output(["git","-C",str(R),"rev-parse","HEAD^{tree}"]).decode().strip()=="'''+T+'''"
assert not subprocess.check_output(["git","-C",str(R),"status","--porcelain"])
assert Path(sys.executable).resolve()==C/"bin/python3.12"
expected='''+repr({k:v for k,v in expected.items() if k!='PATH'})+'''
for key,value in expected.items(): assert os.environ.get(key)==value,key
assert os.environ["PATH"].split(os.pathsep)[0]=="/workspace/actions-cloud/bin"
assert yaml.safe_load((C/"identity.yaml").read_bytes())==yaml.safe_load((R/"developer/setup.yaml").read_bytes())
cache='''+repr(cachebindings)+'''
for row in cache:
 p=Path(row["path"]); assert p.stat().st_size==row["bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==row["sha256"]
for p in [C/"bin/python",C/"bin/poetry"]: assert p.is_file() and os.access(p,os.X_OK)
assert subprocess.check_output(["command-not-invoked"],stderr=subprocess.DEVNULL) if False else True
assert Path(os.environ["ACTIONS_RUNTIME_TEST_PYTHON"]).is_file()
prepared='''+repr(prep['all30_current_inputs_exact_prepared_Git_bytes'])+'''
for path,h in prepared.items(): assert hashlib.sha256((R/path).read_bytes()).hexdigest()==h
configs='''+repr(prep['five_own_environment_configs'])+'''
for package,row in configs.items():
 assert hashlib.sha256((R/package/".venv/pyvenv.cfg").read_bytes()).hexdigest()==row["config_sha256"]
 assert str((R/package/".venv/bin/python").resolve())==row["python_resolved"]
statv=os.statvfs(R); assert statv.f_bavail*statv.f_frsize>=1200000000
print("PASS_MANAGED_ACTIVATION_CURRENT_SOURCE_CACHED_TOOLKIT_READONLY_PREFLIGHT")
'''
# Remove deliberately unreachable marker before freezing; preflight invokes only read-only Git commands.
precode=precode.replace('assert subprocess.check_output(["command-not-invoked"],stderr=subprocess.DEVNULL) if False else True\n','')
ast.parse(precode);preflight.write_text(precode);preflight.chmod(0o600)
# Bash sources immutable activation exports, invokes EXISTING cached Python for read-only preflight, then exact old reviewed configured command.
# Arguments are positional to avoid shell interpolation of the multiline python-c payload.
bashcode='set -euo pipefail\nsource "$1"\n"$2" "$3"\nshift 3\nexec "$@"\n'
successor_argv=['bash','--noprofile','--norc','-c',bashcode,'current74-managed-activation-successor',str(activate),str(C/'bin/python'),str(preflight),*original_argv]
proposal=save('PROPOSED-current74-managed-activation-preflight-and-one-full-successor.json',{'status':'PROPOSAL_ONLY__EXECUTION_HOLD_DISTINCT_ROOT_RELEASE_REQUIRED','head':H,'tree':T,'target':BASE,'cwd':str(R),'activation':bind(activate),'activation_export_names':list(expected),'required_nonsecret_environment':{k:v for k,v in expected.items() if k in ['ROBOCORP_HOME','XDG_CACHE_HOME','XDG_CONFIG_HOME','POETRY_CACHE_DIR','POETRY_CONFIG_DIR','GOMAXPROCS','PYTEST_XDIST_AUTO_NUM_WORKERS']},'PATH_required_first_entry':'/workspace/actions-cloud/bin','preflight':bind(preflight),'cached_toolkit':{'root':str(C),'setup_identity_matches_current':True,'readiness_scope':'Existing cached identity/Python/Poetry metadata only; no bootstrap/import/provider/cold install/actual RCC verification performed','bindings':cachebindings},'argv':successor_argv,'retained_configured_command_exact':d['exact_contract'],'outer_FULL_deadline_TERM':600,'kill_after':10,'worker2_environment':'Ownedactivation sets2; unchanged reviewed command repeats2 before configuredRuntime n-auto','attempts_allowed_only_after_new_release':1,'original_attempt':{'authorization_consumed':bind(auth),'terminal_failed':bind(terminal),'raw_private':bind(raw),'no_counts_reported':'pytest cases/workers/PASS/SKIP/error counts UNREPORTED; not zero-case test execution'},'requirements':['Original root e6de is consumed; no automatic retry','Named root successor authorization must bind this activation/preflight/argv, exact74/tree2238 and current prepared source/refs','Independent failed-home/current-cache preservation receipt is required before release; original complete historical cache baseline UNKNOWN; no completion claim','Current heavy300 has terminated; check root serialized slot and any cleanup/full workload independently','Fresh workspace available capacity>=1200000000B immediately before execution','Rehash1423 complete FS/Git/modes, original68+LIGHT and prepared30/five origins/RCC immediately before and after','Use existing matching cachedToolkit only; if cache inputs/readiness mismatch HOLD, no replacement environment, installer or recovered cache baseline inference','Preserve one new private log and exact terminal; original rootFULL staysFAIL even if a later successor passes'],'not_executed_by_reviewer':True})
lesson='''An absolute managed RCC executable does not select its managed RCC home.
Source the owned activation script and verify RCC home, XDG/Poetry caches,
PATH and explicit worker/Go limits before the gateway. Admit the existing
cached toolkit against current setup identity and executable bindings.
A gateway failure while preparing another home supplies no pytest counts or
source-suite acceptance; retain that failed attempt separately from any
newly authorized successor.
'''
canon=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md');anchor='RCC owns the isolated toolchain and holotree cache.';ct=canon.read_text();assert anchor in ct
patch=O/'canonical-managed-gateway-activation-proposed.patch';assert not patch.exists();patch.write_text('--- a/docs/skills/repository-operations.md\n+++ b/docs/skills/repository-operations.md\n@@\n+'+'\n+'.join(lesson.rstrip().splitlines())+'\n+\n '+anchor+' Poetry and committed package lockfiles\n');patch.chmod(0o600)
report={'schema':'actions-independent-current74-root-gateway-failure-and-activation-proposal/v1','verdict':'GO_SCOPED_DIAGNOSIS_AND_NAMED_ACTIVATION_PREFLIGHT_SUCCESSOR_PROPOSAL_ONLY__HOLD_EXECUTION','head':H,'tree':T,'target':BASE,'original_full_result':{'RCC_returncode':4,'elapsed_seconds':t['elapsed_seconds'],'raw_private':bind(raw),'terminal':bind(terminal),'stage':'Outer toolkit environment preparation before configured pytest command/worker','observed_fixed_categories':{'ENOSPC':True,'default_HOME_robocorp_root':True,'managed_robocorp_root_in_original_log':False,'pytest_command_present':False,'pytest_worker_start_present':False,'pytest_terminal_pass_summary_present':False},'pytest_counts':'UNREPORTED; no tests started observed, not full source FAIL/PASS or zero-case admission','bounded_attribution':'Root declared no owned activation; reviewed fullargv setsxdist2 but noROBOCORP_HOME. Immutable export-only activation selects managedhome. Raw preparation useddefault/home/agent/.robocorp andfailedENOSPC. Source suite never reached; no upstream/cache-corruption/source-cause attribution.'},'source_preservation':{'complete1423_Git_FS_bodies_exec_exact':True,'owner_original68_plus_LIGHT42_unique_refs_rehashed':110,'prepared_inputs':30,'own_environment_configs_and_recorded_origins':5,'RCC_pin0711_unchanged':True,'rootpostreadback':bind(post),'LIGHT_source_full_gates_remain_separate':True},'activation_readonly_admission':{'activation':bind(activate),'export_only':True,'cached_setup_identity_equals_current_source':True,'existing_cached_python_poetry':cachebindings,'scope':'Current cached metadata readiness only, no complete-cache baseline or preservation/restore claim'},'successor_proposal':proposal,'original_failed_home':'Original whole historical cache/body baseline UNKNOWN; owner preservation work is unfinished/unreviewed at this freeze, never asserted complete','remaining_HOLD':['New exact root authorization and independent preservation/currentcapacity/serialization/preflight','Current74 actual configured source suite NOT_RUN by original failed gateway or reviewer','Actual ASGI/TCP/private/consumer/native/provider/whole86/fullgraph/release remain unresolved','No installer/new environment/retry or replacement toolkit qualification authorized'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; exact7-line managed activation paragraph proposed at existing RCC toolchain/home guidance','Exact_delta':bind(patch),'Exact_added_text':lesson,'Durable_learning_captured':'An absolute RCC pin alone does not bind managedhome; admit activation exports/cached setup identity before source gate, preserve failed outerenvironment attempt separately from unrun pytest/successor scope','Evidence':[bind(raw),bind(terminal),bind(activate),proposal]+cachebindings,'Stale_or_ambiguous_guidance_removed':'Adds missing managed activation boundary to existing toolchain guidance; refuses gatewayFAIL-to-source-count or futurepreservation/earlierbaseline claims','Remaining_uncertainty':'Whole old failedhome historical baseline/preservation, newactual full result/currentCI/private/release unqualified'},'Upstream_disposition':'none','read_only_no_activation_execution_tests_gateway_provider_native_source_index_download_push_merge':True,'original_root_authorization_consumed':bind(auth),'all_rehashed_binding_files':len(checked),'review_script':bind(__file__)}
print(json.dumps(save('OWNERFINAL-independent-current74-root-gateway-failure-and-managed-activation-proposal.json',report)))
