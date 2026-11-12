from pathlib import Path
import subprocess,os,json,hashlib,time
base=Path('/workspace/actions-327-a39/installed-combined');out=Path(__file__).parent;frontend=base/'source/action_server/frontend'
node=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin')
env=dict(os.environ,PATH=str(node)+':'+os.environ['PATH'],CI='1')
def snapshot():
 files=[p for d in ['dist','dist-canvas'] for p in (frontend/d).rglob('*') if p.is_file()]
 files += [frontend/'package-lock.json',base/'source/action_server/src/actions/server/_static_contents.py']
 files += list((base/'wheels').rglob('*.whl'))
 return {str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
assert (base/'evidence/wheels.json').exists(),'build not complete'
assert 'clean installed a39 import PASS' in Path('/workspace/actions-327-a39/build-installed-combined.log').read_text(),'build not complete'
before=snapshot();(out/'artifacts-before.json').write_text(json.dumps(before,indent=2)+'\n')
receipt={'source':(base/'source-sha.txt').read_text().strip(),'node':subprocess.check_output([node/'node','--version'],text=True).strip(),'npm':subprocess.check_output([node/'npm','--version'],text=True).strip(),'cwd':str(frontend),'commands':[]}
for command,name in [(['npm','test'],'tests'),(['npm','run','test:quality'],'quality')]:
 start=time.monotonic()
 with (out/(name+'.log')).open('w') as stream:
  try:r=subprocess.run(command,cwd=frontend,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=600);code=r.returncode
  except subprocess.TimeoutExpired:code=124
 receipt['commands'].append({'command':command,'exit_code':code,'seconds':round(time.monotonic()-start,3),'log':name+'.log'})
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
after=snapshot();(out/'artifacts-after.json').write_text(json.dumps(after,indent=2)+'\n');receipt['artifacts_unchanged']=before==after
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
