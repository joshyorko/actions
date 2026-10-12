"""Exercise the prepared source server, REST action, and stateless MCP endpoint."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.error
import urllib.request

import toolkit

state = Path('/workspace/actions-cloud')
root = toolkit.REPOSITORY_ROOT
url = 'http://127.0.0.1:18080'


def request(path, payload=None, method=None):
    headers = {'Accept': 'application/json',
               'Authorization': 'Bearer cloud-onboarding-local-check'}
    data = None
    if method:
        headers['Mcp-Method'] = method
        headers['MCP-Protocol-Version'] = '2026-07-28'
        payload['params']['_meta'] = {
            'io.modelcontextprotocol/protocolVersion': '2026-07-28',
            'io.modelcontextprotocol/clientCapabilities': {},
        }
        if method == 'tools/call':
            headers['Mcp-Name'] = payload['params']['name']
    if payload is not None:
        data = json.dumps(payload).encode()
        headers['Content-Type'] = 'application/json'
    with urllib.request.urlopen(urllib.request.Request(url + path, data=data, headers=headers), timeout=45) as response:
        body = response.read().decode()
    if body.startswith('event:') or body.startswith('data:'):
        body = next(line[6:] for line in body.splitlines() if line.startswith('data: '))
    return json.loads(body)


command = [str(root / 'action_server/.venv/bin/action-server'), 'start',
           '--dir', str(state / 'smoke-package'), '--address', '127.0.0.1',
           '--port', '18080', '--datadir', str(state / 'smoke-datadir'),
           '--min-processes', '1', '--max-processes', '2',
           '--api-key', 'cloud-onboarding-local-check', '--verbose']
with (state / 'logs/source-server.log').open('w') as log:
    process = subprocess.Popen(command, cwd=root / 'action_server',
                               env=toolkit.package_environment(root / 'action_server'),
                               stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        deadline = time.monotonic() + 180
        while True:
            if process.poll() is not None:
                raise RuntimeError(f'Server exited with {process.returncode}; see source-server.log')
            try:
                schema = request('/openapi.json')
                break
            except (OSError, urllib.error.URLError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
        path = next(path for path in schema['paths'] if path.endswith('/greet/run'))
        result = request(path, {'name': 'cloud'})
        assert result == 'Hello, cloud!', result
        catalog = request('/mcp', {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {}}, 'tools/list')
        tool = next(tool for tool in catalog['result']['tools'] if tool['name'].endswith('greet'))
        called = request('/mcp', {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                                 'params': {'name': tool['name'], 'arguments': {'name': 'cloud'}}}, 'tools/call')
        assert 'error' not in called and not called['result'].get('isError'), called
        assert 'Hello, cloud!' in json.dumps(called), called
        evidence = {'rest_path': path, 'rest_result': result, 'mcp_catalog': catalog, 'mcp_call': called}
        (state / 'logs/source-server-results.json').write_text(json.dumps(evidence, indent=2) + '\n')
        print('PASS: source Action Server startup, REST action, MCP tools/list, and MCP tools/call', flush=True)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
