"""Temporarily isolate the owned original cache and restore it in finally."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

base = Path(__file__).parent
old = Path('/workspace/327-probes/a53-claimed/compiler/robocorp')
new = base / 'acquire/robocorp'
hidden = old.with_name('robocorp-a59-isolated-' + uuid.uuid4().hex)
receipt_path = base / 'cold-exec.json'
intent_path = base / 'cache-isolation-intent.json'
assert not receipt_path.exists() and not intent_path.exists() and old.is_dir() and not old.is_symlink()
acquire = json.loads((base/'acquire.json').read_text())
assert acquire['command_exit']==0 and acquire['same_policy_and_artifact'] and acquire['copied_trust_unchanged']
assert acquire['new_home']==str(new)
# Refuse if an active process holds a path in this specific owned cache.
users=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdecimal(): continue
    if int(proc.name)==os.getpid(): continue
    for path in [proc/'cwd',proc/'exe']:
        try:
            value=os.readlink(path)
            if value==str(old) or value.startswith(str(old)+'/'): users.append(int(proc.name))
        except (FileNotFoundError,PermissionError,ProcessLookupError): pass
    try:
        for path in (proc/'fd').iterdir():
            try:
                value=os.readlink(path)
                if value==str(old) or value.startswith(str(old)+'/'): users.append(int(proc.name))
            except (FileNotFoundError,PermissionError,ProcessLookupError): pass
        if str(old)+'/' in (proc/'maps').read_text(): users.append(int(proc.name))
    except (FileNotFoundError,PermissionError,ProcessLookupError): pass
assert not users, sorted(set(users))
identity={'device':old.stat().st_dev,'inode':old.stat().st_ino}
prepared=old.parent/'prepared.json'
original_prepared=hashlib.sha256(prepared.read_bytes()).hexdigest()
intent={'original':str(old),'temporarily_isolated':str(hidden),'identity':identity,'prepared_sha256':original_prepared,'recovery':'If interrupted before final receipt, rename isolated directory back only after checking device/inode and original path absence.'}
intent_path.write_text(json.dumps(intent,indent=2)+'\n')
def interrupted(number, frame): raise InterruptedError('supervisor signal '+str(number))
signal.signal(signal.SIGTERM,interrupted)
signal.signal(signal.SIGINT,interrupted)
argv=['/workspace/actions-cloud/bin/rcc','env','exec','--artifact',acquire['artifact_digest'],'--provider','local','--permissive-local','--trust-carrier',str(base/'acquire/trust'),'--trust-carrier-type','filesystem','--no-build','--inherit-streams','--receipt-file',str(base/'rcc-exec-receipt.json'),'--','python','-I',str(base/'verify_core.py')]
env=os.environ.copy();env['ROBOCORP_HOME']=str(new)
started=time.monotonic();process=None;status=None
result={'qualification':'selected RCC artifact cold execution with original owned cache path absent; not coordinated Runtime restore','argv':argv,'original_identity':identity,'old_cache_users_before':sorted(set(users)),'original_prepared_sha256':original_prepared}
try:
    old.rename(hidden)
    assert not old.exists() and hidden.stat().st_ino==identity['inode']
    with (base/'cold-exec.log').open('xb') as log:
        process=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
        try: status=process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=5)
            raise
    assert not old.exists()
    result['command_exit']=status
    assert status==0
finally:
    if process is not None and process.poll() is None:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill();process.wait(timeout=5)
    if hidden.exists():
        assert not old.exists(), 'refuse overwriting unexpectedly recreated original cache'
        assert hidden.stat().st_dev==identity['device'] and hidden.stat().st_ino==identity['inode']
        hidden.rename(old)
    result['original_cache_restored']=old.is_dir() and old.stat().st_ino==identity['inode']
    result['original_prepared_unchanged']=hashlib.sha256(prepared.read_bytes()).hexdigest()==original_prepared
    result['elapsed_seconds']=round(time.monotonic()-started,2)
    result['status']='PASS' if status==0 and result['original_cache_restored'] and result['original_prepared_unchanged'] else 'FAILED'
    receipt_path.write_text(json.dumps(result,indent=2)+'\n')
assert result['status']=='PASS'
print(json.dumps(result,sort_keys=True))
