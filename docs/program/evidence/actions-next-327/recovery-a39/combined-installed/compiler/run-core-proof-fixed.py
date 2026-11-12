import json,os,subprocess
from pathlib import Path
from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor,build_exec_command
base=Path('/workspace/actions-327-a39/compiler');work=base/'core-proof-run-fixed';work.mkdir()
for n in ('home','actions-home','tmp'):(work/n).mkdir()
r=json.loads((base/'prepared.json').read_text())
d=RccRuntimeDescriptor(artifact_digest=r['artifactDigest'],source_generation='core-wheel-verification',source_hash=r['packageYamlDigest'],environment_fingerprint=r['specificationDigest'].removeprefix('sha256:'),preparation_class='warm-reuse',provider_reference='local')
cmd=build_exec_command(Path('/workspace/actions-cloud/bin/rcc'),d,['python','-I',str(base/'verify-core.py'),str(base)],receipt_file=base/'core-exec-qualified.json',local_trust_carrier=base/'robocorp/artifacts/v1/trust')
cmd.insert(cmd.index('--'),'--no-build')
env={'HOME':str(work/'home'),'PATH':'/usr/sbin:/sbin:/usr/bin:/bin','ROBOCORP_HOME':str(base/'robocorp'),'ACTIONS_HOME':str(work/'actions-home'),'TMPDIR':str(work/'tmp'),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8','RCC_NO_BUILD':'1'}
(work/'invocation.json').write_text(json.dumps({'command':cmd,'environment_keys':sorted(env)},indent=2)+'\n')
subprocess.run(cmd,env=env,cwd=work,check=True,timeout=180)
