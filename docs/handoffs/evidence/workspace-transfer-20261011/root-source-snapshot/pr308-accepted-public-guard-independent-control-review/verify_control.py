import ast,copy,difflib,hashlib,json,os,re,subprocess
from pathlib import Path
R=Path('/workspace/engineering/pr308');S=Path('/workspace/engineering/pr308-accepted-public-guard-source');Q=Path('/workspace/engineering/pr308-accepted-public-guard-control');D=Path('/workspace/engineering/pr308-accepted-public-guard-independent-control-review')
H='b673ddd761ba4ccd68e9baa8faaa9ab666df794e';T='56d108fcdb5d43f7f27a8f2554fec51b702519f4';A='7eb5bce946750555ab009f77592862920a901506';AT='3ff76037779763d0461ff3a755b900c9ed83dcf8';OLD='d642a3ac24f8da85101538bdfdf59b509fd74bfb';OLDTREE='fdf2823ebcdbd938b9047fd452c9fb13eb4be4e4';B='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0';N='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e';BRANCH='fix/rcc-candidate-wheel-identities-20261010'
paths=['.github/workflows/_gen_workflows.py','.github/workflows/actions_runtime_rcc_provider_rollback.yml','developer/tests/test_rcc_provider_rollback_workflow.py'];guide='docs/skills/repository-operations.md'
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def read(p):return json.loads(Path(p).read_text())
def leaves(ref):return {n.decode():m.decode().split() for z in git('ls-tree','-rz',ref).split(b'\0') if z for m,n in [z.split(b'\t',1)]}
F=Q/'CONTROL-frozen-checkpoint.json';assert sha(F)=='4771821583f54164018854bee073ba8318d3164ea4e152324525913f6af734c6';f=read(F)
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse','HEAD^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A] and git('rev-parse',A+'^{tree}').decode().strip()==AT
assert git('status','--porcelain')==b'' and git('branch','--show-current').decode().strip()==BRANCH
a,c,b,n=map(leaves,[A,H,B,N]);assert set(a)==set(c) and len(c)==1409 and sorted(p for p in c if c[p]!=a[p])==sorted(paths);assert sum(c[p]==a[p] for p in c)==1406
refs=[]
for receipt in [f,read(S/'SOURCE-frozen-checkpoint.json')]:
 for r in receipt['evidence']:
  v=bind(r['path']);assert v['bytes']==r['size'] and v['sha256']==r['sha256'];refs.append(v)
assert len(refs)==47
for key in ['source_qualification_receipt','independent_source_GO']:
 r=f[key];v=bind(r['path']);assert v['sha256']==r['sha256'] and v['bytes']==r['size']
pre=read(Q/'final-precommit-control-hashes.json')['complete1409workinghashes'];assert set(pre)==set(c)
for p,v in c.items():assert (R/p).read_bytes()==git('cat-file','blob',v[2]) and sha(R/p)==pre[p] and bool(os.stat(R/p).st_mode&0o111)==(v[0]=='100755')
class Normalize(ast.NodeTransformer):
 def __init__(self):self.pins=[];self.branches=0
 def visit_Constant(self,node):
  if node.value in [A,AT]:self.pins.append(node.value);node.value=OLD if node.value==A else OLDTREE
  return node
 def visit_List(self,node):
  self.generic_visit(node)
  if any(isinstance(v,ast.Constant) and v.value==BRANCH for v in node.elts):
   assert [v.value for v in node.elts]==['test/rcc-provider-rollback-hosted-20261010','fix/rcc-published-artifact-details-20261010',BRANCH];self.branches+=1;node.elts=node.elts[:-1]
  return node
astscope={}
for p in [paths[0],paths[2]]:
 old=ast.parse(git('show',A+':'+p));new=ast.parse(git('show',H+':'+p));normal=Normalize();normalized=normal.visit(copy.deepcopy(new));assert ast.dump(normalized,include_attributes=False)==ast.dump(old,include_attributes=False) and sorted(normal.pins)==sorted([A,AT]) and normal.branches==1;astscope[p]={'two_exact_pin_substitutions':True,'one_exact3branch_list_addition':True,'all_other_AST_identical_SOURCE_S':True}
