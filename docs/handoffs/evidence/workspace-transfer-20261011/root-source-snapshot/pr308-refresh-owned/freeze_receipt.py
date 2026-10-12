import hashlib,json,subprocess,tomllib
from pathlib import Path
root=Path('/workspace/engineering/pr308');owned=Path(__file__).resolve().parent

def git(*args):return subprocess.check_output(['git',*args],cwd=root)
def evidence(path):
 p=Path(path);return {'path':str(p),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
head,tree,*parents=git('log','-1','--format=%H %T %P').decode().strip().split();assert head=='483e3e735c268b08acba1fd3930a9a34e0deaa91';assert not git('status','--porcelain')
merge='493ecbd2c9163786675cc0cc9b3853e6e75ca196';original='94716b90d85a171872e46b1efa8a1fb419e8a0c7';target='fbde0d3a248c47c9964851355f96575c89a87329';assert parents==[merge]
protected=[]
base=root/'docs/program/evidence/runtime-frozen-current-source-20261011'
for name,count in [('producer-input-inventory.json',268),('selected-test-inventory.json',5)]:
 data=json.loads((base/name).read_text());assert len(data)==count
 for path,expected in data.items():
  mode,kind,blob=git('ls-tree',head,'--',path).decode().strip().split('\t')[0].split()
  actual={'mode':mode,'kind':kind,'blob':blob,'sha256':hashlib.sha256(git('show',head+':'+path)).hexdigest()};assert actual==expected,path
 protected.append({'inventory':name,'entries':count,'all_blobs_modes_sha256_match':True,'inventory':evidence(base/name)})
(owned/'frozen-producer-parity-receipt.json').write_text(json.dumps({'head':head,'tree':tree,'checks':protected},indent=2)+'\n')
source_paths=['action_server/scripts/verify_dakota_rcc_acceptance.py','action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py']
for path in source_paths:assert git('ls-tree',original,'--',path)==git('ls-tree',head,'--',path)
for name,phrase in [('scoped-verifier.log','37 passed, 1 deselected'),('toolkit-test.log','69 passed'),('configured-gates.log','1134 passed, 13 skipped')]:assert phrase in (owned/name).read_text()
assert 'Success: no issues found in 334 source files' in (owned/'configured-gates.log').read_text()
roundtrip=json.loads((owned/'workflow-roundtrip-receipt.json').read_text());assert roundtrip['all_eight_exact'];assert len(roundtrip['outputs'])==8
for row in roundtrip['outputs']:assert hashlib.sha256((root/row['path']).read_bytes()).hexdigest()==row['sha256']
files=['doctor.log','bootstrap.log','toolkit-test.log','scoped-verifier.log','configured-gates.log','union-receipt.json','preservation-receipt.json','producer-parity-receipt.json','frozen-producer-parity-receipt.json','workflow-roundtrip.log','workflow-roundtrip-receipt.json','generated-setup-disposition.json']
history=[]
for name in ['candidate-wheel-67e82ef7.json','candidate-wheel-e33987b6.json']:
 path=root/'action_server/tests/acceptance_evidence'/name;r=json.loads(path.read_text());assert git('ls-tree',original,'--',str(path.relative_to(root)))==git('ls-tree',head,'--',str(path.relative_to(root)));history.append({'file':evidence(path),'original_source':r['source_sha'],'wrapper_exitCode':r['rcc_receipt']['exitCode'],'retained_unchanged':True})
versions={p:tomllib.loads((root/p/'pyproject.toml').read_text())['tool']['poetry']['version'] for p in ['actions','actions-http-helper','action_server']}
record={
 'status':'LOCAL_SOURCE_REFRESH_GO; INDEPENDENT_REVIEW_REQUIRED_BEFORE_ROOT_NORMAL_PUSH; FRESH_CI_REQUIRED',
 'source':{'branch':'fix/rcc-candidate-wheel-identities-20261010','head':head,'tree':tree,'parents':parents,'ordinary_merge':json.loads((owned/'union-receipt.json').read_text()),'candidate_verifier_and_formatter_test_original_preserved':{p:evidence(root/p) for p in source_paths},'only_novel_change':'11 canonical guide lines after exact ordinary merge','preservation':json.loads((owned/'preservation-receipt.json').read_text()),'clean':True,'unrelated_master_not_integrated':True,'authority_target':'integration/community-release-20261008 exactfbde;310 not integrated when refreshed'},
 'candidate_identity':{'checked_out_poetry_metadata_versions':versions,'implementation_preserved':'pinnedPoetry version read -> selectedfilename -> uniqueUTF8METADATA Name/Version -> CandidateWheel -> fixture/result/receipt versions and filename/hash','service_free_fixture':'synthetic Core/Helper1.0.3 wheelZIP pair; metadata-version1.0.2 poison rejected; actual Poetry build calls replaced by test fake','production_floors_and_lockfiles_unchanged_by_lane':True},
 'validation':{'doctor':'PASS','bootstrap':'PASS; installer serialized with305 lane','toolkit':'69PASS','scoped_verifier':'37PASS / 1 realRCC integration test deselected','configured_package':'1134PASS / 13existingSKIP / 15warnings; configured lint and Mypy334PASS','configured_markdown_lint':'optional tool absent, task reports warning; canonical delta passes git diff --check','generator':'all8 exact byte roundtrip, generator/workflow unchanged','producer_parity':'all268 producerinputs plus5 selectedtests match retained blob/mode/SHA256 inventory at frozen head','gate_source':'ran on exact ordinary merge493ecbd2 with docworkingtree delta; final483e3e73 only commits those11doclines and preserves all1405 otherblob/modepairs','actual_RCC_test':'NOT_RUN; ACTIONS_REAL_RCC_ACCEPTANCE unset and realRCC marker explicitly deselected; full source excludesintegration_test','acceptance_CLI_provider_cache_jobs':'NOT_RUN; parser/help/no-side-effect admission unit tests are service-free controlled source tests'},
 'evidence':{f:evidence(owned/f) for f in files},'prior_live_inventory':evidence('/workspace/engineering/pr308-live-inventory.json'),
 'historical_receipts':history,
 'held_gates':['fresh hostedCI for483e3e73 union','actual sourceRuntime RCC wrapper/admission/provider-unavailable warmreuse','private134 missing originalsource/spec and fullacceptance','native frozen/Go qualification remains separately producer/sourcebound; no broad issue/release completion','no standalone acceptanceCLI/provider/cache invocation or publication/merge in this lane'],
 'Documentation improvement':{'Canonical file changed or proposed':'Changed docs/skills/repository-operations.md in483e3e73', 'Durable learning captured':'Controlled synthetic candidate ZIPs qualify checked-source version/filename/METADATA identity behavior, not an actual packagebuild/RCC/provider/warmreuse result. Candidate refreshes must check full producer/test inventories and preserve older receipt source/wrapperfailure identities.', 'Evidence':'original94716 verifier/test blob+mode pairs unchanged; scoped37 with explicitrealRCCdeselection; current1134/13 configured gates;69Toolkit;8exact outputs;268+5 frozen parity; retained historical67e82/e339 failedwrapper receipts', 'Stale or ambiguous guidance removed':'Clarifies that candidateversion regression is a synthetic producer control and that preserved producerbytes do not relabel previous actualcandidate receipts; no historical guidance/receipts removed', 'Remaining uncertainty':'New483e3e73 hostedCI pending; actualRCC/provider-unavailable/native/private134 and wholeissue/release gates are not established by source checks.'},
 'windows_design_disposition':{'V2':'read-only designGO, originalV1 retained; no311 edits','receipt':evidence('/workspace/engineering/windows-next-observation-owned/design-v2-receipt.json'),'independent':evidence('/workspace/engineering/windows-next-observation-independent-review/independent-v2-design-review.json'),'next_source_slot':'root queues minimaltest-only observation only afterd75terminal readback still lacksneededfields and explicitwriter assignment; no299/311 mutations authorized here'},
 'Upstream disposition':'none; no maintained upstream defect established and no authorized external issue target'
}
(owned/'successor-receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'head':head,'tree':tree,'receipt':evidence(owned/'successor-receipt.json')}))
