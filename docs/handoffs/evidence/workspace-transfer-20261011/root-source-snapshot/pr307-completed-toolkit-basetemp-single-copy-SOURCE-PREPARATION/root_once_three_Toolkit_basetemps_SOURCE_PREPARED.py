"""SOURCE ONLY: one root-authorized preservation, separate before/alwayspost captures."""
import argparse,hashlib,json,os,signal,stat,subprocess,sys,time
from pathlib import Path

def bound(row):
    p=Path(row['path']);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    raw=p.read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'] and oct(stat.S_IMODE(s.st_mode))==row['mode']
    assert s.st_uid==os.getuid()==1000 and s.st_gid==os.getgid()==1000
    return raw

def seal(p,data):
    raw=(json.dumps(data,sort_keys=True)+'\n').encode();fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    fd=os.open(Path(p).parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def closure(cfg,auth,release_row):
    for row in (release_row,auth['parent_binding'],auth['driver_binding'],auth['config_binding'],auth['independent_review_binding'],cfg['cached_python']):bound(row)
    for row in cfg['protected_bindings']:bound(row)
    assert sys.dont_write_bytecode and not sys.flags.optimize
    assert not any(os.environ.get(k) for k in ('PYTHONOPTIMIZE','PYTEST_ADDOPTS','PYTHONPATH','PYTHONHOME'))
    assert Path(sys.executable).resolve()==Path(cfg['cached_python']['path']).resolve()
    for k,v in cfg['managed_activation_expected'].items():assert os.environ.get(k)==v
    assert os.environ['PATH'].split(':')[:2]==cfg['required_PATH_first_two']
    return {'status':'PASS_BOUND_PARENT_SOURCE_INPUTS_ONLY','protected_rows':len(cfg['protected_bindings'])}

def run(argv,root,stem,budget):
    data={'argv':argv,'status':'NOT_STARTED'};primary=None;started=time.monotonic();proc=None
    paths=[root/(stem+'.stdout.private'),root/(stem+'.stderr.private')]
    try:
        with paths[0].open('xb') as out,paths[1].open('xb') as err:
            os.chmod(paths[0],0o600);os.chmod(paths[1],0o600)
            proc=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True)
            data.update(status='RETURNED',returncode=proc.wait(timeout=budget-5))
    except BaseException as exc:
        primary=exc;data.update(status='FAIL',primary_exception_type=type(exc).__name__)
        if proc is not None and proc.poll() is None:
            try:os.killpg(proc.pid,signal.SIGKILL);data['owned_group_fallback_kill_sent']=True
            except ProcessLookupError:data['owned_group_fallback_kill_sent']=False
            try:data['owned_group_leader_reaped_returncode']=proc.wait(timeout=3)
            except BaseException as secondary:
                data['owned_group_leader_reap_secondary']=type(secondary).__name__
                if hasattr(exc,'add_note'):exc.add_note('Owned group fallback reap also failed: '+type(secondary).__name__)
        raise
    finally:
        data['elapsed_seconds']=time.monotonic()-started
        try:
            for p in paths:
                if p.exists():
                    fd=os.open(p,os.O_RDONLY)
                    try:os.fsync(fd)
                    finally:os.close(fd)
            seal(root/(stem+'.terminal.json'),data)
        except BaseException as secondary:
            if primary is None:raise
            if hasattr(primary,'add_note'):primary.add_note('Original capture retention also failed: '+type(secondary).__name__)
    return data

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root-release',required=True);ap.add_argument('--root-release-sha256',required=True);a=ap.parse_args()
    p=Path(a.root_release);s=p.lstat();row={'path':str(p),'bytes':s.st_size,'mode':'0o600','sha256':a.root_release_sha256};auth=json.loads(bound(row))
    ps=p.parent.lstat();assert not p.parent.is_symlink() and stat.S_IMODE(ps.st_mode)==0o700 and ps.st_uid==os.getuid() and ps.st_gid==os.getgid()
    assert auth['decision']=='RELEASE_ONE_THREE_COMPLETED_ORIGINAL_TOOLKIT_BASETEMP_PRESERVATION_ONLY'
    assert all(type(auth[k]) is int for k in ('child_seconds','outer_seconds','kill_grace_seconds')) and (auth['child_seconds'],auth['outer_seconds'],auth['kill_grace_seconds'])==(600,900,10)
    assert Path(auth['parent_binding']['path']).resolve()==Path(__file__).resolve()
    cfg=json.loads(bound(auth['config_binding']));review=json.loads(bound(auth['independent_review_binding']))
    assert review['decision']=='GO_EXACT_THREE_COMPLETED_TOOLKIT_BASETEMP_PRESERVATION_PREEXECUTION'
    for k in ('parent_binding','driver_binding','config_binding'):assert review[k]==auth[k]
    root=Path(cfg['outer_owned_root']);assert root.parent==Path('/workspace/engineering') and not root.exists() and not root.is_symlink();root.mkdir(mode=0o700)
    base=[cfg['cached_python']['path'],'-B','-u',auth['driver_binding']['path'],'--root-release',str(p),'--root-release-sha256',a.root_release_sha256]
    guard=['/usr/bin/timeout','--signal=TERM','--kill-after=10s','120s']+base+['--only-guard']
    child=['/usr/bin/timeout','--signal=TERM','--kill-after=10s','600s']+base
    terminal={'status':'NOT_STARTED'};primary=None
    try:
        terminal['before_closure']=closure(cfg,auth,row)
        terminal['before']=run(guard,root,'before',135);assert terminal['before']['returncode']==0
        terminal['original_child']=run(child,root,'original-preservation',625);assert terminal['original_child']['returncode']==0
        terminal['status']='PASS_COMPLETED_TOOLKIT_STORAGE_ONLY'
    except BaseException as exc:primary=exc;terminal.update(status='FAIL',primary_exception_type=type(exc).__name__);raise
    finally:
        try:
            terminal['alwayspost']=run(guard,root,'alwayspost',135);assert terminal['alwayspost']['returncode']==0
            terminal['post_closure']=closure(cfg,auth,row)
        except BaseException as secondary:
            terminal.update(status='FAIL',post_exception_type=type(secondary).__name__)
            if primary is None:primary=secondary
            elif hasattr(primary,'add_note'):primary.add_note('External postguard also failed: '+type(secondary).__name__)
        try:seal(root/'original-one-root-parent-terminal.json',terminal)
        except BaseException as secondary:
            if primary is None:primary=secondary
            elif hasattr(primary,'add_note'):primary.add_note('Outer terminal retention also failed: '+type(secondary).__name__)
        if primary is not None and sys.exc_info()[1] is None:raise primary

if __name__=='__main__':main()
