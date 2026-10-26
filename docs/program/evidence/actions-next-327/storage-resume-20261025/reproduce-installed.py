import hashlib,importlib.metadata,json,pathlib,subprocess,sys,zipfile
from actions.server.foundry.rcc_execution import GeneratedRccExecution
import actions.server
b=pathlib.Path('/workspace/recovery327/a41'); site=pathlib.Path(actions.server.__file__).resolve().parents[2]
assert site.is_relative_to(b/'consumer')
counts={}
for wheel in b.glob('wheels/*/*.whl'):
 with zipfile.ZipFile(wheel) as z:
  count=0
  for n in z.namelist():
   if n.endswith('/') or n.endswith('.dist-info/RECORD'):continue
   assert (site/n).read_bytes()==z.read(n),n
   count+=1
  counts[wheel.name]=count
out=b/'reproduce'; out.mkdir(exist_ok=False)
(out/'generated_actions.py').write_text('from pydantic import BaseModel\nclass Report(BaseModel):\n    value: int\ndef report(): return Report(value=2)\n')
(out/'input.json').write_text('{}')
helper=GeneratedRccExecution._execution_helper({'module':'generated_actions','actionName':'report'})
(out/'helper.py').write_text(helper)
r=subprocess.run([sys.executable,'-I','-B',str(out/'helper.py'),str(out),str(out/'input.json'),str(out/'result.json')],capture_output=True,timeout=15)
(out/'stderr.txt').write_bytes(r.stderr)
assert r.returncode!=0 and b'Object of type Report is not JSON serializable' in r.stderr and not (out/'result.json').exists()
receipt={'status':'REPRODUCED','scope':'exact installed wheel helper; not real RCC or public Canvas acceptance','wheel_members_verified':counts,'runtime':importlib.metadata.version('actions-runtime'),'core':importlib.metadata.version('actions-core'),'mcp':importlib.metadata.version('mcp'),'returncode':r.returncode,'helper_sha256':hashlib.sha256(helper.encode()).hexdigest()}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
