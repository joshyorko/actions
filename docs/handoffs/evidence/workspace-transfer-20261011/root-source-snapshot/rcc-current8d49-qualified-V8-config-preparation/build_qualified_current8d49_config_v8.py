"""Construct one current source-qualified config, without native/product imports.

Historical identities remain keyed by (path,SHA); current qualification derives
from the real original inner FULL and separately retained ROOT post supplement.
"""
import argparse
import ast
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

PRIVATE = Path('/workspace/engineering/rcc-current8d49-private-V8-real-fixture-mode-successor')
SHARED = Path('/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation')
sys.path[:0] = [str(PRIVATE), str(SHARED)]
from actual_transport_v8 import BINARIES, CONTROL, CONTROL_TREE, SOURCE, TREE, content_sha, read_bound, verify_temporal_shared_outputs
from historical_binding_current8d49_v8 import HISTORICAL_FIXTURE
from owned_cache_policy_v8 import ROOTS, encoded, sha, cache_plan
from runner_contracts_v3 import SELECTORS, need, next_version, parse_json_object

O = Path(__file__).resolve().parent
OLD = Path('/workspace/engineering/rcc-compatibility-current-e4ff-qualified-config-successor/FROZEN-current-e4ff-control3-owned-cache-SOURCE-QUALIFIED-v4.json')
OLD_SHA = '1411879501e1ef2bd5aec7fbf9627457aa840badc8e86be980c25b207ee9d5dc'
LIGHT_OWNER = Path('/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/OWNERFINAL-current8d49-configured-SOURCE_LIGHT-PASS.json')
LIGHT_OWNER_SHA = 'd7f23a52d044195187992aeac80e692429e1a1a4af16ee9b37f1971cfbdc4104'
LIGHT_REVIEW = {'path': '/workspace/engineering/pr308-current8d49-independent-SOURCE-LIGHT-review/OWNERFINAL-independent-current8d49-configured-SOURCE_LIGHT-review.json', 'bytes': 3596, 'sha256': 'b0d1c4ee4cee11fc3c2ffd9f6fece609869fa4b447d43bfb8c91ca4a2bf6222b', 'mode': '0o400'}
FULL_REVIEW = {'path': '/workspace/engineering/pr308-current8d49-independent-SOURCEFULL-actual-review/OWNERFINAL-independent-current8d49-original-configured-SOURCEFULL-and-retained-ROOTpost-supplement-review.json', 'bytes': 10038, 'sha256': '073e235afffab50dee204bcaae236e77ceb8e23644db15a90a0e56d48dc8dca9', 'mode': '0o400'}
PRIVATE_REVIEW = None  # New named constructor must fill accepted exact review before construction.
LIGHT_CONFIG = Path('/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/frozen-current8d49-source-LIGHT-inputs-v3.json')
LIGHT_CONFIG_SHA = '81f52920b50e67619b3bb418a7c1034a2106ec52f4badd71b9d85e29b7376820'
INVENTORY = Path('/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/private-current8d49-source-body-mode-inventory-v3.json')
TEMPORAL = Path('/workspace/engineering/rcc-current8d49-private-V8-fixture-logger-successor/private-current-shared-generated-output-temporal-body-nsmetadata-bindings.json')
ACQUISITION_SHA = '0da97bfc63a5e47de1c900e8d37ec55261d8b7ef6f68069a74167afc344c72ad'


def physical_bind(path, expected=None):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), 'CONSTRUCTOR_REGULAR_INPUT')
    raw = path.read_bytes()
    need(expected is None or sha(raw) == expected, 'CONSTRUCTOR_FROZEN_HASH')
    return dict(path=str(path), bytes=len(raw), sha256=sha(raw), mode=oct(stat.S_IMODE(path.stat().st_mode)))


def checked(row):
    read_bound(row)
    return dict(row)


def compatibility(label):
    if label == 'control3': return None
    _, digest, _, version = BINARIES[label]
    value = {'version': version, 'source_commit': ('d1aec7d0bb897a81274423c7a6bb747233f9c263' if label == 'released5' else '727c1ff8b679cdbbe12836e53c87734a1edb0071'),
             'source_modified': label == 'released5', 'binary_sha256': digest,
             'platform': 'linux-amd64', 'runtime_kind': 'rcc', 'adapter_contract': 'rcc-runtime/v1',
             'provenance_kind': 'ORIGINAL_API_ASSET_OR_BUILD_RECEIPT_DATA_ONLY', 'provenance_sha256': ACQUISITION_SHA,
             'approval': 'APPROVED_TEST_ONLY', 'required_surface': ['env-publish', 'env-acquire', 'env-exec', 'verified-artifact', 'process-lease']}
    value['compatibility_id'] = content_sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())
    return value


