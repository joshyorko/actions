import ast
import base64
import csv
import email.parser
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

OWNED = Path('/workspace/engineering/pr221-current302-linux-wheel-owned')
REPO = Path('/workspace/engineering/pr302')
SOURCE = 'd642a3ac24f8da85101538bdfdf59b509fd74bfb'
CONTROL = 'a346fd7dfca7a6490e6968d16c809a85814ff5b0'
BUILD = 'f5dd0e18d9cda660c2eaa6bbc33a11180ddd7158'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])

def safe_members(z):
    infos = z.infolist()
    names = [i.filename for i in infos]
    assert len(names) == len(set(names))
    for i in infos:
        name = i.filename
        parts = PurePosixPath(name).parts
        assert name and not name.startswith('/') and '\\' not in name and '\x00' not in name
        assert ':' not in name and all(p not in ('.', '..') for p in parts)
        assert str(PurePosixPath(name)) == name.rstrip('/')
        mode = i.external_attr >> 16
        assert not stat.S_ISLNK(mode)
        assert not i.flag_bits & 1
    return infos

raw = OWNED / 'original-Linux-wheels-11693813383.zip'
assert raw.stat().st_size == 28271148
assert digest(raw.read_bytes()) == '32485758f22e51b529d3ea657c4f4c0033233f6c84ec7d3d605c4493c11d82c6'
assert raw.stat().st_mode & 0o777 == 0o600
pyproject = git('show', SOURCE + ':action_server/pyproject.toml')
poetry = tomllib.loads(pyproject.decode('utf-8'))['tool']['poetry']
expected_name, expected_version = poetry['name'], poetry['version']
assert (expected_name, expected_version) == ('actions-runtime', '1.0.3')
assert pyproject == git('show', CONTROL + ':action_server/pyproject.toml')
authenticated = json.loads((OWNED / 'authenticated-source-artifact-metadata.json').read_text())
assert authenticated['control']['sha'] == CONTROL and authenticated['synthetic']['sha'] == BUILD
assert authenticated['control']['tree'] == authenticated['synthetic']['tree']
assert git('rev-parse', CONTROL + '^{tree}').decode().strip() == authenticated['control']['tree']
with zipfile.ZipFile(raw) as outer:
    outer_infos = safe_members(outer)
    assert len(outer_infos) == 2
    archive_inventory = []
    selected = None
    for i in outer_infos:
        body = outer.read(i)  # CRC verified while decoding, never extracted wholesale.
        archive_inventory.append({'path': i.filename, 'bytes': len(body), 'compressed_bytes': i.compress_size, 'sha256': digest(body), 'crc32': i.CRC})
        if '-cp312-cp312-' in i.filename:
            assert selected is None
            selected = (i.filename, body)
    assert selected is not None

