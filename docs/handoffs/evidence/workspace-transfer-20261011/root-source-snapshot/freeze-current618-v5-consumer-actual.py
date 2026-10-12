import datetime
import hashlib
import json
from pathlib import Path

base = Path('/workspace/engineering/pr221-current618-linux-consumer-preflight')
attempt = base / 'installed-linux-current618-90a785d8-3'
def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
proposal_path = base / 'OWNERFINAL-current618-isolated-Linux-consumer-preexecution-proposal-v5-successor-v2.json'
assert binding(proposal_path)['sha256'] == '38d07ed81d6ce129a7786325b7447c8e2bfb8b134c1f02c78fd2c6788b0ff027'
proposal = json.loads(proposal_path.read_bytes())
for reference in proposal['all_private_preexecution_files_and_preserved_originals']:
    actual = binding(Path(reference['path']))
    assert actual['bytes'] == reference['bytes'] and actual['sha256'] == reference['sha256']
proof = json.loads((attempt / 'consumer-proof.json').read_bytes())
cleanup = json.loads((attempt / 'execution-cleanup-receipt.json').read_bytes())
exit_data = json.loads((base / 'original-one-actual-current618-v5-gateway-exit.json').read_bytes())
assert exit_data['exit_code'] == 0 and proof['status'] == cleanup['status'] == 'passed'
assert proof['cli_version'] == '1.0.3' and len(proof['members']) == 202 and proof['skips'] == 0
assert proof['input_admission']['tracked_payload_source_matches'] == 215
assert proof['input_admission']['record_entries'] == 221 and proof['input_admission']['record_verified_entries'] == 220
for field in ['wrapper_reaped', 'descendant_snapshot_complete', 'descendant_reap_complete', 'temporary_removed']:
    assert cleanup[field] is True
for field in ['observed_live_children', 'observed_zombie_children', 'cleanup_errors']:
    assert cleanup[field] == []
assert binding(attempt / 'installed-inventory-raw.json')['sha256'] == proof['inventory_sha256']
assert binding(attempt / 'pip-install-report.json')['sha256'] == proof['pip_report_sha256']
evidence = [binding(p) for p in sorted(attempt.iterdir()) if p.is_file()]
for filename in ['root-one-actual-current618-v5-execution-authorization.json', 'original-one-actual-current618-v5-gateway.log', 'original-one-actual-current618-v5-gateway-exit.json', 'root-current618-consumer-v5-postexecution-harness-readback.json', 'OWNERFINAL-original-current618-consumer-gateway-failure.json']:
    evidence.append(binding(base / filename))
review = Path('/workspace/engineering/pr221-current618-linux-consumer-independent-preexecution-review/OWNERFINAL-independent-frozen-v5-preexecution-review-GO.json')
assert binding(review)['sha256'] == 'e319a803881eb5f79755f5767d8eee9b04c4a5cb03ed75386537f8f6c7ad33e7'
data = {'status': 'OWNERFINAL_CURRENT618_ONE_INSTALLED_LINUX_CP312_CONSUMER_PASS_INDEPENDENT_ACTUAL_REVIEW_REQUIRED',
 'captured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'proposal': binding(proposal_path), 'independent_preexecution_GO': binding(review),
 'runner': proposal['runner'], 'input_gate': proposal['input_gate'], 'input_manifest': proposal['input_manifest'],
 'case_count': 1, 'skips': 0, 'gateway_exit': 0, 'cli_version': proof['cli_version'],
 'installed_python_members': 202, 'runtime_wheel': proof['runtime_wheel'],
 'input_admission': proof['input_admission'], 'producer': proof['producer'],
 'public_dependencies': proof['public_dependencies'], 'cleanup': cleanup,
 'harness1433_preserved_pre_post': True, 'all153_preexecution_references_preserved': True,
 'original_failed_v4_gateway': '6f29ccd4b905b0036e6347aac23c12bda82cb6a719a1e7da0008eec951c0e773; failed before worker/install/cleanup; remains FAIL',
 'execution_count_disposition': 'Two current618 gateway authorizations: first v4 refused before consumer worker, second independently reviewed isolated v5 ran exactly one installed consumer. No automatic retry.',
 'installed_tree_observation': 'Retained actual in-worker measurements; owned temporary tree removed as designed. Independent review may reread measurements and original wheel but cannot freshly inspect removed installed files.',
 'evidence': evidence, 'limits': proof['limits'],
 'separate_full_distribution_integrity': '38ec59efeccbdb9b17bd308bc3aee1143b0d50f6c9678b35cfb7152262cf412e: seven distributions integrity only; not other consumers or Windows content',
 'remaining_HOLD': ['Required OAuth inputs EMPTY and source/content authority unresolved', 'Windows173Python+5text CRLF and generatedstatic semantic equivalence NOT_ESTABLISHED; historical cause UNKNOWN', 'No other platform/cp313 consumer, service/browser/ChatGPT/provider/native/private acceptance', 'No Runtime tag/Twine/upload/publication/release/PR221integration/retainedissueclosure'],
 'documentation_improvement': 'Exact accepted fb9 selector-directory and5f08 independent provenance lessons reused; no cosmetic delta', 'upstream_disposition': 'none'}
out = base / 'OWNERFINAL-current618-one-installed-Linux-consumer-checkpoint.json'
with out.open('x') as stream:
    json.dump(data, stream, indent=2); stream.write('\n')
print(json.dumps(binding(out)))
