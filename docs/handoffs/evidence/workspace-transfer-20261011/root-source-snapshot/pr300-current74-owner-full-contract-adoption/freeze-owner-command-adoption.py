import ast
import datetime
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

R = Path('/workspace/engineering/pr300')
D = Path('/workspace/engineering/pr300-issue86-assembled-transport-source-successor')
O = Path(__file__).resolve().parent
H = '74beef4d220c3a1e8f983cecd42b9bb84ac75e79'
T = '2238ed312babba9fd5ad89a3a1cc581ca6ad2dcf'
def git(*a):
    return subprocess.check_output(['git', *a], cwd=R)
def binding(p):
    p = Path(p)
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
def check(v):
    assert binding(v['path']) == {k: v[k] for k in ('path', 'bytes', 'sha256')}, v['path']
assert git('rev-parse', 'HEAD').decode().strip() == H
assert git('rev-parse', 'HEAD^{tree}').decode().strip() == T
assert git('status', '--porcelain') == b''
owner_path = D/'OWNERFINAL-current74-issue86-assembled-transport-LIGHT-full-and-actual-HOLD.json'
assert binding(owner_path)['sha256'] == '81262278d658e37b8e8d9afbdfdcfe2b69d1852619bba3898b5a576a0acf1a32'
a = json.loads(owner_path.read_bytes())
proof_ref = a['complete1423_proof']; check(proof_ref)
proof = json.loads(Path(proof_ref['path']).read_bytes())
assert proof['head'] == H and proof['tree'] == T and len(proof['all1423']) == 1423
for v in proof['all1423']:
    p = R/v['path']
    b = os.readlink(p).encode() if v['mode'] == '120000' else p.read_bytes()
    assert len(b) == v['bytes'] and hashlib.sha256(b).hexdigest() == v['sha256']
    assert git('cat-file', 'blob', v['blob']) == b
    assert v['mode'] == '120000' or bool(p.stat().st_mode & 0o111) == (v['mode'] == '100755')
refs = {v['path']: v for v in a['all68_original_reference_bytes_unchanged'] + a['evidence_refs']}
for v in refs.values(): check(v)
prep_path = Path('/workspace/engineering/pr300-actual299-refresh/own-Bootstrap-reuse-inputs-and-origins.json')
prep = json.loads(prep_path.read_bytes())
assert len(prep['all30_current_inputs_exact_prepared_Git_bytes']) == 30
for n, sha in prep['all30_current_inputs_exact_prepared_Git_bytes'].items():
    assert binding(R/n)['sha256'] == sha
for n,v in prep['five_own_environment_configs'].items():
    assert binding(R/n/'.venv/pyvenv.cfg')['sha256'] == v['config_sha256']
    assert str((R/n/'.venv/bin/python').resolve()) == v['python_resolved']
assert len(a['own_origins']) == 5
for v in a['own_origins']:
    check(v)
    origin = json.loads(Path(v['path']).read_bytes())
    assert Path(origin['prefix']).resolve().is_relative_to(R)
    assert Path(origin['origin']).is_relative_to(R) and Path(origin['origin']).is_file()
