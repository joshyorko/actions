import hashlib,importlib.util,json,subprocess,base64,copy
from pathlib import Path
import pytest
PATH=Path('/workspace/actions-cloud/receipts/pr305-runner/canvas-native-public-runner-v5.py')
assert hashlib.sha256(PATH.read_bytes()).hexdigest()=='09cdc6b19f5d3d9cc94fadca23373108868521e0378d33960146b1a8522e88ad'
spec=importlib.util.spec_from_file_location('independent_frozen_v5_launch',PATH);runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
def browser_report(*, launch=None):
    result = {'status': 'passed', 'retry': 0, 'errors': [], 'stderr': []}
    if launch:
        result['stderr'] = [{'text': launch}]
    return {'errors': [], 'stats': {'expected': 1, 'unexpected': 0, 'skipped': 0, 'flaky': 0}, 'suites': [{'title': 'host-harness.spec.ts', 'specs': [{'file': 'host-harness.spec.ts', 'title': 'official bridge renders a real Runtime Action result', 'tests': [{'results': [result]}]}]}]}

def compiled_owned_callback(tmp_path, completed):
    import ast
    from types import SimpleNamespace
    tree = ast.parse(PATH.read_text())
    worker = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'worker'))
    callback = next((n for n in worker.body if isinstance(n, ast.FunctionDef) and n.name == 'owned_command'))
    observed = []

    def owner(command, **kwargs):
        observed.append((command, kwargs))
        return completed
    namespace = dict(runner.__dict__)
    namespace.update(owner=SimpleNamespace(_run_owned_process_tree=owner), attempt=tmp_path, command_receipts=[], capture=lambda: None, verify_helpers=lambda: None)
    exec(compile(ast.Module(body=[callback], type_ignores=[]), str(PATH), 'exec'), namespace)
    return (namespace['owned_command'], observed, namespace['command_receipts'])

def test_postguard_failure_retains_returned_streams(tmp_path):
    import subprocess
    command = [str(runner.NODE), '/synthetic/cli.js', 'test', '--reporter', 'json']
    stdout = json.dumps(browser_report())
    stderr = 'synthetic CLI diagnostic without a browser launch'
    completed = subprocess.CompletedProcess(command, 0, stdout, stderr)
    callback, observed, records = compiled_owned_callback(tmp_path, completed)
    env = {'DEBUG': 'pw:browser', 'CONTROL': 'no product execution'}
    with pytest.raises(AssertionError, match='Actual Playwright launch path not observed') as failure:
        callback(command, cwd=tmp_path, env=env, timeout=180)
    assert type(failure.value) is AssertionError
    assert records[0]['returncode'] == 0 and records[0]['status'] == 'failed'
    assert (tmp_path / 'command-1-stdout.log').read_text() == stdout
    assert (tmp_path / 'command-1-stderr.log').read_text() == stderr
    assert observed == [(command, {'cwd': tmp_path, 'env': env, 'timeout': 180})]

def test_json_captured_test_stderr_is_actual_launch_evidence(tmp_path):
    import subprocess
    command = [str(runner.NODE), '/synthetic/cli.js', 'test', '--reporter', 'json']
    launch = 'pw:browser <launching> ' + str(runner.BROWSER) + ' --synthetic-flags'
    stdout = json.dumps(browser_report(launch=launch))
    completed = subprocess.CompletedProcess(command, 0, stdout, '')
    callback, observed, records = compiled_owned_callback(tmp_path, completed)
    env = {'DEBUG': 'pw:browser', 'CONTROL': 'no product execution'}
    assert callback(command, cwd=tmp_path, env=env, timeout=180) is completed
    assert observed == [(command, {'cwd': tmp_path, 'env': env, 'timeout': 180})]
    assert records[0]['actual_browser_launch_path'] == str(runner.BROWSER)
    assert (tmp_path / 'command-1-stdout.log').read_text() == stdout

