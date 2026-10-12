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
    platforms = ['manylinux_2_5_x86_64', 'manylinux1_x86_64', 'manylinux_2_17_x86_64', 'manylinux2014_x86_64'] if platform == 'Linux' else ['win_amd64']
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
    preserve = write(name, data)
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
    return {'file': write(name, data), 'inventory': inv, 'metadata': metadata,
            'source_pyproject_equal': True, 'source_comparison': comparison,
            'embedded_rcc_member_count': 0, 'generated_oauth_categories': categories,
            'generated_input_authority': 'HOLD', 'build_install_execution': 'NOT_RUN'}

assert git('rev-parse', SOURCE + '^{tree}').decode().strip() == TREE
current_meta = Path('/workspace/engineering/pr221-current618-live-CI-reconciliation/frozen-live-CI-reconciliation.json')
assert digest(current_meta.read_bytes()) == '08f5897905fd121e828865dd0e0823881240f0785a3fc53d81801f5bad66bb46'
report = {'scope': 'DATA_ONLY_CURRENT618_PARTIAL_LINUX_WINDOWS_SDIST_INTEGRITY',
          'actual_integration_source': SOURCE, 'community_base': BASE,
          'producer_checkout': BUILD, 'producer_ordered_parents': [BASE, SOURCE],
          'producer_tree': TREE, 'integration_tree': TREE, 'run_id': 38126987514,
          'producer_tuple_authority': {'path': str(current_meta), 'sha256': digest(current_meta.read_bytes())},
          'artifacts': [], 'wheels': [], 'sdist': None, 'builder_logs': []}
for aid, (artifact_name, size, sha, job) in META.items():
    original = ROOT / f'original-{aid}.zip'
    data = original.read_bytes()
    assert len(data) == size and digest(data) == sha and stat.S_IMODE(original.stat().st_mode) == 0o600
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        inv, payload = zip_payload(z)
    assert len(payload) == (1 if aid == 11697522927 else 2)
    report['artifacts'].append({'id': aid, 'name': artifact_name, 'file': {'path': str(original), 'bytes': size, 'sha256': sha},
                                'job_id': job, 'original_member_crc_verified': True, 'inventory': inv})
    if aid == 11697522927:
        name, (body, _, _) = next(iter(payload.items()))
        report['sdist'] = inspect_sdist(name, body)
    else:
        platform = 'Linux' if aid == 11697353355 else 'Windows'
        for name, (body, _, _) in sorted(payload.items()):
            report['wheels'].append(inspect_wheel(name, body, platform))
    log = ROOT / f'job-{job}-original.private.log'
    log_bytes = log.read_bytes()
    lines = log_bytes.decode().splitlines()
    observations = []
    for i, line in enumerate(lines):
        if 'git' in line and 'log -1' in line and '--format' in line:
            for j in range(i + 1, min(i + 4, len(lines))):
                matches = re.findall(r'\b[0-9a-f]{40}\b', lines[j])
                if BUILD in matches:
                    observations.append({'git_log_command_line': i + 1, 'checkout_sha_line': j + 1, 'checkout': BUILD})
                    break
    assert len(observations) == 1
    stages = {'frontend_build': 'inv build-frontend', 'oauth_config_build': 'inv build-oauth2-config',
              'wheel_clean_test': 'python -m cibuildwheel', 'published_dependency_floor': 'python scripts/verify_published_runtime_floor.py',
              'sdist_build': 'poetry build -f sdist'}
    report['builder_logs'].append({'job_id': job, 'file': {'path': str(log), 'bytes': len(log_bytes), 'sha256': digest(log_bytes)},
                                   'checkout_observations': observations,
                                   'fixed_stage_command_observed': {k: v in log_bytes.decode() for k, v in stages.items()},
                                   'original_completed_success_metadata_authority': str(current_meta),
                                   'raw_log_forwarded': False})
assert len(report['wheels']) == 4
assert {(w['platform'], w['python_abi']) for w in report['wheels']} == {(p, c) for p in ('Linux', 'Windows') for c in ('cp312', 'cp313')}
report['remaining_holds'] = ['MACOS_CP312_CP313_AND_AGGREGATE_MISSING_AT_CAPTURE', 'FULL_SEVEN_PLATFORM_INVENTORY',
                            'GENERATED_OAUTH_SOURCE_AND_CONTENT_AUTHORITY', 'CURRENT_INSTALLED_PLATFORM_CONSUMERS_NOT_RUN',
                            'TAG_REGISTRY_PUBLICATION', 'NATIVE_BROWSER_PROVIDER_PRIVATE_BACKEND_RELEASE_GRAPH']
report['canonical_documentation'] = {'changed_source': False, 'accepted_reuse': ['9744b01f0f2f888de5f88f129b857df33938cb1adf182ec32b30ed08b2f14fe8', 'bf95da899763f97c016f76fa4a0cf8878ebba8326d57c11ab1a520b1df597c81'],
                                    'lesson': 'Original ZIP, wheel, METADATA, RECORD and synthetic build identities remain distinct from current integration and partial consumer/release acceptance.'}
report['upstream_disposition'] = 'none'
binding = write('safe-data-only-integrity-inspection.json', report)
print(json.dumps({'report': binding, 'wheel_count': len(report['wheels']),
                  'python_member_counts': [w['package_python_member_count'] for w in report['wheels']],
                  'oauth_categories': [w['generated_oauth_categories'] for w in report['wheels']],
                  'scope': report['scope'], 'remaining_holds': report['remaining_holds']}))
