"""Private-wheel Template08 B plus authenticated process-restart retrieval.

Run in an RCC-prepared Python toolchain; Runtime executes from an isolated wheel
installation. The only template adapter is ValidateBatch.inputEnvironment.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

EVIDENCE=Path('/workspace/runtime104-evidence')
ROOT=Path('/workspace/runtime104-template/08-python-action-server-robot-runtime')
sys.path.insert(0,str(ROOT))
from scripts import setup_action_server as setup
from scripts import action_server as api

# The RCC outer toolchain must not select the child Runtime's action interpreter.
for name in ("VIRTUAL_ENV", "POETRY_ACTIVE", "CONDA_PREFIX", "CONDA_DEFAULT_ENV",
             "CONDA_PROMPT_MODIFIER", "CONDA_SHLVL", "CONDA_EXE", "_CE_CONDA",
             "_CE_M", "PYTHONHOME", "PYTHONPATH", "PYTHON_EXE", "ROBOT_ROOT", "ROBOT_ARTIFACTS"):
    os.environ.pop(name, None)
os.environ["PATH"] = str(EVIDENCE / "installed/venv/bin") + os.pathsep + os.environ["PATH"]

provenance=json.loads((EVIDENCE/'wheel-provenance.json').read_text())
venv=Path(provenance['installed']['prefix'])
site=Path(provenance['installed']['module']).parent
rcc=site/'bin/rcc-18.19.3'
assert hashlib.sha256(rcc.read_bytes()).hexdigest()=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'

def candidate_runtime(work_dir):
    return {'python':'3.12.15','runtime_version':'1.0.4rc2',
            'bundled_rcc_version':'18.19.3','bundled_rcc_sha256':hashlib.sha256(rcc.read_bytes()).hexdigest(),
            'bundled_rcc_expected_path':str(rcc),'runtime_venv':str(venv),
            'candidate_source':provenance['candidate_source'],'wheel_sha256':provenance['wheel_sha256'],
            'adapter':'Private candidate wheel; checked-in Template08 runtime-lock.json remains 1.0.2'}
setup.prepare_runtime=candidate_runtime

def write(name,data):
    (EVIDENCE/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')

server=setup.LocalActionServer(EVIDENCE/'template-b-server',timeout=180)
mode_dir=EVIDENCE/'template-b'
mode_dir.mkdir(exist_ok=False)
try:
    server.__enter__()
    info=dict(server.runtime)
    info.update(private_home=str(server.home),private_datadir=str(server.datadir),
                private_robots_home=str(server.robots_home),server_pid=server.process.pid)
    client=api.ActionServerClient(server.base_url,server.api_key,timeout=600)
    result=api._execute_mode(ROOT,mode_dir,str(Path('/workspace/runtime104-rcc/rcc')),
                            client=client,runtime_info=info,timeout=900)
    assert result['status']=='PASS',result['checks']
    source=Path(result['api']['import']['robot_path'])
    expected={}
    for label,run in result['runs'].items():
        required='failure.json' if label=='failure' else 'report.json'
        names={i['name'] for i in run['artifacts']['files']}
        assert required in names,(label,names)
        for item in run['artifacts']['files']:
            content=(Path(run['evidence_dir'])/'api-artifacts'/item['name']).read_bytes()
            assert hashlib.sha256(content).hexdigest()==item['sha256']
            expected[(run['run_id'],item['name'])]=content
    failure=result['runs']['failure']
    fbytes=expected[(failure['run_id'],'failure.json')]
    assert fbytes==(source/'output/failure.json').read_bytes()
    assert json.loads(fbytes)=={'error':'deliberate failure requested','status':'FAIL'}

    def verify_retrieval(phase):
        records=[]
        for label,run in result['runs'].items():
            rid=run['run_id']
            listed=f'/api/runs/{rid}/artifacts'
            listing=client.get_json(listed)
            assert {i['name'] for i in listing}=={n for r,n in expected if r==rid}
            for noauth in ({},{'Authorization':'Bearer wrong'}):
                response=api._stdlib_transport('GET',client.base_url+listed,None,noauth,30)
                assert response.status==403
            assert api._normalize_status(client.get_json(f'/api/runs/{rid}')['status'])==run['status']
            for item in listing:
                name=item['name'];content=expected[(rid,name)]
                endpoint=f'/api/runs/{rid}/artifacts/binary-content?'+urllib.parse.urlencode({'artifact_name':name})
                assert client.request('GET',endpoint).body==content
                for headers in ({},{'Authorization':'Bearer wrong'}):
                    assert api._stdlib_transport('GET',client.base_url+endpoint,None,headers,30).status==403
                ranged=api._stdlib_transport('GET',client.base_url+endpoint,None,
                            {'Authorization':f'Bearer {client.api_key}','Range':'bytes=0-3'},30)
                assert ranged.status==206,(name,ranged.status)
                assert ranged.body==content[:4]
                assert ranged.headers.get('content-range',ranged.headers.get('Content-Range'))==f'bytes 0-{min(3,len(content)-1)}/{len(content)}'
                records.append({'run_id':rid,'label':label,'name':name,'size':len(content),
                                'sha256':hashlib.sha256(content).hexdigest(),'binary_status':200,
                                'range_status':206,'missing_auth_status':403,'wrong_auth_status':403})
            textname='failure.json' if label=='failure' else 'report.json'
            textpath=f'/api/runs/{rid}/artifacts/text-content?'+urllib.parse.urlencode({'artifact_names':textname})
            assert client.get_json(textpath)[textname]==expected[(rid,textname)].decode()
            for headers in ({},{'Authorization':'Bearer wrong'}):
                assert api._stdlib_transport('GET',client.base_url+textpath,None,headers,30).status==403
        return records

    before=verify_retrieval('before_restart')
    old_pid=server.process.pid
    command=server.process.args
    server.close()
    assert server.process.poll() is not None
    unavailable=source.with_name(source.name+'-unavailable')
    source.rename(unavailable)
    assert not source.exists()
    env=os.environ.copy()
    env.update(HOME=str(server.home),ACTIONS_HOME=str(server.actions_home),
               ROBOTS_HOME=str(server.robots_home),ROBOCORP_HOME=str(server.actions_home),
               RCC_HOLOTREE_MODE='private')
    for key in ('INVOICE_INPUT','ROBOT_ARTIFACTS'):
        env.pop(key,None)
    server.server_log_file=server.server_log.open('ab')
    server.process=subprocess.Popen(command,cwd=server.state_dir,env=env,stdin=subprocess.DEVNULL,
            stdout=server.server_log_file,stderr=subprocess.STDOUT,start_new_session=True)
    setup._readiness(server.base_url,server.api_key,server.process,time.monotonic()+180)
    assert server.process.pid!=old_pid
    after=verify_retrieval('after_restart')
    assert after==before
    assert not source.exists()
    receipt={'status':'PASS','candidate_source':provenance['candidate_source'],'wheel_sha256':provenance['wheel_sha256'],
             'template_source':'ee2f6c1d7dbc7f84312b046f66d019a09a9c6a50',
             'template_adapter':'ValidateBatch.inputEnvironment: [INVOICE_INPUT]',
             'template_source_digest':result['source_digest'],
             'task_checks':result['checks'],'failure_bytes_exact':True,
             'before_restart':before,'after_restart':after,
             'new_runtime_process':True,'old_process_exited':True,'original_robot_path_unavailable':True,
             'database_reused':True,'bundled_rcc_sha256':hashlib.sha256(rcc.read_bytes()).hexdigest()}
    write('restart-retrieval.json',receipt)
    print('B PASS; RESTART PASS;',len(after),'artifacts re-downloaded with matching hashes',flush=True)
finally:
    server.close()
