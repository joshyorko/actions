from pathlib import Path
import ast,hashlib,json,os,stat,subprocess,yaml
D=Path('/workspace/engineering/pr305-current40ad-managed-activation-preexecution-proposal');D.chmod(0o700);R=Path('/workspace/engineering/pr305');H='40ad3b14d264d0e6aa7843e7c26b9fa3855fc34b';T='2d58cc8e47a50bc6c09d597a56ed8153aa4f2f34';B='a0d258a16095b95b1bf9000cb1201cddfaff4779';C=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(x):
 q=bind(x['path']);assert all(q[k]==x[k] for k in ('path','bytes','sha256'))
 if 'mode' in x:assert oct(stat.S_IMODE(Path(x['path']).stat().st_mode))==x['mode']
 return q
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def save(n,x):
 p=D/n;assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n');p.chmod(0o600);return bind(p)
owner=Path('/workspace/engineering/pr305-actual309-refresh/OWNERFINAL-current40ad-ordinary-a0d-source-LIGHT-full-and-actual-HOLD.json');assert sha(owner)=='2d2771a4f0d44b0021c0233ae367b3957ebe4639e62396518229853fd5b5ec41' and owner.stat().st_size==90785;o=json.loads(owner.read_text())
ind=Path('/workspace/engineering/pr305-current40ad-independent-light-review/OWNERFINAL-independent-pr305-current40ad-LIGHT-and-full-proposal-review.json');assert sha(ind)=='1906267501e173713226eeab16b1cba6c8ca2d75d7189f51565760b2509fd8d2' and ind.stat().st_size==7388
old=Path('/workspace/engineering/pr305-current40ad-independent-light-review/proposed-current40ad-explicit-two-worker-configured-full-contract.json');assert sha(old)=='9a0dc99eecda428ecc03dddcb6b0db7cf5f66f25358fef5284927670629b1bef' and old.stat().st_size==2455;original=json.loads(old.read_text())
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and not git('status','--porcelain') and git('show','-s','--format=%P',H).decode().split()==['519a0beb7451cb6e4410f0bee18c826fc493086e',B]
assert o['head']==H and o['tree']==T and len(o['all112_distinct_previous_bound_refs_bytes_modes_unchanged'])==112
for row in o['all112_distinct_previous_bound_refs_bytes_modes_unchanged']:check(row)
check(o['complete_source_pre_post_body_modes_exec_exact']);proof=json.loads(Path(o['complete_source_pre_post_body_modes_exec_exact']['path']).read_text());assert len(proof['all1422'])==1422
for row in proof['all1422']:
 p=R/row['path'];body=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();assert len(body)==row['bytes'] and hashlib.sha256(body).hexdigest()==row['sha256'] and hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==row['blob']
 if row['mode']!='120000':assert bool(p.stat().st_mode&0o111)==(row['mode']=='100755')