def qualification_documents(inner, light, review, root_original, supplement):
    need(inner['source'] == SOURCE and inner['tree'] == TREE and inner['phase'] == 'FULL'
         and inner['status'] == 'PASS' and inner['primary_started'] is True
         and type(inner['primary']) is int and inner['primary'] == 0
         and type(inner['post']) is int and inner['post'] == 0
         and [(r['stage'], r['returncode']) for r in inner['records']] == [('before',0),('FULL',0),('after-always',0)]
         and all(type(r['returncode']) is int for r in inner['records']), 'CURRENT_ORIGINAL_INNER_FULL_PASS')
    need(light['decision'] == 'GO_CURRENT8D49_CONFIGURED_SOURCE_LIGHT_ONLY'
         and light['source']['commit'] == SOURCE and light['source']['tree'] == TREE
         and light['source']['typed_entries'] == 1440 and light['source']['clean'] is True,
         'CURRENT_SOURCE_LIGHT_QUALIFICATION')
    expected = {'before':0,'configured_primary':0,'runner_after_always':0,'ROOT_outer':0,'ROOT_extra_post':1,
                'named_readonly_supplement':0,'pytest_unique_named_outcomes':1483,'pytest_PASS':1470,'pytest_SKIP':13,
                'pytest_FAIL':0,'pytest_ERROR':0,'pytest_workers':2}
    need(review['decision'] == 'GO_CURRENT8D49_ORIGINAL_CONFIGURED_SOURCEFULL_ONLY_WITH_SEPARATE_READONLY_POST_SUPPLEMENT'
         and review['source'] == SOURCE and review['tree'] == TREE and type(review['complete_typed_source']) is int
         and review['complete_typed_source'] == 1440
         and all(type(review['actual_gate_results'][key]) is int and review['actual_gate_results'][key] == value for key,value in expected.items()),
         'CURRENT_SOURCE_FULL_INDEPENDENT_QUALIFICATION')
    need(root_original['source'] == SOURCE and root_original['tree'] == TREE
         and root_original['status'] == 'FAIL_OR_HOLD_NO_RETRY' and root_original['outer_returncode'] == 0
         and root_original['independent_ROOT_post'] == 1, 'ORIGINAL_ROOT_POST_FAILURE_PRESERVED')
    need(supplement['status'] == 'NAMED_READONLY_POST_ENV_SUPPLEMENT_PASS' and type(supplement['returncode']) is int and supplement['returncode'] == 0
         and supplement['original_FULL_terminal'] == review['original_configured_FULL_terminal']
         and supplement['original_ROOT_owner'] == review['original_ROOT_owner_binding']
         and supplement['only_environment_metadata']['PYTEST_XDIST_AUTO_NUM_WORKERS'] == '2', 'SEPARATE_READONLY_POST_SUPPLEMENT_REQUIRED')


