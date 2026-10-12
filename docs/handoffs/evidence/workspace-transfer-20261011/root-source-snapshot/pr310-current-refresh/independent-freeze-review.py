import ast
import hashlib
import json
import pathlib
import subprocess

repo=pathlib.Path('/workspace/engineering/pr310')
out=pathlib.Path('/workspace/engineering/pr310-current-refresh')
head='dfca3f8e63465595acff421f37f34d2a9d0a1b39'
merge='bd200037c870ebc40052923b681754a6b08ebd18'
old='4b2df94d77b1145a9ed586fb924eeb88c478d01c'
target='1c7585fe8bb3cb9476c3997570bd3f04466f2bbc'
native='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
def leaves(ref):
    result={}
    for line in git('ls-tree','-r',ref).decode().splitlines():
        mode,path=line.split('\t',1);result[path]=mode
    return result
def bind(path):
    p=pathlib.Path(path);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
assert git('rev-parse','HEAD').decode().strip()==head
assert not git('status','--porcelain')
assert git('show','-s','--format=%P',head).decode().strip()==merge
assert git('show','-s','--format=%P',merge).decode().split()==[old,target]
assert git('rev-parse','HEAD^{tree}').decode().strip()=='17c1afa7fbaa6ae817830d85226b41f67dd8b820'
oldleaves,targetleaves,merged,final,nativeleaves=map(leaves,[old,target,merge,head,native])
assert len(final)==1409 and not ((oldleaves.keys()|targetleaves.keys())-final.keys())
guides={'docs/skills/repository-operations.md','docs/skills/work-items.md'}
assert all(final[p]==merged[p] for p in final if p not in guides)
assert {p for p in merged if merged[p] not in [oldleaves.get(p),targetleaves.get(p)]} <= guides
assert all(merged[p]==targetleaves[p] for p in targetleaves.keys()-oldleaves.keys())
inventory=json.loads(pathlib.Path('/workspace/actions-cloud/receipts/pr310-fbde-refresh/current-producer-input-inventory.json').read_text())
selected=json.loads(pathlib.Path('/workspace/actions-cloud/receipts/pr310-fbde-refresh/local-refresh-receipt.json').read_text())['source_union']['selected_test_paths']
assert len(inventory)==268 and len(selected)==5
assert all(final[p]==v==oldleaves[p]==targetleaves[p]==nativeleaves[p] for p,v in inventory.items())
assert all(final[p]==oldleaves[p]==targetleaves[p]==nativeleaves[p] for p in selected)
historical=[p for p in oldleaves if p.startswith('docs/program/evidence/')]
assert all(final[p]==oldleaves[p] for p in historical)
github=[p for p in targetleaves if p.startswith('.github/')]
assert all(final[p]==targetleaves[p] for p in github)
gen='.github/workflows/_gen_workflows.py'
assert ast.dump(ast.parse(git('show',head+':'+gen)))==ast.dump(ast.parse(git('show',target+':'+gen)))
workflow=json.loads((out/'generator-roundtrip.json').read_text())
for p,h in workflow['sha256'].items():assert hashlib.sha256(git('show',head+':'+p)).hexdigest()==h
assert workflow['status']=='PASS' and workflow['all_tracked_yaml_before_after_identical']
bootstrap=json.loads((out/'bootstrap-reuse.json').read_text())
for p,h in bootstrap['inputs_sha256'].items():
    b=git('show',head+':'+p);assert hashlib.sha256(b).hexdigest()==h
    assert b==git('show',bootstrap['original_source']+':'+p)
assert bind(bootstrap['original_bootstrap_log'])['sha256']==bootstrap['original_log_sha256']
proof=json.loads((out/'source-union-proof.json').read_text())
full_receipt_hashes={'pr310-actual-native-pair.json':'e95abb8f7024148019085d630f5755c8472290eabc3ad51537331f95e50b8b64','pr310-independent-actual-review.json':'4d5ed4117610c4d246272556ee31036a14eff85b1ab2e60d64116160c00dccb4','pr310-original-platform-independent-review.json':'c600dfc1cea6208de8698b933ee0597b1c874a9ac8de9dec1bd2779fa5a623d7'}
for name,h in full_receipt_hashes.items():assert bind(proof['retained_receipt_sha256_identities_not_git_commits'][name]['path'])['sha256']==h
failure=pathlib.Path('/workspace/engineering/current-admission-review/310-terminal-first-readiness-independent-review.json')
assert bind(failure)['sha256']=='de53338aa808a3d7308901761f3fcfa5598de5f000e678f7146952bf2268cfc2'
for name,summary in [('toolkit.log','69 passed'),('scoped.log','88 passed, 3 deselected'),('full-source.log','1154 passed, 12 skipped'),('static.log','Success: no issues found in 337 source files')]:
    text=(out/name).read_text();assert summary in text and 'actual main robot run" was SUCCESS' in text
