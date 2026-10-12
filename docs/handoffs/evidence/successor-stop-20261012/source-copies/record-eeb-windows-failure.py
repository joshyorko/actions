import datetime
import hashlib
import json
from pathlib import Path
import subprocess

root=Path('/workspace/successor-evidence/pr308')
p=root/'decoded-eeb-windows114674512952.log'
b=p.read_bytes(); text=b.decode()
assert '2 failed, 1413 passed, 225 skipped' in text
assert 'int(pid_file.read_text()) = 6976' in text and 'process.pid = 5536' in text
assert 'int(pid_file.read_text()) = 5392' in text and 'process.pid = 6312' in text
v=json.loads(subprocess.check_output(['gh','api','repos/joshyorko/actions/git/commits/7ba382a61a5b27831f8eaf759dd5a10ae4a4b54a']))
assert v['tree']['sha']=='ce7ae02d6c7db06ceffedf771c6eb365d11517b9'
assert [q['sha'] for q in v['parents']]==['48eeaf171e695d9b8ac140ea53239eaeb6eff331','eeb806e7699d7f8e6878d5cc1dd83cd22e795ff5']
receipt={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run':38207623439,'job':114674512952,'head':'eeb806e7699d7f8e6878d5cc1dd83cd22e795ff5','producer':{'sha':v['sha'],'tree':v['tree']['sha'],'parents':[q['sha'] for q in v['parents']]},'conclusion':'failure','unit':{'failed':2,'passed':1413,'skipped':225,'seconds':301.50},'failures':[{'node':'test_dakota_rcc_acceptance.py::test_provider_startup_failure_uses_bounded_kill_fallback','assertion':'reported Python PID equals original Popen PID','reported_pid':6976,'popen_pid':5536},{'node':'test_provider_startup_cleanup.py::test_startup_regression_reports_failed_cleanup_and_disposes_original_child','assertion':'expected CONTROLLED_OWNERSHIP_FAILURE diagnostic; actual failed at prior unsupported PID equality','reported_pid':5392,'popen_pid':6312}],'actual_cause':'Both test failures are the new unsupported wrapper/child PID equality assertion. CPython Windows venv redirectors support a distinct child process. Cleanup completeness was not reached by these assertions and remains unqualified.','python':'3.12.15; actual Poetry virtualenv Scripts/python.exe','raw_log':{'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'local_only':True},'production_change':False,'native_baseline_attempts':0,'historical_mac_cause':'UNKNOWN'}
(root/'eeb-windows-source-terminal-diagnosis.json').write_text(json.dumps(receipt,indent=2)+'\n')
c=root/'cpython31215-launcher.c'; data=c.read_bytes()
(root/'cpython31215-venv-launcher-source-provenance.json').write_text(json.dumps({'repository':'python/cpython','ref':'v3.12.15','path':'PC/launcher.c','git_blob':'dc265533740b6763124480162e791e6a9fd92e27','url':'https://github.com/python/cpython/blob/v3.12.15/PC/launcher.c','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'local_only_source_copy':True,'mechanism':'VENV_REDIRECT selects venv variant; run_child invokes CreateProcessW then WaitForSingleObjectEx on the created child handle','limits':'This public source establishes supported wrapper/child behavior, not exact source-byte attribution for the CI executable'},indent=2)+'\n')
print('Windows failure and public source provenance recorded')
