from pathlib import Path
import hashlib, json, subprocess
import toolkit

root = toolkit.REPOSITORY_ROOT
out = Path('/workspace/engineering/pr300-actual299-refresh')
assert root == Path('/workspace/engineering/pr300')
previous = json.loads(Path('/workspace/engineering/pr302-actual310-source-refresh/own-bootstrap-reuse-complete-gateway-proof.json').read_text())
full = json.loads(Path('/workspace/engineering/pr310-current-refresh/bootstrap-reuse.json').read_text())
inputs = sorted(set(previous['all19inputs_exact']) | set(full['inputs_sha256']))
assert len(inputs) == 30
records = {}
for name in inputs:
    before = subprocess.check_output(['git', 'show', '3155fc55ea7d47afbc547fddc963b5860462924b:' + name], cwd=root)
    now = (root / name).read_bytes()
    assert before == now, name
    records[name] = hashlib.sha256(now).hexdigest()
log = Path('/workspace/engineering/pr299-refresh-owned/bootstrap.log')
assert hashlib.sha256(log.read_bytes()).hexdigest() == '8bdeac2f153ad303d8c3b68743517072374630ef3af2b488fb52824a006fab69'
assert 'actual main robot run" was SUCCESS' in log.read_text()
origins = []
environments = {}
for package, module in [('actions','actions'), ('actions-http-helper','actions_http'), ('devutils','devutils.invoke_utils'), ('work-items','actions.work_items'), ('action_server','actions.server.run_outputs.transport')]:
    prefix = root / package / '.venv'
    cfg = prefix / 'pyvenv.cfg'
    assert cfg.is_file()
    environments[package] = {'config_sha256': hashlib.sha256(cfg.read_bytes()).hexdigest(), 'python_resolved': str((prefix / 'bin/python').resolve())}
    destination = out / ('origin-' + package + '.json')
    code = ('import importlib,json,sys; from pathlib import Path; m=importlib.import_module(' + repr(module) + '); prefix=Path(' + repr(str(prefix)) + '); source=Path(m.__file__).resolve(); assert Path(sys.prefix).resolve()==prefix.resolve(); assert source.is_relative_to(Path(' + repr(str(root / package / 'src')) + ').resolve()); Path(' + repr(str(destination)) + ').write_text(json.dumps({"module":' + repr(module) + ',"origin":str(source),"prefix":sys.prefix,"python":sys.executable}))')
    toolkit.poetry(package, 'run', 'python', '-c', code)
    origins.append(json.loads(destination.read_text()))
(out / 'own-Bootstrap-reuse-inputs-and-origins.json').write_text(json.dumps({'status':'OWN_PREPARED_ENVIRONMENT_REUSE_VERIFIED_NO_INSTALLER', 'prepared_source':'3155fc55ea7d47afbc547fddc963b5860462924b', 'original_Bootstrap_log':str(log), 'original_Bootstrap_log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(), 'measured_input_count':len(inputs), 'all30_current_inputs_exact_prepared_Git_bytes':records, 'five_own_environment_configs':environments, 'five_actual_concrete_module_origins_and_prefixes':origins, 'environment_preparation': 'Independent copies of matching prepared pr299 environments; only checkout path metadata and launcher shebangs rebound. Original inputs checked byte unchanged; no installer/download.', 'new_Bootstrap_run':False}, indent=2) + '\n')
print('30 prepared inputs plus all5 own concrete module origins/prefixes PASS; no installer', flush=True)
