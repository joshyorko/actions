import ast,datetime,hashlib,json,os,stat,subprocess
from pathlib import Path
B=Path(__file__).resolve().parent;R=Path('/workspace/engineering/pr305');O=Path('/workspace/engineering/pr305-actual-e2-refresh');P=Path('/workspace/engineering/pr305-currentf75-readonly-LIGHT-readiness-review');REUSED=Path('/workspace/engineering/pr307-current9760-token-light-once6-active-output-address-PREEXECUTION-NOTRUN/launch_one_owned_token_light_once6_current_probe_outputs.py')
SOURCE='f75dcae52fcd78c5c382d3903b012e5b049ca48b';TREE='851834ae6cc87f42abfcf3c963542191e2815599';ATTEMPT='/workspace/engineering/pr305-currentf75-private-bounded-LIGHT-once1-owned'
def row(p):
 p=Path(p);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(m.st_mode))}
def exact(r):assert row(r['path'])==r;return Path(r['path']).read_bytes()
def put(n,v):
 p=B/n
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('rev-parse','HEAD^{tree}').decode().strip()==TREE and not git('status','--porcelain')
oldowner=row(O/'OWNERFINAL-current-f75d-e2-ordinary-union-and-isolated-LIGHT-FULL-PREPARATION.json');old=json.loads(exact(oldowner));c=json.loads(exact(old['FULL_conditional_preparation']['config']));readiness=row(P/'OWNERFINAL-readonly-currentf75-source-LIGHT-readiness-HOLD-and-minimal-successor-plan.json');assert readiness['sha256']=='af0dbcde1da8545eab52d4a4dc8162e3fcbc3241aba73f9ad9336b028df28650'
refs=[oldowner,readiness,row(REUSED),row('/workspace/actions-cloud/activate.sh'),row(c['original_native_config'])]+old['frozen_input_bindings']+c['retained_actual_files_and_helpers']+c['prepared_environment_and_RCC_bindings']
for x in refs:exact(x)
rows=json.loads(Path(c['source_inventory']).read_text());assert len(rows)==1441
for x in rows:
 p=R/x['path'];b=os.readlink(p).encode() if x['mode']=='120000' else p.read_bytes();assert hashlib.sha256(b).hexdigest()==x['sha256'] and stat.S_IMODE(p.lstat().st_mode)==x['fs_mode']
for n,h in c['prepared30_inputs'].items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h
for package,module in c['concrete_origin_packages']:assert (R/package/'.venv/bin/python').is_file()
# Commands import Toolkit only after launcher strict ROOT review/release and before guard admission.
phases=[]
def phase(name,code,budget,pytest=False,logger=False):phases.append({'name':name,'code':code,'budget':budget,'pytest':pytest,'package_logger':logger})
phase('Doctor','import toolkit; toolkit.doctor()',120)
for package,module in c['concrete_origin_packages']:
 dest=ATTEMPT+'/own-origin-'+package+'/origin.json';prefix=str(R/package/'.venv');src=str(R/package/'src')
 code='import toolkit; toolkit.poetry('+repr(package)+', "run", "python", "-c", '+repr('import importlib,json,sys;from pathlib import Path;m=importlib.import_module('+repr(module)+');p=Path('+repr(prefix)+');assert Path(sys.prefix).resolve()==p.resolve();origin=Path(m.__file__).resolve();assert origin.is_relative_to(Path('+repr(src)+').resolve());d=Path('+repr(dest)+');assert not d.exists() and not d.is_symlink();d.write_text(json.dumps({"module":'+repr(module)+',"origin":str(origin),"prefix":sys.prefix,"python":sys.executable}));d.chmod(0o600)')+')'
 phase('own-origin-'+package,code,30)
