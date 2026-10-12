"""Correct file-kind scope and add prospective checkout/filter controls; no tests run."""
import ast
import fnmatch
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
ART = Path('/workspace/engineering/pr221-current618-wheel-integrity-owned')
SOURCE = '6181b044c75de35386f1ae30e71725398b6a7feb'
REPO = '/workspace/actions'

def digest(b):
    return hashlib.sha256(b).hexdigest()

def binding(p):
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': digest(b)}

def write(name, obj):
    p = ROOT / name
    b = obj if isinstance(obj, bytes) else (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode()
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(b)
    return binding(p)

def source(path):
    return subprocess.check_output(['git', '-C', REPO, 'show', SOURCE + ':' + path], stderr=subprocess.PIPE)

previous = ROOT / 'OWNERFINAL-windows-generated-static-rootcause-trace.json'
assert previous.stat().st_size == 20324 and digest(previous.read_bytes()) == '91c258e08d0f9cf232d4822a556d079f37d16b07d11bcfd948eb7811318ebd9b'
r = json.loads(previous.read_text())
comparison = json.loads((ART / 'safe-source-body-and-builder-observations.json').read_text())
windows = next(w for w in comparison['classifications'] if w['platform'] == 'Windows' and w['python_abi'] == 'cp312')
python_rows = [x for x in windows['tracked_package_comparisons'] if x['public_member_path'].endswith('.py')]
crlf = [x for x in windows['tracked_package_comparisons'] if x['category'] == 'CRLF_TO_LF_ONLY']
python_crlf = [x for x in crlf if x['public_member_path'].endswith('.py')]
non_python = [x for x in crlf if not x['public_member_path'].endswith('.py')]
assert len(python_rows) == 201 and len(crlf) == 178 and len(python_crlf) == 173 and len(non_python) == 5
non_python_source_paths = ['action_server/src/' + x['public_member_path'] for x in non_python]
assert non_python_source_paths == [
    'action_server/src/actions/server/README.md', 'action_server/src/actions/server/bin/.gitignore',
    'action_server/src/actions/server/index.html', 'action_server/src/actions/server/templates/action-templates.yaml',
    'action_server/src/actions/server/vendored_deps/README.md']

python_inventory = []
for entry in subprocess.check_output(['git', '-C', REPO, 'ls-tree', '-rz', SOURCE], stderr=subprocess.PIPE).split(b'\0'):
    if not entry:
        continue
    header, path = entry.split(b'\t', 1)
    p = path.decode()
    if p.startswith('action_server/src/') and p.endswith('.py'):
        mode, kind, blob = header.decode().split()
        b = subprocess.check_output(['git', '-C', REPO, 'cat-file', kind, blob], stderr=subprocess.PIPE)
        assert b'\r' not in b
        python_inventory.append({'public_source_path': p, 'mode': mode, 'git_blob': blob,
                                 'bytes': len(b), 'sha256': digest(b), 'CR': 0, 'LF': b.count(b'\n')})
assert len(python_inventory) == 201
for p in non_python_source_paths:
    assert b'\r' not in source(p)
rules = ['action_server/src/**/*.py text eol=lf',
         'action_server/frontend/apps/runtime/index.html text eol=lf',
         *[p + ' text eol=lf' for p in non_python_source_paths]]
attrs = source('.gitattributes')
line_count = len(attrs.splitlines())
patch = '--- a/.gitattributes\n+++ b/.gitattributes\n'
patch += f'@@ -{line_count},0 +{line_count + 1},{len(rules) + 2} @@\n'
patch += '+\n+# Preserve exact Runtime distribution source and HTML scaffold checkout bytes.\n'
patch += ''.join('+' + line + '\n' for line in rules)
attribute_patch = write('proposed-narrow-runtime-checkout-byte-identity-v2.patch', patch.encode())

generator_path = '.github/workflows/_gen_workflows.py'
generator = source(generator_path)
generator_snapshot = write('source-generator-v2.private.txt', generator)
tree = ast.parse(generator.decode())
class_refs = {}
for name in ('ActionServerTests', 'ActionServerPyPiRelease'):
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'on_part')
    class_refs[name] = {'class_line': cls.lineno, 'on_part_line': method.lineno, 'on_part_end_line': method.end_lineno}

