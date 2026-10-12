from pathlib import Path
import ast,contextlib,copy,hashlib,io,json,re,stat,subprocess,types,urllib.parse,zipfile,xml.etree.ElementTree as ET,yaml
R=Path('/workspace/engineering');repo=R/'pr308';owned=R/'pr308-current776-fresh-threecase-owned';out=R/'pr308-current776-independent-actual-review'
S='7eb5bce946750555ab009f77592862920a901506';ST='3ff76037779763d0461ff3a755b900c9ed83dcf8';C='b673ddd761ba4ccd68e9baa8faaa9ab666df794e';CT='56d108fcdb5d43f7f27a8f2554fec51b702519f4'
def sha(b):return hashlib.sha256(b).hexdigest()
def bind(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def git(*a):return subprocess.check_output(['git',*a],cwd=repo)
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n');p.chmod(0o600)
p=owned/'frozen-original-threecase-proof.json';f=json.loads(p.read_text());assert bind(p)['bytes']==19720 and bind(p)['sha256']=='16b60ef82e907388a768642e17db2134b5dfaea966cfc7045aa1715879ca38f4'
for a in f['evidence']:assert bind(Path(a['path']))==a,a['path']
assert len(f['evidence'])==22
assert git('rev-parse','HEAD').decode().strip()==C and not git('status','--porcelain');assert git('rev-parse',C+'^{tree}').decode().strip()==CT and git('show','-s','--format=%P',C).decode().split()==[S];assert git('rev-parse',S+'^{tree}').decode().strip()==ST
zp=owned/'original-artifact-11697165172.zip';lp=owned/'original-job-114425127596.private.log';assert bind(zp)==f['acquisition']['ZIP'] and bind(lp)==f['acquisition']['decoded_original_job_log']
with zipfile.ZipFile(zp) as z:
 names=[i.filename for i in z.infolist()];assert len(names)==len(set(names))==7 and set(names)=={a['member'] for a in f['archive_members']}
 memberproof=[];rawbytes={}
 for i in z.infolist():
  assert not i.flag_bits&1 and stat.S_ISREG(i.external_attr>>16) and i.file_size<50000
  b=z.read(i);a=next(a for a in f['archive_members'] if a['member']==i.filename);assert len(b)==a['bytes'] and sha(b)==a['sha256'] and oct(i.external_attr>>16)==a['zip_recorded_mode'];ret=owned/'original-members'/i.filename;assert ret.read_bytes()==b and stat.S_IMODE(ret.stat().st_mode)==0o600
  rawbytes[i.filename]=b;memberproof.append({'member':i.filename,'bytes':len(b),'sha256':sha(b),'mode':oct(i.external_attr>>16)})
assert sum(a['bytes'] for a in memberproof)==17483
base='rcc-provider-rollback-evidence/'
def raw(name):return json.loads(rawbytes[base+name])
summary=raw('acceptance-summary.json');life=raw('lifecycle-receipt.json');stage=raw('staged-consumer-receipt.json');pub=raw('published-details-receipt.json');lifecycle_summary=raw('lifecycle-summary.json')
assert summary['admission']=={'issues':[],'passed':True};assert summary['source']['candidate_sha']==S and summary['source']['candidate_tree']==ST and summary['source']['workflow_control_sha']==C and summary['source']['workflow_control_tree']==CT
for obj in [life,pub]:assert obj['source']['commit']==S and obj['source']['tree']==ST
assert stage['source_commit']==S and stage['source_tree']==ST and pub['control']=={'commit':C,'tree':CT}
wfpath='.github/workflows/actions_runtime_rcc_provider_rollback.yml';wf=yaml.load(git('show',C+':'+wfpath),Loader=yaml.BaseLoader);step=next(s for s in wf['jobs']['build']['steps'] if s['name']=='Validate RCC rollback admission');steptext=step['run'];assert steptext.encode()==(owned/'immutable-C-validator.private.txt').read_bytes();code=steptext.split("python3 - <<'PY'\n",1)[1].rsplit('\nPY',1)[0];original_tree=ast.parse(code)
source_files=ast.literal_eval(next(n.value for n in original_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='source_files' for t in n.targets)));assert len(source_files)==9
nine=[];hashes={}
for name,path in source_files.items():
 body=git('show',S+':'+path);mode,kind,blob,leafpath=git('ls-tree',S,'--',path).decode().split();assert kind=='blob';actual={'name':name,'path':path,'git_mode':mode,'git_blob':blob,'bytes':len(body),'sha256':sha(body)};assert actual==next(x for x in f['strict_summary']['source_files'] if x['name']==name);assert actual['sha256']==summary['source']['files_sha256'][name];nine.append(actual);hashes[name]=sha(body)