phase('Toolkit','import toolkit; toolkit.toolkit_test()',180,True,False)
phase('devutils-checkout','import toolkit; toolkit.poetry("devutils","run","python","-m","pytest","-n0","-q","tests/test_runtime_checkout_bytes.py","tests/test_runtime_checkout_workflows.py")',180,True,False)
selectors=['tests/action_server_tests/mcp/test_canvas_runtime_admission.py','tests/action_server_tests/test_browser_origin_acceptance.py','tests/action_server_tests/mcp/test_mcp_apps_authoring.py','tests/action_server_tests/test_rcc_runtime_adapter.py','tests/action_server_tests/test_dakota_rcc_acceptance.py','tests/action_server_tests/test_source_staging_rcc_consumer.py','tests/action_server_tests/test_auth_route_inventory.py','tests/action_server_tests/test_auth_route_enforcement.py','tests/action_server_tests/run_outputs/test_transport.py','tests/action_server_tests/test_shutdown_response_order.py']
args=['action_server','run','python','-m','pytest','-n0','-q',*selectors,'-m','not integration_test','--tb=short'];phase('Runtime-scoped','import toolkit; toolkit.poetry('+','.join(repr(x) for x in args)+')',180,True,True)
phase('configured-static','import toolkit; toolkit.poetry("action_server","run","invoke","lint"); toolkit.poetry("action_server","run","invoke","typecheck")',180)
gencode='''import hashlib,json,sys,types
from pathlib import Path
import toolkit
root=toolkit.REPOSITORY_ROOT;p=root/'.github/workflows/_gen_workflows.py';raw=p.read_bytes()
phase=Path(PHASE_PLACEHOLDER);owned=phase/'generated';assert not owned.exists() and not owned.is_symlink();owned.mkdir(mode=0o700)
mod=types.ModuleType('current_f75_owned_generator');mod.__file__=str(p);sys.modules[mod.__name__]=mod
exec(compile(raw,str(p),'exec'),mod.__dict__);mod.CURDIR=owned;records=[]
for target in mod.TARGETS:
 target.generate();generated=(owned/target.target).read_bytes();tracked=(p.parent/target.target).read_bytes();assert generated==tracked;records.append({'path':target.target,'bytes':len(generated),'sha256':hashlib.sha256(generated).hexdigest()})
assert len(records)==8
result=phase/'eight.json';assert not result.exists();result.write_text(json.dumps(records));result.chmod(0o600)
code='import hashlib,json,yaml;from pathlib import Path;root=Path('+repr(str(root))+');rows=sorted(set(root.glob(".github/**/*.yaml"))|set(root.glob(".github/**/*.yml")));assert len(rows)==30;[yaml.load(p.read_bytes(),Loader=yaml.BaseLoader) for p in rows];d=Path('+repr(str(phase/'thirty.json'))+');assert not d.exists() and not d.is_symlink();d.write_text(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in rows}));d.chmod(0o600)'
toolkit.poetry('action_server','run','python','-c',code)
'''.replace('PHASE_PLACEHOLDER',repr(ATTEMPT+'/generated-eight-and-Github30'))
phase('generated-eight-and-Github30',gencode,120)
for x in phases:ast.parse(x['code'])
guard=row(B/'current_f75_readonly_input_guard_NOTRUN.py');refs.append(guard);seen={}
for x in refs:
 if x['path'] in seen:assert seen[x['path']]==x
 seen[x['path']]=x
cfg={'schema':1,'source':SOURCE,'tree':TREE,'source_root':str(R),'source_leaf_count':1441,'source_inventory':row(c['source_inventory']),'cached_prefix':c['cached_toolkit_prefix'],'expected_activation':c['expected_activation_exports'],'forbidden_actual_operator_exports':c['forbidden_actual_operator_exports']+['ACTIONS_RCC_TEST_BINARY_SELECTOR','ACTIONS_RCC_TEST_BINARY','RUNTIME_RELEASE_TEST_BASELINE'],'workspace_floor_bytes':1288490189,'bindings':list(seen.values()),'prepared30':c['prepared30_inputs'],'five_prefix_bindings':c['prepared_environment_and_RCC_bindings'][:5],'origin_packages':c['concrete_origin_packages'],'native_baseline':row(c['original_native_config']),'historical_Git_bodies':c['historical_original_Git_bodies'],'guard':guard,'phases':phases,'source_validation_scope':'Source+historicaldata preservation only, no oldnative/currentbinary/provider/browser outcome carry','outputs':{'attempt':ATTEMPT,'basetemps':'phase/basetemp','junit':'phase/junit.xml','Runtime_Robot':'phase/robot-output','origins':'own-origin-*/origin.json','generated':'generated-eight-and-Github30/generated +eight/thirty.json'},'original_sourceowner14_retained83_env7':'Preserved exactoriginalsubjects, not relabelled as actualcurrentLIGHT','source_LIGHT':'NOT_RUN','source_FULL':'NOT_RUN','bounds':{'primary_total_seconds':600,'primary_enclosing_parent':640,'before_guard':60,'always_post_guard':60,'ROOT_outer':900,'ROOT_KILL_grace':10}}
config=put('FROZEN-currentf75-private-bounded-LIGHT-inputs-NOTRUN.json',cfg)
oldsource=REUSED.read_text();tree=ast.parse(oldsource);wanted=['digest','write','dump','exact','regular_private_json','run_phase','package_env','gateway','pytest_env'];chunks=[];parity={}
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name in wanted:
  raw=ast.get_source_segment(oldsource,n);changed=raw.replace('remaining=780-', 'remaining=600-') if n.name=='run_phase' else raw;chunks.append(changed);parity[n.name]='EXACT_AST_AND_TEXT exceptdeclaredprimary780to600' if n.name=='run_phase' else 'EXACT_AST_AND_TEXT'
