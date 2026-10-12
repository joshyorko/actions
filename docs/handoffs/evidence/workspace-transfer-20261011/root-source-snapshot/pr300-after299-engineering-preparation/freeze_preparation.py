from pathlib import Path
import hashlib, json, subprocess

O = Path(__file__).parent
REPO = '/workspace/actions'
H = '3cad4fd6d9fb386451b3b76d7b1103256eec54e5'
S = '3155fc55ea7d47afbc547fddc963b5860462924b'
T = '77647484b3cdd8e18aabf344a4018ea8ed8e3ea0'
U = 'f6b711f1589bcff6b9df73ab889c30503859d90d'
def git(*args): return subprocess.check_output(['git', '-C', REPO, *args])
def binding(path):
    p = Path(path); b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
def save(name, value):
    p = O / name; p.write_text(json.dumps(value, indent=2) + '\n'); p.chmod(0o600); return binding(p)
def leaves(rev):
    d = {}
    for row in git('ls-tree', '-rz', rev).split(b'\0'):
        if not row: continue
        h, p = row.split(b'\t', 1); mode, kind, blob = h.decode().split()
        d[p.decode()] = {'mode': mode, 'kind': kind, 'blob': blob}
    return d
raw = json.loads((O / 'private-authenticated-PR300-preparation-readbacks.json').read_text())
R = {r['name']: r['response'] for r in raw['reads']}
for suffix in ('before', 'after'):
    p = R['PR300-' + suffix]
    assert p['head']['sha'] == H and p['head']['ref'] == 'feat/run-output-transport-20261010'
    assert p['base']['ref'] == 'feat/shared-run-output-20261010'
    assert p['base']['sha'] == '4cad04ca0e70d219f53452fa5911c6d61192fd0d'
