"""Strict named pure caller admission; stdlib only, never starts a gate itself."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

SOURCE='8d49d0865ad5ad27b2d4e325ec135212080625e8'
TREE='a80600809d373038ca76e445ba0b7b79bb7eeaa6'
BASE=Path('/workspace/engineering/rcc-stop-attempt-concrete-ROOT-caller-PREEXEC-NOTRUN')
CONFIG=BASE/'FROZEN-stop-attempt-concrete-ROOT-config-NOTRUN.json'
RELEASE=Path('/workspace/engineering/root-one-current8d49-stop-attempt-pure-source-controls-release.json')
CACHED='/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'

def need(ok,code):
    if not ok:raise ValueError(code)

def binding(path):
    p=Path(path);s=p.lstat();need(stat.S_ISREG(s.st_mode) and not p.is_symlink(),'STOP_CALLER_REGULAR_FILE')
    raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mode=oct(stat.S_IMODE(s.st_mode)))

def read_bound(row):
    need(type(row) is dict and set(row)=={'path','bytes','sha256','mode'} and binding(row['path'])==row,'STOP_CALLER_BOUND_IDENTITY')
    return Path(row['path']).read_bytes()

def physical(path,mode):
    p=Path(path);s=p.lstat()
    need(stat.S_ISREG(s.st_mode) and not p.is_symlink() and stat.S_IMODE(s.st_mode)==mode
         and s.st_uid==os.getuid()==1000 and s.st_gid==os.getgid()==1000,'STOP_CALLER_OPERATOR_PHYSICAL')

def directory(path):
    p=Path(path);s=p.lstat()
    need(stat.S_ISDIR(s.st_mode) and not p.is_symlink() and stat.S_IMODE(s.st_mode)==0o700
         and s.st_uid==os.getuid()==1000 and s.st_gid==os.getgid()==1000,'STOP_CALLER_DIRECTORY_PHYSICAL')

def durable(path,value,mode=0o600):
    raw=value if type(value) is bytes else (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:
        f.write(raw);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),mode);os.fsync(f.fileno())
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def admit(args,role):
    need(role in ('external_parent','inner_caller'),'STOP_CALLER_KNOWN_ROLE')
    need(Path(args.release)==RELEASE,'STOP_CALLER_FIXED_RELEASE_PATH')
    physical(CONFIG,0o400);physical(RELEASE,0o600)
    need(binding(CONFIG)['sha256']==args.caller_config_sha256,'STOP_CALLER_CONFIG_SHA')
    cfg=json.loads(CONFIG.read_bytes());rb=binding(RELEASE)
    need(rb['sha256']==args.release_sha256,'STOP_CALLER_RELEASE_SHA')
    release=json.loads(read_bound(rb))
    for row in cfg['frozen_bindings']:read_bound(row)
    for row in cfg['implementation_bindings'].values():physical(row['path'],0o400);read_bound(row)
    need(Path(__file__).resolve()==Path(cfg['implementation_bindings']['caller_contract']['path']).resolve(),'STOP_CALLER_CONTRACT_ACTUAL_PATH')
    need(Path(sys.argv[0]).resolve()==Path(cfg['implementation_bindings'][role]['path']).resolve(),'STOP_CALLER_SELF_ROLE_PATH')
    need(Path(sys.executable).resolve()==Path(CACHED).resolve(),'STOP_CALLER_MANAGED_CACHED_INTERPRETER')
    need(cfg['source']==SOURCE and cfg['tree']==TREE and cfg['source_count']==1440,'STOP_CALLER_CURRENT_SOURCE')
    expected=dict(cfg['ROOT_release_template'])
    need(expected.pop('independent_PREEXEC') is None,'STOP_CALLER_UNGRANTED_TEMPLATE')
    need(expected['caller_config_sha256']=='ROOT_CALLER_CONFIG_SHA256','STOP_CALLER_CONFIG_TOKEN_TEMPLATE')
    expected['caller_config_sha256']=args.caller_config_sha256
    need(set(release)==set(expected)|{'independent_PREEXEC'},'STOP_CALLER_RELEASE_KEYS')
    for key,value in expected.items():
        need(type(release[key]) is type(value) and release[key]==value,'STOP_CALLER_TYPED_ROOT_RELEASE')
    physical(release['independent_PREEXEC']['path'],0o400)
    review=json.loads(read_bound(release['independent_PREEXEC']))
    required={'schema':1,'status':'INDEPENDENT_STOP_ATTEMPT_COMPOSITION_PURE_PREEXECUTION_GO',
              'source':SOURCE,'tree':TREE,'config_sha256':cfg['phase_config']['sha256'],
              'helper_sha256':cfg['phase_helper']['sha256'],'caller_config_sha256':args.caller_config_sha256,
              'external_parent_sha256':cfg['implementation_bindings']['external_parent']['sha256'],
              'inner_caller_sha256':cfg['implementation_bindings']['inner_caller']['sha256'],
              'caller_contract_sha256':cfg['implementation_bindings']['caller_contract']['sha256'],
              'source_independent_sha256':cfg['source_independent']['sha256'],
              'guard_only_authorization':cfg['guard_only_authorization']}
    for key,value in required.items():
        need(type(review.get(key)) is type(value) and review[key]==value,'STOP_CALLER_REAL_CONCRETE_REVIEW_SCOPE')
    source_review=json.loads(read_bound(cfg['source_independent']))
    need(source_review.get('status')=='INDEPENDENT_NATIVE_MEMORY_COMPOSITION_STOP_ATTEMPT_SOURCE_PREPARED_GO_NOT_EXECUTED'
         and source_review.get('source')==SOURCE and source_review.get('tree')==TREE,'STOP_CALLER_REAL_SOURCE_GO')
    need('PYTEST_ADDOPTS' not in os.environ and 'PYTHONOPTIMIZE' not in os.environ and not sys.flags.optimize
         and all(k not in os.environ for k in cfg['forbidden_operator_exports']),'STOP_CALLER_NO_INHERITED_OPERATOR_OVERRIDE')
    need(len(cfg['activation'])==18 and all(os.environ.get(k)==v for k,v in cfg['activation'].items()),'STOP_CALLER_MANAGED_ACTIVATION18')
    need(os.environ['PATH'].split(os.pathsep)[:2]==cfg['path_prefix2'],'STOP_CALLER_MANAGED_PATH2')
    pin=cfg['managed_rcc'];p=Path(pin['path']);s=p.lstat()
    need(pin['path']=='/workspace/actions-cloud/bin/rcc' and stat.S_ISREG(s.st_mode) and not p.is_symlink()
         and stat.S_IMODE(s.st_mode)==pin['mode']==0o700 and s.st_uid==pin['uid']==1000
         and s.st_gid==pin['gid']==1000 and s.st_size==pin['bytes']==22282402
         and hashlib.sha256(p.read_bytes()).hexdigest()==pin['sha256'],'STOP_CALLER_PRIMARY700_HASH_NO_RCC_EXECUTION')
    return cfg,rb

def capture(root,name,argv,parent_seconds,*,primary_deadline=None):
    argv=list(argv)
    if primary_deadline is not None:
        remaining=primary_deadline-time.monotonic()
        # Reserve the existing10s kill grace+5s fallback margin inside the
        # shared primary window. No phase starts without that reserve.
        need(remaining>15,'STOP_CALLER_PRIMARY_DEADLINE_EXHAUSTED_NO_ADVANCE')
        need(argv.count('120s')==1,'STOP_CALLER_ONLY_NOMINAL_TIMEOUT_TOKEN')
        term_seconds=min(120,remaining-15)
        argv[argv.index('120s')]=f'{term_seconds:.6f}s'
        parent_seconds=min(parent_seconds,remaining)
    else:term_seconds=120 if '120s' in argv else 900
    out=root/name;out.mkdir(mode=0o700,exist_ok=False);directory(out)
    with (out/'original.stdout.private').open('xb') as stdout,(out/'original.stderr.private').open('xb') as stderr:
        try:
            if primary_deadline is not None:
                parent_seconds=min(parent_seconds,primary_deadline-time.monotonic())
                need(parent_seconds>0,'STOP_CALLER_PRIMARY_DEADLINE_EXHAUSTED_NO_LAUNCH')
            result=subprocess.run(argv,cwd=root,stdout=stdout,stderr=stderr,timeout=parent_seconds,check=False)
            observed={'returncode':result.returncode}
        except BaseException as error:
            observed={'exception_class':type(error).__name__}
        stdout.flush();os.fsync(stdout.fileno());stderr.flush();os.fsync(stderr.fileno())
    observed.update(argv=argv,parent_seconds=parent_seconds,TERM_seconds=term_seconds,shared_primary_deadline=primary_deadline,
                    stdout_binding=binding(out/'original.stdout.private'),stderr_binding=binding(out/'original.stderr.private'))
    durable(out/'original-terminal.json',observed)
    return observed

def guard_argv(cfg):
    # Fixed guard phase only. Old consumed release is historical identity;
    # the new distinct ROOT release separately authorizes this exact reuse.
    auth=cfg['guard_only_authorization']
    need(auth['permitted_phase']=='guard' and auth['rerun35_or_native'] is False,'STOP_CALLER_GUARD_ONLY_SCOPE')
    return list(auth['exact_argv'])

def phase_argv(cfg,release_sha,name):
    need(name in cfg['phase_order'],'STOP_CALLER_LITERAL_PHASE')
    command=list(cfg['phase_commands'][name]);need(command.count('ROOT_REAL_DISTINCT_RELEASE_SHA256')==1,'STOP_CALLER_RELEASE_PLACEHOLDER')
    return [release_sha if x=='ROOT_REAL_DISTINCT_RELEASE_SHA256' else x for x in command]

def census(cfg,name):
    expected=cfg['phase_expectations'][name];p=Path(expected['output'])/'original-node-census.json';physical(p,0o600)
    raw=json.loads(p.read_bytes())
    for k,v in {'schema':1,'status':'EXPECTED_SOURCE_PHASE_ADMITTED','phase':name,'source':SOURCE,'tree':TREE,
                'native':'NOT_RUN','real_cgroup_signals':'NOT_RUN','counts':expected['expected_counts'],'expected_ids':expected['expected_ids']}.items():
        need(type(raw.get(k)) is type(v) and raw[k]==v,'STOP_CALLER_ORIGINAL_PHASE_CENSUS')
    if expected['kind']=='RED':
        need(raw['success_ids']==[] and len(raw['semantic'])==1,'STOP_CALLER_KNOWN_RED_CENSUS')
        value=raw['semantic'][0];pred=expected['predicate']
        need(value['test']==expected['expected_ids'][0] and value['exception_class']=='AssertionError'
             and {'function':pred['function'],'line':pred['line']} in value['control_frames'],'STOP_CALLER_KNOWN_RED_SOURCE_FRAME')
    else:
        need(raw['success_ids']==expected['expected_ids'] and raw['semantic']==[],'STOP_CALLER_TRUE_GREEN_CENSUS')
    return binding(p)
