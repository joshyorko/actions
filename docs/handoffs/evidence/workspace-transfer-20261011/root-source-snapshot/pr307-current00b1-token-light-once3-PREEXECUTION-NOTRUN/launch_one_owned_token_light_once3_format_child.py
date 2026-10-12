"""Root-released once-only current00b1 LIGHT; no installs/network/native gates."""
import ast
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path('/workspace/engineering/pr307')
BASE=Path(__file__).resolve().parent
CONFIG=BASE/'immutable-one-TOKEN-LIGHT-once3-inputs.json'
CONFIG_SHA='5fd30d41b763da8596546a76f907966a5d2ffc479d35c449e30172daea9b3535'
ATTEMPT=Path('/workspace/engineering/pr307-current00b1-token-light-once3-owned')
SOURCE='00b1bb9974b73f2da65e49c9048774c84df286ba'
TREE='2663e86b2344f9e056c3259653cb905a6d195599'
CACHED=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534')
PRIMARY_STARTED=None
SELF_EXPECTED=None
ENV_KEYS=('ACTIONS_CLOUD_ROOT','ROBOCORP_HOME','XDG_CACHE_HOME','XDG_CONFIG_HOME','POETRY_CACHE_DIR','POETRY_CONFIG_DIR','UV_CACHE_DIR','npm_config_cache','GOCACHE','GOPATH','PLAYWRIGHT_BROWSERS_PATH','PYTEST_XDIST_AUTO_NUM_WORKERS','POETRY_NO_INTERACTION','BUILDX_CONFIG','ACTIONS_HOME','ROBOTS_HOME','GOMAXPROCS','ACTIONS_RUNTIME_TEST_PYTHON','PATH')

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
def guard(cfg):
    assert sys.flags.optimize==0 and Path(sys.prefix).resolve()==CACHED.resolve()
    protected=cfg['protected_repository'];protected_root=Path(protected['path'])
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=protected_root,text=True).strip()==protected['head']
    assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=protected_root,text=True).strip()==protected['tree']
    assert not subprocess.check_output(['git','status','--porcelain=v1'],cwd=protected_root)
    config_meta=CONFIG.lstat();assert stat.S_ISREG(config_meta.st_mode) and not CONFIG.is_symlink() and stat.S_IMODE(config_meta.st_mode)==0o400
    assert digest(CONFIG.read_bytes())==CONFIG_SHA
    self_path=Path(__file__);self_meta=self_path.lstat();assert stat.S_ISREG(self_meta.st_mode) and not self_path.is_symlink() and stat.S_IMODE(self_meta.st_mode)==0o444
    assert SELF_EXPECTED is not None and digest(self_path.read_bytes())==SELF_EXPECTED
    assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
    for key,value in cfg['managed_activation_expected'].items():assert os.environ[key]==value,key
    for row in cfg['bindings']:exact(row)
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==SOURCE
    assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip()==TREE
    assert not subprocess.check_output(['git','status','--porcelain=v1'],cwd=ROOT)
    proof=json.loads(Path(cfg['source_proof']['path']).read_bytes())
    assert len(proof['all_git_FS_body_and_exec_mode_exact'])==1442
    for row in proof['all_git_FS_body_and_exec_mode_exact']:
        p=ROOT/row['path'];m=p.lstat()
        if row['mode']=='120000':
            assert stat.S_ISLNK(m.st_mode);raw=os.readlink(p).encode()
        else:
            assert stat.S_ISREG(m.st_mode);raw=p.read_bytes()
            assert bool(m.st_mode&0o111)==(row['mode']=='100755')
        assert len(raw)==row['bytes'] and digest(raw)==row['sha256']
    assert len(proof['prepared30_exact_original307_head'])==30
    for row in proof['prepared30_exact_original307_head']:
        raw=(ROOT/row['path']).read_bytes();assert len(raw)==row['bytes'] and digest(raw)==row['sha256']
    for row in proof['five_existing_venvs_config_only']:exact(row['pyvenv_config'])
    assert len(proof['five_existing_venvs_config_only'])==5
    for row in proof['retained_original_evidence']:exact(row)
    for row in cfg['forbidden_generated_outputs']:
        p=Path(row['path'])
        if row['exists']:
            exact(row['binding'])
        else:
            assert not p.exists() and not p.is_symlink()
    return {'status':'PASS','source':SOURCE,'tree':TREE,'typed_FS_rows':1442,'prepared_inputs':30,'five_configs':5,'historical_refs':len(proof['retained_original_evidence'])}

