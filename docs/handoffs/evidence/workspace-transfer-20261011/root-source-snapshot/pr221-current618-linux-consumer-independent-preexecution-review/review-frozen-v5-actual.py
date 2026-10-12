import ast
import datetime
import hashlib
import json
from pathlib import Path
import stat
import subprocess
from urllib.parse import unquote, urlparse
import zipfile

B = Path('/workspace/engineering/pr221-current618-linux-consumer-preflight')
O = Path('/workspace/engineering/pr221-current618-linux-consumer-independent-preexecution-review')
R = Path('/workspace/engineering/pr282')
def sha(body): return hashlib.sha256(body).hexdigest()
def load(p): return json.loads(Path(p).read_bytes())
verified = {}
def binding(row):
    p = Path(row['path']); body = p.read_bytes()
    assert len(body) == row['bytes'] and sha(body) == row['sha256'], str(p)
    verified[str(p)] = row
    return row
def refs(value):
    if isinstance(value, dict):
        if {'path','bytes','sha256'} <= value.keys() and str(value['path']).startswith('/'):
            binding(value)
        for item in value.values(): refs(item)
    elif isinstance(value, list):
        for item in value: refs(item)
def git(*args): return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*args])
final = binding({'path':str(B/'OWNERFINAL-current618-one-installed-Linux-consumer-checkpoint.json'),'bytes':12657,'sha256':'cc0832511827bc73431f2adbe0dbb92ec01b52b03afa4164cea67d0ae4aaf246'})
d = load(final['path']); refs(d)
proposal = load(d['proposal']['path']); refs(proposal)
assert d['proposal']['sha256'] == '38d07ed81d6ce129a7786325b7447c8e2bfb8b134c1f02c78fd2c6788b0ff027'
assert d['independent_preexecution_GO']['sha256'] == 'e319a803881eb5f79755f5767d8eee9b04c4a5cb03ed75386537f8f6c7ad33e7'
assert len(d['evidence']) == 16 and len(proposal['all_private_preexecution_files_and_preserved_originals']) == 153
for key in ['runner','input_gate','input_manifest']: assert d[key] == proposal[key]
scope = load(proposal['source_control_scope_proof']['path']); refs(scope)
assert len(scope['all_original_preflight_owner_independent_failure_and_artifact_refs']) == 126
attempt = Path(proposal['planned_ONE_actual_gateway']['attempt_root'])
assert attempt.name.endswith('-3') and attempt.is_dir() and stat.S_IMODE(attempt.stat().st_mode) == 0o700
raw = [row for row in d['evidence'] if Path(row['path']).parent == attempt]
assert len(raw) == 11 and all(stat.S_IMODE(Path(row['path']).stat().st_mode) == 0o600 for row in raw)
identity = load(attempt/'attempt-identity.json')
cleanup = load(attempt/'execution-cleanup-receipt.json')
proof = load(attempt/'consumer-proof.json')
inventory = load(attempt/'installed-inventory-raw.json')
input_admit = load(attempt/'input-admission.json')
pip = load(attempt/'pip-install-report.json')
argv = load(attempt/'install-argv.json')
authorization = load(B/'root-one-actual-current618-v5-execution-authorization.json')
assert authorization['proposal'] == d['proposal'] and authorization['independent_GO'] == d['independent_preexecution_GO']
assert authorization['actual_attempts_authorized'] == 1
assert authorization['status'] == 'ROOT_ONE_CURRENT618_V5_LINUX_CP312_CONSUMER_AUTHORIZED'
assert authorization['command'] == proposal['planned_ONE_actual_gateway']
assert authorization['fresh_capacity']['/workspace'] >= 1200000000
exit_receipt = load(B/'original-one-actual-current618-v5-gateway-exit.json')
assert exit_receipt['exit_code'] == 0 and d['gateway_exit'] == 0
gateway = (B/'original-one-actual-current618-v5-gateway.log').read_text()
assert 'actual main robot run" was SUCCESS' in gateway
assert d['case_count'] == proof['case_count'] == 1 and d['skips'] == proof['skips'] == 0
assert proof['status'] == 'passed' and proof['cli_version'] == d['cli_version'] == '1.0.3'
assert (attempt/'cli-version.stdout.log').read_bytes() == b'1.0.3\n'
assert (attempt/'cli-version.stderr.log').read_bytes() == b''
assert 'No broken requirements found.' in (attempt/'worker.stdout.log').read_text()
assert d['cleanup'] == cleanup and cleanup['status'] == 'passed'
for field in ['wrapper_reaped','descendant_snapshot_complete','descendant_reap_complete','temporary_removed']:
    assert cleanup[field] is True
