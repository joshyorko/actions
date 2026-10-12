"""Data-only original archive inspection; never import or execute package members."""
import ast
import base64
import configparser
import csv
import email.parser
import hashlib
import io
import gzip
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
SOURCE = 'e2c81adce7858d5a952991ba9a8b7f72e902038a'
TREE = 'afe2679cc93bf27fa5021c7698ee7ad3ee21a1b9'
ZIP_PATH = Path('/tmp/actions-pr221-e2-aggregate-11708952448-one-owned/actions-runtime-dist-11708952448-original.zip')
OUT = Path('/workspace/engineering/root-current-e2-one-inner-data-inspection-owned-v2')
RELEASE = Path('/workspace/engineering/root-current-e2-one-inner-data-inspection-release-v2.json')
MANIFEST = ROOT / 'frozen-executor-inputs.json'
MANIFEST_SHA = 'f1bae88f9cee392f6623ac6f4c3c500bea65bd39c246df0dec002c4dc7911b9a'
OUTPUT_CAP = 8 * 1024 * 1024
written = 0
CURRENT_INNER = None

def digest(b):
    return hashlib.sha256(b).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args], stderr=subprocess.PIPE, timeout=10)

def binding(path):
    path = Path(path)
    s = path.lstat()
    assert stat.S_ISREG(s.st_mode) and not path.is_symlink()
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return {'path': str(path), 'bytes': s.st_size, 'sha256': h.hexdigest(), 'mode': oct(stat.S_IMODE(s.st_mode))}

def verify_bindings(cfg):
    for row in cfg['bindings']:
        assert binding(row['path']) == row
    assert git('rev-parse', SOURCE + '^{tree}').decode().strip() == TREE
    entries = {}
    for row in git('ls-tree', '-rz', SOURCE, '--', 'action_server/src/actions').split(b'\0'):
        if row:
            head, name = row.split(b'\t', 1)
            mode, kind, oid = head.decode().split()
            entries[name.decode()] = (mode, kind, oid)
    expected = cfg['source_expectations']['rows']
    assert len(entries) == len(expected) == 217
    assert sum(r['path'].endswith('.py') for r in expected) == 202
    for row in expected:
        assert entries[row['path']] == (row['mode'], row['kind'], row['oid'])
        body = git('cat-file', row['kind'], row['oid'])
        assert len(body) == row['bytes'] and digest(body) == row['sha256']

def write(name, value):
    global written
    data = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    assert written + len(data) <= OUTPUT_CAP
    fd = os.open(OUT / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    written += len(data)
    return binding(OUT / name)

def immutable_inner_reference(name, data):
    assert CURRENT_INNER is not None and CURRENT_INNER['member'] == name
    assert len(data) == CURRENT_INNER['bytes'] and digest(data) == CURRENT_INNER['sha256']
    return dict(CURRENT_INNER)

def validate_package(package, comparison, platform):
    assert comparison['tracked_source_files_absent_from_archive'] == []
    generated = {r['git_path'] for r in comparison['comparisons'] if 'classification' in r}
    oauth = 'action_server/src/actions/server/_oauth2_config.py'
    rcc = 'action_server/src/actions/server/bin/rcc-18.19.3' + ('.exe' if platform == 'Windows' else '')
    assert generated == ({oauth} if platform == 'sdist' else {oauth, rcc})
    assert len(package) == (218 if platform == 'sdist' else 219)
    assert sum(n.endswith('.py') for n in package) == 203

def safe_path(name):
    assert name and not name.startswith('/') and '\\' not in name and '\0' not in name and ':' not in name
    p = PurePosixPath(name)
    assert '..' not in p.parts and '.' not in p.parts and str(p) == name.rstrip('/')

def zip_payload(z):
    infos = z.infolist()
    assert len(infos) <= 5000 and len({i.filename for i in infos}) == len(infos)
    assert len({i.filename.casefold() for i in infos}) == len(infos)
    assert sum(i.file_size for i in infos) <= 128 * 1024 * 1024
    # Admit the complete header set before reading any payload.
    for i in infos:
        safe_path(i.filename)
        mode = i.external_attr >> 16
        assert stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR) and not (i.flag_bits & 1)
        assert not i.is_dir() or i.file_size == 0
        assert stat.S_IFMT(mode) != stat.S_IFDIR or i.is_dir()
        assert i.file_size <= 64 * 1024 * 1024
    inventory, payload = [], {}
    for i in infos:
        safe_path(i.filename)
        mode = i.external_attr >> 16
        assert stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR) and not (i.flag_bits & 1)
        assert not i.is_dir() or i.file_size == 0
        assert stat.S_IFMT(mode) != stat.S_IFDIR or i.is_dir()
        assert i.file_size <= 64 * 1024 * 1024
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

