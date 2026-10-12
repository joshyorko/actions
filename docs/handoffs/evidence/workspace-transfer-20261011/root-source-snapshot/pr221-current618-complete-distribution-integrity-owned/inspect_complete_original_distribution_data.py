"""Data-only original archive inspection; never import or execute package members."""
import ast
import base64
import configparser
import csv
import email.parser
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
REPO = Path('/workspace/actions')
SOURCE = '6181b044c75de35386f1ae30e71725398b6a7feb'
BUILD = 'e7666eacf2687f65050b97a88e791f8d0ce4cd20'
BASE = 'a70993fafc99a9f94041485542d5a720797ca394'
TREE = '99ac5309add45af65049546dd3a99f357884cf3b'
META = {
    11697353355: ('Linux-wheels', 28299039, 'fc4018e6e7ed4a0e47c4f5888d36d55655216ca22ebd965f29ce9f1130938f8c', 114433293243),
    11697788053: ('Windows-wheels', 23201552, 'f6c1d0e41ba6a1f8651c7a93ca7f76e4c17c3305e30b2c2e347724b0fc272273', 114433293117),
    11697522927: ('action-server-dist', 1020782, '30b0020ac0dcbea840627a5cfff4c9a8c6be95d89cd319953b51f5d9d1139a5a', 114433293201),
}

def digest(b):
    return hashlib.sha256(b).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args], stderr=subprocess.PIPE)

def write(name, data):
    b = data if isinstance(data, bytes) else (json.dumps(data, indent=2, sort_keys=True) + '\n').encode()
    fd = os.open(ROOT / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(b)
    return {'path': str(ROOT / name), 'bytes': len(b), 'sha256': digest(b)}

def safe_path(name):
    assert name and not name.startswith('/') and '\\' not in name and '\0' not in name and ':' not in name
    p = PurePosixPath(name)
    assert '..' not in p.parts and '.' not in p.parts and str(p) == name.rstrip('/')

def zip_payload(z):
    infos = z.infolist()
    assert len(infos) <= 5000 and len({i.filename for i in infos}) == len(infos)
    assert sum(i.file_size for i in infos) <= 512 * 1024 * 1024
    inventory, payload = [], {}
    for i in infos:
        safe_path(i.filename)
        mode = i.external_attr >> 16
        assert not stat.S_ISLNK(mode) and not (i.flag_bits & 1)
        assert i.file_size <= 128 * 1024 * 1024
        body = z.read(i)  # zipfile checks every member's original CRC.
        assert len(body) == i.file_size
        inventory.append({'path': i.filename, 'bytes': len(body), 'sha256': digest(body),
                          'crc32': f'{i.CRC:08x}', 'unix_mode': oct(mode),
                          'mode_available': i.create_system == 3, 'create_system': i.create_system,
                          'directory': i.is_dir()})
        if not i.is_dir():
            payload[i.filename] = (body, mode, i.create_system)
    return inventory, payload

def norm_version(v):
    parts = [int(i) for i in v.split('.')]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)

def constraints(value):
    if value.startswith('^'):
        v = value[1:]
        p = [int(i) for i in v.split('.')]
        index = next((i for i, n in enumerate(p) if n), len(p) - 1)
        upper = p[:index + 1]
        upper[-1] += 1
        value = '>=' + v + ',<' + '.'.join(map(str, upper))
    elif re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', value):
        value = '==' + value
    result = []
    for term in value.split(','):
        m = re.fullmatch(r'(>=|<=|==|!=|>|<)\s*([0-9]+(?:\.[0-9]+)*)', term.strip())
        assert m, 'unsupported dependency expression'
        result.append((m.group(1), norm_version(m.group(2))))
    return sorted(result)

def canonical_name(name):
    return re.sub(r'[-_.]+', '-', name).lower()

POETRY = tomllib.loads(git('show', SOURCE + ':action_server/pyproject.toml').decode())['tool']['poetry']
EXPECTED_DEPS = {}
for name, value in POETRY['dependencies'].items():
    if name == 'python':
        continue
    spec = value if isinstance(value, str) else value['version']
    extras = [] if isinstance(value, str) else value.get('extras', [])
    EXPECTED_DEPS[canonical_name(name)] = {'extras': sorted(extras), 'constraints': constraints(spec)}