workflow_scopes = []
for path, cls, jobs in [('.github/workflows/actions_runtime_tests.yml', 'ActionServerTests', 3),
                       ('.github/workflows/actions_runtime_pypi_release.yml', 'ActionServerPyPiRelease', 5)]:
    body = source(path)
    d = yaml.safe_load(body)
    events = d.get('on', d.get(True))
    pr = events['pull_request']
    assert '.gitattributes' not in pr['paths']
    assert not any(fnmatch.fnmatchcase('.gitattributes', p) for p in pr['paths'])
    snap = write('source-' + Path(path).name + '-filter-v2.private.txt', body)
    workflow_scopes.append({'public_workflow_path': path, 'generator_class': cls,
                            'generator_on_part_refs': class_refs[cls], 'current_PR_branches': pr['branches'],
                            'current_PR_paths': pr['paths'], 'current_attributes_only_change_triggers': False,
                            'proposed_PR_paths_delta': ['.gitattributes'],
                            'expanded_job_count': jobs, 'source_snapshot': snap,
                            'preserve': ['branches', 'event modes', 'matrix', 'needs', 'timeouts', 'case assertions', 'permissions', 'tag/registry conditions']})
assert workflow_scopes[0]['current_PR_branches'] == ['master', 'community', 'integration/**']
assert workflow_scopes[1]['current_PR_branches'] == ['community', 'integration/**']

proposal = {
    'schema': 'prospective-runtime-checkout-identity-and-builder-filters-v2',
    'status': 'READ_ONLY_PROPOSAL_AWAITING_SOURCE_AND_CONTROL_EXECUTION_AUTHORITY',
    'retained_v1_construction_checkpoint': binding(previous),
    'separate_qualification_failures': {
        'tracked_checkout_bytes': {'CRLF_only_package_differences': 178, 'Python': 173, 'nonPython': 5,
                                   'nonPython_public_source_paths': non_python_source_paths,
                                   'generated_frontend_Python_module_not_in_CRLF_only_set': True},
        'generated_frontend_asset': {'source_HTML_path': 'action_server/frontend/apps/runtime/index.html',
                                     'source_HTML_CR': 0, 'source_HTML_LF': 13,
                                     'retained_Windows_decoded_asset_CR': 13, 'CRLF': 12, 'lone_CR': 1,
                                     'all_CR_removed_matches_Linux': True, 'semantic_equivalence': 'NOT_ESTABLISHED'}},
    'candidate_source_delta': {'narrow_attributes_patch': attribute_patch, 'rules': rules,
                               'Runtime_source_Python_inventory': python_inventory,
                               'selected_original_source_CR_bytes': 0,
                               'Git_body_or_blob_rewrite': False,
                               'source_fixtures_binary_archives_bat_other_packages': 'OUTSIDE_ALL_NEW_RULES'},
    'affected_generated_build_and_test_filters': workflow_scopes,
    'generator_snapshot': generator_snapshot,
    'source_change_scope': ['.gitattributes', 'ActionServerTests.on_part', 'ActionServerPyPiRelease.on_part',
                           'two corresponding generated YAML outputs', 'meaningful checkout/filter regression in existing developer/devutils contracts', 'canonical owning guide'],
    'unrelated_six_generated_outputs_and_other_generator_AST': 'REQUIRE_BYTE_AND_AST_PRESERVATION',
    'meaningful_actual_temporary_Git_index_RED_GREEN_plan': [
        'Use an owned temporary Git repository and index, not the source worktree. Populate canonical .gitattributes, all201 Runtime sourcePython blobs/modes, the five exact packaged nonPython text blobs, and the372B Runtime HTML source directly from the recorded618 Git objects. Bind every input blob/SHA before checkout.',
        'RED: set core.autocrlf=true only in the synthetic Git fixture. Checkout through actual Git conversion under current attributes. Compare original Git bodySHA with every checked-out selected fileSHA; require a meaningful failing exact-byte control for a nonempty RuntimePython file, each five nonPython files, and the Runtime HTML input. Record measured conversions without inferring the historical CI setting.',
        'GREEN: apply only the seven proposed narrow attribute rules in the temporary index and repeat actual checkout. Require complete201 Python plusfive text plusoneHTML bodySHA/byte equality, unchanged expected sourceGit identities/modes,13LF/0CR RuntimeHTML, and success with both core.autocrlf=true andfalse.',
        'Poison/remove the Python rule, exactHTML rule, and each nonPython rule independently; each corresponding exact-byte assertion must fail under the synthetic autocrlf=true checkout. Use actual Git attribute resolution to prove **/*.py matches all intended source descendants, without treating fnmatch as a Git attribute implementation.',
        'Retain binary template ZIP hashes, a .bat fixture with deliberate CRLF, test-only literal-CRLF fixture data, and representative other-package/testPython files under their original policies. Prove the new rules do not globally alter their effective attributes or bytes.',
        'Preserve the encoder read_bytes/repr exact-byte contract using synthetic CRLF/loneCR bytes and retained decoded assetdigests. Do not normalize generatedHTML/Pythonpayload, rewriteRECORD, or waive rawbody differences.',
        'Run generated workflow filter controls with exactly .gitattributes changed: both affected workflows must select on community and integration/** while all existing matrix/needs/event/tag semantics remain. Demonstrate current filter exclusion RED, amended filters GREEN and wrong-branch rejection.',
        'After source authorization, run canonical local configured controls/static/all8generation proof and fresh hosted affected Runtime builder/tests. Reinspect original resulting Windows wheels to qualify everytracked body and generatedfrontend; service-free checkout controls do not prove compiler behavior or retrospectively determine originalcause.'
    ],
    'actual_control_test_execution_now': 'NOT_RUN',
    'actual_historical_core_autocrlf_and_original_HTML_input': 'UNKNOWN_UNRETAINED',
    'no_production_byte_admission_waiver': True,
    'existing_and_remaining_holds': ['Windows Unix executable mode availability', 'generatedOAuth empty/sourceauthority', 'full7/crossplatform installedconsumers', 'private/native/registry/release/fullgraph'],
    'Upstream_disposition': 'none'}
