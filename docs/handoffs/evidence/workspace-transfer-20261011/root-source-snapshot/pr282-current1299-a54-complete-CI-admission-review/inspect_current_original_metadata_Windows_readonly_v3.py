import ast,fnmatch,hashlib,json,os,re,stat,subprocess
from pathlib import Path
import yaml

OUT=Path(__file__).resolve().parent;ROOT=Path('/workspace/engineering/pr282');HEAD='1299cc4bb6586f467d36ca124faaaaa77362695f'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bind(p):
 p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
m=json.loads((OUT/'safe-one-current1299-a54-complete-metadata-census.json').read_bytes())
assert m['source']==HEAD and m['target']=='a54c982462d1e7ad011d8152bfc299d997503fb3'
assert m['check_count']==25 and m['check_conclusions']=={'success':25}and m['all_job_count']==25 and m['status_count']==0
assert m['reviews_count']==m['threads_count']==m['unresolved_threads']==0 and m['closures']==[]
assert m['rulesets_count']==m['active_rules_count']==0 and m['protection_HTTP_status']=='403'
assert m['prospective_parents']==[m['target'],HEAD]and m['prospective_tree']=='afe2679cc93bf27fa5021c7698ee7ad3ee21a1b9'
declarations=[]
paths=git('ls-tree','-r','--name-only',HEAD,'.github/workflows').decode().splitlines()
for path in paths:
 if not path.endswith(('.yml','.yaml')):continue
 doc=yaml.load(git('show',HEAD+':'+path),Loader=yaml.BaseLoader);trigger=doc.get('on',{})
 if not isinstance(trigger,dict)or'pull_request'not in trigger:continue
 filters=trigger['pull_request']or{}
 if filters.get('branches')and not any(fnmatch.fnmatchcase('integration/community-release-20261008',x)for x in filters['branches']):continue
 if filters.get('paths')and not any(fnmatch.fnmatchcase(p,pat)for p in m['PR_paths']for pat in filters['paths']):continue
 jobs=[]
 for name,job in doc['jobs'].items():
  matrix=job.get('strategy',{}).get('matrix',{})
  axes={k:v for k,v in matrix.items()if k not in ('include','exclude')}
  count=1
  if axes:
   for values in axes.values():count*=len(values)
  elif matrix.get('include'):count=len(matrix['include'])
  jobs.append({'id':name,'count':count,'needs':job.get('needs'),'if':job.get('if'),'matrix':matrix})
 declarations.append({'path':path,'name':doc.get('name'),'trigger':filters,'jobs':jobs,'count':sum(x['count']for x in jobs)})
assert len(declarations)==9 and sum(x['count']for x in declarations)==25
assert {x['path']for x in declarations}=={x['path']for x in m['runs']}
assert all(x['event']=='pull_request'and x['head_sha']==HEAD and x['run_attempt']==1 and x['status']=='completed'and x['conclusion']=='success'for x in m['runs'])
assert all(len(run['jobs'])==next(x['count']for x in declarations if x['path']==run['path'])for run in m['runs'])
assert all(j['status']=='completed'and j['conclusion']=='success'for r in m['runs']for j in r['jobs'])
checks=json.loads((OUT/'checkruns-page1.private.json').read_bytes())['check_runs']
assert {x['id']for x in checks}=={j['id']for r in m['runs']for j in r['jobs']}
sd=Path('/workspace/engineering/pr282-original1299-one-Windows-log-acquisition');acq=json.loads((sd/'safe-original-acquisition-receipt.json').read_bytes())
assert acq['job_id']==114513237570 and acq['run_id']==38154052443 and acq['source_head']==HEAD and acq['connector_call_count']==1
for key in ['original_decoded','original_MCP_response_generated_JSON','original_local_copy_failure']:
 row=acq[key];assert bind(row['path'])=={k:v for k,v in row.items()if k!='mode'}and oct(stat.S_IMODE(Path(row['path']).stat().st_mode))==row['mode']
wire=json.loads(Path(acq['original_MCP_response_generated_JSON']['path']).read_bytes());strings=[]
def collect(value):
 if isinstance(value,str):strings.append(value)
 elif isinstance(value,list):
  for item in value:collect(item)
 elif isinstance(value,dict):
  for item in value.values():collect(item)
