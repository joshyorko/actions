import hashlib,json,re,stat
from pathlib import Path
r=Path('/workspace/engineering/rcc-compatibility-actual-runner-readonly-preparation')

def bind(p):
 p=Path(p);z=p.read_bytes();return {'path':str(p),'bytes':len(z),'sha256':hashlib.sha256(z).hexdigest()}

original=Path('/dev/shm/actions-rcc-compatibility-originals-20261011/OWNERFINAL-three-original-RCC-acquisition-data-qualification.json')
assert bind(original)['sha256']=='0da97bfc63a5e47de1c900e8d37ec55261d8b7ef6f68069a74167afc344c72ad'
for row in json.loads(original.read_bytes())['bindings']:assert bind(row['path'])==row
helper=Path('/workspace/actions-cloud/receipts/pr305-runner/frozen-helpers/verify_dakota_rcc_acceptance.py')
assert bind(helper)['sha256']=='60acf72569c2dfe5748f45ac6c3bf4cc8621e28955a4afa3dbf2f417d7290659'
assert stat.S_IMODE(helper.stat().st_mode)==0o444
for v,expected in [('v1',83),('v2',96),('v3',99)]:
 name=f'service-free-{v}-'+('RED' if v=='v1' else 'GREEN')+'.private.log'
 log=(r/name).read_text();assert int(re.search(r'Ran (\d+) tests',log).group(1))==expected
 if v=='v1':assert log.splitlines()[-1]=='FAILED (failures=3)'
 else:assert log.splitlines()[-1]=='OK'
for v in ['v2','v3']:
 p=r/f'service-free-{v}-GREEN-terminal.json'
 with p.open('x') as f:json.dump({'returncode':0,'actual_count':96 if v=='v2' else 99,'skipped':0,'scope':'SERVICE_FREE_SYNTHETIC_PARSER_ONLY_NO_RCC_OR_PROCESS_PROBE'},f,indent=2);f.write('\n')
 p.chmod(0o600)
guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md')
text=guide.read_text();anchor='gate green; rerun its required checks with new logs.\n'
assert text.count(anchor)==1
addition='''\nA capacity sampler reports maxima and minima only at its observed samples,\nnot a kernel quota or a universal peak. Retain its sample count, threshold\ntrip, inspection failures and measured final cancellation/alive states. A\ncapacity failure stays primary even when owned cleanup succeeds. Signal only\nthe exact recorded command child with a matching PID and creation time; leave\nreaping to its existing exclusive supervisor. Round minimum free-byte\nrequirements upward and reject booleans where integer counters are required.\n'''
import difflib
patch=''.join(difflib.unified_diff(text.splitlines(True),text.replace(anchor,anchor+addition).splitlines(True),fromfile='a/docs/skills/repository-operations.md',tofile='b/docs/skills/repository-operations.md'))
p=r/'canonical-sampled-capacity-and-exclusive-owner-proposed.patch'
with p.open('x') as f:f.write(patch)
p.chmod(0o600)
refs=[bind(p),bind(guide),bind(original),bind(helper),bind('/workspace/actions-cloud/activate.sh'),bind('/workspace/engineering/root-two-exact-approved-test-only-binary-copies.json'),bind('/workspace/engineering/rcc-original-acquisition-independent-review/OWNERFINAL-independent-three-original-RCC-acquisition-data-review.json')]
for p in r.iterdir():
 if p.is_file() and p.name!='freeze_service_free_controls.py':
  p.chmod(0o600)
  row=bind(p)
  if row not in refs:refs.append(row)
