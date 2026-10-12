import hashlib,json,os,subprocess,sys,time
from pathlib import Path
O=Path(__file__).resolve().parent
label=sys.argv[1]
assert label == 'GREEN-TEMPORAL'
assert not os.environ.get('PYTHONOPTIMIZE') and 'PYTEST_ADDOPTS' not in os.environ
cfg=json.loads(Path('/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/frozen-current8d49-source-LIGHT-inputs-v3.json').read_text())
for k,v in cfg['expected_activation_exports'].items(): assert os.environ.get(k)==v,k
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
root=O/f'pure-fixture-logger-{label}-owned-once'
assert not root.exists() and not root.is_symlink()
os.umask(0o077);root.mkdir(mode=0o700)
tests=[str(O/'test_historical_fixture_and_logger_servicefree_v8.py')]
if label=='GREEN-TEMPORAL':tests.insert(0,str(O/'test_current_count_alias_servicefree_v8.py'))
argv=['timeout','--signal=TERM','--kill-after=10s','120s','/workspace/engineering/pr308/action_server/.venv/bin/python','-m','pytest','--noconftest','-n0','-q',*tests]
if label=='RED':argv+=['-k','historical_transport_baseline or logger_argv']
argv += [f'--basetemp={root}/pytest','-o','tmp_path_retention_policy=all',f'--robocorp-log-output={root}/robocorp-log',f'--junitxml={root}/original-{label}-junit.xml']
env=os.environ.copy();env['PRIVATE_V8_FIXTURE_BASELINE']='ORIGINAL' if label=='RED' else 'CURRENT'
log=root/f'original-{label}.private.log'
start=time.monotonic()
with log.open('xb') as out: cp=subprocess.run(argv,cwd=O,env=env,stdout=out,stderr=subprocess.STDOUT)
row=dict(argv=argv,returncode=cp.returncode,elapsed_s=time.monotonic()-start,baseline=env['PRIVATE_V8_FIXTURE_BASELINE'],native='NOT_RUN',log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
(root/f'original-{label}-terminal.json').write_text(json.dumps(row,indent=2)+'\n')
for p in (log,root/f'original-{label}-terminal.json',root/f'original-{label}-junit.xml'):p.chmod(0o400)
print(json.dumps({k:row[k] for k in ('returncode','elapsed_s','native')}))
sys.exit(0 if label=='RED' and cp.returncode==1 else cp.returncode)
