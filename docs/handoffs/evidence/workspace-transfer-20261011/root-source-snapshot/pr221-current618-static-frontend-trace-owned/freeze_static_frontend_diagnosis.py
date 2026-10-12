"""Readonly source and retained-archive trace. No frontend/package module executes."""
import ast
import hashlib
import json
import os
import re
import stat
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ART = Path('/workspace/engineering/pr221-current618-wheel-integrity-owned')
REPO = '/workspace/actions'
SOURCE = '6181b044c75de35386f1ae30e71725398b6a7feb'
BUILD = 'e7666eacf2687f65050b97a88e791f8d0ce4cd20'
TREE = '99ac5309add45af65049546dd3a99f357884cf3b'

def digest(b):
    return hashlib.sha256(b).hexdigest()

def binding(p):
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': digest(b)}

def write(name, obj):
    p = ROOT / name
    body = obj if isinstance(obj, bytes) else (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode()
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(body)
    return binding(p)

def source(path):
    return subprocess.check_output(['git', '-C', REPO, 'show', SOURCE + ':' + path], stderr=subprocess.PIPE)

owner = ART / 'OWNERFINAL-current618-partial-distribution-integrity-v2.json'
assert owner.stat().st_size == 12170 and digest(owner.read_bytes()) == '9b406fdf505871e6790d7a4233d0b8c075ae6f170f2c5b7a954bbca0f0d46236'
parent = json.loads(owner.read_text())
for e in parent['evidence']:
    assert binding(Path(e['path'])) == e

paths = ['.gitattributes', 'action_server/tasks.py', 'action_server/build.py', 'action_server/pyproject.toml',
         'action_server/frontend/apps/runtime/index.html', 'action_server/frontend/package.json',
         'action_server/frontend/package-lock.json', 'action_server/frontend/vite.config.js',
         'action_server/frontend/scripts/inline-runtime-assets.mjs',
         '.github/workflows/actions_runtime_pypi_release.yml']
source_bindings = []
for path in paths:
    body = source(path)
    header = subprocess.check_output(['git', '-C', REPO, 'ls-tree', SOURCE, '--', path], stderr=subprocess.PIPE).decode().split('\t')[0]
    mode, kind, blob = header.split()
    preserved = write('source-' + path.replace('/', '__') + '.private.txt', body)
    source_bindings.append({'public_git_path': path, 'git_mode': mode, 'git_blob': blob,
                            'bytes': len(body), 'sha256': digest(body), 'private_source_snapshot': preserved})

index_path = 'action_server/frontend/apps/runtime/index.html'
input_html = source(index_path)
tasks = ast.parse(source('action_server/tasks.py').decode())
f = next(n for n in tasks.body if isinstance(n, ast.FunctionDef) and n.name == 'build_frontend')
reader = next(n for n in ast.walk(f) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'read_bytes')
assert reader.lineno == 153
writer = next(n for n in ast.walk(f) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'open' and n.lineno == 155)
assert {k.arg: k.value.value for k in writer.keywords} == {'encoding': 'utf-8', 'newline': '\n'}
representer = next(n for n in ast.walk(f) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'repr')
assert representer.lineno == 166
assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'replace' for n in ast.walk(f))
assert b'_static_contents' not in source('action_server/build.py')

inspection = json.loads((ART / 'safe-data-only-integrity-inspection.json').read_text())
assets, module_refs = {}, {}
for platform in ('Linux', 'Windows'):
    wheel = next(w for w in inspection['wheels'] if w['platform'] == platform and w['python_abi'] == 'cp312')
    with zipfile.ZipFile(wheel['file']['path']) as z:
        body = z.read('actions/server/_static_contents.py')
    assignment = next(n for n in ast.parse(body.decode()).body if isinstance(n, ast.Assign))
    values = ast.literal_eval(assignment.value)
    assert set(values) == {'index.html'} and isinstance(values['index.html'], bytes)
    assets[platform] = values['index.html']
    module_refs[platform] = {'wheel': wheel['file'], 'module_bytes': len(body), 'module_sha256': digest(body),
                            'module_CR_count': body.count(b'\r'), 'decoded_asset_bytes': len(assets[platform]),
                            'decoded_asset_sha256': digest(assets[platform]), 'decoded_asset_CR': assets[platform].count(b'\r'),
                            'decoded_asset_CRLF': assets[platform].count(b'\r\n'), 'decoded_asset_LF': assets[platform].count(b'\n')}
