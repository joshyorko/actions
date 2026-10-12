import sys,json,copy
from pathlib import Path
sys.path.insert(0,'/workspace/engineering/pr305/action_server/tests')
from action_server_tests.mcp import test_mcp_apps_authoring as bridge
p=Path('/workspace/actions-cloud/receipts/pr305-selector-fix')
base={'stats':{'expected':1,'unexpected':0,'skipped':0,'flaky':0},'suites':[{'specs':[{'title':'official bridge renders a real Runtime Action result','tests':[{'results':[{'status':'passed'}]}]}]}]}
bridge._assert_canvas_playwright_report(base)
poison=copy.deepcopy(base);poison['errors']=[{'message':'Error: No tests found'}]
try:bridge._assert_canvas_playwright_report(poison)
except AssertionError as e:assert str(e)=='Playwright reported errors'
else:raise AssertionError('nonblankerror admitted')
retained=json.loads((p/'full-title-discovery/retained-source-RED-stdout.json').read_text())
try:bridge._assert_canvas_playwright_report(retained)
except AssertionError as e:assert str(e)=='Playwright reported errors'
else:raise AssertionError('retained0case/error report admitted')
(p/'actual-validator-error-controls.json').write_text(json.dumps(dict(phase='ACTUAL_SOURCE_VALIDATOR_SERVICE_FREE_CONTROLS_ONLY',valid_synthetic_baseline_admitted=True,otherwise_valid_nonblank_error_rejected=True,retained_actual_empty_NoTestsFound_report_rejected=True,product_result_claim=False),indent=2)+'\n')
