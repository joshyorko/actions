import hashlib,json,sys,sysconfig,zipfile,importlib.metadata
from pathlib import Path
base=Path('/workspace/actions-recovery-327/installed-a25'); site=Path(sysconfig.get_paths()['purelib']); result={'prefix':sys.prefix,'packages':{}}
assert Path(sys.prefix)==base/'consumer'
for label,directory,package in [('runtime','runtime-wheels','action_server'),('core','core-wheels','actions'),('sdk','sdk-wheels','work-items')]:
 wheel=next((base/directory).glob('*.whl')); count=0
 with zipfile.ZipFile(wheel) as archive:
  for name in archive.namelist():
   if name.endswith('.py') and not '.dist-info/' in name:
    payload=archive.read(name); assert (site/name).read_bytes()==payload, name
    source=base/'source'/package/'src'/name
    assert source.read_bytes()==payload,name
    count+=1
  metadata=next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))
  name=next(l[6:] for l in archive.read(metadata).decode().splitlines() if l.startswith('Name: '))
 dist=importlib.metadata.distribution(name)
 direct=json.loads(dist.read_text('direct_url.json')); assert not direct.get('dir_info',{}).get('editable',False)
 result['packages'][name]={'version':dist.version,'wheel':wheel.name,'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'python_members':count,'all_source_and_installed_bytes_match':True,'direct_url':direct}
import actions.server, actions.mcp, actions.work_items
for module in [actions.server,actions.mcp,actions.work_items]: assert Path(module.__file__).is_relative_to(site),module.__file__
result['status']='PASS'
Path('/workspace/actions-recovery-327/evidence/a25-consumer-provenance.json').write_text(json.dumps(result,indent=2)+'\n')
