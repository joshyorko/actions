"""Construct immutable preparation only; no package import or gates."""
import ast,hashlib,json,os,stat
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=Path('/workspace/engineering/pr307')
PARENT=Path('/workspace/engineering/pr307-actuale2-refresh-PREPARATION')
ATTEMPT=Path('/workspace/engineering/pr307-current2314-light-once-owned');assert not ATTEMPT.exists()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def bind(p):
 p=Path(p);raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':sha(raw),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def save(n,j):
 p=BASE/n;assert not p.exists();p.write_text(json.dumps(j,indent=2,sort_keys=True)+'\n');p.chmod(0o400);return bind(p)
proof=PARENT/'complete-current-ordinary-union-source-and-retained-evidence-proof-v2.json'
j=json.loads(proof.read_text());rows=[bind(proof),bind(PARENT/'OWNERFINAL-pr307-currente2-ordinary-source-union-checkpoint-v2.json'),bind(PARENT/'OWNERFINAL-pr307-currente2-LIGHT-FULL-PREPARATION-NOTRUN-v2.json'),bind('/workspace/actions-cloud/activate.sh'),bind('/workspace/actions-cloud/bin/rcc'),bind('/workspace/engineering/pr307-guard-owned/outer_invoke_no_yaml.py')]
control=BASE/'controlled_invoke_owned_stage.py';ast.parse(control.read_text());control.chmod(0o444);rows.append(bind(control))
expected={}
for line in Path('/workspace/actions-cloud/activate.sh').read_text().splitlines():
 if line.startswith('export '):
  key,value=line[7:].split('=',1)
  if key!='PATH':expected[key]=value.strip('"').replace('$ACTIONS_CLOUD_ROOT','/workspace/actions-cloud')
assert len(expected)==18
forbidden=[]
for p in [ROOT/'action_server/output/output.robolog',ROOT/'action_server/output/log.html',ROOT/'action_server/src/actions/server/_oauth2_config.py',ROOT/'action_server/src/actions/server/_static_contents.py']:
 forbidden.append({'path':str(p),'exists':p.exists(),'binding':bind(p) if p.exists() else None})
