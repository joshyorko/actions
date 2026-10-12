"""Read-only original LIGHT/source/policy examination; no payload imports/gates."""
import ast,hashlib,json,os,re,stat,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=Path('/workspace/engineering/pr307');ACT=Path('/workspace/engineering/pr307-current2314-light-once-owned');PRE=Path('/workspace/engineering/pr307-currente2-concrete-LIGHT-PREEXECUTION-v2')
SOURCE='2314aea95795fbc1372a6f7b0b7b298b7cf124c3';TREE='2987ed3a23e560fb40e13aadbcd6bd613ead3f25'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def bind(p):
 p=Path(p);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink();raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':sha(raw),'mode':oct(stat.S_IMODE(m.st_mode))}
def check(row):
 now=bind(row['path']);assert all(now[k]==row[k] for k in ('path','bytes','sha256','mode'))
def save(n,j):
 p=BASE/n;assert not p.exists();p.write_text(json.dumps(j,indent=2,sort_keys=True)+'\n');p.chmod(0o400);return bind(p)
rootowner=Path('/workspace/engineering/root-current2314-pr307-LIGHT-original-outer-once/OWNERFINAL-root-one-original-current2314-LIGHT-outer.json');rb=bind(rootowner);assert rb['bytes']==709 and rb['sha256']=='3c65333a1b8b16d5e4eb302c97c0ac5c1db8d4841b3b6c3e9f884727aaad15dc' and rb['mode']=='0o400'
r=json.loads(rootowner.read_bytes());assert r['outer_returncode']==0 and r['source']==SOURCE and r['tree']==TREE
config=PRE/'immutable-one-LIGHT-inputs.json';assert bind(config)['sha256']==r['config_sha256'];cfg=json.loads(config.read_bytes())
launcher=PRE/'launch_one_owned_light.py';assert bind(launcher)['sha256']==r['launcher_sha256']
for row in cfg['bindings']:check(row)
assert len(cfg['bindings'])==10
proof=json.loads(Path(cfg['source_proof']['path']).read_bytes())
assert len(proof['all_git_FS_body_and_exec_mode_exact'])==1442
for row in proof['all_git_FS_body_and_exec_mode_exact']:
 p=ROOT/row['path'];m=p.lstat()
 if row['mode']=='120000':assert stat.S_ISLNK(m.st_mode);raw=os.readlink(p).encode()
 else:assert stat.S_ISREG(m.st_mode);raw=p.read_bytes();assert bool(m.st_mode&0o111)==(row['mode']=='100755')
 assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