linux, windows = assets['Linux'], assets['Windows']
assert windows.replace(b'\r', b'') == linux
assert windows.replace(b'\r\n', b'\n') != linux
assert windows.count(b'\r') == 13 and windows.count(b'\r\n') == 12
assert input_html.count(b'\n') == 13 and b'\r' not in input_html

scaffold_ends = {}
for line_number, line in enumerate(input_html.splitlines(keepends=True), 1):
    body = line.rstrip(b'\n')
    locations = [m.start() for m in re.finditer(re.escape(body), linux)]
    if len(locations) == 1:
        scaffold_ends[locations[0] + len(body)] = line_number
mapping = []
for ordinal, match in enumerate(re.finditer(b'\r', windows)):
    offset = match.start() - ordinal
    mapping.append({'ordinal': ordinal + 1, 'normalized_asset_offset': offset,
                    'input_scaffold_line_end': scaffold_ends.get(offset),
                    'CRLF': windows[match.start() + 1:match.start() + 2] == b'\n'})
assert all(m['input_scaffold_line_end'] is not None for m in mapping)
assert [m['input_scaffold_line_end'] for m in mapping] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 12, 13]
assert b'\r\r\n' in windows

logs = []
for job in (114433293243, 114433293117, 114433293201):
    log = ART / f'job-{job}-original.private.log'
    lines = log.read_text().splitlines()
    begin = next(i for i, line in enumerate(lines) if '##[group]Run' in line and 'inv build-frontend' in line)
    end = next(i for i in range(begin + 1, len(lines)) if '##[group]Run' in lines[i])
    assert 'build-oauth2-config' in lines[end]
    logs.append({'job_id': job, 'original_decoded_log': binding(log),
                 'frontend_step_lines': [begin + 1, end], 'next_declared_step': 'Build OAuth2 config (PR)',
                 'npm_artifacts_command_lines': [i + 1 for i in range(begin, end) if 'npm run build:artifacts' in lines[i]],
                 'runtime_inline_script_invocation_lines': [i + 1 for i in range(begin, end) if 'inline-runtime-assets.mjs' in lines[i]],
                 'effective_core_autocrlf_observation': 'UNAVAILABLE',
                 'core_autocrlf_log_mentions_count': sum('autocrlf' in line.lower() for line in lines),
                 'original_checked_out_runtime_HTML_input': 'UNAVAILABLE',
                 'original_pre_encoder_dist_index_digest': 'UNAVAILABLE'})

env = dict(os.environ)
env['GIT_INDEX_FILE'] = str(ROOT / 'source-readonly.index')
raw_attrs = subprocess.check_output(['git', '-C', REPO, 'check-attr', '--cached', '-z', '--all', '--', index_path], env=env, stderr=subprocess.PIPE)
parts = raw_attrs.decode().split('\0')
attrs = {parts[i + 1]: parts[i + 2] for i in range(0, len(parts) - 1, 3)}
assert attrs == {'text': 'auto'}

