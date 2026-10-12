"""Read-only admission of one retained cp312 wheel; never install/import payloads."""
import ast
import base64
import csv
import hashlib
import io
import json
import stat
import subprocess
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath


def digest(data):
    return hashlib.sha256(data).hexdigest()


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


def validate_payload(payload):
    """Retain original inspector's strict METADATA/RECORD predicates."""
    metadata_paths = [p for p in payload if p.endswith('.dist-info/METADATA')]
    assert metadata_paths == ['actions_runtime-1.0.3.dist-info/METADATA']
    root = 'actions_runtime-1.0.3.dist-info'
    metadata = BytesParser().parsebytes(payload[metadata_paths[0]])
    assert metadata.get_all('Name') == ['actions-runtime']
    assert metadata.get_all('Version') == ['1.0.3']
    wheel = BytesParser().parsebytes(payload[root + '/WHEEL'])
    tags = wheel.get_all('Tag')
    assert tags and all(tag.startswith('cp312-cp312-manylinux') for tag in tags)
    assert wheel.get_all('Root-Is-Purelib') == ['false']
    record_name = root + '/RECORD'
    rows = list(csv.reader(io.StringIO(payload[record_name].decode('utf-8'))))
    assert all(len(row) == 3 for row in rows)
    assert len({row[0] for row in rows}) == len(rows)
    assert {row[0] for row in rows} == set(payload)
    verified = 0
    for path, hash_field, length in rows:
        if path == record_name:
            assert hash_field == length == ''
            continue
        assert hash_field.startswith('sha256=') and length.isdigit()
        assert int(length) == len(payload[path])
        canonical = base64.urlsafe_b64encode(hashlib.sha256(payload[path]).digest()).decode('ascii').rstrip('=')
        assert hash_field == 'sha256=' + canonical
        verified += 1
    return {'record_entries': len(rows), 'record_verified_entries': verified,
            'record_sha256': digest(payload[record_name]),
            'python_member_count': sum(p.endswith('.py') for p in payload)}


def admit(archive_path, wheel_path, manifest, repository):
    original = manifest['original_archive']
    body = archive_path.read_bytes()
    assert len(body) == original['bytes'] and digest(body) == original['sha256']
    expected_outer = {r['path']: r for r in manifest['outer_inventory']}
    with zipfile.ZipFile(io.BytesIO(body)) as outer:
        infos = safe_members(outer)
        assert len(infos) == len(expected_outer) == 2
        assert {i.filename for i in infos} == set(expected_outer)
        for info in infos:
            data = outer.read(info)
            expected = expected_outer[info.filename]
            assert len(data) == expected['bytes'] and digest(data) == expected['sha256']
            if info.filename == wheel_path.name:
                assert data == wheel_path.read_bytes()
    expected_wheel = manifest['original_selected_wheel']
    assert wheel_path.name == expected_wheel['filename']
    data = wheel_path.read_bytes()
    assert len(data) == expected_wheel['bytes'] and digest(data) == expected_wheel['sha256']
    with zipfile.ZipFile(io.BytesIO(data)) as wheel:
        infos = safe_members(wheel)
        assert len(infos) == expected_wheel['member_count']
        payload = {i.filename: wheel.read(i) for i in infos if not i.is_dir()}
        expected_inventory = {r['path']: r for r in expected_wheel['all_member_inventory']}
        assert {i.filename for i in infos} == set(expected_inventory)
        for info in infos:
            row = expected_inventory[info.filename]
            assert row['kind'] == ('directory' if info.is_dir() else 'file')
            member = wheel.read(info)
            assert len(member) == row['bytes'] and digest(member) == row['sha256']
    receipt = validate_payload(payload)
    assert receipt['record_entries'] == expected_wheel['record_entries'] == 215
    assert receipt['record_verified_entries'] == expected_wheel['record_sha256_size_verified_entries'] == 214
    assert receipt['record_sha256'] == expected_wheel['record_sha256']
    assert receipt['python_member_count'] == sum(r['kind'] == 'file' and r['path'].endswith('.py') for r in expected_wheel['all_member_inventory'])
    actual = manifest['actual_integration']
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repository), *args])
    assert git('rev-parse', actual['sha'] + '^{tree}').decode().strip() == actual['tree']
    assert git('show', '-s', '--format=%P', actual['sha']).decode().split() == actual['ordered_parents']
    assert manifest['producer_tuple']['control_tree'] == actual['tree']
    assert manifest['producer_tuple']['synthetic_tree_equals_control'] is True
    tracked = {name.decode(): meta.decode().split() for row in git('ls-tree', '-rz', actual['sha']).split(b'\0') if row for meta, name in [row.split(b'\t', 1)]}
    bindings = manifest['tracked_member_bindings']
    assert len(bindings) == manifest['tracked_payload_count'] == 209
    assert len({r['member'] for r in bindings}) == len(bindings)
    for row in bindings:
        assert tracked[row['source_path']][2] == row['source_blob']
        source = git('cat-file', 'blob', row['source_blob'])
        assert source == payload[row['member']]
        assert digest(source) == row['source_sha256'] == row['member_sha256']
    oauth = manifest['oauth_member']
    assert digest(payload[oauth['path']]) == oauth['sha256']
    literal = ast.parse(payload[oauth['path']].decode('utf-8'))
    assert len(literal.body) == 1 and isinstance(literal.body[0], ast.Assign)
    assignment = literal.body[0]
    assert len(assignment.targets) == 1 and isinstance(assignment.targets[0], ast.Name) and assignment.targets[0].id == 'FILE_CONTENTS'
    contents = ast.literal_eval(assignment.value)
    assert contents == {'actions_config': '', 'default_user_config': ''}
    receipt.update({'tracked_payload_source_matches': 209,
                    'original_producer': manifest['producer_tuple'],
                    'actual_integration': actual,
                    'generated_oauth_content': 'EMPTY_CONTENT_AUTHORITY_HOLD',
                    'scope': 'Linuxcp312 input only; no seven-artifact/tag/publication/full-producer/native claim'})
    return receipt