prepbind=o['prepared_environment']['own30_inputs_configs_and_five_concrete_module_origins_verified'];check(prepbind);prep=json.loads(Path(prepbind['path']).read_text());assert len(prep['inputs_exact_prepared_git_bytes_sha256'])==30 and len(prep['own5actual_prefix_and_source_origin_assertions'])==5
for p,h in prep['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/p)==h
for pkg,row in prep['own5venvs_current_config_and_python'].items():assert sha(R/pkg/'.venv/pyvenv.cfg')==row['config_sha256'] and str((R/pkg/'.venv/bin/python').resolve())==row['python_resolved']
for row in prep['own5actual_prefix_and_source_origin_assertions']:assert Path(row['prefix']).resolve().is_relative_to(R) and Path(row['origin']).is_relative_to(R) and Path(row['origin']).is_file()
check(o['prepared_environment']['managed_gateway']);check(o['prepared_environment']['owned_ignored_RCC']);assert o['prepared_environment']['managed_gateway']['sha256']==o['prepared_environment']['owned_ignored_RCC']['sha256']=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
act=Path('/workspace/actions-cloud/activate.sh');assert sha(act)=='6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a' and act.stat().st_size==987;lines=act.read_text().splitlines();assert all(l.startswith('export ') for l in lines if l.strip())
expected={}
for l in lines:
 name,value=l[7:].split('=',1);expected[name]=value.strip('"').replace('$ACTIONS_CLOUD_ROOT','/workspace/actions-cloud')
assert len(expected)==19 and expected['PATH']=='/workspace/actions-cloud/bin:$PATH' and expected['ROBOCORP_HOME']=='/workspace/actions-cloud/robocorp' and expected['GOMAXPROCS']==expected['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
assert yaml.safe_load((C/'identity.yaml').read_bytes())==yaml.safe_load((R/'developer/setup.yaml').read_bytes())
cache=[bind(C/n) for n in ['identity.yaml','rcc_plan.log','bin/python3.12','bin/poetry']];assert (C/'bin/python').resolve()==C/'bin/python3.12'
preserve=[]
for path,expectedsha in [('/workspace/engineering/root-failed300-default-cache-preservation-actual/OWNERFINAL-root-whole-default-cache-preservation-actual.json','fdbdc5705b6a15863d3a065e1e6821f4411d2297bb2268eb268946cecbb0ac6c'),('/workspace/engineering/root-failed300-default-cache-independent-actual-review/OWNERFINAL-independent-actual-whole-default-cache-preservation-review.json','dd95e137add3eb9b2a7213495a55886ee59cdb7e8996aa0bdb6d96618be7c7f9')]:
 q=bind(path);assert q['sha256']==expectedsha;preserve.append(q)
# Build metadata-only preflight program; it is NOT executed during this preparation.
preflight=Path('/workspace/engineering/pr300-current74-managed-activation-independent-review/proposed-managed-activation-preflight.py').read_text()
start=preflight.index('prepared=');end=preflight.index('configs=',start)
preflight=preflight[:start]+'prepared='+repr(prep['inputs_exact_prepared_git_bytes_sha256'])+'\nfor path,h in prepared.items(): assert hashlib.sha256((R/path).read_bytes()).hexdigest()==h\n'+preflight[end:]
start=preflight.index('configs=');end=preflight.index('statv=',start)
preflight=preflight[:start]+'configs='+repr(prep['own5venvs_current_config_and_python'])+'\nfor package,row in configs.items():\n assert hashlib.sha256((R/package/".venv/pyvenv.cfg").read_bytes()).hexdigest()==row["config_sha256"]\n assert str((R/package/".venv/bin/python").resolve())==row["python_resolved"]\n'+preflight[end:]
preflight=preflight.replace('/workspace/engineering/pr300','/workspace/engineering/pr305').replace('74beef4d220c3a1e8f983cecd42b9bb84ac75e79',H).replace('2238ed312babba9fd5ad89a3a1cc581ca6ad2dcf',T)
extra='''\n# Metadata/read-only source/ref checks; no RCC, Poetry, pytest, imports of application or installers.
owner='''+repr(bind(owner))+'''
pp=Path(owner["path"]);assert pp.stat().st_size==owner["bytes"] and hashlib.sha256(pp.read_bytes()).hexdigest()==owner["sha256"]
owned=json.loads(pp.read_text())
for row in owned["all112_distinct_previous_bound_refs_bytes_modes_unchanged"]:
 p=Path(row["path"]);h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""): h.update(block)
 assert p.stat().st_size==row["bytes"] and h.hexdigest()==row["sha256"]
 if "mode" in row: assert oct(p.stat().st_mode & 0o777)==row["mode"]
sourceproof='''+repr(o['complete_source_pre_post_body_modes_exec_exact'])+'''
spp=Path(sourceproof["path"]);assert hashlib.sha256(spp.read_bytes()).hexdigest()==sourceproof["sha256"]
for row in json.loads(spp.read_text())["all1422"]:
 p=R/row["path"];body=os.readlink(p).encode() if row["mode"]=="120000" else p.read_bytes()
 assert len(body)==row["bytes"] and hashlib.sha256(body).hexdigest()==row["sha256"]
 if row["mode"]!="120000": assert bool(p.stat().st_mode&0o111)==(row["mode"]=="100755")
for key in ["managed_gateway","owned_ignored_RCC"]:
 row=owned["prepared_environment"][key];p=Path(row["path"]);assert hashlib.sha256(p.read_bytes()).hexdigest()==row["sha256"] and oct(p.stat().st_mode&0o777)==row["mode"]
for row in owned_origins:
 assert Path(row["prefix"]).resolve().is_relative_to(R) and Path(row["origin"]).is_relative_to(R) and Path(row["origin"]).is_file()
'''
extra='owned_origins='+repr(prep['own5actual_prefix_and_source_origin_assertions'])+'\n'+extra
preflight=preflight.replace('print("PASS_MANAGED_ACTIVATION_CURRENT_SOURCE_CACHED_TOOLKIT_READONLY_PREFLIGHT")',extra+'\nprint("PASS_CURRENT40AD_MANAGED_ACTIVATION_CACHED_TOOLKIT_AND_SOURCE_METADATA_PREFLIGHT")')
ast.parse(preflight);p=D/'proposed-current40ad-managed-activation-source-metadata-preflight.py';assert not p.exists();p.write_text(preflight);p.chmod(0o600)
code='set -euo pipefail\nsource "$1"\n"$2" "$3"\nshift 3\nexec "$@"\n'
argv=['bash','--noprofile','--norc','-c',code,'current40ad-managed-activation-successor',str(act),str(C/'bin/python'),str(p),*original['argv']]
sourceproof=save('safe-current40ad-metadata-readback-preserved.json',{'head':H,'tree':T,'ordered_parents':o['ordered_parents'],'all1422_current_FS_Git_body_exec_exact':True,'all112_original_ref_bytes_modes_exact':True,'own30_inputs_and5cfg_resolved_python_recorded_origins_exact':True,'primary_managed_and_ignored_RCC_hash':'7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428','activation_ALL19_export_names':list(expected),'activation_only_exports':True,'cached_toolkit_setup_identity_equal_current':True,'history_current_cache_preservation_receipts':preserve,'no_original_historical_cache_baseline_or_future_gate_claim':True})
new=save('PROPOSED-current40ad-managed-activation-one-configured-full-v2.json',{'schema':'actions-current40ad-managed-activation-configured-full-proposal/v2','status':'PROPOSAL_GO__EXECUTION_HOLD_DISTINCT_ROOT_RELEASE_AND_SERIALIZATION_CAPACITY','head':H,'tree':T,'target':B,'cwd':str(R),'activation':bind(act),'activation_ALL19_export_names':list(expected),'activation_expected_nonsecret_values_except_inherited_PATH':{k:v for k,v in expected.items() if k!='PATH'},'PATH_first_entry_required':'/workspace/actions-cloud/bin','cached_toolkit_existing_identity_executable_bindings':cache,'preflight':bind(p),'argv':argv,'original_unactivated_contract_retained':bind(old),'unchanged_full_argv_after_activation_and_metadata_preflight':original['argv'],'worker2_inherited_before_Runtime_n_auto':True,'outer_FULL_TERM_seconds':600,'kill_after_seconds':10,'prepared_source_proof':sourceproof,'historical_capacity_only':preserve,'execution_requirements':['Original300 failedauthorization/log retained and already consumed; current300 successor mustterminal and root mustfreezeitsactualresult before305 fullrelease','Cleanup full/source executions and300/305 cannotoverlap; root ownsserialized heavy release','Fresh currentworkspace capacity>=1200000000B independently admitted immediatelybeforeexecution','New named305authorization mustbindexact this proposal/preflight/argv/activation/source/head/tree and currentnamedtarget, not old9a0d alone','Metadata preflight invokes existing cachedToolkit Python only; no RCCvariables/bootstrap/installers/network orapplication imports; mismatch HOLD','Root immediately rechecks actual ownfiveprefix/moduleorigins via reviewed originalmethod if needed; recordedorigin metadata retention is not a new import execution','One exact configuredRuntimefull attempt after distinctrelease, no auto retry; no old519launcher/sourcefull carry','New exclusive0600 private full log, terminal and pre/post source/ref guards; preserve originals'], 'proposed_new_root_outputs':{'authorization':str(D/'root-one-current40ad-activated-configured-full-authorization.json'),'private_log':str(D/'current40ad-one-activated-configured-full.log'),'terminal':str(D/'current40ad-one-activated-configured-full-terminal.json'),'postconditions':str(D/'current40ad-post-full-source-and-reference-readback.json'),'creation':'All NEW exclusively created byROOT afterseparateauthorization; no files authored/run bythismetadata preparation','terminal_fields':['exactargv/activation/preflighthashes','sourcehead/tree/target','UTCstart/end+monotonicelapsed','actualRCCreturncode','originalprivate logbytes/fullSHA','observedpytestcounts/workers/errors/skips/deselectorUNREPORTED','attemptcount1/no retry'],'post_guard':'Repeat complete1422FS/Git/body/exec,112historicalrefsbyte+modes/own30fivecfg+actualrecordedorigins/RCCpin check; raw18/frozen50/native historical qualification unchanged. FullFAIL remainsFAIL and sourcecountsUNKNOWN if beforepytest.'},'native_scope':'274production+5selected separate,261oldmatches7changes6adds. Old92498/3ecV5native UNQUALIFIEDcurrent;112retainedbindings not upgraded','remaining_HOLD':['Current40adconfiguredfull and independentSOURCEFINAL','FreshcurrentexactCI/currentactual/platform/consumer/browser/provider/private/release','Any cleanup/naturalcompletion absent measuredownpredicates remainsUNKNOWN'],'not_executed':True,'Upstream_disposition':'none'})
patch=Path('/workspace/engineering/pr300-current74-managed-activation-independent-review/canonical-managed-gateway-activation-exact-context-v2.patch');assert sha(patch)=='ee804bb1acd0102a0b28b37b66e55c3bcd1eac4f9bd70885ef5f7c245f67f994';guidepatch=o['documentation_improvement']['Exact_delta'];check(guidepatch)
report={'schema':'actions-independent-current40ad-activation-corrected-metadata-proposal/v1','verdict':'GO_NAMED_CURRENT40AD_ACTIVATED_PREFLIGHT_AND_FULL_PROPOSAL_ONLY__HOLD_ACTUAL_EXECUTION','head':H,'tree':T,'target':B,'original_LIGHT':bind(owner),'original_independent_LIGHT':bind(ind),'original_unactivated_full_proposal':bind(old),'source_metadata_preserved':sourceproof,'new_concrete_preexecution_proposal':new,'primary_RCC_pin_unchanged':'7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428','all19activationexports_and_PATH_required':True,'cached_toolkit_identity_setup_and_existing_Python_Poetry_bindings_verified_readonly':True,'own30_five_config_recorded_origins_retained_no_new_importexecution':True,'capacity_history_scope':'Rootfdbdc+inddd95 authenticate currentdefaultcache preservation/recovery only; no historicalcache baseline orgate authorization. Newworkspace capacity andserialization require rootfresh admission.','Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md and provenance-observability.md; exactacceptedbothparentguideimport reused; exactexisting activation proposal reused forowning integration agent','Exact_accepted_source_guide_import':guidepatch,'Exact_activation_delta':bind(patch),'activation_proposal_import_scope':'Already accepted proposal ee804 reused; not claiming its exactblock currently imported into source40ad or checkpoint; no duplicate cosmetic patch','Durable_learning_captured':'AbsolutemanagedRCC executable needs exactmanagedactivation/home/caches/PATH andworker/Golimits; existing cachedsetup/executables andpreparedsource mustbeadmitted beforeseparatelyreleasedfullcommand.','Evidence':[bind(act),sourceproof,new,bind(owner),bind(ind)]+cache+preserve,'Stale_or_ambiguous_guidance_removed':'No old unactivated9a0d or519launcher as currentactivatedfull/no metadata/capacity recovery as actualgate/no historynativescope upgrade','Remaining_uncertainty':'Current300 actualsuccessor/cleanupterminal, futurecapacity/serialization,current40adfull+SOURCEFINAL/CI/platform/private/release remainHOLD'},'Upstream_disposition':'none','no_tests_source_edits_installer_activation_Rcc_Poetry_invoke_native_provider_download_push_merge_executed':True,'review_constructor':bind(__file__)}
print(json.dumps(save('OWNERFINAL-independent-current40ad-managed-activation-metadata-preexecution-proposal.json',report)))
print(json.dumps(new))
