"""Construct a distinct current-source config; no product/process/native imports.

Current full-source/review slots are deliberately unbound. A reviewed named
constructor successor must bind them, never mutate this frozen preparation.
Historical config supplies immutable native inventory and fixture literals only.
"""
import argparse
import ast
import json
import os
import stat
from pathlib import Path

from actual_transport_v7 import BINARIES, CONTROL, CONTROL_TREE, SOURCE, TREE, content_sha
from historical_binding_v1 import MAPPING, verify_missing_original
from owned_cache_policy_v1 import ROOTS, encoded, sha
from runner_contracts_v3 import SELECTORS, need, next_version, parse_json_object

SOURCE_OWNER = Path('/workspace/engineering/pr308-cache-current-e3c-source/OWNERFINAL-current-e4ff-reviewed-cache-application-and-e3c-ordinary-source-LIGHT.json')
SOURCE_OWNER_SHA = 'e18d871d9daf93e21e0b34610af31e9d4198bc4a1c93431d8799464954d37c6c'
BASE = Path('/workspace/engineering/rcc-compatibility-actual-runner-readonly-preparation/FROZEN-control3-current-b614-actual-config-v2.json')
BASE_SHA = '8c5da5be25ebfcf86f286ee9f93ddad328c68b3243b0935ec5937c93376bb948'
ACQUISITION_SHA = '0da97bfc63a5e47de1c900e8d37ec55261d8b7ef6f68069a74167afc344c72ad'
SOURCE_LIGHT_REVIEW = None
SOURCE_FULL = None
SOURCE_FULL_REVIEW = None
FIXTURE_PATH = 'action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'


def bind(path, expected=None):
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        from historical_binding_v1 import ORIGINAL
        need(str(path) == ORIGINAL['path'] and expected == ORIGINAL['sha256'], 'CONSTRUCTOR_MISSING_ORIGINAL')
        verify_missing_original(ORIGINAL)
        return dict(ORIGINAL)
    raw = path.read_bytes()
    need(expected is None or sha(raw) == expected, 'CONSTRUCTOR_FROZEN_HASH')
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw),
            'mode': oct(stat.S_IMODE(path.stat().st_mode))}


def compatibility(label):
    if label == 'control3':
        return None
    _, digest, _, version = BINARIES[label]
    value = {'version': version,
             'source_commit': ('d1aec7d0bb897a81274423c7a6bb747233f9c263'
                               if label == 'released5' else '727c1ff8b679cdbbe12836e53c87734a1edb0071'),
             'source_modified': label == 'released5', 'binary_sha256': digest,
             'platform': 'linux-amd64', 'runtime_kind': 'rcc', 'adapter_contract': 'rcc-runtime/v1',
             'provenance_kind': 'ORIGINAL_API_ASSET_OR_BUILD_RECEIPT_DATA_ONLY',
             'provenance_sha256': ACQUISITION_SHA, 'approval': 'APPROVED_TEST_ONLY',
             'required_surface': ['env-publish', 'env-acquire', 'env-exec', 'verified-artifact', 'process-lease']}
    value['compatibility_id'] = content_sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())
    return value


def nullable_binding(row):
    return row if row is not None else {'path': None, 'bytes': None, 'sha256': None, 'mode': None}


