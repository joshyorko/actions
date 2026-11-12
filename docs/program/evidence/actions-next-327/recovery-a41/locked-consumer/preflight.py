import hashlib,json,re,subprocess,tomllib,zipfile
from pathlib import Path
base=Path('/workspace/actions-327-a41'); old=base/'installed-v2'; out=base/'locked-consumer-evidence'
sha=(old/'source-sha.txt').read_text().strip()
assert sha=='f905c3888ecb448dbce80ce57a9b59ff041eb148'
lock=old/'source/action_server/poetry.lock'
canonical=subprocess.check_output(['git','show',sha+':action_server/poetry.lock'],cwd='/workspace/actions')
assert canonical==lock.read_bytes(),'frozen lock differs from commit'
parsed=tomllib.loads(canonical.decode())
normalize=lambda s:re.sub(r'[-_.]+','-',s).lower()
main={}
for item in parsed['package']:
 if 'main' in item.get('groups',[]):
  main.setdefault(normalize(item['name']),set()).add(item['version'])
assert all(len(v)==1 for v in main.values())
constraints=base/'next-consumer-constraints.txt'
lines=constraints.read_text().splitlines()
expected=sorted(k+'=='+next(iter(v)) for k,v in main.items())
assert sorted(lines)==expected and len(lines)==len(set(lines))==70
manifest=json.loads((old/'evidence/wheels.json').read_text())
expected_names={'actions-runtime':'1.1.0a41','actions-core':'1.1.0a5','actions-work-items':'0.5.0a2'}
import email.parser
wheels={}
for relative,sha256 in manifest.items():
 path=old/relative
 assert hashlib.sha256(path.read_bytes()).hexdigest()==sha256
 with zipfile.ZipFile(path) as z:
  metadata=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')]
  assert len(metadata)==1
  msg=email.parser.Parser().parsestr(z.read(metadata[0]).decode())
  name=normalize(msg['Name']); assert expected_names.pop(name)==msg['Version']
  wheels[name]={'path':str(path),'sha256':sha256,'version':msg['Version']}
assert not expected_names
record={'source_revision':sha,'frozen_lock':str(lock),'lock_sha256':hashlib.sha256(canonical).hexdigest(),'constraints':str(constraints),'constraints_sha256':hashlib.sha256(constraints.read_bytes()).hexdigest(),'unique_main_constraints':len(lines),'selected_runtime_extras':[],'wheels':wheels}
(out/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
