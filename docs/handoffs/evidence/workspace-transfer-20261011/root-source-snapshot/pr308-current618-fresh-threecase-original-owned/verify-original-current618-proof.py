from pathlib import Path
import ast,contextlib,hashlib,io,json,os,re,stat,subprocess,types,zipfile,xml.etree.ElementTree as ET,yaml
D=Path('/workspace/engineering/pr308-current618-fresh-threecase-original-owned');R=Path('/workspace/engineering/pr308');M=Path('/workspace/engineering/pr308-current618-fresh-threecase-metadata-owned')
S='c10380a4d2ebc6f0aca63eb85c8f84a337da4962';ST='21676c626a933c2d55761ec85ecf26fe0eef26bb';C='d5a3d2f53737f4f5380b6ecb7fb93d1a651f005d';CT='fa3f7728d315c9a192f88e17acf15f164d4eee13'
def sha(b):return hashlib.sha256(b).hexdigest()
def bind(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
assert git('rev-parse','HEAD').decode().strip()==C and not git('status','--porcelain')
assert git('rev-parse',C+'^{tree}').decode().strip()==CT and git('show','-s','--format=%P',C).decode().split()==[S]
assert git('rev-parse',S+'^{tree}').decode().strip()==ST
zp=D/'original-artifact-11699213923.zip';lp=D/'job-114449993317-original.private.log';assert zp.stat().st_size==8664 and sha(zp.read_bytes())=='375684fb49460e48451184eae58c7ec26f3b5849d29ab7333b3147b8ef1995f6'
base='rcc-provider-rollback-evidence/';names={base+x for x in ['acceptance-summary.json','acceptance-summary.log','staged-consumer-receipt.json','published-details-receipt.json','lifecycle-summary.json','lifecycle-receipt.json']}|{'rcc-provider-rollback-junit.xml'}
z=zipfile.ZipFile(zp);infos=z.infolist();assert len(infos)==7 and {i.filename for i in infos}==names and sum(i.file_size for i in infos)<100000
orig=D/'original-members';orig.mkdir(mode=0o700);inv=[]
for i in infos:
 assert not i.flag_bits&1 and stat.S_ISREG(i.external_attr>>16) and i.file_size<50000
 b=z.read(i);p=orig/i.filename;p.parent.mkdir(mode=0o700,exist_ok=True);fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(fd,b);os.close(fd);assert p.read_bytes()==b
 inv.append({'member':i.filename,'bytes':len(b),'sha256':sha(b),'zip_recorded_mode':oct(i.external_attr>>16),'zip_CRC32':f'{i.CRC:08x}','compression':i.compress_type,'retained_private_mode':'0600','original_bytes_equal':True})
j=lambda n:json.loads(z.read(base+n));summary=j('acceptance-summary.json');life=j('lifecycle-receipt.json');stage=j('staged-consumer-receipt.json');pub=j('published-details-receipt.json');lsum=j('lifecycle-summary.json')
assert summary['admission']=={'issues':[],'passed':True}
assert summary['source']['candidate_sha']==S and summary['source']['candidate_tree']==ST and summary['source']['workflow_control_sha']==C and summary['source']['workflow_control_tree']==CT
assert life['source']['commit']==stage['source_commit']==pub['source']['commit']==S
assert life['source']['tree']==stage['source_tree']==pub['source']['tree']==ST and pub['control']=={'commit':C,'tree':CT}
raw=json.loads(pub['publication']['raw_json']);assert sha(pub['publication']['raw_json'].encode())==pub['publication']['raw_json_sha256']==summary['published_details']['raw_json_sha256']
assert raw['specificationDigest']==pub['publication']['specification_digest']==summary['published_details']['specification_digest'];assert raw['artifactDigest']==pub['publication']['artifact_digest']==summary['published_details']['artifact_digest']
wfpath='.github/workflows/actions_runtime_rcc_provider_rollback.yml';wf=yaml.safe_load(git('show',C+':'+wfpath));step=next(s for s in wf['jobs']['build']['steps'] if s['name']=='Validate RCC rollback admission');code=step['run'].split("python3 - <<'PY'\n",1)[1].rsplit('\nPY',1)[0];tree=ast.parse(code)
source_files=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='source_files' for t in n.targets)))
sourceproof=[];hashes={}
for name,p in source_files.items():
 b=git('show',S+':'+p);h=sha(b);mode,typ,blob,_=git('ls-tree',S,'--',p).decode().split();assert typ=='blob' and summary['source']['files_sha256'][name]==h;hashes[name]=h;sourceproof.append({'name':name,'path':p,'git_mode':mode,'git_blob':blob,'bytes':len(b),'sha256':h})