def static_categories(body):
    tree = ast.parse(body.decode())
    assignments = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'FILE_CONTENTS' for t in n.targets)]
    assert len(assignments) == 1 and isinstance(assignments[0].value, ast.Dict)
    value = ast.literal_eval(assignments[0].value)
    assert set(value) == {'index.html'}
    assert all(isinstance(v, (str, bytes)) for v in value.values())
    return {k: {'category': 'EMPTY_CONTENT_AUTHORITY_HOLD' if not v else 'NONEMPTY_AUTHORITY_HOLD',
                'bytes': len(v.encode() if isinstance(v, str) else v),
                'sha256': digest(v.encode() if isinstance(v, str) else v)} for k, v in value.items()}

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
    assert len(data) <= 64 * 1024 * 1024
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        inv, payload = zip_payload(z)
    roots = [n[:-len('METADATA')] for n in payload if n.endswith('.dist-info/METADATA')]
    assert len(roots) == 1 and roots[0] == 'actions_runtime-1.0.3.dist-info/'
    root = roots[0]
    assert {n for n in payload if n.startswith(root)} == {root + n for n in ('METADATA', 'WHEEL', 'entry_points.txt', 'RECORD')}
    assert all(n.startswith(('actions/', root)) for n in payload)
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
    validate_package(package, comparison, platform)
    categories = oauth_categories(payload['actions/server/_oauth2_config.py'][0])
    preserve = immutable_inner_reference(name, data)
    return {'file': preserve, 'platform': platform, 'python_abi': cp, 'metadata': metadata,
            'wheel_tags': wh.get_all('Tag'), 'entrypoints': dict(ep['console_scripts']),
            'record': {'rows': len(rows), 'hashed_rows': sum(bool(r[1]) for r in rows), 'all_member_hash_size_verified': True, 'self_unhashed_only': True},
            'inventory': inv, 'package_member_count': len(package),
            'package_python_member_count': sum(n.endswith('.py') for n in package),
            'package_nonpython_member_count': sum(not n.endswith('.py') for n in package),
            'other_payload_member_count': len(payload) - len(package),
            'source_comparison': comparison, 'generated_oauth_categories': categories,
            'generated_static_assets': static_categories(payload['actions/server/_static_contents.py'][0]),
            'tracked_html': {'bytes': len(payload['actions/server/index.html'][0]), 'sha256': digest(payload['actions/server/index.html'][0]), 'authority': 'HOLD'},
            'generated_input_authority': 'HOLD', 'install_import_consumer_execution': 'NOT_RUN'}

