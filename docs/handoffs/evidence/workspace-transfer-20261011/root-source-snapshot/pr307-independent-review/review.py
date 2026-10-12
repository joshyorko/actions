from pathlib import Path
import hashlib
import json
import subprocess

REPO = '/workspace/engineering/pr307'
OWNED = Path('/workspace/engineering/pr307-guard-owned')
OUT = Path('/workspace/engineering/pr307-independent-review')
HEAD = '87e412f89b201c697d3e6bd4bd34031cdbd14df3'
TREE = '638b960a3700bbbba3026874efb158fa6e95117f'
PARENT = '0df315284ec7ddc5d8be47c07874522b52d7e9b4'
ORIGINAL = '729594fc04758502ec2ed985adb428e2863a3bb1'
TARGET = 'fbde0d3a248c47c9964851355f96575c89a87329'

def git(*args):
    return subprocess.check_output(['git', '-C', REPO, *args])

def binding(p):
    raw = p.read_bytes()
    return {'path': str(p), 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def tree(h):
    out = {}
    for row in git('ls-tree', '-rz', h).split(b'\0'):
        if row:
            meta, path = row.split(b'\t', 1)
            out[path.decode()] = tuple(v.decode() for v in meta.split())
    return out

assert git('log', '-1', '--format=%H %T %P', HEAD).decode().strip() == f'{HEAD} {TREE} {PARENT}'
assert git('log', '-1', '--format=%P', PARENT).decode().strip() == f'{ORIGINAL} {TARGET}'
assert not git('status', '--porcelain')
assert subprocess.run(['git', '-C', REPO, 'merge-base', '--is-ancestor', ORIGINAL, HEAD]).returncode == 0
assert subprocess.run(['git', '-C', REPO, 'merge-base', '--is-ancestor', TARGET, HEAD]).returncode == 0
a, b = tree(PARENT), tree(HEAD)
changed = [p for p in sorted(a.keys() | b.keys()) if a.get(p) != b.get(p)]
assert changed == ['action_server/scripts/build_oauth2_config.py', 'action_server/tasks.py', 'action_server/tests/build_system_tests/test_oauth2_config_build.py', 'docs/skills/repository-operations.md']
preserved = [p for p in a if a[p] == b.get(p)]
assert len(preserved) == 1404
assert tree(ORIGINAL)['action_server/docs/CHANGELOG.md'] == b['action_server/docs/CHANGELOG.md']
inventory = json.loads(Path('/workspace/engineering/native292-owned/producer-input-inventory.json').read_text())
assert len(inventory) == 268 and all(b[p][2] == v['blob'] for p, v in inventory.items())
successor = OWNED / 'successor-receipt.json'
assert binding(successor)['sha256'] == 'dc101ebfe12f201cb0a945e3f3c070bf41684289a4df607a8a3416ba7c42fe81'
worker = json.loads(successor.read_text())
for evidence in worker['evidence'].values():
    assert binding(Path(evidence['path'])) == evidence
source_files = []
for path in changed:
    p = Path(REPO, path)
    assert p.read_bytes() == git('show', HEAD + ':' + path)
    assert binding(p) == worker['source']['files'][path]
    source_files.append({'repository_path': path, 'git_mode_kind_blob': b[path], **binding(p)})
gateway = json.loads((OWNED/'controlled-gateway-receipt.json').read_text())
assert gateway['source']['head'] == HEAD and gateway['source']['tree'] == TREE and gateway['source']['parents'] == [PARENT]
for path, digest in gateway['source']['guard_file_sha256'].items():
    assert binding(Path(REPO, path))['sha256'] == digest
assert gateway['outer_yaml_forbidden'] and gateway['actual_invoke_task'] and gateway['actual_package_poetry_helper']
assert gateway['generated_module_restored_in_finally']
assert [c['exit_code'] for c in gateway['cases']] == [0, 1]
assert len(set(c['module_sha256'] for c in gateway['cases'])) == 1
children = [json.loads(line) for line in (OWNED/'gateway-children.jsonl').read_text().splitlines()]
assert children == gateway['helper_processes'] and len(children) == 4
assert all(c['helper_argv0'] == REPO + '/action_server/.venv/bin/python' for c in children)
assert gateway['package_yaml']['prefix'] == REPO+'/action_server/.venv'
assert gateway['package_yaml']['yaml'] == '6.0.3'
assert gateway['package_yaml']['yaml_origin'].startswith(REPO+'/action_server/.venv/')
for case in ['valid_structural_pair', 'second_acquisition_failure']:
    raw = (OWNED/(case+'.stdout.log')).read_bytes()+(OWNED/(case+'.stderr.log')).read_bytes()
    assert b'private acquisition body' not in raw
    if case == 'second_acquisition_failure':
        assert b'(exit 17)' in raw
full = (OWNED/'final-configured-gates.log').read_text()
assert '1173 passed, 13 skipped, 15 warnings' in full
assert '+ poetry run invoke test-not-integration' in full
assert '+ poetry run invoke lint' in full and '298 files already formatted' in full
assert '+ poetry run invoke typecheck' in full and 'Success: no issues found in 335 source files' in full
assert '+ poetry run ruff check scripts/build_oauth2_config.py tests/build_system_tests/test_oauth2_config_build.py' in full
assert '2 files already formatted' in full
assert '41 passed' in (OWNED/'final-focused.log').read_text()
assert '69 passed' in (OWNED/'toolkit-test.log').read_text()
assert '3 failed' in (OWNED/'red-behavior.log').read_text()
assert 'Success: no issues found in 1 source file' in (OWNED/'helper-typecheck.log').read_text()
roundtrip = json.loads((OWNED/'workflow-roundtrip-receipt.json').read_text())
assert len(roundtrip['outputs']) == 8 and roundtrip['all_eight_exact']
for output in roundtrip['outputs']:
    p = Path(REPO, output['path'])
    assert p.read_bytes() == (OWNED/'workflow-roundtrip'/p.name).read_bytes()
    assert binding(p)['sha256'] == output['sha256']
    assert a[output['path']] == b[output['path']]

doc = 'docs/skills/repository-operations.md'
patch = OUT/'canonical-documentation-exact-delta.patch'
patch.write_bytes(git('diff', PARENT, HEAD, '--', doc))
proposal = OUT/'canonical-documentation-disposition.md'
proposal.write_text('''The exact canonical documentation delta is already integrated in PR307 frozen commit 87e412f89b201c697d3e6bd4bd34031cdbd14df3, `docs/skills/repository-operations.md`, SHA256 aa538eb7d51d48567e92a944b0949c2dddba42e798f6498ccc2234ae9dfae0d7. The accompanying patch contains the complete delta against ordinary refresh parent0df31528.

The integrated boundary proposal e222695e retains the existing authority pair and public Invoke interface; it checks bounded binary acquisition, UTF-8 and safe-YAML mapping shape before replacing both original strings as one module. The gateway proposal bbf66a9c records that Runtime Poetry owns PyYAML, all existing generated/manual callers first install Runtime, and outer Invoke/RCC activation hints must be removed from the replacement child environment. Real frozen-source controlled acquisition proves this path with outer YAML forbidden and with a second-input failure preserving prior bytes and private stderr withheld.

The retained consumer proposals 4cfc8e79 and b07cfdc9 distinguish dry-run inventory from strict Twine/publication provenance, API head from actual producer checkout, one selected host wheel from the seven-artifact inventory, and full installed-member identity from generated-content qualification. The stale PR OAuth generation-equivalence claim is removed. Empty provider maps remain structural fixtures, not approved release content. The broad immutable-manifest architecture remains deferred pending the owner’s authoritative source pair/revision and provider policy; no guessed provider, successful skip, disabled mode, replacement source or infrastructure is introduced. An older immutable recovery source invokes its own task version and is not repaired by this current helper.

Evidence: exact source/tree/parent and1404 unrelated blob/mode preservation, original RED3/current focused41 PASS, configured1173 PASS13 existing skips, lint/typecheck335+explicit helper1 PASS, Toolkit69 PASS, exact8 generated roundtrip, and the committed-source real Invoke→Poetry controlled gateway receipt4ae7bd2f. No actual authoritative remote configuration was acquired, no native rebuild was run, and no release gate was waived. Current hosted checks and new generated-payload/source qualification remain open. Upstream disposition: none; the defect is the local Actions build boundary, with no established upstream defect.
''')
receipt = {
 'verdict': 'GO_NORMAL_PUSH_EXACT_87E412_SOURCE_CONTROL; HOLD_MERGE_HOSTED_GATES_OAUTH_AUTHORITY_AND_RUNTIME_PUBLICATION',
 'scope': 'read-only source/control and retained actual controlled test evidence; no review-side test/native rerun, acquisition or source mutation',
 'source': {'head': HEAD, 'tree': TREE, 'parent': PARENT, 'ordinary_refresh_ordered_parents': [ORIGINAL, TARGET], 'clean': True, 'exact_changed_paths': changed, 'files': source_files},
 'independent_preservation': {'unrelated_blob_and_mode_pairs':1404,'original_history_ancestors_retained':True,'original_changelog_blob_retained':True,'all268_measured_native_input_blobs_retained':True,'all_generator_workflows_and_existing_test_deadlines_retained':True},
 'worker_successor_receipt':binding(successor),
 'raw_evidence_verified':worker['evidence'],
 'additional_actual_gateway_bytes': [binding(OWNED/p) for p in ['gateway-children.jsonl','controlled-bin/gh','valid_structural_pair.stdout.log','valid_structural_pair.stderr.log','second_acquisition_failure.stdout.log','second_acquisition_failure.stderr.log']],
 'reviewed_behavior': ['Exact legacy authority/API input names and public task unchanged; no manifest or guessed provider/source policy.', 'Checked subprocess binary stdout/stderr and30-second per-input deadline; nonzero stdout cannot pass even with valid YAML.', 'Strict UTF8/nonblank/safe YAML/root+oauth2Config+providers mapping admission; no semantic provider qualification claimed.', 'Both valid bodies precede same-directory atomic replacement; original strings/module format preserved.', 'Meaningful first/second acquisition, timeout, API error, malformed/wrong shape, temp-write, replacement, cleanup and CLI-private-cause negative tests; RED3 demonstrates original ignored nonzero acquisition.', 'Safe CLI categories suppress raw source/config/stdout/stderr/exception-cause output; owned temporary cleanup preserves tested primary OSError.', 'Real committed Invoke Program→Poetry helper proof forbids outer YAML and checks child argv/prefix/RuntimePyYAML6.0.3 origin; second-input exit17 leaves modulehash unchanged.', 'Outer activation hints removed only from replacement child environment; GH auth forwarding remains available; caller process environment unchanged.'],
 'accepted_gates': {'focused':41,'configured_test_not_integration_pass':1173,'configured_existing_skips':13,'toolkit_pass':69,'configured_lint':'PASS','configured_typecheck_files':335,'explicit_helper_typecheck_files':1,'explicit_helper_test_ruff':'PASS','generated_workflow_roundtrip_exact':8},
 'producer_impact_and_remaining_gates': ['OAuth generated member bytes in future wheels/native artifacts must be qualified against actual checked source acquisition and approved authority; unchanged268 tracked input blobs do not imply unchanged generated payload.', 'Old retained wheel0f366268 and its empty generated member remain historical; narrow installed-wheel consumer GO is unchanged and cannot qualify a new artifact.', 'Current exact-head hosted complete merge gates are still required; local source/control GO is not merge GO.', 'Existing immutable recovery targets use their original task/helper/install environment; current guard does not retroactively repair or admit them.', 'Authoritative supported pair/revision/provider behavior still unidentified; structural empty-provider fixture cannot waive OAuth/release acceptance.', 'No actual remote acquisition, native/build acceptance, full integration/platform gate or Runtime publication performed.'],
 'canonical_documentation': {'disposition':'INTEGRATED in exact reviewed source87e412; read-only exact delta retained outside repository', 'canonical_file':doc,'canonical_sha256':binding(Path(REPO,doc))['sha256'],'exact_delta':binding(patch),'proposal_disposition':binding(proposal),'accepted_proposals':['e222695e minimal boundary','bbf66a9c actual caller/gateway','4cfc8e79 consumer dry-run/provenance/floor','b07cfdc9 generated-content followup'],'deferred':'2b3095 broad immutable-manifest design pending approved source ownership','stale_ambiguity':'PR command-name equivalence and dry-run/Twine implication removed; current-helper versus immutable-recovery source distinguished','remaining_uncertainty':'authority pair/revision/provider behavior and new artifact/current hosted gates','upstream':'none'},
 'private_metadata_policy':'unchanged HOLD; no original private bundle/spec substitution or publication admission',
}
p=OUT/'frozen-source-control-review.json'
p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(binding(p)))