GIT_FILES = {}
for entry in git('ls-tree', '-rz', SOURCE).split(b'\0'):
    if not entry:
        continue
    header, path = entry.split(b'\t', 1)
    mode, kind, blob = header.decode().split()
    GIT_FILES[path.decode()] = (mode, kind, blob)

def source_compare(payload, prefix, git_prefix):
    comparisons = []
    for name, (body, mode, system) in sorted(payload.items()):
        if not name.startswith(prefix):
            continue
        source_path = git_prefix + name[len(prefix):]
        entry = GIT_FILES.get(source_path)
        row = {'archive_path': name, 'git_path': source_path, 'archive_bytes': len(body),
               'archive_sha256': digest(body), 'archive_permission_mode': oct(mode & 0o777),
               'archive_unix_mode_available': system == 3}
        if entry:
            gm, kind, blob = entry
            original = git('cat-file', kind, blob)
            row.update({'git_mode': gm, 'git_blob': blob, 'git_bytes': len(original),
                        'git_sha256': digest(original), 'body_equal': body == original,
                        'executable_bit_equal': bool(mode & 0o111) == (gm == '100755') if system == 3 else None})
        else:
            row['classification'] = 'UNTRACKED_GENERATED_OR_PACKAGED_MEMBER'
        comparisons.append(row)
    expected = {p for p in GIT_FILES if p.startswith(git_prefix)}
    present = {r['git_path'] for r in comparisons if 'git_blob' in r}
    return {'comparisons': comparisons, 'tracked_source_files_absent_from_archive': sorted(expected - present),
            'body_equal_count': sum(r.get('body_equal') is True for r in comparisons),
            'body_difference_count': sum(r.get('body_equal') is False for r in comparisons),
            'untracked_packaged_count': sum('classification' in r for r in comparisons)}

def oauth_categories(body):
    tree = ast.parse(body.decode())
    assignments = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'FILE_CONTENTS' for t in n.targets)]
    assert len(assignments) == 1 and isinstance(assignments[0].value, ast.Dict)
    value = ast.literal_eval(assignments[0].value)
    assert set(value) == {'actions_config', 'default_user_config'}
    assert all(isinstance(v, str) for v in value.values())
    return {k: {'category': 'EMPTY_STRING' if not v else 'NONEMPTY_UNQUALIFIED',
                'utf8_bytes': len(v.encode()), 'sha256': digest(v.encode())} for k, v in sorted(value.items())}

def inspect_metadata(body):
    m = email.parser.BytesParser().parsebytes(body)
    assert m.get_all('Name') == [POETRY['name']] and m.get_all('Version') == [POETRY['version']]
    assert constraints(m['Requires-Python']) == constraints(POETRY['dependencies']['python'])
    actual = {}
    for dep in m.get_all('Requires-Dist', []):
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)(?:\[([^\]]+)\])?\s+\(([^)]+)\)', dep)
        assert match, 'unexpected dependency or marker'
        name, extras, spec = match.groups()
        name = canonical_name(name)
        assert name not in actual
        actual[name] = {'extras': sorted(extras.split(',')) if extras else [], 'constraints': constraints(spec)}
    assert actual == EXPECTED_DEPS
    return {'name': m['Name'], 'version': m['Version'], 'requires_python': m['Requires-Python'],
            'requires_dist': m.get_all('Requires-Dist', []), 'source_dependency_constraints_equal': True,
            'metadata_sha256': digest(body)}

