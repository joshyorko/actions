"""Read retained hosted evidence; never refetch log or execute tests."""
import hashlib
import json
import pathlib
import re
import stat
import subprocess

ROOT=pathlib.Path('/workspace/successor-evidence/review308-windows0546-terminal')
REPO=pathlib.Path('/workspace/actions-pr308')
HEAD='0546ef30a30ff8229cb8fa6268e492c5cd74134e'
TREE='cca24f6fd8f6c18034ef3a12b77dd37e5fe64a97'
PRODUCER='6433af24a322be5f8a715934663b925d5b3cf044'
TARGET='48eeaf171e695d9b8ac140ea53239eaeb6eff331'
def api(path): return json.loads(subprocess.check_output(['gh','api',path]))
def sha(b): return hashlib.sha256(b).hexdigest()
path=ROOT/'decoded-job-private.log'; raw=path.read_bytes(); text=raw.decode('utf-8')
job=api('repos/joshyorko/actions/actions/jobs/114668292616')
run=api('repos/joshyorko/actions/actions/runs/38205604794')
assert job['status']=='completed' and job['conclusion']=='success' and job['run_id']==38205604794
assert run['head_sha']==HEAD and run['run_attempt']==1 and run['conclusion']=='failure'
assert re.search(r'HEAD is now at 6433af2 Merge '+HEAD+r' into '+TARGET,text)
producer=api('repos/joshyorko/actions/git/commits/'+PRODUCER)
assert producer['tree']['sha']==TREE and [p['sha'] for p in producer['parents']]==[TARGET,HEAD]
assert subprocess.check_output(['git','rev-parse',HEAD+'^{tree}'],cwd=REPO,text=True).strip()==TREE
assert re.findall(r'(\d+) passed, (\d+) skipped, (\d+) warnings in ([0-9.]+)s',text)==[('1412','225','15','399.99')]
assert re.findall(r'(\d+) passed, (\d+) skipped, (\d+) deselected in ([0-9.]+)s',text)==[('131','21','1640','1754.39')]
names=['test_existing_wait_events_and_echild_are_observations_not_invented_reaps','test_wait_timeout_keeps_primary_cleanup_error_and_unavailable_echild','test_actual_supervisor_wires_observer_only_when_requested[False-False]','test_actual_supervisor_wires_observer_only_when_requested[False-True]','test_actual_supervisor_wires_observer_only_when_requested[True-False]','test_actual_supervisor_wires_observer_only_when_requested[True-True]','test_raw_wait_error_retains_original_exception_identity','test_supervisor_model_setup_error_fails_without_real_fallback','test_rejected_metadata_attachment_does_not_replace_wait_primary']
results=[]
for name in names:
    node='test_owned_cleanup_evidence.py::'+name
    terminal=[l for l in text.splitlines() if node in l and re.search(r'\b(?:PASSED|FAILED|SKIPPED)\b',l)]
    assert len(terminal)==1 and 'PASSED' in terminal[0],name
    results.append({'node':node,'outcome':'PASSED'})
