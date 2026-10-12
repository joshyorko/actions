from pathlib import Path
import json,hashlib,zipfile,ast,subprocess
D=Path('/workspace/engineering/pr221-current776-linux-consumer-independent-review');B=Path('/workspace/engineering/pr221-current776-linux-consumer-preflight');P=B/'frozen-one-actual-current-linux-consumer-checkpoint.json'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
assert sha(P)=='f681018b9b516d9b969ea8d0786f4688ebb1c95b46e031217cf388645d8affaa' and P.stat().st_size==8866;j=json.loads(P.read_text());proposal=json.loads((B/'immutable-current776-linux-consumer-preexecution-proposal-v2.json').read_text());assert sha(B/'immutable-current776-linux-consumer-preexecution-proposal-v2.json')=='57a8beb87e5a1c03fae276e4b22d7fc8734d1f42cc3c739ceb989a0d946e73a7';assert sha(D/'independent-frozen-one-consumer-preexecution-review.json')==j['independent_preexecution_GO_sha256'];refs={}
def walk(x):
 if isinstance(x,dict):
  if {'path','sha256'}<=x.keys() and isinstance(x['path'],str) and x['path'].startswith('/'):
   assert sha(x['path'])==x['sha256'];e=bind(x['path']);assert 'bytes' not in x or e['bytes']==x['bytes'];refs[e['path']]=e
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(j);walk(proposal);A=Path(proposal['planned_ONE_actual_gateway']['attempt_root']);identity=json.loads((A/'attempt-identity.json').read_text());proof=json.loads((A/'consumer-proof.json').read_text());inventory=json.loads((A/'installed-inventory-raw.json').read_text());cleanup=json.loads((A/'execution-cleanup-receipt.json').read_text());report=json.loads((A/'pip-install-report.json').read_text());auth=json.loads((B/'root-one-actual-execution-authorization.json').read_text())
assert auth['actual_attempts_authorized']==1 and auth['proposal_sha256']==sha(B/'immutable-current776-linux-consumer-preexecution-proposal-v2.json') and auth['independent_GO_sha256']==j['independent_preexecution_GO_sha256'];assert auth['command']==proposal['planned_ONE_actual_gateway'];assert auth['status']=='ROOT_ONE_CURRENT_LINUX_CP312_CONSUMER_AUTHORIZED'
assert identity['runner_sha256']==j['runner_sha256']==sha(proposal['runner']['path']);assert identity['argv']==[identity['supervisor_python'],proposal['runner']['path'],'--worker',identity['temporary_root']];assert identity['worker_deadline_seconds']==595 and identity['overall_process_deadline_seconds']==600 and identity['cleanup_seconds']==5
assert identity['producer']==proof['producer']==j['producer'];assert identity['source_bindings']==proposal['literal_runner_source_bindings'];assert Path(identity['temporary_root']).parent==Path('/tmp') and Path(identity['temporary_root']).name.startswith('rt103-current776-') and not Path(identity['temporary_root']).exists();assert not (A/'supervisor-error.log').exists() and not (A/'cleanup-error.log').exists()
assert proof['status']=='passed' and proof['case_count']==j['case_count']==1 and proof['skips']==j['skips']==0 and proof['cli_version']==j['cli_version']=='1.0.3';assert (A/'cli-version.stdout.log').read_bytes()==b'1.0.3\n' and (A/'cli-version.stderr.log').read_bytes()==b'';assert proof['inventory_sha256']==sha(A/'installed-inventory-raw.json') and proof['pip_report_sha256']==sha(A/'pip-install-report.json');assert proof['input_admission']==j['input_admission']==json.loads((A/'input-admission.json').read_text());assert proof['runtime_wheel']==j['runtime_wheel'];assert sha(proof['runtime_wheel']['path'])==proof['runtime_wheel']['sha256'];assert proof['public_dependencies']==j['public_dependencies']
assert inventory['runtime_version']=='1.0.3' and inventory['wheel_sha256']==proof['runtime_wheel']['sha256'];prefix=Path(inventory['prefix']).resolve();assert prefix==Path(identity['temporary_root'])/'venv' and str(prefix)!=inventory['base_prefix'];assert set(inventory['modules'])=={'actions','actions.server','actions.mcp','actions_http'} and len(inventory['members'])==196
roots=[Path(x).resolve() for x in proposal['known_checkout_roots']]
for p in list(inventory['sys_path'])+list(inventory['modules'].values()):assert not any(Path(p or '.').resolve().is_relative_to(r) for r in roots)
for p in inventory['modules'].values():assert Path(p).resolve().is_relative_to(prefix)
with zipfile.ZipFile(proof['runtime_wheel']['path']) as z:
 expected={n for n in z.namelist() if n.endswith('.py')};assert len(expected)==196 and expected==set(inventory['members'])=={e['member'] for e in proof['members']}
 for e in proof['members']:
  assert Path(e['path']).resolve()==Path(inventory['members'][e['member']]).resolve();assert Path(e['path']).resolve().is_relative_to(prefix) and not any(Path(e['path']).resolve().is_relative_to(r) for r in roots);assert hashlib.sha256(z.read(e['member'])).hexdigest()==e['sha256'];ast.parse(z.read(e['member']))
 manifest=json.loads(Path(proposal['input_manifest']['path']).read_text());assert len(manifest['tracked_member_bindings'])==209
 for e in manifest['tracked_member_bindings']:
  body=z.read(e['member']);assert hashlib.sha256(body).hexdigest()==e['source_sha256']==e['member_sha256'];assert subprocess.check_output(['git','-C',proposal['harness']['checkout'],'show',proposal['actual_integration']['sha']+':'+e['source_path']])==body