assert len(sourceproof)==9
root=ET.fromstring(z.read('rcc-provider-rollback-junit.xml'));suites=list(root.iter('testsuite'));cases=list(root.iter('testcase'));counts={k:sum(int(s.attrib[k]) for s in suites) for k in ['tests','errors','failures','skipped']};assert counts=={'tests':3,'errors':0,'failures':0,'skipped':0} and len(cases)==3 and all(not list(c) for c in cases)
caseids=[{'module':x.attrib['classname'].split('.')[-1],'case':x.attrib['name']} for x in cases]
expected=[('test_current_candidate_import_rollback','test_current_candidate_failed_reload_keeps_last_good_action_usable'),('test_source_staging_rcc_consumer','test_staged_package_executes_in_managed_rcc_runtime'),('test_source_staging_rcc_consumer','test_published_artifact_details_preserves_one_rcc_identity_pair')]
assert {(x['module'],x['case']) for x in caseids}==set(expected)
log=lp.read_text().splitlines();assert 'git log -1 --format=%H' in log[122] and C in log[123];assert 'git log -1 --format=%H' in log[222] and S in log[223]
# Replay the exact validator predicates without executing RCC, provider, tests or commands from receipts.
# Hosted Git and RCC observations are bound recorded inputs; candidate file bytes come from immutable Git blobs.
virtual_candidate=Path(life['source']['module_origins']['runtime_adapter']).parents[4]
assert all(Path(life['source']['module_origins'][n])==virtual_candidate/source_files[n] for n in ['runtime_adapter','actions_import','action_package_handler'])
replay=D/'offline-validator-regenerated';replay.mkdir(mode=0o700)
for i in infos:
 if i.filename.startswith(base): (replay/Path(i.filename).name).write_bytes(z.read(i))
def recorded_git(root,*args):
 assert tuple(args) in [('rev-parse','HEAD'),('rev-parse','HEAD^{tree}')]
 is_c=Path(root).name=='control';return (C if is_c else S) if args[-1]=='HEAD' else (CT if is_c else ST)
def recorded_filehash(p):
 p=Path(p)
 for n,rel in source_files.items():
  if p==virtual_candidate/rel:return hashes[n]
 if str(p)==pub['publication']['args'][0]:return summary['rcc']['sha256']
 if str(p)==default_path:return summary['rcc']['action_server_default_sha256']
 raise AssertionError('unbound file hash observation')
def recorded_version(label):return types.SimpleNamespace(stdout=summary['rcc']['version' if label=='primary' else 'action_server_default_version'])
removed=[];replacement=[]
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name in ('git_value','file_sha256'):
  removed.append(n.name);continue
 if isinstance(n,ast.Try):
  for a in n.body:
   if isinstance(a,ast.Assign) and isinstance(a.value,ast.Call) and isinstance(a.value.func,ast.Attribute) and isinstance(a.value.func.value,ast.Name) and a.value.func.value.id=='subprocess' and a.value.func.attr=='run':
    target=a.targets[0].id;assert target in ('rcc_result','default_version_result');a.value=ast.Call(func=ast.Name(id='recorded_version',ctx=ast.Load()),args=[ast.Constant('primary' if target=='rcc_result' else 'default')],keywords=[]);replacement.append(target)
 replacement_tree_dummy=None
