"""Prepared one-shot stdlib control parent; no import-time operation."""
import os,sys,stat,json,hashlib,subprocess,time,argparse,ast,unittest,pathlib,shutil
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


def managed_environment(cfg):
    bound(cfg['activation_binding']);bound(cfg['cached_python']);bound(cfg['git_binding'])
    assert len(cfg['managed_activation_expected'])==18
    for name,value in cfg['managed_activation_expected'].items():assert os.environ.get(name)==value,'MANAGED_ACTIVATION_INPUT_MISMATCH'
    assert os.environ.get('PATH','').split(os.pathsep)[:2]==cfg['required_PATH_first_two'],'ORDERED_MANAGED_PATH_MISMATCH'
    assert str(Path(sys.prefix).resolve())==cfg['cached_prefix']
    assert Path(sys.executable).resolve()==Path(cfg['cached_python']['path']).resolve()
    assert shutil.which('git')==cfg['git_binding']['path']
    git_info=Path(cfg['git_binding']['path']).lstat();assert git_info.st_uid==cfg['git_binding']['uid'] and git_info.st_gid==cfg['git_binding']['gid']
    modules={'unittest':unittest,'json':json,'pathlib':pathlib,'subprocess':subprocess,'os':os};origins=[]
    for name,module in modules.items():
        row=cfg['stdlib_origin_bindings'][name];p=bound(row)
        assert Path(module.__file__).resolve()==p.resolve() and p.resolve().is_relative_to(Path(cfg['cached_prefix']))
        origins.append({'module':name,'path':str(p),'sha256':row['sha256'],'spec_origin':str(module.__spec__.origin)})
    return {'managed_activation_fields':18,'ordered_PATH_binding':True,'actual_python':sys.executable,'actual_prefix':sys.prefix,'stdlib_module_origins':origins}


def guard(cfg,config_binding,self_binding):
    start=time.monotonic();bound(config_binding);bound(self_binding);bound(_ROOT_RELEASE_BINDING);bound(_ROOT_INDEPENDENT_BINDING);environment=managed_environment(cfg)
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
    return {'status':'PASS','packet_rows':len(cfg['bindings']),'source_rows':1440,'native_rows':1192,'elapsed':time.monotonic()-start,'environment':environment}

