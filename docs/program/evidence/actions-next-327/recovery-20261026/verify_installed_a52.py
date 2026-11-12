import hashlib,json,pathlib,subprocess,zipfile
base=pathlib.Path('/workspace/327-artifacts/consumer-a52')
site=base/'lib/python3.12/site-packages'
wheels=[pathlib.Path('/workspace/327-artifacts/a52/actions_runtime-1.1.0a52-cp312-cp312-linux_x86_64.whl'),pathlib.Path('/workspace/actions/actions/dist/actions_core-1.1.0a8-py3-none-any.whl'),pathlib.Path('/workspace/actions/work-items/dist/actions_work_items-0.5.0a2-py3-none-any.whl')]
receipt={'status':'PASS','profile_note':'Fresh public dependency resolution, not historical a52 environment; MCP version recorded below.','wheels':[]}
for wheel in wheels:
    item={'name':wheel.name,'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'payload_members':0,'mismatches':[]}
    with zipfile.ZipFile(wheel) as z:
        for name in z.namelist():
            if name.endswith('/') or '.dist-info/' in name: continue
            item['payload_members']+=1
            p=site/name
            if not p.is_file() or p.read_bytes()!=z.read(name): item['mismatches'].append(name)
        for name in z.namelist():
            if name.endswith('/METADATA'):
                p=site/name
                item['metadata_identical']=p.read_bytes()==z.read(name)
    if item['mismatches'] or not item['metadata_identical']: receipt['status']='FAILED'
    receipt['wheels'].append(item)
freeze=subprocess.check_output([str(base/'bin/python'),'-m','pip','freeze'],text=True)
out=pathlib.Path('/workspace/327-probes/installed-a52-freeze.txt');out.write_text(freeze)
receipt['freeze_sha256']=hashlib.sha256(freeze.encode()).hexdigest()
receipt['mcp']=[line for line in freeze.splitlines() if line.lower().startswith('mcp==')]
pathlib.Path('/workspace/327-probes/installed-a52-payload.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
assert receipt['status']=='PASS'
