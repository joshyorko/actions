import hashlib
import json
import os
import shutil
import pathlib
import secrets
import signal
import socket
import sqlite3
import subprocess
import time
import urllib.request

ROOT = pathlib.Path('/workspace/327-probes/a57-library-protocol')
BASE = pathlib.Path('/workspace/327-artifacts/a57')
CONSUMER = BASE / 'consumer'
SOURCE = pathlib.Path('/workspace/actions')
NODE = '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/node'
SDK_ROOT = SOURCE / 'action_server/frontend/node_modules/@modelcontextprotocol/client'
EXPECTED = {
    'source_commit': 'bde511d2ba6318d0b100547cc6e777e53b9ebc80',
    'source_tree': '58e3beed765765e13724928d26acefb729d8aeab',
    'runtime_version': '1.1.0a57',
    'runtime_wheel_sha256': '07a144f6200ea6bce8d52e14244aef2889e2c15cd52472a758381648fb693efa',
    'canvas_html_bytes': 490733,
    'canvas_html_sha256': '753e9b50759cb628bf5a402575b33e2a411f4c3a775840146f6d507a05183b44',
    'core_version': '1.1.0a8',
    'work_items_version': '0.5.0a2',
    'sdk_version': '2.0.0',
    'node_version': 'v20.19.3',
}
REC = {
    'status': 'PREPARED_NOT_RUN',
    'scope': 'Installed a57 Node SDK modern-auto Canvas create/get/open/resource-read protocol and static renderer identity only',
    'expected_candidate': EXPECTED,
    'runtime_candidate': str(CONSUMER),
    'datadir_policy': 'fresh disposable datadir; no cross-version database copy',
    'operations': ['tools/list', 'canvas_create default UI only', 'canvas_get', 'canvas_open {}', 'canvas_get', 'resources/read ui://action-canvas/v1/canvas.html'],
    'forbidden_operations': ['canvas_apply', 'canvas_release', 'canvas_dispatch', 'capability_invoke', 'queue or run operations', 'compiler or RCC package execution'],
    'source_fixture_reference': '/workspace/327-probes/a53-claimed/terminal-success-failure/evidence/08-canvas_get.json (app identity only; no state copied)',
}


