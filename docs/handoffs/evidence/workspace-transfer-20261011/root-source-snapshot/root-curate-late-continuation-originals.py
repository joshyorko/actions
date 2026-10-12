import hashlib,json,os,re,stat,subprocess
from pathlib import Path
base=Path('/workspace/engineering');work=base/'campaign-checkpoint'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=work,text=True).strip()=='843cb16dc071fc764f11f1e0b3b07432dcd04a7d'
old=set()
for p in (work/'docs/handoffs/evidence').glob('actions-swarm-mk3-20261011-*/*manifest.json'):
 d=json.loads(p.read_bytes())
 for r in d.get('copies',[]):old.add(r['source'])
folders=[
'rcc-current8d49-memory-stop-attempt-successor-SOURCE-NOTRUN',
'rcc-current8d49-stop-attempt-independent-SOURCE-and-phase-PREEXEC-review',
'rcc-stop-attempt-concrete-caller-independent-PREEXEC-review',
'rcc-stop-attempt-final-reserve-v2-independent-PREEXEC-review',
'rcc-defaultbackend35-once2-exact-census-independent-ACTUAL-review',
'first-five-v5-measured-mode-independent-SOURCE-review',
'first-five-v6-current00b1-independent-SOURCE-and-PREEXEC-review',
'first-five-v7-original-PURE18-ACTUALFAIL-independent-review',
'first-five-v8-current9760-measured-managed-Git-PURE18-PREEXECUTION-PREPARATION',
'first-five-v8-current9760-independent-SOURCE-child-PREEXEC-review',
'first-five-current9760-concrete-preservation-SOURCE-PREPARATION',
'first-five-current9760-concrete-preservation-independent-SOURCE-review',
'pr307-current9760-owning-settings-independent-SOURCE-and-once4-review',
'pr307-current9760-once4-ACTUALFAIL-independent-review',
'pr307-current9760-once5-ACTUALFAIL-independent-review',
'pr307-current9760-private-once5-independent-SOURCE-PREEXEC-review',
'pr305-currentf75-readonly-LIGHT-readiness-review']
selected=[]
for name in folders:
 p=base/name
 if p.exists():selected.extend(sorted(p.glob('OWNERFINAL*.json')))
selected += [base/'rcc-current8d49-memory-stop-attempt-successor-SOURCE-NOTRUN'/name for name in ['native_memory_sampler_overlay_v1_NOTRUN.py','native_memory_entry_v1_NOTRUN.py','test_native_memory_composition_v1_NOTRUN.py','pure_stop_attempt_control_phase_NOTRUN.py']]
selected += [base/'rcc-stop-attempt-caller-final-reserve-v2-PREEXEC-NOTRUN'/name for name in ['stop_attempt_caller_contract_v1_NOTRUN.py','run_stop_attempt_inner_caller_v1_NOTRUN.py','run_stop_attempt_external_parent_v1_NOTRUN.py']]
selected += [base/'obsolete-accepted-environment-preservation-SOURCE-PREPARATION'/name for name in ['preserve_first_five_accepted_obsolete_environments_SOURCE_PREPARED_v4.py','test_first_five_environment_preservation_admission_SOURCE_PREPARED_v5_measured_modes.py']]
selected += [base/'first-five-current9760-concrete-preservation-SOURCE-PREPARATION/root_once_first_five_current9760_SOURCE_PREPARED_v2.py',base/'root-reviewed-first-five-v8-PURE18-external-parent.py',base/'OWNERFINAL-root-concrete-first-five-v8-parent-SOURCE-NOTRUN.json',base/'OWNERFINAL-root-live-retained54-and-five-heads-20261011-2250.json',base/'OWNERFINAL-root-canonical-settings-and-namespace-two-proposal-adoption.json',base/'root-reviewed-stop-attempt-v2-original-execution/OWNERFINAL-root-original-reviewed-stop-attempt-v2-four-phase-execution.json']
selected=[p for p in selected if str(p) not in old]
dst=work/'docs/handoffs/evidence/actions-swarm-mk3-20261011-late-source-continuation';dst.mkdir(mode=0o700)
rows=[]
for i,p in enumerate(selected,1):
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_uid==s.st_gid==1000
 b=p.read_bytes();assert len(b)<100000,p
 assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|X-Amz-Signature=|sig=[A-Za-z0-9%]{32,})',b),p
 if p.suffix=='.json':json.loads(b)
 q=dst/(f'{i:02d}-'+p.name);fd=os.open(q,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 assert q.read_bytes()==b
 rows.append(dict(source=str(p),source_mode=oct(stat.S_IMODE(s.st_mode)),path=str(q.relative_to(work)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),scope='Exact private source or original receipt checkpoint; no execution adoption or evidence promotion'))
m=dict(schema=1,parent='843cb16dc071fc764f11f1e0b3b07432dcd04a7d',copies=rows,files=len(rows),bytes=sum(r['bytes'] for r in rows),excluded=['private configurations','full inventories','raw logs','binaries','archives','credentials'],checkpoint_scope='Originals retained; safe copies are not a standalone executable acceptance bundle.')
p=dst/'exact-safe-late-original-source-and-owner-copy-manifest.json';b=(json.dumps(m,indent=2,sort_keys=True)+'\n').encode();fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
print(json.dumps(dict(manifest=str(p),files=len(rows),bytes=m['bytes'],manifest_bytes=len(b),sha256=hashlib.sha256(b).hexdigest())))