def inspect_wheel(name, data, platform):
    assert len(data) <= 128 * 1024 * 1024
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        inv, payload = zip_payload(z)
    roots = [n[:-len('METADATA')] for n in payload if n.endswith('.dist-info/METADATA')]
    assert len(roots) == 1 and roots[0] == 'actions_runtime-1.0.3.dist-info/'
    root = roots[0]
    metadata = inspect_metadata(payload[root + 'METADATA'][0])
    wh = email.parser.BytesParser().parsebytes(payload[root + 'WHEEL'][0])
    assert wh['Root-Is-Purelib'] == 'false'
    cp = re.search(r'-(cp31[23])-\1-', name).group(1)
    platforms = ['manylinux_2_5_x86_64', 'manylinux1_x86_64', 'manylinux_2_17_x86_64', 'manylinux2014_x86_64'] if platform == 'Linux' else ['win_amd64'] if platform == 'Windows' else ['macosx_12_0_arm64']
    assert wh.get_all('Tag') == [cp + '-' + cp + '-' + p for p in platforms]
    parsed = name.removesuffix('.whl').split('-')
    assert parsed == ['actions_runtime', '1.0.3', cp, cp, '.'.join(platforms)]
    ep = configparser.ConfigParser()
    ep.read_string(payload[root + 'entry_points.txt'][0].decode())
    assert ep.sections() == ['console_scripts'] and dict(ep['console_scripts']) == POETRY['scripts']
    rows = list(csv.reader(io.StringIO(payload[root + 'RECORD'][0].decode())))
    assert all(len(r) == 3 for r in rows) and len({r[0] for r in rows}) == len(rows)
    assert set(r[0] for r in rows) == set(payload)
    for path, encoded, size in rows:
        if path == root + 'RECORD':
            assert encoded == size == ''
        else:
            body = payload[path][0]
            assert encoded == 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode().rstrip('=')
            assert size == str(len(body))
    package = {n: p for n, p in payload.items() if n.startswith('actions/')}
    comparison = source_compare(package, '', 'action_server/src/')
    categories = oauth_categories(payload['actions/server/_oauth2_config.py'][0])
    preserve = immutable_inner_reference(name, data)
    return {'file': preserve, 'platform': platform, 'python_abi': cp, 'metadata': metadata,
            'wheel_tags': wh.get_all('Tag'), 'entrypoints': dict(ep['console_scripts']),
            'record': {'rows': len(rows), 'all_member_hash_size_verified': True, 'self_unhashed_only': True},
            'inventory': inv, 'package_member_count': len(package),
            'package_python_member_count': sum(n.endswith('.py') for n in package),
            'package_nonpython_member_count': sum(not n.endswith('.py') for n in package),
            'other_payload_member_count': len(payload) - len(package),
            'source_comparison': comparison, 'generated_oauth_categories': categories,
            'generated_input_authority': 'HOLD', 'install_import_consumer_execution': 'NOT_RUN'}

