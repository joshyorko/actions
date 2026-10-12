"""Service-free existing result-validator controls; no product or browser run."""
import ast,copy,hashlib,json,sys
from pathlib import Path
root=Path('/workspace/engineering/pr305');own=Path(__file__).resolve().parent
p=root/'action_server/tests/action_server_tests/mcp/test_mcp_apps_authoring.py';raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='d84f5e54dafb29e9beda15673769110952f165aee61c0deb5a04ee920515abcf'
sys.path.insert(0,str(root/'action_server/tests'))
from action_server_tests.mcp import test_mcp_apps_authoring as bridge
assert hashlib.sha256(Path(bridge.__file__).read_bytes()).hexdigest()==hashlib.sha256(raw).hexdigest()
valid={'errors':[],'stats':{'expected':1,'unexpected':0,'skipped':0,'flaky':0},'suites':[{'specs':[{'title':'official bridge renders a real Runtime Action result','tests':[{'results':[{'status':'passed'}]}]}]}]};bridge._assert_canvas_playwright_report(valid);passed=['valid_executed_case_baseline']
for poison in ['nonblank_error','empty','broad_two','wrong_fixture','skipped','failed','retry']:
 r=copy.deepcopy(valid)
 if poison=='nonblank_error':r['errors']=[{'message':'fixed failure category'}]
 elif poison=='empty':r['suites']=[];r['stats']['expected']=0
 elif poison=='broad_two':r['suites'][0]['specs'].append(copy.deepcopy(r['suites'][0]['specs'][0]));r['stats']['expected']=2
 elif poison=='wrong_fixture':r['suites'][0]['specs'][0]['title']='official MCP Apps bridge handles fixture calls and host context lifecycle'
 elif poison=='skipped':r['suites'][0]['specs'][0]['tests'][0]['results'][0]['status']='skipped'
 elif poison=='failed':r['suites'][0]['specs'][0]['tests'][0]['results'][0]['status']='failed'
 else:r['suites'][0]['specs'][0]['tests'][0]['results'].append({'status':'passed'})
 try:bridge._assert_canvas_playwright_report(r)
 except AssertionError:passed.append('reject_'+poison)
 else:raise AssertionError('poison admitted')
result={'phase':'SERVICE_FREE_EXISTING_VALIDATOR; NO_BROWSER_NATIVE_RUNTIME_PACKAGE_BUILD','source_sha256':hashlib.sha256(raw).hexdigest(),'controls':passed,'passed':len(passed),'validator_source_scope':'production test assertions unchanged from14c; synthetic report shapes only'}
(own/'independent-result-validator-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
