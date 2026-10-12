import ast,hashlib,json,subprocess
from pathlib import Path
import toolkit,yaml
r=toolkit.REPOSITORY_ROOT;o=Path('/workspace/engineering/pr282-actual618-refresh');old='9c8f1c95caeded6495877280ed1465fd9850b254'
def git(*a):return subprocess.check_output(['git','-C',str(r),*a])
gen='.github/workflows/_gen_workflows.py'
def method(data):
 return next(n for n in ast.walk(ast.parse(data)) if isinstance(n,ast.FunctionDef) and n.name=='published_canvas_acceptance')
a,b=method(git('show',old+':'+gen)),method((r/gen).read_bytes());assert ast.dump(a)==ast.dump(b)
path='.github/workflows/actions_runtime_tests.yml'
def step(data):return next(s for s in yaml.safe_load(data)['jobs']['build']['steps'] if s.get('name')=='Verify Canvas published-Core Runtime and browser acceptance')
assert step(git('show',old+':'+path))==step((r/path).read_bytes())
proof={'status':'PASS_STRICT_ORIGINAL_CANVAS_GATE_UNCHANGED','original_source':old,'current_head':git('rev-parse','HEAD').decode().strip(),'whole_Canvas_generator_method_AST_exact_original9c':True,'whole_Canvas_workflow_step_exact_original9c':True,'scope':'all39strictpredicates/version/preflight/controller/source/hash/diagnostic expectations unchanged; incoming RCC source control separate','no_actual_execution':True}
(o/'strict-Canvas-original-gateway-preservation.json').write_text(json.dumps(proof,indent=2)+'\n');print('Original Canvas entire method AST and workflow step PASS')