def inspect_sdist(name, data):
    assert name == 'actions_runtime-1.0.3.tar.gz'
    inv, payload = [], {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as t:
        members = t.getmembers()
        assert len(members) <= 5000 and len({m.name for m in members}) == len(members)
        assert sum(m.size for m in members) <= 512 * 1024 * 1024
        for m in members:
            safe_path(m.name)
            assert m.name == 'actions_runtime-1.0.3' or m.name.startswith('actions_runtime-1.0.3/')
            assert m.isfile() or m.isdir(), 'sdist link or special member'
            assert m.size <= 128 * 1024 * 1024
            b = t.extractfile(m).read() if m.isfile() else b''
            assert len(b) == m.size
            inv.append({'path': m.name, 'bytes': m.size, 'sha256': digest(b), 'mode': oct(m.mode),
                        'uid': m.uid, 'gid': m.gid, 'directory': m.isdir()})
            if m.isfile():
                payload[m.name] = (b, m.mode, 3)
    prefix = 'actions_runtime-1.0.3/'
    metadata = inspect_metadata(payload[prefix + 'PKG-INFO'][0])
    project = tomllib.loads(payload[prefix + 'pyproject.toml'][0].decode())['tool']['poetry']
    assert project == POETRY
    comparison = source_compare(payload, prefix + 'src/', 'action_server/src/')
    assert not any('/bin/rcc' in n for n in payload)
    categories = oauth_categories(payload[prefix + 'src/actions/server/_oauth2_config.py'][0])
    return {'file': immutable_inner_reference(name, data), 'inventory': inv, 'metadata': metadata,
            'source_pyproject_equal': True, 'source_comparison': comparison,
            'embedded_rcc_member_count': 0, 'generated_oauth_categories': categories,
            'generated_input_authority': 'HOLD', 'build_install_execution': 'NOT_RUN'}

OLD = Path('/workspace/engineering/pr221-current618-wheel-integrity-owned')
PARTIAL_OWNER = OLD / 'OWNERFINAL-current618-partial-distribution-integrity-v2.json'
CI_OWNER = Path('/workspace/engineering/pr221-current618-terminal-CI-and-artifact-metadata-successor/OWNERFINAL-current618-terminal-CI-artifact-metadata.json')
TRACE_OWNER = Path('/workspace/engineering/pr221-current618-static-frontend-trace-owned/OWNERFINAL-windows-static-and-complete-checkout-diagnosis-v2.json')

def binding(path):
    body = path.read_bytes()
    return {'path': str(path), 'bytes': len(body), 'sha256': digest(body)}

owners = [(PARTIAL_OWNER, '9b406fdf505871e6790d7a4233d0b8c075ae6f170f2c5b7a954bbca0f0d46236'),
          (CI_OWNER, '1cfbc1df13a1df43558271df7ed413e40c45a474644e25a912504a61fcca665e'),
          (TRACE_OWNER, '0839a2ba6ee40b9b2e244f399496158e4775e5bbe1bd3fcc3d6056bbbf51c683')]
unchanged_owner_bindings = []
for path, sha in owners:
    assert digest(path.read_bytes()) == sha
    previous = json.loads(path.read_text())
    for entry in previous['evidence']:
        assert binding(Path(entry['path'])) == entry
    unchanged_owner_bindings.append({'owner': binding(path), 'all_existing_bindings_unchanged': len(previous['evidence'])})

previous_inspection = json.loads((OLD / 'safe-data-only-integrity-inspection.json').read_text())
existing_inners = {Path(w['file']['path']).name: w['file'] for w in previous_inspection['wheels']}
existing_inners[Path(previous_inspection['sdist']['file']['path']).name] = previous_inspection['sdist']['file']

def immutable_inner_reference(name, body):
    if name in existing_inners:
        entry = existing_inners[name]
        assert len(body) == entry['bytes'] and digest(body) == entry['sha256']
        assert binding(Path(entry['path'])) == entry
        return dict(entry)
    return write(name, body)

assert git('rev-parse', SOURCE + '^{tree}').decode().strip() == TREE
ci = json.loads(CI_OWNER.read_text())
assert ci['synthetic'] == {'sha': BUILD, 'ordered_parents': [BASE, SOURCE], 'tree': TREE}
assert ci['actual_integration_Git']['sha'] == SOURCE and ci['actual_integration_Git']['tree'] == TREE

all_distributions = {}
platform_sources = [
    (11697353355, 'Linux', OLD / 'original-11697353355.zip', 28299039, 'fc4018e6e7ed4a0e47c4f5888d36d55655216ca22ebd965f29ce9f1130938f8c'),
    (11697788053, 'Windows', OLD / 'original-11697788053.zip', 23201552, 'f6c1d0e41ba6a1f8651c7a93ca7f76e4c17c3305e30b2c2e347724b0fc272273'),
    (11697522927, 'sdist', OLD / 'original-11697522927.zip', 1020782, '30b0020ac0dcbea840627a5cfff4c9a8c6be95d89cd319953b51f5d9d1139a5a'),
    (11698787320, 'macOS', ROOT / 'original-11698787320.zip', 26440059, '4ea0a96e1d9144db5b5ad900fabeae5db5b8737845e2582053d27e017b18ca79'),
]
report = {'schema': 'complete-original-seven-runtime-distribution-data-inspection-v1',
          'actual_integration_source': SOURCE, 'actual_integration_Git': ci['actual_integration_Git'],
          'producer_checkout': BUILD, 'producer_ordered_parents': [BASE, SOURCE], 'producer_tree': TREE,
          'run_id': 38126987514, 'unchanged_previous_owner_receipts': unchanged_owner_bindings,
          'original_platform_archives': [], 'wheels': [], 'sdist': None}
for aid, platform, path, size, sha in platform_sources:
    body = path.read_bytes()
    assert len(body) == size and digest(body) == sha
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        inventory, payload = zip_payload(z)
    assert len(payload) == (1 if platform == 'sdist' else 2)
    report['original_platform_archives'].append({'id': aid, 'platform': platform, 'file': binding(path),
                                                'inventory': inventory, 'CRC_complete': True,
                                                'acquired_in_this_successor': platform == 'macOS'})
    for name, (data, _, _) in sorted(payload.items()):
        assert name not in all_distributions
        all_distributions[name] = data
        if platform == 'sdist':
            report['sdist'] = inspect_sdist(name, data)
        else:
            row = inspect_wheel(name, data, platform)
            for comp in row['source_comparison']['comparisons']:
                if 'git_mode' in comp:
                    comp['Git_permission_bits_equal'] = int(comp['archive_permission_mode'], 8) == int(comp['git_mode'][-3:], 8) if comp['archive_unix_mode_available'] else None
            package_binary = next(i for i in row['inventory'] if i['path'].startswith('actions/server/bin/rcc-'))
            row['packaged_generated_RCC'] = {'public_path': package_binary['path'], 'bytes': package_binary['bytes'],
                                             'sha256': package_binary['sha256'], 'mode': package_binary['unix_mode'],
                                             'version_execution_or_native_qualification': 'NOT_RUN'}
            row['generated_static_source_comparison'] = next(c for c in row['source_comparison']['comparisons'] if c['archive_path'] == 'actions/server/_static_contents.py')
            report['wheels'].append(row)

assert len(all_distributions) == 7 and len(report['wheels']) == 6
assert {(w['platform'], w['python_abi']) for w in report['wheels']} == {(p, a) for p in ('Linux', 'Windows', 'macOS') for a in ('cp312', 'cp313')}
assert all(w['package_python_member_count'] == 202 and w['package_nonpython_member_count'] == 15 for w in report['wheels'])
assert all(w['source_comparison']['body_equal_count'] + w['source_comparison']['body_difference_count'] == 215 for w in report['wheels'])

aggregate_path = ROOT / 'original-11698838081.zip'
agg = aggregate_path.read_bytes()
assert len(agg) == 78961912 and digest(agg) == 'ceecae3505dea985f0d023223056ad45d15ab53973dbd6893f71819d8720e279'
with zipfile.ZipFile(io.BytesIO(agg)) as z:
    agg_inventory, agg_payload = zip_payload(z)
manifest_name = 'actions-runtime-manifest.sha256'
assert set(agg_payload) == set(all_distributions) | {manifest_name}
assert len(agg_payload) == 8
equality = []
for name, body in sorted(all_distributions.items()):
    aggregate_body = agg_payload[name][0]
    assert body == aggregate_body
    equality.append({'public_filename': name, 'bytes': len(body), 'sha256': digest(body),
                     'original_platform_vs_aggregate_body_equal': True})

publisher_path = 'action_server/scripts/publish_verified_runtime.py'
publisher = git('show', SOURCE + ':' + publisher_path)
pt = ast.parse(publisher.decode())
constant = next(n for n in pt.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MANIFEST_NAME' for t in n.targets))
assert ast.literal_eval(constant.value) == manifest_name
fn = next(n for n in pt.body if isinstance(n, ast.FunctionDef) and n.name == 'write_manifest')
assert fn.lineno == 128 and fn.end_lineno == 136
literal_nodes = [n.value for n in ast.walk(fn) if isinstance(n, ast.Constant)]
assert '  ' in literal_nodes and '\n' in literal_nodes
assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'sorted' for n in ast.walk(fn))
assert any(isinstance(n, ast.Attribute) and n.attr == 'name' for n in ast.walk(fn))
assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'sha256_file' for n in ast.walk(fn))
manifest = agg_payload[manifest_name][0]
expected_manifest = ''.join(digest(body) + '  ' + name + '\n' for name, body in sorted(all_distributions.items())).encode()
assert manifest == expected_manifest
assert len(manifest.decode().splitlines()) == 7
manifest_file = write(manifest_name, manifest)
publisher_snapshot = write('source-publish_verified_runtime.private.py', publisher)
report['aggregate'] = {'id': 11698838081, 'file': binding(aggregate_path), 'original_outer_member_count': len(agg_inventory),
                       'outer_member_inventory': agg_inventory, 'CRC_complete': True,
                       'distribution_member_count': 7, 'distribution_member_set_equal_original_four_platform_archives': True,
                       'distribution_body_equality': equality,
                       'separately_typed_publisher_generated_manifest': {'file': manifest_file, 'original_filename': manifest_name,
                                                                      'lines': 7, 'SHA256_double_space_filename_LF_format': True,
                                                                      'entire_body_equal_source_defined_sorted_original_digests': True,
                                                                      'publisher_source': publisher_path, 'publisher_source_snapshot': publisher_snapshot,
                                                                      'manifest_name_source_line': constant.lineno, 'write_manifest_source_lines': [fn.lineno, fn.end_lineno],
                                                                      'source_function_execution': 'NOT_RUN'}}

