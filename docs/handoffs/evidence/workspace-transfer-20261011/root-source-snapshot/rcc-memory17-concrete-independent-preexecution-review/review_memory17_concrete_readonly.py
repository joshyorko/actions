import ast, datetime, hashlib, json, os, stat, subprocess
from pathlib import Path
ROOT=Path('/workspace/engineering/rcc-memory17-concrete-independent-preexecution-review');os.umask(0o077)
def row(path):
 p=Path(path);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def put(name,value):
 p=ROOT/name
 if not isinstance(value,str):value=json.dumps(value,indent=2,sort_keys=True)+'\n'
 with p.open('x') as f:f.write(value);f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
ownerpath=Path('/workspace/engineering/rcc-memory17-pure-controls-concrete-preexecution-NOTRUN/OWNERFINAL-memory17-concrete-pure-control-launcher-config-and-root-once-preexecution-NOTRUN-v2.json')
assert row(ownerpath)['sha256']=='56d2b731ffcd6bcb3ebf5d752086e6bc30249f423279964d64271f8c8deb676f'
o=json.loads(ownerpath.read_bytes());configrow=o['config'];assert row(configrow['path'])==configrow
cfg=json.loads(Path(configrow['path']).read_bytes())
assert row(o['launcher']['path'])==o['launcher']==cfg['launcher']
for r in o['original_bindings']+cfg['frozen_bindings']:assert row(r['path'])==r,r['path']
assert cfg['source']==o['source']=='8d49d0865ad5ad27b2d4e325ec135212080625e8'
assert cfg['tree']==o['tree']=='a80600809d373038ca76e445ba0b7b79bb7eeaa6'
assert o['root_once']==str(Path(cfg['basetemp']).parent)==str(Path(cfg['junit']).parent)==str(Path(cfg['logger']).parent)
owned=Path(o['root_once']);assert not owned.exists() and not owned.is_symlink()
for key in ('basetemp','junit','logger'): assert not Path(cfg[key]).exists() and not Path(cfg[key]).is_symlink()
assert cfg['envelope']=={'before_seconds':120,'primary_seconds':120,'after_seconds':120,'all_kill_grace_seconds':10,'root_parent_seconds':420}
argv=cfg['pytest_argv'];assert argv[:5]==['timeout','--signal=TERM','--kill-after=10s','120s','/workspace/engineering/pr308/action_server/.venv/bin/python']
assert '-n0' in argv and argv[argv.index('--basetemp')+1]==cfg['basetemp']
assert argv[argv.index('--robocorp-log-output')+1]==cfg['logger'] and argv[argv.index('--junitxml')+1]==cfg['junit']
assert argv[argv.index('-o')+1]=='tmp_path_retention_policy=all'
source=Path(argv[-1]);tree=ast.parse(source.read_bytes());names=[]
for node in tree.body:
 if not isinstance(node,ast.FunctionDef) or not node.name.startswith('test_'):continue
 params=[d for d in node.decorator_list if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr=='parametrize']
 if not params:names.append(node.name);continue
 assert len(params)==1 and not params[0].keywords
 argnames=ast.literal_eval(params[0].args[0]).split(',');values=ast.literal_eval(params[0].args[1])
 for idx,valueset in enumerate(values):
  if len(argnames)==1:valueset=(valueset,)
  ids=[]
  for argname,value in zip(argnames,valueset):ids.append(str(value) if value is None or isinstance(value,(str,float,int,bool,complex)) else argname+str(idx))
  names.append(node.name+'['+'-'.join(ids)+']')
