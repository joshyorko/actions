"""Distinct root-released pure17 only; never calls version/native/artifact main."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

CACHED='/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'
SOURCE='8d49d0865ad5ad27b2d4e325ec135212080625e8'
TREE='a80600809d373038ca76e445ba0b7b79bb7eeaa6'
BASE=Path('/workspace/engineering/rcc-memory17-pure-controls-concrete-preexecution-NOTRUN')
V9=Path('/workspace/engineering/rcc-current8d49-qualified-V9-entry-bootstrap-preparation')
ROOT=Path('/workspace/engineering/root-one-memory17-pure-controls-20261011-1')

def require(ok, category):
    if not ok: raise ValueError(category)

def digest(raw): return hashlib.sha256(raw).hexdigest()

def read_bound(row):
    p=Path(row['path']);require(p.is_file() and not p.is_symlink(),'MEMORY17_BOUND_FILE')
    raw=p.read_bytes();metadata=p.stat()
    require(len(raw)==row['bytes'] and digest(raw)==row['sha256']
            and stat.S_IMODE(metadata.st_mode)==int(row['mode'],8),'MEMORY17_BOUND_IDENTITY')
    return raw

def fsync_write(path, raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    descriptor=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)

def parse_arguments():
    parser=argparse.ArgumentParser()
    for k in ('config','config-sha256','release','release-sha256','phase'):parser.add_argument('--'+k,required=True)
    args=parser.parse_args();require(args.phase in ('launch','guard'),'MEMORY17_PHASE')
    raw=Path(args.config).read_bytes();require(digest(raw)==args.config_sha256,'MEMORY17_CONFIG_HASH')
    cfg=json.loads(raw);raw_release=Path(args.release).read_bytes()
    require(digest(raw_release)==args.release_sha256,'MEMORY17_ROOT_RELEASE_HASH')
    release=json.loads(raw_release)
    expected={'schema':1,'status':'ROOT_RELEASE_ONE_MEMORY17_PURE_CONTROLS','config_sha256':args.config_sha256,
              'launcher_sha256':cfg['launcher']['sha256'],'source':SOURCE,'tree':TREE,
              'root':str(ROOT),'serialized_no_other_heavy_or_storage_mutations':True}
    require(set(release)==set(expected)|{'independent_review'},'MEMORY17_RELEASE_KEYS')
    require(all(type(release[k]) is type(v) and release[k]==v for k,v in expected.items()),'MEMORY17_ROOT_RELEASE_SCOPE')
    review=json.loads(read_bound(release['independent_review']))
    for key,value in {'schema':1,'status':'INDEPENDENT_MEMORY17_PURE_PREEXECUTION_GO',
                       'source':SOURCE,'tree':TREE,'config_sha256':args.config_sha256,
                       'launcher_sha256':cfg['launcher']['sha256']}.items():
        require(type(review.get(key)) is type(value) and review[key]==value,'MEMORY17_INDEPENDENT_REVIEW_SCOPE')
    require(Path(__file__).resolve()==Path(cfg['launcher']['path']) and
            digest(Path(__file__).read_bytes())==cfg['launcher']['sha256'],'MEMORY17_SELF_IDENTITY')
    require(Path(sys.executable).resolve()==Path(CACHED).resolve(),'MEMORY17_CACHED_INTERPRETER')
    for row in cfg['frozen_bindings']:read_bound(row)
    return args,cfg

def activation(cfg):
    require(len(cfg['activation'])==18 and all(os.environ.get(k)==v for k,v in cfg['activation'].items()),'MEMORY17_ACTIVATION18')
    require(os.environ['PATH'].split(os.pathsep)[:2]==cfg['path_prefix2'],'MEMORY17_PATH2')
    require('PYTEST_ADDOPTS' not in os.environ and not os.environ.get('PYTHONOPTIMIZE')
            and not sys.flags.optimize,'MEMORY17_NO_INHERITED_PYTEST_OR_OPTIMIZE')
    require(all(k not in os.environ for k in cfg['forbidden_operator_exports']),'MEMORY17_NO_OPERATOR_OVERRIDE')
    rcc=Path(cfg['managed_rcc']['path']);require(digest(rcc.read_bytes())==cfg['managed_rcc']['sha256']
         and stat.S_IMODE(rcc.stat().st_mode)==0o711,'MEMORY17_PRIMARY_RCC_PIN_NO_EXECUTION')

def guard(cfg):
    # This existing function is strictly identity-only; main/version/Artifact never invoked.
    sys.path.insert(0,str(V9))
    import readonly_current_input_guard_v9
    oldcfg=json.loads(read_bound(cfg['source_guard_config']))
    readonly_current_input_guard_v9.guard(oldcfg)
    for row in oldcfg['concrete_own_origins']:
        code="import importlib,json,sys,pathlib; m=importlib.import_module(sys.argv[1]); assert pathlib.Path(sys.prefix).resolve()==pathlib.Path(sys.argv[2]).resolve(); assert pathlib.Path(m.__file__).resolve()==pathlib.Path(sys.argv[3]).resolve(); print('OWN_PREFIX_ORIGIN_PASS')"
        result=subprocess.run([row['python'],'-c',code,row['module'],row['prefix'],row['origin']],capture_output=True,timeout=10)
        require(result.returncode==0 and result.stdout==b'OWN_PREFIX_ORIGIN_PASS\n','MEMORY17_OWN_FIVE_ORIGINS')
    print('MEMORY17_CURRENT1440_PREPARED30_OWN5_V9_ORIGINALS_PASS')

def run():
    args,cfg=parse_arguments();activation(cfg)
    if args.phase=='guard':guard(cfg);return 0
    require(not ROOT.exists() and not ROOT.is_symlink(),'MEMORY17_ONCE_ROOT_ABSENT')
    os.umask(0o077);ROOT.mkdir(mode=0o700)
    forwarded=[]
    for k in ('config','config_sha256','release','release_sha256'):
        forwarded += ['--'+k.replace('_','-'),getattr(args,k)]
    guardcmd=['timeout','--signal=TERM','--kill-after=10s','120s',CACHED,str(Path(__file__)),'--phase','guard',*forwarded]
    outcomes={'status':'FAIL_OR_HOLD','scope':'PURE17_NO_NATIVE_NO_MEMORY_SAMPLER_ADOPTION'}
    try:
        before=subprocess.run(guardcmd,cwd=ROOT,capture_output=True)
        outcomes['before_returncode']=before.returncode
        fsync_write(ROOT/'before.stdout',before.stdout);fsync_write(ROOT/'before.stderr',before.stderr)
        if before.returncode==0:
            for key in ('basetemp','logger','junit'):
                p=Path(cfg[key]);require(p.parent==ROOT and not p.exists() and not p.is_symlink(),'MEMORY17_ABSENT_OUTPUT')
            primary=subprocess.run(cfg['pytest_argv'],cwd=ROOT,capture_output=True)
            outcomes['primary_returncode']=primary.returncode
            fsync_write(ROOT/'primary.stdout',primary.stdout);fsync_write(ROOT/'primary.stderr',primary.stderr)
            fsync_write(ROOT/'primary-returncode.json',(json.dumps({'returncode':primary.returncode})+'\n').encode())
        else:outcomes['primary']='NOTRUN_BEFORE_FAILED'
    except Exception as error:
        outcomes['primary_exception_class']=type(error).__name__
        fsync_write(ROOT/'primary-exception.private.txt',str(error).encode())
    finally:
        try:
            after=subprocess.run(guardcmd,cwd=ROOT,capture_output=True)
            outcomes['post_returncode']=after.returncode
            fsync_write(ROOT/'post.stdout',after.stdout);fsync_write(ROOT/'post.stderr',after.stderr)
        except Exception as error:outcomes['post_exception_class']=type(error).__name__
        if outcomes.get('before_returncode')==outcomes.get('primary_returncode')==outcomes.get('post_returncode')==0:
            outcomes['status']='PURE_TEST_PROCESS_PASS_PENDING_ORIGINAL_JUNIT_CENSUS'
        fsync_write(ROOT/'original-terminal.json',(json.dumps(outcomes,indent=2)+'\n').encode())
    return 0 if outcomes['status']=='PURE_TEST_PROCESS_PASS_PENDING_ORIGINAL_JUNIT_CENSUS' else 1

if __name__=='__main__':raise SystemExit(run())
