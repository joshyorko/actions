import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path
root=Path('/workspace/engineering/pr310')
out=root.parent/'pr310-runner-qualification-owned'
p=root/'action_server/tests/action_server_tests/test_dakota_workitems_native_ui_acceptance.py'
spec=importlib.util.spec_from_file_location('native_ui_control',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
records=[]
for kind,path in [('frozen',out/'dist/action-server/action-server'),('go-wrapper',out/'dist/final/action-server')]:
 os.environ.update({'DAKOTA_WORKITEMS_UI_EXECUTABLE':str(path),'DAKOTA_WORKITEMS_UI_SOURCE_SHA':'92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e','DAKOTA_WORKITEMS_UI_RUNTIME_KIND':kind,'DAKOTA_WORKITEMS_UI_BUILD_MANIFEST':str(out/'output/native-artifact-manifest.json')})
 os.environ.pop('DAKOTA_WORKITEMS_UI_RECEIPT',None)
 identity=m.packaged_runtime_identity()
 package=identity[0].parent if kind=='frozen' else identity[0].parents[1]/'action-server'
 entry=m.require_bundled_rcc_baseline(m.packaged_tree_inventory(package),platform_name='Linux')
 records.append({'kind':kind,'path':str(identity[0]),'source_sha':identity[1],'sha256':identity[2],'architecture':identity[3],'RCC_baseline':entry})
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='f506a04e240feba048bf10e32bccebf591674f9e'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True)
record={'status':'PASS_SERVICE_FREE_NATIVE_UI_IDENTITY_GUARDS','control':'f506a04e240feba048bf10e32bccebf591674f9e','test_module':str(p),'test_module_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'artifact_identity':records,'native_and_browser_executed':False}
(out/'read-only-preflight.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
