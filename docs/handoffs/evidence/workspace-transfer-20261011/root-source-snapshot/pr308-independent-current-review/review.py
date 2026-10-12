from pathlib import Path
import hashlib
import json
import subprocess

REPO='/workspace/engineering/pr308'
OWNED=Path('/workspace/engineering/pr308-refresh-owned')
OUT=Path('/workspace/engineering/pr308-independent-current-review')
HEAD='483e3e735c268b08acba1fd3930a9a34e0deaa91'
TREE='9b69d78117e0e5cade3f59fcacc6db56a747b61f'
MERGE='493ecbd2c9163786675cc0cc9b3853e6e75ca196'
ORIGINAL='94716b90d85a171872e46b1efa8a1fb419e8a0c7'
TARGET='fbde0d3a248c47c9964851355f96575c89a87329'

def git(*args):return subprocess.check_output(['git','-C',REPO,*args])
def binding(p):
    b=p.read_bytes();return {'path':str(p),'size':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def tree(h):
    d={}
    for row in git('ls-tree','-rz',h).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);d[path.decode()]=tuple(v.decode() for v in meta.split())
    return d

assert git('log','-1','--format=%H %T %P',HEAD).decode().strip()==f'{HEAD} {TREE} {MERGE}'
assert git('log','-1','--format=%P',MERGE).decode().strip()==f'{ORIGINAL} {TARGET}'
assert not git('status','--porcelain')
a,b=tree(MERGE),tree(HEAD)
assert [p for p in sorted(a.keys()|b.keys()) if a.get(p)!=b.get(p)]==['docs/skills/repository-operations.md']
assert sum(v==b.get(p) for p,v in a.items())==1405
ancestor=git('merge-base',ORIGINAL,TARGET).decode().strip()
base,source,target,union=map(tree,[ancestor,ORIGINAL,TARGET,MERGE])
checked=0; conflicted=[]
for p in set(base)|set(source)|set(target):
    s,t,v=source.get(p),target.get(p),base.get(p)
    expected=None
    if s==t:expected=s
    elif s==v:expected=t
    elif t==v:expected=s
    else:conflicted.append(p);continue
    assert union.get(p)==expected,p
    checked+=1
assert set(conflicted)<= {'docs/skills/repository-operations.md'}
for p in ['action_server/scripts/verify_dakota_rcc_acceptance.py','action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py']:
    assert b[p]==source[p]
    assert Path(REPO,p).read_bytes()==git('show',HEAD+':'+p)
guide=Path(REPO,'docs/skills/repository-operations.md')
for h in [ORIGINAL,TARGET]:
    additions=[l[1:] for l in git('diff','--unified=0',ancestor,h,'--','docs/skills/repository-operations.md').decode().splitlines() if l.startswith('+') and not l.startswith('+++') and l[1:].strip()]
    assert all(line in guide.read_text() for line in additions)
for name,count in [('producer-input-inventory.json',268),('selected-test-inventory.json',5)]:
    entries=json.loads(Path('/workspace/engineering/native292-owned',name).read_text())
    assert len(entries)==count
    for p,d in entries.items():
        assert b[p][2]==d['blob'] and b[p][0]==d['mode']
        raw=git('show',HEAD+':'+p);assert hashlib.sha256(raw).hexdigest()==d['sha256']
receipt=OWNED/'successor-receipt.json'
assert binding(receipt)['sha256']=='87f2252e89bdc9f1368a2ea2a0b9b55095606567517e3f378a3a0ce23a5f7f1d'
d=json.loads(receipt.read_text())
for e in d['evidence'].values():assert binding(Path(e['path']))==e
for old in d['historical_receipts']:
    f=Path(old['file']['path']);assert binding(f)==old['file']
    relative=str(f.relative_to(REPO));assert b[relative]==source[relative]
    assert old['wrapper_exitCode']==-1
full=(OWNED/'configured-gates.log').read_text()
for needle in ['+ poetry run invoke test-not-integration','1134 passed, 13 skipped','+ poetry run invoke lint','298 files already formatted','+ poetry run invoke typecheck','Success: no issues found in 334 source files','actual main robot run" was SUCCESS']:
    assert needle in full