assert R['named-stack-base']['commit']['sha'] == S
assert R['named-head']['commit']['sha'] == H
assert R['named-integration-target']['commit']['sha'] == T
assert git('rev-parse', H + '^{tree}').decode().strip() == '2831e5abca6eca2072509789d9990a4b10b2e2e1'
old, current, union = map(leaves, (H,S,U))
assert (len(old),len(current),len(union)) == (1401,1419,1421)
assert not set(current) - set(union) and not set(old) - set(union)
modified = {p: {'target': current[p], 'union': union[p]} for p in current if current[p] != union[p]}
added = {p: union[p] for p in union if p not in current}
assert set(modified) == {'action_server/src/actions/server/_server.py', 'docs/skills/provenance-observability.md'}
assert set(added) == {'action_server/src/actions/server/run_outputs/transport.py', 'action_server/tests/action_server_tests/run_outputs/test_transport.py'}
assert all(union[p] == old[p] for p in set(modified) | set(added))
protected = ['action_server/src/actions/server/run_outputs/' + n for n in ['__init__.py','filesystem.py','models.py','service.py','types.py']] + ['action_server/tests/action_server_tests/run_outputs/' + n for n in ['test_concurrency.py','test_filesystem.py','test_migration.py','test_service.py']]
assert len(protected) == 9 and all(old[p] == current[p] == union[p] for p in protected)
assert {p:x for p,x in current.items() if p.startswith('.github/')} == {p:x for p,x in union.items() if p.startswith('.github/')}
transport = git('show', H + ':action_server/src/actions/server/run_outputs/transport.py').decode()
assert 'methods=["GET"]' in transport and 'status_code=416' in transport
assert 'CHUNK_BYTES = 64 * 1024' in transport and 'config.authenticate(request)' in transport
assert 'actor = await config.authenticate(request)' in transport and 'isinstance(actor, Actor)' in transport
assert 'with self._service.db.connect():' in transport and 'self._service.resolve(self._actor, self._workspace, self._handle)' in transport
assert 'await run_in_threadpool(self._owned.__exit__, None, None, None)' in transport
inventory_path = Path('/workspace/engineering/pr299/docs/program/evidence/runtime-frozen-current-source-20261011/producer-input-inventory.json')
pin = json.loads(inventory_path.read_text()); assert len(pin) == 268
changed = [p for p,x in pin.items() if union.get(p) != {'mode':x['mode'],'kind':x['kind'],'blob':x['blob']}]
new_src = [p for p in union if p.startswith('action_server/src/') and p not in pin]
assert len(changed) == 8 and len(new_src) == 7
testpin = json.loads(Path('/workspace/engineering/pr299/docs/program/evidence/runtime-frozen-current-source-20261011/selected-test-inventory.json').read_text())
assert len(testpin) == 5 and all(union[p] == {'mode':x['mode'],'kind':x['kind'],'blob':x['blob']} for p,x in testpin.items())
proof = save('complete-object-only-prospective-union-proof.json', {'schema': 'actions-pr300-prospective-complete-leaf-union/v1', 'source': H, 'anticipated_accepted_stack_source': S, 'known_integration_target': T, 'object_only_union_tree': U, 'not_an_actual_merge_commit_or_gate': True, 'source_leaves':1401, 'anticipated_target_leaves':1419, 'union_leaves':1421, 'unchanged_target_leaves':1417, 'all_original_paths_retained':True, 'modified_target_paths':modified, 'added_paths':added, 'all_four_transport_patch_paths_exact_original':True, 'all_nine_private_foundation_mode_blob_pairs_exact':{p:union[p] for p in protected}, 'whole_github_exact_anticipated_target':True, 'all1421_prospective_leaf_mode_blob_pairs':union, 'old_native_binding':{'original_named_production_inventory_count':268,'matched':260,'changed_eight':changed,'new_src_paths_seven':new_src,'prospective_named_inventory_count':275,'selected_tests_separate_count':5,'selected_tests_exact':True,'status':'UNQUALIFIED: not a new measured build/native artifact; other build inputs and whole artifact/platform acceptance are separate'}, 'upstream_disposition':'none'})
patch_path = O / 'canonical-original-accepted-GET-transport-guide-proposed.patch'
patch_path.write_bytes(git('diff','4cad04ca0e70d219f53452fa5911c6d61192fd0d',H,'--','docs/skills/provenance-observability.md')); patch_path.chmod(0o600)
op_guide = Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
lesson = ('The private Run output resolver locks its Workspace, checks the actor\'s grant\n'
          'and acquires the provider reader within one transaction, then yields the reader\n'
          'after the transaction exits. Revocation denies future acquisitions; reads on an\n'
          'already authorized reader do not recheck the grant. The existing denial test\n'
          'uses a failing provider-open sentinel for a denied principal, wrong Workspace\n'
          'and revoked grant. This proves denial before reader acquisition, not active-stream\n'
          'revocation, public authenticated transport or HTTP Range/HEAD acceptance.\n')
