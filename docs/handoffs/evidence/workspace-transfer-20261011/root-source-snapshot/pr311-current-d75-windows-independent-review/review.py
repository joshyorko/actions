from pathlib import Path
import hashlib
import json
import re
import subprocess
import zipfile

ROOT=Path('/workspace/engineering/pr311-current-d75-windows-diagnostics-owned')
OUT=Path('/workspace/engineering/pr311-current-d75-windows-independent-review')
REPO='/workspace/engineering/pr311'
HEAD='d75b25fb4c354e5c95bc0f639b426d6ff402104b'
CONTROL='e3c52c5cf3f2a4437a54af137f59264cc77d91ae'
ZIP=Path('/workspace/attachments/33e695fb-7000-461b-88c5-f7623b15ea0d/pr311-current-d75-windows-startup-diagnostics.zip')

def binding(p):
    b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def keys(d,expected):assert isinstance(d,dict) and set(d)==set(expected)
def file_id(d):
    keys(d,['size','sha256']);assert type(d['size']) is int and d['size']>=0
    assert re.fullmatch('[0-9a-f]{64}',d['sha256'])

run=json.loads((ROOT/'authenticated-run.json').read_text())
job=json.loads((ROOT/'authenticated-job.json').read_text())
assert run['id']==38110132836 and run['head_sha']==HEAD and run['event']=='pull_request' and run['run_attempt']==1
assert run['status']=='completed' and run['conclusion']=='success'
assert job['id']==114383803907 and job['head_sha']==HEAD and job['status']=='completed' and job['conclusion']=='success'
skipped=[s for s in job['steps'] if s['conclusion']=='skipped']
assert len(skipped)==1 and skipped[0]['name']=='Install project (not dev)' and skipped[0]['number']==6
assert all(s['conclusion'] in ('success','skipped') for s in job['steps'])
control=json.loads((ROOT/'authenticated-control.json').read_text())
assert control=={'sha':CONTROL,'tree':'35a5168a3904ba41e29047fec2a4cd3b50880a78','parents':['fbde0d3a248c47c9964851355f96575c89a87329',HEAD]}
inventory=json.loads((ROOT/'authenticated-artifact-inventory.json').read_text())
artifact=[a for a in inventory['artifacts'] if a['id']==11691314969][0]
assert artifact['name']=='native-startup-diagnostics-38110132836-1' and not artifact['expired']
assert artifact['size_in_bytes']==ZIP.stat().st_size==2582
assert artifact['digest']=='sha256:'+binding(ZIP)['sha256']=='sha256:0cd288b83a80bddb29e0add0c5f26f16aa6649c0c1582bcd1a8c7a332c6354e7'
reports=[];source_bindings=[];finals=[]
with zipfile.ZipFile(ZIP) as z:
    assert len(z.infolist())==4
    for member in z.infolist():
        p=ROOT/'reports'/member.filename
        assert member.filename==Path(member.filename).name
        assert z.read(member)==p.read_bytes()
        reports.append(binding(p))
for prefix in ['34ec97696df8d90c','7d0f2e912f58600f']:
    identity=json.loads((ROOT/'reports'/f'{prefix}-1.json').read_text())
    keys(identity,['identity']);d=identity['identity']
    keys(d,['GITHUB_RUN_ATTEMPT','GITHUB_RUN_ID','GITHUB_SHA','failure_cleanup_seconds','native_executable','nodeid','rcc_config','readiness_seconds','sample_seconds','schema','source_files'])
    assert (d['GITHUB_RUN_ID'],d['GITHUB_RUN_ATTEMPT'],d['GITHUB_SHA'])==('38110132836','1',CONTROL)
    assert (d['schema'],d['readiness_seconds'],d['failure_cleanup_seconds'],d['sample_seconds'])==(1,90,20,[80,88])
    assert d['native_executable']=={'status':'measured_after_start_returns'}
    file_id(d['rcc_config']);assert d['rcc_config']=={'size':61,'sha256':'1ad9ed9323e1e9250f60aad72598d1231cd861e93c15d41ad1ea568c3fbb0500'}
    assert len(d['source_files'])==7
    for path,measured in d['source_files'].items():
        file_id(measured)
        b=subprocess.check_output(['git','-C',REPO,'show',HEAD+':action_server/'+path]);windows=b.replace(b'\n',b'\r\n')
        assert measured=={'size':len(windows),'sha256':hashlib.sha256(windows).hexdigest()}
        source_bindings.append({'case':prefix,'path':path,'windows_crlf':measured})
    final=json.loads((ROOT/'reports'/f'{prefix}-2.json').read_text())
    keys(final,['after_start_returned','exception','native_executable','outcome','sampler_alive','sampler_cancelled'])
    assert final['exception'] is None and final['outcome']=='ready' and final['sampler_alive'] is False and final['sampler_cancelled'] is True
    assert final['after_start_returned']=={'host_readers_alive':[True,True],'observation':'host_only','returncode':None}
    file_id(final['native_executable'])
    assert final['native_executable']=={'size':57695232,'sha256':'f24c34ff4a65d477a524f21f44122517bb4a85462b1ca3e653232e5df9450be5'}
    finals.append({'nodeid':d['nodeid'],'final_initial_start_report':final})