fixture = a['ignored_owned_RCC_exact_mode0711']
assert binding(R/fixture['path'])['sha256'] == fixture['sha256']
assert (R/fixture['path']).stat().st_size == fixture['bytes']
assert stat.S_IMODE((R/fixture['path']).stat().st_mode) == int(fixture['mode'], 8)
assert binding('/workspace/actions-cloud/bin/rcc')['sha256'] == fixture['sha256']
contract_path = Path('/workspace/engineering/pr300-current74-independent-light-review/proposed-current74-configured-full-command-contract.json')
contract_ref = binding(contract_path)
assert contract_ref['bytes'] == 1830 and contract_ref['sha256'] == '2881ff048c9b97c1c97bf2455c943b1a1cfb0b9fff82a392ac0312ad37ead0a8'
contract = json.loads(contract_path.read_bytes())
assert contract['subject']['head'] == H and contract['subject']['tree'] == T
code = contract['argv'][-1]
assert hashlib.sha256(code.encode()).hexdigest() == contract['python_code_sha256']
compile(code, '<reviewed-current74-command>', 'exec')
parsed = ast.parse(code)
assign = next(i for i,n in enumerate(parsed.body) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript) and ast.unparse(n.targets[0]) == "os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']")
call = next(i for i,n in enumerate(parsed.body) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and ast.unparse(n.value.func) == 'toolkit.poetry')
assert assign < call and ast.literal_eval(parsed.body[assign].value) == '2'
review_dir = contract_path.parent
independent = [binding(review_dir/n) for n in ('OWNERFINAL-independent-current74-A300-LIGHT-source-and-full-proposal-review.json','OWNERFINAL-independent-current74-A300-LIGHT-and-explicit-worker-proposal-complete.json')]
assert all(json.loads(Path(v['path']).read_bytes())['verdict'].startswith('GO') for v in independent)
historical = binding('/workspace/engineering/pr300-actual299-refresh/run-authorized-full.py')
assert historical['sha256'] == '6a8cb72fb3cb2b20561a9ca97a4f4411a1ce201fa7c4ceb3cd41cf4e31e12a5d'
reviewed876 = binding('/workspace/engineering/pr312-actual309-refresh/full-source-gates-explicit-two-workers-root-release-required.py')
assert reviewed876['sha256'] == '876adde7c0f82ee428413afc48a6b8d7851937c55f8140facb3f76335b70501d'
patch = binding(D/'canonical-assembled-output-transport-denial-measurement-exact-source.patch')
assert patch['sha256'] == '8895960c82512f4a4a8e0a45e4a1f0af0a5aa061865e9ffc487961a322745a7b'
assert git('status','--porcelain') == b''
result = {
 'status': 'OWNER_ADOPTS_INDEPENDENTLY_REVIEWED_CURRENT74_COMMAND__EXECUTION_HELD',
 'frozen_at_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'head': H, 'tree': T, 'target': contract['subject']['target'], 'clean': True,
 'exact_contract': contract_ref, 'exact_argv': contract['argv'], 'cwd': str(R),
 'python_code_sha256': contract['python_code_sha256'], 'new_launcher_authored': False,
 'old784_launcher_preserved': historical, 'reviewed876_mechanism_reference': reviewed876,
 'mechanism_comparison': 'Explicit PYTEST_XDIST_AUTO_NUM_WORKERS=2 before unchanged Runtime invoke test-not-integration, which retains configured -n auto and inherits2. Prior876 also runs sequential devutils -n2; current approved contract intentionally runs Runtime only, with Toolkit96 already admitted. No task implementation changed.',
 'independent_current74_reviews': independent,
 'preexecution_source1423_Git_FS_body_exec_verified': proof_ref,
 'original_reference_count': len(a['all68_original_reference_bytes_unchanged']),
 'owner_evidence_reference_count': len(a['evidence_refs']),
 'all_distinct_original_and_LIGHT_reference_bindings_verified': list(refs.values()),
 'prepared_inputs': {'record':binding(prep_path),'count':30,'five_own_configs_and_python_resolution_verified':True,'five_concrete_source_origins':a['own_origins'],'ignored_pinned_RCC':fixture,'managed_gateway':binding('/workspace/actions-cloud/bin/rcc')},
 'required_execution_bracket': ['Root distinct serialization release AFTER312 terminal plus fresh capacity>=1200000000B','Rehash all1423 typed Git/FS source entries, original68 and LIGHT references, own30 inputs/five origins/ignoredRCC immediately before execution','ExactlyONE exact reviewed command with600TERM+10, no source/full retries','After terminal retain raw private log/actual exit and counts, then all same source/ref/prepared byte+mode checks before OWNERFINAL; failures preserved, not relabeled'],
 'fresh_available_bytes_observation_only': os.statvfs(R).f_bavail*os.statvfs(R).f_frsize,
 'current_full_execution_attempts':0, 'actual_ASGI_TCP_envelope_authored_or_run':False,
 'remaining_HOLD': ['Current74 full source result/OWNERFINAL/independent finalSOURCE','Sourcepush/fresh current74-a0d CI','Original784 Windows FIRST startup failure unchanged; no cleanup/reaping conclusion','Whole86/83/84/129/native9/TCP/private/provider/backend/PG/browser/installedwheel/release'],
 'documentation_improvement': {'Canonical_file_changed_or_proposed':'docs/skills/provenance-observability.md','Exact_delta':patch,'Disposition':'Existing independently accepted exact8-line currentSOURCE lesson reused; no further source or root-guide edits.','Evidence':'Frozen LIGHT30PASS with19 measured cases20 requests and two actual mutation sensitivities; explicit attempted-open counts and SQL/schema/full typed ownedFS state.','Stale_ambiguity':'Old784 launcher cannot authorize74; -n auto requires explicit inherited2, unlike assuming an earlier package -n2 limits Runtime. Current contract is still proposed, not executed.','Remaining_uncertainty':'Full result and separately reviewed actual transport absent; capacity/serialization observation is not release.'},
 'upstream_disposition':'none', 'immutable_constructor':binding(__file__)
}
out = O/'OWNERFINAL-current74-reviewed-full-command-adoption-and-execution-HOLD.json'
assert not out.exists()
out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); out.chmod(0o600)
print(json.dumps(binding(out)))
