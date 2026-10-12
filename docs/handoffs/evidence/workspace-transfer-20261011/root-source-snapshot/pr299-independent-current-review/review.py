from pathlib import Path
import hashlib
import json
import subprocess

REPO='/workspace/engineering/pr299'
OWNED=Path('/workspace/engineering/pr299-refresh-owned')
OUT=Path('/workspace/engineering/pr299-independent-current-review')
HEAD='80ba4c3adce0d0f5fd8a7040d271ab19433e4042'
TREE='3c78f95d814fe2603f40169783fc3c4a84cd6315'
MERGE='a99c21df257949006f0e55e14243e2fcac27c138'
ORIGINAL='9cb61c52fce35201221b55707d73da9e9b0840a6'
TARGET='fbde0d3a248c47c9964851355f96575c89a87329'
GUIDE='docs/skills/repository-operations.md'

def git(*args):return subprocess.check_output(['git','-C',REPO,*args])
def binding(p):
    raw=p.read_bytes();return {'path':str(p),'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def tree(h):
    result={}
    for row in git('ls-tree','-rz',h).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);result[path.decode()]=tuple(v.decode() for v in meta.split())
    return result

assert git('log','-1','--format=%H %T %P',HEAD).decode().strip()==f'{HEAD} {TREE} {MERGE}'
assert git('log','-1','--format=%P',MERGE).decode().strip()==f'{ORIGINAL} {TARGET}'
assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain')
a,b=tree(MERGE),tree(HEAD)
assert [p for p in sorted(a.keys()|b.keys()) if a.get(p)!=b.get(p)]==[GUIDE]
assert sum(v==b.get(p) for p,v in a.items())==1415
ancestor=git('merge-base',ORIGINAL,TARGET).decode().strip()
base,source,target,union=map(tree,[ancestor,ORIGINAL,TARGET,MERGE])
checked=0;conflicted=[]
for p in set(base)|set(source)|set(target):
    s,t,v=source.get(p),target.get(p),base.get(p)
    if s==t:expected=s
    elif s==v:expected=t
    elif t==v:expected=s
    else:conflicted.append(p);continue
    assert union.get(p)==expected,p
    checked+=1
assert conflicted==[GUIDE]
auto=tree('ce235efe2f1a0984011a5b4ca3c8d94b6c397181')
assert {p:v for p,v in union.items() if p!=GUIDE}=={p:v for p,v in auto.items() if p!=GUIDE}
original_changed=[p for p in sorted(base.keys()|source.keys()) if base.get(p)!=source.get(p) and not p.startswith('docs/')]
assert len(original_changed)==23
assert all(b.get(p)==source.get(p) for p in original_changed)
guide=Path(REPO,GUIDE)
for h in [ORIGINAL,TARGET]:
    additions=[l[1:] for l in git('diff','--unified=0',ancestor,h,'--',GUIDE).decode().splitlines() if l.startswith('+') and not l.startswith('+++') and l[1:].strip()]
    assert all(line in guide.read_text() for line in additions)

receipt=OWNED/'successor-receipt.json'
assert binding(receipt)['sha256']=='0982b641af073a82c4105aa02538f7e21b219faf35e89d3f2818b9c96c5f5d52'
d=json.loads(receipt.read_text())
for e in d['evidence'].values():assert binding(Path(e['path']))==e
for e in [d['historical_windows']['299'],d['historical_windows']['311_original']]:assert binding(Path(e['path']))==e
inventory_results=[]
for name,count,expected_diff in [('producer-input-inventory.json',268,6),('selected-test-inventory.json',5,0)]:
    entries=json.loads(Path('/workspace/engineering/native292-owned',name).read_text())
    assert len(entries)==count
    assert git('show',HEAD+':docs/program/evidence/runtime-frozen-current-source-20261011/'+name)==Path('/workspace/engineering/native292-owned',name).read_bytes()
    diffs=[]
    for p,historical in entries.items():
        observed={'mode':b[p][0],'kind':b[p][1],'blob':b[p][2],'sha256':hashlib.sha256(git('show',HEAD+':'+p)).hexdigest()}
        if observed!=historical:
            assert b[p]==source[p]
            diffs.append({'path':p,'historical':historical,'current_original299_preserved':observed})
    assert len(diffs)==expected_diff
    inventory_results.append({'inventory':name,'entries':count,'matches':count-expected_diff,'differences':diffs})
added=[p for p in original_changed if p.startswith('action_server/src/') and p not in base]
assert len(added)==6
assert sorted(added)==sorted(e['path'] for e in d['producer_comparison']['original299_added_producer_paths_absent_from_historical_inventory'])
for e in d['producer_comparison']['original299_added_producer_paths_absent_from_historical_inventory']:
    assert e['sha256']==hashlib.sha256(git('show',HEAD+':'+e['path'])).hexdigest()

full=(OWNED/'configured-gates.log').read_text()
for needle in ['+ poetry run invoke test-not-integration','1182 passed, 13 skipped, 15 warnings','+ poetry run invoke lint','308 files already formatted','+ poetry run invoke typecheck','Success: no issues found in 344 source files','actual main robot run" was SUCCESS']:
    assert needle in full