def seal(path,payload):
    assert not path.exists() and not path.is_symlink()
    with path.open('x') as f:
        os.chmod(path,0o600);json.dump(payload,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def main():
    global _ROOT_RELEASE_BINDING,_ROOT_INDEPENDENT_BINDING
    assert sys.dont_write_bytecode is True
    assert sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE') and not os.environ.get('PYTEST_ADDOPTS') and not os.environ.get('PYTHONHOME') and not os.environ.get('PYTHONPATH')
    ap=argparse.ArgumentParser();ap.add_argument('--root-execute-reviewed-pure-controls');ap.add_argument('--root-release-sha256');args=ap.parse_args()
    assert args.root_execute_reviewed_pure_controls and args.root_release_sha256
    auth_path=Path(args.root_execute_reviewed_pure_controls);s=auth_path.lstat();assert stat.S_ISREG(s.st_mode) and not auth_path.is_symlink()
    assert stat.S_IMODE(s.st_mode)==0o600 and s.st_uid==os.getuid() and s.st_gid==os.getgid() and digest(auth_path)==args.root_release_sha256
    parent=auth_path.parent;ps=parent.lstat();assert parent.is_dir() and not parent.is_symlink() and parent.resolve()==parent
    assert stat.S_IMODE(ps.st_mode)==0o700 and ps.st_uid==os.getuid() and ps.st_gid==os.getgid()
    _ROOT_RELEASE_BINDING={'path':str(auth_path),'bytes':s.st_size,'sha256':args.root_release_sha256,'mode':'0o600'}
    auth=json.loads(auth_path.read_bytes());_ROOT_INDEPENDENT_BINDING=auth['independent_review_binding'];assert auth['decision']=='RELEASE_ONE_FIRST_FIVE_V8_CURRENT9760_MEASURED_GIT_MANAGED_PURE18_ONLY'
    review=private_json(auth['independent_review_binding'],0o400)
    assert review['decision']=='GO_FIRST_FIVE_V8_CURRENT9760_MEASURED_GIT_MANAGED_PURE18_PREEXECUTION'
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
        argv=['/usr/bin/timeout','--signal=TERM','--kill-after=10s','120s',cfg['cached_python']['path'],'-u',cfg['controls']['path'],'--owned-machine-census',cfg['census_path']]
        terminal['argv']=argv;env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
        result=None;child_error=None
        with (root/'original.stdout.private').open('xb') as stdout,(root/'original.stderr.private').open('xb') as stderr:
            os.chmod(stdout.name,0o600);os.chmod(stderr.name,0o600)
            try:result=subprocess.run(argv,cwd=root,env=env,stdout=stdout,stderr=stderr,timeout=140)
            except BaseException as caught:child_error=caught
            finally:
                try:stdout.flush();stderr.flush();os.fsync(stdout.fileno());os.fsync(stderr.fileno())
                except BaseException as retention:
                    if child_error is None:child_error=retention
                    elif hasattr(child_error,'add_note'):child_error.add_note('Original stream retention also failed: '+type(retention).__name__)
        terminal['child_returncode']=None if result is None else result.returncode;terminal['tests']='ORIGINAL_CONTROL_ATTEMPT'
        terminal['child_exception_type']=None if child_error is None else type(child_error).__name__
        terminal['original_stdout']={'bytes':(root/'original.stdout.private').stat().st_size,'sha256':digest(root/'original.stdout.private')}
        terminal['original_stderr']={'bytes':(root/'original.stderr.private').stat().st_size,'sha256':digest(root/'original.stderr.private')}
        try:seal(root/'original-child-terminal.json',dict(terminal))
        except BaseException as retention:
            if child_error is None:child_error=retention
            elif hasattr(child_error,'add_note'):child_error.add_note('Original child terminal retention also failed: '+type(retention).__name__)
        if child_error is not None:raise child_error
        assert result is not None and result.returncode==0,'ORIGINAL_CONTROL_CHILD_NONZERO'
        census_path=Path(cfg['census_path']);cs=census_path.lstat()
        assert stat.S_ISREG(cs.st_mode) and not census_path.is_symlink() and stat.S_IMODE(cs.st_mode)==0o600
        assert cs.st_uid==os.getuid() and cs.st_gid==os.getgid()
        census=json.loads(census_path.read_bytes());rows=census['outcomes'];expected=set(cfg['expected_nodeids'])
        assert census['schema']=='ORIGINAL_UNITTEST_18_COMPLETE_MACHINE_CENSUS_V1'
        assert census['status']=='PASS_PURE_CONTROLS_ONLY' and census['tests_run']==18 and census['failure_count']==census['error_count']==census['skip_count']==0
        assert len(rows)==len({r['nodeid'] for r in rows})==18 and {r['nodeid'] for r in rows}==expected
        assert set(census['selected_nodeids'])==expected and len(census['selected_nodeids'])==18 and all(r['status']=='PASSED' for r in rows)
        assert census['actual_prefix']==cfg['cached_prefix'] and Path(census['actual_python']).resolve()==Path(cfg['cached_python']['path']).resolve()
        assert census['stdlib_origins_before']==census['stdlib_origins_after']
        for row in census['stdlib_origins_before']:
            wanted=cfg['stdlib_origin_bindings'][row['module']];assert row['path']==wanted['path'] and row['sha256']==wanted['sha256']
        assert len(census['stdlib_origins_before'])==len({r['module'] for r in census['stdlib_origins_before']})==5
        driver=census['verified_driver_origin'];assert driver['status']=='VERIFIED_BUFFER_SOURCE_MODULE' and driver['path']==cfg['preservation_driver']['path'] and driver['sha256']==cfg['preservation_driver']['sha256']
        terminal['complete_original_18_machine_census']={'path':str(census_path),'bytes':cs.st_size,'sha256':digest(census_path),'passed':18,'failed':0,'error':0,'skip':0}
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
