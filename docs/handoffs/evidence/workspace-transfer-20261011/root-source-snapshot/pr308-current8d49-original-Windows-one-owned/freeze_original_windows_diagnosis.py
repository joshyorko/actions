import ast,hashlib,json,os,re,collections,subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent
SOURCE='8d49d0865ad5ad27b2d4e325ec135212080625e8'
def bind(p):
 p=Path(p);data=p.read_bytes();return {'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'mode':oct(p.stat().st_mode&0o777)}
def put(name,d):
 p=BASE/name;b=(json.dumps(d,sort_keys=True,indent=2)+'\n').encode();fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o400)
 with os.fdopen(fd,'wb') as f:f.write(b)
 return bind(p)
log=BASE/'original-decoded-Windows-job.log';raw=log.read_bytes();text=raw.decode();lines=text.splitlines()
response=json.loads((BASE/'original-full-logical-MCP-response.private.json').read_bytes());assert response['structuredContent']['content'].encode()==raw
rows=[]
for i,l in enumerate(lines,1):
 m=re.search(r'\[(gw\d+)\]\s+\[\s*\d+%\]\s+(PASSED|FAILED|SKIPPED|ERROR)\s+(.+?)\s*$',l)
 if m:rows.append({'line':i,'worker':m[1],'outcome':m[2],'node':m[3]})
