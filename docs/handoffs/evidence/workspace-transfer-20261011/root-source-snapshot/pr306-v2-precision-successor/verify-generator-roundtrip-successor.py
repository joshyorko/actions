import hashlib,json,sys
from pathlib import Path
import toolkit
root=toolkit.REPOSITORY_ROOT;paths=sorted(p for p in (root/'.github').rglob('*.yml') if p.is_file());before={str(p.relative_to(root)):p.read_bytes() for p in paths};toolkit.run([sys.executable,str(root/'.github/workflows/_gen_workflows.py')]);after={str(p.relative_to(root)):p.read_bytes() for p in paths};assert before==after
out=Path('/workspace/engineering/pr306-v2-precision-successor');r={'all_tracked_workflow_and_dependabot_bytes_unchanged_after_generation':True,'measured_YAML_count':len(paths),'sha256':{p:hashlib.sha256(data).hexdigest() for p,data in before.items()},'generator_and_workflow_source_changed':False};(out/'current-generator-roundtrip.json').write_text(json.dumps(r,indent=2)+'\n');print('Current all8 generator outputs + dependabot roundtrip; all',len(paths),'YAML files unchanged',flush=True)
toolkit.poetry('action_server','run','python','-m','pytest','-q','-n','0','tests/action_server_tests/test_database.py','tests/action_server_tests/test_database_shared.py')