assert lesson in op_guide
lesson_path = O / 'canonical-existing-reader-acquisition-scope-verified.txt'; lesson_path.write_text(lesson); lesson_path.chmod(0o600)
refs = git('for-each-ref','--format=%(refname) %(objectname)','refs/heads/feat/run-output-transport-20261010','refs/remotes/origin/feat/run-output-transport-20261010').decode().splitlines()
assert refs == ['refs/remotes/origin/feat/run-output-transport-20261010 ' + H]
worktrees = git('worktree','list','--porcelain').decode()
assert 'worktree /workspace/engineering/pr300\n' not in worktrees
receipt = {
 'schema':'actions-pr300-dependency-ready-engineering-preparation/v2',
 'status':'PREPARED_READ_ONLY_ACTUAL299_ACCEPTED_INTEGRATION_REQUIRED_BEFORE_SOURCE_WRITER_ACTIVATION',
 'observed_at':raw['observed_at'],
 'existing_PR':{'number':300,'state':R['PR300-after']['state'],'draft':R['PR300-after']['draft'],'head':H,'tree':'2831e5abca6eca2072509789d9990a4b10b2e2e1','existing_head_branch':'feat/run-output-transport-20261010','base_branch':'feat/shared-run-output-20261010','payload_base_SHA_stale':'4cad04ca0e70d219f53452fa5911c6d61192fd0d','actual_named_stack_head':S,'known_integration_target':T,'local_worktree':'No currently registered pr300 worktree','local_existing_ref':'Existing origin remote-tracking ref3cad only; no local source branch yet. Materialize a local tracking checkout of the SAME accepted existing remote branch when root activates; no new remote/replacement branch.'},
 'dependency':{'required':'Root final ready/gate/policy readback and actual normal #299 accepted integration, then authenticated actual merged SHA/tree/ordered parents and current named integration ref. Current scoped #299 GO is not itself an actual merge.','order':'#299 actual integration → existing #300 ordinary refresh → source acceptance → normal existing PR retarget to integration branch → fresh declared current-head CI → scoped admission.','no_premature_base_or_head_mutation':True},
 'complete_prospective_union_proof':proof,
 'source_scope':{'route':'Optional default-off server-owned GET /api/workspaces/{workspace_id}/outputs/{handle}','authority':'Installation-key/browser auth is only an outer gate. Trusted server-owned async request-to-Actor callback is mandatory; caller Actor IDs/installation tokens/browser sessions do not create Workspace authority. Current persisted grant and canonical output admission are checked before provider reader acquisition.','streaming':'Measured descriptor; at most64KiB chunks; attachment/no-store/nosniff; validated opaque handle before filename headers; shielded acquisition/owned exit and cancellable streaming.','limits':'GET-only; HEAD405 and Range416 are explicit rejection, not acceptance of full HEAD/Range/static-serving contract. Denial/revocation precede acquisition; active stream does not recheck grant. Preserve original nine private source/test files as source contracts; nine files are not native/platform acceptance.','current_source': 'Four original300 patch paths byte/mode exact in prospective union; entire299 .github exact; no implementation rewrite needed.'},
 'retained_historical_receipts': [binding('/workspace/engineering/pr300-readonly-preparation.json'),binding('/workspace/engineering/pr300-merge-preview.txt'),binding('/workspace/engineering/reconciliation/pr300-live.json'),binding('/workspace/engineering/campaign-checkpoint/docs/program/evidence/current-open-pr-audit-20261010T1753Z/pr300-loopback-review.json')],
 'historical_gate_disposition':'73 focused PASS and author100 broader PASS/one browser fixture not run are historical receipt claims for old source. Original2-test loopback receipt belongs3cad with test-supplied trusted Actor, old prepared interpreter, and its own log/probe hashes; not rerun, not current gateway/full source/package/release proof. Preserve it without borrowing production identity, Canvas/native/browser/public endpoint or current-union acceptance. Old3cad CI and stale payload base are not new actual-target qualification.',
 'concrete_root_authorized_source_plan_after_dependency':[ 'Authenticate actual accepted299 merge and final named target; inspect any intervening target advancement before writer activation.', 'Materialize the SAME existing feat/run-output-transport-20261010 branch at exact remote3cad in a bounded pr300 checkout. Preserve old commits/receipts; ordinary merge ACTUAL target into source, no rebase/replacement/cherry-pick duplication.', 'Inspect complete merge-tree/leaf/mode/body union. If actual299 tree equals3155 tree99ac and no later target delta, anticipated union is f6b711f1589bcff6b9df73ab889c30503859d90d/1421 leaves; compare actual output, do not force it. Retain both parent guide blocks and all original transport/server/tests plus nine private foundation contracts. Stop narrow conflict changes for review if any.', 'Use managed RCC18.19.3 and canonical developer toolkit. Doctor, own Bootstrap or measured exact-input reuse with package-prefix and concrete-module origins for all five packages; no host Poetry/pip or stale historical interpreter.', 'ToolkitTest; configured Runtime focused run_outputs service/filesystem/concurrency/migration/transport tests plus inherited changed-source and auth-origin seams. Keep Linux provider skip explicit on non-Linux; no broadened skips, deadlines or external/native executions.', 'Run ONE authorized current-union full configured Runtime test-not-integration through package Invoke with bounded two workers; full configured lint Ruff/check/format/Isort and full typecheck. Reconcile every skip/external dependency. Preserve before/after complete source body/mode hashes, owned tool inputs and process/cleanup limitations; failures remain source-bound.', 'Canonical generator replay all eight exact outputs and dependabot/all tracked YAML parse/byte comparison; no workflow pin edits unless separately assigned. Commit only the accepted ordinary union and necessary evidence-backed canonical delta. Freeze exact SHA/tree/parents/source/checkpoint; independent source acceptance before guarded existing-ref normal push.', 'Root verifies actual source/head/base/ref and preservation, retargets EXISTING PR300 only after actual299 accepted integration to integration/community-release-20261008, normal-pushes with expected existing-ref/head guard and retains exact HTTP body final newline.', 'Derive expected hosted job set from new exact current-union workflow event/branch/path/matrix/needs rules and prospective diff after retarget. Require every mandatory current-head job including late publisher, complete pagination/status/reviews/threads/policy/readiness, authenticated tested checkout and current scope evidence. No old299/300 greens carry.' ],
 'not_authorized_or_claimed':['No source/worktree/ref/base changes or tests/native/provider/browser execution in this preparation.','No current native build/artifact/installed consumer qualification;275 named inputs vs old268 now260matches8changes7adds, five selectors exact separately.','No new provider/authenticator design, active-stream revocation, HEAD/Range implementation, public tunnel or infrastructure.','No Canvas producer/ChatGPT/full83/86/127/129/private134/frozen-v6/Runtime221/publication/whole campaign closure.'],
 'private_live_API':binding(O/'private-authenticated-PR300-preparation-readbacks.json'),
 'documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/provenance-observability.md original accepted GET transport guide delta retained exactly for ordinary source refresh; existing repository-operations grant-acquisition paragraph verified unchanged.','Exact_proposed_delta':binding(patch_path),'Existing_exact_reader_scope':binding(lesson_path),'Durable_learning_captured':'Default-off trusted Actor plus persisted grant permits bounded GET acquisition; source/ASGI and historical test-authenticated loopback scopes remain distinct from deployed identity/native/Canvas acceptance. Revocation guards future reader acquisition, not an active stream.','Evidence':'Original3cad transport/server/test Git blobs, explicit GET-only/HHEAD405/Range416 tests, same9private foundation mode/blob pairs in prospective1421 union; historicalloopback receipt7562; unchanged original guidec73 and existing reader transaction lesson.','Stale_or_ambiguous_guidance_removed':'PR description old600fb stack reference and stale payload4cad do not supply current named3155 or actual integrated dependency. No original73/100/TCP receipt/current-head CI requalification, HEAD/range rejection as supported contract, or nine source files as native proof.','Remaining_uncertainty':'Actual299 integration and current target tuple not yet authenticated here; future materialized source/full/current-hosted gates; production identity/provider/Canvas/native/whole storage/release acceptance. Existing PRbody source mapping/history remains historical and should be updated to exact final scope only with root-authorized refreshed checkpoint.'},
 'actions':'Bounded private preparation and object-only Git merge-tree preview; no branch/worktree/source/base/ref mutation, test/gateway/native/install/download/rerun/merge or another299 census.',
 'upstream_disposition':'none'}
print(json.dumps({'handoff':save('immutable-after299-existing-PR300-source-handoff.json',receipt),'proof':proof,'canonical_patch':binding(patch_path)}))
