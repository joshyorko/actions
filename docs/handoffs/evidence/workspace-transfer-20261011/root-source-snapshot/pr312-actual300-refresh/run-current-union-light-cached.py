import os,runpy,subprocess,sys,json,hashlib
from pathlib import Path
import toolkit
D=Path('/workspace/engineering/pr312-actual300-refresh');R=toolkit.REPOSITORY_ROOT
assert R==Path('/workspace/engineering/runtime-checkout-eol')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()=='ec70a2928461941c129b1c05332dc441070e0184'
assert subprocess.check_output(['git','status','--porcelain'],cwd=R)==b''
assert os.environ['ROBOCORP_HOME']=='/workspace/actions-cloud/robocorp'
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
for p,mode in [(Path('/workspace/actions-cloud/bin/rcc'),0o700),(R/'action_server/src/actions/server/bin/rcc-18.19.3',0o711)]:
 assert hashlib.sha256(p.read_bytes()).hexdigest()=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428';assert p.stat().st_mode&0o777==mode
toolkit.doctor()
for name in ['verify-own-prepared.py','verify-retained-native-helper-browser-pre-light.py','verify-retained-V5-raw-and-driver-pre-light.py']:runpy.run_path(str(D/name),run_name='__main__')
toolkit.toolkit_test()
toolkit.poetry('action_server','run','python','-m','pytest','-n','0','-q','tests/action_server_tests/test_shutdown_response_order.py','tests/action_server_tests/test_auth_route_inventory.py','tests/action_server_tests/test_auth_route_enforcement.py','tests/action_server_tests/run_outputs/test_transport.py','--junitxml='+str(D/'current-union-scoped-junit.xml'))
toolkit.poetry('devutils','run','python','-m','pytest','-n','0','-q','tests/test_runtime_checkout_bytes.py','tests/test_runtime_checkout_workflows.py','-k','RuntimeCheckoutBytesTests or runtime_checkout','--junitxml='+str(D/'current-EOL-junit.xml'))
toolkit.poetry('action_server','run','invoke','lint','typecheck')
runpy.run_path(str(D/'generator-all-eight-roundtrip.py'),run_name='__main__')
for name in ['verify-retained-native-helper-browser-post-light.py','verify-retained-V5-raw-and-driver-post-light.py']:runpy.run_path(str(D/name),run_name='__main__')
print('PURE_CACHED_CURRENT_E3C_UNION_LIGHT_ALL_PASS',flush=True)