leaf_admission=json.loads((ROOT/'authenticated-source-leaf-admission.json').read_text())
assert leaf_admission['control_tree']==control['tree'] and leaf_admission['authenticated_recursive_tree_untruncated']
assert leaf_admission['producer268_and_selected5_mode_blob_identity'] and leaf_admission['observed_seven_source_leaves_match_d75_git_blobs']
log=ROOT/'job114383803907-original-decoded.log';assert binding(log)['sha256']=='518f4d4a2cb8d28bcbb8a90f37747fe8248fb36b90f97b62f54db5fbc4f95fbb'
text=log.read_text();assert '131 passed, 18 skipped, 1166 deselected' in text
assert '1069 passed, 94 skipped, 14 warnings' in text
assert 'FAILED action_server_tests' not in text and 'startup cleanup did not fully complete' not in text and text.count('Progress')==0
former=['test_failed_watched_reload_keeps_both_packages_and_recovers','test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good[resource]','test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good[template]','test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good[prompt]','test_cli_resource_owner_history_across_reload_and_restart','test_successful_generation_switch_drains_old_run_on_its_source_snapshot']
passes=[]
for name in former:
    found=[l.split('Z ',1)[-1] for l in text.splitlines() if ('::'+name+' PASSED') in l and l.split('Z ',1)[-1].startswith('action_server_tests\\')]
    assert len(found)==1
    passes.append({'test_name':name,'actual_log_status':'PASS'})
