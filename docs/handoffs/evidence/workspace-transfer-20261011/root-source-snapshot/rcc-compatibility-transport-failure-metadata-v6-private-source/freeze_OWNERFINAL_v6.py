import datetime
import hashlib
import json
import stat
import subprocess
from pathlib import Path

OUT=Path('/workspace/engineering/rcc-compatibility-transport-failure-metadata-v6-private-source')
R=Path('/workspace/engineering/rcc-compatibility-actual-runner-readonly-preparation')


def bind(p):
    p=Path(p);b=p.read_bytes()
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(p.stat().st_mode))}


before=json.loads((OUT/'before-v6-complete263-and-original-failure-bindings.json').read_bytes())
for row in [*before['original263'],*before['original_failure']]:
    now=bind(row['path']);assert all(now[k]==row[k] for k in now),row['path']
red=(OUT/'original-v5-exception-path-RED.private.log').read_text()
green=(OUT/'final-v6-integrated-50-servicefree-controls.private.log').read_text()
assert 'Ran 9 tests' in red and 'FAILED (failures=8)' in red
assert 'Ran 50 tests' in green and green.splitlines()[-1]=='OK'
assert json.loads((OUT/'final-v6-integrated-50-servicefree-controls-terminal.json').read_bytes())['returncode']==0
assert 'All checks passed!' in (OUT/'final-v6-scoped-syntax-undefined-name-check.private.log').read_text()
proof=json.loads((OUT/'immutable-postcontrols-original263-and-v6-structural-scope-proof.json').read_bytes())
assert proof['candidate_v6']==bind(R/'actual_transport_v6.py')
assert proof['original263_byte_length_modes_exact'] is True
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd='/workspace/engineering/pr308').decode().strip()=='b614864ba9da55c13662894b6ef3c8515d9fdb25'
assert subprocess.check_output(['git','status','--porcelain'],cwd='/workspace/engineering/pr308')==b''
source_names=['actual_transport_v6.py','test_actual_transport_failure_metadata_v6.py','test_actual_transport_failure_metadata_v6_additional.py','test_actual_transport_v6_inherited_controls.py']
for name in source_names:(R/name).chmod(0o600)
for p in OUT.iterdir():
    if p.is_file():p.chmod(0o600)
refs=[bind(p) for p in sorted(OUT.iterdir()) if p.is_file()]
refs += [bind(R/name) for name in source_names]
for name in ['actual_transport_v5.py','fixture_records_v2.py','owned_monitor_v1.py','runner_contracts_v3.py','FROZEN-control3-current-b614-actual-config-v2.json','OWNERFINAL-current-b614-runnable-three-version-RCC-compatibility-proposal-v2.json']:
    refs.append(bind(R/name))
