from pathlib import Path
import hashlib
import json
import re
import subprocess
import zipfile

ROOT = Path('/workspace/engineering/pr311-original-windows-diagnostics-owned')
OUT = Path('/workspace/engineering/pr311-original-windows-independent-review')
REPO = '/workspace/engineering/pr311'
HEAD = '1151a0c8dfdfc1cba9afcb430e4fee71d9a4b4f9'
ZIP = Path('/workspace/attachments/b854d2e5-b5fc-4b18-ab27-9b7f64879752/pr311-original-1151-windows-startup-diagnostics.zip')

def binding(p):
    b = p.read_bytes()
    return {'path': str(p), 'size': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def keys(obj, allowed):
    assert isinstance(obj, dict)
    assert set(obj) <= set(allowed), (set(obj) - set(allowed))

def file_id(d):
    keys(d, ['size', 'sha256'])
    assert type(d['size']) is int and d['size'] >= 0
    assert re.fullmatch('[0-9a-f]{64}', d['sha256'])

COMMAND = ['operation', 'bundled', 'config_argument_present', 'controller', 'json', 'no_pyc_management', 'no_retry_build', 'package_argument_present', 'robocorp', 'space', 'unrecognized_arguments']
rows = []
source_bindings = []
sample_findings = []
for prefix, label in [('7d0f2e912f58600f', 'failed_watched_reload'), ('34ec97696df8d90c', 'catalog_resource_collision')]:
    reports = []
    for n in range(1, 5):
        p = ROOT / 'reports' / f'{prefix}-{n}.json'
        rows.append(binding(p))
        reports.append(json.loads(p.read_text()))
    identity, first, second, final = reports
    keys(identity, ['identity'])
    d = identity['identity']
    keys(d, ['GITHUB_RUN_ATTEMPT', 'GITHUB_RUN_ID', 'GITHUB_SHA', 'failure_cleanup_seconds', 'native_executable', 'nodeid', 'rcc_config', 'readiness_seconds', 'sample_seconds', 'schema', 'source_files'])
    assert (d['GITHUB_RUN_ID'], d['GITHUB_RUN_ATTEMPT'], d['GITHUB_SHA']) == ('38107807246', '1', 'c4794ac6d8312866a2dac92b52185fca912046bb')
    assert (d['schema'], d['readiness_seconds'], d['failure_cleanup_seconds'], d['sample_seconds']) == (1, 90, 20, [80, 88])
    assert d['native_executable'] == {'status': 'measured_after_start_returns'}
    file_id(d['rcc_config'])
    assert len(d['source_files']) == 7
    for path, measured in d['source_files'].items():
        assert path.startswith(('src/actions/server/', 'tests/action_server_tests/'))
        file_id(measured)
        source = subprocess.check_output(['git', '-C', REPO, 'show', HEAD + ':action_server/' + path])
        windows = source.replace(b'\n', b'\r\n')
        assert measured == {'size': len(windows), 'sha256': hashlib.sha256(windows).hexdigest()}
        source_bindings.append({'case': label, 'path': path, 'git_lf_sha256': hashlib.sha256(source).hexdigest(), 'windows_crlf': measured})
    for report in [first, second]:
        keys(report, ['elapsed_seconds', 'snapshot'])
        s = report['snapshot']
        keys(s, ['captured_stderr', 'captured_stdout_characters', 'descendant_limit_reached', 'host_readers', 'pipes_closed', 'processes', 'rcc_internal_readers', 'wrapper_pid', 'wrapper_returncode'])
        assert s['wrapper_returncode'] is None
        assert s['captured_stdout_characters'] == 0
        assert s['descendant_limit_reached'] is False
        assert s['rcc_internal_readers'] == 'unavailable_from_host'
        keys(s['captured_stderr'], ['characters', 'last_rcc_command'])
        keys(s['captured_stderr']['last_rcc_command'], COMMAND)
        assert s['captured_stderr']['last_rcc_command']['operation'] == 'holotree variables'
        assert s['captured_stderr']['last_rcc_command']['unrecognized_arguments'] == 0
        assert s['pipes_closed'] == {'stderr': False, 'stdout': False}
        assert len(s['host_readers']) == 2
        for reader in s['host_readers']:
            keys(reader, ['ident', 'alive'])
            assert reader['alive'] is True
        assert len(s['processes']) == 3
        for i, process in enumerate(s['processes']):
            keys(process, ['command', 'cpu_seconds', 'created', 'handles', 'io_bytes', 'parent_pid', 'pid', 'status', 'effective_home_matches_launch', 'env_info_cache_exists', 'rcc_executable', 'staged_package'])
            keys(process['command'], COMMAND)
            keys(process['io_bytes'], ['read', 'write'])
            assert process['status'] == 'running'
            if i:
                assert process['parent_pid'] == s['processes'][i-1]['pid']
            if i == 2:
                assert process['command']['operation'] == 'holotree variables'
                assert process['command']['unrecognized_arguments'] == 0
                assert process['effective_home_matches_launch'] is True
                assert process['env_info_cache_exists'] is False
                file_id(process['rcc_executable'])
                file_id(process['staged_package'])
            else:
                assert process['command'] == {'operation': 'unavailable'}
    keys(final, ['after_start_returned', 'exception', 'native_executable', 'outcome', 'sampler_alive', 'sampler_cancelled'])
    assert final['after_start_returned'] == {'host_readers_alive': [False, False], 'observation': 'host_only', 'returncode': 15}
    assert (final['exception'], final['outcome'], final['sampler_alive'], final['sampler_cancelled']) == ('TimeoutError', 'failed', False, True)
    file_id(final['native_executable'])
    a, b = first['snapshot'], second['snapshot']
    assert a['captured_stderr'] == b['captured_stderr']
    deltas = []
    for i, (p, q) in enumerate(zip(a['processes'], b['processes'])):
        for field in ['pid', 'parent_pid', 'created']:
            assert p[field] == q[field]
        deltas.append({'position': i, 'command_operation': p['command']['operation'], 'cpu_seconds_delta': q['cpu_seconds']-p['cpu_seconds'], 'read_bytes_delta': q['io_bytes']['read']-p['io_bytes']['read'], 'write_bytes_delta': q['io_bytes']['write']-p['io_bytes']['write'], 'handles_delta': q['handles']-p['handles']})
    assert deltas[2]['cpu_seconds_delta'] > 0 and deltas[2]['read_bytes_delta'] > 0 and deltas[2]['write_bytes_delta'] > 0
    sample_findings.append({'case': label, 'nodeid': d['nodeid'], 'sample_elapsed_seconds': [first['elapsed_seconds'], second['elapsed_seconds']], 'interval_seconds': second['elapsed_seconds']-first['elapsed_seconds'], 'process_count': 3, 'measured_process_name_counts': 'unavailable: names are not emitted', 'identity_and_parent_links_stable': True, 'deltas': deltas, 'final_observation': final, 'cache_exists_at_both_samples': False})

assert binding(ZIP)['sha256'] == '0115d2e19118f7946734f14952338d97e7982b43d5d79835c75e1179b41e793d'
with zipfile.ZipFile(ZIP) as z:
    assert len(z.infolist()) == 8
    for member in z.infolist():
        assert member.filename == Path(member.filename).name and member.filename.endswith('.json')
        assert z.read(member) == (ROOT/'reports'/member.filename).read_bytes()
log = ROOT / 'job114376917743-original-decoded.log'
assert binding(log)['sha256'] == '8e1e283aec983b2784ef5062685ae3c4877a9c362cca88b883c4add6ebfd3d10'
text = log.read_text()
assert '6 failed, 125 passed, 18 skipped, 1130 deselected' in text
assert sum('E ' in line and 'Action Server startup cleanup did not fully complete within its 20-second deadline.' in line for line in text.splitlines()) == 5
failures = []
for line in text.splitlines():
    if 'FAILED action_server_tests' in line:
        node = line.split('FAILED ', 1)[1].split(' - ', 1)[0]
        assert line.endswith(' - TimeoutError')
        failures.append({'node': node, 'primary_phase': 'first native start; ready-port wait reaches existing 90-second deadline', 'semantic_reload_or_drain_assertions_reached': False})
assert len(failures) == 6
trace_boundaries = [(4217, 4630), (4640, 5015), (5020, 5400), (5410, 5785), (5809, 6140), (6163, 6550)]
lines = text.splitlines()
for case, (a, b) in zip(failures, trace_boundaries):
    segment = '\n'.join(lines[a:b])
    assert 'if time.monotonic() - initial_time >= timeout:' in segment
    assert '>                               raise TimeoutError()' in segment
    assert '..\\src\\actions\\server\\_selftest.py:202: TimeoutError' in segment
    case['raw_log_lines_1_based'] = [a+1, b]
    case['startup_cleanup_incomplete_note'] = 'startup cleanup did not fully complete' in segment
control = json.loads((ROOT/'authenticated-control.json').read_text())
assert control['tree'] == '1b742a1bac55d9dee96a1f70bbf2ad0735edf356'
assert control['parents'] == ['ba85aac7324ea4463bfba8c5f8586e27706dc2fe', HEAD]
receipt = {
 'verdict': 'GO_ACCEPT_ORIGINAL_BOUNDED_DIAGNOSTIC_EVIDENCE_ONLY; HOLD_TIMEOUT_FIX_CLEANUP_COMPLETENESS_AND_MERGE',
 'scope': 'read-only independent original 1151 hosted Windows observation; no rerun, cancel, source mutation or publication',
 'control': control, 'original_head': HEAD,
 'authenticated_github': [binding(ROOT/p) for p in ['authenticated-run.json','authenticated-job.json','authenticated-control.json','authenticated-artifact.json']],
 'original_zip': binding(ZIP), 'original_decoded_job_log': binding(log), 'original_raw_json': rows,
 'artifact_bytes_match_safe_extraction': True, 'allowlisted_all_actual_fields': True,
 'source_bindings_windows_checkout_crlf': source_bindings,
 'actual_integration_counters': {'failed':6,'passed':125,'skipped':18,'deselected':1130},
 'prior_issue_two_failures_is_historical_not_current_run_census': True,
 'failure_primary_phases': failures, 'instrumented_case_count': 2, 'sample_findings': sample_findings,
 'rcc_progress': {'uppercase_Progress_occurrences':0,'lowercase_progress_occurrences':2,'lowercase_occurrence_scope':['checkout show-progress option','git checkout command'], 'raw_rcc_progress_marks_and_intervals':'not available in original decoded log or eight raw diagnostic reports', 'reported_total_rcc_duration':'not available; do not reconstruct from observer elapsed time or treat a previous-mark interval as total'},
 'supported': ['All six fail on first native ready-port wait, before test semantic transitions.', 'The two instrumented starts retain stable owned three-process identity/parent chains through both snapshots.', 'The holotree variables RCC process accrues CPU and disk read/write between 80 and 88 seconds; wrapper and direct child CPU/IO remain unchanged.', 'No observed process forest truncation, unknown RCC argument, home mismatch or measured RCC binary disagreement between the two cases.', 'Final host-only observations record wrapper returncode 15 and stopped two host readers and sampler; sampler cancellation is a request event distinct from sampler_alive.'],
 'contradicted_narrow_hypotheses': ['RCC was completely CPU/IO idle throughout the measured 80-to-88-second intervals.', 'The primary failure was a failed-reload/catalog rollback/resource-history/drain semantic assertion.', 'An observer timeout replaced the original readiness deadline or primary TimeoutError.'],
 'remaining_uncertainty': ['Active CPU/IO does not exclude partial blocking, network waits, subprocess pauses, antivirus work or other unobserved mechanisms.', 'Process names, RCC internal readers, raw progress marks, descendant state after cleanup, and actual ProcessTreeCleanupResult fields are absent.', 'Five primary timeout traces retain an explicit incomplete cleanup note; final host-only rc15/readers/sampler fields cannot erase it or prove all descendants reaped.', 'Absent env-info cache at two moments is an observation, not a demonstrated cache defect.', 'The sixth uninstrumented drain-start failure has no cleanup note, which alone cannot prove complete cleanup.', 'Native executable final hash is measured by the observer but not independently matched to a separately downloaded whole hosted native artifact.', 'Broader six-case initial managed-environment startup failures do not establish a #299-specific regression or the cause of cold Windows RCC work.'],
 'canonical_documentation': {'proposal':'canonical-original-windows-diagnostic-proposal.md','disposition':'proposed to root for next ordinary durable evidence integration; no repository mutation', 'stale_ambiguity':'Earlier two-timeout census applies to earlier run; current original1151 run has six failed initial starts but only two instrumented observations.', 'evidence':'original ZIP, all eight JSON hashes, authenticated run/job/control/artifact and full decoded-log hash above', 'upstream':'none; no root-cause or upstream defect established'},
 'private_metadata_and_release_gates':'unchanged HOLD; no whole-runtime release qualification',
}
proposal = '''The original PR #311 Windows run 38107807246 at source 1151a0c8 failed six integration cases (125 passed, 18 skipped); all six failed in their first native start while waiting for the ready port at the retained 90-second deadline. This current six-case census supersedes the earlier two-timeout census for this run only. The observer remains limited to the failed-watched-reload and resource-collision nodes.

In those two nodes, the 80/88-second snapshots retain a stable wrapper → direct child → RCC ownership chain and a three-process forest. RCC is still executing `holotree variables`: it accrues 3.9375/4.859375 CPU seconds, 63,794,795/61,391,993 read bytes, and 162,976,242/156,130,489 write bytes across the respective intervals. Wrapper/direct-child CPU and IO counters stay unchanged. Process names and RCC-internal reader state are not measured. Absent environment-info cache at these moments does not identify a cache defect. These observations reject complete RCC CPU/IO inactivity during the sampled intervals and a primary reload/drain semantic failure; they do not identify the underlying Windows startup cause or a #299-specific regression.

The original decoded log and reports contain no raw RCC progress marks, so they cannot supply final progress intervals or a total RCC duration. Observer elapsed times are separate measurements. If later immutable raw progress output becomes available, preserve each mark's previous-mark interval semantics instead of relabeling the last interval as total elapsed time.

The final observer reports wrapper returncode 15, both host reader threads stopped, and sampler_alive false after cancellation was requested. Those host-only fields do not report the process-tree cleanup result or prove all descendants reaped. Five raw traces explicitly preserve the original startup TimeoutError with the additional note that the existing 20-second cleanup did not fully complete. The uninstrumented drain failure's absent note alone cannot prove full cleanup either. Retain the 90-second readiness and 20-second cleanup gates; no timeout fix, native acceptance or merge is established by this evidence. No prewarm, retry, replacement configuration or infrastructure action was performed.

Evidence: original artifact 11690888016 ZIP SHA256 0115d2e19118f7946734f14952338d97e7982b43d5d79835c75e1179b41e793d; original job 114376917743 decoded log SHA256 8e1e283aec983b2784ef5062685ae3c4877a9c362cca88b883c4add6ebfd3d10; eight original JSON/source/control bindings in the independent receipt. Proposed next ordinary guidance/evidence update; no repository mutation. Remaining uncertainty is the cause and unobserved cleanup/progress state. Upstream disposition: none.
'''
p=OUT/'canonical-original-windows-diagnostic-proposal.md'
p.write_text(proposal)
receipt['canonical_documentation']['proposal_binding']=binding(p)
p=OUT/'original-hosted-diagnostic-review.json'
p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(binding(p)))
