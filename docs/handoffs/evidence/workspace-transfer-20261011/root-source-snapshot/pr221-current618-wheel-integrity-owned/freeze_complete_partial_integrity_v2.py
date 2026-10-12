"""Add complete sdist root-file provenance; retain the earlier construction checkpoint."""
import ast
import hashlib
import json
import os
import stat
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = '6181b044c75de35386f1ae30e71725398b6a7feb'

def digest(b):
    return hashlib.sha256(b).hexdigest()

def binding(p):
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': digest(b)}

def write(name, obj):
    p = ROOT / name
    b = (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode()
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(b)
    return binding(p)

parent = ROOT / 'frozen-current618-partial-distribution-integrity.json'
assert parent.stat().st_size == 10023
assert digest(parent.read_bytes()) == 'c7e3cdc23d519b52459853ffa1437bb2f563fcad9d18d332e69f4b7d066f3c29'
receipt = json.loads(parent.read_text())
original = json.loads((ROOT / 'safe-data-only-integrity-inspection.json').read_text())
rows = []
with tarfile.open(original['sdist']['file']['path'], 'r:gz') as tar:
    for member in tar.getmembers():
        prefix = 'actions_runtime-1.0.3/'
        if not member.isfile() or member.name.startswith(prefix + 'src/'):
            continue
        relative = member.name[len(prefix):]
        body = tar.extractfile(member).read()
        source_path = 'action_server/' + relative
        result = subprocess.run(['git', '-C', '/workspace/actions', 'ls-tree', SOURCE, '--', source_path], capture_output=True, check=True)
        row = {'public_archive_path': member.name, 'source_candidate': source_path,
               'bytes': len(body), 'sha256': digest(body), 'archive_mode': oct(member.mode)}
        if result.stdout:
            header, path = result.stdout.rstrip(b'\n').split(b'\t', 1)
            mode, kind, blob = header.decode().split()
            src = subprocess.check_output(['git', '-C', '/workspace/actions', 'cat-file', kind, blob], stderr=subprocess.PIPE)
            assert src == body and bool(member.mode & 0o111) == (mode == '100755')
            row.update({'git_mode': mode, 'git_blob': blob, 'source_bytes': len(src), 'source_sha256': digest(src),
                        'body_equal': True, 'executable_bit_equal': True, 'classification': 'TRACKED_BYTE_AND_EXECUTABLE_BIT_EXACT'})
        else:
            assert relative in {'setup.py', 'PKG-INFO'}
            row.update({'classification': 'GENERATED_BUILD_METADATA_NOT_A_TRACKED_GIT_MEMBER',
                        'source_code_execution': 'NOT_RUN'})
            if relative.endswith('.py'):
                ast.parse(body.decode())
                row['syntax_AST_parse'] = 'PASS_DATA_ONLY'
        rows.append(row)
assert len(rows) == 5
assert sum(r['classification'] == 'TRACKED_BYTE_AND_EXECUTABLE_BIT_EXACT' for r in rows) == 3
extra = write('safe-complete-sdist-root-source-bindings.json', {'source': SOURCE, 'root_file_comparisons': rows,
              'complete_sdist_members': len(original['sdist']['inventory']),
              'all_original_source_package_members_verified': True,
              'generated_setup_metadata_not_promoted_to_private_source_authority': True})
old_helper = Path('/workspace/actions-cloud/receipts/pr305-runner/frozen-helpers/test_canvas_query_template.py')
old_runner = Path('/workspace/actions-cloud/receipts/pr305-runner/canvas-native-public-runner-v5.py')
assert digest(old_helper.read_bytes()) == 'edc7ccfb85bd20bc89775f73ee45039bcf4c501fe6dae9a5ebd81a80e16eda4e'
assert digest(old_runner.read_bytes()) == '09cdc6b19f5d3d9cc94fadca23373108868521e0378d33960146b1a8522e88ad'
receipt['schema'] = 'current-runtime-partial-original-distribution-integrity-v2'
receipt['preserved_construction_checkpoint'] = binding(parent)
receipt['complete_sdist_root_source_bindings'] = extra
receipt['unchanged_frozen_external_helpers_history_only'] = [binding(old_helper), binding(old_runner)]
receipt['original_decoded_log_scope'] = 'EXACT_CONNECTOR_RETURNED_DECODED_CONTENT_PRESERVED_UTF8; NOT_A_CLAIM_OF_ORIGINAL_COMPRESSED_LOG_ARCHIVE_BYTES'
receipt['evidence'] = [binding(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name not in {'freeze-complete-v2.private.log'}]
for b in receipt['evidence']:
    assert stat.S_IMODE(Path(b['path']).stat().st_mode) == 0o600
    assert binding(Path(b['path'])) == b
frozen = write('OWNERFINAL-current618-partial-distribution-integrity-v2.json', receipt)
print(json.dumps({'OWNERFINAL': frozen, 'evidence_bindings': len(receipt['evidence']), 'release_verdict': 'HOLD', 'source_difference_scope': receipt['whole_source_body_equality_verdict']}))
