import ast
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

R=Path('/workspace/engineering/pr300')
O=Path('/workspace/engineering/pr300-issue86-next-assembled-transport-proposal')
def sha(body): return hashlib.sha256(body).hexdigest()
def ref(p):
    p=Path(p);body=p.read_bytes();return {'path':str(p),'bytes':len(body),'sha256':sha(body)}
def git(*a): return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a])
def frozen(name, value):
    p=O/name;assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n');p.chmod(0o444);return ref(p)
head='7840057a8b055576d11d339d8c0fbb738927a491';tree='10e09d88027ca4fea512ff06c57efaab95755ffb'
assert git('rev-parse','HEAD').decode().strip()==head and git('rev-parse','HEAD^{tree}').decode().strip()==tree
assert git('status','--porcelain')==b''
checkpoint=ref('/workspace/engineering/pr300-actual299-refresh/immutable-actual299-source-checkpoint.json')
assert checkpoint['bytes']==72050 and checkpoint['sha256']=='b16ef794377b8a51a66444efa697401bc41793842ac6b7bf2986085501e967ee'
issue=ref(O/'issue86-original-current-read.private.json');issue_data=json.loads(Path(issue['path']).read_bytes())
assert issue_data['number']==86 and issue_data['state']=='open'
historical=ref('/workspace/engineering/campaign-checkpoint/docs/program/evidence/current-open-pr-audit-20261010T1753Z/pr300-loopback-review.json')
assert historical['sha256']=='7562e2aaf7bd357a6d208faf629b53b7a0d25f51cb46ab74bfe1fa7d748a95d5'
old=json.loads(Path(historical['path']).read_bytes())
source_paths=[
 'action_server/src/actions/server/run_outputs/transport.py',
 'action_server/src/actions/server/run_outputs/service.py',
 'action_server/src/actions/server/run_outputs/filesystem.py',
 'action_server/src/actions/server/run_outputs/types.py',
 'action_server/src/actions/server/run_outputs/models.py',
 'action_server/src/actions/server/_server.py',
 'action_server/src/actions/server/_models.py',
 'action_server/src/actions/server/_database.py',
 'action_server/src/actions/server/_browser_session.py',
 'action_server/tests/action_server_tests/run_outputs/test_transport.py',
 'action_server/tests/action_server_tests/run_outputs/test_service.py',
 'action_server/tests/action_server_tests/fixtures.py',
 'action_server/tests/conftest.py','action_server/pyproject.toml',
 'action_server/poetry.lock','developer/toolkit.py',
 'docs/skills/provenance-observability.md',
]
bindings=[]
for name in source_paths:
    body=git('show',head+':'+name);row=ref(R/name);assert row['sha256']==sha(body)
    row['repository_path']=name;row['git_blob']=git('rev-parse',head+':'+name).decode().strip();bindings.append(row)
entries=git('ls-tree','-r','-z',head);typed=[]
for entry in entries.split(b'\0'):
    if not entry:continue
    metadata,path=entry.split(b'\t',1);mode,kind,blob=metadata.decode().split();name=path.decode()
    assert kind=='blob';body=(R/name).read_bytes();assert body==git('cat-file','blob',blob)
    assert bool((R/name).stat().st_mode&0o111)==(mode=='100755')
    typed.append({'path':name,'mode':mode,'blob':blob,'bytes':len(body),'sha256':sha(body)})