# Compare exact dependency identities in actual pip report to unchanged floor literals, without exposing other report payload.
floor=ast.parse(Path(proposal['literal_runner_source_bindings']['floor']['path']).read_text());constants={}
for n in floor.body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
  try:constants[n.targets[0].id]=ast.literal_eval(n.value)
  except (ValueError,TypeError):pass
expected=proof['public_dependencies'];found={}
for item in report['install']:
 meta=item.get('metadata',{});name=meta.get('name','').lower().replace('_','-')
 if name in expected:
  assert name not in found;exp=expected[name];dl=item['download_info'];assert meta['version']==exp['version'] and dl['url']==exp['url'] and dl['archive_info']['hashes']['sha256']==exp['sha256'];found[name]=True
assert set(found)=={'actions-core','actions-http-helper'} and expected['actions-core']['version']==constants['EXPECTED_CORE']=='1.0.2' and expected['actions-http-helper']['version']==constants['EXPECTED_HELPER']=='1.0.3'
install=json.loads((A/'install-argv.json').read_text());assert install[0]==str(prefix/'bin/python');assert install[1:]==['-m','pip','install','--isolated','--no-cache-dir','--index-url','https://pypi.org/simple','--only-binary=:all:','--report',str(A/'pip-install-report.json'),proof['runtime_wheel']['path'],'actions-core==1.0.2','actions-http-helper==1.0.3'];assert 'No broken requirements found.' in (A/'worker.stdout.log').read_text()
flags=['wrapper_reaped','descendant_snapshot_complete','descendant_reap_complete','temporary_removed'];lists=['cleanup_errors','active_readers','observed_live_children','observed_zombie_children'];assert cleanup['status']==j['cleanup']['status']=='passed';assert all(cleanup[k] is True and j['cleanup'][k] is True for k in flags) and all(cleanup[k]==j['cleanup'][k]==[] for k in lists);assert cleanup['elapsed_seconds']==j['cleanup']['elapsed_seconds']<600
assert j['gateway_exit']==0 and (B/'original-one-actual-gateway.exit').read_bytes()==b'0\n';assert 'actual main robot run" was SUCCESS' in (B/'original-one-actual-gateway.log').read_text();assert j['input_admission']['generated_oauth_content']=='EMPTY_CONTENT_AUTHORITY_HOLD';assert j['input_admission']['record_entries']==215 and j['input_admission']['record_verified_entries']==214 and j['input_admission']['tracked_payload_source_matches']==209 and j['input_admission']['python_member_count']==196
out={'checkpoint':bind(P),'verified_unique_frozen_and_original_raw_bindings':len(refs),'raw_file_hash_bindings':list(refs.values()),'exact_one_root_authorization_and_command_matches_frozen_proposal':True,'runner_and_helpers_unchanged_after_actual':True,'one_consumer_case_no_skip_CLI103_Rcc_gateway_exit0':True,'installed_measured_member_hashes196_equal_original_current_wheel':True,'inventory_origin_and_prefix_outside_fifteen_known_checkout_roots':True,'all196_payloads_AST_parse_and_unchanged_full_member_privateCore_guard_required_before_proof_write':True,'current209_tracked_payloads_actual776_match':True,'exact_public_Core102_Helper103_versions_URLs_SHAs_in_pip_report':True,'pip_check_no_broken_requirements_reported':True,'exact_isolated_uncached_binary_only_install_argv':True,'strict_cleanup_flags_all4_true_lists_all4_empty':True,'owned_temporary_removed':True,'cleanup_elapsed_seconds':cleanup['elapsed_seconds'],'cleanup_observed_descendant_identities_count':len(cleanup['observed_descendants']),'installed_current_files_postcleanup':'ABSENT_BY_DESIGN; independently verifies recorded raw installed-member digest inventory against original wheel and reviewed guard control path; no claim of rehashing removed installed files now','producer':j['producer'],'limits':j['limits'],'review_execution_scope':'read-only byte/hash/JSON/ZIP/AST/Git metadata review; no pip/install/download/consumer/gateway/native/browser/provider or actual retry'}
p=D/'independent-original-one-consumer-result-proof.json';p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(bind(p),indent=2))