def inspect_sdist(name, data):
    assert name == 'actions_runtime-1.0.3.tar.gz'
    inv, payload = [], {}
    assert len(data) <= 64 * 1024 * 1024
    seen, total = set(), 0
    with gzip.GzipFile(fileobj=io.BytesIO(data), mode='rb') as gz:
        expanded = gz.read(128 * 1024 * 1024 + 1)
        assert len(expanded) <= 128 * 1024 * 1024
        assert gz.read(1) == b''  # Force complete gzip CRC/ISIZE/EOF validation.
    with tarfile.open(fileobj=io.BytesIO(expanded), mode='r:') as t:
        for m in t:
            assert len(seen) < 5000
            safe_path(m.name)
            assert m.name.casefold() not in seen
            seen.add(m.name.casefold())
            assert m.name == 'actions_runtime-1.0.3' or m.name.startswith('actions_runtime-1.0.3/')
            assert m.isfile() or m.isdir(), 'sdist link or special member'
            assert 0 <= m.size <= 64 * 1024 * 1024
            total += m.size
            assert total <= 128 * 1024 * 1024
            assert not m.isdir() or m.size == 0
            b = t.extractfile(m).read() if m.isfile() else b''  # Memory-only read; no filesystem extraction.
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
    package = {n: p for n, p in payload.items() if n.startswith(prefix + 'src/actions/')}
    validate_package(package, comparison, 'sdist')
    categories = oauth_categories(payload[prefix + 'src/actions/server/_oauth2_config.py'][0])
    return {'file': immutable_inner_reference(name, data), 'inventory': inv, 'metadata': metadata,
            'source_pyproject_equal': True, 'source_comparison': comparison,
            'embedded_rcc_member_count': 0, 'generated_oauth_categories': categories,
            'generated_static_assets': static_categories(payload[prefix + 'src/actions/server/_static_contents.py'][0]),
            'tracked_html': {'bytes': len(payload[prefix + 'src/actions/server/index.html'][0]), 'sha256': digest(payload[prefix + 'src/actions/server/index.html'][0]), 'authority': 'HOLD'},
            'generated_input_authority': 'HOLD', 'build_install_execution': 'NOT_RUN'}

def configure_source():
    global POETRY, EXPECTED_DEPS, GIT_FILES
    POETRY = tomllib.loads(git('show', SOURCE + ':action_server/pyproject.toml').decode())['tool']['poetry']
    EXPECTED_DEPS = {}
    for name, value in POETRY['dependencies'].items():
        if name != 'python':
            spec = value if isinstance(value, str) else value['version']
            extras = [] if isinstance(value, str) else value.get('extras', [])
            EXPECTED_DEPS[canonical_name(name)] = {'extras': sorted(extras), 'constraints': constraints(spec)}
    GIT_FILES = {}
    for entry in git('ls-tree', '-rz', SOURCE).split(b'\0'):
        if entry:
            head, name = entry.split(b'\t', 1)
            mode, kind, oid = head.decode().split()
            GIT_FILES[name.decode()] = (mode, kind, oid)


def inspect_current(cfg):
    global CURRENT_INNER
    configure_source()
    expected_outer = cfg['outer_inventory']
    expected_names = {r['name'] for r in expected_outer}
    reports = []
    with zipfile.ZipFile(ZIP_PATH) as outer:
        infos = outer.infolist()
        assert len(infos) == len(expected_names) == 8
        assert {i.filename for i in infos} == expected_names
        assert sum(i.file_size for i in infos) <= 128 * 1024 * 1024
        for row in expected_outer:
            name = row['name']
            i = outer.getinfo(name)
            assert not i.is_dir() and not (i.flag_bits & 1)
            assert i.file_size <= 64 * 1024 * 1024
            data = outer.read(i)
            assert len(data) == row['bytes'] and digest(data) == row['sha256']
            if not (name.endswith('.whl') or name.endswith('.tar.gz')):
                continue
            CURRENT_INNER = {'outer_original': cfg['zip_binding'], 'member': name, 'bytes': len(data), 'sha256': digest(data), 'filesystem_extraction': 'NOT_RUN'}
            if name.endswith('.whl'):
                platform = 'Linux' if 'manylinux' in name else 'Windows' if 'win_amd64' in name else 'Mac'
                report = inspect_wheel(name, data, platform)
                assert report['record']['rows'] == 223 and report['record']['hashed_rows'] == 222
                assert report['other_payload_member_count'] == 4
            else:
                report = inspect_sdist(name, data)
            reports.append(write('private-' + name + '-inspection.json', report))
            del data, report
    assert len(reports) == 7
    return reports


def execution_environment_admission():
    import sys
    if sys.flags.optimize != 0 or 'PYTHONOPTIMIZE' in os.environ:
        raise RuntimeError('UNOPTIMIZED_INTERPRETER_REQUIRED')


