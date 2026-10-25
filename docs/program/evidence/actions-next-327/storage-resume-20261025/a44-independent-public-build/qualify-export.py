"""Qualify a newly built public dependency cache; never reads a prior archive."""
import ast
import email
import gzip
import hashlib
import io
import json
import posixpath
import runpy
import shutil
import zipfile
from pathlib import Path

CATALOGS = ('05bce139c5c902c0v12.linux_amd64', '4240e3dcbf7fa40dv12.linux_amd64')
FIXED_ROOT = Path('/tmp/actions327-a44-offline-v1/compiler')
CORE = '718ea63637f096d26c4de5f82ca736eec1358b197d0a63883c063ad205e0860e'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(root, tools):
    assert root == FIXED_ROOT
    expected = json.loads((tools / 'PUBLIC-DEPENDENCIES.json').read_text())
    assert sha(root / 'package.yaml') == expected['package_yaml_sha256']
    proof = json.loads((root / 'core-proof.json').read_text())
    assert proof['status'] == 'PASS' and proof['payload_members_verified'] == 87
    prefix = Path(proof['interpreter']).resolve().parent.parent
    assert prefix.parent == root / 'robocorp/holotree', 'Fresh target interpreter base required'
    conda = []
    for path in sorted((prefix / 'conda-meta').glob('*.json')):
        row = json.loads(path.read_text())
        conda.append({key: row[key] for key in ('name', 'version', 'build', 'url', 'sha256')})
    compare = lambda rows: sorted(rows, key=lambda row: row['name'])
    assert len(conda) == len(expected['conda']) == 26
    assert compare(conda) == compare(expected['conda']), 'Public conda identity drift'
    site = prefix / 'lib/python3.12/site-packages'
    python = []
    for path in sorted(site.glob('*.dist-info/METADATA')):
        raw = path.read_bytes()
        meta = email.message_from_bytes(raw)
        python.append({'name': meta['Name'], 'version': meta['Version'],
                       'installed_metadata_sha256': hashlib.sha256(raw).hexdigest()})
    fields = ('name', 'version', 'installed_metadata_sha256')
    expected_python = [{key: row[key] for key in fields} for row in expected['python']]
    assert len(python) == len(expected_python) == 19
    assert compare(python) == compare(expected_python), 'Python metadata identity drift'
    wheel = root / 'robocorp/wheels/actions_core-1.1.0a6-py3-none-any.whl'
    assert sha(wheel) == CORE
    with zipfile.ZipFile(wheel) as archive:
        members = [name for name in archive.namelist()
                   if not name.endswith('/') and '.dist-info/' not in name and '.data/' not in name]
        assert len(members) == 87
        for name in members:
            assert (site / name).read_bytes() == archive.read(name), 'Core payload mismatch'
    catalogs = root / 'robocorp/hololib/catalog'
    assert {p.name for p in catalogs.iterdir() if not p.name.endswith('.info')} == set(CATALOGS)
    checked = []
    for name in CATALOGS:
        with gzip.GzipFile(fileobj=io.BytesIO((catalogs / name).read_bytes())) as stream:
            raw = stream.read(8 * 1024**2 + 1)
        assert len(raw) <= 8 * 1024**2
        catalog = json.loads(raw)
        assert Path(catalog['path']).parent == root / 'robocorp/holotree'
        assert Path(catalog['path']).name == catalog['identity']
        assert catalog['platform'] == 'linux_amd64' and catalog['rcc'] == 'v18.19.3'
        links = 0
        def walk(node, prefix=''):
            nonlocal links
            for kind in ('files', 'subdirs'):
                for entry, value in node.get(kind, {}).items():
                    assert entry not in ('', '.', '..') and '/' not in entry and '\\' not in entry
                    assert value['name'] == entry
                    if kind == 'subdirs':
                        walk(value, prefix + entry + '/')
                    elif 'symlink' in value:
                        target = posixpath.normpath(posixpath.join(prefix, value['symlink']))
                        assert target != '..' and not target.startswith(('../', '/'))
                        links += 1
        walk(catalog['tree'])
        checked.append({'name': name, 'sha256': sha(catalogs / name),
                        'path': catalog['path'], 'links_checked': links})
    evidence = {'status': 'PASS', 'scope': 'this fresh build only; Python hashes identify METADATA, not wheels',
                'core_payload_members': 87, 'core_wheel_sha256': CORE,
                'public_manifest_sha256': sha(tools / 'PUBLIC-DEPENDENCIES.json'),
                'conda': conda, 'python': python, 'catalogs': checked}
    (root / 'independent-public-build-proof.json').write_text(json.dumps(evidence, indent=2) + '\n')
    return evidence


def finalize(root, export_root, tools, archive, evidence):
    digest = sha(archive)
    size = archive.stat().st_size
    validator = (tools / 'validate-public-cache.template.py').read_text()
    assert validator.count('REQUIRED_FRESH_ARCHIVE_SHA256') == 1
    validator = validator.replace('REQUIRED_FRESH_ARCHIVE_SHA256', digest).replace('SIZE=0', f'SIZE={size}')
    target = (tools / 'prepare-offline-managed.template.py').read_text()
    assert target.count('REQUIRED_FRESH_ARCHIVE_SHA256') == 1
    target = target.replace('REQUIRED_FRESH_ARCHIVE_SHA256', digest)
    ast.parse(validator)
    ast.parse(target)
    (export_root / 'validate-public-cache.py').write_text(validator)
    # Load only validator definitions; its __main__ import action does not run.
    validate = runpy.run_path(str(export_root / 'validate-public-cache.py'))['validate']
    inventory = validate(archive)
    (export_root / 'prepare-offline-managed.py').write_text(target)
    shutil.copyfile(tools / 'verify-core.py', export_root / 'verify-core.py')
    output = {'status': 'FRESH_EXPORT_VALIDATED', 'archive': archive.name,
              'archive_sha256': digest, 'archive_bytes': size,
              'source_public_manifest_sha256': evidence['public_manifest_sha256'],
              'producer_proof_sha256': sha(root / 'independent-public-build-proof.json'),
              'catalogs': inventory['catalogs'],
              'script_sha256': {name: sha(export_root / name) for name in
                               ('prepare-offline-managed.py', 'validate-public-cache.py', 'verify-core.py')},
              'target_status': 'NOT_RUN; fresh exact root and target-owned trust required'}
    (export_root / 'independent-export-manifest.json').write_text(json.dumps(output, indent=2) + '\n')
