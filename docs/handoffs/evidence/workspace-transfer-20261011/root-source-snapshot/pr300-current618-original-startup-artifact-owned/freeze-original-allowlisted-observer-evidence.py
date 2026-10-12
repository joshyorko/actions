import json,hashlib,os,re,subprocess,zipfile,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ZIP=Path('/workspace/attachments/3d364fa6-2b44-4fb0-a31e-7a4c2e20e07e/pr300-original-current-Windows-startup-diagnostics-11699491969.zip')
SOURCE='7840057a8b055576d11d339d8c0fbb738927a491';CHECKOUT='2076246f60afc4c8fb069b4206699e57e006890b'
def digest(p):
 b=Path(p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def keys(x,allowed):assert set(x)<=set(allowed),(set(x)-set(allowed))
assert ZIP.stat().st_size==5776 and digest(ZIP)['sha256']=='fdf2ec1a863ef47c98ec26b1ff7d5a0c4a9be1598e1be7a29a1cbb1f863696a8'
assert os.stat(ROOT).st_mode&0o777==0o700 and os.stat(ZIP).st_mode&0o777==0o600
members=[];groups={}
with zipfile.ZipFile(ZIP) as z:
 assert len(z.infolist())==8 and len(set(z.namelist()))==8
 for i in z.infolist():
  p=ROOT/Path(i.filename).name;b=z.read(i);assert p.read_bytes()==b and os.stat(p).st_mode&0o777==0o600
  assert re.fullmatch(r'[0-9a-f]{16}-[1-4]\.json',i.filename)
  members.append(digest(p));groups.setdefault(i.filename.split('-')[0],{})[int(i.filename[-6])]=json.loads(b)
assert len(groups)==2
cases=[]
for prefix,docs in groups.items():
 assert set(docs)=={1,2,3,4};ident=docs[1]['identity']
 keys(ident,['GITHUB_RUN_ATTEMPT','GITHUB_RUN_ID','GITHUB_SHA','failure_cleanup_seconds','native_executable','nodeid','rcc_config','readiness_seconds','sample_seconds','schema','source_files'])
 assert (ident['GITHUB_SHA'],ident['GITHUB_RUN_ID'],ident['GITHUB_RUN_ATTEMPT'])==(CHECKOUT,'38129325703','1')
 assert ident['sample_seconds']==[80,88] and ident['readiness_seconds']==90 and ident['failure_cleanup_seconds']==20
 assert ident['nodeid'] in ['tests/action_server_tests/test_cli_live_reload_multi_package.py::test_failed_watched_reload_keeps_both_packages_and_recovers','tests/action_server_tests/test_cli_mcp_catalog_rollback.py::test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good[resource]']
 sourceproof=[]
 for rel,v in ident['source_files'].items():
  keys(v,['sha256','size']);b=subprocess.check_output(['git','show',SOURCE+':action_server/'+rel],cwd='/workspace/engineering/pr300');crlf=b.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n');assert len(crlf)==v['size'] and hashlib.sha256(crlf).hexdigest()==v['sha256']
  sourceproof.append({'source_path':'action_server/'+rel,'Git_blob_sha256':hashlib.sha256(b).hexdigest(),'reported_windows_CRLF':v,'exact_CRLF_representation_match':True})
 assert len(sourceproof)==7
 for index in (2,3):
  a=docs[index];keys(a,['elapsed_seconds','snapshot']);assert 80<=a['elapsed_seconds']<81 if index==2 else 88<=a['elapsed_seconds']<89
  s=a['snapshot'];keys(s,['captured_stderr','captured_stdout_characters','descendant_limit_reached','host_readers','pipes_closed','processes','rcc_internal_readers','wrapper_pid','wrapper_returncode'])
  keys(s['captured_stderr'],['characters','last_rcc_command']);assert s['rcc_internal_readers']=='unavailable_from_host';assert s['descendant_limit_reached'] is False
  keys(s['pipes_closed'],['stderr','stdout'])
  for h in s['host_readers']:keys(h,['alive','ident'])
  for proc in s['processes']:
   keys(proc,['command','cpu_seconds','created','handles','io_bytes','parent_pid','pid','status','effective_home_matches_launch','env_info_cache_exists','rcc_executable','staged_package'])
   keys(proc['io_bytes'],['read','write'])
  commands=[s['captured_stderr']['last_rcc_command']]+[p['command'] for p in s['processes']]
  for c in commands:
   if c is None:continue
   keys(c,['operation','bundled','config_argument_present','controller','json','no_pyc_management','no_retry_build','package_argument_present','robocorp','space','unrecognized_arguments'])
   assert c['operation'] in ('unavailable','holotree variables')
   if c['operation']!='unavailable':assert c['unrecognized_arguments']==0 and re.fullmatch('[0-9a-f]{16}',c['space'])
 final=docs[4];keys(final,['after_start_returned','exception','native_executable','outcome','sampler_alive','sampler_cancelled']);keys(final['after_start_returned'],['host_readers_alive','observation','returncode']);assert final['after_start_returned']['observation']=='host_only'
 keys(final['native_executable'],['sha256','size'])
 first,second=docs[2]['snapshot'],docs[3]['snapshot'];deltas=[]
 for p in first['processes']:
  q=next((q for q in second['processes'] if (q['pid'],q['created'],q['parent_pid'])==(p['pid'],p['created'],p['parent_pid'])),None)
  if q:deltas.append({'pid':p['pid'],'same_PID_creation_parent_tuple':True,'CPU_seconds_delta':q['cpu_seconds']-p['cpu_seconds'],'read_bytes_delta':q['io_bytes']['read']-p['io_bytes']['read'],'write_bytes_delta':q['io_bytes']['write']-p['io_bytes']['write'],'operation80':p['command']['operation'],'operation88':q['command']['operation']})
 cases.append({'nodeid':ident['nodeid'],'identity_source_proofs':sourceproof,'reported_rcc_config_measured_not_independently_generated_source_qualified':ident['rcc_config'],'snapshots80_88':docs[2:4] if isinstance(docs,list) else [docs[2],docs[3]],'same_identity_interval_deltas':deltas,'original_final_host_observation':final})
watched=next(c for c in cases if 'live_reload' in c['nodeid']);catalog=next(c for c in cases if 'catalog_rollback' in c['nodeid'])
rcc=next(d for d in watched['same_identity_interval_deltas'] if d['operation80']=='holotree variables');assert rcc['CPU_seconds_delta']==4.71875 and rcc['read_bytes_delta']==26735013 and rcc['write_bytes_delta']==70315694
assert watched['original_final_host_observation']['outcome']=='failed' and catalog['original_final_host_observation']['outcome']=='ready'
for c in cases:assert c['original_final_host_observation']['native_executable']=={'sha256':'6bf4d23df68b4ef87b7c2e2e8ddfb80fffc1c914a357f29953c2bb11f58963d0','size':57752576}
logreceipt=Path('/workspace/engineering/pr300-current618-original-Windows-owned/OWNERFINAL-original-current300-Windows-bounded-first-startup-diagnosis.json');assert digest(logreceipt)['sha256']=='56098cf774c36b7049e1cb288a2d427deee3df4996ac2cfbe2f7bde483f7401e'
guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text();lesson='Active RCC CPU/I/O does not establish a preparation cause;';assert lesson in guide
out={'schema':'original-current300-allowlisted-observer-evidence-v1','status':'GO_AUTHENTICATED_BOUNDED_EVIDENCE_ADMISSION__PR300_MERGE_HOLD','frozen_at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_head':SOURCE,'source_tree':'10e09d88027ca4fea512ff06c57efaab95755ffb','target':'6181b044c75de35386f1ae30e71725398b6a7feb','original_actual_checkout':CHECKOUT,'run':38129325703,'job':114440174596,'artifact_id':11699491969,'original_ZIP':digest(ZIP),'exact8_original_members':members,'one_connector_acquisition_no_retry':True,'safe_allowlist_no_unknown_fields_no_rawenv_URLs_provider_payloads':True,'original_connector_result_private0600_not_Git':digest(ROOT/'original-connector-result.private.json'),'cases':cases,'classification':{'whole_integration':{'PASS':130,'SKIP':19,'FAIL':1},'two_observer_nodes':'one FIRSTstartup90 TimeoutError and one successful catalog readiness; observer is not entire150 casecensus','active_same_identity_failed_RCC80_to88':{'CPU_seconds':4.71875,'read_bytes':26735013,'write_bytes':70315694},'failed_case_observation':'same RCC holotree variables process activeCPU/IO; capturedstdout0 and capturedstderr4308 unchanged; missinginternal marks/forwarding not identified','successful_case_observation':'RCC observed80, absent from88 bounded forest with new child; stderr4312→22868; final ready; disappearance not independentlyprovedreaping','failed_final_host_fields':{'returncode':15,'host_readers_alive':[False,False],'sampler_alive':False,'sampler_cancelled':True},'actual_cleanup_owned_snapshot_reap_live_zombie_error_predicates':'UNKNOWN_NOT_REPORTED','sampler_cancelled_is_cancel_requested_not_process_cleanup':True,'no_incomplete_note_not_cleanup_PASS':True,'process_identity_tuple_comparison_not_universal_live_handle_revalidation_or_all_descendant_census':True,'env_info_cache_absence_not_cache_defect':True,'native_binary_measured_report_identity_not_wholewheel_or_newnativequalification':True,'source_fix_or_timeout_change_justified':False,'root_cause':'UNKNOWN'},'original_log_diagnosis_unchanged':digest(logreceipt),'no_source_tests_rerun_native_browser_provider_installer_publication_merge_mutation':True,'documentation_improvement':{'exact_delta':'none; verified existing accepted terminal-census/activeCPU-I/O/missingmarks/host-cleanup paragraph already encodes this learning','verified_existing_text':lesson,'evidence':'same PID/creation/parent at80and88 adds4.71875CPU seconds and measured diskbytes while later hostrc15/readersfalse doesnot expose actual ownership cleanup','remaining_uncertainty':'internalvariables phase/ready emission/pipearrival/forwarding/actualcleanup unavailable; sourcecausation not established','stale_ambiguity':'separate current150casecensus from two-node observer and host observation from descendant cleanup'},'upstream_disposition':'none','immutable_constructor':digest(Path(__file__))}
p=ROOT/'OWNERFINAL-original-current300-eight-member-observer-evidence.json';assert not p.exists();p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');os.chmod(p,0o600);print(json.dumps(digest(p)))
