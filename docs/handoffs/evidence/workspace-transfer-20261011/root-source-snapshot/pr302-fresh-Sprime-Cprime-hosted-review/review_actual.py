import ast,dataclasses,hashlib,json,os,re,subprocess,sys,types,xml.etree.ElementTree as ET,zipfile
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit
r=Path('/workspace/engineering/pr302');out=Path('/workspace/engineering/pr302-fresh-Sprime-Cprime-hosted-review');members=out/'original-artifact-members';e=members/'rcc-provider-rollback-evidence';S='d642a3ac24f8da85101538bdfdf59b509fd74bfb';ST='fdf2823ebcdbd938b9047fd452c9fb13eb4be4e4';C='a346fd7dfca7a6490e6968d16c809a85814ff5b0';CT='a1c4aecb8aa83935245377cfecfa1de568a25dcf';T='774438b130afb2ead9bbc1c1b76cb6f91e72150a';RCCSHA='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(r),*a])
def blob(ref,p):return git('show',ref+':'+p)
def read(n):return json.loads((e/n).read_bytes())
s=read('acceptance-summary.json');l=read('lifecycle-receipt.json');ls=read('lifecycle-summary.json');p=read('published-details-receipt.json');v=read('staged-consumer-receipt.json')
cp=json.loads(Path('/workspace/engineering/pr302-actual310-control-refresh/control-Cprime-frozen-checkpoint.json').read_bytes());nine=cp['preserved_prior_acceptance']['source_nine']
assert s['admission']=={'issues':[],'passed':True};source=s['source'];assert source['candidate_sha']==S and source['candidate_tree']==ST and source['workflow_control_sha']==C and source['workflow_control_tree']==CT
assert l['status']==ls['status']==p['status']==v['status']=='PASS'
assert l['source']['commit']==S and l['source']['tree']==ST and l['source']['dirty_paths']==[]
files={}
for n,x in nine.items():
 raw=blob(S,x['path']);assert sha(raw)==s['source']['files_sha256'][n]==x['sha256'];assert blob(C,x['path'])==raw
 mode=git('ls-tree',S,'--',x['path']).decode().split()[0];assert mode==git('ls-tree',C,'--',x['path']).decode().split()[0];files[n]={'path':x['path'],'sha256':sha(raw),'mode':mode}
expected_delta=git('diff','--name-only',S+'^',S).decode().splitlines();assert set(l['source']['parent_delta_file_sha256'])==set(expected_delta)
for path,digest in l['source']['parent_delta_file_sha256'].items():assert sha(blob(S,path))==digest
for n in ['action_package_handler','actions_import','runtime_adapter']:
 assert l['source']['runtime_module_sha256'][n]==files[n]['sha256'];origin=PurePosixPath(l['source']['module_origins'][n]);assert str(origin).endswith('/candidate/'+files[n]['path'])
