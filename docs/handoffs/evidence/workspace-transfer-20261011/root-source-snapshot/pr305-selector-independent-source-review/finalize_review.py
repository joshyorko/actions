import hashlib,json,re,subprocess
from pathlib import Path
own=Path(__file__).resolve().parent
writer=Path('/workspace/actions-cloud/receipts/pr305-selector-fix')
def evidence(p):
 p=Path(p);return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
freeze=writer/'frozen-current-union-source-checkpoint.json'
assert evidence(freeze)['sha256']=='ccfb6baa0a3e63b446ce388bfe00519cfcf992ba2821053e44a91528043381e9'
f=json.loads(freeze.read_text())
for group in ['logs','source_proofs','actual_predecessors']:
 for row in f[group]:assert evidence(row['path'])['sha256']==row['sha256'],row['path']
for row in [f['documentation_improvement']['exact_delta'],f['documentation_improvement']['guide_bytes']]+[r['patch'] for r in f['documentation_improvement']['reviewer_patch_disposition']]:assert evidence(row['path'])['sha256']==row['sha256']
p=json.loads((own/'preliminary-source-review.json').read_text());assert (f['head'],f['tree'],f['ordered_parents'])==(p['head'],p['tree'],p['ordered_parents'])
log=(writer/'current-union-full-source-gates.log').read_text()
for text in ['1170 passed, 12 skipped, 15 warnings in 139.28s','69 passed','20 passed, 2 deselected','302 files already formatted','Success: no issues found in 338 source files','actual main robot run" was SUCCESS']:
 assert text in log,text
assert f['tests']['configured_Runtime_invoke_test_not_integration']['workers']==2
assert f['tests']['scoped_authoring_and_admission']=={'integration_deselected':2,'passed':20,'skipped':0}
repo=Path('/workspace/engineering/pr305')
assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo).decode().strip()==p['head']
p['status']='GO_SOURCE_CONTROLS_NORMAL_PUSH_REVIEW_ONLY; CURRENT_ACTUAL_ACCEPTANCE_NOT_RUN'
p['writer_frozen_checkpoint']=evidence(freeze)
p['fresh_configured_gates']=f['tests']
p['independent_review_source']=evidence(own/'review_source.py')
p['independent_source_gateway_log']=evidence(own/'source-review.log')
p['review_finalizer']=evidence(__file__)
p['frozen_evidence_hashes_verified']=f['logs']+f['source_proofs']+f['actual_predecessors']
p['canonical_proposal_disposition']=f['documentation_improvement']['reviewer_patch_disposition']
p['Documentation improvement']['Remaining uncertainty']='Fresh current-union hostedCI, immutable V4 runner qualification and separately authorized actual browser/five-tool-Run/shared-cache gate are pending. Historical14c actual receipts remain failures and do not become3ec actual results. WholeCorewheel/coldregistry/productionartifact/OAuth/full134 remain unqualified.'
p['limitations']=['No product/native/browser actual execution in independent source review; only eight synthetic result-admission controls and static/generator parity under canonical RCC gateway.','Source gates admit production input equivalence to the measured92498 build, not a new build or public acceptance run.','Configured lint reported Markdownlint unavailable; configured Ruff/Isort/typecheck pass. No skip/deadline/cleanup/ownership waiver.']
path=own/'independent-frozen-source-review.json';path.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(evidence(path)))