assert '37 passed, 1 deselected' in (OWNED/'scoped-verifier.log').read_text()
assert '69 passed' in (OWNED/'toolkit-test.log').read_text()
roundtrip=json.loads((OWNED/'workflow-roundtrip-receipt.json').read_text())
assert len(roundtrip['outputs'])==8 and roundtrip['all_eight_exact']
for e in roundtrip['outputs']:
    raw=git('show',HEAD+':'+e['path'])
    assert raw==(OWNED/'workflow-roundtrip'/Path(e['path']).name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==e['sha256']
    assert b[e['path']]==a[e['path']]
patch=OUT/'canonical-current-version-source-scope.patch'
patch.write_bytes(git('diff',MERGE,HEAD,'--','docs/skills/repository-operations.md'))
subprocess.check_call(['git','-C',REPO,'diff','--check',MERGE,HEAD])
result={
 'verdict':'GO_NORMAL_PUSH_EXACT483E_CURRENT_UNION_SOURCE_CONTROL; HOLD_CURRENT_HOSTED_MERGE_AND_REAL_CANDIDATE_RCC_ACCEPTANCE',
 'scope':'read-only current source/control/evidence review; no reviewer actual test/RCC/native/provider/cache execution or source mutation',
 'source':{'head':HEAD,'tree':TREE,'parent':MERGE,'ordinary_merge_ordered_parents':[ORIGINAL,TARGET],'merge_tree':git('rev-parse',MERGE+'^{tree}').decode().strip(),'clean':True},
 'independent_union':{'common_ancestor':ancestor,'nonconflicting_parent_leaves_checked':checked,'conflicted_guide_paths':conflicted,'both_parent_guide_additions_retained':True,'original_verifier_and_candidate_control_blobs_modes_preserved':True,'only_followup_delta':'11 canonical guide lines','followup_unchanged_blob_mode_pairs':1405,'native_producer_inputs_mode_blob_sha_verified':268,'selected_test_inputs_mode_blob_sha_verified':5,'production_versions_locks_Rcc_process_selftest_fixtures_workflows_preserved':True},
 'source_behavior_review':['PinnedPoetry reads actual checkedout package versions before building both owned candidate wheels; no hardcodedCore1.0.2 relabeling.', 'Expected distribution/version determine selected wheel filename and exactName/Version admission from uniqueMETADATA member; mismatch stops use.', 'Candidate records bind actual wheel filename/version/digest and expected managed-action results to the same candidate versions.', 'Original synthetic baseline verifies source/filename/METADATA tuple; independent metadata-version poison meaningfully rejects mismatch.', 'No Runtime/Core/Helper production, publicfloor, releasepin, nativefixture or workflow policy changed in this refresh.'],
 'current_validation':{'configured_test_not_integration_pass':1134,'existing_skips':13,'configured_lint':'PASS','configured_typecheck_source_files':334,'scoped_source_controls_pass':37,'real_RCC_optin_test_deselected':1,'toolkit_pass':69,'all_generated_roundtrip_exact':8,'tests_source_tuple':'493 ordinary union; frozen483 only docs, all1405 otherblob/modepairs unchanged','optional_markdownlint':'unavailable; required implemented task warnings retained; canonicaldiffcheckPASS'},
 'original_worker_receipt':binding(receipt),'raw_evidence_hashes_verified':d['evidence'],'historical_receipts_retained':d['historical_receipts'],
 'held_gates':['Fresh exact483 hosted complete job/check/review gates are required before merge; no oldgreen carry.','Servicefree synthetic candidateversion controls do not prove actualPoetrywheel/RCC/provider/coldorwarmreuse/native/private acceptance.','Older candidate67e82/e339 receipt source/version identities and failedwrapperexit-1 remain historical; sourceparity does not repair or relabel them.','Unchanged268native producer inputs support scoped retainedartifact sourceparity only, not currentcandidatewheel or latermerged source qualification.','Original private01f/fafb chain and frozenv6spec/runner/publication gates remain HOLD; no infrastructure substitution.','Generated setup.py was absent atfreeze; worker discloses no retained bytes/digest and no manual/generic cleanup claim.'],
 'canonical_documentation':{'canonical_file':'docs/skills/repository-operations.md','canonical_binding':binding(guide),'exact_integrated_delta':binding(patch),'disposition':'INTEGRATED exact483 doconly followup, both parent sourceguidance retained','durable_learning':'synthetic checkedversion tuple controls are source admission, not realcandidateRCC/warmprovider/native execution; preserve previous failed receipt tuple','evidence':'preserved94716implementation/controls;37sourcecontrols1liveDESELECT;1134/13configured334type/69Toolkit/8roundtrip;268+5inventory;67e82/e339historicalfailures','stale_ambiguity':'passing mock version control proves realPoetrybuild or nativewarmreuse; unchanged producerbytes relabel olderactualsource/failedwrapper','remaining_uncertainty':'freshhosted/fullrealcandidate/privateissue/releasegates','upstream':'none'},
 'windows_design':'previous95f V2 designonlyGO remains separate; freshd75 readback ongoing; no implementation/run authorized',
}
p=OUT/'independent-current-source-review.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(binding(p)))
