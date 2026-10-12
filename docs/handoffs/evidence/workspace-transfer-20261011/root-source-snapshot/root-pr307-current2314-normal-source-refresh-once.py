import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/workspace/engineering/root-pr307-current2314-normal-source-refresh-once')
ROOT.mkdir(mode=0o700)
WORK = '/workspace/engineering/pr307'
HEAD = '2314aea95795fbc1372a6f7b0b7b298b7cf124c3'
OLD = '87e412f89b201c697d3e6bd4bd34031cdbd14df3'
BASE = 'e2c81adce7858d5a952991ba9a8b7f72e902038a'
BRANCH = 'fix/runtime-release-changelog-selection-20261010'
review = Path('/workspace/engineering/pr307-current2314-actual-LIGHT-independent-review/OWNERFINAL-independent-original-current2314-LIGHT-and-normal-draft-push-gate-review.json')
assert hashlib.sha256(review.read_bytes()).hexdigest() == 'f602a973a97f194449996cae53a2ab5f5d38b8b76378fe9d871dfb8fd6f38d03'

def save(name, data, mode=0o600):
    content = data if isinstance(data, bytes) else json.dumps(data, indent=2, sort_keys=True).encode() + b'\n'
    fd = os.open(ROOT / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, 'wb') as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    return hashlib.sha256(content).hexdigest()

def run(name, argv):
    p = subprocess.run(argv, cwd=WORK, capture_output=True, timeout=120)
    save(name + '.stdout.private', p.stdout)
    save(name + '.stderr.private', p.stderr)
    assert p.returncode == 0, (name, p.returncode)
    return p.stdout

assert run('source-clean', ['git', 'status', '--porcelain=v1']) == b''
assert run('source-head', ['git', 'rev-parse', 'HEAD']).decode().strip() == HEAD
refs = run('before-refs', ['git', 'ls-remote', 'origin', 'refs/heads/' + BRANCH, 'refs/heads/integration/community-release-20261008']).decode()
assert OLD + '\trefs/heads/' + BRANCH in refs
assert BASE + '\trefs/heads/integration/community-release-20261008' in refs
pr = json.loads(run('before-pr', ['gh', 'api', 'repos/joshyorko/actions/pulls/307']))
assert pr['head']['sha'] == OLD and pr['state'] == 'open'
body = ('Current engineering source refresh: ordinary merge of accepted integration `e2c81adc` into the existing branch; new source `2314aea9`, tree `2987ed3a`. The OAuth build acquisition guard and changelog selection are preserved.\n\n'
        'Independent current LIGHT evidence: Toolkit 179 PASS, guard 41 PASS, configured static/type checks, workflow generation and a controlled real Invoke acquisition success/failure boundary passed. The controlled OAuth pair is synthetic structural evidence, not approved provider content. Local complete Runtime suite is NOT RUN for this union because TMP capacity is below its 1.2 GB admission floor. Fresh exact-source hosted CI is required; merge, authoritative OAuth acquisition, Runtime publication and RCC native qualification remain pending. Production RCC remains v18.19.3.\n\n'
        '<details><summary>Preserved prior PR description and evidence</summary>\n\n' + pr['body'] + '\n\n</details>\n')
save('body.private.md', body.encode())
save('body-payload.private.json', {'body': body})
edited = json.loads(run('body-update', ['gh', 'api', '--method', 'PATCH', 'repos/joshyorko/actions/pulls/307', '--input', str(ROOT / 'body-payload.private.json')]))
assert edited['body'] == body
run('one-normal-push', ['git', 'push', 'origin', 'HEAD:refs/heads/' + BRANCH])
after = run('after-refs', ['git', 'ls-remote', 'origin', 'refs/heads/' + BRANCH, 'refs/heads/integration/community-release-20261008']).decode()
assert HEAD + '\trefs/heads/' + BRANCH in after
assert BASE + '\trefs/heads/integration/community-release-20261008' in after
final = {'schema': 'ROOT_ONE_NORMAL_EXISTING_PR307_SOURCE_REFRESH', 'source': HEAD, 'tree': '2987ed3a23e560fb40e13aadbcd6bd613ead3f25', 'old_remote': OLD, 'base': BASE, 'normal_push_returncode': 0, 'remote_ref_verified': True, 'draft_before': pr['draft'], 'draft_changed': False, 'FULL': 'NOT_RUN_LOCAL_CAPACITY', 'merge_release_native': 'HOLD', 'fresh_hosted_CI': 'PENDING', 'old_body_preserved': True, 'independent_review_sha256': hashlib.sha256(review.read_bytes()).hexdigest(), 'time': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'documentation_improvement': 'Existing accepted guard/logging/source-authority guidance reused; no cosmetic duplicate.', 'upstream_disposition': 'none'}
save('OWNERFINAL-root-one-normal-existing-PR307-source-refresh.json', final, 0o400)
print(json.dumps(final))