@pytest.mark.parametrize('poison', [None, 'outer', 'buffer', 'split', 'wrong_path', 'missing', 'skip', 'count', 'name', 'file', 'retry', 'errors', 'result_error', 'malformed_stderr', 'malformed_buffer', 'malformed_json'])
def test_actual_launch_parser_requires_original_exact_case_and_path(poison):
    import base64
    import copy
    import subprocess
    report = browser_report(launch='pw:browser <launching> ' + str(runner.BROWSER) + ' --flags')
    result = report['suites'][0]['specs'][0]['tests'][0]['results'][0]
    stderr = ''
    if poison == 'outer':
        stderr = result['stderr'][0]['text']
        result['stderr'] = []
    elif poison == 'buffer':
        result['stderr'] = [{'buffer': base64.b64encode(result['stderr'][0]['text'].encode()).decode()}]
    elif poison == 'split':
        text = result['stderr'][0]['text']
        result['stderr'] = [{'text': text[:20]}, {'text': text[20:]}]
    elif poison == 'wrong_path':
        result['stderr'][0]['text'] = 'pw:browser <launching> /wrong/browser --flags'
    elif poison == 'missing':
        result['stderr'] = []
    elif poison == 'skip':
        report['stats']['skipped'] = 1
    elif poison == 'count':
        report['suites'][0]['specs'].append(copy.deepcopy(report['suites'][0]['specs'][0]))
    elif poison == 'name':
        report['suites'][0]['specs'][0]['title'] = 'wrong case'
    elif poison == 'file':
        report['suites'][0]['specs'][0]['file'] = 'other.spec.ts'
    elif poison == 'retry':
        result['retry'] = 1
    elif poison == 'errors':
        report['errors'] = [{'message': 'report failed'}]
    elif poison == 'result_error':
        result['error'] = {'message': 'result failed'}
    elif poison == 'malformed_stderr':
        result['stderr'] = [{'text': 1}]
    elif poison == 'malformed_buffer':
        result['stderr'] = [{'buffer': 'not-base64!'}]
    stdout = 'not JSON' if poison == 'malformed_json' else json.dumps(report)
    completed = subprocess.CompletedProcess([str(runner.NODE), 'owned CLI'], 0, stdout, stderr)
    if poison in (None, 'outer', 'buffer', 'split'):
        assert runner.admit_browser_launch(completed) == ('outer_stderr' if poison == 'outer' else 'named_case_result_stderr')
    else:
        with pytest.raises((AssertionError, ValueError)):
            runner.admit_browser_launch(completed)

def test_postguard_primary_and_completed_bytes_survive_secondary_hash_failure(tmp_path):
    import subprocess
    command = [str(runner.NODE), '/synthetic/cli.js', 'test', '--reporter', 'json']
    stdout = json.dumps(browser_report())
    completed = subprocess.CompletedProcess(command, 0, stdout, 'completed stderr')
    callback, _, _ = compiled_owned_callback(tmp_path, completed)
    primary = AssertionError('synthetic postcondition primary; no product execution')
    checks = []

    def reject(completed):
        raise primary

    def verify():
        checks.append(True)
        if len(checks) == 2:
            raise AssertionError('secondary helper mismatch')
    callback.__globals__['admit_browser_launch'] = reject
    callback.__globals__['verify_helpers'] = verify
    with pytest.raises(AssertionError) as failure:
        callback(command, cwd=tmp_path, env={'CONTROL': 'only'}, timeout=180)
    assert failure.value is primary
    assert any(('secondary helper mismatch' in note for note in primary.__notes__))
    assert (tmp_path / 'command-1-stdout.log').read_text() == stdout
    assert (tmp_path / 'command-1-stderr.log').read_text() == 'completed stderr'

@pytest.mark.parametrize('poison',['boolean_retry','invalid_utf8','mixed_chunk','failed_result','nested_errors','extra_result','nonzero_exit'])
def test_additional_shape_and_result_poison(poison):
 report=browser_report(launch='pw:browser <launching> '+str(runner.BROWSER)+' --flags');result=report['suites'][0]['specs'][0]['tests'][0]['results'][0];returncode=0
 if poison=='boolean_retry':result['retry']=False
 elif poison=='invalid_utf8':result['stderr']=[{'buffer':base64.b64encode(b'\xff').decode()}]
 elif poison=='mixed_chunk':result['stderr'][0]['buffer']='eA=='
 elif poison=='failed_result':result['status']='failed'
 elif poison=='nested_errors':result['errors']=[{'message':'fixed synthetic error'}]
 elif poison=='extra_result':report['suites'][0]['specs'][0]['tests'][0]['results'].append(copy.deepcopy(result))
 else:returncode=1
 with pytest.raises((AssertionError,ValueError)):
  runner.admit_browser_launch(subprocess.CompletedProcess(['synthetic-never-executed'],returncode,json.dumps(report),''))
