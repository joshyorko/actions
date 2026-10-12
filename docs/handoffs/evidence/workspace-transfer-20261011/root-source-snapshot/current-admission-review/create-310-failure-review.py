import hashlib
import json
import pathlib
import re
import subprocess

out = pathlib.Path('/workspace/engineering/current-admission-review')
repo = pathlib.Path('/workspace/engineering/pr310')
head = '4b2df94d77b1145a9ed586fb924eeb88c478d01c'
tested = '9b0928c477771ac1623401f5c6d28cb03edb2e03'
tree = 'f035fd321afe1a5821a249fa7ccd3aea95ee703d'
target = '1c7585fe8bb3cb9476c3997570bd3f04466f2bbc'
base = 'ba85aac7324ea4463bfba8c5f8586e27706dc2fe'
def git(*args):
    return subprocess.check_output(['git', '-C', str(repo), *args])
def bind(p):
    p = pathlib.Path(p)
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
def leaves(ref):
    entries = {}
    if ref == tested:
        identity = json.loads((out / '310-tested-merge-authenticated-identity.json').read_text())
        assert identity['sha'] == tested and identity['tree'] == tree
        ref = tree
    for row in git('ls-tree', '-r', ref).decode().splitlines():
        value, path = row.split('\t', 1)
        entries[path] = value
    return entries
source = json.loads((pathlib.Path('/workspace/actions-cloud/receipts/pr310-fbde-refresh/local-refresh-receipt.json')).read_text())
inputs = json.loads((pathlib.Path('/workspace/actions-cloud/receipts/pr310-fbde-refresh/current-producer-input-inventory.json')).read_text())
selected = source['source_union']['selected_test_paths']
refs = {ref: leaves(ref) for ref in (head, tested, base, target)}
assert len(inputs) == 268 and len(selected) == 5
assert all(refs[head][p] == v == refs[base][p] == refs[tested][p] == refs[target][p] for p, v in inputs.items())
assert all(refs[head][p] == refs[base][p] == refs[tested][p] == refs[target][p] for p in selected)
primary_paths = [
    'action_server/src/actions/server/_selftest.py',
    'action_server/src/actions/server/_rcc.py',
    'action_server/src/actions/server/_robo_utils/process.py',
    *selected[:2],
]
assert all(refs[head][p] == refs[base][p] == refs[target][p] for p in primary_paths)
log = out / 'original-job-logs/310_runtime_windows_failure.log'
text = log.read_bytes().decode()
progress = [(int(n), float(s)) for n, s in re.findall(r'Progress:\s*(\d+)/15\s+v18\.19\.3\s+([0-9.]+)s', text)]
assert len(progress) == 48
nodes = re.findall(r'FAILED (action_server_tests[^\r\n]+?) - TimeoutError', text)
assert len(nodes) == 3
callers = [89.52, 88.34, 87.45]
timings = []
for i, node in enumerate(nodes):
    marks = progress[i*16:(i+1)*16]
    assert [n for n, s in marks] == list(range(16))
    total = round(sum(s for n, s in marks), 3)
    timings.append({'node': node, 'intervals_00_through_15_seconds': [s for n, s in marks], 'interval_sum_seconds': total, 'caller_holotree_duration_seconds': callers[i], 'caller_minus_interval_sum_seconds': round(callers[i]-total, 3), 'phase': 'INITIAL_FIRST_READINESS_BEFORE_SEMANTIC_ASSERTIONS'})
notes = {phrase: text.count(phrase) for phrase in ['Action Server startup cleanup did not fully complete', 'Action Server startup cleanup raised while handling']}
assert not any(notes.values())
metadata_path = out / '310-terminal-authenticated-safe-metadata.json'
metadata = json.loads(metadata_path.read_text())
assert len(metadata['checks']) == 23
assert metadata['job']['conclusion'] == 'failure'
assert [s['name'] for s in metadata['job']['steps'] if s['conclusion'] == 'failure'] == ['Test (integration)']
rcc = json.loads(pathlib.Path('/workspace/engineering/pr299-windows-independent-diagnosis.json').read_text())['immutable_rcc_source']
for record in rcc.values():
    assert bind(record['local_path'])['sha256'] == record['sha256']
