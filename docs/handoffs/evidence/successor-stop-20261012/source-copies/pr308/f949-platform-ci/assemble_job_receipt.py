import hashlib
import json
import sys
from pathlib import Path

job_id = int(sys.argv[1])
root = Path(__file__).resolve().parent
extraction_path = root / f"job-{job_id}-log-extraction-receipt.json"
extraction = json.loads(extraction_path.read_text())
job_path = root / f"job-{job_id}-terminal-rest.json"
job = json.loads(job_path.read_text())
producer_path = root / "producer-d663b19f-git-commit.json"
producer = json.loads(producer_path.read_text())
assert job['id'] == job_id and job['run_id'] == 38211281631
assert job['head_sha'] == 'f949bef2eeab518ffd34d9e69955938a007f8922'
assert job['status'] == 'completed'
assert extraction['producer_sha_candidates'] == [producer['sha']]
assert producer['tree']['sha'] == 'ce5a94a37f108438daa9d2d283ab575b1000ce99'
assert [p['sha'] for p in producer['parents']] == [
    '48eeaf171e695d9b8ac140ea53239eaeb6eff331',
    'f949bef2eeab518ffd34d9e69955938a007f8922',
]

def identity(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

receipt = {
    'schema': 1,
    'run': job['run_id'],
    'job': job_id,
    'platform_job_name': job['name'],
    'status': job['status'],
    'conclusion': job['conclusion'],
    'started_at': job['started_at'],
    'completed_at': job['completed_at'],
    'head_sha': job['head_sha'],
    'source_producer': {
        'checkout_commit': producer['sha'],
        'complete_git_tree': producer['tree']['sha'],
        'matches_reviewed_f949_tree': True,
        'ordered_parents': [p['sha'] for p in producer['parents']],
        'metadata': identity(producer_path),
        'checkout_log_proof': extraction['producer_checkout_lines'],
    },
    'steps': job['steps'],
    'suite_summaries': extraction['suite_summaries'],
    'named_test_events': extraction['named_test_events'],
    'log_identity': {k: extraction[k] for k in ['decoded_log', 'decoded_log_bytes', 'decoded_log_sha256', 'leading_utf8_bom', 'crlf_count', 'lf_count']},
    'completed_log_fetch_calls': 1,
    'log_scope': extraction['retrieval'],
    'terminal_rest': identity(job_path),
    'extraction_receipt': identity(extraction_path),
    'native_baseline_attempts': 0,
    'optional_rcc_18_19_5_or_727_candidate_launched': False,
    'lease_queries_or_writes': False,
    'source_or_workflow_changes_by_watch_lane': False,
    'ci_rerun_or_cancel_by_watch_lane': False,
    'release_or_rcc_publication_authority': 'unchanged HOLD; general platform CI does not qualify admitted RCC native baseline',
    'historical_0546_macos_provider_failure_cause': 'UNKNOWN; later passing test does not recover discarded typed diagnostic',
    'upstream_disposition': 'none',
}
path = root / f"job-{job_id}-safe-receipt.json"
assert not path.exists(), 'Never overwrite retained safe receipts'
path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(identity(path)))
