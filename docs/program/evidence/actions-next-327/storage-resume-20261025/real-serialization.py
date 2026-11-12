import hashlib,json,os,pathlib,subprocess
from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor,build_exec_command,read_receipt
from actions.server.foundry.rcc_execution import GeneratedRccExecution
b=pathlib.Path('/workspace/recovery327/compiler'); root=pathlib.Path('/workspace/recovery327/real-serialization');root.mkdir()
r=json.loads((b/'prepared.json').read_text()); results=[]
for label in ['frozen','corrected']:
 d=root/label;d.mkdir()
 for n in ['home','tmp','actions-home']:(d/n).mkdir()
 (d/'generated_actions.py').write_text('from pydantic import BaseModel\nclass Report(BaseModel):\n    value: int\ndef report(): return Report(value=2)\n')
 (d/'input.json').write_text('{}')
 helper=pathlib.Path('/workspace/recovery327/a41/reproduce/helper.py').read_text() if label=='frozen' else GeneratedRccExecution._execution_helper({'module':'generated_actions','actionName':'report'})
 (d/'helper.py').write_text(helper)
 cmd=build_exec_command(pathlib.Path('/workspace/actions-cloud/bin/rcc'),RccRuntimeDescriptor(artifact_digest=r['artifactDigest'],provider_reference='local'),['python','-I','-B',str(d/'helper.py'),str(d),str(d/'input.json'),str(d/'result.json')],receipt_file=d/'rcc-receipt.json',local_trust_carrier=b/'robocorp/artifacts/v1/trust');cmd.insert(1,'--no-build')
 env={'HOME':str(d/'home'),'PATH':'/usr/sbin:/sbin:/usr/bin:/bin','ROBOCORP_HOME':str(b/'robocorp'),'ACTIONS_HOME':str(d/'actions-home'),'TMPDIR':str(d/'tmp'),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8','RCC_NO_BUILD':'1'}
 with (d/'stdout.log').open('wb') as out,(d/'stderr.log').open('wb') as err:p=subprocess.run(cmd,env=env,cwd=d,stdout=out,stderr=err,timeout=90)
 receipt=read_receipt(d/'rcc-receipt.json',r['artifactDigest'])
 if label=='frozen':assert p.returncode!=0 and 'Object of type Report is not JSON serializable' in (d/'stderr.log').read_text() and not (d/'result.json').exists()
 else:assert p.returncode==0 and json.loads((d/'result.json').read_text())=={'value':2}
 results.append({'case':label,'exit_code':p.returncode,'rcc_status':receipt['status'],'helper_sha256':hashlib.sha256(helper.encode()).hexdigest(),'artifact_digest':r['artifactDigest']})
(root/'receipt.json').write_text(json.dumps({'scope':'real pinned RCC helper execution, not installed public Canvas lifecycle','results':results},indent=2)+'\n');print(json.dumps(results))
