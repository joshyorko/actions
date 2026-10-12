import json,hashlib,os,subprocess,time
from pathlib import Path
O=Path(__file__).resolve().parent;root=O/'pure-qualification-GREEN-once'
assert 'PYTEST_ADDOPTS' not in os.environ and not os.environ.get('PYTHONOPTIMIZE')
assert not root.exists() and not root.is_symlink();os.umask(0o077);root.mkdir(mode=0o700)
argv=['timeout','--signal=TERM','--kill-after=10s','120s','/workspace/engineering/pr308/action_server/.venv/bin/python','-m','pytest','--noconftest','-n0','-q',str(O/'test_current_qualified_FULL_provenance_v8.py'),f'--basetemp={root}/pytest','-o','tmp_path_retention_policy=all',f'--robocorp-log-output={root}/robocorp-log',f'--junitxml={root}/original-junit.xml']
log=root/'original.private.log';start=time.monotonic()
with log.open('xb') as out:cp=subprocess.run(argv,cwd=O,stdout=out,stderr=subprocess.STDOUT)
(root/'terminal.json').write_text(json.dumps(dict(returncode=cp.returncode,seconds=time.monotonic()-start,argv=argv,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),native='NOT_RUN'),indent=2)+'\n')
for p in (log,root/'terminal.json',root/'original-junit.xml'):p.chmod(0o400)
print(json.dumps(dict(returncode=cp.returncode,seconds=time.monotonic()-start)));raise SystemExit(cp.returncode)
