"""Prepared bounded private currentf75 LIGHT. Execution requires real ROOT review/release."""
import hashlib,json,os,signal,stat,subprocess,sys,time
from pathlib import Path
ROOT=Path('/workspace/engineering/pr305')
BASE=Path(__file__).resolve().parent
CONFIG=BASE/'FROZEN-currentf75-private-bounded-LIGHT-inputs-NOTRUN.json'
CONFIG_SHA='d5cb3cd637e254df63e024503d8cef52f8dc223ddb74a777631592d13a5899a8'
ATTEMPT=Path('/workspace/engineering/pr305-currentf75-private-bounded-LIGHT-once1-owned')
SOURCE='f75dcae52fcd78c5c382d3903b012e5b049ca48b'
TREE='851834ae6cc87f42abfcf3c963542191e2815599'
CACHED=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534')
PRIMARY_STARTED=None
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

def regular_private_json(path,expected):
    p=Path(path);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink()
    assert stat.S_IMODE(m.st_mode)==0o600 and m.st_uid==os.getuid() and m.st_gid==os.getgid()
    raw=p.read_bytes();assert digest(raw)==expected;return json.loads(raw)

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

def strict_review(path,sha):
 p=Path(path);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink() and stat.S_IMODE(m.st_mode)==0o400 and m.st_uid==os.getuid() and m.st_gid==os.getgid()
 raw=p.read_bytes();assert digest(raw)==sha;return json.loads(raw)
def main():
 global PRIMARY_STARTED
 assert len(sys.argv)==5 and sys.flags.optimize==0 and 'PYTHONOPTIMIZE' not in os.environ and 'PYTEST_ADDOPTS' not in os.environ
 assert Path(sys.prefix).resolve()==CACHED.resolve()
 assert Path(sys.argv[1])==BASE/'root-one-currentf75-private-LIGHT-release.json'
 auth=regular_private_json(sys.argv[1],sys.argv[2]);review=strict_review(sys.argv[3],sys.argv[4])
 cm=CONFIG.lstat();assert stat.S_ISREG(cm.st_mode) and not CONFIG.is_symlink() and stat.S_IMODE(cm.st_mode)==0o400 and digest(CONFIG.read_bytes())==CONFIG_SHA
 cfg=json.loads(CONFIG.read_bytes());selfrow=Path(__file__);sm=selfrow.lstat();assert stat.S_ISREG(sm.st_mode) and not selfrow.is_symlink() and stat.S_IMODE(sm.st_mode)==0o444
 assert set(auth)=={'schema','decision','source','tree','config_sha256','launcher_sha256','independent_source_review','independent_preexecution_review','serialized_no_other_heavy_or_installer'}
 assert type(auth['schema']) is int and auth['schema']==1 and auth['serialized_no_other_heavy_or_installer'] is True
 assert auth['decision']=='ROOT_RELEASE_ONE_CURRENT_F75_PRIVATE_BOUNDED_LIGHT_ONLY' and auth['source']==SOURCE and auth['tree']==TREE
 assert auth['config_sha256']==CONFIG_SHA and auth['launcher_sha256']==digest(selfrow.read_bytes())
 assert auth['independent_preexecution_review']=={'path':sys.argv[3],'sha256':sys.argv[4]}
 assert review['decision']=='GO_CURRENT_F75_PRIVATE_BOUNDED_LIGHT_PREEXECUTION' and review['source']==SOURCE and review['tree']==TREE and review['config_sha256']==CONFIG_SHA and review['launcher_sha256']==auth['launcher_sha256']
 sr=auth['independent_source_review'];source_review=strict_review(sr['path'],sr['sha256']);assert source_review['decision']=='GO_CURRENT_F75_PRIVATE_BOUNDED_LIGHT_SOURCE_PREPARED_ONLY' and source_review['source']==SOURCE and source_review['tree']==TREE and source_review['config_sha256']==CONFIG_SHA and source_review['launcher_sha256']==auth['launcher_sha256']
 for r in cfg['bindings']:exact(r)
 assert not ATTEMPT.exists() and not ATTEMPT.is_symlink();ATTEMPT.mkdir(mode=0o700);os.umask(0o077)
 primary=None;post=None;before=False;status='FAILED'
 env=os.environ.copy()
 try:
  guardcmd=[sys.executable,cfg['guard']['path'],str(CONFIG),CONFIG_SHA,'before'];run_phase('before-guard',guardcmd,env,60);before=True
  # Product Toolkit imports occur only inside admitted managed gateway commands after this guard.
  PRIMARY_STARTED=time.monotonic();env['ACTIONS_RUNTIME_TEST_PYTHON']=str(ROOT/'action_server/.venv/bin/python')
  for phase in cfg['phases']:
   free=os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize
   assert free>=cfg['workspace_floor_bytes'],'SOURCE_LIGHT_WORKSPACE_CAPACITY_HOLD'
   phaseenv=pytest_env(env,phase['name'],phase['package_logger']) if phase['pytest'] else env
   directory=run_phase(phase['name'],gateway(phase['code']),phaseenv,phase['budget'])
   if phase['pytest']:
    import xml.etree.ElementTree as ET
    j=directory/'junit.xml';cases=list(ET.fromstring(j.read_bytes()).iter('testcase'));ids=[(x.get('classname'),x.get('name')) for x in cases];assert cases and len(ids)==len(set(ids))
    counts={n:sum(x.find(n) is not None for x in cases) for n in ('failure','error','skipped')};assert counts['failure']==counts['error']==0
    dump(directory/'actual-unique-source-census.json',{'unique_cases':len(cases),'passed':len(cases)-counts['skipped'],**counts,'scope':'SOURCE_ONLY_SKIPS_RETAIN_UNQUALIFIED'})
  status='PASSED_CURRENT_F75_PRIVATE_BOUNDED_LIGHT_ONLY'
 except BaseException as error:primary=error
 finally:
  # Guard has its own finite budget independent of exhausted primary. Parent hard-kill still cannot promise finally.
  PRIMARY_STARTED=None
  try:
   run_phase('always-post-guard',[sys.executable,cfg['guard']['path'],str(CONFIG),CONFIG_SHA,'after'],env,60);post='PASS'
  except BaseException as error:
   post='FAIL';dump(ATTEMPT/'always-post-exception.json',{'exception_type':type(error).__name__})
   if primary is not None:primary.add_note('Independent bounded source LIGHT postguard failed; original primary preserved')
   else:primary=error
  if primary is not None or post!='PASS':status='FAILED'
  dump(ATTEMPT/'original-terminal.json',{'status':status,'before_passed':before,'post_guard':post,'primary_exception_type':type(primary).__name__ if primary else None,'source':SOURCE,'tree':TREE,'actual_NATIVE_FULL_PROVIDER_BROWSER_RELEASE':'NOT_RUN','one_attempt':'CONSUMED_NO_AUTORETRY','reader_descendant_reaping':'UNKNOWN_BEYOND_RECORDED_OWN_WRAPPER_WAITS'})
 if primary is not None:raise primary
if __name__=='__main__':main()
