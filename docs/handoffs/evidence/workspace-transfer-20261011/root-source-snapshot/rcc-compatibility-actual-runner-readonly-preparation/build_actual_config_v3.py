"""Read-only input constructor: creates a DISTINCT private once-version config.

No RCC/probe/process launch/product import. Missing FULL review creates a blocked
conditional config. Final review produces a new successor, never overwrites it.
"""
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

from actual_transport_v5 import BINARIES, CONTROL, CONTROL_TREE, SOURCE, TREE, content_sha
from runner_contracts_v3 import SELECTORS, need, next_version, parse_json_object

SOURCE_OWNER = Path('/workspace/engineering/pr308-rcc-compatibility-source/OWNERFINAL-current-a0d-approved-RCC-compatibility-SOURCE-LIGHT.json')
SOURCE_OWNER_SHA = '336cfca277d8e3b08035af8057e77af580fc7a5cbeb54226ae2140abedb79bba'
LIGHT_REVIEW = Path('/workspace/engineering/pr308-approved-compatibility-independent-source-light-review/OWNERFINAL-independent-current-a0d-approved-RCC-compatibility-SOURCE-LIGHT-review.json')
LIGHT_REVIEW_SHA = 'ea79c4b762d3cdcd5b9d54d2ab475b250596e55e78c6a3ead0574b1845f4ee92'
FULL_OWNER = Path('/workspace/engineering/root-rcc308-one-current-b614-source-full/OWNERFINAL-root-current-b614-configured-SOURCEFULL.json')
FULL_OWNER_SHA = 'eb73d4a34acaf77266f6aff75f758fa674e6b48aff968a31bbeca85148319bf8'
ACQUISITION = Path('/dev/shm/actions-rcc-compatibility-originals-20261011/OWNERFINAL-three-original-RCC-acquisition-data-qualification.json')
ACQUISITION_SHA = '0da97bfc63a5e47de1c900e8d37ec55261d8b7ef6f68069a74167afc344c72ad'
APPROVED_COPIES = Path('/workspace/engineering/root-two-exact-approved-test-only-binary-copies.json')
APPROVED_COPIES_SHA = '2b81e077eab373ed1574371608b0112e20c5d2ec96327f40b0c1d0d2a6a39c8a'


def bind(path, expected=None):
    p = Path(path)
    raw = p.read_bytes()
    need(expected is None or content_sha(raw) == expected, 'CONSTRUCTOR_ORIGINAL_HASH')
    return {'path': str(p), 'bytes': len(raw), 'sha256': content_sha(raw),
            'mode': oct(stat.S_IMODE(p.stat().st_mode))}


def compatibility(label):
    if label == 'control3':
        return None
    _, sha, _, version = BINARIES[label]
    value = {'version': version,
             'source_commit': ('d1aec7d0bb897a81274423c7a6bb747233f9c263'
                               if label == 'released5' else '727c1ff8b679cdbbe12836e53c87734a1edb0071'),
             'source_modified': label == 'released5', 'binary_sha256': sha,
             'platform': 'linux-amd64', 'runtime_kind': 'rcc', 'adapter_contract': 'rcc-runtime/v1',
             'provenance_kind': 'ORIGINAL_API_ASSET_OR_BUILD_RECEIPT_DATA_ONLY',
             'provenance_sha256': ACQUISITION_SHA, 'approval': 'APPROVED_TEST_ONLY',
             'required_surface': ['env-publish', 'env-acquire', 'env-exec', 'verified-artifact', 'process-lease']}
    value['compatibility_id'] = content_sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())
    return value


