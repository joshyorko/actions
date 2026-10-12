import ast,hashlib,json,subprocess,zipfile
from pathlib import Path
r=Path('/workspace/engineering/pr302');e=Path('/workspace/engineering/pr302-actual310-control-refresh');out=Path('/workspace/engineering/pr302-Cprime-independent-control-review');sha=lambda b:hashlib.sha256(b).hexdigest()
p=e/'control-Cprime-frozen-checkpoint.json';assert sha(p.read_bytes())=='a96bb92e2d2bac6602ff5ff944c916bf2acbab68681d0c54c467af04e7eedf1e';c=json.loads(p.read_bytes())
def git(*args):return subprocess.check_output(['git','-C',str(r),*args])
def text(*args):return git(*args).decode().strip()
def raw(ref,p):return git('show',ref+':'+p)
def leaves(ref):return {n.decode():tuple(h.decode().split()) for h,n in (x.split(b'\t',1) for x in git('ls-tree','-rz',ref).split(b'\0') if x)}
C=c['control_Cprime'];S=c['source_Sprime'];ST=c['source_tree'];assert C!=S
assert text('rev-parse','HEAD')==C and text('rev-parse','HEAD^{tree}')==c['control_tree'] and text('rev-parse',S+'^{tree}')==ST
assert text('show','-s','--format=%P',C).split()==[S] and not git('status','--porcelain') and text('branch','--show-current')==c['branch']
A,B=leaves(S),leaves(C);assert set(A)==set(B) and len(B)==1409
allowed={'.github/workflows/_gen_workflows.py','.github/workflows/actions_runtime_rcc_provider_rollback.yml','developer/tests/test_rcc_provider_rollback_workflow.py'}
changed={p for p in A if A[p]!=B[p]};assert changed==allowed
oldsha=c['preserved_prior_acceptance']['S'];oldtree=c['preserved_prior_acceptance']['S_tree'];counts={}
for p in allowed:
 assert A[p][:2]==B[p][:2]
 before,after=raw(S,p),raw(C,p)
 assert after.replace(S.encode(),oldsha.encode()).replace(ST.encode(),oldtree.encode())==before
 counts[p]={'sha_occurrences':after.count(S.encode()),'tree_occurrences':after.count(ST.encode())}
 if p.endswith('.py'):
  b,a=ast.parse(before),ast.parse(after)
  class Pins(ast.NodeTransformer):
   def visit_Constant(self,n):
    if n.value==S:n.value=oldsha
    elif n.value==ST:n.value=oldtree
    return n
  assert ast.dump(Pins().visit(a))==ast.dump(b)
  assert counts[p]=={'sha_occurrences':1,'tree_occurrences':1}
 else: assert counts[p]=={'sha_occurrences':3,'tree_occurrences':2}
for p,(mode,kind,oid) in B.items():
 if p not in allowed:assert B[p]==A[p]
 if kind=='blob':
  assert (r/p).read_bytes()==raw(C,p),p
  assert bool((r/p).stat().st_mode&0o111)==(mode=='100755'),p
assert len(set(A)-allowed)==1406
checked={}
for k,v in c['evidence_files'].items():
 data=Path(v['path']).read_bytes();assert sha(data)==v['sha256'] and len(data)==v['size'],k;checked[k]=v
for k,v in c['immutable_source_prerequisites'].items():
 data=Path(k).read_bytes();assert sha(data)==v['sha256'] and len(data)==v['size'],k
srpath=Path('/workspace/engineering/pr302-Sprime-independent-source-review/independent-Sprime-source-review-v2.json');sr=json.loads(srpath.read_bytes());assert sr['status']=='GO_SPRIME_SOURCE_FOR_CONTROL_AUTHORING_ONLY' and sr['source']['head']==S and sr['source']['tree']==ST
# Recheck every frozen S-prime evidence digest before relying on preserved full-suite evidence.
for k,v in sr['evidence_files'].items():
 data=Path(v['path']).read_bytes();assert sha(data)==v['sha256'] and len(data)==v['size'],k
# All source/runtime/test/toolkit/build/configuration and guidance leaves are exact S-prime.
assert B['docs/skills/repository-operations.md']==A['docs/skills/repository-operations.md']
patch=Path('/workspace/engineering/pr302-next-refresh-readonly/canonical-nine-source-bindings-proposed.patch');assert sha(patch.read_bytes())=='fef37515784cbf9fbb003ecca90ec0acb78d8e319bf2fd0ce2c2c1805ff955e6'
addition=''.join(x[1:]+'\n' for x in patch.read_text().splitlines() if x.startswith('+') and not x.startswith('+++')).encode();assert raw(C,'docs/skills/repository-operations.md').count(addition)==1
red=(e/'old-source-pin-RED-serial.log').read_text();green=(e/'new-source-pin-GREEN-static.log').read_text();toolkit=(e/'current-control-ToolkitTest.log').read_text();static=(e/'inherited-format-diagnosis-v2-and-remaining-static.log').read_text()
assert '1 failed, 54 passed in 21.52s' in red
assert "{'ref': '43a73f2dbc48ba9afcb43a22e98b1e087712cdc8'} != {'ref': 'd642a3ac24f8da85101538bdfdf59b509fd74bfb'}" in red
assert 'FAILED developer/tests/test_rcc_provider_rollback_workflow.py::test_rcc_rollback_workflow_is_opt_in_pinned_and_secret_free' in red
assert '55 passed in 21.01s' in green and 'All checks passed!' in green and 'Would reformat: .github/workflows/_gen_workflows.py' in green
assert '96 passed in 21.73s' in toolkit and 'actual main robot run" was SUCCESS' in toolkit
assert '1 file already formatted' in static and 'poetry run isort --check' in static and 'py_compile' in static and 'actual main robot run" was SUCCESS' in static
fd=c['extra_generator_formatter_diagnostic'];assert fd['same_parent_format_diff'] and (e/'generator-format-Cprime.diff').read_bytes()==(e/'generator-format-Sprime.diff').read_bytes()
for label,ref in [('Sprime',S),('Cprime',C)]:
 v=fd['records'][label];assert v['returncode']==1 and sha(raw(ref,'.github/workflows/_gen_workflows.py'))==v['source_sha256'];assert sha((e/f'generator-format-{label}.diff').read_bytes())==v['diff_sha256']
