"""Actual fixture handoff controls only; standalone Node, no browser launch."""
import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest
sys.path.insert(0, '/workspace/engineering/pr305/action_server/tests')
import action_server_tests.test_browser_origin_acceptance as fixture

def current_reader(path):
    if hasattr(fixture, '_read_browser_harness_pid'):
        return fixture._read_browser_harness_pid(path)
    tree = ast.parse(Path(fixture.__file__).read_text())
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.If) and ast.unparse(n.test) == 'child_pid_file.exists()')
    namespace = {'child_pid_file': path, 'node_pid': None}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.If(test=node.test, body=[node.body[0]], orelse=[])], type_ignores=[])), fixture.__file__, 'exec'), namespace)
    return namespace['node_pid']

@pytest.mark.parametrize('payload', ['', '{"pid":'])
def test_actual_reader_keeps_empty_or_incomplete_handoff_pending(tmp_path, payload):
    path = tmp_path / 'child.pid'
    path.write_text(payload)
    assert current_reader(path) is None

def test_actual_publisher_never_exposes_partial_named_handoff(tmp_path):
    path = tmp_path / 'child.pid'
    body = fixture._BROWSER_SCRIPT.split('if (input.force_hang_after_browser_launch) {', 1)[1].split('await new Promise', 1)[0]
    script = '''import {writeFileSync as realWrite, readFileSync, existsSync, renameSync} from 'node:fs';
const input = {process_pid_file: process.argv[1]};
let partialPublished = false;
function writeFileSync(path, content, options) {
    realWrite(path, '', options);
    if (existsSync(input.process_pid_file) && readFileSync(input.process_pid_file, 'utf8') === '') partialPublished = true;
    realWrite(path, content);
}
''' + body + '''
console.log(JSON.stringify({actual_node_pid: process.pid, partial_published: partialPublished, payload: JSON.parse(readFileSync(input.process_pid_file, 'utf8'))}));'''
    completed = subprocess.run([shutil.which('node'), '--input-type=module', '-e', script, str(path)], capture_output=True, text=True, timeout=5, check=True)
    result = json.loads(completed.stdout)
    assert result['partial_published'] is False
    assert result['payload'] == {'pid': result['actual_node_pid']}
    assert result['actual_node_pid'] > 0
    assert current_reader(path) == result['actual_node_pid']