for field in ['active_readers','cleanup_errors','observed_live_children','observed_zombie_children']:
    assert cleanup[field] == []
assert 0 < cleanup['elapsed_seconds'] < 600
assert identity['worker_deadline_seconds'] == 595 and identity['overall_process_deadline_seconds'] == 600 and identity['cleanup_seconds'] == 5
assert proposal['budgets']['outer_gateway_seconds'] == 645 and proposal['budgets']['outer_TERM_KILL_grace_seconds'] == 10
assert identity['runner_sha256'] == d['runner']['sha256']
for name, row in identity['source_bindings'].items():
    assert sha(Path(row['path']).read_bytes()) == row['sha256']
temporary = Path(identity['temporary_root']); prefix = temporary/'venv'
assert temporary.parent == Path('/tmp') and temporary.name.startswith('rt103-current618-') and not temporary.exists()
assert identity['argv'] == [identity['supervisor_python'], d['runner']['path'], '--worker', str(temporary)]
assert identity['supervisor_python'] == str(R/'action_server/.venv/bin/python')
wheel = Path(proposal['selected_cp312_wheel']['path'])
expected_argv = [str(prefix/'bin/python'),'-m','pip','install','--isolated','--no-cache-dir','--index-url','https://pypi.org/simple','--only-binary=:all:','--report',str(attempt/'pip-install-report.json'),str(wheel),'actions-core==1.0.2','actions-http-helper==1.0.3']
assert argv == expected_argv
assert proof['pip_report_sha256'] == sha((attempt/'pip-install-report.json').read_bytes()) == '65a0b1f7e9b9cb1d071e83e9f61d3ec17d7383f7830c05366f4f4b4a44ad4ee8'
assert proof['inventory_sha256'] == sha((attempt/'installed-inventory-raw.json').read_bytes())
installed = {row['metadata']['name'].lower().replace('_','-'):row for row in pip['install']}
assert len(installed) == len(pip['install'])
for name, public in d['public_dependencies'].items():
    assert proof['public_dependencies'][name] == public
    row = installed[name]
    assert row['metadata']['version'] == public['version']
    assert row['download_info']['url'] == public['url']
    assert row['download_info']['archive_info']['hashes']['sha256'] == public['sha256']
    assert row['requested'] is True
    assert row['download_info']['url'].startswith('https://files.pythonhosted.org/')
assert d['public_dependencies']['actions-core']['version'] == '1.0.2'
assert d['public_dependencies']['actions-core']['sha256'] == '9d527edf540978172178894546add75f117f240786aec804cb75c308615a7e80'
assert d['public_dependencies']['actions-http-helper']['version'] == '1.0.3'
assert d['public_dependencies']['actions-http-helper']['sha256'] == '46ed7ce0e0d3e2e05456d937b5b24bc9dfa0d7d4b98f8119b9fdf00d4fa7e9f9'
runtime = installed['actions-runtime']
assert runtime['metadata']['version'] == '1.0.3' and runtime['is_direct'] is True and runtime['requested'] is True
assert unquote(urlparse(runtime['download_info']['url']).path) == str(wheel)
assert runtime['download_info']['archive_info']['hashes']['sha256'] == proposal['selected_cp312_wheel']['sha256']
assert inventory['prefix'] == str(prefix) and inventory['prefix'] != inventory['base_prefix']
assert inventory['runtime_version'] == '1.0.3' and inventory['wheel_sha256'] == proposal['selected_cp312_wheel']['sha256']
assert set(inventory['modules']) == {'actions','actions.server','actions.mcp','actions_http'}
assert all(Path(path).is_relative_to(prefix) for path in inventory['modules'].values())
for checkout in proposal['known_checkout_roots']:
    assert all(not Path(path).is_relative_to(checkout) for path in inventory['sys_path'] + list(inventory['modules'].values()))
