"""Bounded selected-artifact export; no credentials or trust-policy changes."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time

root = Path(__file__).parent / 'provider-local'
root.mkdir(exist_ok=True)
old_home = Path('/workspace/327-probes/a53-claimed/compiler/robocorp')
digest = 'ab46f17f4b1ec8d620a3111ad103eff36f78515df5b4db88d1739f5b1e0a6a24'
rcc = Path('/workspace/actions-cloud/bin/rcc')
archive = root / 'environment-ab46f17f.zip'
receipt = root / 'export.json'
floor = 10 * 1024**3
cap = 256 * 1024**2
assert not archive.exists() and not receipt.exists()
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()
assert sha(rcc) == '7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
paths = [old_home / f'artifacts/v1/{store}/manifests/sha256/ab/46/{digest}' for store in ('content', 'provider')]
paths += sorted((old_home / f'artifacts/v1/trust/sha256/{digest}').iterdir())
paths += [old_home.parent / 'prepared.json']
before = {str(p): sha(p) for p in paths}
free_before = shutil.disk_usage(root).free
assert free_before > floor + 2*cap
argv = [str(rcc), 'env', 'export', '--artifact', 'sha256:' + digest, '--provider', 'local', '--output', str(archive)]
env = os.environ.copy()
env['ROBOCORP_HOME'] = str(old_home)
def limit():
    resource.setrlimit(resource.RLIMIT_FSIZE, (cap, cap))
started = time.monotonic()
reason = None
with (root / 'export.log').open('xb') as log:
    process = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT, preexec_fn=limit)
    try:
        while process.poll() is None:
            if shutil.disk_usage(root).free < floor + cap:
                reason = 'FREE_SPACE_GUARD'
                process.terminate()
                break
            if time.monotonic() - started > 90:
                reason = 'TIMEOUT'
                process.terminate()
                break
            time.sleep(.05)
        try:
            status = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            status = process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
after = {str(p): sha(p) for p in paths}
out = {'argv':argv,'command_exit':status,'guard':reason,'source_immutable_hashes_before':before,'source_immutable_hashes_after':after,'source_immutable_unchanged':before == after,'free_before':free_before,'free_after':shutil.disk_usage(root).free,'elapsed_seconds':round(time.monotonic()-started,2),'artifact_digest':'sha256:'+digest,'archive_bytes':archive.stat().st_size if archive.exists() else None,'archive_sha256':sha(archive) if archive.exists() else None,'policy_change':False,'qualification':'selected RCC artifact export only, not coordinated Runtime restore'}
receipt.write_text(json.dumps(out, indent=2)+'\n')
assert before == after
assert status == 0 and reason is None and archive.is_file() and archive.stat().st_size > 0, out
print(json.dumps({k:out[k] for k in ('command_exit','archive_bytes','archive_sha256','source_immutable_unchanged','qualification')}))
