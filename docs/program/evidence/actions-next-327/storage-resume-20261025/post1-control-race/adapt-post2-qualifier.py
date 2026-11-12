"""Prepare the reviewed consumer qualifier for the separately versioned UI fix."""
import argparse,ast,hashlib,json
from pathlib import Path
SOURCE='46488e59f419d6bb55ab594031a0f227b4e0d817'
VERSION='1.1.0a44.post2'
ORIGINAL='44b13d438b5a12171edd4492b1b4bfc8c00ceeb593d9c575c43a74ac388b9770'
p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise SystemExit('Fresh output file required')
s=a.original.read_bytes()
if hashlib.sha256(s).hexdigest()!=ORIGINAL:raise SystemExit('Expected exact parent-reviewed port-adapted qualifier')
t=s.decode()
for old,new in [("assert CONFIG['source_sha'] == 'd0c87a38a937cc339e8e661ac453c7a62ed41fa6'",f"assert CONFIG['source_sha'] == '{SOURCE}'"),("assert CONFIG['runtime_version'] == '1.1.0a44'",f"assert CONFIG['runtime_version'] == '{VERSION}'")]:
 if t.count(old)!=1:raise SystemExit('Candidate assertion must occur exactly once')
 t=t.replace(old,new)
replacements = [
    ("before=snapshot('before-browser')", "before=snapshot('before-browser')\n        assert all(before[name] == 0 for name in ('run','run_attempt','run_admission')), before"),
    ("for name in ('run','run_attempt','run_admission'):\n            assert after[name]==before[name]+3, (name,before,after)", "for name in ('run','run_attempt'):\n            assert after[name]==before[name]+3, (name,before,after)\n        assert after['run_admission']==before['run_admission']+1, (before,after)"),
    ("assert len(browser_ids)==3", """assert len(browser_ids)==3
        with sqlite3.connect(DATA/'server.db') as db:
            pins=db.execute('SELECT run_id,run_admission_id FROM run_pin WHERE run_id IN (?,?,?)',tuple(sorted(browser_ids))).fetchall()
            assert len(pins)==3 and {row[0] for row in pins}==browser_ids
            admissions={row[1] for row in pins}
            assert len(admissions)==1
            row=db.execute('SELECT snapshot_json FROM run_admission WHERE id=?',(next(iter(admissions)),)).fetchone()
            assert row is not None
            from actions.server.run_outputs.types import ExecutionSnapshot
            retained_snapshot=ExecutionSnapshot.model_validate_json(row[0])
            assert retained_snapshot.deployment.model_dump(mode='json')=={'workspace_id':RECEIPT['workspace'],'deployment_id':app,'revision_id':revision}
        RECEIPT['browser_admission_invariant']='three Runs and Attempts share one exact authorized snapshot Admission'"""),
]
for old,new in replacements:
 if t.count(old)!=1:raise SystemExit('Expected exact original snapshot assertion block')
 t=t.replace(old,new)
ast.parse(t);a.output.write_text(t)
print(json.dumps({'source_sha':SOURCE,'runtime_version':VERSION,'qualifier_sha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),'scope':'Candidate identity assertions and reviewed snapshot-admission invariant corrected; no execution/auth/host change'}))
