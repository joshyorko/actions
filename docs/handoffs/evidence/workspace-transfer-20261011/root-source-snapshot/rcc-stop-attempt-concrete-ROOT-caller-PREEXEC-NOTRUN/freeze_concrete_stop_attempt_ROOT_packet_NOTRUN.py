"""Static stdlib metadata freeze only; no gate/control imports or execution."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

B=Path('/workspace/engineering/rcc-stop-attempt-concrete-ROOT-caller-PREEXEC-NOTRUN')
PHASE=Path('/workspace/engineering/rcc-current8d49-memory-stop-attempt-successor-SOURCE-NOTRUN')
GUARD=Path('/workspace/engineering/rcc-defaultbackend35-once2-exact-census-PREEXEC-NOTRUN')

def row(path):
    p=Path(path);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mode=oct(stat.S_IMODE(s.st_mode)))

def put(name,value):
    p=B/name;raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o400)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    return row(p)

phase_config=row(PHASE/'FROZEN-stop-attempt-composition-pure-control-config-NOTRUN.json')
assert phase_config['sha256']=='59f02612d2660b793ead8c5c945af3d648e8427f6f3a30e872f0272113bf63ff'
phase=json.loads(Path(phase_config['path']).read_text())
phase_helper=phase['helper'];assert row(phase_helper['path'])==phase_helper
phase_owner=row(PHASE/'OWNERFINAL-current8d49-memory-stop-attempt-latch-successor-SOURCE-and-pure-phase-preparation-NOTRUN.json')
assert phase_owner['sha256']=='1482d5e23f66e0e7639659deb49b0f533df75c83cc9bfd0dd3fd0d6dcd86fb9d'
po=json.loads(Path(phase_owner['path']).read_text())
phase_contract=row(PHASE/'minimum-current8d49-stop-attempt-pure-ROOT-phase-contract-NOTRUN.json')
pc=json.loads(Path(phase_contract['path']).read_text())
source_go=row('/workspace/engineering/rcc-current8d49-stop-attempt-independent-SOURCE-and-phase-PREEXEC-review/OWNERFINAL-independent-current8d49-stop-attempt-composition-SOURCE-GO-NOTEXECUTED.json')
assert source_go['sha256']=='cd5ca803945f30b806e255066cf353ff2f3342efc5f2411d9aeca2343ab0bae2'
prior_hold=row('/workspace/engineering/rcc-current8d49-stop-attempt-independent-SOURCE-and-phase-PREEXEC-review/OWNERFINAL-independent-stop-attempt-PURE-PREEXEC-HOLD-ROOTcaller-ABSENT.json')
guard_config=row(GUARD/'FROZEN-defaultbackend35-once2-exact-census-config-NOTRUN.json')
assert guard_config['sha256']=='7021f53c12b5392ffe5cf14da7915f25188c68e6d5a9a3b07458b588c4b527fa'
guard_launcher=row(GUARD/'run_root_defaultbackend35_once2_exact_census_NOTRUN.py')
assert guard_launcher['sha256']=='4d52c52e806266a7b399e4d24671bc500b4aa7d98c334192fa16c30ed139f4d9'
guard_old=json.loads(Path(guard_config['path']).read_text())
guard_release=row('/workspace/engineering/root-one-defaultbackend35-once2-exact-census-release.json')
assert guard_release['sha256']=='f9079a6dfb8e234e4976d1a3feb32d88be9f3ff9ba6c32bc3a6d43d5cfecbf02'
guard_review=row('/workspace/engineering/rcc-defaultbackend35-once2-exact-census-independent-PREEXEC-review/OWNERFINAL-independent-defaultbackend35-once2-exact-census-SOURCE-PREEXEC-GO.json')
assert guard_review['sha256']=='b309b76054718d5deecce80b482f012b0ebbf9f37bdb2ccf42673dbac3758b3e'
guard_actual=row('/workspace/engineering/rcc-defaultbackend35-once2-exact-census-independent-ACTUAL-review/OWNERFINAL-independent-original-defaultbackend35-once2-exact-census-ACTUAL-PURE-GO.json')
assert guard_actual['sha256']=='232365377184c5e9534ebf13eb57e6859a2ed33a3c0c58fd66611546089df60f'
implementations={}
for role,name in [('caller_contract','stop_attempt_caller_contract_v1_NOTRUN.py'),('inner_caller','run_stop_attempt_inner_caller_v1_NOTRUN.py'),('external_parent','run_stop_attempt_external_parent_v1_NOTRUN.py')]:
    p=B/name;ast.parse(p.read_text());p.chmod(0o400);implementations[role]=row(p)
cached='/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'
activation_shell='export PATH="/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin:$PATH"; source /workspace/actions-cloud/activate.sh && exec "$@"'
guard_argv=['timeout','--signal=TERM','--kill-after=10s','120s','bash','-c',activation_shell,'stop-attempt-guard-only',cached,guard_launcher['path'],'--phase','guard','--config',guard_config['path'],'--config-sha256',guard_config['sha256'],'--release',guard_release['path'],'--release-sha256',guard_release['sha256']]
auth=dict(schema=1,permitted_phase='guard',rerun35_or_native=False,guard_config_binding=guard_config,guard_launcher_binding=guard_launcher,historical_consumed_release=guard_release,guard_PREEXEC_review=guard_review,guard_ACTUAL_pure_review=guard_actual,exact_argv=guard_argv,dynamic_timeout_only='Inner shared-primary calls may shorten only120s GNUtimeout token, reserving10sKILL+5s fallback; all other guard arguments frozen. External before/post remain120s/135.',role='New ROOT release authorizes only identity guard reuse; old consumed release is historical admission identity, never a second35 launch grant.')
release_template=dict(schema=1,decision='ROOT_RELEASE_ONE_STOP_ATTEMPT_SOURCE_CONTROLS_ONLY',source=phase['source'],tree=phase['tree'],config_sha256=phase_config['sha256'],helper_sha256=phase_helper['sha256'],caller_config_sha256='ROOT_CALLER_CONFIG_SHA256',implementation_bindings=implementations,source_independent=source_go,guard_only_authorization=auth,serialized_no_other_heavy_or_storage_mutations=True,independent_PREEXEC=None)
refs=phase['bindings']+po['all_original_bindings']+po['all_new_bindings']+guard_old['frozen_bindings']+[phase_config,phase_owner,phase_contract,source_go,prior_hold,guard_config,guard_launcher,guard_release,guard_review,guard_actual]
unique={}
for r in refs:
    assert row(r['path'])==r
    if r['path'] in unique:assert unique[r['path']]==r
    unique[r['path']]=r
refs=list(unique.values())
assert not Path(phase['root_once']).exists() and not Path(phase['root_once']).is_symlink() and not Path(phase['root_release_path']).exists() and not Path(phase['root_release_path']).is_symlink()
assert phase['phase_order']==['baseline_original16','RED_memory_preauthorization','RED_disk_preauthorization','restored_successor20']
assert all(cmd.count('120s')==1 for cmd in pc['phase_commands'].values())
cfg=dict(schema=1,status='CONCRETE_STOP_ATTEMPT_ROOT_CALLER_PREPARED_NOTRUN',source=phase['source'],tree=phase['tree'],source_count=1440,root_once=phase['root_once'],root_release_path=phase['root_release_path'],phase_config=phase_config,phase_helper=phase_helper,phase_owner=phase_owner,source_independent=source_go,guard_only_authorization=auth,implementation_bindings=implementations,frozen_bindings=refs,phase_order=phase['phase_order'],phase_commands=pc['phase_commands'],phase_expectations=phase['phases'],ROOT_release_template=release_template,activation=guard_old['activation'],path_prefix2=guard_old['path_prefix2'],forbidden_operator_exports=list(dict.fromkeys(guard_old['forbidden_operator_exports']+['RCC_RELOAD_PRIVATE_MUTANT'])),managed_rcc=guard_old['managed_rcc'],bounds=dict(external_before_TERM=120,external_before_KILL=10,external_before_parent=135,inner_TERM=900,inner_KILL=10,inner_parent=930,inner_shared_primary_seconds=765,inner_reserved_alwayspost_parent=135,nominal_each_guard_and_phase_TERM=120,nominal_KILL=10,nominal_parent=135,uncapped_inner_nominal_fallback_sum=1215,inner_shared_deadline_enforced=True,minimum_new_stage_remaining=15,dynamic_TERM='min120(remaining-15) with10KILL+5fallbackreserve',dynamic_parent='min135(remaining) rechecked immediately beforePopen; no newstage onexhaustion',external_post_TERM=120,external_post_KILL=10,external_post_parent=135,external_fallback_sum=1200,ROOT_outer_TERM=1200,ROOT_KILL=10,ROOT_parent=1230),no_native='Only synthetic unittest phases and accepted complete readonly guard; no35reexecution/realcgroup/signals/RCC main/versions/provider/service/profile adoption.')
config=put('FROZEN-stop-attempt-concrete-ROOT-config-NOTRUN.json',cfg)
compatible=dict(schema=1,status='INDEPENDENT_STOP_ATTEMPT_COMPOSITION_PURE_PREEXECUTION_GO',source=phase['source'],tree=phase['tree'],config_sha256=phase_config['sha256'],helper_sha256=phase_helper['sha256'],caller_config_sha256=config['sha256'],external_parent_sha256=implementations['external_parent']['sha256'],inner_caller_sha256=implementations['inner_caller']['sha256'],caller_contract_sha256=implementations['caller_contract']['sha256'],source_independent_sha256=source_go['sha256'],guard_only_authorization=auth)
grant=dict(release_template);grant['caller_config_sha256']=config['sha256']
rootargv=['timeout','--signal=TERM','--kill-after=10s','1200s','bash','-c',activation_shell,'stop-attempt-root-once',cached,implementations['external_parent']['path'],'--caller-config-sha256',config['sha256'],'--release',phase['root_release_path'],'--release-sha256','ROOT_REAL_DISTINCT_RELEASE_SHA256']
contract=put('ROOT-distinct-stop-attempt-concrete-caller-release-and-argv-contract-NOTRUN.json',dict(schema=1,status='TEMPLATE_NO_EXECUTION_RELEASE',config_binding=config,implementation_bindings=implementations,ROOT_release_path=phase['root_release_path'],ROOT_release_template=grant,compatible_independent_PREEXEC_required_fields=compatible,ROOT_exact_argv=rootargv,ROOT_parent=1230,bounds=cfg['bounds'],ROOT_mandatory_preflight=['Reject inheritedpytest/optimize/operator overrides BEFOREmanagedactivation; config/3code0400 +ROOTrelease0600 regularnonsymlinkUIDGID1000/exacthash; no chmod/repair.','Current1440/source/native1192/prepared30/own5 and alloldrows preserved through fixedacceptedguard-only; newtypedROOTgrant explicitlypermits onlyguard phase, never old35 launch.','FreshABSENT700 rootonce1 and allphaseoutputparents/census; no otherheavy/storage/devshm/source mutations.','Actual4sourcephases exactmachinecensus: baseline16PASS, memoryknown1REDAssertionError(frame208), diskknown1REDAssertionError(frame222), restored20PASS. No advance afterwrongcount/frame/error/skip/timeout.','Existinghelper/config untouched; originalSOURCEHOLD/d9/nativeV8/V9FAIL/default35original34P1F/PREEXCHOLD remain.','Externalbefore135/inner930/externalalwayspost135 preserveprimary/post/retention separately; rootouter1200TERM10/parent1230. Inner primarydeadline765 reserves135post, honestuncapped1215 not guaranteed completion.'],adoption='Independent concrete caller/config review +distinctROOT600 release required before any import/control/gate; metadata template alone authorizesnothing.'))
source=Path('/workspace/engineering/pr308');git=lambda *a:subprocess.check_output(['git','-C',str(source),*a]).decode().strip()
assert git('rev-parse','HEAD')==cfg['source'] and git('rev-parse','HEAD^{tree}')==cfg['tree'] and not git('status','--porcelain','--untracked-files=no')
oldsource=json.loads(Path(guard_old['source_guard_config']['path']).read_text())
assert oldsource['source_root']==str(source) and len(oldsource['prepared_inputs'])==30 and len(oldsource['concrete_own_origins'])==5
assert not any('/pr307/' in r['path'] for r in guard_old['frozen_bindings']+oldsource['bindings'])
for name,digest in oldsource['prepared_inputs'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
pin=Path(cfg['managed_rcc']['path']);s=pin.lstat();assert stat.S_ISREG(s.st_mode) and not pin.is_symlink() and stat.S_IMODE(s.st_mode)==0o700 and s.st_uid==s.st_gid==1000 and row(pin)['sha256']==cfg['managed_rcc']['sha256']
proof=put('static-exact-concrete-caller-command-deadline-and-input-closure-NOTRUN.json',dict(schema=1,status='STDLIB_DATA_AST_ONLY_NO_IMPORT_TEST_EXECUTION',source=cfg['source'],tree=cfg['tree'],source_clean=True,source_count=1440,all_original_binding_count=len(refs),prepared30_current_pr308_exact=True,unrelated307_live_rows=0,managed_rcc700_data_only=True,implementation_bindings=implementations,original_phase_config_and_helper_unchanged=[phase_config,phase_helper],guard_argv_fixed_guard_only=guard_argv,fresh_root_and_release_absent=True,source_go=source_go,prior_concrete_HOLD=prior_hold,config_binding=config,release_contract=contract,deadline_math=cfg['bounds'],scope='Four synthetic controlphases only; primitivephasehelper unchanged, native memory configuration/profile untouched. Sourcecontrol success needs original actualmachinecensus +independent review.'))
local=[row(p) for p in sorted(B.iterdir()) if p.is_file()]
owner=put('OWNERFINAL-stop-attempt-concrete-inner-external-parent-PREEXEC-NOTRUN.json',dict(schema=1,status='CONCRETE_STOP_ATTEMPT_INNER_EXTERNAL_ROOT_PREEXEC_PREPARED_NOTRUN',source=cfg['source'],tree=cfg['tree'],source_count=1440,source_clean=True,config_binding=config,implementation_bindings=implementations,root_contract=contract,static_proof=proof,source_independent=source_go,original_phase_owner=phase_owner,guard_ACTUAL_pure=guard_actual,all_local_bindings=local,all_original_bindings=refs,originals='ALL_UNCHANGED; phasehelper59f/db65/code20 and old35f907/b309/2323 remain exact. No source/productbranch adoption.',actual_tests_imports_cgroup_signals_native='NOT_RUN',outputs_release='ABSENT_NOT_CREATED',deadline_scope=cfg['bounds'],documentation_improvement=dict(canonical_file='docs/skills/repository-operations.md',exact_reuse=[po['documentation']['exact_delta'],*po['documentation']['reused8c28d68366']],durable_learning='Controlorchestration must implementbefore/alwayspost and actual phasecensus, not describe it. Reused consumed controlreceipt grants no newtest execution; ROOT separately grants exactguard-only role. Sharedprimarydeadline reservesinnerpost; hardinnercap plusseparateexternalpost retains failures.',evidence=[proof,contract],stale_ambiguity='Olduncapped810 assumption replaced by1215 nominal with enforced765primary/135post; no allphases-completion guarantee underworstcase.',remaining_uncertainty='All16baseline/2RED/20GREEN phases unexecuted; exactnative/headroom/calibration/profile and newer compatibility unqualified.'),upstream_disposition='none',writer_B='RELEASED_AFTER_FREEZE',captured=datetime.datetime.now(datetime.timezone.utc).isoformat()))
for r in refs+local:assert row(r['path'])==r
print(json.dumps(owner))
