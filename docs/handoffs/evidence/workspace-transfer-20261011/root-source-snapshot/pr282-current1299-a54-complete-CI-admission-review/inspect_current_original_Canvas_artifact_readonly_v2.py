import ast,hashlib,json,stat,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

OUT=Path(__file__).resolve().parent;ROOT=Path('/workspace/engineering/pr282');BASE=Path('/workspace/engineering/pr282-current1299-one-original-Canvas-artifact')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bind(p):
 p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
owner=BASE/'OWNERFINAL-root-distinct-current1299-Canvas-artifact-connector-repair-result.json';p=json.loads(owner.read_bytes())
assert p['artifact_id']==11708206027 and p['run_id']==38154052443 and p['source_head']=='1299cc4bb6586f467d36ca124faaaaa77362695f'
assert p['original_cli_zero_byte_failure_retained']and p['one_connector_repair_call']and p['one_file_reference_transfer']
row=p['original_zip'];archive=Path(row['path']);assert archive.stat().st_size==2098 and sha(archive)=='2bb9ce2302d0a309e0718df767771b90b657a366f57fbd71dd773dca23c53de9'
metadata=json.loads((OUT/'current-Canvas-artifact-metadata.private.json').read_bytes());entry=next(a for a in metadata['artifacts']if a['id']==p['artifact_id']);assert entry['size_in_bytes']==2098 and entry['digest']=='sha256:'+sha(archive)and not entry['expired']
with zipfile.ZipFile(archive)as z:
 assert z.testzip()is None
 names=z.namelist();assert len(names)==len(set(names))==2 and set(names)=={'published-core-receipt.sanitized.json','junit.xml'}
 for member in z.infolist():
  assert not member.is_dir()and not member.filename.startswith('/')and '..'not in Path(member.filename).parts and stat.S_ISREG(member.external_attr>>16)
  body=z.read(member);bound=next(r['body']for r in p['verified_members']if r['name']==member.filename)
  assert len(body)==bound['bytes']and hashlib.sha256(body).hexdigest()==bound['sha256']and Path(bound['path']).read_bytes()==body
