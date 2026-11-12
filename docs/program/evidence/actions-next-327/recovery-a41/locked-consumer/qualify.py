import hashlib,importlib.util,json,os,shutil,signal,subprocess,time,tomllib,traceback
from pathlib import Path
base=Path('/workspace/actions-327-a41');out=base/'locked-consumer-evidence';consumer=base/'locked-consumer'
inputs=json.loads((out/'inputs.json').read_text())
assert shutil.disk_usage(base).free>=5.5*1024**3
checks={};start=time.monotonic()
module_path=out/'qualifier-snapshot.py'
spec=importlib.util.spec_from_file_location('qualify_consumer_inventory_327',module_path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
try:
 value=module.qualify(json.loads((out/'pip-inspect.json').read_text()),tomllib.loads(Path(inputs['frozen_lock']).read_text()),'1.1.0a41',[])
 (out/'dependency-closure.json').write_text(json.dumps(value,indent=2)+'\n')
 checks['dependency_closure']={'status':'passed','resolved_count':len(value['resolved']),'extras':[]}
except BaseException as exc:
 checks['dependency_closure']={'status':'failed','type':type(exc).__name__,'reason':str(exc)}
 (out/'dependency-closure-failure.txt').write_text(traceback.format_exc())
def run(name,args,timeout=60):
 log=out/(name+'.log');env=dict(os.environ,PYTHONNOUSERSITE='1');env.pop('PYTHONPATH',None)
 with log.open('wb') as stream:
  process=subprocess.Popen(args,cwd=out,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
  deadline=time.monotonic()+timeout;reason=None
  while process.poll() is None:
   if shutil.disk_usage(base).free<5.5*1024**3:reason='disk floor'
   if sum(p.stat().st_size for p in out.glob('*.log'))>12*1024**2:reason='log bound'
   if time.monotonic()>deadline:reason='timeout'
   if reason:
    os.killpg(process.pid,signal.SIGTERM)
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
    break
   time.sleep(.1)
 checks[name]={'status':'passed' if process.returncode==0 and not reason else 'failed','exit_code':process.returncode,'reason':reason}
run('cli-version',[str(consumer/'bin/action-server'),'--version'])
run('installed-probe',[str(consumer/'bin/python'),'-I',str(out/'probe-installed.py')])
receipt={'scope':'dependency closure and installed identity/basic MCP compatibility; not vendor-independent or full Canvas acceptance','source_revision':inputs['source_revision'],'expected_runtime':'1.1.0a41','selected_runtime_extras':[],'qualifier_sha256':hashlib.sha256(module_path.read_bytes()).hexdigest(),'checks':checks,'elapsed_seconds':round(time.monotonic()-start,3)}
(out/'qualification.json').write_text(json.dumps(receipt,indent=2)+'\n')
raws=['inputs.json','install-report.json','pip-inspect.json','pip-check.txt','install-supervisor.json','qualifier-snapshot.py','dependency-closure.json','installed-bytes.json','mcp-initialize.json','qualification.json','cli-version.log','installed-probe.log']
(out/'SHA256SUMS.json').write_text(json.dumps({name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in raws if (out/name).exists()},indent=2)+'\n')
print(json.dumps(receipt,indent=2))
if any(v['status']!='passed' for v in checks.values()):raise SystemExit(1)
