import hashlib,json,os,shutil,signal,subprocess,time
from pathlib import Path
root=Path('/workspace/actions-recovery-327/capability-bundle-native');e=root/'evidence'
floor=768*1024*1024;budget=800*1024*1024
free=shutil.disk_usage(root).free
pre={'free_bytes':free,'floor_bytes':floor,'incremental_budget_bytes':budget,'fits':free>=floor+budget,'reason':'serial existing no-build prepared artifact; only one capability view kept,700MiB view+100MiB transient/evidence allowance'}
(e/'preflight.json').write_text(json.dumps(pre,indent=2))
if not pre['fits']:raise SystemExit('budget blocked before environment use')
with (e/'stdout.log').open('wb') as log:
    p=subprocess.Popen(['/workspace/actions/action_server/.venv/bin/python',str(root/'qualify.py')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    samples=[];stopped=False
    while p.poll() is None:
        free=shutil.disk_usage(root).free;samples.append({'time':time.time(),'free_bytes':free})
        if free<floor:
            stopped=True;os.killpg(p.pid,signal.SIGTERM)
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
            break
        time.sleep(1)
    (e/'monitor.json').write_text(json.dumps({'returncode':p.wait(),'disk_floor_stop':stopped,'min_free':min(s['free_bytes'] for s in samples),'samples':samples},indent=2))
raise SystemExit(p.returncode)
