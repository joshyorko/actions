import json, os, sys, subprocess, stat, hashlib, time, datetime, xml.etree.ElementTree as ET
from pathlib import Path

def read(row):
    p = Path(row['path']); s = p.lstat(); raw = p.read_bytes()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'] and stat.S_IMODE(s.st_mode) == int(row['mode'], 8)
    return raw

review = {'path': '/workspace/engineering/pr308-current8d49-nine-real-reload-drain-independent-preexecution-review/OWNERFINAL-independent-current8d49-nine-real-SQLite-route-pool-control-SOURCE-and-baseline-first-PREEXEC-review.json', 'bytes': 16437, 'sha256': '6da104c02c146bd2594a1c307a81b6280ce9665664cc3f34d634a886e3e3daa0', 'mode': '0o400'}
contract = json.loads(read(json.loads(read(review))['ROOT_command_contract']))
assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE') and 'PYTEST_ADDOPTS' not in os.environ and 'RCC_RELOAD_PRIVATE_MUTANT' not in os.environ
source_cfg = json.loads(Path('/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/frozen-current8d49-source-LIGHT-inputs-v3.json').read_bytes())
assert len(source_cfg['expected_activation_exports']) == 18 and all(os.environ.get(k) == v for k, v in source_cfg['expected_activation_exports'].items())
assert os.environ['PATH'].split(os.pathsep)[:2] == ['/workspace/actions-cloud/bin', '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin']
assert all(k not in os.environ for k in source_cfg['forbidden_actual_operator_exports'])
read(contract['test_source_binding'])
native_cfg_path = Path('/workspace/engineering/rcc-current8d49-qualified-V9-entry-bootstrap-preparation/FROZEN-current8d49-control3-qualified-V9-entry-config-v2.json')
native_raw = native_cfg_path.read_bytes(); assert hashlib.sha256(native_raw).hexdigest() == '5dc48075c8a2c91042f38a4c4c8941e9eb7f5c0feb82dcc93917cb8ec76c9f25'
native_cfg = json.loads(native_raw)
owned = Path('/workspace/engineering/pr308-current8d49-nine-real-source-control-root-once-1')
owned.mkdir(mode=0o700, exist_ok=False); os.umask(0o077)
phase = owned / 'baseline'; phase.mkdir(mode=0o700)
release = {'scope': 'ROOT_SINGLE_SERVICEFREE_NINE_BASELINE_ONLY_NO_MUTANTS', 'review': review, 'contract': json.loads(read(review))['ROOT_command_contract'], 'source': contract['source'], 'tree': contract['tree'], 'native': 'NOT_RUN', 'production_pin': '18.19.3_UNCHANGED'}
with (owned / 'root-release.json').open('x') as f: json.dump(release, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
guard = ['timeout', '--signal=TERM', '--kill-after=10s', '120s', '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python', '/workspace/engineering/rcc-current8d49-qualified-V9-entry-bootstrap-preparation/readonly_current_input_guard_v9.py', '--config', str(native_cfg_path), '--config-sha256', '5dc48075c8a2c91042f38a4c4c8941e9eb7f5c0feb82dcc93917cb8ec76c9f25', '--release', '/workspace/engineering/root-rcc-current8d49-control3-V9-one-release.json', '--release-sha256', 'a131e30087742764ba6dbdbc2634749924133431de3310b2065ced446b97bf3b', '--label', 'control3']
outcomes = {}; started = time.monotonic()
def run(name, argv):
    begin = time.monotonic()
    with (phase / (name + '.stdout.private')).open('xb') as stdout, (phase / (name + '.stderr.private')).open('xb') as stderr:
        try:
            c = subprocess.run(argv, cwd='/workspace/engineering/pr308/action_server', stdout=stdout, stderr=stderr, timeout=135, check=False)
            row = {'returncode': c.returncode, 'elapsed_seconds': time.monotonic() - begin}
        except BaseException as e:
            row = {'exception_class': type(e).__name__, 'elapsed_seconds': time.monotonic() - begin}
        stdout.flush(); os.fsync(stdout.fileno()); stderr.flush(); os.fsync(stderr.fileno())
    with (phase / (name + '.terminal.json')).open('x') as f: json.dump(row, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    outcomes[name] = row
    return row.get('returncode') == 0

try:
    if run('before', guard):
        all_origins = True
        for i, row in enumerate(native_cfg['concrete_own_origins']):
            code = 'import importlib,pathlib,sys; m=importlib.import_module(' + repr(row['module']) + '); assert pathlib.Path(sys.prefix).resolve()==pathlib.Path(' + repr(row['prefix']) + ').resolve(); assert pathlib.Path(m.__file__).resolve()==pathlib.Path(' + repr(row['origin']) + ').resolve()'
            if not run('own-origin-' + str(i), ['timeout', '--signal=TERM', '--kill-after=10s', '15s', row['python'], '-c', code]):
                all_origins = False; break
        if all_origins:
            run('original-nine-baseline', contract['baseline_argv_after_exact_managed_activation'])
finally:
    run('always-post', guard)
result = {'scope': 'ORIGINAL_NINE_SOURCE_BASELINE_ONLY_NO_NATIVE_NO_MUTANTS', 'source': contract['source'], 'tree': contract['tree'], 'independent_review': review, 'outcomes': outcomes, 'elapsed_seconds': time.monotonic() - started, 'capture': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'native': 'NOT_RUN', 'mutants': 'NOT_RUN', 'source_adoption': 'NONE'}
junit = phase / 'original-junit.xml'
if junit.exists():
    raw = junit.read_bytes(); tests = list(ET.fromstring(raw).iter('testcase'))
    counts = {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
    for t in tests:
        key = 'failed' if t.find('failure') is not None else 'errors' if t.find('error') is not None else 'skipped' if t.find('skipped') is not None else 'passed'
        counts[key] += 1
    result['junit'] = {'path': str(junit), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'counts': counts, 'names': [t.get('name') for t in tests]}
    result['baseline_accepted'] = counts == {'passed': 9, 'failed': 0, 'errors': 0, 'skipped': 0} and set(result['junit']['names']) == {r['test'] for r in contract['case_map']} and all(v.get('returncode') == 0 for v in outcomes.values()) and 'original-nine-baseline' in outcomes and 'always-post' in outcomes
else:
    result['baseline_accepted'] = False
out = owned / 'OWNERFINAL-root-one-original-nine-real-source-baseline.json'
out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n'); out.chmod(0o400)
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['baseline_accepted'] else 1)