junit=ET.fromstring(rawbytes['rcc-provider-rollback-junit.xml']);suites=list(junit.iter('testsuite'));cases=list(junit.iter('testcase'));assert len(cases)==3
counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ['tests','errors','failures','skipped']};assert counts=={'tests':3,'errors':0,'failures':0,'skipped':0};assert all(not list(c) for c in cases)
identities={(c.get('classname').rsplit('.',1)[-1],c.get('name')) for c in cases};expected=ast.literal_eval(next(n.value for n in original_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='expected_test_identities' for t in n.targets)));assert identities==expected
log=lp.read_text().splitlines();assert 'git log -1 --format=%H' in log[122] and C in log[123] and 'git log -1 --format=%H' in log[222] and S in log[223];assert any('3 passed' in l for l in log)
# Replay original validator once using only retained observations, never RCC or provider.
replay=out/'independent-offline-validator-recorded-inputs-v3';replay.mkdir(mode=0o700)
for name,b in rawbytes.items():
 if name.startswith(base):q=replay/Path(name).name;q.write_bytes(b);q.chmod(0o600)
virtual=Path(life['source']['module_origins']['runtime_adapter']).parents[4]
for name in ['runtime_adapter','actions_import','action_package_handler']:
 assert Path(life['source']['module_origins'][name])==virtual/source_files[name];assert life['source']['runtime_module_sha256'][name]==hashes[name]
def recorded_git(root,*args):
 assert args in [('rev-parse','HEAD'),('rev-parse','HEAD^{tree}')]
 assert Path(root) in [virtual,virtual.parent/'control'];control=Path(root)==virtual.parent/'control';return (C if control else S) if args[-1]=='HEAD' else (CT if control else ST)
def recorded_hash(path):
 path=Path(path)
 for name,p in source_files.items():
  if path==virtual/p:return hashes[name]
 if str(path)==pub['publication']['args'][0]:return summary['rcc']['sha256']
 if path==virtual/'action_server/bin/rcc':return summary['rcc']['action_server_default_sha256']
 raise AssertionError('unbound recorded file hash')
versions={'rcc_result':summary['rcc']['version'],'default_version_result':summary['rcc']['action_server_default_version']}
def recorded_version(key):return types.SimpleNamespace(stdout=versions[key])
transformed=copy.deepcopy(original_tree);transformed.body=[n for n in transformed.body if not isinstance(n,ast.FunctionDef) or n.name not in ['git_value','file_sha256']];removed=['git_value','file_sha256'];replacements=[]
for n in transformed.body:
 if isinstance(n,ast.Try):
  for a in n.body:
   if isinstance(a,ast.Assign) and isinstance(a.value,ast.Call) and isinstance(a.value.func,ast.Attribute) and isinstance(a.value.func.value,ast.Name) and a.value.func.value.id=='subprocess' and a.value.func.attr=='run':
    key=a.targets[0].id;assert key in versions;a.value=ast.Call(func=ast.Name(id='recorded_version',ctx=ast.Load()),args=[ast.Constant(key)],keywords=[]);replacements.append(key)