def constructor(label, preceding=()):
    need(PRIVATE_REVIEW is not None, 'PRIVATE_CURRENT_INDEPENDENT_REVIEW_UNBOUND')
    source_root=Path('/workspace/engineering/pr308');root=Path(ROOTS[label])
    need(not root.exists() and not root.is_symlink(), 'CONSTRUCTOR_ONCE_ROOT_MUST_BE_ABSENT')
    old_binding=physical_bind(OLD,OLD_SHA);old=parse_json_object(OLD.read_bytes())
    need(len(old['bindings']) == 237 and old['control'] == CONTROL and old['control_tree'] == CONTROL_TREE, 'HISTORICAL237_CONTROL')
    refs={}
    def add(row):
        row=checked(row);key=(row['path'],row['sha256'])
        need(key not in refs or refs[key] == row, 'SAME_CONTENT_BINDING_METADATA_CONFLICT')
        refs[key]=row
        return row
    for row in old['bindings']:add(row)
    add(old_binding)
    need(any(row == HISTORICAL_FIXTURE for row in old['bindings']), 'EXACT_ORIGINAL237_FIXTURE_REQUIRED')
    light_owner_binding=add(physical_bind(LIGHT_OWNER,LIGHT_OWNER_SHA));owner=parse_json_object(LIGHT_OWNER.read_bytes())
    for row in owner['frozen_bindings']:add(row)
    lreview=add(LIGHT_REVIEW);freview=add(FULL_REVIEW);private_review=add(PRIVATE_REVIEW)
    l=parse_json_object(Path(lreview['path']).read_bytes());f=parse_json_object(Path(freview['path']).read_bytes())
    full=add(f['original_configured_FULL_terminal']);add(f['original_configured_FULL_log'])
    original_root=add(f['original_ROOT_owner_binding']);supplement=add(f['named_readonly_post_env_supplement'])
    for row in f['named_supplement_frozen_facts'].values():
        if type(row) is dict and 'path' in row:add(row)
    qualification_documents(parse_json_object(Path(full['path']).read_bytes()),l,f,
                             parse_json_object(Path(original_root['path']).read_bytes()),parse_json_object(Path(supplement['path']).read_bytes()))
    add(physical_bind(LIGHT_CONFIG,LIGHT_CONFIG_SHA));prepared=parse_json_object(LIGHT_CONFIG.read_bytes())
    need(len(prepared['prepared_inputs']) == 30,'CURRENT_PREPARED30')
    for path,digest in prepared['prepared_inputs'].items():need(sha((source_root/path).read_bytes())==digest,'CURRENT_PREPARED_BODY')
    for row in prepared['prepared_environment_and_RCC_bindings']:add(row)
    inventory=json.loads(INVENTORY.read_bytes());add(physical_bind(INVENTORY))
    need(type(inventory) is list and len(inventory)==1440 and len({r['path'] for r in inventory})==1440, 'CURRENT_COMPLETE1440')
    for row in inventory:
        p=source_root/row['path'];raw=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes()
        need(sha(raw)==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode'],'CURRENT_SOURCE_FS_BODY_MODE')
    temporal=json.loads(TEMPORAL.read_bytes());verify_temporal_shared_outputs(temporal);add(physical_bind(TEMPORAL))
    for path in (*PRIVATE.glob('*.py'),O/'build_qualified_current8d49_config_v8_FINAL.py'):add(physical_bind(path))
    for row in parse_json_object(Path(PRIVATE_REVIEW['path']).read_bytes()).get('frozen_bindings',[]):add(row)
    prior=[]
    for path in preceding:
        row=add(physical_bind(path));value=parse_json_object(Path(path).read_bytes())
        need(value.get('source')==SOURCE and value.get('tree')==TREE and value.get('status')=='PASS_SCOPED'
             and value.get('tests')=={'tests':2,'passed':2,'skipped':0,'failures':0,'errors':0}
             and all(type(x) is int for x in value['tests'].values()),'SAME_SOURCE_PREDECESSOR_ACTUAL_PASS')
        prior.append(dict(label=value.get('label'),status='PASS',tests=2,skipped=0,errors=0))
    next_version(label,prior)
    binary_path,digest,selector,version=BINARIES[label];add(physical_bind(binary_path,digest))
    live_fixture=add(physical_bind(source_root/'action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'))
    need(live_fixture['sha256']!=HISTORICAL_FIXTURE['sha256'],'CURRENT_AND_HISTORICAL_FIXTURE_SEPARATE')
    marker=dict(schema=1,runtime_source_sha=SOURCE,runtime_source_tree=TREE,label=label,binary_sha256=digest,state_root=str(root),package_cache_root=str(root/'actions-home/pkgs'))
    plan=dict(schema=1,marker=marker,marker_sha256=sha(encoded(marker)),marker_path=str(root/'rcc-package-cache-owner.json'),child_config=dict(marker,state_marker_sha256=sha(encoded(marker))),environment_key='ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG',cold_publication_then_warm_staged_pkgs_only=True)
    value=dict(old);python=str(source_root/'action_server/.venv/bin/python')
    value.update(source=SOURCE,tree=TREE,source_count=1440,source_FULL=full,source_independent=lreview,source_FULL_independent=freview,
                 source_FULL_original_ROOT_HOLD=original_root,source_FULL_readonly_post_supplement=supplement,
                 owned_root=str(root),prepared_inputs=prepared['prepared_inputs'],source_body_modes=inventory,bindings=list(refs.values()),preceding=prior,
                 preceding_original_bindings=[physical_bind(path) for path in preceding],owned_package_cache=plan,
                 binary=dict(path=binary_path,sha256=digest,selector=selector,version=version),temporal_shared_outputs=temporal,
                 pytest_argv=[python,'-m','pytest','-n0','-vv','-rA','-m','integration_test and real_rcc','--basetemp',str(root/'pytest'),
                              '--robocorp-log-output',str(root/'pytest-logging'),'-o','tmp_path_retention_policy=all','--junitxml',str(root/'junit.xml'),*SELECTORS],
                 current_source_LIGHT=light_owner_binding,current_fixture_binding=live_fixture,historical_fixture_binding=dict(HISTORICAL_FIXTURE),
                 historical_native_and_literal_source_config=old_binding,private_source_independent=private_review,
                 launch_disposition='SOURCE_QUALIFIED_CONFIG_INDEPENDENT_REVIEW_AND_DISTINCT_ROOT_ADOPTION_REQUIRED',actual_status='NOT_RUN')
    value['fixture_expected']=dict(old['fixture_expected'],source=dict(commit=SOURCE,tree=TREE),compatibility=compatibility(label),rcc=dict(version=version,sha256=digest))
    cache_plan(value,label,SOURCE,TREE,BINARIES)
    return value


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',choices=tuple(BINARIES),required=True);parser.add_argument('--output',required=True);parser.add_argument('--preceding',action='append',default=[]);args=parser.parse_args()
    value=constructor(args.label,args.preceding)
    fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:out.write((json.dumps(value,indent=2,sort_keys=True)+'\n').encode())
    print(json.dumps(physical_bind(args.output)))
if __name__=='__main__':main()
