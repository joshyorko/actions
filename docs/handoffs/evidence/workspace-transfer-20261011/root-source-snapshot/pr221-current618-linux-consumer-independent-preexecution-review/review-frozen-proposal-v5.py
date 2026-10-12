import ast
import base64
import copy
import csv
import datetime
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
import zipfile

B = Path('/workspace/engineering/pr221-current618-linux-consumer-preflight')
O = Path('/workspace/engineering/pr221-current618-linux-consumer-independent-preexecution-review')
R = Path('/workspace/engineering/pr282')
def sha(body): return hashlib.sha256(body).hexdigest()
def load(path): return json.loads(Path(path).read_bytes())
verified = {}
def binding(row):
    p = Path(row['path']); body = p.read_bytes()
    assert len(body) == row['bytes'] and sha(body) == row['sha256'], str(p)
    verified[str(p)] = row
    return row
def refs(value):
    if isinstance(value, dict):
        if {'path', 'bytes', 'sha256'} <= value.keys() and str(value['path']).startswith('/'):
            binding(value)
        for child in value.values(): refs(child)
    elif isinstance(value, list):
        for child in value: refs(child)
def tree(path): return ast.parse(Path(path).read_bytes())
def dump(node): return ast.dump(node, include_attributes=False)
def functions(path): return {n.name:n for n in tree(path).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
def git(*args): return subprocess.check_output(['git', '--no-optional-locks', '-C', str(R), *args])
final = binding({'path':str(B/'OWNERFINAL-current618-isolated-Linux-consumer-preexecution-proposal-v5-successor-v2.json'), 'bytes':70901, 'sha256':'38d07ed81d6ce129a7786325b7447c8e2bfb8b134c1f02c78fd2c6788b0ff027'})
d = load(final['path']); refs(d)
assert len(d['all_private_preexecution_files_and_preserved_originals']) == 153
v4 = load(d['previous_v4_immutable_proposal']['path']); refs(v4)
original_owner = load(d['previous_immutable_v5_owner_before_scope_wording_correction']['path']); refs(original_owner)
assert d['previous_immutable_v5_owner_before_scope_wording_correction']['sha256'] == '5650f8ee5f90f209ccc547d67593f1d5f2e773340b92f4b81dae83a1d1ff5db4'
scope = load(d['source_control_scope_proof']['path']); refs(scope)
assert len(scope['all_original_preflight_owner_independent_failure_and_artifact_refs']) == 126
assert d['runner']['sha256'] == '67912e4bfdc1de4dd83d36511bf19b19cd90e34c0d84197d30a7e05f0fce4ad9'
assert d['input_gate'] == v4['input_gate'] and d['input_gate']['sha256'] == '1edf96b6b801de5e7b8c1c7c284a636cec44bc06fcb45adb6e1781e519b3a8f6'
assert d['input_manifest']['sha256'] == '596942a7c85fe6f742777454d6d1a76c1bc3e8c29ed88f693eea28af856d7c34'
runner = Path(d['runner']['path']); previous = Path(v4['runner']['path'])
a, b = functions(runner), functions(previous)
assert a.keys() == b.keys() and len(a) == 9
assert all(dump(a[name]) == dump(b[name]) for name in a)
isolated = d['new_v5_private_dedicated_input_directory']
wheel = Path(d['selected_cp312_wheel']['path'])
assert wheel.parent == Path(isolated['path']) and stat.S_IMODE(wheel.parent.stat().st_mode) == 0o700
assert set(wheel.parent.iterdir()) == {Path(row['copy']['path']) for row in isolated['files']}
assert len(isolated['files']) == 2
with zipfile.ZipFile(d['original_archive']['path']) as archive:
    for row in isolated['files']:
        binding(row['original']); binding(row['copy'])
        assert row['original']['sha256'] == row['copy']['sha256']
        assert stat.S_IMODE(Path(row['copy']['path']).stat().st_mode) == 0o600
        assert not Path(row['copy']['path']).is_symlink()
        assert sha(archive.read(row['original_ZIP_member'])) == row['copy']['sha256']
v5body, v4body = runner.read_text(), previous.read_text()
new_manifest = load(d['input_manifest']['path']); old_manifest = load(v4['input_manifest']['path'])
restored = copy.deepcopy(new_manifest)
assert restored['original_selected_wheel']['private_path'] == str(wheel)
restored['original_selected_wheel']['private_path'] = old_manifest['original_selected_wheel']['private_path']
assert restored == old_manifest
for old, new in [(v4['selected_cp312_wheel']['path'], str(wheel)),
                 (v4['planned_ONE_actual_gateway']['attempt_root'], d['planned_ONE_actual_gateway']['attempt_root']),
                 (v4['input_manifest']['path'], d['input_manifest']['path']),
                 (v4['input_manifest']['sha256'], d['input_manifest']['sha256'])]:
    assert v4body.count(old) == 1
    v4body = v4body.replace(old, new)
assert v5body == v4body
for name in ['test_installed_consumer_runner', 'test_current_input_admission', 'test_current_input_provenance']:
    old = (B/(name+'_v4.py')).read_text()
    new = (B/(name+'_v5.py')).read_text()
    old = old.replace('installed-consumer-runner-v4.py', 'installed-consumer-runner-v5.py').replace('input-and-source-admission-v4.json','input-and-source-admission-v5.json')
    assert dump(ast.parse(new)) == dump(ast.parse(old)), name
controls = functions(B/'test_platform_input_directory_v5.py')
assert len([name for name in controls if name.startswith('test_')]) == 6
controls_body = (B/'test_platform_input_directory_v5.py').read_text()
assert 'floor.select_runtime_wheel(ORIGINAL)' in controls_body
assert controls_body.count('found 2$') == 2
assert 'shutil.copyfile(FOREIGN' in controls_body
assert 'b"Name: actions-runtime"' in controls_body and 'b"Version: 1.0.3"' in controls_body
assert 'runner.load("input_gate").admit(' in controls_body
green = d['service_free_controls']['current_v5']; binding(green['log'])
log = Path(green['log']['path']).read_text()
assert '100 passed, 2 warnings in 12.65s' in log and 'actual main robot run" was SUCCESS' in log
assert green['skipped'] == 0 and green['existing'] == 93 and green['new_directory_controls'] == 7
assert all(token in log for token in ['ruff check', 'ruff format --check', 'isort --check'])
selector_receipt = load(isolated['real_selector_and_full_current_input_admission']['path'])
assert selector_receipt['selected_exact_path'] == str(wheel)
assert selector_receipt['original_mixed_result'] == 'REJECTED_2_MATCHING_CP312_WHEELS'
assert selector_receipt['worker_install_pip_CLI_cleanup_executed'] is False
assert selector_receipt['selector_source_sha256'] == d['helpers_current_Git618_and_immutable_snapshots_exact']['floor']['sha256']
assert d['budgets'] == v4['budgets']
assert d['helpers_current_Git618_and_immutable_snapshots_exact'] == v4['helpers_current_Git618_and_immutable_snapshots_exact']
assert d['known_checkout_roots'] == v4['known_checkout_roots'] and len(d['known_checkout_roots']) == 15
assert d['producer'] == v4['producer'] and d['actual_integration'] == v4['actual_integration']
owner = load(d['artifact_data_ownerfinal']['path']); refs(owner)
assert d['artifact_data_ownerfinal']['sha256'] == '9b406fdf505871e6790d7a4233d0b8c075ae6f170f2c5b7a954bbca0f0d46236'
assert len(owner['evidence']) == 24
inspection = load(owner['complete_original_member_inventories']['path'])
artifact = next(row for row in inspection['artifacts'] if row['file']['sha256'] == d['original_archive']['sha256'] and row['file']['path'] == d['original_archive']['path'])
identity = {'id':artifact['id'], 'run':owner['producer']['run_id'], 'job':artifact['job_id']}
assert identity == d['independent_provenance_expectation']['derived_identity'] == {'id':11697353355,'run':38126987514,'job':114433293243}
for label, key in [('id','artifact_id'),('run','run_id'),('job','job_id')]:
    assert type(new_manifest['original_archive'][label]) is int
    assert new_manifest['original_archive'][label] == new_manifest['producer_tuple'][key] == identity[label]
counts = d['current_counts']; assert counts == {'python':202,'tracked_source_payloads':215,'RECORD_files':221,'RECORD_hashsize_verified':220,'directories':27}
with zipfile.ZipFile(wheel) as archive:
    files = [row for row in archive.infolist() if not row.is_dir()]
    assert len(files) == 221 and len(archive.infolist()) - len(files) == 27
    assert len([row for row in files if row.filename.endswith('.py')]) == 202
    assert len([row for row in files if '.dist-info/' in row.filename]) == 4
    for row in new_manifest['original_selected_wheel']['all_member_inventory']:
        body = archive.read(row['path']); assert len(body) == row['bytes'] and sha(body) == row['sha256']
    for row in new_manifest['tracked_member_bindings']:
        body = archive.read(row['member'])
        assert sha(body) == row['member_sha256'] == row['source_sha256']
        source = git('show', new_manifest['producer_tuple']['synthetic']+':'+row['source_path'])
        assert source == body
        entry = git('ls-tree', new_manifest['producer_tuple']['synthetic'], row['source_path']).decode().split()
        assert entry[0] == row['source_mode'] and entry[2] == row['source_blob']
        assert bool((archive.getinfo(row['member']).external_attr >> 16) & 0o111) == (row['source_mode'] == '100755')
    record = next(row.filename for row in files if row.filename.endswith('.dist-info/RECORD'))
    rows = list(csv.reader(io.StringIO(archive.read(record).decode())))
    assert len(rows) == 221
    hashed = 0
    for name, digest, size in rows:
        if name == record: assert digest == size == ''; continue
        algorithm, encoded = digest.split('=',1); assert algorithm == 'sha256'
        body = archive.read(name)
        assert len(body) == int(size) and base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode().rstrip('=') == encoded
        hashed += 1
    assert hashed == 220
assert d['harness'] == v4['harness']
harness = load(d['harness']['complete_prehash']['path'])
assert git('rev-parse','HEAD').decode().strip() == d['harness']['head'] == 'e736f846557ed1d603348e97c5eb80060d62e3e2'
assert git('rev-parse','HEAD^{tree}').decode().strip() == '07b716104ba623df81c00bd83be08dde84dd29f1'
assert git('status','--porcelain') == b'' and len(harness['tracked_sha256']) == 1433
for name, digest in harness['tracked_sha256'].items():
    assert sha((R/name).read_bytes()) == digest
    assert bool((R/name).stat().st_mode & 0o111) == harness['tracked_executable_bits'][name]
for name, row in d['helpers_current_Git618_and_immutable_snapshots_exact'].items():
    binding(row)
    if name != 'rcc':
        rel = Path(row['path']).relative_to('/workspace/engineering/pr311' if name == 'guard' else R).as_posix()
        assert sha(git('show', d['actual_integration']['sha']+':'+rel)) == row['sha256']
snapshots = [row for row in d['all_private_preexecution_files_and_preserved_originals'] if '/unchanged-helper-snapshots/' in row['path']]
assert len(snapshots) == 4 and all(stat.S_IMODE(Path(row['path']).stat().st_mode) == 0o444 for row in snapshots)
assert not Path(d['planned_ONE_actual_gateway']['attempt_root']).exists()
assert d['planned_ONE_actual_gateway']['attempt_root'].endswith('-3')
assert d['planned_ONE_actual_gateway']['argv'][:-1] == v4['planned_ONE_actual_gateway']['argv'][:-1]
assert d['planned_ONE_actual_gateway']['argv'][-1] == v4['planned_ONE_actual_gateway']['argv'][-1].replace('installed-consumer-runner-v4.py','installed-consumer-runner-v5.py')
assert d['actual_consumer_executed'] is False and d['pip_install_download_publication_executed'] is False
assert d['previous_original_v4_GATEWAY_FAIL']['sha256'] == '6f29ccd4b905b0036e6347aac23c12bda82cb6a719a1e7da0008eec951c0e773'
binding({'path':str(O/'independent-frozen-original-v4-consumer-failure-review-final.json'),'bytes':7215,'sha256':'c61398f72766de55af65d5817a23e831ce9d8b5f97fdc298f8f7521fe89004eb'})
doc = d['documentation_improvement']; patch = binding(doc['Exact_accepted_delta'])
assert patch['sha256'] == 'fb9c9604f6f9dd32259d9a133eadafba076acfd92546ab0ccce2a080a918591c'
added = [line[1:] for line in Path(patch['path']).read_text().splitlines() if line.startswith('+') and not line.startswith('+++')]
assert len(added) == 8
guide = Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
assert '\n'.join(added).strip() in guide
assert 'DO_NOT_APPLY_DUPLICATE' in doc['Equivalent_unintegrated_proposal_disposition']['status']
receipt = {
    'schema':'current618-linux-consumer-independent-v5-preexecution-review/v1',
    'status':'GO_V5_PREEXECUTION_ONLY_DISTINCT_ROOT_CAPACITY_SERIALIZATION_AND_ONE_EXECUTION_REQUIRED',
    'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'owner_final_proposal':final,'runner':d['runner'],'gate':d['input_gate'],'manifest':d['input_manifest'],
    'verified':{'final_refs':153,'preserved_original_refs':126,'owner_refs':24,'unique_direct_file_bindings':len(verified),
        'all_ref_sizes_SHA_exact':True,'original_Linux_pair_copies_original_ZIP_bytes_exact':True,'private_input_directory0700_files0600':True,
        'real_unchanged_selector_controls_mixed2_baseline1_foreign2_metadata_and_identity':True,'recorded100_controls0skip_existing93_AST_exact':True,
        'all9_runner_functions_and_remaining_globals_exact_v4_four_literals_only':True,'manifest_only_private_wheel_path_changed':True,
        'independently_bound_current_archive_identity':identity,'current_counts':counts,'all215_producer_Git_bytes_modes_and_all221_RECORD220_hashes_exact':True,
        'four_distinfo_and_two_generated_exceptions_separate':True,'clean1433_harness_e736_07b_prehash_and_execbits':True,
        'unchanged_four_helpers_Git618_and0444_snapshots_Rcc7e588_15roots':True,'fresh_suffix3_absent':True,
        'original_v3_HOLD_v4_preexecGO_and_original_actual_FAILURE_unmodified':True,'initial_KeyError_preparation_diagnostic_retained_no_product_failure':True,
        'metadata_only_v5_successor_scope_correction_not_test_rerun':True},
    'exact_planned_gateway':d['planned_ONE_actual_gateway'],'budgets':d['budgets'],
    'capacity':'No actual consumer executed by reviewer. Fresh >=1.2GB and serialization plus distinct root ONE authorization required; recorded freeze space is not current capacity approval.',
    'failure_disposition':'Original v4 failed at real mixed-directory selector before attempt/worker/install/CLI/cleanup. v5 isolates exact original bytes without weakening selector or guards. Original refusal and consumed authorization remain historical, not a consumer result.',
    'documentation_improvement':doc,'remaining_HOLDs':d['remaining_HOLDs'],
    'not_performed':['Selector/control/gateway/consumer rerun','Runtime payload imports/install/CLI','Source/index/branch changes','Download or acquisition','Publication/tag/native/provider/browser/Windows gates/push/merge'],
    'upstream_disposition':'none'}
dest = O/'OWNERFINAL-independent-frozen-v5-preexecution-review-GO.json'; assert not dest.exists()
dest.write_text(json.dumps(receipt,indent=2)+'\n'); dest.chmod(0o444)
print(json.dumps({'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest.read_bytes()),'status':receipt['status']}))