assert len(typed)==1421
source_proof=frozen('exact784-source-preservation-and-selected-contract-bindings.json',{'head':head,'tree':tree,'clean':True,'typed_leaf_count':len(typed),'typed_entry_sha256':sha(json.dumps(typed,sort_keys=True,separators=(',',':')).encode()),'selected_source_bindings':bindings,'historical_loopback_module_parity':{name:git('rev-parse',head+':'+name).decode().strip()==blob for name,blob in old['source']['module_blobs'].items()},'historical_raw_probe_and_log_available_here':{'probe':Path('/dev/shm/pr300-loopback-probe/probe.py').exists(),'log':Path('/dev/shm/pr300-loopback-probe/pytest.log').exists()},'historical_receipt_reverified_bytes_only_not_current_actual_acceptance':True})
module='tests/action_server_tests/run_outputs/test_transport.py'
names=[
 'test_actual_runtime_authorized_handle_and_response_policy',
 'test_installation_auth_never_creates_actor',
 'test_outer_wrong_key_blocks_valid_actor_credential',
 'test_ungranted_actor_denied_before_provider',
 'test_revoked_grant_denied_before_provider',
 'test_cross_workspace_unknown_and_malformed_fail_before_provider',
 'test_range_and_head_explicitly_unsupported',
 'test_missing_object_does_not_return_path_or_claim_success',
]
functions={node.name:node for node in ast.parse((R/'action_server'/module).read_bytes()).body if isinstance(node,ast.FunctionDef)}
assert set(names)<=functions.keys()
selected=[module+'::'+name for name in names]
guide='docs/skills/provenance-observability.md';before=(R/guide).read_text()
anchor='Production identity\nprovider configuration and actual Canvas producer/consumer execution still need\nseparate integration; a retrievable private-service output does not authorize\nchanging a template\'s `artifact: null` without its own end-to-end proof.\n'
assert before.count(anchor)==1
lesson='\nFor assembled output-transport denials, count provider-open attempts before\nentering the reader context; a list of successfully opened readers alone cannot\nprove that storage was never touched. Take complete logical database and owned\nfilesystem snapshots after legitimate publication or grant changes, then compare\nthem across each request. Compare SQL rows rather than physical SQLite bytes:\nthe resolver takes idempotent writer locks even for authorized reads. HEAD 405\nand Range 416 prove rejection, not method support or persisted-grant resolution.\n'
after=before.replace(anchor,anchor+lesson)
patch=O/'canonical-assembled-output-transport-denial-measurement-proposed.patch';assert not patch.exists()
patch.write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+guide,tofile='b/'+guide)));patch.chmod(0o444)
proposal={
 'schema':'issue86-current784-next-assembled-transport-proposal/v1',
 'status':'READONLY_CONCRETE_SOURCE_AND_ACCEPTANCE_PROPOSAL_ONLY_NOT_EXECUTION_OR_ISSUE_CLOSURE',
 'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source':{'worktree':str(R),'existing_branch':'feat/run-output-transport-20261010','head':head,'tree':tree,'actual_299_base':'6181b044c75de35386f1ae30e71725398b6a7feb','immutable_source_checkpoint':checkpoint,'independent_source_preservation':source_proof},
 'live_issue':{'number':86,'title':issue_data['title'],'state':'open','updated_at':issue_data['updated_at'],'original_API_single_read_private':issue,'scope':'Replica-safe output lifecycle/authorization and broad13 acceptance invariants remain open; this proposal only measures current optional assembled GET route, not all86 or parent83 authority policy.'},
 'retained_prior_actual':{'receipt':historical,'source':old['source'],'original_tcp_execution':'Two tests reported PASS at3cad, real SQLite/Linux provider, real Runtime/uvicorn loopback HTTP/disconnect with test-owned Actor callback. Receipt bytes retained; original named probe/log absent on this host. Not current784 actual or production identity proof.','separate_current_source_evidence':'Current784 unchanged transport tests plus1242/13 full source receipt already accepted; no new actual execution by this lane.'},
 'smallest_remaining_gap':{'accepted_implementation_reused':'Existing real start_server callback-stopped app, existing store fixture/database/provider and trusted credential callback. No production transport/auth/service/provider implementation changes proposed.',
    'precise_missing_contract':'Selected route denials currently assert status/provider successful opens, not complete logical SQL/owned filesystem equality; open list records only readers yielded successfully, not failed open attempts. Missing-key exact status is currently403-or404 aggregate. Missing/wrong-key HEAD/Range outer gate rows absent.',
    'features_not_added':'HEAD remains405 and Range remains416. No active-stream revocation, ETag, LastModified, range implementation, public identity protocol, Canvas artifact output, shared/static provider support or native reconstruction.'},
 'bounded_source_plan_requires_root_writerA_authorization':{
    'allowed_paths':[module,guide],
    'fixture_reuse':'Extend existing runtime fixture only: increment a private provider-open attempt counter before original_open; retain actual original provider/reader behavior. Do not substitute successful app/handler/service responses.',
    'state_snapshot':'After legitimate store publish/grant/revoke/wrongActor/wrongWorkspace setup and before each HTTP request, enumerate ALL SQLite schema/table logical rows through a separate read-only connection; preserve all normalized Run/RunPin/RunAttempt/RunOutput/Workspace/Grant/Counter and other existing tables, not a handpicked model subset. Compare exact sorted row content and schema. Compare typed bindings/modes/symlinks/file hashes for owned fixture datadir/provider tree. Explicitly exclude only runs.db and known SQLite journal/WAL/shm physical payloads because SQL snapshot is their authority, retain their name/type containment. No observed mutation masked; fail closed above bounded fixture1000 rows/16MiB/2048 filesystem entries.',
    'per_request_assertions':'Complete before/after logical state equality for valid GET/read and every denial/failure, no new namespace/artifact binding, exact status/body privacy, authentication/open attempt/success counts. Count actual requests separately from pytest case count.',
    'minimal_changes':'Strengthen existing eight selected tests; parameterize existing outer wrong-key test with missing and wrong installation key while preserving valid test-owned Actor credential. Add one four-case unsupported-method outer-auth test (HEAD and GET+Range times missing/wrong key). Keep existing real missing-object503 as provider-open failure; take its snapshot after intentional deletion and assert open attempt1/success0, unchanged Run/output/grant rows and no disclosed path.',
    'baseline_and_control_requirements':'Actual authorized GET baseline must return exact measured result bytes15 and required headers, one opened-and-closed real reader. Denial-only sentinel around provider-open may be used solely to fail unexpected access; no mocked positive result. A snapshot sensitivity control must detect an owned SQL row mutation and owned file mutation, restoring only its own synthetic state; no production byte mutation or broad bypass.',
    'stop_condition':'Any genuine current source/fixture failure freezes original state/log and stops dependent work for root review; no masks/skips/status substitution/deadline widening or production patch in this proposal.',
    'current_selected_tests':selected,
    'future_added_selector':module+'::test_outer_key_rejection_precedes_unsupported_methods',
    'expected_after_source_collection':{'cases':19,'HTTP_requests':20,'skips':0,'errors':0,'not_yet_collected':'Current selected source has14cases/15requests; five new cases add missing-key GET and four unsupported-method key denials. Verify exact immutable collection after source checkpoint; these are planned counts, not a pass.'}},
 'expected_semantic_cells':[
    {'requests':2,'case':'GET missing or wrong installation-key +valid trusted Actor credential','status':403,'actor_auth_calls':0,'provider_open_attempts':0},
    {'requests':2,'case':'GET valid installation-key but no trusted Actor credential or only forged Actor UUID','status':404,'provider_open_attempts':0},
    {'requests':1,'case':'GET wholly absent installation-key/credential existing fixture row','status':403,'actor_auth_calls':0,'provider_open_attempts':0},
    {'requests':2,'case':'GET valid installation+Actor but ungranted actor/revoked grant','status':404,'provider_open_attempts':0},
    {'requests':5,'case':'GET wrongWorkspace/unknown/malformed/unicode/newline handle','status':404,'provider_open_attempts':0,'headers':'No content-disposition'},
    {'requests':1,'case':'GET authorized current grant','status':200,'bytes':'measured result','provider_open_attempts':1,'successful_reader_opens':1,'reader_closed':True},
    {'requests':2,'case':'valid-key HEAD and valid-key GET Range','status_by_method':{'HEAD':405,'GET_Range':416},'provider_open_attempts':0,'limit':'HEAD never calls route Actor auth; Range returns before service grant resolution. Neither proves grant resolution for unsupported methods.'},
    {'requests':4,'case':'missing/wrong installation-key HEAD or GET Range','status':403,'actor_auth_calls':0,'provider_open_attempts':0},
    {'requests':1,'case':'valid-key Actor+grant GET missing provider object','status':503,'provider_open_attempts':1,'successful_reader_opens':0,'body':'Output storage unavailable','privacy':'No provider/root path/exception disclosure','logical_Run_output_state':'Unchanged; no false success mutation'}
 ],
 'future_frozen_runner_after_source_review':{
    'readiness':'NOT_YET_AUTHORED_OR_AUTHORIZED; freeze source first, independently review source+selected collection, then create hash-pinned external runner/proposal before distinct root ONE authorization.',
    'gateway_cwd':str(R),'activation':'source /workspace/actions-cloud/activate.sh',
    'consumer_command_cwd':str(R/'action_server'),
    'planned_pytest_argv':['python','-m','pytest','-n','0','-p','no:cacheprovider','-p','no:robocorp_log_pytest','-m','not integration_test','--junitxml=OWNED_FRESH/junit.xml','--basetemp=OWNED_FRESH/pytest-temp',*selected,module+'::test_outer_key_rejection_precedes_unsupported_methods','-q'],
    'exact_gateway_shape':['timeout','--signal=TERM','--kill-after=10s','240s','/workspace/actions-cloud/bin/rcc','task','script','-r','developer/toolkit.yaml','--','python','-c','import toolkit; toolkit.poetry("action_server", "run", "python", "FUTURE_IMMUTABLE_REVIEWED_RUNNER")'],
    'bounds':{'serial_selected_pytest_seconds':180,'owned_process_cleanup_seconds':20,'outer_gateway_seconds':240,'TERM_KILL_grace_seconds':10},
    'environment':'Inherit activated prepared gateway/own package Poetry env; PYTHONDONTWRITEBYTECODE=1; no PYTHONPATH checkout override, no package installs, no alternate RCC/download fallback. Synthetic installation/Actor secrets are test-owned constants in private test process; no real credentials or pending-human principal policy.',
    'fixture_local_RCC_disclosure':'Existing autouse disable_feedback fixture executes pinned existing RCC configure identity --do-not-track --config once in owned session temp. No cache serve/provider/env execution. Preserve this original fixture behavior and measure owned callback argv/result/cleanup if runner admission needs it; no no-RCC claim or bypass.',
    'capacity':'Before root ONE authorization recheck >=1.2GB available and serialize installer/broad source/actual slots. No new Bootstrap if all30 own prepared inputs/five concrete origins and ignored7e588 pinned RCC fixture asset still match; else stop for root preparation authority.',
    'owned_cleanup':'Use existing reviewed identity-owned supervisor only after hash/argv review; no new ownership module or helper byte edits. Capture parent/worker identities and raw stdout/stderr first; whole pytest180 deadline, existing helper bounded reap20, gateway240+10. Verify TestClient contexts close, original store/create_db/provider context exits, opened reader closed and FD delta0; no Uvicorn socket startup/pool/action/native/browser/provider service. Keep receipt/private temp files and allowlist paths; remove only exact owned temp roots after guard; no system-wide cleanup.',
    'receipt_admission':'Exactly19 matching JUnit cases0skip/error and20 recorded semantic HTTP requests, every expected status/privacy/counter/state assertion true; raw private stdout/stderr/JUnit and bounded cleanup. Original full1242 source gate is predecessor source evidence, not these future strengthened semantics. Source successor requires normal configured tests/static/gen/full before push.',
    'source_before_after':'Bind all current1421 typed leaves and all future authorized successor leaves before/after; keep784 predecessor distinct from source/test successor and from historical3cad socket proof.'},
 'documentation_improvement':{'Canonical_file_changed_or_proposed':guide,'Exact_delta':ref(patch),'Added_lines':8,'Durable_learning':'Count provider-open attempts separately from successful readers; complete logical SQL and owned-filesystem snapshots belong after legitimate setup and around each request; unsupported methods do not imply grant resolution or supported HEAD/Range.',
    'Evidence':'Current runtime.observe_open appends only after original_open context yields; service.resolve uses idempotent Workspace/Counter writer locks; transport returns416 before resolve and routes GET-only; actual preserved loopback evidence remains separately source3cad. Existing canonical trust boundary retained.',
    'Stale_or_ambiguous_guidance_removed':'No shipped guidance removed. Proposal corrects acceptance inference that not runtime.opened proves no attempted storage access or that405/416 qualify range/head support.',
    'Remaining_uncertainty':'Planned snapshot assertions/source change/collection/actual gate unexecuted; current socket proof, production identity, shared provider/replica/multiadapter/native/platform/private/full86 remain unqualified.'},
 'remaining_HOLD':['Full issue86/83/84/129 and13 broad acceptance invariants','HEAD/Range feature support, public/deployed identity, active-stream revocation','Replica-safe shared/object backend, PostgreSQL, Windows/Linux provider parity, multi-adapter publication/GC/quotas','Current socket/TCP/native/Canvas/browser/installed-wheel and private backend/Workspace/ChatGPT/release proofs','Current hosted CI/policy admission is separately assigned to acceptance_review; no sampling or old source CI carry here'],
 'not_performed':['Tests/collection/control/gateway/installer/consumer or service execution','Source/ref/index edits or push/merge','External service provisioning/native/provider/browser/privateRCC reconstruction','Issue closures/publication/upstream mutation','CI polling/log or ZIP acquisition'],
 'upstream_disposition':'none'}
assert sum(row['requests'] for row in proposal['expected_semantic_cells'])==20
result=frozen('OWNERFINAL-current784-issue86-bounded-assembled-transport-next-proposal.json',proposal)
assert git('status','--porcelain')==b''
print(json.dumps(result))
