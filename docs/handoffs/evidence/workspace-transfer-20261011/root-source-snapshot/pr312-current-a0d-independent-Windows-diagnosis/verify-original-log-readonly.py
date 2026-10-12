import collections,hashlib,json,re,stat,subprocess
from pathlib import Path
D=Path(__file__).parent;L=Path('/workspace/engineering/pr312-current-a0d-original-Windows-owned');C=Path('/workspace/engineering/pr312-current-a0d-one-CI-reconciliation');R=Path('/workspace/engineering/runtime-checkout-eol')
def binding(p):
 p=Path(p);z=p.read_bytes();return dict(path=str(p),bytes=len(z),sha256=hashlib.sha256(z).hexdigest())
def verify(row):assert binding(row['path'])=={k:row[k] for k in ('path','bytes','sha256')},row['path']
a=L/'root-one-original-decoded-log-acquisition.json';acq=json.loads(a.read_bytes());assert binding(a)['sha256']=='5f55a64439aedb2251a9b20da127415149762dfdabca776e591bc9406575cdc7'
for key in ['original_connector_response_private','original_decoded_actual_content','authorization']:
 verify(acq[key]);assert stat.S_IMODE(Path(acq[key]['path']).stat().st_mode)==0o600
assert stat.S_IMODE(L.stat().st_mode)==0o700
response=json.loads(Path(acq['original_connector_response_private']['path']).read_bytes());z=Path(acq['original_decoded_actual_content']['path']).read_bytes()
assert response['structuredContent']['content'].encode('utf-8')==z and not response['isError']
assert hashlib.sha256(z).hexdigest()=='d446e96f11c20ed63e59656e2ab81f315cde1e892ccfe32eb975ad79c8842336'
ls=z.decode('utf-8').splitlines();s='\n'.join(re.sub(r'^\d{4}-\d\d-\d\dT\S+Z\s?','',l) for l in ls)
meta=C/'OWNERFINAL-independent-current312-one-complete-CI-metadata-review.json';m=json.loads(meta.read_bytes())
for row in m['private_API_original_bindings']:verify(row)
cm=json.loads((C/'merge-commit.raw.private.json').read_bytes());hm=json.loads((C/'head-commit.raw.private.json').read_bytes())
checkout='71bb6ca2901bc4de7fae86058e72ac2a4016d248';head='77065131a0aee63d2b1f8621476374bdde3c7b65';base='a0d258a16095b95b1bf9000cb1201cddfaff4779';tree='edf1801e565692fb3f07b809b3a95b27981fe2fe'
assert cm['sha']==checkout and [p['sha'] for p in cm['parents']]==[base,head] and cm['commit']['tree']['sha']==hm['commit']['tree']['sha']==tree
assert f'HEAD is now at {checkout[:7]} Merge {head} into {base}' in s and checkout in s
source=re.findall(r'^\[(gw\d+)\]\s+\[\s*\d+%\]\s+(PASSED|SKIPPED|FAILED|ERROR)\s+(.+?)\s*$',s,re.M)
assert collections.Counter(st for gw,st,n in source)=={'PASSED':1166,'SKIPPED':142}
assert len(source)==len({n for gw,st,n in source})==1308 and {gw for gw,st,n in source}=={'gw0','gw1'}
assert '2 workers [1308 items]' in s and '1166 passed, 142 skipped, 14 warnings in 359.06s' in s
start=s.index('collecting ... collected 1461 items / 1311 deselected / 150 selected');end=s.index('=================================== FAILURES')
integration=re.findall(r'^((?:action_server_tests|contract_tests)\S+?::\S+)\s+(PASSED|SKIPPED|FAILED)\b',s[start:end],re.M)
assert len(integration)==len({n for n,st in integration})==150 and collections.Counter(st for n,st in integration)=={'PASSED':130,'SKIPPED':19,'FAILED':1}
failed=[n for n,st in integration if st=='FAILED'];assert failed==['action_server_tests\\test_cli_live_reload_multi_package.py::test_failed_watched_reload_keeps_both_packages_and_recovers']
assert '1 failed, 130 passed, 19 skipped, 1311 deselected in 1644.80s' in s
capture=s[s.index('---------------------------- Captured stdout call'):s.index('=========================== short test summary info')]
assert '\nWATCHED_FAILURE_LAST_GOOD_PASS A=A1 B=B1\n' in capture and 'WATCHED_RECOVERY_PASS' not in capture and 'WATCHED_RESTART_PASS' not in capture
assert '>               _shutdown(client, process)' in s and 'test_cli_live_reload_multi_package.py:341:' in s and 'test_cli_live_reload_multi_package.py:116: in _shutdown' in s
assert 'httpx.ReadError: [WinError 10053]' in s and '"POST /api/shutdown/ HTTP/1.1" 200' in capture and 'receive_response_headers.failed exception=ReadError' in capture
assert 'Killing process and subprocesses of:' in capture and '##[error]Process completed with exit code 1.' in s
eol=['action_server_tests\\test_database_shared.py::test_historical_migration_checkout_preserves_git_blob_bytes','contract_tests\\test_active_contracts.py::test_wheel_fixture_member_writer_preserves_lf_bytes_on_windows','contract_tests\\test_package_revision_schema.py::test_portable_fixture_is_stably_serialized','contract_tests\\test_package_revision_schema.py::test_consumer_reference_fixture_is_stably_serialized']
assert all(any(n==name and st=='PASSED' for gw,st,n in source) for name in eol)
git=lambda *args:subprocess.check_output(['git','-C',str(R),*args])
assert git('rev-parse','HEAD').decode().strip()==head and git('rev-parse','HEAD^{tree}').decode().strip()==tree and git('status','--porcelain')==b''
names=['action_server/tests/action_server_tests/test_cli_live_reload_multi_package.py','action_server/src/actions/server/_server.py','action_server/src/actions/server/_selftest.py']
for name in names:assert git('show',head+':'+name)==git('show',base+':'+name)
patch=D/'canonical-server-access-client-completion-proposed.patch'
patch.write_text('--- a/docs/skills/repository-operations.md\n+++ b/docs/skills/repository-operations.md\n@@\n+A server access-log status200 does not prove that the client received the\n+response. Classify shutdown failures at the exact client send/read boundary\n+and keep successful response delivery, natural exit and cleanup predicates\n+separate. Passing checkout-byte tests do not establish a shutdown cause.\n');patch.chmod(0o600)
census=D/'safe-complete-integration-node-census.json';census.write_text(json.dumps({'source_unique_nodes':1308,'source_counts':{'PASS':1166,'SKIP':142},'integration_unique_nodes':150,'integration':[{'node':n,'outcome':st} for n,st in integration]},indent=2)+'\n');census.chmod(0o600)
result={
'schema':'independent-original-PR312-Windows-diagnosis-v1',
'verdict':'HOLD_CURRENT770_ORIGINAL_WINDOWS_INTEGRATION_FAILURE_NO_EOL_CAUSE_OR_WAIVER',
'run':38138100611,'job':114466057789,'source':head,'base':base,'tree':tree,
'original_acquisition':binding(a),'original_log':acq['original_decoded_actual_content'],
'original_connector_response_private':acq['original_connector_response_private'],
'transport':'StructuredContent decoded content exactUTF8/CRLF; connector wire bytes unavailable. Only root original acquisition; reviewer acquired no additional log/artifact/API.',
'logged_checkout':{'sha':checkout,'API_ordered_parents':[base,head],'API_tree':tree,'source_API_tree_equal':True,'local_synthetic_commit_object':'UNAVAILABLE; existingAPI+loggedidentity qualified, no object fetch','original_API_metadata_review':binding(meta)},
'source_phase':{'PASS':1166,'SKIP':142,'FAIL':0,'ERROR':0,'unique_nodes':1308,'pytest_workers':['gw0','gw1'],'seconds':359.06,'warnings':14},
'integration_phase':{'PASS':130,'SKIP':19,'FAIL':1,'ERROR':0,'unique_selected_nodes':150,'collected':1461,'deselected':1311,'workers':'Sequential configured --jobs0; no xdist workers','seconds':1644.80,'configured_step_exit':1},
'failed_nodes':[{'node':failed[0],'phase':'Shutdown client response-header read AFTER readiness/last-good/correctedB2 assertions','FIRST90_timeout':False,'exception_category':'httpx.ReadError / WinError10053','trace':'Testline341 _shutdown; helperline116 client.post','last_good_marker':True,'correctedB2_semantic_assertions_reached_before_shutdown':True,'server_access_status':200,'client_success_response':'NOT_ADMITTED; receive_response_headers failed','natural_exit_rc1':'UNKNOWN_NOT_REACHED','final_recovery_restart_markers':'ABSENT; shutdownfailedbeforeprint/restart','legacy_stop_request':'Killing process/subprocesses observed','identity_owned_cleanup_result_readers_samplers_reaping':'UNKNOWN; access/legacykill lines not complete result'}],
'complete_integration_census':binding(census),
'LF_evidence':{'source_tests_logged_PASS':eol,'new_devutils_EOLists_in_this_Windows_Runtime_log':'NOT_OBSERVED; no invented Toolkit counters','original_frozen_artifact_members':'UNMEASURED; no artifact acquisition','cause':'UNKNOWN; no EOL-caused-shutdown attribution','unchanged_test_handler_selftest_Git_blobs_exactbase':names},
'bounded_next_boundary':'Existing conditional shutdown route synchronously calls _thread.interrupt_main before returning. Separately authorized service-free response-send ordering controls can test this boundary; not fixture tolerance, retry, timeout increase or sourcefix acceptance.',
'followon_startup_artifact_proposal':'Not requested. Solefailure is after readiness/recovery; startup80/88 receipt is not required to classify failed client shutdown read and cannot establish response completion or exit unless actual predicates recorded. Extra acquisition requires distinctrootrelease/exactjobsource tuple.',
'remaining_HOLD':['PR312 integration/currentWindows acceptance/Runtime1.0.3publication','Client200 delivery/naturalshutdown/completeownedcleanup','Cause/sourcefixqualification; no actual/rerun/native/private/newinfra release'],
'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md external exact4line proposal','Exact_delta':binding(patch),'Durable_learning_captured':'Access status differs from actual client receipt; classify reached phase and separate response, naturalexit, cleanup, LF evidence','Evidence':'Original serveraccess200/clientReadError10053; _shutdowntrace afterlastgood+correctedB2; fourLFrelatedsourcePASS nodes','Stale_or_ambiguous_guidance_removed':'Not FIRST90 recurrence; no naturalexit inferred from access200; no artifact bytes/cause inferred from sourceLF tests','Remaining_uncertainty':'Transport interruptioncause and actual parentexit/readers/reaping unresolved'},
'Upstream_disposition':'none','constructor':binding(__file__),
'non_gate_inspection_limits':'Exploratory missing assumed devutils contract path and saved jobs list schema mismatch failed before producing receipt; corrected knownshapes. Earlier saved jobstatusIN_PROGRESS is historical; original newer log supplies integrationterminal1.'
}
out=D/'OWNERFINAL-independent-original-PR312-Windows-shutdown-phase-diagnosis.json'
with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
out.chmod(0o600);print(json.dumps(binding(out)))