assert git('diff','--name-only',merge,head).decode().splitlines()==sorted(guides)
operations=git('show',head+':docs/skills/repository-operations.md').decode()
workitems=git('show',head+':docs/skills/work-items.md').decode()
for phrase in ['previous mark','not a Git commit','does not establish a failure','absence']:
    assert phrase.lower() in operations.lower()
for phrase in ['template-rollback variant','Neither receipt proves a public registry installation','natural Runtime','65c0cb83','92498aff','no production repair']:
    if phrase=='no production repair':assert 'not a production repair' in workitems
    else:assert phrase in workitems
subprocess.check_call(['git','-C',str(repo),'diff','--check',old,head])
receipt={
 'verdict':'GO_EXACT_SOURCE_REFRESH_FOR_NORMAL_PUSH_ONLY; HOLD_FRESH_HOSTED_CI_AND_MERGE_ADMISSION',
 'head':head,'tree':'17c1afa7fbaa6ae817830d85226b41f67dd8b820','parent':merge,
 'ordinary_refresh':{'commit':merge,'tree':'5e7b7f481345a2637fa59af1d379414e2350d628','ordered_parents':[old,target]},
 'complete_union':{'leaves':1409,'no_parent_leaf_missing':True,'every_nondoc_final_mode_blob_equals_ordinary_merge':True,'all_incoming_target_only_leaves_preserved':True,'all268_native_producer_and5_selected_inputs_equal_old_target_original92498':True,'tracked_historical_evidence_leaves_unchanged':len(historical),'whole_github_AST_and_blobs_equal_actual_target':True,'all8_generated_workflows_plus_all_tracked_YAML_and_dependabot_roundtrip':'PASS'},
 'source_changes':'Accepted311 observer/fixture/tests/workflow imported by normal merge; only2canonicalguides novel after ordinary merge; no production/process/RCC/_selftest or deadline changes',
 'observer_scope':'Windows native watched-reload and duplicate-resource only80/88; duplicate-template unsampled; best-effort artifact observation not cause repair, full cleanup proof or V2 implementation',
 'local_gates':{'Doctor':'PASS','Bootstrap':'PASS prepared own worktree reuse24exact unchangedinputs','Toolkit':'69PASS','focused':'88PASS3integrationdeselected','full_portable_source':'1154PASS12SKIP15warnings','configured_lint':'PASS Ruff rules/format301 and Isort','configured_typecheck':'PASS337files','canonical_workflow_regeneration':'PASS','diffcheck':'PASS'},
 'gates_and_proofs':{n:bind(out/n) for n in ['doctor.log','bootstrap-reuse.json','toolkit.log','scoped.log','full-source.log','static.log','source-union-proof.json','generator-roundtrip.json','generator-roundtrip.log']},
 'retained_native_receipt_content_identities':full_receipt_hashes,
 'old_failure':bind(failure),
 'historical_limits':'4b Runtime Windows3FIRSTtimeouts distinct from currentold nativeUI3OSselectedPASS; cleanupUNKNOWN and causeUNKNOWN. Linux92498/f506 pair distinct from original65c MacWin tuple; missingnativeJUnit/browserliveidentity, localcandidateCore, seedfixture and incidentalMac teardown remain in unchanged c600 review. No original proof relabeling or rerun/rebuild.',
 'fresh_requirements':'Root must normalpush exactdfca then reconcile completefreshsource/currenttarget CI, Runtime included, before merge. Old21SUCCESS+1SKIP+1FAIL is historical only; no carry. Full208/private/release remain held.',
 'Documentation improvement':{'Canonical file changed or proposed':'docs/skills/repository-operations.md and docs/skills/work-items.md integrated in exactdfca','Durable learning captured':'Completeprevious-mark timing and FIRSTfailure scopes; receipt SHA256 separatefrom Git source ancestry; originalplatform/candidateCore/native cleanup scopes separatefrom fullRuntimeCI','Evidence':'de5333-node failure; immutableRCC4148; corrected evidenceproof; original4d5/e95/c600; all1409union/268+5 and configuredgates','Stale or ambiguous guidance removed':'MacWin stillunverified despite scopedoriginalreceipts; UIcreation-only statement despite separateworkerconsumer evidence; progress15total; receiptsha as commit; selectedUIpass admits Runtime','Remaining uncertainty':'Freshhostedunion CI/native Runtime FIRSTcause/explicitcleanup; templateobserverabsent; candidate/publicCore/nativebrowseridentity/private/fullrelease limits'},
 'Upstream disposition':'none',
}
p=out/'independent-source-freeze-review.json';p.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(bind(p)))
