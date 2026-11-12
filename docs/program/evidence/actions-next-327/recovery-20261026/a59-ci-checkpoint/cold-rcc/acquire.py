"""Acquire one exported local fixture with its unchanged trust carrier."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time

base = Path(__file__).parent
target = base / 'acquire'
target.mkdir(exist_ok=False)
home = target / 'robocorp'
old = Path('/workspace/327-probes/a53-claimed/compiler/robocorp')
digest = 'ab46f17f4b1ec8d620a3111ad103eff36f78515df5b4db88d1739f5b1e0a6a24'
archive = base / 'provider-local/environment-ab46f17f.zip'
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda: stream.read(1024**2), b''): h.update(b)
    return h.hexdigest()
assert sha(archive) == 'a7877f1451e0bd3ea0b3d27eee771b5a60b10369846f307e24542d8da685d356'
assert not home.exists()
trust = target / 'trust'
source_trust = old / f'artifacts/v1/trust/sha256/{digest}'
destination = trust / 'sha256' / digest
destination.mkdir(parents=True)
trust_before = {}
for path in source_trust.iterdir():
    assert path.is_file() and not path.is_symlink()
    trust_before[path.name] = sha(path)
    shutil.copyfile(path, destination / path.name)
    assert sha(destination / path.name) == trust_before[path.name]
env = os.environ.copy()
env['ROBOCORP_HOME'] = str(home)
argv = ['/workspace/actions-cloud/bin/rcc','env','acquire','--archive',str(archive),'--artifact','sha256:'+digest,'--provider','local','--permissive-local','--trust-carrier',str(trust),'--trust-carrier-type','filesystem','--json']
floor = 10*1024**3
cap = 256*1024**2
free_before = shutil.disk_usage(base).free
assert free_before > floor+2*cap
started = time.monotonic()
reason = None
def limit(): resource.setrlimit(resource.RLIMIT_FSIZE, (cap,cap))
with (target/'acquire.log').open('xb') as log:
    process = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT, preexec_fn=limit)
    try:
        while process.poll() is None:
            if shutil.disk_usage(base).free < floor+cap:
                reason='FREE_SPACE_GUARD';process.terminate();break
            if time.monotonic()-started > 120:
                reason='TIMEOUT';process.terminate();break
            time.sleep(.05)
        try: status=process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill();status=process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill();process.wait(timeout=5)
verification_path=home/f'artifacts/v1/verification/sha256_{digest}.json'
verification=json.loads(verification_path.read_text()) if verification_path.exists() else None
old_verification=json.loads((old/f'artifacts/v1/verification/sha256_{digest}.json').read_text())
policy_fields=('artifactDigest','policyMode','policyRevision','policyDigest','platform','builder','provenanceDigest','sbomDigest','revocationSnapshot')
same_policy=bool(verification) and all(verification.get(k)==old_verification.get(k) for k in policy_fields)
receipt={'command_exit':status,'guard':reason,'argv':argv,'archive_sha256':sha(archive),'artifact_digest':'sha256:'+digest,'new_home':str(home),'old_home':str(old),'old_home_unavailable':False,'trust_hashes':trust_before,'copied_trust_unchanged':all(sha(destination/k)==v==sha(source_trust/k) for k,v in trust_before.items()),'verification':verification,'same_policy_and_artifact':same_policy,'free_before':free_before,'free_after':shutil.disk_usage(base).free,'elapsed_seconds':round(time.monotonic()-started,2),'qualification':'fresh selected RCC artifact acquisition only; original cache still available; not whole Runtime restore'}
(base/'acquire.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert status==0 and reason is None and same_policy and receipt['copied_trust_unchanged'], receipt
print(json.dumps({k:receipt[k] for k in ('command_exit','new_home','same_policy_and_artifact','qualification')}))