proposal = {
    'status': 'PROSPECTIVE_NARROW_INPUT_CONTRACT_FIX_REQUIRES_OWNER_SOURCE_AUTHORIZATION',
    'minimal_source_delta_candidate': 'Set text eol=lf for action_server/frontend/apps/runtime/index.html only.',
    'why_this_boundary': 'The retained difference is confined to CR at original HTML scaffold boundaries; the byte encoder deliberately preserves the compiled asset. Canonicalize the single tracked HTML input rather than stripping generated content or waiving raw equality.',
    'actual_hosted_cause': 'UNKNOWN_ORIGINAL_INPUT_AND_EFFECTIVE_AUTOCRLF_NOT_RETAINED',
    'implementation_now': 'NOT_AUTHORIZED_NOT_PERFORMED',
    'meaningful_service_free_RED_GREEN_plan': [
        'In an owned temporary Git repository/index, retain the exact current Runtime HTML blob and current attributes. Set core.autocrlf=true for this synthetic checkout only; assert checked-out Runtime HTML SHA/bytes equal the LF Git blob. The current text=auto/no-eol contract should produce13CRLF and fail that exact-byte assertion.',
        'Apply only the proposed exact Runtime HTML text eol=lf attribute in the owned fixture. Repeat the same checked-out-file assertion; it must be byte/hash exact to the retained372B Git input with13LF and0CR.',
        'Repeat with core.autocrlf=false/input UTF8 content; require unchanged canonical bytes. Include a separate representative Python/text input to show that the targeted policy does not globally normalize other files.',
        'Use synthetic bytes containing CRLF and a loneCR to protect the actual AST-extracted read_bytes/repr byte-preservation contract; evaluate only the literal representation as data and require every original byte retained. Do not turn this into a post-build CR-removal fix.',
        'Require a source-following Windows build artifact requalification after any authorized source change; service-free Git and encoder controls do not establish frontend compiler equivalence, the original hosted cause, fullplatform consumers or release acceptance.'
    ],
    'minimal_next_diagnostic_if_input_policy_not_approved': 'Retain allowlisted Runtime source-index and pre-encoder dist-index SHA/byte/CR/CRLF/LF counts plus effective text/eol/core.autocrlf classes at the next already-authorized build; never dump HTML, environment, URLs or raw command output.',
    'preserve': ['all178 module CRLF-only comparisons', 'Windows Unix-mode UNAVAILABLE', 'both empty OAuth entries and source/content authorityHOLD', 'all original RECORD hashes', 'alloriginal previous qualifications and current full7/releaseHOLD'],
    'not_proposed': ['global attributes policy', 'blanket output normalization', 'RECORD relabel', 'semantic equivalence waiver', 'new native/browser/provider/consumer run']}
proposal_ref = write('bounded-source-fix-and-regression-proposal.json', proposal)

guide = Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md')
text = guide.read_text()
anchor = 'A platform artifact containing only Linux wheels does not satisfy the'
assert anchor in text
position = text.index(anchor)
lines = text[:position].count('\n')
lesson = [
    'When qualifying generated Runtime frontend content, decode `_static_contents.py`',
    'as data and bind each asset\'s bytes to its builder checkout. The encoder reads',
    '`dist/index.html` as bytes and writes their representation; setting the generated',
    'module\'s newline to LF does not normalize the embedded asset. Keep outer module',
    'CRLF differences, decoded asset CR differences and semantic equivalence separate.',
    'A carriage-return-removal comparison is diagnostic evidence, not a source or',
    'content waiver. If the original frontend input and effective checkout newline',
    'setting were not retained, keep checkout-versus-compiler causation unknown.', '']
assert '\n'.join(lesson[:-1]) not in text
patch = '--- a/docs/skills/repository-operations.md\n+++ b/docs/skills/repository-operations.md\n'
patch += f'@@ -{lines},0 +{lines + 1},{len(lesson)} @@\n' + ''.join('+' + line + '\n' for line in lesson)
canonical_ref = write('canonical-generated-static-input-and-byte-identity-proposed.patch', patch.encode())

