"""Concrete ROOT-released fake descriptor35 only; no native/profile adoption."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import re
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
BASE = Path('/workspace/engineering/rcc-defaultbackend35-concrete-PREEXEC-NOTRUN')
CONFIG = BASE / 'FROZEN-defaultbackend35-concrete-config-NOTRUN.json'
RELEASE = Path('/workspace/engineering/root-one-defaultbackend35-pure-controls-release.json')
CACHED = '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'


def need(ok, code):
    if not ok:
        raise ValueError(code)


def binding(path):
    path = Path(path); st = path.lstat()
    need(stat.S_ISREG(st.st_mode) and not path.is_symlink(), 'DEFAULTBACKEND35_BOUND_REGULAR')
    body = path.read_bytes()
    return {'path': str(path), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
            'mode': oct(stat.S_IMODE(st.st_mode))}


def read_bound(row):
    need(binding(row['path']) == row, 'DEFAULTBACKEND35_BOUND_IDENTITY')
    return Path(row['path']).read_bytes()


def physical(path, mode):
    p = Path(path); st = p.lstat()
    need(stat.S_ISREG(st.st_mode) and not p.is_symlink() and stat.S_IMODE(st.st_mode) == mode
         and st.st_uid == os.getuid() == 1000 and st.st_gid == os.getgid() == 1000,
         'DEFAULTBACKEND35_OPERATOR_PHYSICAL_IDENTITY')


def durable(path, value, mode=0o600):
    raw = value if type(value) is bytes else (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.fchmod(stream.fileno(), mode); os.fsync(stream.fileno())
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def parse_arguments():
    p = argparse.ArgumentParser()
    for name in ('config','config-sha256','release','release-sha256','phase'):
        p.add_argument('--'+name, required=True)
    a = p.parse_args()
    need(Path(a.config) == CONFIG and Path(a.release) == RELEASE and a.phase in ('launch','guard'), 'DEFAULTBACKEND35_FIXED_PATH_PHASE')
    return a


def admission(a, *, primary=False):
    physical(CONFIG,0o400); physical(RELEASE,0o600)
    cfg_binding=binding(CONFIG); need(cfg_binding['sha256']==a.config_sha256,'DEFAULTBACKEND35_CONFIG_SHA')
    cfg=json.loads(read_bound(cfg_binding)); release_binding=binding(RELEASE)
    need(release_binding['sha256']==a.release_sha256,'DEFAULTBACKEND35_RELEASE_SHA')
    release=json.loads(read_bound(release_binding))
    for row in cfg['frozen_bindings']:
        read_bound(row)
    for row in (cfg['launcher'],):
        physical(row['path'],0o400); read_bound(row)
    expected={'schema':1,'status':'ROOT_DISTINCT_ONE_DEFAULT_DESCRIPTOR35_PURE_CONTROLS',
              'source':cfg['source'],'tree':cfg['tree'],'config_binding':cfg_binding,
              'launcher_binding':cfg['launcher'],
              'source_owner_binding':cfg['source_owner'],'source_independent_review':cfg['source_independent_review'],
              'root':cfg['root_once'],'serialized_no_other_heavy_or_storage_mutations':True}
    need(set(release)==set(expected)|{'independent_preexecution_review'},'DEFAULTBACKEND35_RELEASE_KEYS')
    for key,value in expected.items():
        need(type(release[key]) is type(value) and release[key]==value,'DEFAULTBACKEND35_RELEASE_SCOPE')
    source_review=json.loads(read_bound(cfg['source_independent_review']))
    for key,value in cfg['required_source_review_fields'].items():
        need(value is not None and type(source_review.get(key)) is type(value) and source_review[key]==value,'DEFAULTBACKEND35_INDEPENDENT_SOURCE_SCOPE')
    review=json.loads(read_bound(release['independent_preexecution_review']))
    for key,value in {'schema':1,'status':'INDEPENDENT_DEFAULTBACKEND35_CONCRETE_PREEXECUTION_GO',
                      'source':cfg['source'],'tree':cfg['tree'],'config_sha256':a.config_sha256,
                      'launcher_sha256':cfg['launcher']['sha256'],'controls_sha256':cfg['controls']['sha256']}.items():
        need(type(review.get(key)) is type(value) and review[key]==value,'DEFAULTBACKEND35_INDEPENDENT_PREEXECUTION_SCOPE')
    pin=cfg['managed_rcc']; st=Path(pin['path']).lstat()
    need(pin['path']=='/workspace/actions-cloud/bin/rcc' and stat.S_ISREG(st.st_mode) and not Path(pin['path']).is_symlink()
         and stat.S_IMODE(st.st_mode)==pin['mode']==0o700 and st.st_uid==pin['uid']==os.getuid()==1000
         and st.st_gid==pin['gid']==os.getgid()==1000 and st.st_size==pin['bytes']==22282402
         and hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest()==pin['sha256'],'DEFAULTBACKEND35_MANAGED_PRIMARY700_NO_EXECUTION')
    need(not sys.flags.optimize and 'PYTHONOPTIMIZE' not in os.environ and 'PYTEST_ADDOPTS' not in os.environ
         and 'RCC_RELOAD_PRIVATE_MUTANT' not in os.environ,'DEFAULTBACKEND35_NO_INHERITED_OVERRIDE')
    need(len(cfg['activation'])==18 and all(os.environ.get(k)==v for k,v in cfg['activation'].items()),'DEFAULTBACKEND35_MANAGED_ACTIVATION18')
    need(os.environ['PATH'].split(os.pathsep)[:2]==cfg['path_prefix2'] and all(k not in os.environ for k in cfg['forbidden_operator_exports']),'DEFAULTBACKEND35_PATH2_OPERATOR_ENV')
    need(Path(sys.argv[0]).resolve()==Path(cfg['launcher']['path']).resolve(),'DEFAULTBACKEND35_LAUNCHER_ACTUAL_PATH')
    need(Path(sys.executable).resolve()==Path(CACHED).resolve(),'DEFAULTBACKEND35_CACHED_PARENT_INTERPRETER')
    return cfg,release_binding


def guard(cfg):
    # Existing identity-only function: no version/native/main, same own-five probes.
    old=json.loads(read_bound(cfg['source_guard_config']))
    sys.path.insert(0,cfg['old_V9_module_root'])
    import readonly_current_input_guard_v9
    readonly_current_input_guard_v9.guard(old)
    for row in old['concrete_own_origins']:
        code="import importlib,pathlib,sys; m=importlib.import_module(sys.argv[1]); assert pathlib.Path(sys.prefix).resolve()==pathlib.Path(sys.argv[2]).resolve(); assert pathlib.Path(m.__file__).resolve()==pathlib.Path(sys.argv[3]).resolve(); print('OWN_PREFIX_ORIGIN_PASS')"
        result=subprocess.run([row['python'],'-c',code,row['module'],row['prefix'],row['origin']],capture_output=True,timeout=10,check=False)
        need(result.returncode==0 and result.stdout==b'OWN_PREFIX_ORIGIN_PASS\n','DEFAULTBACKEND35_OWN_FIVE_ORIGINS')
    print('DEFAULTBACKEND35_CURRENT1440_PREPARED30_OWN5_OLD_INPUTS_PASS')



def admit_census(cfg, root):
    junit=Path(cfg['junit']);physical(junit,0o600)
    xml=ET.fromstring(junit.read_bytes())
    need(xml.tag=='testsuites' and len(xml)==1 and xml[0].tag=='testsuite','DEFAULTBACKEND35_JUNIT_ENVELOPE')
    suite=xml[0]
    need(all(suite.get(k)==v for k,v in {'tests':'35','failures':'0','errors':'0','skipped':'0'}.items()),'DEFAULTBACKEND35_JUNIT_COUNTS')
    cases=list(suite.findall('testcase')); names=[c.get('name') for c in cases]
    need(len(cases)==len(set(names))==35 and sorted(names)==sorted(cfg['expected_case_names']),'DEFAULTBACKEND35_EXACT_PARAMETER_CASES')
    need(all(not c.findall('failure') and not c.findall('error') and not c.findall('skipped') and c.get('classname')==Path(cfg['controls']['path']).stem for c in cases),'DEFAULTBACKEND35_JUNIT_NO_NONPASS_OR_FOREIGN_CLASS')
    stdout=(root/'primary'/'original.stdout.private').read_text(encoding='utf-8',errors='strict')
    nodes=[]
    for match in re.finditer(r'^(.+?)::(test_\S+) PASSED(?:\s+.*)?$',stdout,re.M):
        path,name=match.groups()
        need((root/path).resolve()==Path(cfg['controls']['path']).resolve(),'DEFAULTBACKEND35_ACTUAL_NODE_PATH')
        nodes.append(name)
    need(len(nodes)==len(set(nodes))==35 and sorted(nodes)==sorted(cfg['expected_case_names']),'DEFAULTBACKEND35_TRUE_STDOUT_NODE_CENSUS')
    return {'schema':1,'status':'PASS_35_FAKE_BACKEND_CASES_ONLY','counts':{'passed':35,'failed':0,'errors':0,'skipped':0,'unique_cases':35},'expected_names':cfg['expected_case_names'],'junit_names':names,'stdout_names':nodes,'junit_binding':binding(junit)}


def main():
    a=parse_arguments(); cfg,release_binding=admission(a)
    if a.phase=='guard':
        guard(cfg); return 0
    need(a.phase=='launch','DEFAULTBACKEND35_LAUNCH_PHASE')
    root=Path(cfg['root_once']); need(not root.exists() and not root.is_symlink(),'DEFAULTBACKEND35_FRESH_ONCE_ROOT_ABSENT')
    os.umask(0o077); root.mkdir(mode=0o700,exist_ok=False)
    durable(root/'consumed-distinct-ROOT-release.json',{'release_binding':release_binding,'native':'NOT_RUN'})
    forwarded=['--config',a.config,'--config-sha256',a.config_sha256,'--release',a.release,'--release-sha256',a.release_sha256]
    guardcmd=['timeout','--signal=TERM','--kill-after=10s','120s',CACHED,str(Path(__file__)),'--phase','guard',*forwarded]
    primarycmd=cfg['pytest_argv']
    outcomes={}; failure=None; started=time.monotonic(); census=None
    def phase(name,argv):
        parent=root/name; parent.mkdir(mode=0o700,exist_ok=False)
        parent_seconds = cfg['budgets']['primary_parent'] if name == 'primary' else cfg['budgets']['before_parent']
        with (parent/'original.stdout.private').open('xb') as out,(parent/'original.stderr.private').open('xb') as err:
            try:
                done=subprocess.run(argv,cwd=root,stdout=out,stderr=err,timeout=parent_seconds,check=False)
                result={'returncode':done.returncode}
            except BaseException as error:
                result={'exception_class':type(error).__name__}
            out.flush();os.fsync(out.fileno());err.flush();os.fsync(err.fileno())
        result.update(argv=argv,parent_seconds=parent_seconds,stdout_binding=binding(parent/'original.stdout.private'),stderr_binding=binding(parent/'original.stderr.private'))
        durable(parent/'original-terminal.json',result);outcomes[name]=result;return result
    try:
        need(phase('before',guardcmd).get('returncode')==0,'DEFAULTBACKEND35_BEFORE_GUARD_FAILED')
        for key in ('basetemp','logger','junit'):
            p=Path(cfg[key]);need(p.parent==root and not p.exists() and not p.is_symlink(),'DEFAULTBACKEND35_FRESH_OUTPUT_ABSENT')
        need(phase('primary',primarycmd).get('returncode')==0,'DEFAULTBACKEND35_CONTROL_PROCESS_FAILED_OR_TIMEOUT')
        census=admit_census(cfg,root)
        durable(root/'original-pytest35-node-census.json',census)
    except BaseException as error:
        failure={'exception_class':type(error).__name__}
        durable(root/'original-primary-failure.private.json',{'exception_class':type(error).__name__,'private_error_text':str(error)})
    finally:
        try:
            need(phase('always-post',guardcmd).get('returncode')==0,'DEFAULTBACKEND35_ALWAYSPOST_FAILED')
            admission(a)
        except BaseException as error:
            if failure is None:failure={'post_exception_class':type(error).__name__}
            durable(root/'original-post-failure.private.json',{'exception_class':type(error).__name__,'private_error_text':str(error)})
    result={'schema':1,'status':'PASS_35_FAKE_BACKEND_CASES_PENDING_INDEPENDENT_ORIGINAL_CENSUS' if failure is None else 'FAIL_OR_HOLD_NO_RETRY',
            'source':cfg['source'],'tree':cfg['tree'],'outcomes':outcomes,'failure':failure,'counts':census['counts'] if census else None,
            'original_census_binding':binding(root/'original-pytest35-node-census.json') if census else None,
            'release_binding':release_binding,'elapsed_seconds':time.monotonic()-started,'native':'NOT_RUN',
            'backend_full_descriptor_walk':'OWNED_FAKE_TREE_ONLY','memory_sampler_native_adoption':'NONE',
            'scope':'35 real default descriptor walks on owned fake trees only, no host cgroup observations/signals/threshold calibration/profile adoption'}
    durable(root/'OWNERFINAL-root-one-original-defaultbackend35-pure-controls.json',result,0o400)
    print(json.dumps({'status':result['status'],'counts':result['counts'],'native':'NOT_RUN'}))
    return 0 if failure is None else 1


if __name__=='__main__':
    raise SystemExit(main())
