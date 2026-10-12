"""Prepared parameter successor; unresolved accepted predecessor slots fail closed.

No configuration is constructed in this preparation wave. A separately named
final constructor must fill actual original-result/root/independent bindings
from real accepted preceding gates; existing files may never be rewritten.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import stat

CURRENT_CONFIG = Path('/workspace/engineering/rcc-current8d49-qualified-V9-entry-bootstrap-preparation/FROZEN-current8d49-control3-qualified-V9-entry-config-v2.json')
CURRENT_SHA = '5dc48075c8a2c91042f38a4c4c8941e9eb7f5c0feb82dcc93917cb8ec76c9f25'
SOURCE = '8d49d0865ad5ad27b2d4e325ec135212080625e8'
TREE = 'a80600809d373038ca76e445ba0b7b79bb7eeaa6'
ACQUISITION = '0da97bfc63a5e47de1c900e8d37ec55261d8b7ef6f68069a74167afc344c72ad'
APPROVED_PREDECESSORS = None  # MUST stay unresolved until root accepts actual3/5.
SPECIFICATIONS = {
    'released5': ('/dev/shm/actions-rcc-approved-test-only-binaries-20261011/released5', '1a617ad7c736fa67c605e20e5ebe3c7d54b02cd548f733e05c809cf49a48db1e', 'released-18.19.5-linux-amd64', 'v18.19.5', 'd1aec7d0bb897a81274423c7a6bb747233f9c263', True),
    'candidate7276': ('/dev/shm/actions-rcc-approved-test-only-binaries-20261011/candidate7276', 'be55dadc391ae4ac7dd38356755a1698c595fdf41bd4a0141f8df7cc9d29f00e', 'candidate-727-18.19.6-linux-amd64', 'v18.19.6', '727c1ff8b679cdbbe12836e53c87734a1edb0071', False),
}
ROOTS = {
    'control3': '/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-4',
    'released5': '/dev/shm/actions-rcc-compatibility-actual-released5-20261011-owned-pkgs-1',
    'candidate7276': '/dev/shm/actions-rcc-compatibility-actual-candidate7276-20261011-owned-pkgs-1',
}
ORDER = ('control3','released5','candidate7276')
SURFACE = ('env-publish','env-acquire','env-exec','verified-artifact','process-lease')


def require(condition,category):
    if not condition:
        raise RuntimeError(category)


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


def bound(row):
    require(type(row) is dict and set(row)=={'path','sha256','bytes','mode'},'PREDECESSOR_BINDING_SHAPE')
    p=Path(row['path']);meta=p.lstat();require(stat.S_ISREG(meta.st_mode) and not p.is_symlink(),'PREDECESSOR_REGULAR')
    raw=p.read_bytes();require(type(row['bytes']) is int and len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'] and oct(stat.S_IMODE(meta.st_mode))==row['mode'],'PREDECESSOR_FROZEN_IDENTITY')
    return json.loads(raw)


def exact_predecessors(label):
    require(label in SPECIFICATIONS,'NEXT_VERSION_UNKNOWN')
    require(type(APPROVED_PREDECESSORS) is dict,'WAIT_REAL_ROOT_ACCEPTED_SAME_SOURCE_PREDECESSORS')
    expected=ORDER[:ORDER.index(label)]
    require(label in APPROVED_PREDECESSORS and type(APPROVED_PREDECESSORS[label]) is list and len(APPROVED_PREDECESSORS[label])==len(expected),'PREDECESSOR_ACCEPTED_COUNT')
    rows=[];bindings=[]
    for required_label, token in zip(expected,APPROVED_PREDECESSORS[label]):
        require(set(token)=={'original_result','original_ROOT','independent_review','expected_ROOT_body','expected_independent_body'},'PREDECESSOR_ROOT_AUTHENTICATED_TOKEN_FIELDS')
        result=bound(token['original_result']);root=bound(token['original_ROOT']);review=bound(token['independent_review'])
        require(root==token['expected_ROOT_body'] and review==token['expected_independent_body'],'PREDECESSOR_ACCEPTED_ROOT_REVIEW_EXACT')
        require(token['original_result']['path']==ROOTS[required_label]+'/OWNERFINAL-one-version-actual-result.json','PREDECESSOR_ORIGINAL_PATH')
        require(result.get('label')==required_label and result.get('source')==SOURCE and result.get('tree')==TREE and result.get('status')=='PASS_SCOPED','PREDECESSOR_CURRENT_SOURCE_ACTUAL_PASS')
        require(result.get('tests')=={'tests':2,'passed':2,'skipped':0,'failures':0,'errors':0} and all(type(x) is int for x in result['tests'].values()),'PREDECESSOR_EXACT_TWO_ACTUAL_CASES')
        # Tokens are immutable original observations, not newly asserted features.
        rows.append({'label':required_label,'status':'PASS','tests':2,'skipped':0,'errors':0})
        bindings.extend(token[k] for k in ('original_result','original_ROOT','independent_review'))
    return rows,bindings


def prospective_config(label):
    prior,prior_bindings=exact_predecessors(label)  # fail before touching output or binary.
    raw=CURRENT_CONFIG.read_bytes();require(hashlib.sha256(raw).hexdigest()==CURRENT_SHA,'CURRENT_V9_CONFIG_IDENTITY')
    cfg=copy.deepcopy(json.loads(raw));require(cfg['source']==SOURCE and cfg['tree']==TREE and cfg['source_count']==1440,'CURRENT_SOURCE_QUALIFIED_TUPLE')
    path,digest,selector,version,revision,modified=SPECIFICATIONS[label]
    require(not Path(ROOTS[label]).exists() and not Path(ROOTS[label]).is_symlink(),'NEXT_VERSION_FRESH_ONCE_ROOT')
    # Stream hash before native probing; no binary is executed by this constructor.
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    require(h.hexdigest()==digest,'NEXT_VERSION_APPROVED_BINARY_HASH')
    cfg['binary']={'path':path,'sha256':digest,'selector':selector,'version':version}
    oldroot=cfg['owned_root'];cfg['owned_root']=ROOTS[label]
    cfg['pytest_argv']=[ROOTS[label]+arg[len(oldroot):] if arg.startswith(oldroot+'/') else arg for arg in cfg['pytest_argv']]
    compatibility={'version':version,'source_commit':revision,'source_modified':modified,'binary_sha256':digest,'platform':'linux-amd64','runtime_kind':'rcc','adapter_contract':'rcc-runtime/v1','provenance_kind':'ORIGINAL_API_ASSET_OR_BUILD_RECEIPT_DATA_ONLY','provenance_sha256':ACQUISITION,'approval':'APPROVED_TEST_ONLY','required_surface':list(SURFACE)}
    compatibility['compatibility_id']=hashlib.sha256(json.dumps(compatibility,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    cfg['fixture_expected']=dict(cfg['fixture_expected'],rcc={'sha256':digest,'version':version},compatibility=compatibility)
    marker={'schema':1,'runtime_source_sha':SOURCE,'runtime_source_tree':TREE,'label':label,'binary_sha256':digest,'state_root':ROOTS[label],'package_cache_root':ROOTS[label]+'/actions-home/pkgs'}
    marker_sha=hashlib.sha256(encoded(marker)).hexdigest()
    cfg['owned_package_cache']={'schema':1,'marker':marker,'marker_sha256':marker_sha,'marker_path':ROOTS[label]+'/rcc-package-cache-owner.json','child_config':dict(marker,state_marker_sha256=marker_sha),'environment_key':'ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG','cold_publication_then_warm_staged_pkgs_only':True}
    cfg['preceding']=prior;cfg['preceding_original_bindings']=prior_bindings
    cfg['bindings'].extend(prior_bindings)
    cfg['actual_status']='NOT_RUN_NEXT_VERSION_REQUIRES_INDEPENDENT_CONFIG_AND_ROOT_ONCE'
    cfg['launch_disposition']='HOLD_NEXT_VERSION_INDEPENDENT_CONFIGURATION_AND_DISTINCT_ROOT_RELEASE'
    return cfg


if __name__=='__main__':
    raise SystemExit('PREPARATION_ONLY: no configuration write or native launch; accepted predecessor slots unresolved')
