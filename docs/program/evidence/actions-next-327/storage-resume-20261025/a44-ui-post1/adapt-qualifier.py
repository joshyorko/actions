"""Prepare the reviewed consumer qualifier for the separately versioned UI fix."""
import argparse,ast,hashlib,json
from pathlib import Path
SOURCE='cd0ed1ce4f425322efd29f0fe09ad430b157bea5'
VERSION='1.1.0a44.post1'
ORIGINAL='44b13d438b5a12171edd4492b1b4bfc8c00ceeb593d9c575c43a74ac388b9770'
p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise SystemExit('Fresh output file required')
s=a.original.read_bytes()
if hashlib.sha256(s).hexdigest()!=ORIGINAL:raise SystemExit('Expected exact parent-reviewed port-adapted qualifier')
t=s.decode()
for old,new in [("assert CONFIG['source_sha'] == 'd0c87a38a937cc339e8e661ac453c7a62ed41fa6'",f"assert CONFIG['source_sha'] == '{SOURCE}'"),("assert CONFIG['runtime_version'] == '1.1.0a44'",f"assert CONFIG['runtime_version'] == '{VERSION}'")]:
 if t.count(old)!=1:raise SystemExit('Candidate assertion must occur exactly once')
 t=t.replace(old,new)
ast.parse(t);a.output.write_text(t)
print(json.dumps({'source_sha':SOURCE,'runtime_version':VERSION,'qualifier_sha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),'scope':'Only two candidate identity assertions changed; no execution/auth/host change'}))