wheel_name, wheel_body = selected
wheel_path = OWNED / wheel_name
if not wheel_path.exists():
    with os.fdopen(os.open(wheel_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as stream:
        stream.write(wheel_body)
assert wheel_path.read_bytes() == wheel_body and wheel_path.stat().st_mode & 0o777 == 0o600
assert digest(wheel_body) == 'f82ee06c09e07bd224e797e11b7e58138920c0c8df49ef814ac50b0087d81c6c'
with zipfile.ZipFile(io.BytesIO(wheel_body)) as wheel:
    infos = safe_members(wheel)
    payload = {i.filename: wheel.read(i) for i in infos if not i.is_dir()}
    assert len(payload) == len(infos)
    inventory = [{'path': i.filename, 'bytes': len(payload[i.filename]), 'sha256': digest(payload[i.filename]), 'crc32': i.CRC} for i in infos]
    metadata_names = [p for p in payload if p.endswith('.dist-info/METADATA')]
    assert len(metadata_names) == 1
    info_root = metadata_names[0].rsplit('/', 1)[0]
    assert info_root == 'actions_runtime-1.0.3.dist-info'
    msg = email.parser.BytesParser().parsebytes(payload[metadata_names[0]])
    assert msg.get_all('Name') == [expected_name] and msg.get_all('Version') == [expected_version]
    assert wheel_name.startswith('actions_runtime-' + expected_version + '-cp312-cp312-')
    wheel_meta = email.parser.BytesParser().parsebytes(payload[info_root + '/WHEEL'])
    tags = wheel_meta.get_all('Tag')
    assert tags and all(tag.startswith('cp312-cp312-manylinux') for tag in tags)
    assert wheel_meta.get_all('Root-Is-Purelib') == ['false']
    record_name = info_root + '/RECORD'
    rows = list(csv.reader(io.StringIO(payload[record_name].decode('utf-8'))))
    assert all(len(row) == 3 for row in rows)
    assert len({row[0] for row in rows}) == len(rows)
    assert {row[0] for row in rows} == set(payload)
    hash_count = 0
    for path, hash_field, length in rows:
        if path == record_name:
            assert hash_field == length == ''
            continue
        assert hash_field.startswith('sha256=') and length.isdigit()
        assert int(length) == len(payload[path])
        canonical = base64.urlsafe_b64encode(hashlib.sha256(payload[path]).digest()).decode('ascii').rstrip('=')
        assert hash_field == 'sha256=' + canonical
        hash_count += 1
    oauth_name = 'actions/server/_oauth2_config.py'
    oauth_body = payload[oauth_name]
    oauth_tree = ast.parse(oauth_body.decode('utf-8'))
    assert len(oauth_tree.body) == 1 and isinstance(oauth_tree.body[0], ast.Assign)
    assignment = oauth_tree.body[0]
    assert len(assignment.targets) == 1 and isinstance(assignment.targets[0], ast.Name) and assignment.targets[0].id == 'FILE_CONTENTS'
    assert isinstance(assignment.value, ast.Dict)
    oauth_fields = []
    for key, value in zip(assignment.value.keys, assignment.value.values):
        assert isinstance(key, ast.Constant) and key.value in ('actions_config', 'default_user_config')
        assert isinstance(value, ast.Constant) and isinstance(value.value, str)
        literal = value.value.encode('utf-8')
        oauth_fields.append({'fixed_field': key.value, 'category': 'EMPTY_STRING' if not literal else 'NONEMPTY_STRING_UNQUALIFIED', 'utf8_bytes': len(literal), 'characters': len(value.value), 'sha256': digest(literal)})
    assert {f['fixed_field'] for f in oauth_fields} == {'actions_config', 'default_user_config'}
    tracked = {}
    for row in git('ls-tree', '-rz', SOURCE).split(b'\0'):
        if row:
            meta, name = row.split(b'\t', 1)
            tracked[name.decode()] = meta.decode().split()
    matches, differences, untracked = [], [], []
    for path, data in payload.items():
        if not path.startswith('actions/'):
            continue
        source_path = 'action_server/src/' + path
        if source_path in tracked:
            source_bytes = git('show', SOURCE + ':' + source_path)
            row = {'member': path, 'source_path': source_path, 'source_blob': tracked[source_path][2], 'source_sha256': digest(source_bytes), 'member_sha256': digest(data)}
            (matches if source_bytes == data else differences).append(row)
        else:
            untracked.append({'member': path, 'sha256': digest(data), 'bytes': len(data), 'category': 'GENERATED_OR_PACKAGED_INPUT_NOT_TRACKED_AT_SPRIME'})

root_receipt_path = Path('/workspace/engineering/pr302-next-publisher-metadata-readback/safe-next-publisher-and-build-metadata-checkpoint.json')
root_receipt = json.loads(root_receipt_path.read_text())
assert digest(root_receipt_path.read_bytes()) == 'd17834004efe0121e171492db4017942aafa9eed1cddd3c308f22c945777e6ca'
log_binding = next(x for x in root_receipt['completed_builder_log_observations'] if x['job'] == 114409246244)['original_log_private']
log_path = Path(log_binding['path'])
log_body = log_path.read_bytes()
assert len(log_body) == log_binding['bytes'] and digest(log_body) == log_binding['sha256']
assert BUILD.encode() in log_body and CONTROL.encode() in log_body
workflow = git('show', CONTROL + ':.github/workflows/actions_runtime_pypi_release.yml')  # Authenticated synthetic tree equals control tree.
task_source = git('show', SOURCE + ':action_server/tasks.py')
assert b'Build OAuth2 config (PR)' in workflow and b'inv build-oauth2-config' in workflow
tree = ast.parse(task_source.decode('utf-8'))
builder = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'build_oauth2_config')
runs = [x for x in ast.walk(builder) if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and isinstance(x.func.value, ast.Name) and x.func.value.id == 'subprocess' and x.func.attr == 'run']
assert len(runs) == 2
checked = [any(k.arg == 'check' and isinstance(k.value, ast.Constant) and k.value.value is True for k in x.keywords) for x in runs]
result = {'schema': 'actions-current-linux-wheel-stdlib-inspection/v1', 'status': 'PASS_ARCHIVE_METADATA_RECORD_INTEGRITY; HOLD_GENERATED_OAUTH_AUTHORITY_CONTENT_AND_RELEASE', 'tuple': root_receipt['tuple'], 'candidate_disposition': 'PR302 prospective candidate C-prime/S-prime/synthetic build; NOT current PR221/integration774 wheel. Root has not integrated302; source identity never relabeled', 'synthetic_source_body_binding': 'Local full synthetic tree unavailable; authenticated Git API records synthetic treea1c4 equal control treea1c4, and local control tree matches; source bodies read at full control identity', 'authorized_artifact': {'id': 11693813383, 'run': 38118859475, 'job': 114409246244, 'path_private': str(raw), 'bytes': raw.stat().st_size, 'sha256': digest(raw.read_bytes()), 'mode': '0600', 'download_count': 1}, 'archive_checks': {'complete_member_count': len(outer_infos), 'duplicates': 0, 'unsafe_paths': 0, 'symlinks': 0, 'encrypted_members': 0, 'all_member_crc_and_original_byte_digests': True, 'inventory': archive_inventory}, 'selected_wheel': {'private_path': str(wheel_path), 'filename': wheel_name, 'bytes': len(wheel_body), 'sha256': digest(wheel_body), 'member_count': len(infos), 'all_member_inventory': inventory, 'central_directory_duplicates_unsafe_paths_symlinks_encrypted': 0, 'all_member_crc_checked': True, 'expected_source_name': expected_name, 'expected_source_version': expected_version, 'source_pyproject_sha256': digest(pyproject), 'METADATA_Name': msg['Name'], 'METADATA_Version': msg['Version'], 'metadata_sha256': digest(payload[metadata_names[0]]), 'wheel_tag_count': len(tags), 'wheel_tags': tags, 'purelib': False, 'record_entries': len(rows), 'record_sha256_size_verified_entries': hash_count, 'record_unhashed_entries': [record_name], 'record_sha256': digest(payload[record_name])}, 'generated_oauth_member': {'path': oauth_name, 'bytes': len(oauth_body), 'sha256': digest(oauth_body), 'AST_only_never_executed': True, 'fixed_assignment': 'FILE_CONTENTS', 'fixed_fields': oauth_fields, 'required_payload_both_current_measured_empty': all(f['category'] == 'EMPTY_STRING' for f in oauth_fields), 'authority_and_provider_config_policy': 'UNQUALIFIED; no approved input pair/revisions/digests authenticated; historical empty1.0.2 is not a fallback', 'record_match_scope': 'RECORD integrity authenticates measured empty-member bytes within this original wheel; it does not qualify generator input authority or completeness'}, 'partial_source_member_comparison': {'tracked_payload_member_matches': len(matches), 'tracked_payload_member_differences': len(differences), 'untracked_generated_or_packaged_members': len(untracked), 'matches': matches, 'differences': differences, 'untracked': untracked, 'scope': 'Selected wheel member correspondence only; not complete producer-input/native/whole source qualification'}, 'build_source_bindings': {'original_completed_Linux_log': log_binding, 'log_reacquired': False, 'workflow_sha256': digest(workflow), 'tasks_source_sha256': digest(task_source), 'source_build_config_subprocess_call_count': len(runs), 'subprocess_checked_flags': checked, 'generator_source_scope': 'Source observes stdout decoding and unchecked subprocess calls; current artifact empty values are measured separately. Exact failed acquisition/root cause is not attributed here.'}, 'qualification_limits': ['No wheel install, import/execution, consumer cold acquisition or dependency resolution', 'No registry publication or officialRuntime1.0.3 validation', 'No new RCC/native/browser/provider execution or installer', 'Other OS/architectures and cp313 inner wheel not qualified', 'Full producer/generated-input authority, private/full134/fullrelease remain HOLD'], 'upstream_disposition': 'none'}
output = OWNED / 'safe-current-linux-wheel-inspection.json'
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'receipt': str(output), 'sha256': digest(output.read_bytes()), 'bytes': output.stat().st_size, 'archive_members': len(outer_infos), 'wheel_members': len(infos), 'record_verified': hash_count, 'source_matches': len(matches), 'source_differences': len(differences), 'untracked_packaged': len(untracked), 'oauth_fields': oauth_fields, 'status': result['status']}))
