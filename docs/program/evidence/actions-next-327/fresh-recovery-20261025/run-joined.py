"""Bounded source qualification using an owned loopback PostgreSQL fixture."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT = Path('/workspace/actions')
OUT = Path('/workspace/actions-327-recovery-evidence')
IMAGE = 'postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81'
MODULES = [
    'test_logical_domain', 'test_logical_runner_join', 'test_task_service',
    'test_generic_work_item_execution', 'test_generic_execution_port',
    'test_foundry_authoring', 'test_foundry_authoring_model_contract',
    'test_foundry_sql_authoring',
]


def capture(args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def main():
    if shutil.disk_usage(ROOT).free < 5 * 1024**3:
        raise SystemExit('Need 5 GiB before joined qualification')
    env = dict(os.environ, POSTGRES_PASSWORD=secrets.token_hex(24))
    name = 'actions327-recovery-' + secrets.token_hex(5)
    container = capture(['docker', 'run', '--rm', '-d', '--name', name,
        '--label', 'actions.owner=fresh-recovery-327', '--memory', '768m',
        '--tmpfs', '/var/lib/postgresql/data:rw,size=512m',
        '-p', '127.0.0.1::5432', '-e', 'POSTGRES_PASSWORD', IMAGE], env=env)
    summary = {'source': capture(['git', 'rev-parse', 'HEAD'], cwd=ROOT),
               'tree': capture(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT),
               'container': container, 'image': IMAGE, 'batches': []}
    try:
        port = capture(['docker', 'port', container, '5432/tcp']).rsplit(':', 1)[1]
        for _ in range(100):
            ready = subprocess.run(['docker', 'exec', container, 'pg_isready', '-U', 'postgres'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if ready.returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError('Owned PostgreSQL not ready')
        env['ACTIONS_INVOICE_TEST_POSTGRES'] = 'postgresql://postgres:' + env['POSTGRES_PASSWORD'] + '@127.0.0.1:' + port + '/postgres'
        env['ACTIONS_REQUIRE_INVOICE_PROVIDERS'] = '1'
        for module in MODULES:
            target = OUT / module
            target.mkdir(exist_ok=False)
            env['ACTIONS_SELECTED_INVENTORY'] = str(target / 'selected.json')
            args = ['rcc', 'task', 'script', '-r', 'developer/toolkit.yaml', '--', 'python',
                    '/workspace/actions-cloud/package-command.py', 'action_server', 'run', 'python',
                    str(OUT / 'selected-pytest.py'), 'tests/action_server_tests/' + module + '.py',
                    '-k', 'not real_generic_rcc and not optin_actual_rcc_model_wrapper',
                    '-p', 'no:robocorp_log_pytest', '-q', '--tb=short',
                    '--junitxml=' + str(target / 'tests.xml'), '--basetemp=' + str(target / 'fixtures')]
            log = target / 'run.log'
            started = time.monotonic()
            minimum = shutil.disk_usage(ROOT).free
            reason = None
            with log.open('w') as output:
                process = subprocess.Popen(args, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                while process.poll() is None:
                    minimum = min(minimum, shutil.disk_usage(ROOT).free)
                    if minimum < 2 * 1024**3 or log.stat().st_size > 20 * 1024**2 or time.monotonic() - started > 1200:
                        import signal
                        reason = 'resource/time bound reached'
                        os.killpg(process.pid, signal.SIGTERM)
                        break
                    time.sleep(1)
                code = process.wait(timeout=30)
            receipt = {'module': module, 'command': args, 'exit_code': code,
                       'minimum_free_bytes': minimum, 'stop_reason': reason,
                       'source_sha256': hashlib.sha256((ROOT / 'action_server/tests/action_server_tests' / (module + '.py')).read_bytes()).hexdigest()}
            if (target / 'tests.xml').exists():
                cases = ET.parse(target / 'tests.xml').findall('.//testcase')
                receipt['counts'] = {'tests': len(cases), **{kind: sum(case.find(kind) is not None for case in cases) for kind in ['failure', 'error', 'skipped']}}
            (target / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
            summary['batches'].append(receipt)
            (OUT / 'joined-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
            print(module, code, receipt.get('counts'), flush=True)
            if code:
                break
    finally:
        summary['cleanup_exit'] = subprocess.run(['docker', 'stop', '--time', '15', container], stdout=subprocess.DEVNULL).returncode
        (OUT / 'joined-summary.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
