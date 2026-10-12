import ast,json,subprocess,hashlib
from pathlib import Path
repo=Path('/workspace/engineering/pr305');source=repo/'action_server/tests/action_server_tests/mcp/test_mcp_apps_authoring.py';frontend=repo/'action_server/frontend';out=Path('/workspace/actions-cloud/receipts/pr305-selector-fix')
fn=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_run_canvas_browser')
lists=[n for n in ast.walk(fn) if isinstance(n,ast.List) and any(isinstance(v,ast.Constant) and v.value=='--reporter' for v in n.elts)]
assert len(lists)==1
values=lists[0].elts;index=next(i for i,v in enumerate(values) if isinstance(v,ast.Constant) and v.value=='--grep');selector=ast.literal_eval(values[index+1])
node='/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/node'
command=[node,str(frontend/'node_modules/@playwright/test/cli.js'),'test','--config',str(frontend/'playwright.canvas-harness.config.ts'),'--grep',selector,'--workers','1','--reporter','json','--list']
r=subprocess.run(command,cwd=frontend,capture_output=True,text=True,timeout=30)
(out/'actual-emitted-list-stdout.json').write_text(r.stdout);(out/'actual-emitted-list-stderr.log').write_text(r.stderr);a=json.loads(r.stdout);specs=[]
def collect(suites):
 for suite in suites:
  specs.extend(suite.get('specs',[]));collect(suite.get('suites',[]))
collect(a.get('suites',[]))
assert r.returncode==0 and not a.get('errors')
assert len(specs)==1 and specs[0]['title']=='official bridge renders a real Runtime Action result'
assert len(specs[0]['tests'])==1
receipt=dict(phase='ACTUAL_SOURCE_EMITTED_SELECTOR_DISCOVERY_ONLY_NO_EXECUTION',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),argv=command,returncode=r.returncode,specs=[s['title'] for s in specs],test_entries=1,browser_launched=False,testcase_executed=False)
(out/'actual-emitted-selector-GREEN.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
