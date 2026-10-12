"""One explicitly released read-only data guard; no storage operation."""
import hashlib, json, os, stat, sys, traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
OWNED=Path('/workspace/engineering/completed8d49-four-root-storage-corrected-guard-readonly-probe-v3')
GUARD=HERE/'guard_readonly.py'
CONFIG=Path('/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v2/private-four-root-input-supplement.json')
EXPECTED_GUARD_SHA='897294c4602dea6f847d36ba0bfba3e64bf22d885a6fe16f000dc4fed013f98f'
assert sys.flags.optimize==0 and not OWNED.exists()
os.umask(0o077);OWNED.mkdir(mode=0o700)
raw=GUARD.read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED_GUARD_SHA
ns={'__name__':'verified_private_guard'};exec(compile(raw,str(GUARD),'exec'),ns)
try:
 result=ns['protected'](ns['load_config'](CONFIG),phase='readonly-probe',capture_parent=OWNED)
 terminal={'status':'PASS_READONLY_DATA_ONLY','returncode':0,'result':result,'archive':'NOT_RUN','native':'NOT_RUN'}
except BaseException as exc:
 terminal={'status':'FAIL_READONLY_DATA_ONLY','returncode':1,'exception_type':type(exc).__name__,'archive':'NOT_RUN','native':'NOT_RUN'}
 with (OWNED/'exception.private.log').open('x') as f:os.chmod(f.name,0o600);f.write(traceback.format_exc());f.flush();os.fsync(f.fileno())
with (OWNED/'original-readonly-probe-terminal.json').open('x') as f:
 os.chmod(f.name,0o600);f.write(json.dumps(terminal,indent=2,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
sys.exit(terminal['returncode'])