assert replacements==['rcc_result','default_version_result']
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess' for n in ast.walk(transformed))
env={'GITHUB_WORKSPACE':str(virtual.parent),'EVIDENCE_DIR':str(replay),'JUNIT_PATH':str(owned/'original-members/rcc-provider-rollback-junit.xml'),'EXPECTED_CANDIDATE_SHA':S,'EXPECTED_CANDIDATE_TREE':ST,'EXPECTED_CONTROL_SHA':C,'EXPECTED_RCC_SHA256':summary['rcc']['sha256'],'RCC_WORKER_LIBC_NAME':summary['runner']['libc_name'],'RCC_WORKER_LIBC_VERSION':summary['runner']['libc_version'],'RCC_PROVIDER_ROLLBACK_TEST_EXIT_CODE':str(summary['test']['exit_code']),'ACTIONS_RUNTIME_RCC_BINARY':pub['publication']['args'][0],'ACTION_SERVER_RCC_DEFAULT':str(virtual/'action_server/bin/rcc')}
for i,n in enumerate(transformed.body):
 if isinstance(n,ast.Import) and any(a.name=='os' for a in n.names):transformed.body.insert(i+1,ast.Assign(targets=[ast.Name(id='os',ctx=ast.Store())],value=ast.Name(id='recorded_os',ctx=ast.Load())));break
# Reconstruct the exact AST to prove only observation adapters changed.
restored=copy.deepcopy(transformed);restored.body=[n for n in restored.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='os' for t in n.targets))]
for i,n in enumerate(original_tree.body):
 if isinstance(n,ast.FunctionDef) and n.name in removed:restored.body.insert(i,copy.deepcopy(n))
for n,o in zip(restored.body,original_tree.body):
 if isinstance(n,ast.Try):
  for a,b in zip(n.body,o.body):
   if isinstance(a,ast.Assign) and isinstance(a.value,ast.Call) and isinstance(a.value.func,ast.Name) and a.value.func.id=='recorded_version':a.value=copy.deepcopy(b.value)
assert ast.dump(restored,include_attributes=False)==ast.dump(original_tree,include_attributes=False)
ns={'git_value':recorded_git,'file_sha256':recorded_hash,'recorded_version':recorded_version,'recorded_os':types.SimpleNamespace(environ=env)};captured=io.StringIO();exitcode=None
with contextlib.redirect_stdout(captured):
 try:exec(compile(ast.fix_missing_locations(transformed),'<independent-original-validator-recorded-inputs>','exec'),ns)
 except SystemExit as ex:exitcode=ex.code
assert exitcode==0 and ns['issues']==[]
for name in ['acceptance-summary.json','acceptance-summary.log','lifecycle-summary.json']:assert (replay/name).read_bytes()==rawbytes[base+name]
q=replay/'validator-output.private.log';q.write_text(captured.getvalue());q.chmod(0o600)
# Publication: one real runner invocation and canonical pair, without publication rerun.
publication=pub['publication'];payload=json.loads(publication['raw_json']);assert sha(publication['raw_json'].encode())==publication['raw_json_sha256'];assert type(publication['invocation_count']) is int and publication['invocation_count']==1
assert payload['specificationDigest']==publication['specification_digest']==summary['published_details']['specification_digest'] and payload['artifactDigest']==publication['artifact_digest']==summary['published_details']['artifact_digest']
assert ns['published_details_valid'] and ns['raw_aliases_match'] and ns['provider_is_loopback'] and ns['publish_args_valid']
# Two authored staged sample members bind both raw inventories and installed worker result.
test=ast.parse(git('show',S+':'+source_files['staged_consumer_test']));fun=next(n for n in test.body if isinstance(n,ast.FunctionDef) and n.name=='test_staged_package_executes_in_managed_rcc_runtime');constants={}
for n in fun.body:
 if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['manifest_bytes','action_bytes']:
  if isinstance(n.value,ast.Constant):constants[n.targets[0].id]=n.value.value
  else:
   assert isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='encode' and isinstance(n.value.func.value,ast.Constant) and isinstance(n.value.func.value.value,str) and ast.literal_eval(n.value.args[0])=='utf-8' and len(n.value.args)==1 and not n.value.keywords
   constants[n.targets[0].id]=n.value.func.value.value.encode('utf-8')
si=json.loads(stage['source_inventory']);ti=json.loads(stage['staged_inventory']);assert si==ti and len(si['entries'])==2 and {x['path'] for x in si['entries']}=={'action.py','package.yaml'}
for entry in si['entries']:
 b=constants['action_bytes' if entry['path']=='action.py' else 'manifest_bytes'];assert entry['size']==len(b) and entry['sha256']==sha(b) and entry['mode']==420