assert all(source[k] is True for k in ['receipt_source_matches_candidate','runtime_module_hashes_match_candidate','runtime_module_origins_match_candidate'])
# Actual exact three-case identity and counters independently derived from all XML cases.
t=ET.parse(members/'rcc-provider-rollback-junit.xml');cases=list(t.getroot().iter('testcase'));expected=[('tests.action_server_tests.test_current_candidate_import_rollback','test_current_candidate_failed_reload_keeps_last_good_action_usable'),('tests.action_server_tests.test_source_staging_rcc_consumer','test_staged_package_executes_in_managed_rcc_runtime'),('tests.action_server_tests.test_source_staging_rcc_consumer','test_published_artifact_details_preserves_one_rcc_identity_pair')]
assert [(x.get('classname'),x.get('name')) for x in cases]==expected and len(cases)==3
assert all(x.find(y) is None for x in cases for y in ['failure','error','skipped'])
assert s['test']['junit']=={'tests':3,'failures':0,'errors':0,'skipped':0}
suites=list(t.getroot().iter('testsuite'));assert sum(int(x.get('tests',0)) for x in suites)==3 and all(int(x.get(k,0))==0 for x in suites for k in ['failures','errors','skipped'])
assert s['test']['exit_code']==0 and type(s['test']['exit_code']) is int
for n in ['expected_test_identity_matches','junit_counts_match_testcases','managed_worker_origins_confirmed','provider_operations_unchanged','run_results_match','staged_action_sha256_matches','staged_consumer_receipt_valid','published_details_receipt_valid','forced_cleanup_returncode_observed']:assert s['test'][n] is True
assert s['test']['failed_case_names']==[]
for raw in [s['rcc'],p['rcc'],ls['rcc']]:assert raw['version']=='v18.19.3' and raw['sha256']==RCCSHA
assert s['rcc']['receipt_matches_binary'] is True and s['rcc']['action_server_default_sha256']==RCCSHA and s['rcc']['action_server_default_version']=='v18.19.3'
assert l['rcc_version']==v['rcc_version']=='v18.19.3' and l['rcc_sha256']==v['rcc_sha256']==RCCSHA
assert s['runner']['meets_artifact_minimum'] is True and s['runner']['libc_name']=='glibc'
# One actual details publish. Replay only the two exact pure parsers against its retained JSON;
# no subprocess, provider, package import, Runtime build or actual gate runs here.
publication=p['publication'];assert p['source']=={'commit':S,'tree':ST} and p['control']=={'commit':C,'tree':CT}
assert type(publication['invocation_count']) is int and publication['invocation_count']==1
provider=urlsplit(publication['provider']);assert provider.scheme=='http' and provider.hostname=='127.0.0.1' and provider.port and not provider.username and not provider.password and not provider.query and not provider.fragment
args=publication['args'];assert len(args)==8 and args[1:4]==['env','publish','--environment'] and args[5:]==['--json','--provider',publication['provider']] and PurePosixPath(args[4]).is_absolute() and PurePosixPath(args[4]).name=='package.yaml' and PurePosixPath(args[4]).parent.name=='minimal-package'
raw_json=publication['raw_json'];assert sha(raw_json.encode())==publication['raw_json_sha256'];payload=json.loads(raw_json)
assert payload['specificationDigest']==publication['specification_digest'] and payload['artifactDigest']==publication['artifact_digest']
assert s['published_details']=={'specification_digest':publication['specification_digest'],'artifact_digest':publication['artifact_digest'],'raw_json_sha256':publication['raw_json_sha256'],'single_invocation':True,'provider_is_loopback':True}
ast_tree=ast.parse(blob(S,'action_server/src/actions/server/_rcc_runtime_adapter.py'));defs=[]
for node in ast_tree.body:
 if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in {'RccRuntimeError','RccPublishedArtifactDetails','parse_artifact_digest','parse_published_artifact_details'}:defs.append(node)
