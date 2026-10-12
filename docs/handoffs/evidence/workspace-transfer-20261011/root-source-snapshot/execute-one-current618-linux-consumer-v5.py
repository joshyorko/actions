import argparse
import datetime
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--review', required=True)
parser.add_argument('--review-sha256', required=True)
args = parser.parse_args()
os.umask(0o077)
base = Path('/workspace/engineering/pr221-current618-linux-consumer-preflight')
proposal_path = base / 'OWNERFINAL-current618-isolated-Linux-consumer-preexecution-proposal-v5-successor-v2.json'
def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
assert binding(proposal_path)['sha256'] == '38d07ed81d6ce129a7786325b7447c8e2bfb8b134c1f02c78fd2c6788b0ff027'
proposal = json.loads(proposal_path.read_bytes())
review_path = Path(args.review)
assert binding(review_path)['sha256'] == args.review_sha256
review = json.loads(review_path.read_bytes())
assert 'GO' in str(review.get('status', review.get('verdict', review.get('disposition', '')))).upper()
for key in ['runner', 'input_gate', 'input_manifest', 'artifact_data_ownerfinal', 'original_archive', 'selected_cp312_wheel']:
    row = proposal[key]
    assert binding(Path(row['path'])) == row, key
for row in proposal['helpers_current_Git618_and_immutable_snapshots_exact'].values():
    assert binding(Path(row['path'])) == row
gateway = proposal['planned_ONE_actual_gateway']
checkout = Path(gateway['cwd'])
def git(*argv):
    return subprocess.check_output(['git', '-C', str(checkout), *argv])
assert git('rev-parse', 'HEAD').decode().strip() == proposal['harness']['head']
assert git('rev-parse', 'HEAD^{tree}').decode().strip() == proposal['harness']['tree']
assert not git('status', '--porcelain', '--untracked-files=normal').strip()
assert git('ls-remote', 'origin', 'refs/heads/integration/community-release-20261008').decode().split()[0] == proposal['actual_integration']['sha']
expected = json.loads(Path(proposal['harness']['complete_prehash']['path']).read_bytes())
def harness_readback():
    paths = [x.decode('utf-8') for x in git('ls-files', '-z').split(b'\0') if x]
    assert len(paths) == expected['count'] == 1433
    hashes = {p: hashlib.sha256((checkout / p).read_bytes()).hexdigest() for p in paths}
    modes = {p: bool((checkout / p).stat().st_mode & stat.S_IXUSR) for p in paths}
    assert hashes == expected['tracked_sha256']
    assert modes == expected['tracked_executable_bits']
    assert not git('status', '--porcelain', '--untracked-files=normal').strip()
    return {'head': git('rev-parse', 'HEAD').decode().strip(), 'tree': git('rev-parse', 'HEAD^{tree}').decode().strip(), 'count': len(paths), 'tracked_sha256': hashes, 'tracked_executable_bits': modes}
pre = harness_readback()
assert not Path(gateway['attempt_root']).exists()
capacity = {p: shutil.disk_usage(p).free for p in ['/workspace', '/tmp', '/dev/shm']}
assert capacity['/workspace'] >= 1_200_000_000
# Coordinator releases this exact invocation only after SOURCE308 full is terminal
# and both writers acknowledge that no other local full/actual gate is active.
authorization = {'status': 'ROOT_ONE_CURRENT618_V5_LINUX_CP312_CONSUMER_AUTHORIZED',
 'time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'proposal': binding(proposal_path), 'independent_GO': binding(review_path),
 'command': gateway, 'fresh_capacity': capacity,
 'serialization': 'SOURCE308 full terminal; writer A fixture prep terminal; writer B EOL prepared own environments, service-free lights only and full held; no other actual consumer',
 'actual_attempts_authorized': 1, 'attempt_suffix_disposition': 'suffix3 is frozen v5 namespace; original v4 gateway exit10 failed before attempt/worker/install and remains preserved; new isolated inputs have independent review',
 'failure_policy': 'Preserve original failure and strict cleanup; no automatic retry',
 'remaining_HOLDs': proposal['remaining_HOLDs'], 'pre_harness': pre}
authorization_path = base / 'root-one-actual-current618-v5-execution-authorization.json'
with authorization_path.open('x') as stream:
    json.dump(authorization, stream, indent=2); stream.write('\n')
log_path = base / 'original-one-actual-current618-v5-gateway.log'
command = 'source /workspace/actions-cloud/activate.sh\nexec ' + shlex.join(gateway['argv'])
with log_path.open('xb') as log:
    result = subprocess.run(['bash', '-lc', command], cwd=checkout, stdout=log, stderr=subprocess.STDOUT)
exit_path = base / 'original-one-actual-current618-v5-gateway-exit.json'
exit_data = {'exit_code': result.returncode, 'authorization': binding(authorization_path), 'original_log': binding(log_path), 'time': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'automatic_retry': False}
with exit_path.open('x') as stream:
    json.dump(exit_data, stream, indent=2); stream.write('\n')
post_path = base / 'root-current618-consumer-v5-postexecution-harness-readback.json'
post = harness_readback()
assert pre == post
with post_path.open('x') as stream:
    json.dump(post, stream, indent=2); stream.write('\n')
print(json.dumps({'status': 'TERMINAL', 'exit_code': result.returncode, 'exit_receipt': binding(exit_path), 'post_harness': binding(post_path)}))
raise SystemExit(result.returncode)