receipt = {
    'schema': 'current618-windows-static-frontend-source-trace-v1', 'verdict': 'HOLD_PRECISE_CHECKOUT_VERSUS_COMPILER_CAUSE_UNRESOLVED',
    'source': SOURCE, 'producer_checkout': BUILD, 'tree': TREE,
    'producer_ordered_parents': ['a70993fafc99a9f94041485542d5a720797ca394', SOURCE],
    'original_owner_qualification': binding(owner), 'all24original_owner_bindings_unchanged': True,
    'confirmed': {'encoder_source_refs': {'public_source_path': 'action_server/tasks.py', 'input_path_assignment_line': 147,
                                        'read_bytes_line': 153, 'outer_module_write_LF_line': 155, 'byte_repr_line': 166},
                  'source_package_build_does_not_reference_static_module': True,
                  'source_Runtime_HTML_input': {'path': index_path, 'bytes': len(input_html), 'sha256': digest(input_html), 'CR': 0, 'LF': 13},
                  'effective_source_attributes': attrs, 'explicit_source_eol_attribute': 'UNSET',
                  'retained_assets': module_refs, 'Windows_CR_scaffold_mapping': mapping,
                  'Windows_all_CR_removed_equal_Linux': True, 'Windows_CRLF_only_normalization_equal_Linux': False,
                  'duplicate_CR_at_scaffold_line10': True, 'semantic_equivalence': 'NOT_ESTABLISHED'},
    'original_builder_step_bindings': logs,
    'source_pipeline': {'workflow': {'source_path': '.github/workflows/actions_runtime_pypi_release.yml', 'command': 'inv build-frontend', 'build_then_OAuth_then_package': True},
                        'npm_commands': [{'tasks_line': 136, 'phase': 'npm ci'}, {'tasks_line': 144, 'phase': 'npm run build:artifacts'}],
                        'runtime_build': 'Vite runtime mode, then inline-runtime-assets, then artifact manifest and SBOM',
                        'inline_script_source_refs': {'path': 'action_server/frontend/scripts/inline-runtime-assets.mjs', 'read_index_line': 5, 'read_asset_line': 29, 'write_index_line': 51, 'explicit_CR_normalizer': False},
                        'Vite_source_refs': {'path': 'action_server/frontend/vite.config.js', 'runtime_root_selection_lines': [11, 13, 16], 'output_directory_line': 45}},
    'hypotheses': [{'name': 'CRLF_checkout_HTML_scaffold_retained_through_frontend_compilation', 'confidence': 'STRONGLY_SUPPORTED_BUT_ORIGINAL_INPUT_UNAVAILABLE',
                    'support': '13CR confined to source HTML scaffold, source input13LF, attributes text=auto/eolunset, Windows remaining trackedmodule178CRLF-only.',
                    'not_established': 'Actual effective core.autocrlf value, actual checked-out input CR bytes, exact compiler intermediate and initial origin of CR.'}],
    'necessary_policy_decision': 'Approve an LF checkout contract for this single Runtime HTML source or first retain the missing input/config evidence. No claim that the candidate attribute fixes actual original hosted cause.',
    'source_fix_and_RED_GREEN_plan': proposal_ref,
    'Documentation_improvement': {'canonical_file_proposed': 'docs/skills/repository-operations.md', 'exact_delta': canonical_ref,
                                 'durable_learning': 'LF Python module output and exact embedded frontend asset identity are independent; input evidence is required for checkout-versus-compiler causal attribution.',
                                 'stale_or_ambiguous_guidance_removed': 'An LF module writer or CR-removal comparison must not be mistaken for embedded-content normalization or semantic equivalence.',
                                 'remaining_uncertainty': 'Original checkout input/config and compiler intermediate were not retained.'},
    'read_only_scope': {'new_downloads_polls': 0, 'source_changes': False, 'build_install_package_import_browser_native_provider': False,
                       'consumer_runner_or_control_changes': False, 'raw_HTML_logs_configs_signed_URLs_forwarded': False},
    'remaining_holds': ['Windows raw frontend body difference', 'Windows unavailable Unix executable mode', 'OAuth empty generated entries/sourceauthority', 'macOS/aggregate/full7/platform consumers', 'private/native/registry/release/whole graph'],
    'Upstream_disposition': 'none', 'source_bindings': source_bindings,
    'evidence': [binding(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name != 'freeze-private.log']}
frozen = write('OWNERFINAL-windows-generated-static-rootcause-trace.json', receipt)
print(json.dumps({'OWNERFINAL': frozen, 'source_bindings': len(source_bindings), 'evidence': len(receipt['evidence']), 'verdict': receipt['verdict']}))