# Keep all strict predicate expressions and summary construction unchanged.
tree.body=[n for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name not in removed];assert removed==['git_value','file_sha256'] and replacement==['rcc_result','default_version_result']
default_path=str(virtual_candidate/'action_server/bin/rcc')
env={'GITHUB_WORKSPACE':str(virtual_candidate.parent),'EVIDENCE_DIR':str(replay),'JUNIT_PATH':str(orig/'rcc-provider-rollback-junit.xml'),'EXPECTED_CANDIDATE_SHA':S,'EXPECTED_CANDIDATE_TREE':ST,'EXPECTED_CONTROL_SHA':C,'EXPECTED_RCC_SHA256':summary['rcc']['sha256'],'RCC_WORKER_LIBC_NAME':summary['runner']['libc_name'],'RCC_WORKER_LIBC_VERSION':summary['runner']['libc_version'],'RCC_PROVIDER_ROLLBACK_TEST_EXIT_CODE':str(summary['test']['exit_code']),'ACTIONS_RUNTIME_RCC_BINARY':pub['publication']['args'][0],'ACTION_SERVER_RCC_DEFAULT':default_path}
# Source imports os; replace its alias with a proxy immediately after the import, leaving process environment untouched.
for index,n in enumerate(tree.body):
 if isinstance(n,ast.Import) and any(a.name=='os' for a in n.names):tree.body.insert(index+1,ast.Assign(targets=[ast.Name(id='os',ctx=ast.Store())],value=ast.Name(id='recorded_os',ctx=ast.Load())));break
ns={'git_value':recorded_git,'file_sha256':recorded_filehash,'recorded_version':recorded_version,'recorded_os':types.SimpleNamespace(environ=env)};out=io.StringIO();exitcode=None
with contextlib.redirect_stdout(out):
 try:exec(compile(ast.fix_missing_locations(tree),'<immutable-C-validator-offline-recorded-observations>','exec'),ns)
 except SystemExit as e:exitcode=e.code
assert exitcode==0 and ns['issues']==[]
(replay/'validator-output.private.log').write_text(out.getvalue())
assert (replay/'acceptance-summary.json').read_bytes()==z.read(base+'acceptance-summary.json')
assert (replay/'acceptance-summary.log').read_bytes()==z.read(base+'acceptance-summary.log')
assert (replay/'lifecycle-summary.json').read_bytes()==z.read(base+'lifecycle-summary.json')
# Compare the actual authored staged sample bytes and modes to both original inventories.
testtree=ast.parse(git('show',S+':'+source_files['staged_consumer_test']));f=next(n for n in testtree.body if isinstance(n,ast.FunctionDef) and n.name=='test_staged_package_executes_in_managed_rcc_runtime');constants={}
def literal_sample_bytes(n):
 if isinstance(n,ast.Constant) and isinstance(n.value,bytes):return n.value
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='encode' and isinstance(n.func.value,ast.Constant) and isinstance(n.func.value.value,str) and not n.keywords and len(n.args)<=1 and all(isinstance(a,ast.Constant) and a.value=='utf-8' for a in n.args):return n.func.value.value.encode('utf-8')
 raise AssertionError('unapproved authored constant expression')
for n in f.body:
 if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('manifest_bytes','action_bytes'):constants[n.targets[0].id]=literal_sample_bytes(n.value)
assert b'actions-core=1.0.2' in constants['manifest_bytes'] and len(constants)==2
si=json.loads(stage['source_inventory']);ti=json.loads(stage['staged_inventory']);assert si==ti
for entry in si['entries']:
 b=constants['action_bytes' if entry['path']=='action.py' else 'manifest_bytes'];assert len(b)==entry['size'] and sha(b)==entry['sha256'] and entry['mode']==420