mac_log = ROOT / 'job-114433293230-original.private.log'
lines = mac_log.read_text().splitlines()
checkout = []
floor = []
for i, line in enumerate(lines):
    if 'git' in line and 'log -1' in line and '--format' in line:
        for j in range(i + 1, min(i + 4, len(lines))):
            if BUILD in re.findall(r'\b[0-9a-f]{40}\b', lines[j]):
                checkout.append({'git_log_command_line': i + 1, 'checkout_SHA_line': j + 1, 'checkout': BUILD})
                break
    marker = 'Verified uncached PyPI Runtime dependency artifacts: '
    if marker in line:
        values = json.loads(line.split(marker, 1)[1])
        fixed = {k: {'version': v.get('version'), 'sha256': v.get('sha256')} for k, v in values.items()}
        assert fixed == {'actions-core': {'version': '1.0.2', 'sha256': '9d527edf540978172178894546add75f117f240786aec804cb75c308615a7e80'},
                         'actions-http-helper': {'version': '1.0.3', 'sha256': '46ed7ce0e0d3e2e05456d937b5b24bc9dfa0d7d4b98f8119b9fdf00d4fa7e9f9'}}
        floor.append({'line': i + 1, 'allowlisted_package_versions_and_digests': fixed})
assert len(checkout) == len(floor) == 1
report['new_original_Mac_builder_log'] = {'job_id': 114433293230, 'file': binding(mac_log), 'checkout_observations': checkout,
                                         'original_completed_SUCCESS_metadata_authority': binding(CI_OWNER),
                                         'existing_builder_cp312_published_floor_marker': floor,
                                         'scope': 'EXISTING_BUILD_CP312_CORE1.0.2_HELPER1.0.3_SAMPLE_NOT_NEW_CONSUMER_OR_CP313_FLOOR',
                                         'original_decoded_content_scope': 'EXACT_CONNECTOR_DECODED_TEXT_UTF8; NOT_ORIGINAL_COMPRESSED_LOG_ARCHIVE_BYTES'}
