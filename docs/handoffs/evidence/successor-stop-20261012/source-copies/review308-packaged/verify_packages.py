"""Read-only OAuth package/source verification for the immutable PR307 tuple."""
import ast
import base64
import csv
import hashlib
import io
import json
import pathlib
import stat
import subprocess
import tarfile
import zipfile
from email.parser import BytesParser

import yaml

ROOT = pathlib.Path('/workspace/actions-pr308')
ARTIFACTS = pathlib.Path('/workspace/successor-evidence/pr308-packaged')
OUT = pathlib.Path('/workspace/successor-evidence/review308-packaged')
HEAD = 'fe1bdee3d5014d39a763d088535c29d65b38315d'
PAIR = [('actions_config', 'actions-oauth-config.yaml'), ('default_user_config', 'oauth-config.yaml')]
OAUTH_SOURCES = ['_oauth2.py', '_api_oauth2.py', '_common/oauth2_settings.py', 'vendored_deps/oauth2_settings.py']


def sha(body):
    return hashlib.sha256(body).hexdigest()


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git_body(relative):
    return subprocess.check_output(['git', 'show', HEAD + ':' + relative], cwd=ROOT)


def check_names(names):
    assert len(names) == len(set(names)), 'Duplicate archive paths'
    for name in names:
        path = pathlib.PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts and '\\' not in name, name


def bundle(body, windows=False):
    tree = ast.parse(body)
    assert len(tree.body) == 2
    values = {}
    for node in tree.body:
        assert isinstance(node, ast.Assign) and len(node.targets) == 1
        assert isinstance(node.targets[0], ast.Name)
        values[node.targets[0].id] = ast.literal_eval(node.value)
    assert set(values) == {'FILE_CONTENTS', 'INPUT_SHA256'}
    assert set(values['FILE_CONTENTS']) == {key for key, name in PAIR}
    assert set(values['INPUT_SHA256']) == {name for key, name in PAIR}
    result = []
    for key, name in PAIR:
        blob = git_body('action_server/oauth2/' + name)
        expected = blob.replace(b'\n', b'\r\n') if windows else blob
        actual = values['FILE_CONTENTS'][key].encode('utf-8')
        assert actual == expected
        assert values['INPUT_SHA256'][name] == sha(actual)
        assert yaml.safe_load(actual) == {'formatVersion': '1.0.0', 'oauth2Config': {'providers': {}}}
        result.append({'name': name, 'git_blob_sha256': sha(blob), 'packaged_input_sha256': sha(actual), 'checkout_conversion': 'LF-to-CRLF' if windows else 'none', 'exact_git_blob_bytes': actual == blob})
    return result


metadata = json.loads((OUT / 'github-metadata.json').read_text())
artifact = metadata['artifacts'][0]
archive = ARTIFACTS / 'download-connector-verified.zip'
assert archive.stat().st_size == artifact['size_in_bytes']
assert 'sha256:' + file_sha(archive) == artifact['digest']
assert artifact['id'] == 11725299041 and not artifact['expired']
assert artifact['workflow_run']['head_sha'] == HEAD
manifest = {}
for line in (ARTIFACTS / 'actions-runtime-manifest.sha256').read_text().splitlines():
    digest, name = line.split('  ')
    assert name not in manifest
    manifest[name] = digest
assert len(manifest) == 7
with zipfile.ZipFile(archive) as aggregate:
    check_names(aggregate.namelist())
    assert set(aggregate.namelist()) == set(manifest) | {'actions-runtime-manifest.sha256'}
    for name in aggregate.namelist():
        with aggregate.open(name) as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        assert digest == file_sha(ARTIFACTS / name)
        if name in manifest:
            assert digest == manifest[name]

tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', HEAD, '--', 'action_server/src/actions/server'], cwd=ROOT, text=True).splitlines()
source_files = {name.removeprefix('action_server/src/'): name for name in tracked if name.endswith('.py')}
members = []
for name in manifest:
    path = ARTIFACTS / name
    if name.endswith('.whl'):
        with zipfile.ZipFile(path) as wheel:
            check_names(wheel.namelist())
            for info in wheel.infolist():
                assert stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG, stat.S_IFDIR), info.filename
            record_name = next(n for n in wheel.namelist() if n.endswith('.dist-info/RECORD'))
            rows = list(csv.reader(io.StringIO(wheel.read(record_name).decode())))
            assert len(rows) == len({r[0] for r in rows})
            assert {r[0] for r in rows} == {info.filename for info in wheel.infolist() if not info.is_dir()}
            for entry, digest, size in rows:
                if entry == record_name:
                    assert not digest and not size
                    continue
                assert digest.startswith('sha256=')
                with wheel.open(entry) as stream:
                    measured = hashlib.file_digest(stream, 'sha256').digest()
                assert base64.urlsafe_b64encode(measured).rstrip(b'=').decode() == digest.split('=', 1)[1]
                assert int(size) == wheel.getinfo(entry).file_size
            info_name = next(n for n in wheel.namelist() if n.endswith('.dist-info/METADATA'))
            package_metadata = BytesParser().parsebytes(wheel.read(info_name))
            assert package_metadata['Name'] == 'actions-runtime' and package_metadata['Version'] == '1.0.3'
            requires = package_metadata.get_all('Requires-Dist')
            assert not any(' @ ' in req for req in requires)
            for relative in OAUTH_SOURCES:
                assert wheel.read('actions/server/' + relative) == git_body('action_server/src/actions/server/' + relative)
            present_sources = [member for member in wheel.namelist() if member in source_files]
            assert set(present_sources) == set(source_files), 'Missing tracked runtime Python member'
            for member in present_sources:
                assert wheel.read(member) == git_body(source_files[member]), member
            unknown_python = [member for member in wheel.namelist() if member.endswith('.py') and member.startswith('actions/server/') and member not in source_files]
            assert set(unknown_python) == {'actions/server/_oauth2_config.py'}, unknown_python
            public_inputs = bundle(wheel.read('actions/server/_oauth2_config.py'), 'win_amd64' in name)
            members.append({'file': name, 'sha256': manifest[name], 'size': path.stat().st_size, 'record_entries_verified': len(rows), 'tracked_runtime_python_files_exact': len(present_sources), 'generated_python_files': unknown_python, 'oauth_source_exact': True, 'public_inputs': public_inputs, 'requires_dist': requires})
    else:
        with tarfile.open(path) as sdist:
            all_members = sdist.getmembers()
            check_names([m.name for m in all_members])
            assert all(m.isfile() or m.isdir() for m in all_members)
            prefix = 'actions_runtime-1.0.3/'
            def read(relative):
                return sdist.extractfile(prefix + relative).read()
            for relative in OAUTH_SOURCES:
                assert read('src/actions/server/' + relative) == git_body('action_server/src/actions/server/' + relative)
            for key, input_name in PAIR:
                assert read('oauth2/' + input_name) == git_body('action_server/oauth2/' + input_name)
            for relative in ('build.py', 'pyproject.toml'):
                assert read(relative) == git_body('action_server/' + relative)
            public_inputs = bundle(read('src/actions/server/_oauth2_config.py'))
            members.append({'file': name, 'sha256': manifest[name], 'size': path.stat().st_size, 'oauth_source_inputs_build_py_pyproject_exact': True, 'public_inputs': public_inputs, 'builder_script_distributed': any(m.name.endswith('scripts/build_oauth2_config.py') for m in all_members), 'note': 'sdist contains exact pre-generated OAuth bundle; build.py performs RCC acquisition and does not regenerate it'})
receipt = {'accepted_source_head': HEAD, 'accepted_source_tree': 'c0371a7a0fa113be56199f260029ee1c09f63d1a', 'artifact_id': artifact['id'], 'run_id': artifact['workflow_run']['id'], 'archive_sha256': file_sha(archive), 'archive_size': archive.stat().st_size, 'scope': 'OAuth package/source/resource provenance and wheel RECORD integrity; no native execution or publication', 'members': members}
(OUT / 'independent-package-verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'artifact_sha256': receipt['archive_sha256'], 'distributions': len(members), 'each_wheel_tracked_runtime_python_files': [m.get('tracked_runtime_python_files_exact') for m in members if m['file'].endswith('.whl')], 'oauth_inputs_all_exact_expected_checkout_bytes': True, 'windows_input_hashes_preserve_crlf_provenance': True, 'all_archive_manifest_record_checks_pass': True}, indent=2))