members = {row['member']:row for row in proof['members']}
assert len(members) == len(proof['members']) == len(inventory['members']) == d['installed_python_members'] == 202
assert set(members) == set(inventory['members'])
with zipfile.ZipFile(wheel) as archive:
    expected_names = {name for name in archive.namelist() if name.endswith('.py')}
    assert expected_names == set(members)
    for name, row in members.items():
        assert row['path'] == inventory['members'][name] and Path(row['path']).is_relative_to(prefix)
        assert row['sha256'] == sha(archive.read(name))
        # Inspect syntax directly; do not import wheel payloads or invoke the guard.
        t = ast.parse(archive.read(name))
        for node in ast.walk(t):
            if isinstance(node, ast.Import): assert not any(x.name.startswith('actions._') for x in node.names)
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or '').startswith('actions._')
                assert not (node.module == 'actions' and any(x.name.startswith('_') for x in node.names))
    assert sha(archive.read('actions/server/_oauth2_config.py')) == load(proposal['input_manifest']['path'])['oauth_member']['sha256']
assert input_admit == proof['input_admission'] == d['input_admission']
assert input_admit['record_entries'] == 221 and input_admit['record_verified_entries'] == 220
assert input_admit['tracked_payload_source_matches'] == 215 and input_admit['python_member_count'] == 202
assert input_admit['qualified_archive_provenance'] == {'id':11697353355,'run':38126987514,'job':114433293243}
assert input_admit['generated_oauth_content'] == 'EMPTY_CONTENT_AUTHORITY_HOLD'
assert proof['producer'] == d['producer'] == identity['producer']
producer = d['producer']
assert producer['checkout'] == 'e7666eacf2687f65050b97a88e791f8d0ce4cd20'
assert producer['parents'] == ['a70993fafc99a9f94041485542d5a720797ca394','6181b044c75de35386f1ae30e71725398b6a7feb']
assert producer['tree'] == producer['actual_integration_tree'] == '99ac5309add45af65049546dd3a99f357884cf3b'
assert producer['build_is_actual_integration_job'] is False and producer['publication'] is False
assert git('show','-s','--format=%P',producer['checkout']).decode().strip().split() == producer['parents']
assert git('rev-parse',producer['checkout']+'^{tree}').decode().strip() == producer['tree']
post = load(B/'root-current618-consumer-v5-postexecution-harness-readback.json')
pre = load(proposal['harness']['complete_prehash']['path'])
assert post['tracked_sha256'] == pre['tracked_sha256'] and post['tracked_executable_bits'] == pre['tracked_executable_bits']
assert post['count'] == len(post['tracked_sha256']) == 1433
assert git('rev-parse','HEAD').decode().strip() == 'e736f846557ed1d603348e97c5eb80060d62e3e2'
assert git('rev-parse','HEAD^{tree}').decode().strip() == '07b716104ba623df81c00bd83be08dde84dd29f1'
assert git('status','--porcelain') == b''
for name, digest in post['tracked_sha256'].items():
    assert sha((R/name).read_bytes()) == digest
    assert bool((R/name).stat().st_mode & 0o111) == post['tracked_executable_bits'][name]
old_final = binding({'path':str(O/'independent-frozen-original-v4-consumer-failure-review-final.json'),'bytes':7215,'sha256':'c61398f72766de55af65d5817a23e831ce9d8b5f97fdc298f8f7521fe89004eb'})
assert not (B/'installed-linux-current618-90a785d8-2').exists()
constructor = Path('/workspace/engineering/freeze-current618-v5-consumer-actual.py')
constructor_ref = binding({'path':str(constructor),'bytes':constructor.stat().st_size,'sha256':sha(constructor.read_bytes())})
guide = Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
canonical = []
for p, expected in [(O/'canonical-selector-directory-contract-proposed.patch','fb9c9604f6f9dd32259d9a133eadafba076acfd92546ab0ccce2a080a918591c'),(B/'canonical-independent-archive-provenance-v4-proposed.patch','5f08b459a43e6fe50c6baac0c56f0a6d5241ec6aff913498df39e0d597962aeb')]:
    ref = binding({'path':str(p),'bytes':p.stat().st_size,'sha256':expected}); canonical.append(ref)
    lines = [line[1:] for line in p.read_text().splitlines() if line.startswith('+') and not line.startswith('+++')]
    assert '\n'.join(lines).strip() in guide