report['old_original_builder_logs_reused_unchanged'] = ci['original_producer_logs_already_owned']
report['source_checkout_vs_actual_integration'] = 'Originalbuilder e766 remains synthetic a709+618; tree equality does not relabel it actualintegration618.'
report['remaining_holds'] = ['Windows173Python+5nonPythonCRLF_body_differences', 'Windows_generated_static_13CR_content_difference',
                            'Windows_Unix_mode_unavailable', 'generated_OAuth_empty_source_content_authority',
                            'current_platform_installed_consumers', 'native_browser_provider_Homebrew_private_backend_registry_tag_release_graph']
report['content_semantic_equivalence_or_waiver'] = 'NOT_ESTABLISHED_NOT_ALLOWED'
report['historical_Windows_input_checkout_cause'] = 'UNKNOWN'
report['new_acquisitions'] = {'artifact_ids': [11698787320, 11698838081], 'job_log_ids': [114433293230],
                             'one_each': True, 'retries': 0, 'old_three_ZIP_or_log_reacquisition': False,
                             'prior_owned_exact_ID_filename_search': 'NO_MATCH'}
report['read_only_scope'] = {'package_import_install_source_build': False, 'consumer': False,
                             'native_browser_provider_registry_tag_merge_issue_close': False, 'source_changes': False,
                             'metadata_repoll': False, 'raw_member_payload_URL_config_log_forwarded': False}
result = write('safe-complete-original-seven-distribution-inspection.json', report)
print(json.dumps({'report': result, 'seven_distributions_verified': len(all_distributions),
                  'aggregate_original_outer_members': len(agg_inventory),
                  'wheel_tracked_source_body_counts': [{'platform': w['platform'], 'ABI': w['python_abi'],
                                                        'equal': w['source_comparison']['body_equal_count'],
                                                        'different': w['source_comparison']['body_difference_count']} for w in report['wheels']],
                  'release': 'HOLD'}))