collect(wire['structuredContent']);raw=Path(acq['original_decoded']['path']).read_bytes()
assert any(text.encode()==raw for text in strings)
text=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',raw.decode())
assert m['prospective_synthetic']in text and re.search(r'HEAD is now at '+m['prospective_synthetic'][:7],text)
source=[];integration=[]
for line in text.splitlines():
 line=re.sub(r'^\d{4}-\d\d-\d\dT\S+\s*','',line)
 match=re.search(r'\[gw\d+\]\s+\[\s*\d+%\]\s+(PASSED|SKIPPED|FAILED|ERROR)\s+(.+)',line)
 if match:source.append({'node':match[2].strip(),'status':match[1]});continue
 if'::'in line and'[gw'not in line:
  match=re.match(r'(.*?\.py::.*?)\s+(PASSED|SKIPPED|FAILED|ERROR)',line)
  if match:integration.append({'node':match[1].strip(),'status':match[2]})
for rows,total,passed,skipped in[(source,1361,1184,177),(integration,152,131,21)]:
 assert len(rows)==len({x['node']for x in rows})==total
 assert sum(x['status']=='PASSED'for x in rows)==passed and sum(x['status']=='SKIPPED'for x in rows)==skipped
 assert not any(x['status']in['FAILED','ERROR']for x in rows)
shutdown=[x for x in source if'test_shutdown_response_order.py' in x['node']];assert len(shutdown)==10 and all(x['status']=='PASSED'for x in shutdown)
transport=[x for x in source if'run_outputs' in x['node']and'test_transport.py'in x['node']];assert len(transport)==30 and all(x['status']=='SKIPPED'for x in transport)
canvasintegration=[x for x in integration if'test_canvas_query_template.py'in x['node']];assert len(canvasintegration)==2 and all(x['status']=='SKIPPED'for x in canvasintegration)
assert re.search(r'1184 passed, 177 skipped, 15 warnings in 287.75s',text)and re.search(r'131 passed, 21 skipped, 1364 deselected in 1239.61s',text)
sourceinventory=json.loads(Path('/workspace/engineering/pr282-current-a54-source-LIGHT/private-current-1299-complete-source-body-mode-inventory.json').read_bytes())
apitree=json.loads((OUT/'actual-tested-tree-private.json').read_bytes());assert not apitree['truncated']and apitree['sha']==m['prospective_tree']
blobs={x['path']:(x['mode'],x['sha'])for x in apitree['tree']if x['type']=='blob'}
assert len(blobs)==len(sourceinventory)==1440
for row in sourceinventory:
 assert blobs[row['path']]==(row['mode'],row['blob'])
 path=ROOT/row['path'];body=os.readlink(path).encode()if row['mode']=='120000'else path.read_bytes();assert hashlib.sha256(body).hexdigest()==row['sha256']and stat.S_IMODE(path.lstat().st_mode)==row['fs_mode']
assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[HEAD,m['prospective_tree']]and not git('status','--porcelain')
q=OUT/'private-original-Windows-source-and-integration-complete-nodes.json'
with q.open('x')as f:json.dump({'source':source,'integration':integration},f,indent=2,sort_keys=True);f.write('\n')
q.chmod(0o600)
result={'status':'GO_METADATA_AND_ORIGINAL_WINDOWS_SOURCE_INTEGRATION_ONLY_PUBLISHED_CANVAS_RECEIPT_PENDING','source':HEAD,'target':m['target'],'original_runner_checkout':m['prospective_synthetic'],'actual_runner_parents':m['prospective_parents'],'actual_runner_tree':m['prospective_tree'],'complete_tree_Git_API_sourceFS_body_modes':1440,'nine_declared_PR_flows':declarations,'all25current_check_and_job_IDs_match':True,'late_Runtime_publisher_success':114514579799,'original_windows_log':acq['original_decoded'],'exact_copy_from_retained_structured_content':True,'original_copy_FAILURE_preserved':acq['original_local_copy_failure'],'wire_bytes':'UNKNOWN','source_results':{'unique':1361,'passed':1184,'skipped':177,'warnings':15,'seconds':287.75,'shutdown10':'PASS','transport30':'WindowsSKIP explicitlyLinuxonly'},'integration_results':{'unique':152,'passed':131,'skipped':21,'deselected':1364,'seconds':1239.61,'Canvas2':'WindowsSKIP explicitPOSIXbrowser gate'},'original_process_reader_cleanup':'UNKNOWN_OUTSIDE_TEST_ASSERTIONS_NO_UNIVERSAL_CLAIM','private_nodes':bind(q),'published_Core_Runtime_browser_gate':'LinuxSUCCESS_stepmetadata_ONLY_CURRENT_ORIGINAL_RECEIPT_PENDING','normal_policy':'rulesets[]/active[]/branchfalse visible;protection403UNKNOWN;normalready/expectedhead merge rootonly; noadminbypass','reviewer_acquisition_tests_imports_gate_rerun_or_mutations':False}
q=OUT/'independent-current1299-complete-metadata-and-original-Windows-proof.json'
with q.open('x')as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
q.chmod(0o600);print(json.dumps(bind(q)))