assert {x.name for x in defs}=={'RccRuntimeError','RccPublishedArtifactDetails','parse_artifact_digest','parse_published_artifact_details'}
ns={'re':re,'dataclass':dataclasses.dataclass,'_DIGEST_RE':re.compile(r'^sha256:[0-9a-f]{64}$'),'__name__':'pr302_readonly_pure_parser_review'};mod=types.ModuleType(ns['__name__']);sys.modules[ns['__name__']]=mod;mod.__dict__.update(ns)
exec(compile(ast.Module(body=defs,type_ignores=[]),'immutable-Sprime-pure-parsers','exec'),mod.__dict__)
string_digest=mod.parse_artifact_digest(payload);details=mod.parse_published_artifact_details(payload);assert string_digest==details.artifact_digest==publication['artifact_digest'] and details.specification_digest==publication['specification_digest']
# Last-good descriptor preserved, cached provider artifact reused and recovered source generation changes.
assert l['descriptor_preserved_after_failure'] is True
before,after,rec=[l[k] for k in ['provider_ops_before_failure','provider_ops_after_failure','provider_ops_after_recovery']];assert before==after==rec and len(before)==2 and [x['phase'] for x in before]==['publish','acquire']
assert all(x['provider']==l['provider'] for x in before)
for n,result in [('first_run','last-good'),('second_run','last-good'),('recovered_run','recovered')]:assert type(l[n]['status']) is int and l[n]['status']==2 and l[n]['result']==result and l[n]['error_message'] is None
assert len(l['run_ids'])==len(set(l['run_ids']))==3 and l['run_ids']==[l[k]['id'] for k in ['first_run','second_run','recovered_run']]
i,f,rec=[l[k] for k in ['initial_runtime','final_runtime','recovered_runtime']];assert i==f and rec['artifact_digest']==i['artifact_digest'] and rec['source_generation']!=i['source_generation'] and rec['source_hash']==rec['source_generation']
assert all(x['kind']=='rcc' and x['contract_version']=='rcc-runtime/v1' and x['rcc_version']=='v18.19.3' and x['provider_context_bound'] is True and x['provider_reference']==l['provider'] for x in [i,f,rec])
# Managed Core1.0.2 staged bytes/inventory and origins, never wholewheel/Core1.0.3 qualification.
assert v['source_commit']==S and v['source_tree']==ST;assert v['source_sha256']==v['staged_sha256'] and set(v['source_sha256'])=={'action.py','package.yaml'}
si=json.loads(v['source_inventory']);di=json.loads(v['staged_inventory']);assert si==di and si['sourcePolicyVersion']==1 and len(si['entries'])==2
assert {x['path']:x['sha256'] for x in si['entries']}==v['source_sha256'];assert all(type(x['mode']) is int and x['mode']==420 and type(x['size']) is int and x['size']>0 for x in si['entries'])
result=v['typed_action_result'];assert set(result)=={'action_source_sha256','action_source_path','core_origin','core_version','python_executable'} and all(type(x) is str for x in result.values()) and result['core_version']=='1.0.2' and result['action_source_sha256']==v['source_sha256']['action.py']
root=PurePosixPath(v['managed_root']);assert PurePosixPath(result['core_origin']).is_relative_to(root) and PurePosixPath(result['python_executable']).is_relative_to(root) and '.rcc-runtime-sources' in PurePosixPath(result['action_source_path']).parts
# Natural return before cleanup separately verified. Only observed captured descendants are covered.
cleanup=l['action_server_process_exit'];assert l['shutdown_http_status']==cleanup['shutdown_http_status']==200 and cleanup['shutdown_request_succeeded'] is True
assert cleanup['natural_exit_status']=='PASS' and type(cleanup['returncode_before_forced_cleanup']) is int and cleanup['returncode_before_forced_cleanup']==1
assert cleanup['forced_stop_used'] is False and cleanup['forced_cleanup_returncode_observed'] is True and cleanup['returncode_after_forced_cleanup_is_natural_evidence'] is False
assert cleanup['owned_descendants_before_stop']==cleanup['same_owned_descendants_remaining_after_stop']==[]
assert s['test']['natural_return_code_before_cleanup']==1 and s['test']['forced_stop_used'] is False and s['test']['remaining_owned_descendant_count']==0
assert ls['action_server_process_exit']['returncode_before_forced_cleanup']==1 and ls['same_owned_descendants_remaining_after_stop']==[]
logp=out/'original-job-114409238566.log';lograw=logp.read_bytes();log=lograw.decode();assert '3 passed, 1 warning in 169.44s' in log and 'admission_passed=True' in log and S in log and C in log and RCCSHA in log
assert sum('PASSED' in line and name in line for line in log.splitlines() for _,name in expected)>=3
assert len(lograw)==908083 and sha(lograw)=='f1b471186942061f615a5ac9e83902a29cfcca83174ef22eac6bbf24d2967fc7'
archive=out/'original-artifact-11694723060.zip';assert archive.stat().st_size==8018 and sha(archive.read_bytes())=='59d3448321e40fe0801a2a5f836823752f0fb06932262150dc37ecd19bb8e2fb'
rows=[]
with zipfile.ZipFile(archive) as z:
 assert len(z.namelist())==7
 for n in z.namelist():b=z.read(n);assert (members/n).read_bytes()==b;rows.append({'member':n,'size':len(b),'sha256':sha(b)})