proposal_ref = write('bounded-complete-runtime-checkout-and-filter-proposal-v2.json', proposal)

old_patch = (ROOT / 'canonical-generated-static-input-and-byte-identity-proposed.patch').read_text()
extra = [
    'Include tracked non-Python package text in checkout-byte qualification. A',
    'Python-only rule leaves packaged README, HTML, YAML and other text differences',
    'unresolved; keep binary archives and intentional platform-specific line-ending',
    'fixtures outside any proposed text rule. A checkout-byte fix must also appear',
    'in affected builder and test workflow path filters. A passing census that',
    'excluded those workflows does not qualify its distribution bytes.', '']
header, body = old_patch.split('@@\n', 1)
m = re.search(r'@@ -(\d+),0 \+(\d+),(\d+) ', header)
old_count = int(m.group(3))
new_header = header[:m.start()] + f'@@ -{m.group(1)},0 +{m.group(2)},{old_count + len(extra)} '
new_patch = new_header + '@@\n' + body + ''.join('+' + line + '\n' for line in extra)
doc_ref = write('canonical-generated-static-and-complete-checkout-scope-proposed-v2.patch', new_patch.encode())

r['schema'] = 'current618-windows-static-and-complete-checkout-rootcause-trace-v2'
r['retained_v1_construction_checkpoint'] = binding(previous)
r['scope_correction'] = '178 tracked CRLF-only differences =173Python+5nonPython; one additional generatedfrontend Pythonbody differs. Do not call178allPython.'
r['separate_checkout_scope_proposal'] = proposal_ref
r['source_fix_and_RED_GREEN_plan'] = proposal_ref
r['actual_service_free_control_execution'] = 'NOT_RUN_REQUIRES_OWNER_AUTHORIZATION'
r['hypotheses'][0]['support'] = '13CR confined to HTML scaffold, source13LF/eolunset; separate173Python+5nonPython CRLF-only bodies. Actual checkout inputs/config and compiler intermediates are unretained.'
r['Documentation_improvement']['exact_delta'] = doc_ref
r['Documentation_improvement']['durable_learning'] += ' Include packaged nonPython source text and affected workflow trigger filters in checkout-byte qualification.'
r['Documentation_improvement']['stale_or_ambiguous_guidance_removed'] += ' Distinguish173Python fromfive othertext bodies; attributes-only changes currently exclude both Runtime builder/test workflows.'
r['evidence'] = [binding(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name != 'freeze-v2-private.log']
result = write('OWNERFINAL-windows-static-and-complete-checkout-diagnosis-v2.json', r)
print(json.dumps({'OWNERFINAL': result, 'evidence': len(r['evidence']), 'scope': r['scope_correction'], 'actual_controls': 'NOT_RUN'}))