workflow=(R/paths[1]).read_bytes();oldworkflow=git('show',A+':'+paths[1]);assert workflow.count(A.encode())==3 and workflow.count(AT.encode())==2
branchline=f'    - {BRANCH}\n'.encode();assert workflow.count(branchline)==1;assert workflow.replace(A.encode(),OLD.encode()).replace(AT.encode(),OLDTREE.encode()).replace(branchline,b'')==oldworkflow
sample=read(Q/'workflow-and-nine-source-preservation-proof.json')['nine_source_sample'];assert len(sample)==9
for v in sample.values():assert a[v['path']]==c[v['path']] and c[v['path']][0]==v['mode'] and sha(R/v['path'])==v['sha256']
producer=read(S/'producer-inputs-and-pre-full-source-checkpoint.json');assert len(producer['producer_inputs'])==268 and len(producer['selected_tests'])==5
for p,v in {**producer['producer_inputs'],**producer['selected_tests']}.items():assert c[p]==a[p]==b[p]==v
old_delta=[p for p in producer['producer_inputs'] if c[p]!=n[p]];assert old_delta==['action_server/src/actions/server/_rcc_runtime_adapter.py'] and all(c[p]==n[p] for p in producer['selected_tests'])
for name in ['pin-RED.log','branch-RED.log']:assert '1 failed, 4 passed' in (Q/name).read_text()
pinred=(Q/'pin-RED.log').read_text();branchred=(Q/'branch-RED.log').read_text();assert OLD in pinred and A in pinred and BRANCH in branchred and 'AssertionError' in pinred+branchred
light=(Q/'green-controls-static.log').read_text();assert '55 passed in 21.31s' in light and 'All checks passed!' in light and '1 file already formatted' in light and 'isort --check' in light and '-m py_compile' in light and 'actual main robot run" was SUCCESS' in light
assert '96 passed' in (Q/'toolkit.log').read_text()
gen=read(Q/'generator-roundtrip.json');assert gen['before']==gen['after']==gen['sha256'] and len(gen['before'])==26 and len(gen['generated_workflows'])==8;all_yaml={**gen['before'],**gen['additional_yaml_parsed_and_bytes_preserved']};assert len(all_yaml)==30
for p,digest in all_yaml.items():assert sha(R/p)==digest
assert [p for p in c if p.startswith('.github/workflows/') and p.endswith(('.yaml','.yml')) and c[p]!=a[p]]==[paths[1]]
assert c[guide]==a[guide];acceptedpatch=S/'exact-implemented-canonical-delta.patch';assert sha(acceptedpatch)=='2bd81847fda0b761e42b24c704dbe9eccda907c21f40cc3b4e5d88bf704e12f6' and acceptedpatch.read_bytes()==git('diff',A+'^',A,'--',guide)
text=(R/guide).read_text();old='''the original opt-in branch
`test/rcc-provider-rollback-hosted-20261010` and the existing reviewed PR branch
`fix/rcc-published-artifact-details-20261010`, subject to the retained path filter.
''';new='''the original opt-in branch `test/rcc-provider-rollback-hosted-20261010` and the
existing reviewed PR branches `fix/rcc-published-artifact-details-20261010` and
`fix/rcc-candidate-wheel-identities-20261010`, subject to the retained path filter.
''';assert text.count(old)==1
patch=''.join(difflib.unified_diff(text.splitlines(True),text.replace(old,new).splitlines(True),fromfile='a/'+guide,tofile='b/'+guide));proposal=D/'canonical-three-reviewed-control-branches-proposed.patch';proposal.write_text(patch)
result={'status':'INDEPENDENT_EXACT_CONTROL_C_SOURCE_PUSH_PROOF','C':H,'C_tree':T,'sole_parent_SOURCE_S':A,'SOURCE_S_tree':AT,'branch':BRANCH,'clean':True,'complete1409_Gitworking_precommit_bytes_executable_bits_exact':True,'exact3paths_only_and1406_other_modeblobs_SOURCE_S_exact':paths,'all47_control16_and_source31_original_external_refs_hashsize_exact':refs,'whole_generator_and_developer_test_AST_normalization':astscope,'rawworkflow_exact_SOURCE_S_after_only3SHA_2tree_substitutions_and1branch':True,'all_other_workflows_pins_paths_predicates_deadlines_permissions_retries_skips_receipts_Core1_0_2_byte_exact':True,'nine_candidate_inputs_modehash_exact_immutable_SOURCE_S_currentC':True,'full268_production_plus5selected_bodymode_exact_S_actual776':True,'old92498_unqualified_adapter_delta':old_delta,'REDpin1fail4pass_REDbranch1fail4pass_GREEN55_rawlogs_verified':True,'Toolkit96_changed_static_compile_gen8_all30_currentbytes_verified':True,'SOURCE_S_full1190_13_Mypy337_reused_originalidentity_NOT_C_full_execution':True,'source_accepted_canonical_delta':bind(acceptedpatch),'canonical_control_branchlist_correction_external_proposal':bind(proposal),'scope':'GO normal existingbranch CONTROL source push only; freshcurrentS/C hostedCI+actual3case required; NOTactualcandidateCLI2510/private/native/full134/integration/releaseGO','reviewer_no_source_mutation_or_tests_actual_gateway_download_push_merge':True}
p=D/'independent-exact-C-control-proof.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(bind(p),indent=2));print(json.dumps(bind(proposal),indent=2))
