import json,os,shutil,signal,time
from pathlib import Path
import psutil
root=Path('/workspace/actions-recovery-327');suffix='a35-frozen-portable-bounded/tests.xml'
selected=[]
for p in psutil.process_iter(['pid','name','cmdline']):
 if p.info['name']=='pytest' and any(suffix in a for a in (p.info['cmdline'] or [])):selected.append((p.pid,p.create_time()))
assert len(selected)==1,selected
pid,created=selected[0];floor=768*1024*1024
receipt={'pid':pid,'create_time':created,'stop_floor_bytes':floor,'initial_free_bytes':shutil.disk_usage(root).free,'minimum_free_bytes':shutil.disk_usage(root).free,'scope':'current frozen verifier only; graceful interrupt before exhaustion','action':'NONE'}
while True:
 try:
  p=psutil.Process(pid)
  if p.create_time()!=created or p.status()==psutil.STATUS_ZOMBIE:break
 except psutil.NoSuchProcess:break
 free=shutil.disk_usage(root).free;receipt['minimum_free_bytes']=min(free,receipt['minimum_free_bytes'])
 if free<floor:
  p.send_signal(signal.SIGINT);receipt['action']='INTERRUPTED_LOW_SPACE';break
 time.sleep(2)
receipt['final_free_bytes']=shutil.disk_usage(root).free
(root/'evidence/a35-frozen-budget-watch.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
