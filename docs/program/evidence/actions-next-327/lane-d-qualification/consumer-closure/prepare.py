import hashlib,json,subprocess,tomllib
from pathlib import Path
root=Path('/workspace/lane-d'); wheelhouse=root/'resolved-wheelhouse'; wheelhouse.mkdir()
lock=tomllib.loads((root/'repo/action_server/poetry.lock').read_text())
allowed={f['file']:f['hash'].removeprefix('sha256:') for p in lock['package'] for f in p.get('files',[])}
entries=[]
for wheel in sorted((root/'cache/poetry/artifacts').rglob('*.whl')):
 if wheel.name not in allowed: continue
 digest=hashlib.sha256(wheel.read_bytes()).hexdigest()
 if digest!=allowed[wheel.name]: raise ValueError('cached archive differs from lock: '+wheel.name)
 target=wheelhouse/wheel.name
 if not target.exists(): target.symlink_to(wheel)
 entries.append({'name':wheel.name,'sha256':digest,'authority':'Runtime poetry.lock'})
for wheel in sorted((root/'consumer-wheels').glob('*.whl')):
 (wheelhouse/wheel.name).symlink_to(wheel)
 entries.append({'name':wheel.name,'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'authority':'locally built source package'})
wheel=root/'wheels/actions_runtime-1.1.0a38-cp312-cp312-linux_x86_64.whl'
(wheelhouse/wheel.name).symlink_to(wheel)
entries.append({'name':wheel.name,'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'authority':'retained da928 candidate'})
(root/'receipts/consumer-wheelhouse.json').write_text(json.dumps(entries,indent=2)+'\n')
(root/'consumer-constraints.txt').write_text('\n'.join(sorted({p['name']+'=='+p['version'] for p in lock['package']}))+'\n')