for row in proof['prepared30_exact_original307_head']:
 raw=(ROOT/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
assert len(proof['prepared30_exact_original307_head'])==30
for row in proof['five_existing_venvs_config_only']:check(row['pyvenv_config'])
assert len(proof['retained_original_evidence'])==15
for row in proof['retained_original_evidence']:check(row)
for row in cfg['forbidden_generated_outputs']:
 p=Path(row['path'])
 if row['exists']:check(row['binding'])
 else:assert not p.exists() and not p.is_symlink()
for key,args in [('head',['rev-parse','HEAD']),('tree',['rev-parse','HEAD^{tree}'])]:
 assert subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()=={'head':SOURCE,'tree':TREE}[key]
assert not subprocess.check_output(['git','status','--porcelain=v1'],cwd=ROOT)
parents=subprocess.check_output(['git','show','-s','--format=%P','HEAD'],cwd=ROOT,text=True).split();assert parents==['87e412f89b201c697d3e6bd4bd34031cdbd14df3','e2c81adce7858d5a952991ba9a8b7f72e902038a']
pre=json.loads((ACT/'before-guard.json').read_bytes());post=json.loads((ACT/'always-post-guard.json').read_bytes());assert pre==post=={'five_configs':5,'historical_refs':15,'prepared_inputs':30,'source':SOURCE,'status':'PASS','tree':TREE,'typed_FS_rows':1442}
terminal=json.loads((ACT/'original-terminal.json').read_bytes());assert terminal['status']=='PASSED_CURRENT2314_LIGHT_ONLY' and terminal['before_passed'] is True and terminal['post_guard']=='PASS' and terminal['primary_exception_type'] is None
phases={};rawbindings=[]
for name in ('doctor','own-five-origins','toolkit','guard-focus','configured-static','generated-eight-and-Github30','controlled-invoke-command'):
 d=ACT/name;j=json.loads((d/'terminal.json').read_bytes());assert j['returncode']==0
 assert sha((d/'stdout.bin').read_bytes())==j['stdout_sha256'] and sha((d/'stderr.bin').read_bytes())==j['stderr_sha256']
 phases[name]={'returncode':0,'elapsed_seconds':j['elapsed_seconds'],'timeout_seconds':j['timeout_seconds'],'kill_grace_seconds':j['kill_grace_seconds']}
 rawbindings.extend(bind(d/f) for f in ('stdout.bin','stderr.bin','terminal.json'))
xml={};ids={}
for name,count in [('toolkit',179),('guard-focus',41)]:
 p=ACT/name/'junit.xml';cases=list(ET.parse(p).getroot().iter('testcase'));names=[c.get('classname')+'::'+c.get('name') for c in cases];assert len(cases)==count and len(set(names))==count
 assert not any(c.find(k) is not None for c in cases for k in ('failure','error','skipped'))
 xml[name]={'tests':count,'passed':count,'failures':0,'errors':0,'skips':0,'binding':bind(p)};ids[name]=names
# XML case names correspond to current tracked modules, never a cached prior census.
for name in ids['guard-focus']:
 assert name.startswith('tests.build_system_tests.test_oauth2_config_build::')
 focusfunc=name.split('::',1)[1].split('[',1)[0]
 functions={n.name for n in ast.parse((ROOT/'action_server/tests/build_system_tests/test_oauth2_config_build.py').read_bytes()).body if isinstance(n,ast.FunctionDef)}
 assert focusfunc in functions
assert (ACT/'guard-focus/robot-output/log.html').is_file() and not (ACT/'toolkit/robot-output').exists()
originrows=json.loads((ACT/'own-five-origins/all-five.json').read_bytes());assert len(originrows)==5
expected=[('actions','actions'),('actions-http-helper','actions_http'),('devutils','devutils.invoke_utils'),('work-items','actions.work_items'),('action_server','actions.server')]
for row,(package,module) in zip(originrows,expected):
 assert row['module']==module and Path(row['prefix']).resolve()==(ROOT/package/'.venv').resolve()
 assert Path(row['origin']).resolve().is_relative_to((ROOT/package/'src').resolve())
generated=json.loads((ACT/'generated-eight-and-Github30/eight-outputs.json').read_bytes());assert len(generated)==8
for row in generated:
 raw=(ROOT/'.github/workflows'/row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
 assert (ACT/'generated-eight-and-Github30/generated'/row['path']).read_bytes()==raw
paths=json.loads((ACT/'generated-eight-and-Github30/thirty-YAML.json').read_bytes());expectedpaths=sorted(str(p.relative_to(ROOT)) for p in set(ROOT.glob('.github/**/*.yaml'))|set(ROOT.glob('.github/**/*.yml')));assert paths==expectedpaths and len(paths)==30
static=(ACT/'configured-static/stdout.bin').read_text();assert 'Success: no issues found in 354 source files' in static and 'Success: no issues found in 1 source file' in static and '2 files already formatted' in static
stage=ACT/'controlled-invoke';sj=json.loads((stage/'controlled-gateway-receipt.json').read_bytes());assert sj['status']=='PASS_SYNTHETIC_INVOKE_BOUNDARY_ONLY' and sj['no_product_generated_config_write'] is True
assert [x['returncode'] for x in sj['cases']]==[0,1] and len({x['module_sha256'] for x in sj['cases']})==1
for row in sj['unchanged_stage_source']:
 a=(ROOT/'action_server'/row['relative']).read_bytes();b=(stage/'stage/action_server'/row['relative']).read_bytes();assert a==b and sha(a)==row['sha256'] and len(a)==row['bytes']
assert len(sj['four_helper_identities'])==4
for row in sj['four_helper_identities']:assert Path(row['helper_argv0']).parent.resolve()==(ROOT/'action_server/.venv/bin').resolve()
assert Path(sj['yaml_origin']['prefix']).resolve()==(ROOT/'action_server/.venv').resolve() and Path(sj['yaml_origin']['yaml_origin']).resolve().is_relative_to((ROOT/'action_server/.venv').resolve())
for case,rc in [('valid_structural_pair',0),('second_acquisition_failure',1)]:
 assert json.loads((stage/(case+'.terminal.json')).read_bytes())['returncode']==rc
 out=(stage/(case+'.stdout')).read_bytes()+(stage/(case+'.stderr')).read_bytes();assert b'controlled private cause' not in out
 if rc:assert b'(exit 17)' in out
assert not list((stage/'stage/action_server/src/actions/server').glob('.oauth2-config-*.tmp'))
review=Path('/workspace/engineering/pr307-current2314-concrete-LIGHT-independent-review/OWNERFINAL-independent-current2314-concrete-LIGHT-PREEXECUTION-v2-GO.json');assert bind(review)['sha256']=='d2388f27f5f46aea162d5bd41e067058bcadd67af86f625417c979607968344e';assert json.loads(review.read_bytes())['decision']=='GO_CURRENT2314_LIGHT_PREEXECUTION'
release=Path('/workspace/engineering/pr307-currente2-concrete-LIGHT-PREEXECUTION/root-one-LIGHT-release.json');assert bind(release)['sha256']==r['release_sha256'];rel=json.loads(release.read_bytes());assert rel['launcher_sha256']==r['launcher_sha256'] and rel['config_sha256']==r['config_sha256']
activation=json.loads((ACT/'activation-private.json').read_bytes());assert all(activation[k]==v for k,v in cfg['managed_activation_expected'].items());assert activation['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
# Full output inventories are private, not public safe receipts.
actualinventory=[]
for p in sorted(ACT.rglob('*')):
 m=p.lstat();row={'relative':str(p.relative_to(ACT)),'mode':oct(stat.S_IMODE(m.st_mode))}
 if stat.S_ISREG(m.st_mode):row.update({'type':'file','bytes':m.st_size,'sha256':sha(p.read_bytes())})
 elif stat.S_ISDIR(m.st_mode):row['type']='directory'
 elif stat.S_ISLNK(m.st_mode):row.update({'type':'symlink','target':os.readlink(p)})
 else:raise AssertionError('Unexpected LIGHT output type')
 actualinventory.append(row)
proofbinding=save('private-complete-actual-output-source-node-and-binding-proof.json',{'source':SOURCE,'tree':TREE,'parents':parents,'all1442_git_FS_verified':True,'source_proof_binding':bind(Path(cfg['source_proof']['path'])),'ten_cfg_rows_checked':cfg['bindings'],'initial_cfg_and_root_authorized_launcher_rechecked':True,'old15_evidence_rechecked':proof['retained_original_evidence'],'seven_phases':phases,'complete_XML_nodes':ids,'original_raw_phase_bindings':rawbindings,'XML':xml,'actual_output_inventory':actualinventory,'own5_measured_origins':originrows,'generated8_outputs':generated,'GitHub30paths':paths,'controlled_stage_receipt':bind(stage/'controlled-gateway-receipt.json'),'rootrelease':bind(release),'source_preexec_review':bind(review),'rootparent':rb})
policy={'AGENTS_testing_line41':'Run the smallest focused test while iterating, then the affected package\'s full suite, configured lint/type checks, and `git diff --check`. Cross-package changes require every affected package suite.','repository_skill_verification_line65':'Run the smallest focused test while iterating, then the affected package\'s complete suite, configured lint/type checks, and `git diff --check`. For cross-package contracts, run every affected package suite. Report exact commands, results, skipped gates, and remaining uncertainty.','AGENTS_PR_line90':'Pull requests summarize behavior and safety impact, link issues, disclose breaking changes, list exact verification output and skipped gates','interpretation':'Full affected suite remains mandatory verification; these rules do not expressly require localFULLPASS before a normal draft branch push. Root may use a disclosed normal existing-branch source push to obtain fresh current hosted evidence under user-authorized engineering. This is not completion/merge/releaseGO or a full-gate waiver. PreserveFULLNOTRUN and onlyadmit fresh exactsource hosted full results later.','prior_root_no_push_until_newsource_gatesaccepted':'Currentroottask explicitly asks assessment after independentactualLIGHT; root alone decides distinct normalpush. Worker hasno pushauthority.'}
owner={'schema':'OWNERFINAL_INDEPENDENT_ORIGINAL_CURRENT2314_LIGHT_REVIEW','decision':'GO_ACTUAL_CURRENT2314_LIGHT_ONLY_CONDITIONAL_NORMAL_DRAFT_SOURCE_PUSH_FOR_FRESH_CI','source':SOURCE,'tree':TREE,'parents':parents,'root_owner':rb,'proof':proofbinding,'actual':{'outer_returncode':0,'outer_elapsed_seconds':r['elapsed_seconds'],'allseven_phase_returncodes':0,'Toolkit179PASS0skip':True,'guard41PASS0skip':True,'configured_Mypy354_plus_helper1':True,'generated8_and_GitHub30':True,'five_own_origins':True,'full1442_and30inputs_fiveconfigs_old15_before_alwayspost':True,'config_self_18values_PATH_prefix_ignoredoutputs_unchanged':True,'controlled_real_Invoke':{'success':0,'expected_secondfailure':1,'wrapper':0,'unchanged_stage_source':True,'oldmodule_preserved':True,'actual_product_generated_config_written':False,'authority':'SYNTHETIC_STRUCTURAL_ONLY_NOT_APPROVED_OAUTH_CONTENT'}},'push_gate_assessment':policy,'named_refs_once_readback':{'sourcebranch':'fix/runtime-release-changelog-selection-20261010','remote_source_head':'87e412f89b201c697d3e6bd4bd34031cdbd14df3','integration_head':'e2c81adce7858d5a952991ba9a8b7f72e902038a','normal_push_after_rootdecision':'existingref fastforward87e_to2314 only; recheckexpected head immediately before rootpush; no force/admin/newbranch','fresh_hosted_CI_REQUIRED':True},'FULL':'NOT_RUN_ROOTCAPACITY_TMP316547072_BELOW1200000000_FLOOR','not_qualified':['FullcurrentaffectedRuntime suite','Merged integration/release','AuthoritativeOAuth pair/revision/providers/consumerbehavior','Nativecurrent3/5/7276 oroldproducer equivalence','Old307 hosted7acquisition failures remainhistoricalFAIL'], 'method_precision':'Root dispatch400 wasfileMODE0400, notbytecount. Actual owner709B exactROOTannounced3c653; no originalbodydrift/unrecovered400bytebody claimed. Initial readerambiguity preservedasmethodnote.', 'protected_external308_scope':'No source/native/devshm orshared308 output mutations bythislane; ROOTreportsold9namespaces retained, butthis307 launcher doesnotdeclare a9namespace inventory andthisreviewdoesnotupgrade thatROOTassertion toindependentallnamespace proof.', 'documentation_improvement':{'canonical_file':'docs/skills/repository-operations.md','delta':'Exactguard/gateway/authority parentlesson reused; currentactual proves stagedInvoke separation and interface-specific logging, no cosmetic new child','durable_learning':'ActualcontrolledInvoke is structural boundary proof only; fullcurrent gate and OAuthauthorityremainseparate','evidence':proofbinding,'stale_ambiguity_removed':'179/41 realcurrentXML notold69/41/full1173carry; realstage ratherthanproductconfigwrite;400permission vsbytes','remaining_uncertainty':'CurrentFULL/freshCI/OAuthauthoritativecontent/native/release remainHOLD'},'upstream_disposition':'none','reviewer_executed_gates_or_tests_or_imports_or_networkacquisition_or_mutated_source':False}
ob=save('OWNERFINAL-independent-original-current2314-LIGHT-and-normal-draft-push-gate-review.json',owner);print(json.dumps({'owner':ob,'proof':proofbinding}))
