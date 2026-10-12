"""Prepared primary-only source phase loop; ROOT parent admission required."""
import hashlib,json,os,signal,stat,subprocess,sys,time
from pathlib import Path
ROOT=Path('/workspace/engineering/pr305')
CACHED=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534')
ATTEMPT=None
PRIMARY_STARTED=None
SOURCE='f75dcae52fcd78c5c382d3903b012e5b049ca48b'
TREE='851834ae6cc87f42abfcf3c963542191e2815599'
def digest(raw):return hashlib.sha256(raw).hexdigest()

def write(path,raw):
    with Path(path).open('xb') as stream:
        os.chmod(path,0o600);stream.write(raw);stream.flush();os.fsync(stream.fileno())

def dump(path,record):write(path,(json.dumps(record,indent=2,sort_keys=True)+'\n').encode())

def exact(row):
    p=Path(row['path']);m=p.lstat()
    assert stat.S_ISREG(m.st_mode) and not p.is_symlink()
    assert m.st_size==row['bytes'] and digest(p.read_bytes())==row['sha256']
    assert stat.S_IMODE(m.st_mode)==int(row['mode'],8)

def run_phase(name,command,env,budget,expected_returncode=0):
    directory=ATTEMPT/name;assert not directory.exists();directory.mkdir(mode=0o700)
    env=env.copy();env['TMPDIR']=str(directory);env['TMP']=str(directory);env['TEMP']=str(directory)
    if PRIMARY_STARTED is not None:
        remaining=600-(time.monotonic()-PRIMARY_STARTED)
        if remaining<=20:raise TimeoutError('LIGHT_PRIMARY_BUDGET_EXHAUSTED')
        budget=min(budget,int(remaining-15))
    started=time.monotonic();process=None;error=None;terminal={}
    with (directory/'stdout.bin').open('xb') as stdout,(directory/'stderr.bin').open('xb') as stderr:
        os.chmod(stdout.name,0o600);os.chmod(stderr.name,0o600)
        try:
            process=subprocess.Popen(['timeout','--signal=TERM','--kill-after=10s',str(budget)+'s',*command],cwd=ROOT,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
            terminal['returncode']=process.wait(timeout=budget+15)
        except BaseException as exception:
            error=exception;terminal['primary_exception_type']=type(exception).__name__
            if process is not None and process.poll() is None:
                # Only the fresh parent-created command process group, never global processes.
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
                terminal['owned_wrapper_fallback_reaped']=True
        finally:
            stdout.flush();stderr.flush();os.fsync(stdout.fileno());os.fsync(stderr.fileno())
    terminal.update({'expected_returncode':expected_returncode,'elapsed_seconds':time.monotonic()-started,'command':command,'timeout_seconds':budget,'kill_grace_seconds':10,'stdout_sha256':digest((directory/'stdout.bin').read_bytes()),'stderr_sha256':digest((directory/'stderr.bin').read_bytes())})
    dump(directory/'terminal.json',terminal)  # Persist original outputs and returncode before assertion.
    if error is not None:raise error
    if terminal['returncode']!=expected_returncode:
        raise subprocess.CalledProcessError(terminal['returncode'],command,output=(directory/'stdout.bin').read_bytes(),stderr=(directory/'stderr.bin').read_bytes())
    return directory

def package_env(env):
    env=env.copy()
    for name in ('VIRTUAL_ENV','POETRY_ACTIVE','CONDA_PREFIX','CONDA_DEFAULT_ENV','CONDA_PROMPT_MODIFIER','CONDA_SHLVL','CONDA_EXE','_CE_CONDA','_CE_M','PYTHONHOME','PYTHONPATH','PYTHON_EXE','ROBOT_ARTIFACTS','ROBOT_ROOT'):
        env.pop(name,None)
    env.update({'POETRY_VIRTUALENVS_CREATE':'true','POETRY_VIRTUALENVS_IN_PROJECT':'true','POETRY_VIRTUALENVS_OPTIONS_SYSTEM_SITE_PACKAGES':'false'})
    return env

def gateway(code):return ['rcc','task','script','-r','developer/toolkit.yaml','--','python','-c',code]

def pytest_env(env,name,package_logger):
    env=env.copy();phase=ATTEMPT/name
    # These paths must still be ABSENT; pytest/plugin owns their initial creation.
    assert not (phase/'basetemp').exists() and not (phase/'robot-output').exists()
    args=['--basetemp='+str(phase/'basetemp'),'-o','tmp_path_retention_policy=all','-o','tmp_path_retention_count=999999','--junitxml='+str(phase/'junit.xml')]
    if package_logger:args.append('--robocorp-log-output='+str(phase/'robot-output'))
    env['PYTEST_ADDOPTS']=' '.join(args)
    return env

def main():
 global ATTEMPT,PRIMARY_STARTED
 assert len(sys.argv)==4 and sys.flags.optimize==0
 p=Path(sys.argv[1]);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink() and stat.S_IMODE(m.st_mode)==0o400
 raw=p.read_bytes();assert len(raw)==m.st_size and digest(raw)==sys.argv[2];cfg=json.loads(raw)
 assert cfg['source']==SOURCE and cfg['tree']==TREE
 ATTEMPT=Path(sys.argv[3]);assert str(ATTEMPT)==cfg['outputs']['attempt']
 assert ATTEMPT.is_dir() and not ATTEMPT.is_symlink() and stat.S_IMODE(ATTEMPT.stat().st_mode)==0o700
 assert Path(sys.prefix).resolve()==CACHED.resolve()
 for row in cfg['bindings']:exact(row)
 parent_lease=json.loads((ATTEMPT/'original-parent-lease.json').read_bytes())
 assert parent_lease['source']==SOURCE and parent_lease['tree']==TREE and parent_lease['config_sha256']==sys.argv[2]
 env=os.environ.copy();primary_env=env.copy();primary_env['ACTIONS_RUNTIME_TEST_PYTHON']=str(ROOT/'action_server/.venv/bin/python')
 PRIMARY_STARTED=time.monotonic();error=None
 try:
  for phase in cfg['phases']:
   free=os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize
   assert free>=cfg['workspace_floor_bytes'],'SOURCE_LIGHT_WORKSPACE_CAPACITY_HOLD'
   phaseenv=pytest_env(primary_env,phase['name'],phase['package_logger']) if phase['pytest'] else primary_env
   directory=run_phase(phase['name'],gateway(phase['code']),phaseenv,phase['budget'])
   if phase['pytest']:
    import xml.etree.ElementTree as ET
    j=directory/'junit.xml';cases=list(ET.fromstring(j.read_bytes()).iter('testcase'));ids=[(x.get('classname'),x.get('name')) for x in cases];assert cases and len(ids)==len(set(ids))
    counts={n:sum(x.find(n) is not None for x in cases) for n in ('failure','error','skipped')};assert counts['failure']==counts['error']==0
    dump(directory/'actual-unique-source-census.json',{'unique_cases':len(cases),'passed':len(cases)-counts['skipped'],**counts,'scope':'SOURCE_ONLY_SKIPS_RETAIN_UNQUALIFIED'})
 except BaseException as caught:error=caught
 finally:
  dump(ATTEMPT/'primary-original-terminal.json',{'status':'FAIL' if error else 'PASS_SOURCE_PHASES_ONLY','source':SOURCE,'tree':TREE,'primary_exception_type':type(error).__name__ if error else None,'native_Action_lease_pool_provider_reader_scope':'NOT_RUN_HOLD'})
 if error is not None:raise error
if __name__=='__main__':main()
