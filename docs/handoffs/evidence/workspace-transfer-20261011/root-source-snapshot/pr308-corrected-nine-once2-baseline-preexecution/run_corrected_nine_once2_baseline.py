"""ONE corrected service-free baseline; requires independent review and ROOT release."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

CONFIG_PATH = Path('/workspace/engineering/pr308-corrected-nine-once2-baseline-preexecution/frozen-corrected-nine-once2-baseline-execution-config-NOTRUN.json')
CONFIG_SHA256 = 'd8dd253da2711437e1c94db0950d1352afbc963963d6ae1ec3c14d43eacd336a'

def binding(path):
    path = Path(path)
    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode) and not path.is_symlink()
    body = path.read_bytes()
    return {'path': str(path), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'mode': oct(stat.S_IMODE(metadata.st_mode))}

def read(row):
    assert binding(row['path']) == row
    return Path(row['path']).read_bytes()

def fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def durable_json(path, value, mode=0o600):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(mode)
    fsync_directory(path.parent)

parser = argparse.ArgumentParser()
parser.add_argument('--release', required=True)
parser.add_argument('--release-sha256', required=True)
args = parser.parse_args()
assert not sys.flags.optimize and 'PYTHONOPTIMIZE' not in os.environ
assert 'PYTEST_ADDOPTS' not in os.environ and 'RCC_RELOAD_PRIVATE_MUTANT' not in os.environ
config_binding = binding(CONFIG_PATH)
assert config_binding['sha256'] == CONFIG_SHA256 and config_binding['mode'] == '0o400'
config = json.loads(read(config_binding))
assert config['schema'] == 1 and config['source_leaves'] == 1440
contract = json.loads(read(config['contract']))
for name in ('source_config', 'native_readonly_config', 'native_readonly_original_release', 'readonly_guard', 'source_independent', 'final_source_owner', 'private_source_owner', 'test_source', 'original_failed_baseline', 'original_contract', 'original_launcher'):
    read(config[name])
assert json.loads(read(config['source_independent']))['decision'] == 'GO_PRIVATE_CORRECTED_NINE_CATALOG_COPY_AND_HELD_LOCK_SOURCE_ONLY'
assert contract['source'] == config['source'] and contract['tree'] == config['tree']
assert contract['test_source_binding'] == config['test_source']
release_path = Path(args.release)
release_binding = binding(release_path)
assert release_binding['mode'] == '0o600' and release_binding['sha256'] == args.release_sha256
assert release_path.lstat().st_uid == os.getuid()
release = json.loads(read(release_binding))
assert set(release) == set(config['required_ROOT_release_fields'])
assert release['schema'] == 1 and release['scope'] == config['required_ROOT_release_scope']
assert release['source'] == config['source'] and release['tree'] == config['tree']
assert release['baseline_only'] is True and release['native'] == release['mutants'] == 'NOT_RUN'
self_binding = binding(Path(__file__).resolve())
assert release['launcher_binding'] == self_binding
assert release['config_binding'] == config_binding and release['contract_binding'] == config['contract']
review = json.loads(read(release['independent_preexecution_binding']))
assert review['decision'] == config['required_preexecution_decision']
assert review['launcher_binding'] == self_binding and review['config_binding'] == config_binding and review['contract_binding'] == config['contract']
source_cfg = json.loads(read(config['source_config']))
assert len(source_cfg['expected_activation_exports']) == 18
assert all(os.environ.get(key) == value for key, value in source_cfg['expected_activation_exports'].items())
assert os.environ['PATH'].split(os.pathsep)[:2] == ['/workspace/actions-cloud/bin', '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin']
assert all(key not in os.environ for key in source_cfg['forbidden_actual_operator_exports'])
native_cfg = json.loads(read(config['native_readonly_config']))
assert len(native_cfg['concrete_own_origins']) == 5
owned = Path(config['owned_root'])
assert not owned.exists() and not owned.is_symlink()
os.umask(0o077)
owned.mkdir(mode=0o700, exist_ok=False)
phase = owned / 'baseline'
phase.mkdir(mode=0o700)
fsync_directory(owned.parent)
fsync_directory(owned)
durable_json(owned / 'consumed-distinct-root-release.json', {'release_binding': release_binding, 'release': release, 'native': 'NOT_RUN', 'mutants': 'NOT_RUN'})
outcomes = {}
started = time.monotonic()

def run(name, argv):
    begin = time.monotonic()
    with (phase / (name + '.stdout.private')).open('xb') as stdout, (phase / (name + '.stderr.private')).open('xb') as stderr:
        try:
            completed = subprocess.run(argv, cwd='/workspace/engineering/pr308/action_server', stdout=stdout, stderr=stderr, timeout=config['subprocess_parent_seconds'], check=False)
            result = {'returncode': completed.returncode, 'elapsed_seconds': time.monotonic() - begin}
        except BaseException as error:
            result = {'exception_class': type(error).__name__, 'elapsed_seconds': time.monotonic() - begin}
        stdout.flush()
        os.fsync(stdout.fileno())
        stderr.flush()
        os.fsync(stderr.fileno())
    durable_json(phase / (name + '.terminal.json'), result)
    outcomes[name] = result
    return result.get('returncode') == 0

try:
    if run('before', config['readonly_guard_argv']):
        origins_passed = True
        for index, row in enumerate(native_cfg['concrete_own_origins']):
            code = 'import importlib,pathlib,sys; m=importlib.import_module(' + repr(row['module']) + '); assert pathlib.Path(sys.prefix).resolve()==pathlib.Path(' + repr(row['prefix']) + ').resolve(); assert pathlib.Path(m.__file__).resolve()==pathlib.Path(' + repr(row['origin']) + ').resolve()'
            if not run('own-origin-' + str(index), ['timeout', '--signal=TERM', '--kill-after=10s', '15s', row['python'], '-c', code]):
                origins_passed = False
                break
        if origins_passed:
            assert not (phase / 'basetemp').exists() and not (phase / 'basetemp').is_symlink()
            assert not (phase / 'pytest-logging').exists() and not (phase / 'original-junit.xml').exists()
            run('corrected-nine-baseline', contract['baseline_argv_after_exact_managed_activation'])
finally:
    run('always-post', config['readonly_guard_argv'])

result = {'schema': 1, 'scope': 'ORIGINAL_ONCE2_CORRECTED_NINE_BASELINE_ONLY_NO_NATIVE_NO_MUTANTS', 'source': config['source'], 'tree': config['tree'], 'source_leaves': 1440, 'launcher_binding': self_binding, 'config_binding': config_binding, 'contract_binding': config['contract'], 'release_binding': release_binding, 'independent_preexecution_binding': release['independent_preexecution_binding'], 'corrected_source_independent': config['source_independent'], 'original_failed_baseline_retained': config['original_failed_baseline'], 'outcomes': outcomes, 'elapsed_seconds': time.monotonic() - started, 'capture': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'native': 'NOT_RUN', 'mutants': 'NOT_RUN', 'source_adoption': 'NONE', 'baseline_accepted': False, 'junit': 'ABSENT_OR_UNADMITTED'}
junit = phase / 'original-junit.xml'
if junit.exists():
    try:
        junit_binding = binding(junit)
        raw = read(junit_binding)
        tree = ET.fromstring(raw)
        cases = list(tree.iter('testcase'))
        counts = {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
        for case in cases:
            key = 'failed' if case.find('failure') is not None else 'errors' if case.find('error') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
            counts[key] += 1
        names = [case.get('name') for case in cases]
        suites = list(tree.iter('testsuite'))
        suite_counts = {key: sum(int(suite.get(key, '-1')) for suite in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
        envelopes_match = bool(suites) and suite_counts == {'tests': 9, 'failures': 0, 'errors': 0, 'skipped': 0}
        required_phases = {'before', 'always-post', 'corrected-nine-baseline'} | {'own-origin-' + str(i) for i in range(5)}
        result['junit'] = {'binding': junit_binding, 'counts': counts, 'names': names, 'reported_suite_counts': suite_counts}
        result['baseline_accepted'] = envelopes_match and counts == {'passed': 9, 'failed': 0, 'errors': 0, 'skipped': 0} and len(names) == len(set(names)) == 9 and set(names) == {row['test'] for row in contract['case_map']} and set(outcomes) == required_phases and all(value.get('returncode') == 0 for value in outcomes.values())
    except BaseException as error:
        result['junit_admission_exception_class'] = type(error).__name__
durable_json(owned / 'OWNERFINAL-root-one-original-corrected-nine-once2-baseline.json', result, 0o400)
print(json.dumps({'baseline_accepted': result['baseline_accepted'], 'owner_path': str(owned / 'OWNERFINAL-root-one-original-corrected-nine-once2-baseline.json'), 'native': 'NOT_RUN', 'mutants': 'NOT_RUN'}))
raise SystemExit(0 if result['baseline_accepted'] else 1)
