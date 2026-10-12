import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

base = Path('/workspace/engineering/pr300-current74-owner-full-contract-adoption')
source = Path('/workspace/engineering/pr300')
owner_path = base / 'OWNERFINAL-current74-reviewed-full-command-adoption-and-execution-HOLD.json'
out = base / 'root-one-reviewed-current74-full-authorization.json'

def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def verify(entry):
    actual = binding(Path(entry['path']))
    assert all(actual[k] == entry[k] for k in ('path', 'bytes', 'sha256')), entry['path']

def git(*args):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(source), *args])

def source_and_references(owner):
    assert git('rev-parse', 'HEAD').decode().strip() == owner['head']
    assert git('rev-parse', 'HEAD^{tree}').decode().strip() == owner['tree']
    assert not git('status', '--porcelain')
    for entry in owner['all_distinct_original_and_LIGHT_reference_bindings_verified']:
        verify(entry)
    verify(owner['preexecution_source1423_Git_FS_body_exec_verified'])
    scope = json.loads(Path(owner['preexecution_source1423_Git_FS_body_exec_verified']['path']).read_bytes())
    assert len(scope['all1423']) == 1423
    for entry in scope['all1423']:
        path = source / entry['path']
        data = os.readlink(path).encode() if entry['mode'] == '120000' else path.read_bytes()
        assert len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256'], entry['path']
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == entry['blob'], entry['path']
        if entry['mode'] != '120000':
            assert bool(path.stat().st_mode & 0o111) == (entry['mode'] == '100755'), entry['path']
    prepared = json.loads(Path(owner['prepared_inputs']['record']['path']).read_bytes())
    for relative, digest in prepared['all30_current_inputs_exact_prepared_Git_bytes'].items():
        assert hashlib.sha256((source / relative).read_bytes()).hexdigest() == digest, relative
    for package, entry in prepared['five_own_environment_configs'].items():
        assert hashlib.sha256((source / package / '.venv/pyvenv.cfg').read_bytes()).hexdigest() == entry['config_sha256']
        assert str((source / package / '.venv/bin/python').resolve()) == entry['python_resolved']
    pinned = owner['prepared_inputs']['ignored_pinned_RCC']
    path = source / pinned['path']
    assert binding(path)['sha256'] == pinned['sha256'] and path.stat().st_size == pinned['bytes']
    assert (path.stat().st_mode & 0o777) == 0o711
    verify(owner['prepared_inputs']['managed_gateway'])

assert not out.exists()
assert binding(owner_path)['sha256'] == '17c61faa68cbdfe2daf6915335cc2a93ccd67328dbdf34c2cb2455963ad35eca'
owner = json.loads(owner_path.read_bytes())
verify(owner['exact_contract'])
assert owner['exact_contract']['sha256'] == '2881ff048c9b97c1c97bf2455c943b1a1cfb0b9fff82a392ac0312ad37ead0a8'
contract = json.loads(Path(owner['exact_contract']['path']).read_bytes())
assert owner['exact_argv'] == contract['argv']
for entry in owner['independent_current74_reviews']:
    verify(entry)
source_and_references(owner)
terminal_path = Path('/workspace/engineering/pr312-actual309-refresh/current-full-terminal.json')
terminal = json.loads(terminal_path.read_bytes())
assert any(v == 0 for k, v in terminal.items() if k in ('exit_code', 'returncode', 'return_code'))
capacity_path = Path(os.environ['CURRENT74_CAPACITY_REVIEW_PATH'])
assert binding(capacity_path)['sha256'] == os.environ['CURRENT74_CAPACITY_REVIEW_SHA256']
space = os.statvfs(source)
available = space.f_bavail * space.f_frsize
assert available >= 1_200_000_000, available
authorization = {'status': 'ROOT_DISTINCT_RELEASE_ONE_EXACT_CURRENT74_REVIEWED_FULL',
                 'owner': binding(owner_path), 'contract': owner['exact_contract'],
                 'head': owner['head'], 'tree': owner['tree'], 'target': owner['target'],
                 'capacity_review': binding(capacity_path), 'prior312_terminal': binding(terminal_path),
                 'available_bytes': available, 'complete1423_and_original_LIGHT_inputs_reverified': True,
                 'execution': 'Exactly one reviewed Runtime full command; explicit two workers and 600s TERM plus 10s kill-after; no retry',
                 'holds': 'Actual acceptance, independent source final, normal push, hosted CI and whole-release remain separate'}
with out.open('x') as stream:
    json.dump(authorization, stream, indent=2)
    stream.write('\n')
out.chmod(0o600)
print(json.dumps({'authorization': binding(out)}), flush=True)
log = base / 'current74-one-reviewed-configured-full.log'
started = time.monotonic()
with log.open('xb') as stream:
    log.chmod(0o600)
    process = subprocess.run(contract['argv'], cwd=contract['cwd'], stdout=stream, stderr=subprocess.STDOUT)
elapsed = time.monotonic() - started
exit_receipt = {'status': 'ONE_ACTUAL_CURRENT74_FULL_TERMINAL', 'returncode': process.returncode,
                'elapsed_seconds': elapsed, 'log': binding(log), 'head': owner['head'], 'tree': owner['tree']}
path = base / 'current74-one-reviewed-configured-full-terminal.json'
with path.open('x') as stream:
    json.dump(exit_receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps(exit_receipt), flush=True)
source_and_references(owner)
post = base / 'root-current74-postfull-complete-source-and-reference-readback.json'
with post.open('x') as stream:
    json.dump({'status': 'EXACT_CURRENT74_POSTFULL_SOURCE_AND_RETAINED_BINDINGS', 'head': owner['head'],
               'tree': owner['tree'], 'tracked_count': 1423, 'terminal': binding(path),
               'all_original_and_LIGHT_refs_inputs_modes_exact': True}, stream, indent=2)
    stream.write('\n')
assert process.returncode == 0, 'Full gate failed; no retry authorized'