origin_code='''import importlib,json,sys
from pathlib import Path
import toolkit
root=toolkit.REPOSITORY_ROOT;out=Path('/workspace/engineering/pr307-current2314-light-once-owned/own-five-origins')
records=[]
for package,module in [('actions','actions'),('actions-http-helper','actions_http'),('devutils','devutils.invoke_utils'),('work-items','actions.work_items'),('action_server','actions.server')]:
 prefix=root/package/'.venv';dest=out/(package+'.json')
 code='import importlib,json,sys; from pathlib import Path; m=importlib.import_module('+repr(module)+'); prefix=Path('+repr(str(prefix))+'); source=Path(m.__file__).resolve(); assert Path(sys.prefix).resolve()==prefix.resolve(); assert source.is_relative_to(Path('+repr(str(root/package/'src'))+').resolve()); Path('+repr(str(dest))+').write_text(json.dumps({"module":'+repr(module)+',"origin":str(source),"prefix":sys.prefix,"python":sys.executable}))'
 toolkit.poetry(package,'run','python','-c',code);records.append(json.loads(dest.read_text()))
assert len(records)==5
(out/'all-five.json').write_text(json.dumps(records,indent=2)+'\\n')
'''
gen_code='''import hashlib,json,sys,types
from pathlib import Path
import toolkit
root=toolkit.REPOSITORY_ROOT;p=root/'.github/workflows/_gen_workflows.py';raw=p.read_bytes()
owned=Path('/workspace/engineering/pr307-current2314-light-once-owned/generated-eight-and-Github30/generated');assert not owned.exists();owned.mkdir(mode=0o700)
mod=types.ModuleType('current307_reviewed_generator');mod.__file__=str(p);sys.modules[mod.__name__]=mod
exec(compile(raw,str(p),'exec'),mod.__dict__);mod.CURDIR=owned;records=[]
for target in mod.TARGETS:
 target.generate();generated=(owned/target.target).read_bytes();tracked=(p.parent/target.target).read_bytes();assert generated==tracked;records.append({'path':target.target,'bytes':len(generated),'sha256':hashlib.sha256(generated).hexdigest()})
assert len(records)==8
Path('/workspace/engineering/pr307-current2314-light-once-owned/generated-eight-and-Github30/eight-outputs.json').write_text(json.dumps(records,indent=2))
code='import json,yaml;from pathlib import Path;root=Path('+repr(str(root))+');rows=sorted(set(root.glob(".github/**/*.yaml"))|set(root.glob(".github/**/*.yml")));assert len(rows)==30;[yaml.safe_load(p.read_bytes()) for p in rows];Path("/workspace/engineering/pr307-current2314-light-once-owned/generated-eight-and-Github30/thirty-YAML.json").write_text(json.dumps([str(p.relative_to(root)) for p in rows]))'
toolkit.poetry('action_server','run','python','-c',code)
'''
ast.parse(origin_code);ast.parse(gen_code)
config=save('immutable-one-LIGHT-inputs.json',{'schema':'CURRENT2314_SOURCE_LIGHT_ONCE_INPUTS','source_proof':bind(proof),'bindings':rows,'managed_activation_expected':expected,'origin_probe_code':origin_code,'generator_probe_code':gen_code,'controlled_runner':bind(control),'forbidden_generated_outputs':forbidden,'light_workspace_floor_bytes':536870912})
launcher=BASE/'launch_one_owned_light.py';s=launcher.read_text();assert s.count('REPLACE_CONFIG_SHA')==1;s=s.replace('REPLACE_CONFIG_SHA',config['sha256']);ast.parse(s);launcher.write_text(s);launcher.chmod(0o444)
argv=['timeout','--signal=TERM','--kill-after=10s','900s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',str(launcher),'/workspace/engineering/pr307-currente2-concrete-LIGHT-PREEXECUTION/root-one-LIGHT-release.json','ROOT_OWNER_RELEASE_SHA','IMMUTABLE_INDEPENDENT_REVIEW_PATH','IMMUTABLE_INDEPENDENT_REVIEW_SHA']
owner={'schema':'OWNERFINAL_CURRENT2314_CONCRETE_LIGHT_PREEXECUTION','status':'FROZEN_NOEXECUTION_REQUIRES_INDEPENDENT_GO_AND_ROOT_DISTINCT_RELEASE','source':'2314aea95795fbc1372a6f7b0b7b298b7cf124c3','tree':'2987ed3a23e560fb40e13aadbcd6bd613ead3f25','source_union_owner':rows[1],'config':config,'launcher':bind(launcher),'controlled_staged_Invoke':bind(control),'constructor':bind(__file__),'argv_adoption_after_activation':argv,'argv_remaining_bound_fields':'Root release SHA and owner-announced independent path/SHA are not yet available; root must replace precisely before execution','cwd':str(ROOT),'activation':bind('/workspace/actions-cloud/activate.sh'),'required_decision':'GO_CURRENT2314_LIGHT_PREEXECUTION','root_release_schema':{'decision':'RELEASE_ONE_CURRENT2314_LIGHT_ONLY','source':'2314aea95795fbc1372a6f7b0b7b298b7cf124c3','tree':'2987ed3a23e560fb40e13aadbcd6bd613ead3f25','launcher_sha256':bind(launcher)['sha256'],'config_sha256':config['sha256'],'independent_review':{'path':'EXACT_OWNERANNOUNCED_PATH','sha256':'EXACT_OWNERANNOUNCED_HASH'},'file':'exclusive regular nonsymlink0600 ownUID/GID'},'guards':{'source_typed_rows':1442,'prepared30':30,'own_five_configs':5,'old_owned_refs':len(j['retained_original_evidence']),'before_and_always_finally':'full1442FS/body/exec,30inputs/fiveconfigs/alloldrefs/configdeclaredbindings+fixedignoredgeneratedoutputidentities. Primary exception retained on postguard failure; separate original terminal','config_own_SHA':'checked initially; launcher exactSHA enforced by root release; both externally reviewed','root_hard_kill':'Postguard cannot be guaranteed after outerSIGKILL; such outcome remains incomplete/HOLD'},'logging_interfaces':{'ToolkitTest':'actual unchanged developer/toolkit.py toolkit_test -> cached outer python -m pytest developer/tests. Cache haspytest8.3.4; no *log*pytest* namespace/dist-info files. Distinct absentALL basetemp/JUnit+absolute private stdout/stderr; no Runtime loggerCLI/pluginclaim','Runtime_guard_focus':'separate absentALL basetemp/JUnit+absolute --robocorp-log-output. No other package pytest invoked','pytest_global_inheritance':'Reject inheritedPYTEST_ADDOPTS/PYTHONOPTIMIZE atlauncherentry; inject separate own options only perpytestphase','configuredstatic_generator_origin_Invoke':'no pytest invocation; each absolute private stdio/outputroot'},'controlled_Invoke_scope':'unchanged actual task/helper/pyproject/lock staged underuniqueowned root; existingownRuntime .venv symlink anddevutils link; realInvokeProgram/YAML-blocking outer; owned fakegh only; successpair +secondexit17/preserveprior/notprivatecause; no productconfigoutput writes; stagedsyntheticreleasecontentUNQUALIFIED','bounds':{'root_outer_seconds':900,'rootkill_grace_seconds':10,'primary_sequence_budget_seconds':780,'per_phase_budgets_seconds':{'Doctor':120,'origins':120,'Toolkit':180,'focus':180,'static':180,'generator':120,'controlled':210},'Invoke_each':90,'Invoke_YAML_probe':30,'fallback_owned_wrapper_waits':5,'full_NOTRUN':True},'fresh_conditions':['Currentsourceclean2314/tree2987 andallfrozenbindings','FreshuniqueABSENTattemptroot; workspace>=536870912; rootserialization/no otherheavy','Managedactivation18values+PATHprefix verified; cachedprefix exact; ownRuntime testPython explicit perphase','Independent concretePREEXECGO+distinct rootrelease; no automaticretry'], 'documentation_improvement':{'canonical_file':'docs/skills/repository-operations.md','delta':'Retain exact original307 guard/gateway/sourceauthority lesson already imported; proposal documents interface-specific logging without adding unsupported env behavior','evidence':'source1442proof/actual canonicalToolkit definition/cachedplugin metadata/owned unchangedInvoke sources','stale_ambiguity_removed':'07e2 plan was not executable; cachedToolkit cannot accept Runtime loggingCLI; stagedInvoke no longer writes productconfig/sharedlogger','remaining_uncertainty':'AllcurrentLIGHTgatesNOTRUN; actualfiveorigin,41controls/static/gen,stagePoetry boundary need reviewedoneexecution; FULLtmpfloor/OAuthauthority/freshCI/native remain HOLD'},'upstream_disposition':'none','tests_installs_gateway_native_network_execution':False}
ob=save('OWNERFINAL-current2314-concrete-LIGHT-PREEXECUTION.json',owner)
print(json.dumps({'owner':ob,'config':config,'launcher':bind(launcher),'control':bind(control)}))
