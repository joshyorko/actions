"""Unchanged real Invoke task/helper in an owned stage; fake gh only."""
import ast
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path('/workspace/engineering/pr307')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path, raw):
    path = Path(path)
    assert not path.exists()
    with path.open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

def run(command, cwd, env, prefix, timeout):
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        write(str(prefix)+'.stdout', error.stdout or b'')
        write(str(prefix)+'.stderr', error.stderr or b'')
        write(str(prefix)+'.terminal.json', json.dumps({'status':'TIMEOUT','timeout':timeout}).encode())
        raise
    write(str(prefix)+'.stdout', result.stdout)
    write(str(prefix)+'.stderr', result.stderr)
    write(str(prefix)+'.terminal.json', json.dumps({'returncode':result.returncode}).encode())
    return result

def main():
    assert sys.flags.optimize == 0 and 'PYTHONOPTIMIZE' not in os.environ
    owned=Path(sys.argv[1]); assert owned.is_dir() and stat.S_IMODE(owned.stat().st_mode)==0o700
    stage=owned/'stage'; assert not stage.exists(); stage.mkdir(mode=0o700)
    package=stage/'action_server'; package.mkdir(mode=0o700)
    (package/'scripts').mkdir(mode=0o700)
    (package/'src/actions/server').mkdir(parents=True, mode=0o700)
    copied=[]
    for name in ('tasks.py','pyproject.toml','poetry.lock','scripts/build_oauth2_config.py'):
        original=ROOT/'action_server'/name; destination=package/name
        write(destination,original.read_bytes())
        assert destination.read_bytes()==original.read_bytes()
        copied.append({'relative':name,'sha256':sha(destination),'bytes':destination.stat().st_size})
    (package/'.venv').symlink_to(ROOT/'action_server/.venv',target_is_directory=True)
    (stage/'devutils').symlink_to(ROOT/'devutils',target_is_directory=True)
    bin_dir=owned/'controlled-bin'; bin_dir.mkdir(mode=0o700)
    fake=bin_dir/'gh'
    write(fake,('#!'+sys.executable+'\n'+'''import json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
name=sys.argv[-1].rsplit('/',1)[-1]
assert sys.argv[1:4]==['api','-H','Accept: application/vnd.github.raw']
assert sys.argv[-1].startswith('repos/Sema4AI/oauth-public-configs/contents/')
assert name in ('actions-oauth-config.yaml','oauth-config.yaml')
parent=Path('/proc')/str(os.getppid())
row={'input':name,'helper_argv0':parent.joinpath('cmdline').read_bytes().split(b'\\0')[0].decode(),'helper_exe':os.readlink(parent/'exe')}
with (root/'gateway-children.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\\n')
if os.environ.get('CONTROLLED_OAUTH_SECOND_FAILURE')=='1' and name=='oauth-config.yaml':
 sys.stderr.write('controlled private cause must be withheld\\n');sys.exit(17)
sys.stdout.buffer.write(b"formatVersion: '1.0.0'\\noauth2Config:\\n  providers: {}\\n")
''').encode())
    fake.chmod(0o700)
    outer_source=Path('/workspace/engineering/pr307-guard-owned/outer_invoke_no_yaml.py')
    outer=owned/'outer_invoke_no_yaml.py';write(outer,outer_source.read_bytes())
    assert sha(outer)== '394e1434e46dc86888be313dd8896cf42def904045945543e9f890b3d81e3ba3'
    env=os.environ.copy()
    for name in ('GH_TOKEN','GITHUB_TOKEN','PYTHONOPTIMIZE','PYTEST_ADDOPTS'):
        env.pop(name,None)
    env['PATH']=str(bin_dir)+os.pathsep+env['PATH']
    assert shutil.which('gh',path=env['PATH'])==str(fake)
    env['VIRTUAL_ENV']=str(owned/'foreign-outer-environment')
    dest=package/'src/actions/server/_oauth2_config.py';rows=[]
    for case in ('valid_structural_pair','second_acquisition_failure'):
        case_env=env.copy()
        if case=='second_acquisition_failure':case_env['CONTROLLED_OAUTH_SECOND_FAILURE']='1'
        previous=dest.read_bytes() if dest.exists() else None
        result=run([sys.executable,str(outer),str(package)],stage,case_env,owned/case,90)
        assert b'controlled private cause' not in result.stdout+result.stderr
        if case=='valid_structural_pair':
            assert result.returncode==0
            tree=ast.parse(dest.read_bytes())
            values=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign))
            assert set(values)=={'actions_config','default_user_config'}
            assert all('providers: {}' in value for value in values.values())
        else:
            assert result.returncode!=0 and b'(exit 17)' in result.stdout+result.stderr
            assert dest.read_bytes()==previous
        assert not list(dest.parent.glob('.oauth2-config-*.tmp'))
        rows.append({'case':case,'returncode':result.returncode,'module_sha256':sha(dest),'private_cause_withheld':True})
    identities=[json.loads(line) for line in (owned/'gateway-children.jsonl').read_text().splitlines()]
    assert len(identities)==4
    assert all(Path(row['helper_argv0']).parent.resolve()==(ROOT/'action_server/.venv/bin').resolve() for row in identities)
    # Retain independently observed Runtime Python/YAML origin, not executable realpath alone.
    probe_env={k:v for k,v in env.items() if k not in ('VIRTUAL_ENV','POETRY_ACTIVE','CONDA_PREFIX','CONDA_DEFAULT_ENV','PYTHONHOME','PYTHONPATH')}
    probe=run(['poetry','run','python','-c','import yaml,sys,json;print(json.dumps({"prefix":sys.prefix,"python":sys.executable,"yaml_origin":yaml.__file__}))'],package,probe_env,owned/'yaml-origin',30)
    assert probe.returncode==0
    origin=json.loads(probe.stdout)
    assert Path(origin['prefix']).resolve()==(ROOT/'action_server/.venv').resolve()
    assert Path(origin['yaml_origin']).resolve().is_relative_to((ROOT/'action_server/.venv').resolve())
    assert all(sha(package/row['relative'])==row['sha256'] for row in copied)
    write(owned/'controlled-gateway-receipt.json',json.dumps({'status':'PASS_SYNTHETIC_INVOKE_BOUNDARY_ONLY','unchanged_stage_source':copied,'cases':rows,'four_helper_identities':identities,'yaml_origin':origin,'outer_yaml_forbidden':True,'private_stage_only':True,'no_product_generated_config_write':True,'release_content':'UNQUALIFIED'},indent=2).encode())

if __name__=='__main__':
    main()