scoped=(OWNED/'scoped-shared-run.log').read_text()
assert '189 passed, 1 skipped, 12 deselected' in scoped and '-m not integration_test' in scoped
assert '69 passed' in (OWNED/'toolkit-test.log').read_text()
assert 'not integration_test' in git('show',HEAD+':action_server/tasks.py').decode()
roundtrip=json.loads((OWNED/'workflow-roundtrip-receipt.json').read_text())
assert len(roundtrip['outputs'])==8 and roundtrip['all_eight_exact']
assert hashlib.sha256(git('show',HEAD+':.github/workflows/_gen_workflows.py')).hexdigest()==roundtrip['generator_sha256']
for e in roundtrip['outputs']:
    raw=git('show',HEAD+':'+e['path'])
    assert raw==(OWNED/'workflow-roundtrip'/Path(e['path']).name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==e['sha256'] and len(raw)==e['size']
    assert b[e['path']]==a[e['path']]==target[e['path']]
patch=OUT/'canonical-current-union-source-scope.patch'
patch.write_bytes(git('diff',MERGE,HEAD,'--',GUIDE))
assert git('diff','--numstat',MERGE,HEAD).decode().strip()==f'20\t0\t{GUIDE}'
subprocess.check_call(['git','-C',REPO,'diff','--check',MERGE,HEAD])
assert not Path(REPO,'action_server/setup.py').exists()
result={
 'verdict':'GO_NORMAL_PUSH_EXACT80BA_CURRENT_UNION_SOURCE_CONTROL; HOLD_FRESH_HOSTED_MERGE_REAL_NATIVE_BACKEND_ARTIFACT_AND_RELEASE_ACCEPTANCE',
 'scope':'read-only ordinary refresh/source preservation/evidence review; no gate rerun/native/provider/browser/build/PR300/source mutation',
 'source':{'head':HEAD,'tree':TREE,'parent':MERGE,'merge_tree':git('rev-parse',MERGE+'^{tree}').decode().strip(),'ordinary_merge_ordered_parents':[ORIGINAL,TARGET],'same_original_branch':'feat/shared-run-output-20261010','clean':True},
 'independent_union':{'common_ancestor':ancestor,'nonconflicting_parent_leaves_checked':checked,'only_conflict':conflicted,'complete_non_guide_tree_matches_existing_auto_merge_tree':True,'both_parent_guide_additions_retained':True,'original_changed_nondoc_paths':original_changed,'original23_mode_blob_pairs_preserved':True,'final_only_novel_delta':'20 canonical guide lines','followup_unchanged_blob_mode_pairs':1415},
 'artifact_producer_scope':{'retained_inventories_independently_mode_blob_sha_compared':inventory_results,'additional_original299_production_paths_outside_historical268_inventory':d['producer_comparison']['original299_added_producer_paths_absent_from_historical_inventory'],'old_frozen_artifact_carry':'NOT_QUALIFIED_FOR299; six changed plus six added producer inputs','selected_test_mode_blob_sha_matches':5},
 'current_source_validation':{'configured_nonintegration_pass':1182,'existing_skips':13,'warnings':15,'configured_lint':'PASS;308formatted','configured_typecheck_source_files':344,'focused_servicefree_pass':189,'existing_Windows_only_skip':1,'integration_deselected':12,'toolkit_pass':69,'all_generated_roundtrip_exact':8,'tested_source':'a99 ordinary merge with final20doc lines in workingtree; frozen80ba changes only guide and preserves all other1415mode/blobpairs','required_real_acceptance':'NOT_RUN','optional_Markdownlint':'unavailable as recorded by configured gate'},
 'worker_successor_receipt':binding(receipt),'verified_original_raw_evidence':d['evidence'],'historical_windows_receipts_preserved':{k:d['historical_windows'][k] for k in ['299','311_original']},
 'held_gates':['Fresh exact80ba complete hosted checks/reviews/merge gates; no prior green carry.','Old2999cb FIRSTnative startup90timeout/89.28variables/89.259previous-mark sum and incomplete20cleanup remain historical; current311d75pass is separate and does not clear299.','Original3111151sixFIRSTstartupfailures/two samplednodes remain separate; historical cause/cleanup dimensions not proven.','Current299 has six changed and six added production inputs relative to retained frozenartifact, so source/nativeartifact qualification requires actual new tuple.','Real PostgreSQL/backend/currentnative/browser/provider/private acceptance remains unqualified.','PR300 dependent refresh/integration must retain its accepted dependency order; this source review does not change300.','Private01f/fafb and frozenv6spec/runner release gates remain HOLD; no publication claim.'],
 'canonical_documentation':{'canonical_file':GUIDE,'canonical_binding':binding(guide),'exact_integrated_delta':binding(patch),'disposition':'INTEGRATED exact80ba doconly20line followup retaining both parent lessons','durable_learning':'RCC18.19.3 elapsed fields are previous-mark intervals; preserve complete series/caller/owned cleanup dimensions and source-bound failures through ordinary refresh','evidence':'immutable4148 semantics; retained4eef/81b historical sourcebound diagnoses; independently preserved23source/testpaths and current1182/13+189/69+8configured source gates','stale_ambiguity':'finalinterval-as-total;66.491-as-UV-duration;incompletecleanup-note-as-specificleak;branchrefresh-or-current311pass-as-299failure-clearance;unchangedselectedtests-as-producerartifactparity','remaining_uncertainty':'fresh exactunion CI/native/backend/currentartifact acceptance, historical Windows cause/cleanup dimensions, private/full issue/release graph','upstream':'none'},
 'setup_py_disposition':'absent at reviewerfreeze; no generic cleanup/deletion by reviewer; worker says initialreadback/freeze absent',
 'no_actual_rerun_source_mutation_or_infrastructure':True,
}
p=OUT/'independent-current-source-review.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(binding(p)))