receipt = {'schema':'current618-one-Linuxcp312-consumer-independent-actual-review/v1',
    'status':'GO_ONE_CURRENT618_LINUX_CP312_INSTALLED_CONSUMER_ONLY',
    'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owner_final':final,
    'proposal':d['proposal'],'preexecution_GO':d['independent_preexecution_GO'],'runner':d['runner'],
    'original_actual_evidence':d['evidence'],'root_constructor_observed_not_executed':constructor_ref,
    'verified':{'actual_case_count':1,'skips':0,'gateway_exit':0,'CLI_version':'1.0.3',
        'original_raw_evidence_bindings':16,'preexecution_refs_unchanged':153,'original_preserved_refs':126,
        'all_direct_reference_sizes_SHA_exact':True,'direct_file_bindings':len(verified),'raw_attempt0700_files0600':True,
        'exact_pip_install_argv_and_fixed_public_Core102_Helper103_URL_SHA':True,'pip_report_SHA256':proof['pip_report_sha256'],
        'pip_check_success_recorded':True,'four_real_module_origins_in_fresh_prefix_no15_checkout_roots':True,
        '202_retained_in_worker_member_measurements_equal_original_wheel_SHA':True,
        'wholemember_private_Core_guard_ran_in_original_worker_no_violations':True,
        'independent_202_source_AST_direct_import_inspection_no_private_Core':True,
        '215_source_bindings221_RECORD220_hashes_input_admission':True,
        'current_artifact_identity':input_admit['qualified_archive_provenance'],
        'builder_e766_a709_618_equal_actual618_tree_not_actual_job_relabel':True,
        'strict_cleanup_four_true_empty_lists_temporary_removed':True,
        'cleanup_elapsed_seconds':cleanup['elapsed_seconds'],'observed_identity_count':len(cleanup['observed_descendants']),
        '1433_harness_posthash_andexec_exact_e736_07b_clean':True,
        'original_v4_failure_before_worker_and_old_preexec_proofs_unchanged':True},
    'budgets':proposal['budgets'],
    'execution_count':'Two distinct authorized gateways: v4 refused before worker; v5 ran one installed worker. Original v4 remains FAIL; no automatic retry.',
    'measurement_limits':['Owned installed temporary tree removed as designed: retained in-worker SHA/origin measurements, not fresh independent installed-file reread',
        'Cleanup confirms only identity-owned point-in-time captured descendants; no universal adoption or natural shutdown claim',
        'Original private-import static guard scope; no arbitrary dynamic code/security equivalence claim',
        'Linuxcp312-only consumer; separate seven-distribution integrity is not other platform consumers or release admission'],
    'remaining_HOLDs':d['remaining_HOLD'],'documentation_improvement':{
        'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md',
        'Exact_accepted_reuse':canonical,'Durable_learning':'Admit actual selector directory independently of wheel digest; bind artifact/run/job to independently frozen provenance. Both exact lessons remain present; no cosmetic duplicate.',
        'Evidence':'Original v4 preworker refusal; v5 exact isolated pair and current IDs; retained raw actual pip/origin/member/cleanup measurements',
        'Stale_guidance_removed':'None; existing lessons prevent digest-only directory and duplicate-label provenance assumptions.',
        'Remaining_uncertainty':'Removed installed tree cannot be reread; OAuth/source-authority/platform/private/native/full release holds remain.'},
    'not_performed':['Consumer/install/payload imports/CLI/selector/control/gateway rerun','Downloads or acquisitions','Source/ref/index mutations','Tag/publication/native/provider/browser/Windows acceptance'],
    'upstream_disposition':'none'}
dest = O/'OWNERFINAL-independent-current618-one-installed-Linux-consumer-review.json'; assert not dest.exists()
dest.write_text(json.dumps(receipt,indent=2)+'\n');dest.chmod(0o444)
print(json.dumps({'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest.read_bytes()),'status':receipt['status']}))
