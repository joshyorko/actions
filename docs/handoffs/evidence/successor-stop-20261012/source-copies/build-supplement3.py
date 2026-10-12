import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

root=Path('/workspace/successor-evidence')
out=Path('/workspace/actions-checkpoint/docs/handoffs/evidence/successor-20261012-supplement3')
out.mkdir(parents=True,exist_ok=True)
head='f949bef2eeab518ffd34d9e69955938a007f8922'
def api(endpoint): return json.loads(subprocess.check_output(['gh','api',endpoint]))
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
checks=api(f'repos/joshyorko/actions/commits/{head}/check-runs?per_page=100')
snapshot={'observed_at':now,'head':head,'checks':[{k:c[k] for k in ('name','status','conclusion','html_url')} for c in checks['check_runs']]}
snapshot_path=root/'current-checks-f949-supplement3.json'
if not snapshot_path.exists(): snapshot_path.write_text(json.dumps(snapshot,indent=2)+'\n')
names=['current-checks-f949-supplement3.json','current-checks-f949-terminal.json','supplement3-first-selector-FAIL.json','supplement3-documentation-disposition.json','supplement3-final-inventory-resource.json','pr308-f949-metadata-readback.json','pr308-f949-terminal-metadata-readback.json']
names += ['pr308/'+s for s in ['eeb-windows-source-terminal-diagnosis.json','cpython31215-venv-launcher-source-provenance.json','pr308-d358f9c2-windows-launcher-source-receipt.json','native-baseline-profile-d358f9c2-v10-SOURCE-PREPARED-NOTRUN.json','pr308-f949bef2-async-admission-source-receipt.json','native-baseline-profile-f949bef2-v11-SOURCE-PREPARED-NOTRUN.json','f949bef2-remote-source-readback.json','native-baseline-profile-f949bef2-v12-CI-PASS-NOTADMITTED.json']]
for group in ['review308-windows-launcher','review308-async-admission','review308-linux-async-failure','review308-windows0546-terminal','review308-mac-eeb-terminal','review-checkpoint-remote3b861632']:
 names += [str(p.relative_to(root)) for p in (root/group).glob('*.json') if p.name not in {'decoded-private-transport.json'}]
names += ['pr308-f949-packaged/'+s for s in ['download-connector-receipt.json','artifact-metadata.json','installed-command-receipt.json','installed-verification.json','installed-verifier-first-FAIL.json','pip-owned-cache-receipt.json','installed-minimum-core-consumer/admission.json','installed-minimum-core-consumer/startup-once2/startup-receipt.json']]
names += ['verify-pr308-f949-packaged/'+s for s in ['github-metadata.json','independent-package-verification.json','sdist-complete-source-verification.json']]
names += [str(p.relative_to(root)) for p in (root/'pr308/f949-platform-ci').glob('job-*-safe-receipt.json')]
names += [str(p.relative_to(root)) for p in (root/'review308-f949-packaged').glob('*.json')]
cur=int(Path('/sys/fs/cgroup/memory.current').read_text())
maximum=int(Path('/sys/fs/cgroup/memory.max').read_text())
resource=root/'supplement3-resource-observation.json'
if not resource.exists(): resource.write_text(json.dumps({'observed_at':now,'memory_current':cur,'memory_max':maximum,'visible_headroom_bytes':maximum-cur,'memory_events':Path('/sys/fs/cgroup/memory.events').read_text(),'disk_free':shutil.disk_usage('/workspace').free,'tmp_free':shutil.disk_usage('/tmp').free,'shm_free':shutil.disk_usage('/dev/shm').free,'self_binding':'UNQUALIFIED','native_admitted':False,'native_baseline_attempts':0,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()},indent=2)+'\n')
names.append('supplement3-resource-observation.json')
names += ['review308-f949-windows/review.json','review-checkpoint-supplement3/supplement3-review.json']
old=set()
for group in ['successor-20261012','successor-20261012-supplement1','successor-20261012-supplement2']:
 old.update(r['path'] for r in json.loads((out.parent/group/'manifest.json').read_text()))
rows=[]
for n in sorted(set(names)):
 if n in old: continue
 data=(root/n).read_bytes(); json.loads(data)
 assert not re.search(rb'file://|x-amz-signature=|github_pat_|ghp_[A-Za-z0-9]|Authorization.{0,10}Bearer|client_secret\s*=|api_key\s*=',data,re.I),n
 dst=out/n; dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists(): assert dst.read_bytes()==data,n
 else: dst.write_bytes(data)
 rows.append({'path':n,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(out/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({'payloads':len(rows),'bytes':sum(r['bytes'] for r in rows),'observed_at':now}))