paragraph = '''For a native first-readiness timeout, bind the failed Runtime job separately
from passing selected native UI jobs. A timeout in `process.start()` precedes
watched reload or catalog collision assertions and does not establish a failure
of those semantics. RCC v18.19.3 Progress values measure the interval since the
previous mark; retain the complete sequence and compare its sum with the caller's
duration. The value printed beside the final holotree message is not the total,
and the interval printed when UV starts includes the preceding micromamba and
layer setup work. A completed environment close to the startup deadline does not
measure the remaining ready-port work or prove a cache, provider or forwarding
cause. Absence of a startup-cleanup exception note is not an explicit wrapper,
reader or descendant census. Preserve unavailable cleanup fields, original failed
tuples and unchanged readiness/cleanup deadlines; a passing different tuple or
matching producer inputs does not explain the failure. A subsequent ordinary
target refresh can import reviewed observation hooks without claiming a production
fix, but requires its own complete union review and fresh gates.
'''
guide = git('show', head+':docs/skills/repository-operations.md').decode()
anchor = 'treating a timeout as an RCC or Runtime failure.\n'
assert guide.count(anchor) == 1
proposed = guide.replace(anchor, anchor+'\n'+paragraph)
import difflib
patch = ''.join(difflib.unified_diff(guide.splitlines(True), proposed.splitlines(True), fromfile='a/docs/skills/repository-operations.md', tofile='b/docs/skills/repository-operations.md'))
patch_path = out / '310-initial-readiness-canonical-proposed.patch'
patch_path.write_text(patch)
receipt = {
 'verdict': 'HOLD_EXACT310_CURRENT_COMPLETE_CI_AND_MERGE; GO_BOUNDED_FIRST_READINESS_FAILURE_CENSUS_ONLY',
 'source': {'head': head, 'tested_merge': tested, 'tree': tree, 'ordered_tested_parents': ['fbde0d3a248c47c9964851355f96575c89a87329', head], 'new_actual_target': target, 'old_tested_union_not_current_target_acceptance': True},
 'job': {'run': 38110093076, 'job': 114383685403, 'terminal': 'FAILURE', 'only_failed_step': 'Test (integration)', 'url': 'https://github.com/joshyorko/actions/actions/runs/38110093076/job/114383685403'},
 'full_declared_inventory': {'count': 23, 'success': 21, 'expected_tag_only_workitems_publish_skip': 1, 'failure': 1, 'current_Runtime_required_failure_not_excluded': True, 'metadata': bind(metadata_path)},
 'counts': {'portable': {'passed':1054, 'skipped':94, 'warnings':14, 'seconds':434.44}, 'integration': {'failed':3, 'passed':128, 'skipped':18, 'deselected':1151, 'seconds':1835.10}, 'configured_typecheck_after_test_failure': {'status':'PASS','source_files':335}},
 'failed_nodes_and_complete_RCC_intervals': timings,
 'primary_source_attribution': {'exception':'TimeoutError', 'location':'action_server/src/actions/server/_selftest.py:202', 'wait':'future.result(1) followed by native90-second deadline', 'startup_stage':'first host/port readiness before reload/collision/recovery assertions', 'primary_paths_mode_blobs':{p:refs[head][p] for p in primary_paths}, 'primary_paths_equal_accepted292_current4b_and_actual311target':True, 'producer268_selected5_equal_base_head_tested_actual_target':True, 'actual311_observer_import_is_test_only':['action_server/tests/action_server_tests/fixtures.py','action_server/tests/action_server_tests/native_startup_diagnostics.py'], 'unchanged_test_nodes_preserved':True},
 'RCC_interpretation': {'version':'18.19.3', 'immutable_source':rcc, 'delta_contract':'now minus previous ProgressMark', 'step08':'preceding micromamba/layer-record/setup interval before UV starts', 'step09':'UV interval', 'step15':'restoration/externally-managed/stage cleanup interval; not total', 'no_unexplained_caller_vs_sum_forwarding_gap':True, 'remaining_ready_port_duration_and_phase':'UNAVAILABLE; no child CPU/IO or firstREADY observation retained in this job'},
 'cleanup': {'failure_cleanup_source_budget_seconds':20, 'explicit_note_counts':notes, 'wrapper_return_reader_descendant_census':'UNKNOWN in retained failure output; absence of notes does not establish each cleanup predicate', 'no_cleanup_waiver_or_Rcc_cause_claim':True},
 'artifact_identity': {'Windows_Runtime_build_metadata':next(a for a in metadata['artifact_metadata_only'] if a['id']==11691821082), 'digest_scope':'GitHub artifact metadata digest only; original ZIP/binary members not independently downloaded/rehashed in this failure review', 'actual_binary_checkout':tested, 'actual_executable_member_hash':'UNKNOWN', 'native_UI_3OS_current_jobs':'PASS for selected31-module/frozen31/wrapper31 and two consumer cases as previously reviewed logs; distinct workflow binaries and selector scope, does not repair failed Runtime integration job', 'historical_native_tuples':'Linux92498/f506 and original65c Mac/Windows remain separate; neither relabeled'},
 'original_private_log':bind(log),
 'safe_receipt_policy':'No provider URLs, environment payloads, configuration values or raw child paths copied; full decoded log remains local-only',
 'Documentation improvement': {'Canonical file changed or proposed':'docs/skills/repository-operations.md exact additive patch', 'Exact delta':bind(patch_path), 'Durable learning captured':'First-readiness and semantic failures differ; complete previous-mark timing sequence and absent-cleanup-note limits; separate selected native UI from full Runtime gate', 'Evidence':'Exact terminal3-node log, unchanged source/deadlines and268+5 inventory, immutable RCC4148 sources, separately passing native workflow jobs', 'Stale or ambiguous guidance removed':'Final progress equals total; step08 duration is UV; no cleanup note proves full cleanup; selected UI green admits full Runtime CI', 'Remaining uncertainty':'Cause of first readiness delay, unmeasured READY remainder, explicit cleanup census, executable member identity, new actual-target union and fresh full gates'},
 'Upstream disposition':'none; no confirmed maintained upstream defect established; no external issue authority used',
}
receipt_path = out / '310-terminal-first-readiness-independent-review.json'
receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({'receipt':bind(receipt_path),'canonical_patch':bind(patch_path),'numeric_progress_sequences':len(timings),'producer_inputs_verified':len(inputs),'selected_inputs_verified':len(selected)}))
