import json,subprocess
from pathlib import Path
node='/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/node'
frontend=Path('/workspace/engineering/pr305/action_server/frontend')
out=Path('/workspace/actions-cloud/receipts/pr305-selector-fix/full-title-discovery');out.mkdir(exist_ok=True)
patterns={'retained-source-RED':'^official bridge renders a real Runtime Action result$','full-title-GREEN':r'^\s*host-harness\.spec\.ts official bridge renders a real Runtime Action result$','overbroad-POISON':'.*','wrong-case-POISON':r'^\s*host-harness\.spec\.ts official MCP Apps bridge handles fixture calls and host context lifecycle$'}
results=[]
for label,pattern in patterns.items():
 command=[node,str(frontend/'node_modules/@playwright/test/cli.js'),'test','--config',str(frontend/'playwright.canvas-harness.config.ts'),'--grep',pattern,'--workers','1','--reporter','json','--list']
 completed=subprocess.run(command,cwd=frontend,capture_output=True,text=True,timeout=30)
 (out/(label+'-stdout.json')).write_text(completed.stdout);(out/(label+'-stderr.log')).write_text(completed.stderr)
 report=json.loads(completed.stdout); specs=[]
 def collect(suites):
  for suite in suites:
   specs.extend(suite.get('specs',[]));collect(suite.get('suites',[]))
 collect(report.get('suites',[])); results.append(dict(label=label,argv=command,returncode=completed.returncode,specs=[s['title'] for s in specs],errors=[e.get('message') for e in report.get('errors',[])],phase='DISCOVERY_ONLY_NO_TESTCASE_OR_BROWSER'))
(out/'selector-discovery.json').write_text(json.dumps(results,indent=2)+'\n'); print(json.dumps(results,indent=2))
assert results[0]['returncode']==1 and results[0]['specs']==[]
assert results[1]['returncode']==0 and results[1]['specs']==['official bridge renders a real Runtime Action result']
assert len(results[2]['specs'])==2
assert results[3]['specs']==['official MCP Apps bridge handles fixture calls and host context lifecycle']