assert b'actions-core=1.0.2' in constants['manifest_bytes'];assert ns['staged_receipt_valid'] and ns['managed_worker_origins']
rt=life['action_server_process_exit'];assert life['shutdown_http_status']==rt['shutdown_http_status']==200 and rt['returncode_before_forced_cleanup']==1 and rt['forced_stop_used'] is False and rt['returncode_after_forced_cleanup']==1 and rt['returncode_after_forced_cleanup_is_natural_evidence'] is False and rt['owned_descendants_before_stop']==rt['same_owned_descendants_remaining_after_stop']==[]
assert life['provider_ops_before_failure']==life['provider_ops_after_failure']==life['provider_ops_after_recovery'] and len(life['provider_ops_before_failure'])==2
for name,result in [('first_run','last-good'),('second_run','last-good'),('recovered_run','recovered')]:assert life[name]['status']==2 and life[name]['result']==result
# The actual workflow source authority has three reviewed opt-in branches, unchanged filter.
branches=wf['on']['push']['branches'];assert branches==['test/rcc-provider-rollback-hosted-20261010','fix/rcc-published-artifact-details-20261010','fix/rcc-candidate-wheel-identities-20261010'];assert wf['on']['push']['paths']==yaml.load(git('show','77647484b3cdd8e18aabf344a4018ea8ed8e3ea0:'+wfpath),Loader=yaml.BaseLoader)['on']['push']['paths']
proposal=Path(f['Documentation_improvement']['Exact_proposal']['path']);assert bind(proposal)==f['Documentation_improvement']['Exact_proposal'];assert branches[-1] in proposal.read_text()
assert not git('status','--porcelain') and bind(p)=={'path':str(p),'bytes':19720,'sha256':'16b60ef82e907388a768642e17db2134b5dfaea966cfc7045aa1715879ca38f4'}
proof={'schema':'independent-original-threecase-byte-proof-v1','source':{'sha':S,'tree':ST},'control':{'sha':C,'tree':CT,'sole_parent':S},'all22_references_verified':True,'original':bind(p),'ZIP':bind(zp),'decoded_original_log':bind(lp),'all7_original_archive_members':memberproof,'raw_members_equal_owner_retained_and_private0600':True,'JUnit_counts':counts,'JUnit_identities':[list(x) for x in sorted(identities)],'actual_C_and_S_checkout_SHA_original_log_lines':[124,224],'immutable_Git_trees_match_raw_receipts':True,'all9_source_mode_blob_hash_records':nine,'independent_offline_validator':{'actual_binary_provider_or_test_execution':False,'exit':exitcode,'issues':ns['issues'],'original_strict_predicate_AST_restored_exact':True,'observation_adapters':['git_value','file_sha256','two recorded RCCversion values','private os.environ proxy'],'regenerated_summary_files_byte_exact_original':['acceptance-summary.json','acceptance-summary.log','lifecycle-summary.json'],'output':bind(q)},'publication':{'invocations':1,'raw_pair_and_aliases_args_valid':True,'raw_payload_sha256':publication['raw_json_sha256'],'RCCsha':pub['rcc']['sha256'],'RCCversion':pub['rcc']['version'],'scope':'publication-details case only; other two cases have separate providers/environments'},'staged_core':{'version':'1.0.2','member_count':2,'authored_source_staged_inventory_bytes_sizes_modes_equal':True,'managed_worker_and_Core_origins_verified':True,'not_wholeCore_or_wheel_proof':True},'lifecycle':{'HTTP':200,'natural_return_before_separate_cleanup':1,'forced_stop_used':False,'post_cleanup_return':1,'post_cleanup_is_natural_evidence':False,'captured_before':0,'same_captured_remaining':0,'provider_operations_count':2,'provider_operations_unchanged':True,'persisted_runs_status2_and_expected_results':True,'scope':'captured tree only; source treats psutil inspection failure as empty, so no complete snapshot/universal reap proof'},'actual_control_three_branches':branches,'path_filter_exact_accepted_target':True,'canonical':bind(proposal),'source_clean_and_owner_frozen_inputs_unchanged':True,'no_download_native_provider_or_binary_rerun':True}
q=out/'independent-original-byte-identity-and-offline-proof.json';write(q,proof);print(json.dumps(bind(q)))
