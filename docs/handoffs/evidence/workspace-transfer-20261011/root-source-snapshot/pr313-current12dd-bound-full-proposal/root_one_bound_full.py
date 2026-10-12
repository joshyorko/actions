"""Root-only bound SOURCEFULL orchestration; importing runs no gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

HERE = Path(__file__).parent
PROPOSAL = HERE / 'OWNERFINAL-current12dd-root-bound-FULL-preexecution.json'

def bind(path):
    path = Path(path)
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def write_new(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def run_phase(argv, cwd, log):
    result = {'returncode': None, 'exception_category': None}
    start = time.monotonic()
    try:
        fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            done = subprocess.run(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, check=False)
            result['returncode'] = done.returncode
    except BaseException as error:
        result['exception_category'] = type(error).__name__
    result['elapsed_seconds'] = time.monotonic() - start
    result['original_output'] = bind(log) if log.exists() else None
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-root-authorized', action='store_true')
    args = parser.parse_args()
    if not args.execute_root_authorized:
        parser.error('Distinct root authorization required')
    proposal = json.loads(PROPOSAL.read_bytes())
    owned = Path(proposal['owned'])
    assert owned.is_dir() and stat.S_IMODE(owned.stat().st_mode) == 0o700
    authpath = owned / 'root-one-current12dd-full-authorization.json'
    assert stat.S_IMODE(authpath.stat().st_mode) == 0o600
    auth = json.loads(authpath.read_bytes())
    assert auth['head'] == proposal['head'] and auth['tree'] == proposal['tree']
    assert auth['attempts'] == 1 and auth['serialized_heavy_slot_clearance'] is True
    assert auth['bound_full_proposal'] == bind(PROPOSAL)
    assert auth['full_proposal'] == proposal['original_proposal']
    assert auth['source_LIGHT'] == proposal['source_LIGHT']
    review = auth['independent_preexecution_review']
    assert bind(review['path']) == {k: review[k] for k in ('path', 'bytes', 'sha256')}
    assert review['decision'] == json.loads(Path(review['path']).read_bytes())['decision']
    assert review['decision'] == 'GO_CURRENT12DD_BOUND_FULL_PREEXECUTION'
    assert os.environ['PR313_CURRENT12DD_DISTINCT_ROOT_RELEASE_PATH'] == str(authpath)
    assert os.environ['PR313_CURRENT12DD_DISTINCT_ROOT_RELEASE_SHA256'] == bind(authpath)['sha256']
    assert os.environ['PR313_CURRENT12DD_SERIALIZED_HEAVY_SLOT'] == 'root-pr313-current12dd-one-configured-full'
    for row in proposal['bindings']:
        assert bind(row['path']) == row
    primary = run_phase(proposal['primary_argv'], proposal['cwd'], owned / 'one-current12dd-configured-source-full.private.log')
    # Preserve original primary terminal before the independently bounded post guard.
    seal_error = None
    try:
        write_new(owned / 'primary-terminal-before-postguard.json', primary)
    except BaseException as error:
        seal_error = type(error).__name__
    post = run_phase(proposal['post_argv'], proposal['cwd'], owned / 'one-current12dd-postguard.private.log')
    write_new(owned / 'postguard-terminal-separate.json', post)
    rc = 0 if primary['returncode'] == 0 and post['returncode'] == 0 and seal_error is None else 10
    write_new(owned / 'one-current12dd-configured-source-full-terminal.json', {
        'head': proposal['head'], 'tree': proposal['tree'], 'attempts': 1,
        'primary': primary, 'primary_seal_error': seal_error, 'postguard': post,
        'overall_returncode': rc, 'cleanup_inference': 'UNKNOWN_NO_CLEANUP_CLAIM',
    })
    return rc

if __name__ == '__main__':
    raise SystemExit(main())
