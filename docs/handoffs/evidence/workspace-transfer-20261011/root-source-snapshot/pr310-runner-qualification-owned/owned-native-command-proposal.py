"""Proposed command wrapper; actual execution requires root review and explicit flag."""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path('/workspace/engineering/pr310')
OWNED = Path('/workspace/engineering/pr310-runner-qualification-owned')
CONTROL = 'f506a04e240feba048bf10e32bccebf591674f9e'
TREE = '782ff78fa4bfc751b6d02004f665da84fc79c81b'
BUILD = '92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
BROWSER = Path('/workspace/actions-cloud/cache/playwright/chromium-1234/chrome-linux64/chrome')
NODE = '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/node'
TEST = 'test_packaged_work_items_ui_create_keyboard_narrow_and_storage_recovery'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def module(path, name):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', required=True, choices=['frozen', 'go-wrapper'])
    parser.add_argument('--execute-reviewed-proposal', action='store_true', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    assert platform.system() == 'Linux' and platform.machine() == 'x86_64'
    git = lambda *a: subprocess.check_output(['git', *a], cwd=ROOT, text=True).strip()
    assert git('rev-parse', 'HEAD') == CONTROL and git('rev-parse', 'HEAD^{tree}') == TREE
    assert not git('status', '--porcelain')
    parity = json.loads((OWNED / 'current-source-parity.json').read_text())
    assert set(git('diff', '--name-only', BUILD, CONTROL).splitlines()) == set(parity['only_differing_paths'])
    for path, identity in parity['selected_test_and_fixture_identities'].items():
        assert digest(ROOT / path) == identity['sha256']
    assert digest(BROWSER) == '0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71'
    assert digest('/workspace/actions-cloud/bin/rcc') == '7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
    assert shutil.disk_usage(OWNED).free >= 2 * 1024**3
    lock = json.loads((ROOT / 'action_server/frontend/package-lock.json').read_text())
    installed = json.loads((ROOT / 'action_server/frontend/node_modules/.package-lock.json').read_text())
    for key in ['node_modules/@playwright/test', 'node_modules/playwright', 'node_modules/playwright-core']:
        assert installed['packages'][key]['version'] == lock['packages'][key]['version'] == '1.62.1'
        assert installed['packages'][key]['integrity'] == lock['packages'][key]['integrity']
    manifest = OWNED / 'output/native-artifact-manifest.json'
    assert digest(manifest) == '70405e6e831066a37631c7a63045010fcbc8b3c928a6a22ff5130467c3ad9d44'
    artifact = json.loads(manifest.read_text())
    measured = module(ROOT / 'action_server/scripts/write_native_artifact_manifest.py', 'unchanged_manifest_reader')
    frozen_root = OWNED / 'dist/action-server'
    assert measured.packaged_tree_inventory(frozen_root) == json.loads((OWNED / 'output/native-artifact-tree-inventory.json').read_text())
    assert measured.packaged_tree_sha256(frozen_root) == artifact['artifacts']['frozen']['frozen_package_tree_sha256']
    assert measured.packaged_files_sha256(frozen_root) == artifact['artifacts']['frozen']['embedded_files_sha256']
    assert digest(ROOT / 'action_server/go-wrapper/assets/assets.zip') == artifact['artifacts']['frozen']['assets_zip_sha256']
    assert measured.source_files_sha256(ROOT / 'action_server', tuple(artifact['artifacts']['frozen']['wrapper_source_files'])) == artifact['artifacts']['frozen']['wrapper_source_sha256']
    for kind, path in [('frozen', OWNED / 'dist/action-server/action-server'), ('go-wrapper', OWNED / 'dist/final/action-server')]:
        assert digest(path) == artifact['artifacts'][kind]['sha256']
    result_root = OWNED / ('actual-' + args.kind)
    result_root.mkdir(exist_ok=False)
    executable = OWNED / ('dist/action-server/action-server' if args.kind == 'frozen' else 'dist/final/action-server')
    receipt_path = result_root / 'native-ui-receipt.json'
    short_tmp = None
    env = dict(os.environ)
    env.update({'DAKOTA_WORKITEMS_UI_EXECUTABLE': str(executable), 'DAKOTA_WORKITEMS_UI_SOURCE_SHA': BUILD, 'DAKOTA_WORKITEMS_UI_RUNTIME_KIND': args.kind, 'DAKOTA_WORKITEMS_UI_BUILD_MANIFEST': str(manifest), 'DAKOTA_WORKITEMS_UI_RECEIPT': str(receipt_path), 'DAKOTA_WORKITEMS_UI_NODE': NODE, 'PLAYWRIGHT_BROWSERS_PATH': '/workspace/actions-cloud/cache/playwright', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_ADDOPTS': '', 'PYTEST_XDIST_AUTO_NUM_WORKERS': '1'})
    env.pop('ACTIONS_REAL_RCC_ARTIFACT_TEST', None)
    env.pop('ACTIONS_RUNTIME_RCC_PROVIDER', None)
    command = [str(ROOT / 'action_server/.venv/bin/python'), '-m', 'pytest', '-n', '0', '-q', '--tb=short', '-rA', '-m', 'integration_test and native_artifact_test', str(ROOT / 'action_server/tests/action_server_tests/test_dakota_workitems_native_ui_acceptance.py') + '::' + TEST, '--basetemp=' + str(result_root / 'pytest-owned'), '--junitxml=' + str(result_root / 'junit.xml')]
    helper = module(ROOT / 'action_server/scripts/verify_dakota_rcc_acceptance.py', 'existing_owned_process')
    started = time.monotonic()
    envelope = {'harness_sha': CONTROL, 'harness_tree': TREE, 'artifact_source_sha': BUILD, 'artifact_build_tree': '80e5c77513f6abf5d07005ee3aee47d49efd927f', 'artifact_workflow_run': '38098225250', 'runtime_kind': args.kind, 'command': command, 'command_timeout_seconds': 600, 'cleanup_grace_seconds': 10, 'supervisor_parent_timeout_seconds': 645, 'browser_sha256': digest(BROWSER), 'binary_sha256': digest(executable), 'browser_temp_root': None, 'status': 'FAIL_OR_INCOMPLETE'}
    try:
        short_tmp = Path(tempfile.mkdtemp(prefix='wiui-', dir='/tmp'))
        assert len(str(short_tmp)) <= 24 and (short_tmp.stat().st_mode & 0o777) == 0o700
        env.update({'TMPDIR': str(short_tmp), 'TMP': str(short_tmp), 'TEMP': str(short_tmp)})
        envelope['browser_temp_root'] = str(short_tmp)
        result = helper.run_owned_process(command, timeout_seconds=600, cleanup_grace_seconds=10, env=env, cwd=ROOT / 'action_server')
        (result_root / 'test-stdout.log').write_text(result.stdout)
        (result_root / 'test-stderr.log').write_text(result.stderr)
        envelope.update(returncode=result.returncode, cleanup_disposition=result.cleanup_disposition, reaped_descendants=result.reaped_descendants)
        assert result.returncode == 0
        cases = ET.parse(result_root / 'junit.xml').getroot().findall('.//testcase')
        assert len(cases) == 1 and cases[0].get('name') == TEST
        assert not any(cases[0].find(tag) is not None for tag in ['skipped', 'error', 'failure'])
        receipt = json.loads(receipt_path.read_text())
        assert receipt['status'] == 'PASS_BOUNDED' and receipt['source_sha'] == BUILD and receipt['runtime_kind'] == args.kind
        assert receipt['executable_sha256'] == digest(executable)
        assert [s['stage'] for s in receipt['browser_stages']] == ['normal', 'authorization-denied', 'storage-error']
        assert all(s['status'] == 'PASS' and s['script_exit_code'] == 0 for s in receipt['browser_stages'])
        assert 'authorization_denial_ui' not in receipt['states_not_run'] and not receipt['states_failed']
        c = receipt['cleanup_observation']
        assert c['wrapper_reaped'] and c['descendant_snapshot_complete'] and c['live_descendant_count'] == c['control_error_count'] == 0
        assert receipt['post_runtime_tree_validation']['valid'] and receipt['post_runtime_tree_validation']['immutable_build_tree_unchanged']
        envelope.update(status='PASS_BOUNDED', receipt_sha256=digest(receipt_path), observed_zombie_descendant_count=c['zombie_descendant_count'])
    except BaseException as error:
        envelope['failure_type'] = type(error).__name__
        for attribute, name in [('output', 'failure-stdout.log'), ('stderr', 'failure-stderr.log'), ('command_stdout', 'control-failure-stdout.log'), ('command_stderr', 'control-failure-stderr.log')]:
            value = getattr(error, attribute, None)
            if value is not None:
                (result_root / name).write_text(value.decode(errors='replace') if isinstance(value, bytes) else str(value))
        raise
    finally:
        try:
            if short_tmp is not None:
                shutil.rmtree(short_tmp)
            envelope['browser_temp_cleanup'] = 'REMOVED_AFTER_SUPERVISOR_COMPLETED'
        except BaseException as cleanup_error:
            envelope['browser_temp_cleanup'] = 'FAIL'
            envelope['browser_temp_cleanup_failure_type'] = type(cleanup_error).__name__
            envelope['status'] = 'FAIL_OR_INCOMPLETE'
        envelope['elapsed_seconds'] = time.monotonic() - started
        envelope['files'] = {p.name: digest(p) for p in result_root.iterdir() if p.is_file()}
        (result_root / 'runner-envelope.json').write_text(json.dumps(envelope, indent=2) + '\n')
    print(json.dumps(envelope, indent=2))
    assert envelope['status'] == 'PASS_BOUNDED'


if __name__ == '__main__':
    main()