assert len(chunks)==9
header='''"""Prepared bounded private currentf75 LIGHT. Execution requires real ROOT review/release."""
import hashlib,json,os,signal,stat,subprocess,sys,time
from pathlib import Path
ROOT=Path('/workspace/engineering/pr305')
BASE=Path(__file__).resolve().parent
CONFIG=BASE/'FROZEN-currentf75-private-bounded-LIGHT-inputs-NOTRUN.json'
CONFIG_SHA=CONFIG_SHA_PLACEHOLDER
ATTEMPT=Path(ATTEMPT_PLACEHOLDER)
SOURCE='f75dcae52fcd78c5c382d3903b012e5b049ca48b'
TREE='851834ae6cc87f42abfcf3c963542191e2815599'
CACHED=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534')
PRIMARY_STARTED=None
'''.replace('CONFIG_SHA_PLACEHOLDER',repr(config['sha256'])).replace('ATTEMPT_PLACEHOLDER',repr(ATTEMPT))
main='''
def strict_review(path,sha):
 p=Path(path);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink() and stat.S_IMODE(m.st_mode)==0o400 and m.st_uid==os.getuid() and m.st_gid==os.getgid()
 raw=p.read_bytes();assert digest(raw)==sha;return json.loads(raw)
def main():
 global PRIMARY_STARTED
 assert len(sys.argv)==5 and sys.flags.optimize==0 and 'PYTHONOPTIMIZE' not in os.environ and 'PYTEST_ADDOPTS' not in os.environ
 assert Path(sys.prefix).resolve()==CACHED.resolve()
 assert Path(sys.argv[1])==BASE/'root-one-currentf75-private-LIGHT-release.json'
 auth=regular_private_json(sys.argv[1],sys.argv[2]);review=strict_review(sys.argv[3],sys.argv[4])
 cm=CONFIG.lstat();assert stat.S_ISREG(cm.st_mode) and not CONFIG.is_symlink() and stat.S_IMODE(cm.st_mode)==0o400 and digest(CONFIG.read_bytes())==CONFIG_SHA
 cfg=json.loads(CONFIG.read_bytes());selfrow=Path(__file__);sm=selfrow.lstat();assert stat.S_ISREG(sm.st_mode) and not selfrow.is_symlink() and stat.S_IMODE(sm.st_mode)==0o444
 assert set(auth)=={'schema','decision','source','tree','config_sha256','launcher_sha256','independent_source_review','independent_preexecution_review','serialized_no_other_heavy_or_installer'}
 assert type(auth['schema']) is int and auth['schema']==1 and auth['serialized_no_other_heavy_or_installer'] is True
 assert auth['decision']=='ROOT_RELEASE_ONE_CURRENT_F75_PRIVATE_BOUNDED_LIGHT_ONLY' and auth['source']==SOURCE and auth['tree']==TREE
 assert auth['config_sha256']==CONFIG_SHA and auth['launcher_sha256']==digest(selfrow.read_bytes())
 assert auth['independent_preexecution_review']=={'path':sys.argv[3],'sha256':sys.argv[4]}
 assert review['decision']=='GO_CURRENT_F75_PRIVATE_BOUNDED_LIGHT_PREEXECUTION' and review['source']==SOURCE and review['tree']==TREE and review['config_sha256']==CONFIG_SHA and review['launcher_sha256']==auth['launcher_sha256']
 sr=auth['independent_source_review'];source_review=strict_review(sr['path'],sr['sha256']);assert source_review['decision']=='GO_CURRENT_F75_PRIVATE_BOUNDED_LIGHT_SOURCE_PREPARED_ONLY' and source_review['source']==SOURCE and source_review['tree']==TREE and source_review['config_sha256']==CONFIG_SHA and source_review['launcher_sha256']==auth['launcher_sha256']
 for r in cfg['bindings']:exact(r)
 assert not ATTEMPT.exists() and not ATTEMPT.is_symlink();ATTEMPT.mkdir(mode=0o700);os.umask(0o077)
 primary=None;post=None;before=False;status='FAILED'
 env=os.environ.copy()
 try:
  guardcmd=[sys.executable,cfg['guard']['path'],str(CONFIG),CONFIG_SHA,'before'];run_phase('before-guard',guardcmd,env,60);before=True
  # Product Toolkit imports occur only inside admitted managed gateway commands after this guard.
  PRIMARY_STARTED=time.monotonic();env['ACTIONS_RUNTIME_TEST_PYTHON']=str(ROOT/'action_server/.venv/bin/python')
  for phase in cfg['phases']:
   free=os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize
   assert free>=cfg['workspace_floor_bytes'],'SOURCE_LIGHT_WORKSPACE_CAPACITY_HOLD'
   phaseenv=pytest_env(env,phase['name'],phase['package_logger']) if phase['pytest'] else env
   directory=run_phase(phase['name'],gateway(phase['code']),phaseenv,phase['budget'])
   if phase['pytest']:
    import xml.etree.ElementTree as ET
    j=directory/'junit.xml';cases=list(ET.fromstring(j.read_bytes()).iter('testcase'));ids=[(x.get('classname'),x.get('name')) for x in cases];assert cases and len(ids)==len(set(ids))
    counts={n:sum(x.find(n) is not None for x in cases) for n in ('failure','error','skipped')};assert counts['failure']==counts['error']==0
    dump(directory/'actual-unique-source-census.json',{'unique_cases':len(cases),'passed':len(cases)-counts['skipped'],**counts,'scope':'SOURCE_ONLY_SKIPS_RETAIN_UNQUALIFIED'})
  status='PASSED_CURRENT_F75_PRIVATE_BOUNDED_LIGHT_ONLY'
 except BaseException as error:primary=error
 finally:
  # Guard has its own finite budget independent of exhausted primary. Parent hard-kill still cannot promise finally.
  PRIMARY_STARTED=None
  try:
   run_phase('always-post-guard',[sys.executable,cfg['guard']['path'],str(CONFIG),CONFIG_SHA,'after'],env,60);post='PASS'
  except BaseException as error:
   post='FAIL';dump(ATTEMPT/'always-post-exception.json',{'exception_type':type(error).__name__})
   if primary is not None:primary.add_note('Independent bounded source LIGHT postguard failed; original primary preserved')
   else:primary=error
  if primary is not None or post!='PASS':status='FAILED'
  dump(ATTEMPT/'original-terminal.json',{'status':status,'before_passed':before,'post_guard':post,'primary_exception_type':type(primary).__name__ if primary else None,'source':SOURCE,'tree':TREE,'actual_NATIVE_FULL_PROVIDER_BROWSER_RELEASE':'NOT_RUN','one_attempt':'CONSUMED_NO_AUTORETRY','reader_descendant_reaping':'UNKNOWN_BEYOND_RECORDED_OWN_WRAPPER_WAITS'})
 if primary is not None:raise primary
if __name__=='__main__':main()
'''
launcher=B/'launch_current_f75_private_bounded_LIGHT_once_NOTRUN.py';launcher.write_text(header+'\n\n'.join(chunks)+'\n'+main);launcher.chmod(0o444);launch=row(launcher);ast.parse(launcher.read_text())
# Declared ROOT900 enclosure: before<=75+fallback10, primary<=600+lastfallback10, post<=75+fallback10; capture/admission margin retained.
contract=put('strict-currentf75-private-bounded-LIGHT-ROOT-release-contract-NOTRUN.json',{'schema':1,'status':'PREPARED_SOURCE_ONLY_NOT_EXECUTABLE_WITHOUT_REAL_SOURCE_PREEXEC_REVIEWS_ROOT_RELEASE','source':SOURCE,'tree':TREE,'config':config,'launcher':launch,'guard':guard,'attempt':ATTEMPT,'root_release':str(B/'root-one-currentf75-private-LIGHT-release.json'),'ROOT_exact_argv':['timeout','--signal=TERM','--kill-after=10s','900s','bash','-c','source /workspace/actions-cloud/activate.sh && exec /workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python '+str(launcher)+' "$@"','pr305-private-light',str(B/'root-one-currentf75-private-LIGHT-release.json'),'ROOT_RELEASE_SHA256','REAL_PREEXEC_REVIEW_PATH','REAL_PREEXEC_REVIEW_SHA256'],'required_root_release_schema':{'schema':1,'decision':'ROOT_RELEASE_ONE_CURRENT_F75_PRIVATE_BOUNDED_LIGHT_ONLY','source':SOURCE,'tree':TREE,'config_sha256':config['sha256'],'launcher_sha256':launch['sha256'],'independent_source_review':{'path':'REAL_SOURCE_REVIEW_PATH','sha256':'REAL_SOURCE_REVIEW_SHA256'},'independent_preexecution_review':{'path':'REAL_PREEXEC_REVIEW_PATH','sha256':'REAL_PREEXEC_REVIEW_SHA256'},'serialized_no_other_heavy_or_installer':True},'required_review_decisions':['GO_CURRENT_F75_PRIVATE_BOUNDED_LIGHT_SOURCE_PREPARED_ONLY','GO_CURRENT_F75_PRIVATE_BOUNDED_LIGHT_PREEXECUTION'],'bounds':cfg['bounds'],'source_floor':1288490189,'enclosure_limit':'Finite perphase GNU TERM+10 and parentbudget+15, original freshowned processgroupfallback5+5 only; before+primary600+post phases fit900 nominal. OS hard kill/fsync/systemcall stalls cannot promise finally; retain UNKNOWN rather than claim cleanupPASS.','main_not_executed':True})
reuse=put('reused-nine-functions-AST-profile-scope-and-old-command-preservation-proof-NOTRUN.json',{'schema':1,'source':SOURCE,'tree':TREE,'original_helper':row(REUSED),'helper_function_parity':parity,'profile_delta':'ONLYrun_phase primary780to600; separatePR305 strictrelease/guard/main/config explicit','current14_owner_originals':14,'retained83_helpers':83,'prepared7':7,'current30':'UNCHANGED','fiveactualorigins':'Prepared explicitpackageprobes NOTRUN','source1441':'UNCHANGED','existing_commands':'Doctor/ownfive/Toolkit/twoDevutils+tenRuntimeselectors/notintegration/staticlint+type/gen8all30 kept; JUnit/Robot/origin/generated outputs onlyfreshphase paths','original_LIGHT':'4d7b/unbounded body preserved unexecuted; old5306275P1S historical, FULLnever','original1192':'Guard prepared content/mode/member-set check; no reviewer native execution or newnativequalification','current_workspace_observation':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize,'source_floor':'Unchanged1288490189; executionHOLDnow','no_adoption':True})
controls=put('meaningful-private-admission-and-output-negative-control-plan-NOTRUN.json',{'schema':1,'status':'PREPARED_CONTROLS_NOT_EXECUTED','baseline_first_required':['Synthetic strictROOTrelease/config/review admission +exactargv composition with delegatedprocessseam; actualsource/guardinputsreadonly beforeROOTgate','Reject wrongmode/symlink/missingreview/wrongconfighash/wrongsource/tree/boolean-schema/serializationfalse BEFORE any productToolkit import or phasePopen','Reject poisoned/missing sourceinventory/current30/original14/helper83/native1192/managedRCCmode700-vsfixture711 input; preservebeforefailure/alwayspost observation separately','Reject stale generator/origin/JUnit/logger output bases/duplicate preexistingattempt/basetemp; admittedoutputs unique andnested phases only','Injected primary failure plus successful post =>originalfailure; primary+postfailure =>retain original exception and separate postFAIL; no fakecounts/no retries','Budget remaining<=20 rejectsnewprimaryphase; alwayspost independent60 budget; originalhelper groupfallbackonlyfreshownedgroup','Currentphase actualJUnit counter comes only originalXML uniqueclassnames/names; skips retained, failure/errors reject. No predicted275/179/currentcount borrowing'],'do_not_execute_in_source_review':'No imports, tests, gateway, native, cgroup/provider/sourcechange or ROOTrelease creation'})
canonical=B/'canonical-LIGHT-release-admission-before-import-and-owned-results-proposed.txt';canonical.write_text('Canonical target: docs/skills/repository-operations.md, frozen command adoption.\n\nAdmit the strict ROOT release, real independent review hashes and complete immutable input closure before importing product tooling. A LIGHT gate needs a finite enclosing primary budget and an independently bounded always-post guard, with the original failure kept when post-validation also fails. Separate source/preparation inputs from fresh phase-owned origin, JUnit, generated and absolute Robot outputs; audit nested executable output literals as well as the outer attempt path. Matching old prefixes and unchanged native selector source remain input evidence until actual current origin probes and source cases run. Preserve floor failures and unexecuted packets, and derive actual unique case counts from original results rather than reusing historical counts.\n');canonical.chmod(0o400)
assert not Path(ATTEMPT).exists() and not (B/'root-one-currentf75-private-LIGHT-release.json').exists()
allrefs=[row(p) for p in sorted(B.iterdir()) if p.is_file()]
owner=put('OWNERFINAL-currentf75-private-strict-bounded-LIGHT-SOURCE-and-control-plan-NOTRUN.json',{'schema':1,'status':'OWNER_FINAL_PRIVATE_CURRENTF75_BOUNDED_LIGHT_SOURCE_PREPARED_NOTEXECUTED','source':SOURCE,'tree':TREE,'source_count':1441,'source_clean':True,'same_existing_branch':'test/canvas-runtime-cache-isolation-20261010 unchanged','app_source_ref_config_env_delta':'NONE','original_owner':oldowner,'original_readonly_HOLD':readiness,'config':config,'launcher':launch,'guard':guard,'ROOT_contract':contract,'scope_reuse_proof':reuse,'meaningful_controls_plan':controls,'packet_bindings':allrefs,'immutable_input_rows':len(cfg['bindings']),'outputs':'ABSENT uniquephase origin/rawstdio/JUnit/Robot/generated only; no writingoldpreparationoroldattempt','strict_release_admission':'Physical600/nonsymlink/UIDGID/hash typedROOT +real SOURCE/PREEXEC review/config/self identity before guardedproductimports','current_LIGHT':'NOT_RUN','FULL_native_browser_provider_release':'NOT_RUN_HOLD','fresh_capacity':{'workspace':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize,'required_floor':1288490189,'status':'OBSERVATION_ONLY_ROOT_FRESH_CHECK_REQUIRED'},'required_next':'Independent SOURCEreview; meaningfulpureadmissioncontrols +concretePREEXEC review asROOTassigns; distinctROOTsingleexecutiononlyafterfreshcapacity+serializedslot. No selfadmission from preparation.','documentation':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta':row(canonical),'evidence':'Original4d7b LIGHT guard/budget/output gaps fromaf0d; reusedacceptedphasecapturer, newpreimport typedrelease+boundedbeforealwayspost; originalinputs exact/read-only sourceproof; allactualoutputs remainNOTRUN','stale_ambiguity':'Preparedcurrent1441/current30/oldprefixmetadata notactualcurrentLIGHT; historical275P1S/native1192 do not qualifyfreshsource/provider/browser; phaseclosureandpostscopehonest','remaining_uncertainty':'New source/control/PREEXEC review and actualguard/origins/sourcecensus/floor/cleanupobservations/FULL/CI/native/release pending. No tests or productimports executed.','upstream_disposition':'none'},'capture':datetime.datetime.now(datetime.timezone.utc).isoformat()})
for x in cfg['bindings']+allrefs:exact(x)
assert not git('status','--porcelain')
print(json.dumps(owner))