for path in [archive,logp,*[members/x['member'] for x in rows]]:assert (path.stat().st_mode&0o777)==0o600
patch=Path('/workspace/engineering/pr302-next-refresh-readonly/canonical-nine-source-bindings-proposed.patch');assert sha(patch.read_bytes())=='fef37515784cbf9fbb003ecca90ec0acb78d8e319bf2fd0ce2c2c1805ff955e6'
addition=''.join(x[1:]+'\n' for x in patch.read_text().splitlines() if x.startswith('+') and not x.startswith('+++')).encode();assert blob(S,'docs/skills/repository-operations.md').count(addition)==1 and blob(S,'docs/skills/repository-operations.md')==blob(C,'docs/skills/repository-operations.md')
res={'verdict':'GO_EXACT_PUBLIC_LINUX_SPRIME_THREE_CASE_ACCEPTANCE_ONLY','source_candidate':{'sha':S,'tree':ST},'control':{'sha':C,'tree':CT},'run':{'id':38118856632,'attempt':1,'event':'push','job':114409238566,'status':'completed/success'},'original_archive':{'id':11694723060,'path':str(archive),'size':8018,'sha256':sha(archive.read_bytes()),'members':rows},'complete_original_job_private':{'path':str(logp),'size':len(lograw),'sha256':sha(lograw),'decoded_original_UTF16_units':907587,'lines':len(log.splitlines()),'acquired_once':True,'mode':'0600','summary':'3PASS1warning169.44s'},'verified':{'source_nine_git_body_modes':files,'lifecycle_source_clean_and_11_parent_delta_hashes_exact':True,'three_Runtime_module_hashes_and_candidate_source_origins':True,'summary_admission_passed':True,'raw_three_receipts_statusPASS':True,'three_exact_JUnit':[(x.get('classname'),x.get('name'),x.get('time')) for x in cases],'JUnit':s['test']['junit'],'one_actual_publication_command':True,'same_retained_JSON_exact_pure_string_and_details_parsers':'PASS; no newpublish/Runtime execution','publication_pair':{k:publication[k] for k in ['specification_digest','artifact_digest','raw_json_sha256','invocation_count']},'lifecycle_same_two_provider_ops':['publish','acquire'],'three_unique_runs_status2_and_lastgood_recovered':True,'artifact_reused_source_generation_changes':True,'three_case_provider_artifacts':'Distinct fixture identities; do not combine publication details/staged/lifecycle into one shared operation','staged_two_entry_body_inventory_and_mode420_equal':True,'managed_Core102_typed_origin_containment':True,'RCC_and_default_version':'v18.19.3/Linux7e588c','runner_glibc_compatible':True,'profile_scope':'Inherited source/provider profile contract unchanged; isolated homes and loopbackprovider source assertions executed in these exact cases; no namedprofile/universal trust carrier claim','shutdown_http':200,'natural_return_before_cleanup':1,'forced_stop_used':False,'captured_descendants_before_after':{'before':0,'after':0},'postcleanup_return_is_natural_evidence':False,'complete_universal_descendant_reaping':'NOT_PROVED; captured-tree-only old observer scope','trace_scope':'23 summarized RCC entries; phase is a one-element list slice, not complete argv or universal child activity. Provider operations verified separately.'},'merge':'HOLD fresh fullCI/testedmerge and lateRuntimepublisher currentinventory pending; this actualGO is S-prime/C-prime publicLinux3case only','HOLDs':cp['preserved_HOLDs'],'historical_receipts':'63cf/26checks/artifact11691074610 remain originalS43a/Cba04; no current relabel','mutations':'Owned original downloads/extraction/reviewreceipt only; no checkout/ref/source/actual rerun/push/merge/application writes','Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md accepted fef375 source/control/nine-sample/fullproducer/testedmerge patch integrated S-prime, C-prime byte-exact','Durable_learning_captured':'Authenticate nine reported hashes under actual immutable candidate; keep actual control and fullCI testedmerge separate even tree-equal. One measured publication JSON supports both parser identities; captured shutdown and mapped Core1.0.2 are bounded evidence.','Evidence':'Fresh original11694723060 archive/API digest+all7members, completejob114409238566, exact3JUnit, rawcandidate/control tuple, nineGitbody/mode and natural-before-cleanup receipt above','Stale_or_ambiguous_guidance_removed':'Accepted fef375 explicitly blocks carrying oldcontrol receipts/sample hashes onto currentunion/fullproducer. New frozen proof has its own tuple; no extra cosmetic proposal.','Remaining_uncertainty':'CurrentfullCI/publisher/testedmerge, adapterchanged92498UNQUALIFIED, originalprivate/full134metadata, WindowsRCC/Core103/wholewheel/fullrelease and complete reaping remain unqualified.','accepted_patch_sha256':sha(patch.read_bytes()),'disposition':'Existing accepted exactdelta verified once, retained unchanged; newactualevidence supports its narrow scope.'},'Upstream_disposition':'none','review_script_sha256':sha(Path(__file__).read_bytes())}
f=out/'independent-fresh-three-case-actual-review.json';f.write_text(json.dumps(res,indent=2)+'\n');f.chmod(0o444);print(json.dumps({'verdict':res['verdict'],'receipt':str(f),'sha256':sha(f.read_bytes()),'size':f.stat().st_size}))
