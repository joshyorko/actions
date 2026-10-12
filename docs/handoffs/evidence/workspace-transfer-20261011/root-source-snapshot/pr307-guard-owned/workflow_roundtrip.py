import hashlib,importlib.util,json
from pathlib import Path
root=Path('/workspace/engineering/pr307')
owned=Path(__file__).resolve().parent/'workflow-roundtrip'
owned.mkdir(exist_ok=True)
p=root/'.github/workflows/_gen_workflows.py'
spec=importlib.util.spec_from_file_location('reviewed_workflow_generator',p)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.CURDIR=owned
rows=[]
for target in module.TARGETS:
 target.generate()
 generated=(owned/target.target).read_bytes()
 tracked=(p.parent/target.target).read_bytes()
 assert generated==tracked,target.target
 rows.append({'path':'.github/workflows/'+target.target,'size':len(generated),'sha256':hashlib.sha256(generated).hexdigest(),'identical':True})
assert len(rows)==8
(owned.parent/'workflow-roundtrip-receipt.json').write_text(json.dumps({'generator_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'outputs':rows,'all_eight_exact':True},indent=2)+'\n')