def predecessor_rows(paths, label):
    result = []
    for path in paths:
        raw = Path(path).read_bytes()
        value = parse_json_object(raw)
        need(value.get('status') == 'PASS_SCOPED' and value.get('source') == SOURCE and value.get('tree') == TREE,
             'PREDECESSOR_SUBJECT_AND_SCOPE')
        need(value.get('tests') == {'tests': 2, 'passed': 2, 'skipped': 0, 'failures': 0, 'errors': 0}, 'PREDECESSOR_JUNIT')
        need(all(type(x) is int for x in value['tests'].values()), 'PREDECESSOR_COUNTER_TYPES')
        result.append({'label': value.get('label'), 'status': 'PASS', 'tests': 2, 'skipped': 0, 'errors': 0})
    next_version(label, result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', choices=tuple(BINARIES), required=True)
    parser.add_argument('--owned-root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--full-independent')
    parser.add_argument('--full-independent-sha256')
    parser.add_argument('--preceding', action='append', default=[])
    args = parser.parse_args()
    root = Path(args.owned_root)
    need(root.parent == Path('/dev/shm') and root.name.startswith('actions-rcc-compatibility-actual-')
         and not root.exists() and not root.is_symlink(), 'CONSTRUCTOR_ONCE_ROOT')
    need(not Path(args.output).exists(), 'CONSTRUCTOR_ONCE_OUTPUT')
    source_binding = bind(SOURCE_OWNER, SOURCE_OWNER_SHA)
    light_binding = bind(LIGHT_REVIEW, LIGHT_REVIEW_SHA)
    full_binding = bind(FULL_OWNER, FULL_OWNER_SHA)
    acquisition_binding = bind(ACQUISITION, ACQUISITION_SHA)
    copies_binding = bind(APPROVED_COPIES, APPROVED_COPIES_SHA)
    owner = parse_json_object(SOURCE_OWNER.read_bytes())
    need(owner['source']['head'] == SOURCE and owner['source']['tree'] == TREE, 'CONSTRUCTOR_SOURCE')
    refs = {r['path']: bind(r['path'], r['sha256']) for r in owner['frozen_bindings']}
    acquisition = parse_json_object(ACQUISITION.read_bytes())
    for row in acquisition['bindings']:
        refs[row['path']] = bind(row['path'], row['sha256'])
    for row in [source_binding, light_binding, full_binding, acquisition_binding, copies_binding]:
        refs[row['path']] = row
    if args.full_independent:
        need(args.full_independent_sha256 is not None, 'FULL_REVIEW_HASH_REQUIRED')
        full_review = bind(args.full_independent, args.full_independent_sha256)
        refs[full_review['path']] = full_review
    else:
        full_review = {'path': None, 'bytes': None, 'sha256': None, 'mode': None}
    for p in args.preceding:
        refs[str(Path(p))] = bind(p)
    for name in ('actual_transport_v5.py', 'fixture_records_v2.py', 'owned_monitor_v1.py',
                 'runner_contracts_v3.py', 'build_actual_config_v3.py', 'gateway_entry_v1.py', 'managed_metadata_only_preflight.py'):
        p = Path(__file__).with_name(name)
        refs[str(p)] = bind(p)
    prepared_path = SOURCE_OWNER.parent / 'own-Bootstrap-reuse-inputs-and-origins.json'
    prepared = parse_json_object(prepared_path.read_bytes())
    need(len(prepared['inputs_exact_prepared_git_bytes_sha256']) == 30
         and len(prepared['own5actual_prefix_and_source_origin_assertions']) == 5, 'CONSTRUCTOR_PREPARED')
    committed = parse_json_object(Path(owner['complete_committed_body_mode_proof']['path']).read_bytes())
    need(committed['head'] == SOURCE and committed['tree'] == TREE, 'CONSTRUCTOR_COMMITTED_SUBJECT')
    rows = []
    source_root = Path('/workspace/engineering/pr308')
    for path, row in committed['complete1421_Git_FS_body_mode_exact'].items():
        p = source_root / path
        raw = os.readlink(p).encode() if row['mode'] == '120000' else p.read_bytes()
        need(len(raw) == row['bytes'] and content_sha(raw) == row['sha256'], 'CONSTRUCTOR_COMMITTED_BYTES')
        rows.append({'path': path, 'mode': row['mode'], 'sha256': row['sha256'],
                     'fs_mode': stat.S_IMODE(p.lstat().st_mode)})
    retained = parse_json_object((SOURCE_OWNER.parent / 'after-source-retained-native-helper-browser-and-V5-proof.json').read_bytes())
    native_proposal = parse_json_object(Path(retained['immutable_proposal']['path']).read_bytes())
    inventory = json.loads(Path(retained['original_inventory']['path']).read_bytes())
    need(type(inventory) is list and len(inventory) == 1192, 'CONSTRUCTOR_NATIVE1192')
    for key in ('immutable_proposal', 'original_inventory', 'original_manifest', 'original_assets_zip',
                'original_frozen_executable', 'browser', 'historical_V5_checkpoint', 'historical_V5_independent_review'):
        row = retained[key]
        refs[row['path']] = bind(row['path'], row['sha256'])
    for pair in retained['frozen_helper_original_and_snapshot_bindings'].values():
        for key in ('original', 'snapshot'):
            row = pair[key]; refs[row['path']] = bind(row['path'], row['sha256'])
    literal_path = Path(__file__).with_name('frozen-b614-literal-fixture-expected-inventory.json')
    literal = parse_json_object(literal_path.read_bytes())
    refs[str(literal_path)] = bind(literal_path)
    path, sha, selector, version = BINARIES[args.label]
    refs[path] = bind(path, sha)
    python = '/workspace/engineering/pr308/action_server/.venv/bin/python'
    fixture_expected = {'source': {'commit': SOURCE, 'tree': TREE},
                        'control': {'commit': CONTROL, 'tree': CONTROL_TREE},
                        'rcc': {'version': version, 'sha256': sha},
                        'compatibility': compatibility(args.label),
                        'fixture_inventory': literal['fixture_inventory'],
                        'fixture_source_sha256': literal['fixture_source_sha256']}
    value = {'schema': 1, 'source': SOURCE, 'tree': TREE, 'control': CONTROL, 'control_tree': CONTROL_TREE,
             'source_FULL': full_binding, 'source_independent': light_binding, 'source_FULL_independent': full_review,
             'source_root': str(source_root), 'python': python, 'own_runtime_prefix': str(source_root / 'action_server/.venv'),
             'prepared_inputs': prepared['inputs_exact_prepared_git_bytes_sha256'],
             'concrete_own_origins': prepared['own5actual_prefix_and_source_origin_assertions'],
             'budgets': [600, 10, 645, 660, 10], 'selectors': list(SELECTORS), 'owned_root': str(root),
             'preceding': predecessor_rows(args.preceding, args.label), 'preceding_original_bindings': [bind(p) for p in args.preceding],
             'binary': {'path': path, 'sha256': sha, 'selector': selector, 'version': version},
             'bindings': list(refs.values()), 'source_body_modes': rows,
             'native_original_root': str(Path(native_proposal['native']['layout']) / 'dist/action-server'),
             'native_original_members': inventory, 'fixture_expected': fixture_expected,
             'actual_status': 'NOT_RUN', 'launch_disposition': 'ROOT_RELEASE_AND_REVIEW_REQUIRED' if args.full_independent else 'SOURCE_FULL_INDEPENDENT_MISSING_HOLD'}
    fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps(bind(args.output), sort_keys=True))


if __name__ == '__main__':
    main()