def run_phase(name,command,env,budget,expected_returncode=0):
    directory=ATTEMPT/name;assert not directory.exists();directory.mkdir(mode=0o700)
    env=env.copy();env['TMPDIR']=str(directory);env['TMP']=str(directory);env['TEMP']=str(directory)
    if PRIMARY_STARTED is not None:
        remaining=780-(time.monotonic()-PRIMARY_STARTED)
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
    global PRIMARY_STARTED,SELF_EXPECTED
    assert len(sys.argv)==5 and sys.flags.optimize==0
    assert 'PYTHONOPTIMIZE' not in os.environ and 'PYTEST_ADDOPTS' not in os.environ
    assert Path(sys.prefix).resolve()==CACHED.resolve()
    raw=CONFIG.read_bytes();assert digest(raw)==CONFIG_SHA;cfg=json.loads(raw)
    auth=regular_private_json(sys.argv[1],sys.argv[2])
    reviewpath=Path(sys.argv[3]);reviewraw=reviewpath.read_bytes();assert digest(reviewraw)==sys.argv[4]
    assert reviewpath.is_file() and not reviewpath.is_symlink()
    review=json.loads(reviewraw)
    assert auth['decision']=='RELEASE_ONE_CURRENT00B1_TOKEN_LIGHT_ONCE3_ONLY' and auth['source']==SOURCE and auth['tree']==TREE
    assert auth['launcher_sha256']==digest(Path(__file__).read_bytes()) and auth['config_sha256']==CONFIG_SHA
    SELF_EXPECTED=auth['launcher_sha256']
    assert auth['independent_review']=={'path':str(reviewpath),'sha256':sys.argv[4]}
    assert review['decision']=='GO_CURRENT00B1_TOKEN_LIGHT_ONCE3_GATEWAY_PREEXECUTION'
    assert not ATTEMPT.exists();ATTEMPT.mkdir(mode=0o700)
    os.umask(0o077)
    primary=None;post=None;status='FAILED';before=False
    try:
        assert os.environ['ROBOCORP_HOME']=='/workspace/actions-cloud/robocorp'
        assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
        assert os.environ['GOMAXPROCS']=='2' and os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
        assert os.environ['ACTIONS_CLOUD_ROOT']=='/workspace/actions-cloud'
        for key,value in cfg['managed_activation_expected'].items():assert os.environ[key]==value,key
        assert not list((CACHED/'lib/python3.12/site-packages').glob('*log*pytest*'))
        assert not list((ROOT/'devutils/.venv/lib/python3.12/site-packages').glob('*log*pytest*'))
        assert list((ROOT/'action_server/.venv/lib/python3.12/site-packages').glob('*log*pytest*.dist-info'))
        assert shutil_disk_free(ROOT)>=cfg['light_workspace_floor_bytes']
        dump(ATTEMPT/'before-guard.json',guard(cfg));before=True
        dump(ATTEMPT/'activation-private.json',{k:os.environ[k] for k in ENV_KEYS})
        PRIMARY_STARTED=time.monotonic()
        env=os.environ.copy()
        for key in ('GH_TOKEN','GITHUB_TOKEN','ACTIONS_RCC_TEST_BINARY_SELECTOR','ACTIONS_RCC_TEST_BINARY','RUNTIME_RELEASE_TEST_BASELINE'):env.pop(key,None)
        env['ACTIONS_RUNTIME_TEST_PYTHON']=str(ROOT/'action_server/.venv/bin/python')
        env['PYTEST_XDIST_AUTO_NUM_WORKERS']='2'
        run_phase('doctor',['rcc','run','-r','developer/toolkit.yaml','--dev','-t','Doctor'],env,120)
        code=cfg['origin_probe_code'];run_phase('own-five-origins',gateway(code),env,120)
        # Cached outer Toolkit pytest has no Runtime logging plugin. Preserve its
        # normal task; separate absolute stdio/base/JUnit only, no plugin claim.
        t_env=pytest_env(env,'toolkit',False)
        run_phase('toolkit',['rcc','run','-r','developer/toolkit.yaml','--dev','-t','ToolkitTest'],t_env,180)
        # Select only immutable parent YAML through the existing test seam;
        # never replace/mutate the generator or source.
        red_env=pytest_env(env,'token-RED-parent2314',False)
        red_env['RUNTIME_RELEASE_TEST_BASELINE']='2314aea95795fbc1372a6f7b0b7b298b7cf124c3'
        run_phase('token-RED-parent2314',gateway('import toolkit; toolkit.poetry("devutils","run","python","-m","pytest","tests/test_runtime_release_workflows.py","-k","test_generated_pypi_oauth_credentials_are_scoped_to_exact_event","-n","0","-vv")'),red_env,180,expected_returncode=10)
        # Admit only this observed task-gateway protocol, with the original
        # checked inner pytest exit1 trace and unchanged semantic JUnit checks.
        import re
        red_stderr=(ATTEMPT/'token-RED-parent2314'/'stderr.bin').read_text()
        assert re.search(r'(?m)^subprocess\.CalledProcessError: Command .* returned non-zero exit status 1\.$',red_stderr)
        assert str(ROOT/'developer/toolkit.py') in red_stderr
        import xml.etree.ElementTree as ET
        red_cases=ET.parse(ATTEMPT/'token-RED-parent2314'/'junit.xml').getroot().findall('.//testcase')
        assert len(red_cases)==2
        assert {case.attrib['name'] for case in red_cases}=={'test_generated_pypi_oauth_credentials_are_scoped_to_exact_event[build-sdist]','test_generated_pypi_oauth_credentials_are_scoped_to_exact_event[build-wheels]'}
        for case in red_cases:
            assert len(case.findall('failure'))==1 and not case.findall('error') and not case.findall('skipped')
            failure=case.find('failure').text or ''
            assert 'canary.get' in failure and '${{ github.token }}' in failure
        dump(ATTEMPT/'token-RED-parent2314'/'expected-two-original-env-failures.json',{'status':'EXPECTED_RED_CONFIRMED','case_count':2,'underlying_original_pytest_exit':1,'observed_rcc_gateway_exit':10,'checked_inner_exit1_trace_required':True,'source_unchanged':SOURCE})
        green_env=pytest_env(env,'token-release-line-GREEN',False)
        green_env.pop('RUNTIME_RELEASE_TEST_BASELINE',None)
        run_phase('token-release-line-GREEN',gateway('import toolkit; toolkit.poetry("devutils","run","python","-m","pytest","tests/test_runtime_release_workflows.py","tests/test_actions_runtime_release_line.py","-n","0","-vv")'),green_env,180)
        f_env=pytest_env(env,'guard-focus',True)
        run_phase('guard-focus',gateway('import toolkit; toolkit.poetry("action_server","run","python","-m","pytest","tests/build_system_tests/test_oauth2_config_build.py","-n","0","-vv")'),f_env,180)
        run_phase('configured-static',gateway('import toolkit; toolkit.poetry("action_server","run","invoke","lint"); toolkit.poetry("action_server","run","invoke","typecheck"); toolkit.poetry("action_server","run","ruff","check","scripts/build_oauth2_config.py","tests/build_system_tests/test_oauth2_config_build.py"); toolkit.poetry("action_server","run","ruff","format","--check","scripts/build_oauth2_config.py","tests/build_system_tests/test_oauth2_config_build.py"); toolkit.poetry("action_server","run","mypy","scripts/build_oauth2_config.py"); toolkit.poetry("devutils","run","ruff","check","src","tests"); toolkit.poetry("devutils","run","ruff","format","--check","--config","ruff.toml","src","tests"); toolkit.poetry("devutils","run","isort","--check","src","tests"); toolkit.poetry("devutils","run","mypy","--follow-imports=silent","--namespace-packages","--explicit-package-bases","src")'),env,180)
        run_phase('generated-eight-and-Github30',gateway(cfg['generator_probe_code']),env,120)
        assert not (ATTEMPT/'controlled-invoke').exists();(ATTEMPT/'controlled-invoke').mkdir(mode=0o700)
        run_phase('controlled-invoke-command',[sys.executable,cfg['controlled_runner']['path'],str(ATTEMPT/'controlled-invoke')],package_env(env),210)
        status='PASSED_CURRENT00B1_TOKEN_LIGHT_ONCE3_ONLY'
    except BaseException as error:
        primary=error
    finally:
        try:
            dump(ATTEMPT/'always-post-guard.json',guard(cfg));post='PASS'
        except BaseException as error:
            post='FAIL';dump(ATTEMPT/'post-guard-failure.json',{'exception_type':type(error).__name__})
            if primary is not None:primary.add_note('Independent LIGHT postguard failed; retained separately')
            else:primary=error
        if primary is not None or post!='PASS':status='FAILED'
        dump(ATTEMPT/'original-terminal.json',{'status':status,'before_passed':before,'post_guard':post,'primary_exception_type':type(primary).__name__ if primary is not None else None,'source':SOURCE,'tree':TREE,'no_full_or_native_or_actual_OAuth':True})
    if primary is not None:raise primary

def shutil_disk_free(path):
    import shutil
    return shutil.disk_usage(path).free

if __name__=='__main__':main()