rt=life['action_server_process_exit'];assert life['shutdown_http_status']==rt['shutdown_http_status']==200 and rt['returncode_before_forced_cleanup']==1 and rt['returncode_after_forced_cleanup']==1 and rt['returncode_after_forced_cleanup_is_natural_evidence'] is False and rt['forced_stop_used'] is False and rt['natural_exit_status']=='PASS'
assert rt['owned_descendants_before_stop']==rt['same_owned_descendants_remaining_after_stop']==[]
proposal=Path('/workspace/engineering/pr308-accepted-public-guard-independent-control-review/canonical-three-reviewed-control-branches-proposed.patch');assert sha(proposal.read_bytes())=='cd97355e9506350c286532607b87c5ce4ff492073a78fb72336517fe8164b5cd'
r={'status':'ORIGINAL_THREECASE_PROOF_VERIFIED_PENDING_INDEPENDENT_READ_FULL_CI_HOLD','PR':308,'source_S':{'commit':S,'tree':ST},'control_C':{'commit':C,'tree':CT,'sole_parent':S},'target':'6181b044c75de35386f1ae30e71725398b6a7feb','run':38132652607,'job':114449993317,'artifact':11699213923,'acquisition':{'original_MCP_calls_once_each':True,'previous_owned_search_no_original_found':True,'ZIP_reference_transfer_continuation':'Returned reusable file reference transferred once; no second GitHub artifact/log request','ZIP':bind(zp),'decoded_original_job_log':bind(lp),'raw_log_decode':'Connector decoded Unicode string persisted UTF-8, not original remote ZIP-of-joblogs byte claim','error_outputs_private':True,'inspector_output_privacy':'Allowlisted source and receipt categories only; no raw provider URI, private paths, signed URLs or raw job-log fields forwarded in this inspection.'},'archive_members':inv,'total_expanded_bytes':sum(i.file_size for i in infos),'original_members_exact_retained':True,'original_recorded_mode_vs_private_storage':'Archive members recorded100644; private retained bytes600 and parent700 intentionally. No remote ACL/xattr preservation claim.','actual_checkout_evidence':{'control_git_log_command_line':123,'control_SHA_output_line':124,'candidate_git_log_command_line':223,'candidate_SHA_output_line':224,'control_tree':CT,'candidate_tree':ST,'trees_bound_original_receipts_and_immutable_Git_objects':True,'not_synthetic_merge_reassignment':True},'strict_summary':{'schema_version':summary['schema_version'],'admission':summary['admission'],'source_files':sourceproof,'runtime_source_module_origins_hashes_verified':True,'JUnit':counts,'cases':caseids,'all_original_summary_bytes_regenerated_equal':True,'lifecycle_summary_original_bytes_regenerated_equal':True,'offline_validator_replay':{'exit_code':exitcode,'unchanged_strict_predicate_AST':True,'source_step_sha256':sha(step['run'].encode()),'recorded_observation_adapters':['git_value from immutable source/control and original checkout log','file_sha256 nine immutable Git bodies and original summary RCC observations','two RCC --version observations from original summary; no RCC execution','os.environ fixed recorded scope only'],'limits':'Replay checks raw predicates and summary derivation against recorded hosted observations. It is not a fresh RCC binary execution or an independent current host measurement.'}},'publication_details':{'invocation_count':pub['publication']['invocation_count'],'one_invocation_scope':'Publication-details case only; lifecycle and staged-consumer use separate providers/environments','RCC':pub['rcc'],'specification_digest':raw['specificationDigest'],'artifact_digest':raw['artifactDigest'],'raw_payload_sha256':pub['publication']['raw_json_sha256'],'raw_keys':sorted(raw),'raw_object_count':raw['objectCount'],'raw_uploaded_bytes':raw['uploadedBytes'],'raw_reused_bytes':raw['reusedBytes'],'raw_identity_pair_and_aliases_exact':True,'pure_return_API':'publish_artifact_details returns parse_published_artifact_details(_publish_artifact_payload(...)); one captured runner invocation binds the unmodified JSON pair. No second publication/query reconstructed.','published_args_and_loopback_provider_strict_validation':True},'staged_consumer':{'status':stage['status'],'Core_version':stage['typed_action_result']['core_version'],'original_authored_sample_bytes_inventory_modes_equal':True,'sample_entry_count':2,'managed_worker_prefix_and_core_origin':ns['managed_worker_origins'],'typed_return_fields_exact':True,'sample_only':'Published Core1.0.2 sample action/manifest, not wholeCore3/Runtime wheel or content-authority proof'},'lifecycle':{'status':life['status'],'provider_operations_before_failure_after_failure_after_recovery_equal':True,'provider_operation_count':len(life['provider_ops_before_failure']),'run_results':{n:{'status':life[n]['status'],'expected_result_equal':life[n]['result']==v} for n,v in [('first_run','last-good'),('second_run','last-good'),('recovered_run','recovered')]},'shutdown_HTTP_status':200,'natural_return_code_before_separate_cleanup':1,'post_cleanup_return_code':1,'post_cleanup_return_code_is_natural_evidence':False,'forced_stop_used':False,'captured_descendants_before_stop':0,'same_captured_survivors_after_stop':0,'cleanup_scope':'Original source records HTTP shutdown and natural poll return before separate cleanup; captured tree empty proves no captured survivors, not complete universal descendant reaping.'},'scope_limits':['Original successful threecase scopes only; frozen fullCI snapshot has15success and11pending of26','PolicyHTTP403UNKNOWN remainsHOLD, not bypass','NOT_RUN public negativeCLI2510 is not positiveparentguard qualification','No private134135/provider metadata/native/currentcoldinstall/fullwheel/publication/release acceptance','Nine source sample is not complete native producer qualification; accepted302adapter differs old92498','Old302d642/a346/54a receipts remain separate despite sampledcode equality'], 'Documentation_improvement':{'Canonical_file_proposed':'docs/skills/repository-operations.md','Exact_proposal':bind(proposal),'Durable_learning':'Three reviewed control push branches are permitted with unchanged path filter; source S/control C/fresh raw proof and fullCI tested merge remain separate. OriginalZIP/raw-vs-summary/nineGitbody sample and Core1.0.2/capturedcleanup limits verified.','Evidence':['current immutable control workflow threebranch list and successful currentpushrun','seven original members and unchanged validator offline raw-predicate replay','nine sourceGitmode/body hashes; original C/S checkout output','original lifecycle/rawpublication/staged inventory and exactJUnit'], 'Stale_or_ambiguous_guidance_removed':'Existing cd973 exact patch replaces stale two-branch permission list with three; no fabricated current execution or broad cleanup/Core3 claim added.','Remaining_uncertainty':'FullCI/policy/private/currentnegativeCLI/native/wholewheel gates remainHOLD; offline RCC observations bound original summary, not new binary measurement.'},'Upstream_disposition':'none','source_mutations_actual_runs_retries':False}
(D/'original-acquisition-and-member-inventory.json').write_text(json.dumps({'artifact':11699213923,'ZIP':bind(zp),'job_log':bind(lp),'members':inv},indent=2)+'\n')
r['evidence']=[bind(p) for p in sorted(D.rglob('*')) if p.is_file() and p.name not in ('OWNERFINAL-original-current618-threecase-proof.json','verify-original-current618-proof-private.log')]+[bind(M/'OWNERFINAL-fresh308-current618-threecase-original-artifact-metadata.json'),bind(proposal)]
for p in D.rglob('*'):
 if p.is_file():p.chmod(0o600)
q=D/'OWNERFINAL-original-current618-threecase-proof.json';q.write_text(json.dumps(r,indent=2)+'\n');q.chmod(0o600)
assert git('rev-parse','HEAD').decode().strip()==C and not git('status','--porcelain')
print(json.dumps({'receipt':bind(q),'expanded_bytes':r['total_expanded_bytes'],'cases':3,'admission_issues':0,'source_hashes':9,'full_CI':'HOLD'}))