def constructor(label, owned_root, preceding=()):
    root = Path(owned_root)
    need(root.parent == Path('/dev/shm') and root.name.startswith('actions-rcc-compatibility-actual-' + label + '-')
         and not root.exists() and not root.is_symlink(), 'CONSTRUCTOR_PER_VERSION_ONCE_ROOT')
    need(str(root) == ROOTS[label], 'CONSTRUCTOR_DISTINCT_FROZEN_ONCE_ROOT')
    owner_binding = bind(SOURCE_OWNER, SOURCE_OWNER_SHA)
    owner = parse_json_object(SOURCE_OWNER.read_bytes())
    need(owner['source']['commit'] == SOURCE and owner['source']['tree'] == TREE, 'CURRENT_SOURCE_OWNER')
    old_binding = bind(BASE, BASE_SHA)
    old = parse_json_object(BASE.read_bytes())
    need(old['control'] == CONTROL and old['control_tree'] == CONTROL_TREE, 'LEGACY_CONTROL_UNCHANGED')
    refs = {row['path']: bind(row['path'], row['sha256']) for row in old['bindings']}
    refs[str(BASE)] = old_binding
    refs[MAPPING['path']] = bind(MAPPING['path'], MAPPING['sha256'])
    refs[str(SOURCE_OWNER)] = owner_binding
    for row in owner['frozen_bindings']:
        refs[row['path']] = bind(row['path'], row['sha256'])
    for path in Path(__file__).parent.glob('*.py'):
        refs[str(path)] = bind(path)
    inventory_path = SOURCE_OWNER.parent / 'private-current-e4ff-complete-source-body-mode-inventory.json'
    inventory = json.loads(inventory_path.read_bytes())
    need(type(inventory) is list and len(inventory) == owner['complete_union']['leaves'] == 1423,
         'CURRENT_COMPLETE_SOURCE_COUNT')
    source_root = Path('/workspace/engineering/pr308')
    for row in inventory:
        path = source_root / row['path']
        raw = os.readlink(path).encode() if row['mode'] == '120000' else path.read_bytes()
        need(content_sha(raw) == row['sha256'] and len(raw) == row['bytes']
             and stat.S_IMODE(path.lstat().st_mode) == row['fs_mode'], 'CURRENT_SOURCE_BODY_MODE')
    prepared = parse_json_object((SOURCE_OWNER.parent / 'own-current30-input-and-five-concrete-origins-Bootstrap-reuse.json').read_bytes())
    need(len(prepared['inputs']) == 30 and len(prepared['origins']) == 5, 'CURRENT_PREPARED_SCOPE')
    prior = []
    for path in preceding:
        bound = bind(path)
        refs[bound['path']] = bound
        value = parse_json_object(Path(path).read_bytes())
        need(value.get('source') == SOURCE and value.get('tree') == TREE
             and value.get('status') == 'PASS_SCOPED'
             and value.get('tests') == {'tests': 2, 'passed': 2, 'skipped': 0, 'failures': 0, 'errors': 0}
             and all(type(x) is int for x in value['tests'].values()), 'CURRENT_PREDECESSOR_REQUIRED')
        prior.append({'label': value.get('label'), 'status': 'PASS', 'tests': 2, 'skipped': 0, 'errors': 0})
    next_version(label, prior)
    path, digest, selector, version = BINARIES[label]
    refs[path] = bind(path, digest)
    fixture_binding = bind(source_root / FIXTURE_PATH)
    refs[fixture_binding['path']] = fixture_binding
    fixture_ast = ast.parse((source_root / FIXTURE_PATH).read_bytes())
    need(any(isinstance(node, ast.FunctionDef) and node.name == '_prepare_owned_rcc_test_package_cache'
             for node in fixture_ast.body), 'CURRENT_CACHE_FIXTURE_REQUIRED')
    marker = {'schema': 1, 'runtime_source_sha': SOURCE, 'runtime_source_tree': TREE,
              'label': label, 'binary_sha256': digest, 'state_root': str(root),
              'package_cache_root': str(root / 'actions-home/pkgs')}
    plan = {'schema': 1, 'marker': marker, 'marker_sha256': sha(encoded(marker)),
            'marker_path': str(root / 'rcc-package-cache-owner.json'),
            'child_config': dict(marker, state_marker_sha256=sha(encoded(marker))),
            'environment_key': 'ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG',
            'cold_publication_then_warm_staged_pkgs_only': True}
    python = str(source_root / 'action_server/.venv/bin/python')
    value = dict(old)
    value.update(source=SOURCE, tree=TREE, source_FULL=nullable_binding(SOURCE_FULL),
                 source_independent=nullable_binding(SOURCE_LIGHT_REVIEW), source_FULL_independent=nullable_binding(SOURCE_FULL_REVIEW),
                 owned_root=str(root), prepared_inputs=prepared['inputs'], concrete_own_origins=prepared['origins'],
                 source_body_modes=inventory, bindings=list(refs.values()), preceding=prior,
                 preceding_original_bindings=[bind(path) for path in preceding], owned_package_cache=plan,
                 binary={'path': path, 'sha256': digest, 'selector': selector, 'version': version},
                 pytest_argv=[python, '-m', 'pytest', '-n0', '-vv', '-rA', '-m', 'integration_test and real_rcc',
                              '--basetemp', str(root / 'pytest'), '--junitxml', str(root / 'junit.xml'), *SELECTORS],
                 current_source_LIGHT=owner_binding, current_fixture_binding=fixture_binding,
                 historical_native_and_literal_source_config=old_binding,
                 launch_disposition='HOLD_CURRENT_SOURCE_FULL_INDEPENDENT_AND_CACHE_CONFIGURATION_ADOPTION', actual_status='NOT_RUN')
    value['fixture_expected'] = dict(old['fixture_expected'], source={'commit': SOURCE, 'tree': TREE},
                                    compatibility=compatibility(label), rcc={'version': version, 'sha256': digest})
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', choices=tuple(BINARIES), required=True)
    parser.add_argument('--owned-root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--preceding', action='append', default=[])
    args = parser.parse_args()
    value = constructor(args.label, args.owned_root, args.preceding)
    fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2) + '\n').encode())
    print(json.dumps(bind(args.output), sort_keys=True))


if __name__ == '__main__':
    main()
