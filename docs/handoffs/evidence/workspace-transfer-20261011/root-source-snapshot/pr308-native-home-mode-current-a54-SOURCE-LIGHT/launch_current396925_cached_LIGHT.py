import hashlib,json,os,subprocess,sys,time
from pathlib import Path
R=Path('/workspace/engineering/pr308');O=Path(__file__).parent;cached=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python')
assert sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE')
os.umask(0o077);log=O/'current396925-cached-LIGHT-original.private.log';assert not log.exists();records=[];first_error=None
with log.open('xb') as output:
 try:
  for name,argv,budget in [('before',[str(cached),str(O/'read_only_current396925_guard.py'),'before'],90),('LIGHT',[str(cached),str(O/'run_current396925_cached_LIGHT.py')],480)]:
   start=time.monotonic();cp=subprocess.run(['timeout','--signal=TERM','--kill-after=10s',str(budget)+'s',*argv],cwd=R,stdout=output,stderr=subprocess.STDOUT);records.append({'stage':name,'argv':argv,'TERM_seconds':budget,'returncode':cp.returncode,'seconds':time.monotonic()-start})
   if cp.returncode:raise RuntimeError(name+'_FAILED')
 except BaseException as error:first_error=type(error).__name__
 finally:
  start=time.monotonic();cp=subprocess.run(['timeout','--signal=TERM','--kill-after=10s','90s',str(cached),str(O/'read_only_current396925_guard.py'),'after'],cwd=R,stdout=output,stderr=subprocess.STDOUT);records.append({'stage':'after-always','TERM_seconds':90,'returncode':cp.returncode,'seconds':time.monotonic()-start})
result={'status':'PASS' if first_error is None and all(row['returncode']==0 for row in records) else 'FAIL/HOLD','source':'396925cb3d6527af1768b7f5333f9653c005fc55','tree':'84f850f0d4e08b21afcd8220413ce94322370acf','records':records,'primary_error_class':first_error,'log':{'path':str(log),'bytes':log.stat().st_size,'sha256':hashlib.sha256(log.read_bytes()).hexdigest()},'full_or_native_or_installer':'NOT_RUN'}
p=O/'current396925-cached-LIGHT-terminal.json';p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');p.chmod(0o600);print(json.dumps(result),flush=True);raise SystemExit(0 if result['status']=='PASS' else 10)