refs.append(bind(Path(__file__)))
for row in refs:assert bind(row['path'])==row
owner={'schema':'RCC_RUNNER_SERVICE_FREE_ADMISSION_CONTROLS_ONLY_V3','decision':'SYNTHETIC_PARSER_CONTROLS_PASS_ACTUAL_RUNNER_SOURCE_FIXTURE_AND_EXECUTION_HOLD','original_parser_RED':{'tests':83,'failed':3,'passed':80,'failed_nodes':['bool_predecessor_counter','json_nonfinite','signal_bool_time'],'interpretation':'Private runner-parser construction gaps, not RCC or Runtime defects.'},'named_parser_v2_GREEN':{'tests':96,'passed':96,'skipped':0},'named_parser_v3_GREEN':{'tests':99,'passed':99,'skipped':0,'minimum_cold_free_bytes':3865470567,'new_countercontrols':'Firstcold threshold uses ceil3.6GiB; one byte below rejected. Exact integer counters, workspace floor and bool rejection.'},'actual_controls':['Exact2selector/name/JUnitcounter/outcome','SourceGit vs controlGit vs runnerSHA256 distinct binding','Binary source/version/platform/digest/root-approvedcopy/acquisition provenance','Co-mutated local approval body fails independent root approval digest','Existing lease identity/verification plus terminal outcome','Unique stable matched command child; PIDreuse/booltimes rejected; signal classification only, no OS signal','Exact600/10/645/660/10budget; rejectboolzeroNaNoversized','Sampled maxima scope, inspectionfailure/threshold/workspace/finalcancelalive, unique lastfinal marker','Strict measured Runtime flags/survivors/errors cannot be normalized after outerreap','Primaryfailure plus cleanupsuccess remainsFAIL; both failures retained','Ordered3→5→7276 predecessor identities/counts/statuses strict'], 'argv':{'metadata_preflight':['/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',str(r/'managed_metadata_only_preflight.py')],'controls':['timeout','--signal=TERM','--kill-after=10s','60s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',str(r/'test_runner_contracts_v3.py')],'activation':'Exact987B6478 source before each private pure-control call, all19 fixed export values/PATH and cachedinterpreter checked; no RCC gateway or package install'},'preservation':{'all76_original_acquisition_bindings_after_controls':True,'helper0444_originalbytes_unchanged':True,'no_Rcc_binaries_invoked':True,'no_children_or_native_provider_network_probes':True,'no_product_packages_imported':True,'no_source_app_branch_gate_push_or_registry_mutations':True},'source_and_actual_runner_HOLD':{'head_tree_fixture_full':'NOT_YET_OWNER_ANNOUNCED_DO_NOT_INVENT','final_normalized_receipt_adapters':'Pending exact frozen sourcefixture schemas/raw records; pure views are synthetic and not a substitute for actual raw-field evidence.','actual_supervisor_Popen_observer_and_sampler':'Design only; actual executable runner/observer control integration not yet frozen. These tests only cover pure admission predicates.','actual3_5_6':'NOT_RUN_SEPARATE_ROOT_ONE_EACH_REQUIRED','sampler_scope':'No kernel quota or universal peak claim; future observations may miss intervening overshoot.','historical5dirty':'Unchanged D1 source-equivalence UNKNOWN; functional tests do not resolve it.','no_native_CLI_wheel_pool_offline_cache_private_or_release_upgrade':True},'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; canonical-sampled-capacity-and-exclusive-owner-proposed.patch, plus accepted324d68cd identity lessons reused','Durable_learning_captured':'Sampled resource counters cannot imply universalpeak/kernelquota; minimum byte floors require upward conversion; fixed identity-safe signal ownership leaves exclusive wrapperreaping unchanged. Primary and cleanup statuses remain independent.','Evidence':'Actual pure99controls, original3parser RED gaps and96/99GREEN, helper60acf solewait/selflaunch/budget source, root exact thresholds and activation6478.','Stale_or_ambiguous_guidance_removed':'Avoid sampledpeak-as-quota, bool-as-integer, successfulcleanup-as-primary-success and sampler-owned wrapper reaping.','Remaining_uncertainty':'Actual monitored runner and final source/fixture adapters are not yet frozen or executed; real process/provider/capacity behavior unqualified.'},'Upstream_disposition':'none','bindings':refs}
p=r/'OWNERFINAL-service-free-runner-parser-controls-source-tuple-PENDING.json'
with p.open('x') as f:json.dump(owner,f,indent=2);f.write('\n')
p.chmod(0o600)
print(json.dumps(bind(p)))
