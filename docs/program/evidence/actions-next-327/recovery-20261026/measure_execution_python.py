import os,subprocess,json
from pathlib import Path
from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor,build_exec_command,read_receipt
root=Path('/workspace/327-probes/a53-claimed/compiler')
verifier=(root/'verify_compiler.py').read_text().replace("root/'core-proof.json'","root/'execution-core-proof.json'")
(root/'verify_execution.py').write_text(verifier)
artifact=json.loads((root/'prepared.json').read_text())['artifactDigest']
rcc=Path('/workspace/327-artifacts/a53/consumer/lib/python3.12/site-packages/actions/server/bin/rcc-18.19.3')
command=build_exec_command(rcc,RccRuntimeDescriptor(artifact_digest=artifact,provider_reference='local'),['python','-I',str(root/'verify_execution.py'),str(root)],receipt_file=root/'execution-core-exec.json',local_trust_carrier=root/'robocorp/artifacts/v1/trust');command.insert(1,'--no-build')
env={'PATH':'/usr/sbin:/sbin:'+os.defpath,'LANG':'C.UTF-8','PYTHONIOENCODING':'utf-8','PYTHONUNBUFFERED':'1','ROBOCORP_HOME':str(root/'robocorp'),'RCC_NO_BUILD':'1'}
subprocess.run(command,env=env,cwd=root,check=True,timeout=60)
assert read_receipt(root/'execution-core-exec.json',artifact)
print((root/'execution-core-proof.json').read_text())