def save():
    (ROOT / 'receipt.json').write_text(json.dumps(REC, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def db_run_attempt_counts():
    path = ROOT / 'datadir/server.db'
    uri = 'file:' + str(path.resolve()) + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as db:
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        selected = [name for name in tables if name.casefold() in {'run', 'attempt', 'run_attempt', 'runattempt', 'task', 'run_task', 'run_task_receipt'}]
        return {name: db.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0] for name in sorted(selected)}


def env_make():
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(('PYTHON', 'ACTIONS_', 'ROBOCORP_', 'RC_')):
            env.pop(key, None)
    env.pop('VIRTUAL_ENV', None)
    env.update(
        OMP_NUM_THREADS='1',
        ACTIONS_HOME=str(ROOT / 'actions-home'),
        ROBOTS_HOME=str(ROOT / 'robots-home'),
        PYTHON_EXE=str(CONSUMER / 'bin/python'),
    )
    env['PATH'] = str(CONSUMER / 'bin') + ':/workspace/actions-cloud/bin:' + env.get('PATH', '')
    return env


def start(port, key, env):
    log = (ROOT / 'runtime.log').open('w')
    args = [str(CONSUMER / 'bin/action-server'), 'start', '--address', '127.0.0.1', '--port', str(port), '--datadir', str(ROOT / 'datadir'), '--actions-sync=false', '--api-key=' + key, '--cors-allow-origin', 'http://localhost:8080']
    proc = subprocess.Popen(args, cwd=ROOT / 'empty', env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError('runtime_exited_' + str(proc.returncode))
        try:
            request = urllib.request.Request(f'http://127.0.0.1:{port}/api/managed-work-items/v1/schema', headers={'Authorization': 'Bearer ' + key})
            with urllib.request.urlopen(request, timeout=1) as response:
                if response.status == 200:
                    return proc, log
        except Exception:
            pass
        time.sleep(0.2)
    raise TimeoutError('runtime_readiness_timeout')


def stop(pair):
    proc, log = pair
    server_log = ROOT / 'datadir/server_log.txt'
    offset = server_log.stat().st_size if server_log.exists() else 0
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
    try:
        code = proc.wait(timeout=25)
    finally:
        log.close()
    lines = server_log.read_bytes()[offset:].decode('utf-8', errors='replace') if server_log.exists() else ''
    graceful = 'Application shutdown complete.' in lines and f'Finished server process [{proc.pid}]' in lines and 'Application shutdown failed.' not in lines
    REC['runtime_shutdown'] = {'exit_code': code, 'graceful_lifespan': graceful}
    if code not in (0, -signal.SIGTERM) or not graceful:
        raise RuntimeError('runtime_graceful_shutdown_failed')


def main():
    if os.environ.get('A57_BUILD_CONFIRMED') != '1':
        raise RuntimeError('parent_build_confirmation_required')
    if not CONSUMER.exists() or not (BASE / 'install-receipt.json').exists() or not (BASE / 'artifact-receipt.json').exists():
        raise RuntimeError('a57_clean_consumer_not_ready')
    if shutil.disk_usage(ROOT).free <= 10 * 1024**3:
        raise RuntimeError('disk_preflight_below_10GiB')
    artifact_receipt = json.loads((BASE / 'artifact-receipt.json').read_text())
    install_receipt = json.loads((BASE / 'install-receipt.json').read_text())
    assert artifact_receipt['source_commit'] == EXPECTED['source_commit'] and artifact_receipt['source_tree'] == EXPECTED['source_tree']
    assert artifact_receipt['status'] == 'PASS_ARTIFACT_ONLY'
    assert install_receipt['status'] == 'PASS_CLEAN_INSTALL' and install_receipt['pip_check'] == 'passed'
    static_receipt = json.loads((BASE / 'canvas-static-receipt.json').read_text())
    assert static_receipt['status'] == 'PASS_READ_ONLY_STATIC_DATA' and static_receipt['runtime_started'] is False
    assert static_receipt['canvas_html_bytes'] == EXPECTED['canvas_html_bytes'] and static_receipt['canvas_html_sha256'] == EXPECTED['canvas_html_sha256']
    assert install_receipt['runtime_version'] == EXPECTED['runtime_version']
    wheel = BASE / artifact_receipt['wheel']
    assert sha(wheel) == artifact_receipt['wheel_sha256'] == install_receipt['runtime_wheel_sha256'] == EXPECTED['runtime_wheel_sha256']
    for name, expected_hash in install_receipt['companion_wheels'].items():
        assert sha(BASE / 'wheels' / name) == expected_hash
    for directory in ('datadir', 'actions-home', 'robots-home', 'empty'):
        path = ROOT / directory
        if path.exists() and any(path.iterdir()):
            raise RuntimeError('task_local_' + directory + '_not_fresh')
        path.mkdir(parents=True, exist_ok=True)
    identity_text = "import importlib.metadata as m, actions.server, actions.server._static_contents as s, hashlib, json; b=s.FILE_CONTENTS['canvas.html']; print(json.dumps({'runtime':m.version('actions-runtime'),'core':m.version('actions-core'),'work_items':m.version('actions-work-items'),'server':actions.server.__file__,'renderer_sha256':hashlib.sha256(b).hexdigest(),'renderer_bytes':len(b),'renderer_has_library_heading':b'Action Canvas library' in b}))"
    identity = json.loads(subprocess.check_output([str(CONSUMER / 'bin/python'), '-c', identity_text], text=True))
    assert identity['runtime'] == EXPECTED['runtime_version'] and identity['core'] == EXPECTED['core_version'] and identity['work_items'] == EXPECTED['work_items_version']
    assert pathlib.Path(identity['server']).resolve().is_relative_to(CONSUMER.resolve())
    assert identity['renderer_has_library_heading'] is True
    assert identity['renderer_bytes'] == EXPECTED['canvas_html_bytes'] and identity['renderer_sha256'] == EXPECTED['canvas_html_sha256']
    assert subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip() == EXPECTED['source_commit']
    assert subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD^{tree}'], text=True).strip() == EXPECTED['source_tree']
    node_version = subprocess.check_output([NODE, '-p', 'process.version'], text=True).strip()
    assert node_version == EXPECTED['node_version']
    sdk_metadata = json.loads((SDK_ROOT / 'package.json').read_text())
    assert sdk_metadata['name'] == '@modelcontextprotocol/client' and sdk_metadata['version'] == EXPECTED['sdk_version']
    REC.update(
        artifact_receipt_status=artifact_receipt['status'],
        install_receipt_status=install_receipt['status'],
        runtime_wheel_sha256=artifact_receipt['wheel_sha256'],
        companion_wheel_sha256=install_receipt['companion_wheels'],
        installed_identity=identity,
        node_version=node_version,
        node_undici_version=subprocess.check_output([NODE, '-p', 'process.versions.undici'], text=True).strip(),
        sdk_entry_sha256=sha(SDK_ROOT / 'dist/index.mjs'),
        sdk_types_sha256=sha(SDK_ROOT / 'dist/index.d.mts'),
        node_script_sha256=sha(ROOT / 'node_canvas_protocol.mjs'),
        renderer_sha256=identity['renderer_sha256'],
        renderer_bytes=identity['renderer_bytes'],
        free_disk_bytes=__import__('shutil').disk_usage(ROOT).free,
    )
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    key = secrets.token_urlsafe(32)
    env = env_make()
    pair = None
    save()
    try:
        pair = start(port, key, env)
        REC['runtime_ready'] = True
        before = db_run_attempt_counts()
        REC['run_attempt_counts_before'] = before
        assert {'run', 'run_attempt'} <= set(before), 'run_attempt_tables_missing'
        child_env = dict(env)
        child_env.update(
            NODE_SDK_ROOT=str(SDK_ROOT),
            RUNTIME_ENDPOINT=f'http://127.0.0.1:{port}/mcp',
            RUNTIME_BEARER=key,
            PROBE_ROOT=str(ROOT),
            EXPECTED_HTML_SHA256=identity['renderer_sha256'],
        )
        output = ROOT / 'node-probe.jsonl'
        with output.open('w') as stream:
            child = subprocess.Popen([NODE, str(ROOT / 'node_canvas_protocol.mjs')], cwd=ROOT / 'empty', env=child_env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            code = child.wait(timeout=90)
        REC['node_exit_code'] = code
        if code != 0:
            raise RuntimeError('node_probe_exit_' + str(code))
        rows = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
        assert any(row.get('event') == 'natural_before_exit' and row.get('code') == 0 for row in rows)
        assert any(row.get('event') == 'client_close_complete' for row in rows)
        assert any(row.get('event') == 'transport_close_complete' for row in rows)
        assert any(row.get('event') == 'phase_complete' for row in rows)
        REC['node_events'] = [{'event': row['event'], 'stage': row.get('stage')} for row in rows]
        after = db_run_attempt_counts()
        REC['run_attempt_counts_after'] = after
        assert before == after, 'run_or_task_rows_changed'
        REC['run_attempt_counts_unchanged'] = True
        REC['result'] = json.loads((ROOT / 'result.json').read_text())
        REC['status'] = 'PASS_PROTOCOL_AND_STATIC_RESOURCE'
    except BaseException as exc:
        REC.update(status='FAILED', failure_type=type(exc).__name__, failure=str(exc) if isinstance(exc, (RuntimeError, TimeoutError)) else 'preflight_or_assertion_failed')
        raise
    finally:
        if pair is not None:
            stop(pair)
        if key:
            for path in ROOT.glob('*.log'):
                path.write_text(path.read_text(errors='replace').replace(key, '[REDACTED_LOCAL_TEST_KEY]'))
        save()


if __name__ == '__main__':
    main()