refs.extend([bind('/workspace/actions-cloud/activate.sh'),bind('/workspace/actions-cloud/receipts/pr305-runner/frozen-helpers/verify_dakota_rcc_acceptance.py')])
owner={'schema':'private-RCC-transport-v6-failure-metadata-source-only-v1',
       'status':'OWNER_PRIVATE_SOURCE_FROZEN_INDEPENDENT_REVIEW_REQUIRED_NO_ACTUAL_OR_CONFIG_RELEASE',
       'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'source':'b614864ba9da55c13662894b6ef3c8515d9fdb25','tree':'6fa4f5c1e9837a0d893868255575b355b3977fae',
       'control':'c10380a4d2ebc6f0aca63eb85c8f84a337da4962','control_tree':'21676c626a933c2d55761ec85ecf26fe0eef26bb',
       'new_transport':bind(R/'actual_transport_v6.py'),'constructor':bind(Path(__file__)),
       'implementation':['Keep original helper cleanup_disposition/command_returncode and available reaped_descendants separately from primary/cleanup status',
                         'Retain original exception message/traceback only through a separate private callback; callback failure is secondary and cannot erase capacity or cleanup failure',
                         'Always assemble previously observed supervisor/pytest PID-create-time pairs before admission; unobserved identity remains null, never sentinel/current-PID inference',
                         'Retain only last existing process-tree observation, capped64 with original count/truncation/sample scope; no additional capture or psutil Process reads',
                         'Pinned helper exposes no final captured census or reader joins; these facts remain null/UNKNOWN, never filled from sampler cancellation or completed wrapper',
                         'Named v6 main requires exact own path/hash/bytes/mode in separately reviewed config before state/process startup; original v5 config/release cannot admit it'],
       'TDD':{'original_v5_tests':9,'original_v5_failed':8,'original_v5_passed':1,'original_v5_errors':0,
              'final_named_v6_tests':50,'final_passed':50,'final_failed':0,'final_skipped':0,
              'groups':{'new_exception_and_original_safe_assembly_controls':9,'private_callback_existing_observe_and_selfbinding_controls':5,'all_unchanged_inherited_v5_controls':36},
              'earlier_private_GREEN9_and_additional3_5':'Historical construction steps only; final current50 with frozen source are authoritative; no actual result',
              'scoped_syntax_undefined_name_Ruff_F821_E9':'PASS_NOT_FULL_APP_LINT',
              'command':['source /workspace/actions-cloud/activate.sh','existing managed holotree bin on PATH','env TRANSPORT_METADATA_UNDER_TEST=actual_transport_v6','timeout --signal=TERM --kill-after=10s 60s /workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python -m unittest test_actual_transport_failure_metadata_v6 test_actual_transport_failure_metadata_v6_additional test_actual_transport_v6_inherited_controls'],
              'synthetic_scope':'Exact pinned exception class AST and isolated original safe-main assembly/observe AST; injected helper controller only; no real helper.main/run/process/native/RCC gateway'},
       'scope_proof':bind(OUT/'immutable-postcontrols-original263-and-v6-structural-scope-proof.json'),
       'retained_failure':{'root1483':next(row for row in before['original_failure'] if row['sha256']=='72cb3d7fb9ff99386f2c9e2a8d43282ec77ac609d1eb813543d23a6596047697'),
                           'actual1696':next(row for row in before['original_failure'] if row['sha256']=='8dc25bb1b99503af386d12d32c0637aa3503617c6f97d66a83f4643969934d4c'),
                           'original_status':'CAPACITY_THRESHOLD_PRIMARY_AND_CLEANUP_FAIL_-15_UNCHANGED','missing_original_final_fields':'NOT_RECOVERED_OR_RETROSPECTIVELY_INVENTED','original_failed_state_members_unchanged':12},
       'original_preservation':{'all263_refs_bytes_sizes_modes':True,'source1421_FS_mode_bytes_clean':True,'native1192':True,'prepared_inputs30':True,'helper60acf_mode0444':True,'old_v5_and_config8c5_and_all_FAILED_state':'UNCHANGED'},
       'unchanged_transport_semantics':'Whole original v5 AST equals normalized v6 after exactly metadata/observer retention/private callback and successor selfbinding additions; same helper, one Popen ownership, 600/10/645/660/10 budgets, source/control/command/selector/retirement/admission assertions',
       'failed_inspector_preserved':'Original scope constructor selected historical config-v1 while expecting actual config-v2 hash; original stop retained, named v2 corrects ONLY path; no source mutation or retrospective PASS',
       'documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta':bind(OUT/'canonical-retain-original-transport-failure-and-observed-ownership-proposed.patch'),
          'durable_learning':'Transport exceptions preserve observed ownership and original helper attrs independently of primary/cleanup admission; sampled bounded captures cannot fill missing final/reader facts; raw details stay private and each successor requires a new content-bound config',
          'evidence':'Genuine old8FAIL1PASS, new50PASS, pinned60acf exception attrs and unchanged supervisor source, original1696 capacity+cleanup failure, full AST projection/new selfbinding negative controls',
          'stale_ambiguity_removed':'Ownership facts no longer disappear on failure; cleanup FAIL never loses primary capacity classification or implies known readers/final survivors',
          'remaining_uncertainty':'Actual v6 execution/config/gateway/fixture cache integration not authorized; original failed fields remain unrecoverable; no RCC3/5/7276, persistent/reload/drain/provider/private/release admission'},
       'root_next_boundary':'Independent v6 source review, separately accepted fixture/source/version baseline and immutable config/gateway retarget, then distinct ROOT one execution release; none granted here',
       'source313_preexecution':'Existing49181f proposal remains frozen; this lane does not execute or edit it',
       'app_source_or_source308_edits':'NONE','new_Popen_signal_wait_reap_or_helper':'NONE','actual_new_RCC_native_gateway_full_download_install_infrastructure':'NONE',
       'upstream_disposition':'none','bindings':refs,'binding_count':len(refs)}
p=OUT/'OWNERFINAL-private-transport-v6-original-exception-and-observed-ownership-source.json'
with p.open('x') as f:json.dump(owner,f,indent=2);f.write('\n')
p.chmod(0o600)
print(json.dumps(bind(p)))