# Exact earlier raw seven-member proof remains historical; no download or rerun.
a=c['preserved_prior_acceptance']['artifact'];assert sha(Path(a['local_path']).read_bytes())==a['sha256'] and Path(a['local_path']).stat().st_size==a['size']
with zipfile.ZipFile(a['local_path']) as z:
 for v in a['members']:
  d=z.read(v['member']);assert sha(d)==v['sha256'] and len(d)==v['size']
summary=json.loads(zipfile.ZipFile(a['local_path']).read('rcc-provider-rollback-evidence/acceptance-summary.json'));assert summary['source']['candidate_sha']==oldsha and summary['source']['workflow_control_sha']==c['preserved_prior_acceptance']['C']
assert text('rev-parse','HEAD')==C and not git('status','--porcelain')
res={'status':'GO_CPRIME_FOR_NORMAL_EXISTING_BRANCH_PUSH_ONLY','control':{'head':C,'tree':c['control_tree'],'ordered_parents':[S],'branch':c['branch'],'clean':True},'source_candidate':{'head':S,'tree':ST,'source_not_control_self':True,'independent_review_sha256':sha(srpath.read_bytes())},'checkpoint':{'path':str(p),'sha256':sha(p.read_bytes())},'review_operations':'Read-only Git body/mode/AST/hash and frozen-log readback; external evidence only. No gateway/toolkit/package/test/regeneration/product/native/provider execution.','verified':{'only_three_declared_paths_changed':sorted(changed),'all1406_other_leaves_body_mode_type_exact_Sprime':True,'all1409_working_bytes_modes_match_Cprime':True,'whole_generator_AST_only_two_source_pins':True,'whole_test_AST_only_two_expected_constants':True,'generated_RCC_workflow_only_threeSHA_twoTREE_identity_substitutions':counts['.github/workflows/actions_runtime_rcc_provider_rollback.yml'],'all_unrelated_workflows_and_dependabot_exact':True,'three_selectors_profile_one_publish_Core102_raw_summary_RCCbinary_deadlines_and_every_other_AST_predicate_exact':True,'meaningful_pin_RED':'1FAIL54PASS: actualoldcandidate_checkoutref rejects reviewedSprime','GREEN':'55PASS21.01s existingworkflow/actualsummaryvalidatorcontrols','ToolkitTest':'96PASS21.73s/configuredRuff/RCCSUCCESS','changed_generator_and_test_Ruff':'PASS','changed_test_format':'PASS','configured_Poetry_Isort':'PASS','compile':'PASS','diffcheck':'writerPASS/frozenexactidentitydiff inspected','source_full_gates':'Correctly reused S-prime1169PASS13SKIP/scoped109PASS4SKIP/type337/fullconfiguredlint because every affectedpackage/build/toolkit leaf unchanged','extra_generator_format':'Not PASS; S-prime and C-prime return1 with byte-identical47a7db diff. Accepted inherited diagnostic outside two-pin scope; no unrelated format edits or waiver of configured source checks.','canonical_fef375_exact_retained':'S-prime lesson occurs once/guideblob unchanged','original7member_artifact_and_old_candidate_control_identity':'Verified unchanged/historical only'},'evidence_files':checked,'preserved_HOLDs':c['preserved_HOLDs'],'native_reuse':'92498UNQUALIFIED changedadapter from earlierSprime, selected5 equality does not close fullproducer qualification','next_gate':'Root may normal-push existing branch after this exact review. Fresh current S-prime/C-prime hostedLinuxthreecase and fulltestedmergeCI required before integration; no actual/merge authorization granted by reviewer.','Documentation_improvement':c['Documentation_improvement'],'canonical_review_disposition':'Exact fef375 lesson integrated S-prime and retained byte-exact in C-prime; independent review confirms source/control/fullproducer/testedmerge separation. No cosmetic duplicate delta.','Upstream_disposition':'none','retained_306':'fd8621 recurrence+4d08 acceptedV2adaptation remains read-only/source-ready proposal; no observer implementation or actualretry.'}
res['review_script_sha256']=sha(Path(__file__).read_bytes());f=out/'independent-Cprime-control-review.json';f.write_text(json.dumps(res,indent=2)+'\n');f.chmod(0o444);print(json.dumps({'status':res['status'],'receipt':str(f),'sha256':sha(f.read_bytes()),'size':f.stat().st_size}))