proposal=OUT/'canonical-current-windows-readback-proposal.md'
proposal.write_text('''Current PR311 d75 Windows run38110132836/job114383803907 completed successfully at04:40:44Z. Its actual synthetic control is e3c52c5cf3f2a4437a54af137f59264cc77d91ae/tree35a5168a3904ba41e29047fec2a4cd3b50880a78 with ordered parentsfbde0d3a/d75b25fb. The original log reports131 integration passes,18skips and1166deselections; all six nodes that failed first startup in historical1151 have explicitPASS here. The nonintegration job reports1069passes/94skips. These are original log counters, not retained native JUnit claims.

The existing two-node observer artifact contains four original JSON records: initial identity and READY outcome for each node, with no retained80/88-second snapshot. Do not convert absent snapshots into measured startup duration or phase. At initial ready return, wrapper returncode is null and both host readers are alive: the service is still running as expected for the following test assertions, not being reported as cleaned up. Sampler cancellation was requested and sampler_alive is false. These fields do not prove eventual full descendant reaping or natural shutdown. No raw RCC Progress marks or actual cleanup result fields were retained, so interval sums and cleanup disjunctions remain unavailable.

Authenticated control leaf identity and Windows CRLF worktree hashes bind the seven reported source files; all268 tracked producer and five selected-test input blobs/modes match retained source checkpoints. The current61-byte RCC configuration digest and native executable digest differ from historical1151. Keep each run's measured artifact identity separate; a source match does not equate produced bytes. The current native hash is observer-measured and was not independently compared with a downloaded full native archive.

This passing current result removes the observed Windows job blocker for its exact source/control only. It does not prove a timeout root-cause fix, clear historical2999cb's failed native start, repair original1151, or satisfy a full issue/release acceptance graph. The already reviewed V2 test-only observation design remains available, but defer implementation and another actual run now: no current startup failure requires that discrimination wave. Root must separately reconcile complete exact-head merge gates. Original failures and their five incomplete20-second cleanup notes remain immutable historical evidence; retain unchanged90/20 gates and no prewarm/retry/configuration replacement.

Canonical destination proposed: docs/skills/repository-operations.md beside historical Windows diagnostic limits. Evidence: authenticated run/job/control/leaf records, original artifact11691314969 ZIP0cd288b8/four safe JSONs, private decoded log518f4d4a and independent receipt. Full raw log stays outside repository. Stale ambiguity removed: historical failures describe currentCI; no snapshots prove exact timing; READY initial fields are cleanup proof; a new pass establishes cause or repairs another branch. Remaining uncertainty: historical cause/native phases and full cleanup, complete merge/release gates. Upstream disposition: none.
''')
result={
 'verdict':'GO_EXACT_CURRENT_D75_WINDOWS_JOB_AND_BOUNDED_DIAGNOSTIC_READBACK; HOLD_TIMEOUT_ROOTCAUSE_FULL_CLEANUP_WHOLE_PR_AND_RELEASE',
 'scope':'existing terminal artifacts/log acquired once; read-only source/evidence review; no rerun,cancel,implementation or infrastructure',
 'run':run,'job':job,'actual_control':control,
 'authenticated_identity_bindings':[binding(ROOT/n) for n in ['authenticated-run.json','authenticated-job.json','authenticated-control.json','authenticated-artifact-inventory.json','authenticated-source-leaf-admission.json']],
 'original_artifact':artifact,'original_zip':binding(ZIP),'original_four_json':reports,'all_actual_report_fields_allowlisted':True,
 'windows_crlf_source_bindings':source_bindings,'source_admission':'authenticated untruncated synthetic-control tree validates seven reported leaves plus268tracked producer/five selected-test modes/blobs; source hash identity not artifact equivalence',
 'actual_integration_counters':{'passed':131,'failed':0,'skipped':18,'deselected':1166,'seconds':1682.50},'actual_nonintegration_counters':{'passed':1069,'failed':0,'skipped':94,'warnings':14,'seconds':463.97},'six_former_failure_nodes':passes,
 'initial_start_observations':finals,'retained_80_88_samples':0,'reported_startup_duration_seconds':'unavailable; no timing inferred from missing samples','raw_RCC_progress_marks':0,'actual_cleanup_return_predicates':'unavailable; initial ready report is not final cleanup','full_decoded_job_log_private':binding(log),
 'observed_current_vs_historical_bytes':{'current_native_executable':finals[0]['final_initial_start_report']['native_executable'],'historical1151_native_sha256':'45e6de407f12101d04d2d7e4972c563c5dafb48fafa4a2183d1136bc987566f0','current_RCC_config_sha256':'1ad9ed9323e1e9250f60aad72598d1231cd861e93c15d41ad1ea568c3fbb0500','historical_RCC_config_sha256':'e3ad189fdb6b833fca5f3411078f3b7ead993dbfc42f7330dbb8111bd8b1d6b0','not_relabelled':True,'current_RCC_executable_actual_digest':'not observed; no process sample, historical binary digest not carried'},
 'windows_V2_design_disposition':'DEFER_IMPLEMENTATION_AND_ACTUAL_RUN_NOW; retained95f design-onlyGO remains available if a later exact failure needs discrimination; no current Windows failure demonstrated here',
 'limits':['No retained native JUnit fabricated from original log counters.','Initial READY/livewrapper/livereaders is normal active-service observation, not full cleanup or a leak.','No raw Progress/80or88sample/actualcleanup flags; rootcause/internalphase/precise startup duration remain unknown.','One passing current run does not prove cold-cache repeatability or timeout fix and does not repair2999cb/original1151 failures.','Current finalnative digest is observer-measured only, not independent wholearchive/nativeartifact comparison.','Full exact-head merge gates/reviews/otherjobs and private/release acceptance remain root-owned and separate.'],
 'canonical_documentation':{'canonical_file':'docs/skills/repository-operations.md','exact_proposed_delta':binding(proposal),'disposition':'PROPOSED current exact scoped readback; original81b/2994eef histories untouched','evidence':'currentauthenticated identities/four safe originalJSON/268+5+7source leafs/private518f rawlog counters','stale_ambiguity':'historic6 failures are current; missing80/88 proves duration; initialREADY proves cleanup; currentpass repairs oldbranch or establishescause','remaining_uncertainty':'rootcause/nativephase/fullcleanup/complete merge/private/release gates','upstream':'none'},
}
p=OUT/'independent-current-terminal-readback.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(binding(p)))
