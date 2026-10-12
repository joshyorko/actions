import hashlib
import json
import os
import stat
import subprocess
import time
from pathlib import Path

os.umask(0o077)
BASE = Path('/workspace/engineering')
out = BASE / 'root-B27-one-existing-tmp-recovery-named-v2'
out.mkdir(mode=0o700)
original = json.loads((BASE / 'root-B27-one-existing-tmp-recovery/OWNERFINAL-root-one-B27-existing-tmp-volume-terminal.json').read_text())
assert original['primary_returncode'] is None and original['error_class'] == 'KeyError'
assert not (BASE / 'root-B27-one-existing-tmp-recovery/original-command-terminal.json').exists()
proposal_path = BASE / 'capacity-recovery-batch27-proposal/OWNERFINAL-batch27-exact-three-completed-existing-tmp-preexecution-proposal-v2.json'
raw = proposal_path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'dabe89c9b8d05c714207c7880b30195baf90c341fd3ecc657b9143545d6d2673'
proposal = json.loads(raw)
review_path = BASE / 'capacity-recovery-batch27-independent-preexecution-review/OWNERFINAL-independent-exact-three-B27-existing-tmp-preexecution-review-v2.json'
assert hashlib.sha256(review_path.read_bytes()).hexdigest() == '80756dfa426e6d176e1fbaf966cef85a4ef50c041727b56a302b58efa7e69588'
records = json.loads((BASE / 'capacity-recovery-batch27-proposal/private-all58-original-archives26-indices-current-SHA-mode-retention.json').read_text())
actual_review = BASE / 'rcc-current-e4ff-control3-actual-independent-review/OWNERFINAL-independent-original-current-e4ff-control3-cache-mode-actual-failure-review.json'
assert hashlib.sha256(actual_review.read_bytes()).hexdigest() == '61506cf064896dc750ccf47450d440170861cef4cf9a5c68060ac3ea3bedf5b1'

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()

def preserve_prior():
    assert len(records['archives']) == 58 and len(records['indices']) == 26
    for row in records['archives'] + records['indices']:
        path = Path(row['archive'] if 'archive' in row else row['path'])
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
        assert oct(stat.S_IMODE(path.stat().st_mode)) == row['mode']
    assert Path('/workspace/actions-cloud/robocorp/temp/563d911e4172f035').exists()
    assert sha('/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-2/OWNERFINAL-one-version-actual-result.json') == 'd4ebd4111e362d3ac3f8dc519d3826ad19c71e1d06dffe7dd959a4ebd2b45ca8'

guard = ['env', '-u', 'PYTHONOPTIMIZE', 'timeout', '--signal=TERM', '--kill-after=10s', '120s',
         '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',
         str(BASE / 'rcc-compatibility-owned-cache-runner-successor-preparation/readonly_current_input_guard_v1.py'),
         '--config', str(BASE / 'rcc-compatibility-current-e4ff-qualified-config-successor/FROZEN-current-e4ff-control3-owned-cache-SOURCE-QUALIFIED-v4.json'),
         '--config-sha256', '1411879501e1ef2bd5aec7fbf9627457aa840badc8e86be980c25b207ee9d5dc',
         '--release', str(BASE / 'root-rcc-current-e4ff-control3-distinct-adoption/root-one-control3-authorization.json'),
         '--release-sha256', '1d86f4fce29fb8afa777059e78a2f2b3ed52d60ec240478d231c238261f730ec',
         '--label', 'control3']
authorization = {'schema': 1, 'status': 'ROOT_ONE_B27_NAMED_METADATA_SUCCESSOR',
                 'proposal_sha256': hashlib.sha256(raw).hexdigest(),
                 'review_sha256': '80756dfa426e6d176e1fbaf966cef85a4ef50c041727b56a302b58efa7e69588',
                 'script_sha256': proposal['script']['sha256'],
                 'names': proposal['names_exact_allowlist'], 'archive_attempts': 1,
                 'original_wrapper_primary_NOT_STARTED': True,
                 'metadata_correction': 'Archive rows use archive; indices use path; failed actual digest from accepted61506 binding.',
                 'serialized': True}
(out / 'root-one-authorization.json').write_text(json.dumps(authorization, sort_keys=True, indent=2) + '\n')
primary = None
error = None
post = None
started = time.monotonic()
try:
    preserve_prior()
    assert sha(proposal['script']['path']) == proposal['script']['sha256']
    with (out / 'original-pre-guard.private.log').open('xb') as log:
        cp = subprocess.run(guard, stdout=log, stderr=subprocess.STDOUT)
    assert cp.returncode == 0
    space = os.statvfs('/tmp')
    assert space.f_bavail * space.f_frsize >= 316187060
    with (out / 'original-one-B27.private.log').open('xb') as log:
        cp = subprocess.run(proposal['root_proposed_exact_argv'], stdout=log, stderr=subprocess.STDOUT)
    primary = cp.returncode
    (out / 'original-command-terminal.json').write_text(json.dumps({'returncode': primary, 'archive_attempts': 1}) + '\n')
except Exception as exc:
    error = type(exc).__name__
    (out / 'original-error.private.txt').write_text(str(exc))
finally:
    try:
        preserve_prior()
        with (out / 'original-post-guard.private.log').open('xb') as log:
            cp = subprocess.run(guard, stdout=log, stderr=subprocess.STDOUT)
        post = cp.returncode
    except Exception as exc:
        post = type(exc).__name__
        (out / 'original-post-error.private.txt').write_text(str(exc))
    available = {}
    for path in ['/workspace', '/tmp', '/dev/shm']:
        space = os.statvfs(path)
        available[path] = space.f_bavail * space.f_frsize
    result = {'schema': 1, 'status': 'PRESERVATION_ONLY_PASS' if primary == 0 and error is None and post == 0 else 'FAIL_HOLD',
              'primary_returncode': primary, 'error_class': error, 'post_guard': post,
              'seconds': time.monotonic() - started, 'available_bytes': available,
              'original_failed_wrapper_retained': True, 'archive_attempts': int(primary is not None),
              'names': proposal['names_exact_allowlist'], 'native_newer_qualification': 'NONE_UNCHANGED'}
    (out / 'OWNERFINAL-root-one-B27-named-metadata-existing-tmp-terminal.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result))
raise SystemExit(0 if result['status'] == 'PRESERVATION_ONLY_PASS' else 1)