receipt=json.loads((BASE/'verified-connector-repair-members/published-core-receipt.sanitized.json').read_bytes())
xml=ET.fromstring((BASE/'verified-connector-repair-members/junit.xml').read_bytes());cases=list(xml.iter('testcase'))
assert xml.attrib['tests']=='1'and xml.attrib['skipped']==xml.attrib['failures']==xml.attrib['errors']=='0'
assert len(cases)==1 and cases[0].attrib['classname']=='tests.action_server_tests.mcp.test_canvas_query_template'and cases[0].attrib['name']=='test_canvas_template_runs_through_runtime_and_real_browser'and float(cases[0].attrib['time'])==39.973
assert not list(xml.iter('failure'))and not list(xml.iter('error'))and not list(xml.iter('skipped'))
m=json.loads((OUT/'safe-one-current1299-a54-complete-metadata-census.json').read_bytes())
assert receipt['scope']=='published-core Runtime/browser acceptance only'
assert receipt['source']=={'commit':m['prospective_synthetic'],'tree':m['prospective_tree'],'parents':[]}
core=receipt['published_core'];worker=core['measured_worker'];assert core['declared_version']==worker['version']=='1.0.3'
assert core['independently_verified_registry_wheel_sha256']=='8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265'
expected={'actions':'790b5e45f1a570f4d209879a47007ce94b73aab76c522bd6400867168726b0d2','actions.mcp':'c944de3b044a232143e66edd85ebd342b81b49cd100221689e22908d0dd5f365','actions.mcp._metadata':'c5750e654cb3c1e057705d80e65c4f6a935a3d81e46450d6dbf68d37f45cb48c'}
assert worker['module_hashes']==expected and set(worker['modules'])==set(expected)
assert all(Path(v).is_relative_to(Path(worker['worker_prefix']))for v in worker['modules'].values())
runtime=receipt['runtime'];assert runtime['module_origin']=='<checkout>/action_server/src/actions/server/__init__.py'and runtime['module_sha256']==sha(ROOT/'action_server/src/actions/server/__init__.py')
assert runtime['process_args'][1:3]==['-m','actions.server']and '--max-processes=2'in runtime['process_args']
assert all(runtime[k]is True for k in ['wrapper_reaped','descendant_snapshot_complete','descendant_reap_complete'])
assert all(runtime[k]==[]for k in ['active_readers','cleanup_errors','live_descendant_pids','zombie_descendant_pids'])
assert receipt['runtime_calls']==['published_core_identity','canvas_fixture_search:alpha','canvas_fixture_search:unmatched-query']
assert receipt['template_zip_sha256']==sha(ROOT/'action_server/src/actions/server/templates/zips/canvas-query.zip')
assert receipt['production_package_manifest_sha256']==sha(ROOT/'templates/canvas-query/package.yaml')
with zipfile.ZipFile(ROOT/'action_server/src/actions/server/templates/zips/canvas-query.zip')as z:assert receipt['built_resource_sha256']==hashlib.sha256(z.read('canvas.html')).hexdigest()
browser=receipt['browser'];lock=ROOT/'action_server/frontend/package-lock.json'
assert browser['status']=='passed'and browser['selection']=='explicit'and browser['temporary_root_removed']is True and browser['temporary_root'].startswith('/tmp/cv-')
assert browser['version']=='Google Chrome for Testing 151.0.7922.34'and browser['sha256']=='0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71'
assert browser['playwright_version']==json.loads(lock.read_bytes())['packages']['node_modules/@playwright/test']['version']=='1.62.1'and browser['frontend_lock_sha256']==sha(lock)
assert '/chromium-1234/chrome-linux64/chrome' in browser['path']and 'headless_shell'not in browser['path']
assert len(receipt['limits'])==4
workflow=yaml.load((ROOT/'.github/workflows/actions_runtime_tests.yml').read_bytes(),Loader=yaml.BaseLoader)
step=next(s for s in workflow['jobs']['build']['steps']if s.get('name')=='Verify Canvas published-Core Runtime and browser acceptance')
assert step['if']=="matrix.os == 'ubuntu-22.04'"
code=step['run'];assert 'test_canvas_template_runs_through_runtime_and_real_browser'in code
block=code.split("<<'PY'",1)[1].split('\nPY',1)[0];tree=ast.parse(block)
guards=[n.value for n in ast.walk(tree)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='receipt_ok'for t in n.targets)and isinstance(n.value,ast.BoolOp)]
assert len(guards)==1 and len(guards[0].values)==39
jobs=json.loads((OUT/'run-38154052443-jobs-page1.private.json').read_bytes())['jobs'];linux=next(j for j in jobs if j['id']==114513237728)
assert next(s for s in linux['steps']if s['name']==step['name'])['conclusion']=='success'
assert next(s for s in linux['steps']if s['name']=='Upload Canvas published-Core receipt')['conclusion']=='success'
originalfailure=json.loads((BASE/'OWNERFINAL-root-one-current1299-original-Canvas-artifact-data-acquisition.json').read_bytes());assert originalfailure['original_returncode']==1 and originalfailure['original_zip']['bytes']==0
result={'status':'PASS_ORIGINAL_CURRENT_CANVAS_PUBLISHED_CORE_RUNTIME_BROWSER_NARROW_GATE','artifact':11708206027,'run':38154052443,'Linux_job':114513237728,'root_repair_owner':bind(owner),'original_ZIP':bind(archive),'all_member_CRC_and_regular_paths':True,'member_count':2,'receipt':bind(BASE/'verified-connector-repair-members/published-core-receipt.sanitized.json'),'JUnit':bind(BASE/'verified-connector-repair-members/junit.xml'),'JUnit_exact_case':cases[0].attrib['name'],'JUnit_cases':1,'skips_failures_errors':0,'case_seconds':39.973,'source_PR_HEAD':m['source'],'actual_receipt_checkout':receipt['source']['commit'],'actual_tree':receipt['source']['tree'],'receipt_parents_original':[],'ordered_parents_authenticated_separately':m['prospective_parents'],'strict_original_validator_conjuncts':39,'sanitized_paths':'Originalnormalizedpath markers preserved; absolute containment was checked by unchanged39-conjunct gate before sanitization, not re-executed against normalizedpaths.','Core':'1.0.3/three measuredmemberhashes/prefixdistribution only;no completewheel/coldregistryproof','browser':'ExplicitfullChrome151/0b20/Playwright1.62.1/lockhash','resource_manifest_template_runtime_source':'Allcurrenttrackedbodydigests match','Runtime_cleanup':'3true plus4empty arrays; browsertemporaryrootremovedtrue, boundedpoint-in-time only','full_private_native_ChatGPT_artifactretrieval_release':'HOLD','original_CLI_zeroFAIL_retained':True,'repair':'Distinctauthorizedconnector/filetransfer;no secondghartifactcommand','additionalLinuxlogneeded':False,'reviewer_no_fetch_tests_imports_validator_execution_or_mutation':True}
q=OUT/'independent-current1299-original-Canvas-artifact-proof.json'
with q.open('x')as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
q.chmod(0o600);print(json.dumps(bind(q)))
