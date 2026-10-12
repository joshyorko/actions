import hashlib,json,re,subprocess
from pathlib import Path
root=Path('/workspace/engineering/pr309');out=Path('/workspace/engineering/pr309-actual311-refresh')
def git(*a):return subprocess.check_output(['git','-C',str(root),*a]).decode().strip()
def bind(p):
 p=Path(p);d=p.read_bytes();return {'path':str(p),'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()}
assert git('status','--porcelain')==''
assert git('diff','--name-only','51392cfcb6e8e09968e359e45a9ace3b4c6afbc0','HEAD')=='docs/skills/repository-operations.md'
for name in ('doctor','toolkit','scoped','full-source','static','generator-roundtrip'):
 text=(out/(name+'.log')).read_text();assert 'SUCCESS' in text,name
 assert 'FAILED' not in text and 'ERROR ' not in text,name
assert '69 passed' in (out/'toolkit.log').read_text()
assert '80 passed, 1 deselected' in (out/'scoped.log').read_text()
full=(out/'full-source.log').read_text();m=re.search(r'(\d+) passed, (\d+) skipped',full);assert m
static=(out/'static.log').read_text();n=re.search(r'Success: no issues found in (\d+) source files',static);assert n
assert 'poetry run isort --check src tests' in static and 'files already formatted' in static
old_receipts=[Path('/workspace/engineering/pr309-refresh-receipt.json'),Path('/workspace/engineering/pr309-independent-current-review/source-control-prepush-review.json')]
proof=json.loads((out/'source-union-proof.json').read_text())
receipt={'schema':'actions-pr309-actual311-source-refresh/v1','status':'FROZEN_SOURCE_FOR_INDEPENDENT_REVIEW_NO_PUSH','branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'tree':git('rev-parse','HEAD^{tree}'),'parent':git('rev-parse','HEAD^'),'ordinary_merge':{'head':proof['ordinary_merge'],'tree':proof['tree'],'ordered_parents':proof['ordered_parents']},'source_proof':bind(out/'source-union-proof.json'),'source_inspector':bind(out/'verify_source.py'),'all_old_target_leaves_retained':True,'original_route_test_exact':proof['owned_route_test'],'all268_plus_five_exact_old_actual_target92498':True,'whole_github_exact_target':True,'only_followup':'Canonical guide Counter multiplicity/normalized route identity clarification; no production/auth/test/workflow mutation','gates':{'Doctor':'PASS','Bootstrap':'REUSED exact24 inputs plus five own prepared package environments; no installer','Toolkit':69,'scoped_auth':{'pass':80,'integration_deselect':1,'skip':0},'full_configured_Runtime_source':{'pass':int(m[1]),'skip':int(m[2]),'workers':2},'full_configured_lint':'Ruff check/format/Isort PASS','typecheck_files':int(n[1]),'all_workflow_and_dependabot_roundtrip':'PASS'},'bootstrap_reuse':bind(out/'bootstrap-reuse.json'),'original_bootstrap':bind('/workspace/engineering/pr309-bootstrap.log'),'old_receipts_own_original_identities':[bind(p) for p in old_receipts],'gate_logs':{p.stem:bind(p) for p in sorted(out.glob('*.log'))},'generator_roundtrip':bind(out/'generator-roundtrip.json'),'documentation_improvement':{'Canonical_file_changed':'docs/skills/repository-operations.md','Exact_delta':bind(out/'canonical-actual-delta.patch'),'Durable_learning':'Route census compares Counter identities of class/path_format/full sorted methods; duplicated, missing, changed-class/method registrations fail alongside new routes. URL-set equality loses meaningful evidence.','Evidence':'Preserved test_auth_route_inventory._capture_routes/_classify_routes and scoped80PASS/1deselect plus full configured source gate; exact route test blob unchanged','Stale_or_ambiguous_guidance_removed':'Replaced new-route-only rejection description with precise multiplicity and identity contract','Remaining_uncertainty':'Registration/classification remains distinct from complete missing/wrong/valid credentials and side-effect matrix/full152; current full hosted/native execution pending'},'cached_GitHub_control':{'receipt':bind('/workspace/engineering/next-current-union-preparation-owned/pr309-current-prospective-control.json'),'scope':'Oldfbde/41d tested merge08f051/tree211cea; not the current1c75/5139 union. No earlier CI carried forward.'},'not_run':['Actual RCC/provider/native/browser gate','Fresh hosted CI','Full issue152'],'upstream_disposition':'none'}
(out/'frozen-source-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
for p in out.glob('*.log'):p.chmod(0o600)
print(json.dumps(bind(out/'frozen-source-receipt.json')))
