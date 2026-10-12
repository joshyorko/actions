"""Prospective fresh control3-root5 entry, inert without separate ROOT adoption.

Old native main and functional predicates are delegated unchanged. No producer
configuration/release is constructed by importing this file.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
import sys

SOURCE='8d49d0865ad5ad27b2d4e325ec135212080625e8'
TREE='a80600809d373038ca76e445ba0b7b79bb7eeaa6'
ORIGINAL='/workspace/engineering/rcc-current8d49-private-V8-real-fixture-mode-successor'
CONTRACTS='/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation'
READER='/workspace/engineering/rcc-current8d49-cgroup-reader-observer-private-SOURCE-PREPARED-NOTRUN'
POLICY='/workspace/engineering/rcc-next-native-cgroup-admission-source-PREPARED-NOTRUN'
HERE='/workspace/engineering/rcc-current8d49-memory-native-composition-SOURCE-PREPARED-NOTRUN'
OLD_ROOTS={'control3':'/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-3',
           'released5':'/dev/shm/actions-rcc-compatibility-actual-released5-20261011-owned-pkgs-1',
           'candidate7276':'/dev/shm/actions-rcc-compatibility-actual-candidate7276-20261011-owned-pkgs-1'}
NEW_CONTROL3='/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-5'
GATES={'memory17_actual','reader28_actual','backend35_actual','composition_actual','composition_source_independent'}


def need(ok,code):
    if not ok:raise ValueError(code)


def binding(path):
    p=Path(path);s=p.lstat();need(stat.S_ISREG(s.st_mode) and not p.is_symlink(),'MEMORY_ENTRY_REGULAR_FILE')
    raw=p.read_bytes()
    return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}


def read_bound(row):
    need(type(row) is dict and set(row)=={'path','bytes','sha256','mode'} and binding(row['path'])==row,'MEMORY_ENTRY_BOUND_IDENTITY')
    return Path(row['path']).read_bytes()


def physical(path,mode):
    p=Path(path);s=p.lstat()
    need(stat.S_ISREG(s.st_mode) and not p.is_symlink() and stat.S_IMODE(s.st_mode)==mode
         and s.st_uid==os.getuid()==1000 and s.st_gid==os.getgid()==1000,'MEMORY_ENTRY_OPERATOR_PHYSICAL')


def admit_profile(config,release,config_sha,label):
    """Fail before original imports/main unless all independent gates are real."""
    need(label=='control3' and config['source']==SOURCE and config['tree']==TREE,'MEMORY_BASELINE_CONTROL3_ONLY')
    need(config['owned_root']==NEW_CONTROL3 and config['preceding']==[],'MEMORY_FRESH_CONTROL3_PROFILE')
    need(not Path(NEW_CONTROL3).exists() and not Path(NEW_CONTROL3).is_symlink(),'MEMORY_FRESH_CONTROL3_ROOT_ABSENT')
    profile=config.get('cgroup_memory_profile')
    need(type(profile) is dict and set(profile)=={'schema','status','source','tree','initial_headroom_bytes','reserve_bytes','cgroup_identity','module_bindings','gate_bindings','gate_expected_fields'},'MEMORY_PROFILE_SCHEMA')
    need(type(profile['schema']) is int and profile['schema']==1 and profile['status']=='QUALIFIED_CURRENT_CGROUP_MEMORY_CONTROL3_PROFILE'
         and profile['source']==SOURCE and profile['tree']==TREE,'MEMORY_PROFILE_STATUS_SOURCE')
    need(type(profile['initial_headroom_bytes']) is int and profile['initial_headroom_bytes']==3113851289
         and type(profile['reserve_bytes']) is int and profile['reserve_bytes']==536870912,'MEMORY_NO_THRESHOLD_CHANGE')
    need(type(profile['gate_bindings']) is dict and set(profile['gate_bindings'])==GATES
         and type(profile['gate_expected_fields']) is dict and set(profile['gate_expected_fields'])==GATES,'MEMORY_ALL_DISTINCT_GATE_ROLES')
    need(len({(r['path'],r['sha256']) for r in profile['gate_bindings'].values()})==len(GATES),'MEMORY_DISTINCT_GATE_BINDINGS')
    for role in sorted(GATES):
        review=json.loads(read_bound(profile['gate_bindings'][role]))
        expected=profile['gate_expected_fields'][role]
        need(type(expected) is dict and {'schema','source','tree','decision'}.issubset(expected),'MEMORY_GATE_EXPECTED_SCHEMA')
        need(expected['schema']==1 and expected['source']==SOURCE and expected['tree']==TREE
             and type(expected['decision']) is str and expected['decision'].startswith('GO_PRIVATE_NATIVE_MEMORY_COMPOSITION_SOURCE_' if role=='composition_source_independent' else 'GO_ACTUAL_'),'MEMORY_GATE_NO_NULL_SOURCE_HOLD_AS_ACTUAL')
        for key,value in expected.items():
            need(type(review.get(key)) is type(value) and review[key]==value,'MEMORY_REAL_GATE_BINDING')
    required_paths={str(Path(HERE)/'native_memory_entry_v1_NOTRUN.py'),str(Path(HERE)/'native_memory_sampler_overlay_v1_NOTRUN.py'),
                    str(Path(READER)/'cgroup_memory_reader_observer_v1_NOTRUN.py'),str(Path(POLICY)/'proposed_cgroup_memory_state_v1_NOTRUN.py'),
                    str(Path(ORIGINAL)/'actual_transport_v8.py'),str(Path(ORIGINAL)/'owned_cache_policy_v8.py'),str(Path(CONTRACTS)/'runner_contracts_v3.py')}
    need(type(profile['module_bindings']) is list and len(profile['module_bindings'])==7 and {r['path'] for r in profile['module_bindings']}==required_paths,'MEMORY_MODULE_PATH_CLOSURE')
    for row in profile['module_bindings']:
        read_bound(row)
        need(row in config['bindings'],'MEMORY_ORIGINAL_GUARD_COVERS_NEW_MODULE')
    need(type(release) is dict and set(release)=={'schema','status','source','tree','label','config_sha256','memory_profile_sha256','memory_config_independent','original_native_cache_release','serialized_no_other_heavy_or_devshm_mutations'},'MEMORY_DISTINCT_ROOT_RELEASE_SCHEMA')
    profile_sha=hashlib.sha256((json.dumps(profile,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()
    for key,value in {'schema':1,'status':'ROOT_RELEASE_FRESH_CONTROL3_WITH_QUALIFIED_CGROUP_MEMORY',
                      'source':SOURCE,'tree':TREE,'label':label,'config_sha256':config_sha,
                      'memory_profile_sha256':profile_sha,'serialized_no_other_heavy_or_devshm_mutations':True}.items():
        need(type(release.get(key)) is type(value) and release[key]==value,'MEMORY_ROOT_EXACT_ADOPTION')
    independent=json.loads(read_bound(release['memory_config_independent']))
    for key,value in {'schema':1,'status':'INDEPENDENT_NATIVE_MEMORY_PROFILE_CONFIG_GO','source':SOURCE,'tree':TREE,'label':'control3',
                      'config_sha256':config_sha,'memory_profile_sha256':profile_sha,'gate_bindings':profile['gate_bindings'],'module_bindings':profile['module_bindings']}.items():
        need(type(independent.get(key)) is type(value) and independent[key]==value,'MEMORY_INDEPENDENT_CONFIG_ADOPTION')
    # Actual native floors, not the separate source-FULL TMP floor.
    for path,floor in (('/workspace',1288490189),('/dev/shm',3865470567)):
        fs=os.statvfs(path);need(fs.f_bavail*fs.f_frsize>=floor,'MEMORY_NATIVE_EXISTING_RESOURCE_FLOOR')
    return profile


def main():
    p=argparse.ArgumentParser()
    for name in ('config','config-sha256','release','release-sha256','label'):p.add_argument('--'+name,required=True)
    a=p.parse_args();physical(a.config,0o600);physical(a.release,0o600);physical(__file__,0o400)
    raw=Path(a.config).read_bytes();need(hashlib.sha256(raw).hexdigest()==a.config_sha256,'MEMORY_CONFIG_SHA')
    config=json.loads(raw);rawrelease=Path(a.release).read_bytes();need(hashlib.sha256(rawrelease).hexdigest()==a.release_sha256,'MEMORY_RELEASE_SHA')
    release=json.loads(rawrelease);profile=admit_profile(config,release,a.config_sha256,a.label)
    need(Path(sys.prefix).resolve()==Path(config['own_runtime_prefix']).resolve() and Path(sys.executable).absolute()==Path(config['python']).absolute(),'MEMORY_OWN_RUNTIME_PYTHON')
    sys.dont_write_bytecode=True
    sys.path[:0]=[HERE,READER,POLICY,ORIGINAL,CONTRACTS]
    cache=importlib.import_module('owned_cache_policy_v8')
    legacy=importlib.import_module('actual_transport_v8')
    overlay=importlib.import_module('native_memory_sampler_overlay_v1_NOTRUN')
    need(Path(cache.__file__).resolve()==Path(ORIGINAL)/'owned_cache_policy_v8.py' and Path(legacy.__file__).resolve()==Path(ORIGINAL)/'actual_transport_v8.py','MEMORY_ORIGINAL_IMPORT_PATHS')
    need(binding(Path(ORIGINAL)/'owned_cache_policy_v8.py')['sha256']=='4ccac4e3bd2c1e91352ef4e647968b4ca61f8691e1fc0f41e72a128a2942c205'
         and binding(Path(ORIGINAL)/'actual_transport_v8.py')['sha256']=='33dda17140ef749e22f086cc91b92ed8c3230fddfde8a4a369769e2183f695a1','MEMORY_ORIGINAL_MODULE_HASHES')
    need(cache.ROOTS==OLD_ROOTS,'MEMORY_ORIGINAL_ROOTS3_MAP')
    original_require=legacy.require_release
    cache.ROOTS['control3']=NEW_CONTROL3  # Exactly the existing V9 process-local fresh-root pattern.
    installed=None
    def require_release(candidate,grant,sha,label):
        need(candidate==config and grant==release and sha==a.config_sha256 and label=='control3','MEMORY_ORIGINAL_CALL_CONTEXT')
        return original_require(candidate,grant['original_native_cache_release'],sha,label)
    try:
        installed=overlay.install_composition(legacy,profile['cgroup_identity'])
        legacy.require_release=require_release
        return legacy.main()  # All artifact/Action/lease/lifecycle/cleanup checks unchanged.
    finally:
        legacy.require_release=original_require
        if installed is not None:
            legacy.FiniteSampler=installed['original_FiniteSampler']
            legacy.execute_one=installed['original_execute_one']
            del legacy._prepared_memory_composition_installed
        cache.ROOTS['control3']=OLD_ROOTS['control3']


if __name__=='__main__':
    raise SystemExit(main())
