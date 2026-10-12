"""Prepared one-shot stdlib control parent; no import-time operation."""
import os,sys,stat,json,hashlib,subprocess,time,argparse,ast
from pathlib import Path

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def bound(row):
    p=Path(row['path']);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    assert s.st_size==row['bytes'] and oct(stat.S_IMODE(s.st_mode))==row['mode'] and digest(p)==row['sha256']
    return p

def private_json(row,mode):
    p=bound(row);s=p.stat();assert stat.S_IMODE(s.st_mode)==mode and s.st_uid==os.getuid() and s.st_gid==os.getgid()
    return json.loads(p.read_bytes())

def guard(cfg,config_binding,self_binding):
    start=time.monotonic();bound(config_binding);bound(self_binding)
    for row in cfg['bindings']:bound(row);assert time.monotonic()-start<30,'BEFORE_POST_GUARD_BUDGET'
    bound(cfg['cached_python']);bound(cfg['preservation_driver']);bound(cfg['frozen_environment_config']);bound(cfg['controls'])
    for source in cfg['active_source_bindings']:
        p=source['path']
        assert subprocess.check_output(['git','-C',p,'rev-parse','HEAD'],timeout=5).decode().strip()==source['head']
        assert subprocess.check_output(['git','-C',p,'rev-parse','HEAD^{tree}'],timeout=5).decode().strip()==source['tree']
        assert not subprocess.check_output(['git','-C',p,'status','--porcelain','--untracked-files=no'],timeout=5)
    v9=json.loads(bound(cfg['current_v9_config_binding']).read_bytes())
    assert len(v9['source_body_modes'])==cfg['source_guard_count']==1440
    assert len(v9['native_original_members'])==cfg['native_guard_count']==1192
    for row in v9['source_body_modes']:
        p=Path(v9['source_root'])/row['path'];s=p.lstat();assert stat.S_IMODE(s.st_mode)==row['fs_mode']
        assert stat.S_ISREG(s.st_mode) and digest(p)==row['sha256'];assert time.monotonic()-start<30,'BEFORE_POST_GUARD_BUDGET'
    for row in v9['native_original_members']:
        p=Path(v9['native_original_root'])/row['path'];s=p.lstat();assert stat.S_IMODE(s.st_mode)==row['mode']
        if row['kind']=='file':assert stat.S_ISREG(s.st_mode) and digest(p)==row['content_sha256']
        elif row['kind']=='directory':assert stat.S_ISDIR(s.st_mode)
        elif row['kind']=='symlink':assert stat.S_ISLNK(s.st_mode) and os.readlink(p)==row['link_target']
        else:raise AssertionError('UNKNOWN_NATIVE_INPUT_KIND')
        assert time.monotonic()-start<30,'BEFORE_POST_GUARD_BUDGET'
    # Prove actual copied control constants consume the announced files; do not rely on inverse AST alone.
    tree=ast.parse(bound(cfg['controls']).read_bytes());constants={}
    for n in tree.body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            if isinstance(n.value,ast.Constant):constants[n.targets[0].id]=n.value.value
            elif isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='Path' and len(n.value.args)==1 and isinstance(n.value.args[0],ast.Constant):constants[n.targets[0].id]=n.value.args[0].value
    assert constants['DRIVER_PATH']==cfg['preservation_driver']['path'] and constants['DRIVER_SHA']==cfg['preservation_driver']['sha256']
    assert constants['FIXTURE']==cfg['fixture_root']
    paths=[n.args[0].value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='Path' and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str)]
    assert cfg['frozen_environment_config']['path'] in paths
    return {'status':'PASS','packet_rows':len(cfg['bindings']),'source_rows':1440,'native_rows':1192,'elapsed':time.monotonic()-start}

def seal(path,payload):
    assert not path.exists() and not path.is_symlink()
    with path.open('x') as f:
        os.chmod(path,0o600);json.dump(payload,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def main():
    assert sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE') and not os.environ.get('PYTEST_ADDOPTS')
    ap=argparse.ArgumentParser();ap.add_argument('--root-execute-reviewed-pure-controls');ap.add_argument('--root-release-sha256');args=ap.parse_args()
    assert args.root_execute_reviewed_pure_controls and args.root_release_sha256
    auth_path=Path(args.root_execute_reviewed_pure_controls);s=auth_path.lstat();assert stat.S_ISREG(s.st_mode) and not auth_path.is_symlink()
    assert stat.S_IMODE(s.st_mode)==0o600 and s.st_uid==os.getuid() and s.st_gid==os.getgid() and digest(auth_path)==args.root_release_sha256
    auth=json.loads(auth_path.read_bytes());assert auth['decision']=='RELEASE_ONE_FIRST_FIVE_ENVIRONMENT_MODE_CLOSURE_PURE_CONTROLS_ONLY'
    review=private_json(auth['independent_review_binding'],0o400)
    assert review['decision']=='GO_FIRST_FIVE_ENVIRONMENT_MODE_CLOSURE_PURE_CONTROLS_PREEXECUTION'
    assert review['launcher_binding']==auth['launcher_binding'] and review['config_binding']==auth['config_binding']
    assert Path(auth['launcher_binding']['path']).resolve()==Path(__file__).resolve()
    cfg=private_json(auth['config_binding'],0o400)
    root=Path(cfg['owned_root']);fixture=Path(cfg['fixture_root'])
    assert root.parent==Path('/workspace/engineering') and not root.exists() and not root.is_symlink()
    assert not fixture.exists() and not fixture.is_symlink()
    root.mkdir(mode=0o700)
    terminal={'status':'NOT_STARTED','tests':'NOT_RUN'};primary=None
    try:
        terminal['before']=guard(cfg,auth['config_binding'],auth['launcher_binding'])
        argv=['/usr/bin/timeout','--signal=TERM','--kill-after=10s','120s',cfg['cached_python']['path'],'-u',cfg['controls']['path']]
        terminal['argv']=argv;env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
        with (root/'original.stdout.private').open('xb') as stdout,(root/'original.stderr.private').open('xb') as stderr:
            os.chmod(stdout.name,0o600);os.chmod(stderr.name,0o600)
            result=subprocess.run(argv,cwd=root,env=env,stdout=stdout,stderr=stderr,timeout=140)
            stdout.flush();stderr.flush();os.fsync(stdout.fileno());os.fsync(stderr.fileno())
        terminal['child_returncode']=result.returncode;terminal['tests']='ORIGINAL_CONTROL_ATTEMPT'
        seal(root/'original-child-terminal.json',dict(terminal))
        assert result.returncode==0,'ORIGINAL_CONTROL_CHILD_NONZERO'
        terminal['status']='PASS_PURE_CONTROLS_ONLY'
    except BaseException as exc:
        primary=exc;terminal['status']='FAIL';terminal['primary_exception_type']=type(exc).__name__;raise
    finally:
        try:terminal['post']=guard(cfg,auth['config_binding'],auth['launcher_binding'])
        except BaseException as secondary:
            terminal['post']={'status':'FAIL','exception_type':type(secondary).__name__};terminal['status']='FAIL'
            if primary is None:primary=secondary
            elif hasattr(primary,'add_note'):primary.add_note('Owned postguard also failed: '+type(secondary).__name__)
        try:seal(root/'original-parent-terminal.json',terminal)
        except BaseException as secondary:
            if primary is None:primary=secondary
            elif hasattr(primary,'add_note'):primary.add_note('Owned terminal retention also failed: '+type(secondary).__name__)
        if primary is not None and sys.exc_info()[1] is None:raise primary

if __name__=='__main__':main()
