import hashlib,importlib.util,json,pathlib,tomllib,zipfile
root=pathlib.Path('/workspace/actions'); b=pathlib.Path('/workspace/recovery327/a42')
spec=importlib.util.spec_from_file_location('inventory',root/'action_server/scripts/qualify_consumer_inventory_327.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
result=m.qualify(json.loads((b/'evidence/inspect.json').read_text()),tomllib.loads((b/'source/action_server/poetry.lock').read_text()),'1.1.0a42',[])
(b/'evidence/dependency-closure.json').write_text(json.dumps(result,indent=2)+'\n')
site=next((b/'consumer/lib').glob('python*/site-packages'));counts={}
for wheel in (b/'wheels').glob('*/*.whl'):
 with zipfile.ZipFile(wheel) as z:
  count=0
  for n in z.namelist():
   if n.endswith('/') or n.endswith('.dist-info/RECORD'):continue
   assert (site/n).resolve().is_relative_to(site)
   assert (site/n).read_bytes()==z.read(n),n
   count+=1
  counts[wheel.name]={'members':count,'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest()}
(b/'evidence/installed-bytes.json').write_text(json.dumps(counts,indent=2)+'\n');print(json.dumps({'status':'PASS','wheels':counts,'scope':'exact installed members and frozen-lock dependency closure; not SBOM graph or full release'}))
