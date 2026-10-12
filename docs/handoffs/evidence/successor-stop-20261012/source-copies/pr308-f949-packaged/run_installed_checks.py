import datetime
import hashlib
import json
from pathlib import Path
import subprocess

root=Path(__file__).parent
consumer=root/'installed-minimum-core-consumer'
wrapper='/workspace/successor-evidence/run-prepared-package.py'
commands=[
    ('installed-inventory',['python','consumer_inventory.py']),
    ('installed-oauth',['python','-m','pytest','-q','test_installed_oauth.py']),
    ('installed-cancellation-admission',['python','-m','pytest','-q','test_async_run_cancellation_admission.py']),
    ('installed-pip-check',['python','-m','pip','check']),
    ('installed-real-template',['python','real_bundled_template.py']),
    ('installed-idle-startup',['python','check_installed_startup.py']),
]
results=[]
for label,args in commands:
    command=['python',wrapper,str(consumer),'poetry','run',*args]
    output=root/(label+'.log')
    with output.open('xb') as stream:
        result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=50)
    data=output.read_bytes()
    results.append({'label':label,'command':command,'exit_code':result.returncode,'bytes':len(data),'output_sha256':hashlib.sha256(data).hexdigest()})
    print(json.dumps({'label':label,'exit_code':result.returncode}),flush=True)
    if result.returncode: break
receipt={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_head':'f949bef2eeab518ffd34d9e69955938a007f8922','source_tree':'ce5a94a37f108438daa9d2d283ab575b1000ce99','artifact':11728534466,'run':38211281718,'results':results,'managed_actions':0,'scope':'installed Linux minimum-Core OAuth, held-executor admission, template, dependency and idle startup only; no managed Action/MCP/native/whole reader/lease qualification'}
(root/'installed-command-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(0 if len(results)==len(commands) and all(r['exit_code']==0 for r in results) else 1)