assert len(names)==len(set(names))==17
launcher_tree=ast.parse(Path(o['launcher']['path']).read_bytes());compile(launcher_tree,o['launcher']['path'],'exec')
assert cfg['expected_test_census']=={'passed':17,'failed':0,'errors':0,'skipped':0,'unique_cases':17}
scfg=json.loads(Path('/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/frozen-current8d49-source-LIGHT-inputs-v3.json').read_bytes())
assert cfg['activation']==scfg['expected_activation_exports'] and len(cfg['activation'])==18
assert cfg['path_prefix2']==['/workspace/actions-cloud/bin','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin']
assert cfg['forbidden_operator_exports']==scfg['forbidden_actual_operator_exports']
assert row('/workspace/actions-cloud/activate.sh')['sha256']=='6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
repo='/workspace/engineering/pr308';assert subprocess.check_output(['git','-C',repo,'rev-parse','HEAD']).decode().strip()==cfg['source']
assert subprocess.check_output(['git','-C',repo,'rev-parse','HEAD^{tree}']).decode().strip()==cfg['tree']
assert subprocess.check_output(['git','-C',repo,'status','--porcelain=v1'])==b''
assert len(subprocess.check_output(['git','-C',repo,'ls-tree','-rz','HEAD']).split(b'\0'))-1==1440
physical={'schema':1,'status':'MANDATORY_ROOT_EXTERNAL_PREFLIGHT_NOT_PERFORMED_BY_REVIEWER','reason':'Launcher parses config/release raw bytes and verifies hashes+scope, but does not itself enforce physical config/release path/type/mode/owner. ROOT must perform these exact checks in its distinct once parent immediately before invoking unchanged launcher.','exact_files':[{'path':cfg['root_release_path'],'mode':'0o600','sha256':'ROOT_DISTINCT_RELEASE_SHA256','uid':'CURRENT_ROOT_OPERATOR_UID','kind':'REGULAR_NON_SYMLINK'},{**configrow,'uid':'CURRENT_ROOT_OPERATOR_UID','kind':'REGULAR_NON_SYMLINK'},{**o['launcher'],'uid':'CURRENT_ROOT_OPERATOR_UID','kind':'REGULAR_NON_SYMLINK'}],'exact_release_path':cfg['root_release_path'],'exact_config_path':configrow['path'],'root_output_path':o['root_once'],'root_output_before_launch':'ABSENT_INCLUDING_DANGLING_SYMLINK','child_paths_before_launch':'ABSENT_AND_EXACT_DIRECT_CHILDREN','root_release_requirements':o['root_release_expected'],'argv':o['argv_template'],'only_ROOT_substitution':'ROOT_DISTINCT_HASH_REQUIRED_NOT_GRANTED -> measured freshly written600release SHA','independent_review_fields':o['independent_review_topfields_required'],'read_only_preflight_algorithm':['lstat each exact path; require stat.S_ISREG and not is_symlink, exact mode and st_uid==os.getuid.','Hash exact bytes; require accepted config/launcherSHA, fresh releaseSHA supplied to CLI.','Parse freshrelease: exact keys/schema/status/config/launcher/source/tree/root/serializedTrue and accepted independent review row; suppliedargv exactexceptfreshROOTreleaseSHA.','Require absentroot and directoutputpaths before launch; retain verifiedpreflightJSON in ROOT private wrapper.','Never create/reconstruct oldfailedroots or repair modes; anyfailedpreflight HOLD/no invocation.'],'mutation':'NONE_BY_REVIEWER'}
physicalrow=put('mandatory-ROOT-outer-physical-release-config-path-preflight-contract-NOTRUN.json',physical)
proof={'schema':1,'source':cfg['source'],'tree':cfg['tree'],'owner':row(ownerpath),'config':configrow,'launcher':o['launcher'],'all13_unique_original_rows_exact':len({r['path'] for r in o['original_bindings']})==13,'config_frozen_bindings_equal_owner':cfg['frozen_bindings']==o['original_bindings'],'expected_original_named_testcases_default_pytest_id_algorithm':names,'expected_test_census':cfg['expected_test_census'],'id_algorithm_evidence':row('/workspace/engineering/pr308/action_server/.venv/lib/python3.12/site-packages/_pytest/python.py'),'ids_runtime_limit':'Default installed Pytest ID algorithm source inspected; actual collection/JUnit names must be authenticated after one run. No tests imported/collected here.','pure_source_coverage':'Fresh baseline headroom, no attribution from oldhighOOM; bool/malformed/finite/identity rejection; newevent stickyfailure; <=reserve threshold; identity/max/counterreset/unknown fail. Memoryreader/signals/stop ownership/native calibration NOTPROVED.','launcher_scope':'launch andguard phases only; guard imports V9 identity-only guard not native MAIN; five ownprefixorigin probes10s inside120guard; primary exact120TERM10; ROOT420TERM10 enclosing3x130 nominalmax390+capture.','outcomes':'Rawstdoutstderr andprimaryrc fsynced beforealwayspost; all-outcome original terminal written; process0 only PURE_TEST_PROCESS_PASS_PENDING_ORIGINAL_JUNIT_CENSUS; no launcher17pass fabrication.','release_scope':'Exact rootreleasekeys/typedfields + independentstatus/configSHA/launcherSHA internally; physicalpath/regular600release/400config/currentUID only required externalROOTcontract, NOT intrinsic launcherfeature.','timeouts_limit':'Unexpected outer termination can leave post/terminal missing; missing evidence HOLD. No universal process/reader/reaping claim.','current_source_checks':'Read-only exactHEAD/tree/clean/count1440; fullbody/native1192/prepared30/237aliases+temporal2 checked by existingguard onactualexecution only.','source_review':'No code/test/product imports or execution; stdlibAST/read/hash only.','all_original_HOLD':'d706 source/designHOLD remainshistorical; proposedmemorypolicy NOTADOPTED','mandatory_ROOT_preflight':physicalrow}
proofrow=put('independent-memory17-concrete-static-source-launcher-and-scope-proof.json',proof)
receipt={'schema':1,'status':'INDEPENDENT_MEMORY17_PURE_PREEXECUTION_GO','decision':'GO_CONCRETE_MEMORY17_PURE_CONTROLS_ONLY_WITH_MANDATORY_DISTINCT_ROOT_EXTERNAL_PHYSICAL_PREFLIGHT','source':cfg['source'],'tree':cfg['tree'],'config_sha256':configrow['sha256'],'launcher_sha256':o['launcher']['sha256'],'owner_binding':row(ownerpath),'config_binding':configrow,'launcher_binding':o['launcher'],'proof_binding':proofrow,'mandatory_ROOT_external_preflight':physicalrow,'execution':'NOT_RUN','root_release':'NOT_CREATED','admission':'Only one serialized concrete pure17 process with verified ROOTphysicalpreflight+distinct600release+allinternalguards. Terminal0 still requires original JUnit exactly17uniquePASS/0F/0E/0SKIP and sourceafterguard; not nativeexecution authorization.','remaining_uncertainty':['No current17 control has run; names are statically derived and need actual JUnitconfirmation.','Memoryreader/finitecounter sampler integration, ownedonlystop behavior and coldsolverheadroom calibration remainunqualified.','OriginalV9 killedMicromamba publicationFAIL and stagedmissingdependency remainFAIL; event increase does not identify killingcomponent.'],'documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_reused_delta':o['original_bindings'][-1],'disposition':'REUSE_EXISTING900B8c28fc_MEMORY_VS_MOUNT_SCOPE_LESSON_NO_COSMETIC_CHILD','durable_learning':'Filesystem capacity does not establish sharedcgroupmemoryheadroom; fresh identity/counters and pressure interval differ from specificchildOOM attribution. Purecontrolsuccess wouldnotcalibrate nativeworkload.','evidence':'Exactproposedpurememorysnapshot/state and17sourcepredicates; originalV9privatefailure ownerfeef and indcb888; concretependingJUnitlauncher.','stale_or_ambiguous_guidance_removed':'No mountfreedata implies memoryqualification; purecontrols/source-onlyprep notnativeadmission.','remaining_uncertainty':'PurecontrolsNOTRUN and native memoryprofile NOTADOPTED.'},'upstream_disposition':'none','capture':datetime.datetime.now(datetime.timezone.utc).isoformat()}
receiptrow=put('OWNERFINAL-independent-memory17-concrete-config-launcher-and-ROOT-preflight-PREEXEC-review.json',receipt)
print(json.dumps({'review':receiptrow,'ROOTpreflight':physicalrow,'proof':proofrow}))