def read_private_root_release(path):
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode) or path.is_symlink() or stat.S_IMODE(s.st_mode) != 0o600:
        raise RuntimeError('PRIVATE_REGULAR_ROOT_RELEASE_REQUIRED')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as f:
        current = os.fstat(f.fileno())
        if (current.st_dev, current.st_ino, current.st_mode) != (s.st_dev, s.st_ino, s.st_mode):
            raise RuntimeError('ROOT_RELEASE_IDENTITY_CHANGED')
        value = json.loads(f.read(64 * 1024 + 1))
    if not isinstance(value, dict):
        raise RuntimeError('ROOT_RELEASE_OBJECT_REQUIRED')
    return value


def main():
    import signal, resource, sys
    execution_environment_admission()
    assert sys.argv[1:] == ['--execute-root-reviewed-one-inner-inspection']
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('bounded data-only inspection deadline')))
    signal.alarm(110)
    manifest_bytes = MANIFEST.read_bytes()
    assert digest(manifest_bytes) == MANIFEST_SHA
    cfg = json.loads(manifest_bytes)
    assert cfg['source_expectations']['source'] == SOURCE
    assert cfg['source_expectations']['tree'] == TREE
    assert cfg['zip_binding']['bytes'] == 80745614
    assert cfg['zip_binding']['sha256'] == 'e16a414fefc1778ba49d09c466fd9d8054cfbf952e7766ee5cc6558f871f4def'
    assert cfg['zip_binding']['path'] == str(ZIP_PATH)
    assert json.loads(Path(cfg['outer_independent']['path']).read_bytes())['decision'] == 'GO_CURRENT_E2_ORIGINAL_EXISTING_FILE_OUTER_DATA_INTEGRITY_ONLY'
    assert json.loads(Path(cfg['outer_result']['path']).read_bytes())['status'] == 'PASS_ORIGINAL_E2_AGGREGATE_OUTER_DATA_ONLY'
    verify_bindings(cfg)
    auth = read_private_root_release(RELEASE)
    assert auth['schema'] == 'ROOT_ONE_CURRENT_E2_INNER_DATA_INSPECTION'
    assert auth['execute'] is True
    assert binding(auth['proposal_binding']['path']) == auth['proposal_binding']
    owner = json.loads(Path(auth['proposal_binding']['path']).read_bytes())
    assert owner['executor_binding'] == binding(__file__)
    assert owner['manifest_binding'] == binding(MANIFEST)
    indrow = auth['independent_review_binding']
    assert binding(indrow['path']) == indrow
    ind = json.loads(Path(indrow['path']).read_bytes())
    assert ind['decision'] == 'GO_CURRENT_E2_INNER_DATA_INSPECTION_PREEXECUTION'
    assert ind['proposal_binding'] == auth['proposal_binding']
    assert not OUT.exists()
    OUT.mkdir(mode=0o700)
    write('consumed-one-root-release.json', auth)
    primary = None
    result = {'status': 'FAILED', 'source': SOURCE, 'tree': TREE, 'scope': 'DATA_ONLY_CURRENT_AGGREGATE_INNER_INTEGRITY', 'remaining_holds': ['generated OAuth authority', 'generated frontend source/producer authority', 'other-platform producer checkout', 'install/consumer/native/private/release/publication']}
    try:
        result['reports'] = inspect_current(cfg)
        result['status'] = 'PASS_STRUCTURAL_INNER_INTEGRITY_WITH_CONTENT_AUTHORITY_HOLDS'
    except BaseException as exc:
        primary = exc
        result['primary_exception_type'] = type(exc).__name__
    finally:
        try:
            verify_bindings(cfg)
            assert binding(__file__) == owner['executor_binding']
            assert binding(MANIFEST) == owner['manifest_binding']
            result['protected_post'] = 'PASS'
        except BaseException as secondary:
            result['status'] = 'FAILED'
            result['protected_post'] = 'FAILED'
            result['secondary_exception_type'] = type(secondary).__name__
            if primary is not None:
                primary.add_note('Independent input postcondition also failed: ' + type(secondary).__name__)
            else:
                primary = secondary
        try:
            write('OWNERFINAL-one-current-e2-inner-data-inspection-result.json', result)
        except BaseException as output_error:
            if primary is not None:
                primary.add_note('Final receipt persistence also failed: ' + type(output_error).__name__)
            else:
                primary = output_error
        signal.alarm(0)
    if primary is not None:
        raise primary

if __name__ == '__main__':
    main()