assert stat.S_IMODE(ROOT.stat().st_mode)==0o700 and stat.S_IMODE(path.stat().st_mode)==0o600
assert len(raw)==741199 and sha(raw)=='7a856e19801ba7f26795bfabfc48978088a794c8880c2acd8a2ed9ab46c782b8'
test_source=subprocess.check_output(['git','show',HEAD+':action_server/tests/action_server_tests/test_owned_cleanup_evidence.py'],cwd=REPO)
eebpath=pathlib.Path('/workspace/successor-evidence/pr308/eeb-windows-source-terminal-diagnosis.json')
eeb=json.loads(eebpath.read_text());assert eeb['conclusion']=='failure' and eeb['unit']['failed']==2
control={'initial_private_log_transport':'FAIL_BYTE_IDENTITY: line-based patch writer dropped5371 carriage returns','initial_observed_bytes':735828,'initial_observed_sha256':'c560c6dd7ba62f664501c3f3c85761aff75ff1b24d50382a6d77212840e23a44','corrected_transport':'serialize JSON then encode exactUTF8 preservingBOM/CRLF','corrected_bytes':len(raw),'corrected_sha256':sha(raw),'single_log_fetch':True,'initial_result_parser':'FAIL: expected one node occurrence but log has start+terminal rows; corrected filter requires explicit terminal outcome'}
(ROOT/'log-transport-control.json').write_text(json.dumps(control,indent=2)+'\n')
doc={'canonical_file':'docs/skills/repository-operations.md','insertion_point':'Hosted pull-request validation provenance paragraph','exact_delta':'When retaining a tool-decoded hosted job log, write its exact UTF-8 content without newline or BOM normalization and label the digest as decoded-content identity. Preserve carriage returns through any serialization transport; a line-based text patch can drop them. Record the job and overall run conclusions separately: one completed successful platform job can provide terminal suite evidence while another platform causes the workflow run to fail. Bind suite counts and named regression outcomes to that job\'s actual checkout tree. Parse the explicit terminal outcome for each node; its start row is not an additional result.','durable_learning':'Decoded byte identity and terminal per-job results require separate controls from whole workflow success.','evidence':['log-transport-control.json retains initial byte and parser failures plus corrections','terminal-review.json binds Windows jobSUCCESS/whole runFAILURE to actual syntheticcheckout tree and namedregressions'],'stale_or_ambiguous_guidance_removed':'Avoid normalized text hashes being labeled exact decoded content, start rows counted as outcomes, or job success labeled fullrun/currenthead acceptance.','remaining_uncertainty':'Currenteeb sourceFAIL2 and all outstanding native/managed/lease gates remain unqualified.','upstream_disposition':'none'}
(ROOT/'documentation-proposal.json').write_text(json.dumps(doc,indent=2)+'\n')
source_command='uv run --no-project --python 3.12 poetry run inv test-not-integration'
frozen_command='uv run --no-project --python 3.12 poetry run inv test-binary --jobs 0'
assert source_command in text and frozen_command in text
review={'verdict':'GO_TERMINAL_WINDOWS_PREDECESSOR_RECEIPT_SCOPED','repository':'joshyorko/actions','workflow':run['path'],'run':{k:run[k] for k in ['id','head_sha','event','status','conclusion','run_attempt']},'job':{k:job[k] for k in ['id','name','status','conclusion','run_id','started_at','completed_at']},'producer':{'sha':PRODUCER,'tree':TREE,'parents':[p['sha'] for p in producer['parents']],'whole_tree_equals_recorded_head':True,'authority':'oncefetched completedlog checkout message; independent RESTgitcommit metadata and immutablelocalhead tree'},'decoded_log':{'private_path':str(path),'bytes':len(raw),'sha256':sha(raw),'mode':'0600','ancestor_mode':'0700','fetches':1,'raw_content_exported':False,'digest_scope':'exact tool-decodedUTF8 content/BOM/CRLF; not predecodeHTTPwire bytes'},'source_suite':{'command':source_command,'passed':1412,'skipped':225,'warnings':15,'seconds':399.99},'frozen_suite':{'command':frozen_command,'passed':131,'skipped':21,'deselected':1640,'seconds':1754.39},'corrected_fake_wait_regressions':results,'immutable_fake_wait_test_source_sha256':sha(test_source),'fake_wait_scope':'Injected Linux wait primitives/frozen-clock controls onWindows; no realLinuxwaitpid/provider/lease proof. Frozen counts bind actual0546 binaries only.','current_eeb_failed_receipt':{'head':eeb['head'],'run':eeb['run'],'job':eeb['job'],'conclusion':'failure','unit':eeb['unit'],'failures':eeb['failures'],'receipt_sha256':sha(eebpath.read_bytes())},'qualification_bounds':['predecessor0546 only, notcurrenteeb/newsource','overall0546 runFAILURE remainsFAILURE','skips/deselections unverified','no currentnativebaseline/managedAction/MCP/uncappedcleanup/readers/lease acceptance','no publication/externalmutation/retry/native dispatch by reviewer'],'reviewer_actions':'One completeddecodedlog fetch; readonlymetadata/source parsing and ownprivate evidence only. Rawlogs/signedURLs excluded from safe export.','documentation_improvement':doc,'initial_controls_preserved':control,'upstream_disposition':'none'}
(ROOT/'terminal-review.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'verdict':review['verdict'],'bytes':len(raw),'sha256':sha(raw),'source_passed':1412,'frozen_passed':131,'named_regressions_passed':len(results),'run_conclusion':'failure','currenteeb_failure_retained':True}))
