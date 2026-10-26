import hashlib,importlib.metadata,json,sys,sysconfig,zipfile
from pathlib import Path
root=Path(sys.argv[1]);site=Path(sysconfig.get_paths()['purelib'])
assert sys.flags.isolated and Path(sys.executable).resolve().is_relative_to(root/'robocorp')
assert importlib.metadata.version('robotframework')=='7.4.2'
counts={}
for stem,version,digest in [('actions_core','1.1.0a8','42e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f'),('actions_work_items','0.5.0a2','72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb')]:
 assert importlib.metadata.version(stem)==version
 wheel=root/'robocorp/wheels'/f'{stem}-{version}-py3-none-any.whl'
 assert hashlib.sha256(wheel.read_bytes()).hexdigest()==digest
 count=0
 with zipfile.ZipFile(wheel) as z:
  for name in z.namelist():
   if name.endswith('/') or '.dist-info/' in name or '.data/' in name:continue
   assert (site/name).read_bytes()==z.read(name),name;count+=1
 counts[stem]=count
assert counts=={'actions_core':87,'actions_work_items':26}
proof={'status':'PASS','core_version':'1.1.0a8','robot_version':'7.4.2','payload_members_verified':87,'work_items_members_verified':26,'wheel_sha256':'42e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f','interpreter':sys.executable,'interpreter_resolved':str(Path(sys.executable).resolve()),'interpreter_sha256':hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),'isolated':True}
(root/'core-proof.json').write_text(json.dumps(proof,indent=2))