assert len(rows)==len({r['node'] for r in rows})==1483
counts=dict(collections.Counter(r['outcome'] for r in rows));assert counts=={'SKIPPED':224,'PASSED':1257,'FAILED':2}
census=put('private-whole-line-unique-source-node-census.json',{'nodes':rows,'counts':counts,'total_unique':1483,'method':'wholeline terminal worker outcome, parameter spaces retained'})
first=next(i for i,l in enumerate(lines) if ' FAILURES ' in l)
last=next(i for i,l in enumerate(lines[first:],first) if 'warnings summary' in l)
stack=put('private-original-first-failure-blocks-and-static-errors.json',{'failure_lines':[{'line':i+1,'original':l} for i,l in enumerate(lines) if first<=i<last],'static_error_lines':[{'line':i+1,'original':l} for i,l in enumerate(lines) if ': error:' in l],'source_terminal':[l for l in lines if '2 failed, 1257 passed, 224 skipped' in l],'static_terminal':[l for l in lines if 'Found 7 errors in 1 file (checked 354 source files)' in l]})
run=json.loads((BASE/'run-stdout.private.json').read_bytes());job=json.loads((BASE/'job-stdout.private.json').read_bytes());synthetic=json.loads((BASE/'synthetic-commit-stdout.private.json').read_bytes())
assert run['id']==38164596550 and run['event']=='pull_request' and run['head_sha']==SOURCE and run['run_attempt']==1
assert job['id']==114544417671 and job['run_id']==run['id'] and job['head_sha']==SOURCE and job['conclusion']=='failure'
assert synthetic['sha']=='8d582979cad2aae844814abbe42ce1f2ca840ed9' and synthetic['tree']['sha']=='a80600809d373038ca76e445ba0b7b79bb7eeaa6'
assert [p['sha'] for p in synthetic['parents']]==['e2c81adce7858d5a952991ba9a8b7f72e902038a',SOURCE]
assert any(synthetic['sha'] in l and 'Z '+synthetic['sha'] in l for l in lines)
sourcefacts=[]
for p in ['action_server/src/actions/server/_rcc_runtime_adapter.py','action_server/tests/action_server_tests/test_rcc_runtime_adapter.py','action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py']:
 d=subprocess.check_output(['git','-C','/workspace/actions','show',SOURCE+':'+p]);work=Path('/workspace/engineering/pr308')/p;assert work.read_bytes()==d
 sourcefacts.append({'path':p,'Git_source':SOURCE,'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest(),'working_copy_exact':True})
facts=put('private-exact-failed-source-bindings.json',{'source':SOURCE,'source_facts':sourcefacts,'adapter_contract':'verify_rcc_version and verify_rcc_compatibility pass str(Path) to default/injectedrunner; budgets unchanged','seven_feature_sites':'sixos.getuid and oneos.getgid in cachehelper; fixtureLinuxskip doesnotexcludeWindowstypecheck'})
refs=[bind(p) for p in BASE.iterdir() if p.is_file() and p.name!='freeze_original_windows_diagnosis.py']+[bind(__file__),census,stack,facts]
# Deduplicate complete private references.
refs=list({r['path']:r for r in refs}.values())
proposal=Path('/workspace/engineering/pr308-current8d49-Windows-private-portability-successor/OWNERFINAL-private-current8d49-Windows-portability-source-PROPOSAL.json');refs.append(bind(proposal))
owner=put('OWNERFINAL-current8d49-one-original-Windows-source-and-static-failure-diagnosis.json',{'schema':'OWNERFINAL_CURRENT8D49_ONE_ORIGINAL_WINDOWS_FAILURE_DIAGNOSIS','decision':'HOLD_CURRENT_WINDOWS_SOURCE_AND_STATIC_GATES_PORTABILITY_DEFECTS_PROVED','source':SOURCE,'source_tree':synthetic['tree']['sha'],'original_checkout':{'sha':synthetic['sha'],'ordered_parents':[p['sha'] for p in synthetic['parents']],'tree':synthetic['tree']['sha'],'evidence':'original checkout git-log output + original authenticated API; local synthetic object UNAVAILABLE'},'job':{k:job[k] for k in ['id','run_id','head_sha','name','status','conclusion','started_at','completed_at']},'run':{k:run[k] for k in ['id','event','head_sha','head_branch','run_attempt','status','conclusion']},'full_source_outcomes':{'unique':1483,'passed':1257,'failed':2,'skipped':224,'errors':0,'warnings':15,'seconds':391.74,'workers':['gw0','gw1']},'failure_classification':{'tests':'Two hardcoded POSIX-string expectedarguments conflict with actual str(WindowsPath) renderedbackslashes; original900.0 equals900, no generalcommandbudget defect','static':'Sevenattr-defined errors: os.getuid/getgid absentfromWindowsstub; checked354files','integration':'SKIPPED_AFTER_SOURCEFAILURE; no originalintegration timeoutornewnativeclaim','production_adapter_regression':'NOT_ESTABLISHED; capturedarguments follow unchangedPathstrcontract'},'failed_nodes':[r['node'] for r in rows if r['outcome']=='FAILED'],'steps':[{k:s[k] for k in ['number','name','status','conclusion']} for s in job['steps']],'acquisition':{'supported_connector_calls':1,'direct_storage_downloads':0,'decodedUTF8_exact':True,'MCP_full_logical_response_retained':True,'original_wire_bytes':'UNKNOWN','initial_local_save':'execargumenttoolong beforefilewrite; originalstoredresponse savedwithoutnewnetworkcall'},'evidence':refs,'private_patch_proposal':bind(proposal),'operations':'Read-only original log once; metadata APIs once each; no rerun/native/productsource/ref changes. Private service-free portability proposal separate.','remaining_holds':['sourceadoption/freshfullandWindowsCI','allnewnativeRCC5/6qualification','release/private/provider/publication'],'documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; seven-line nativePath/POSIXfeature lesson bound in privatepatchproposal','Durable_learning':'Use actual nativePath rendering for argv assertions; runtimeplatformskip and staticplatformfeature availability are separate','Evidence':'original checkout/API +1483wholeline outcomes/twooriginalstacks/sevenmypyerrors +nineprivatecontrols','Stale_or_ambiguous_guidance_removed':'Avoid attributing fixtureformat assertionsto adapterregression/integrationtimeout; avoid Linuxskip⇒Windowsstaticexclusion','Remaining_uncertainty':'No productpatchadopted/newWindowsgate/nativequalification'},'upstream_disposition':'none; Actions-owned testportabilitydefects, no externalmutation'})
for r in refs:assert bind(r['path'])==r
print(json.dumps({'owner':owner,'references':len(refs),'unique_nodes':1483,'path_controls':9,'product_mutation':'NONE'}))
