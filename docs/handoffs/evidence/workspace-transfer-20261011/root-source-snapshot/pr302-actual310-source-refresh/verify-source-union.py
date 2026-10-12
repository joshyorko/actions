import ast,difflib,hashlib,json,subprocess
from pathlib import Path
r=Path.cwd();out=Path('/workspace/engineering/pr302-actual310-source-refresh');left='ba04dff7c932b963f2d7a60529fbc3c325bbee1d';right='774438b130afb2ead9bbc1c1b76cb6f91e72150a';base=subprocess.check_output(['git','merge-base',left,right],text=True).strip()
def leaves(ref):
 result={}
 for line in subprocess.check_output(['git','ls-tree','-rz',ref]).split(b'\0'):
  if line:
   header,name=line.split(b'\t',1);mode,kind,blob=header.decode().split();result[name.decode()]=(mode,kind,blob)
 return result
B,L,R=map(leaves,[base,left,right]);tree=subprocess.check_output(['git','write-tree'],text=True).strip();U=leaves(tree);combined=[];failures=[]
for p in B.keys()|L.keys()|R.keys():
 b,l,rr=B.get(p),L.get(p),R.get(p)
 if l==rr:expected=l
 elif l==b:expected=rr
 elif rr==b:expected=l
 else:combined.append(p);continue
 if U.get(p)!=expected:failures.append(p)
assert not failures;assert set(combined)=={'.github/workflows/_gen_workflows.py','docs/skills/repository-operations.md'};assert set(L)|set(R)<=set(U)
read=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],text=True)
def blocks(text):
 result={}
 for i,n in enumerate(ast.parse(text).body):
  key=(type(n).__name__,getattr(n,'name',None))
  if isinstance(n,ast.Assign):key=('assign',ast.dump(n.targets[0]))
  elif isinstance(n,(ast.Import,ast.ImportFrom)):key=('import',ast.dump(n))
  elif isinstance(n,ast.Expr):key=('expr',i)
  elif isinstance(n,ast.If):key=('if',ast.dump(n.test))
  assert key not in result;result[key]=ast.dump(n)
 return result
p='.github/workflows/_gen_workflows.py';bb,ll,rr,uu=map(blocks,[read(base,p),read(left,p),read(right,p),(r/p).read_text()]);selected=[]
for key in bb.keys()|ll.keys()|rr.keys():
 b,l,rv=bb.get(key),ll.get(key),rr.get(key)
 if l==rv:expected=l
 elif l==b:expected=rv
 elif rv==b:expected=l
 else:raise AssertionError(('overlapping ASTblock',key))
 assert uu.get(key)==expected;selected.append(str(key))
p='docs/skills/repository-operations.md';bs=read(base,p);union=(r/p).read_text();docretained={}
patch=Path('/workspace/engineering/pr302-next-refresh-readonly/canonical-nine-source-bindings-proposed.patch').read_text();addition=''.join(x[1:]+'\n' for x in patch.splitlines() if x.startswith('+') and not x.startswith('+++'));assert union.count(addition)==1; union=union.replace(addition,'',1)
for parent in [left,right]:
 ps=read(parent,p);count=0
 for tag,a,b,c,d in difflib.SequenceMatcher(a=bs.splitlines(True),b=ps.splitlines(True)).get_opcodes():
  if tag in ['insert','replace']:
   block=''.join(ps.splitlines(True)[c:d]);assert block in union;count+=1
 docretained[parent]=count
inventory=json.loads((r/'docs/program/evidence/runtime-frozen-current-source-20261011/producer-input-inventory.json').read_text());deltas=[]
for p,v in inventory.items():
 digest=hashlib.sha256((r/p).read_bytes()).hexdigest();assert U[p][0]==v['mode']
 if digest!=v['sha256']:deltas.append({'path':p,'native_sha256':v['sha256'],'source_union_sha256':digest})
assert len(inventory)==268 and len(deltas)==1 and deltas[0]['path']=='action_server/src/actions/server/_rcc_runtime_adapter.py'
selected5=json.loads((r/'docs/program/evidence/runtime-frozen-current-source-20261011/selected-test-inventory.json').read_text());assert len(selected5)==5
for p,v in selected5.items():assert hashlib.sha256((r/p).read_bytes()).hexdigest()==v['sha256'] and U[p][0]==v['mode']
prep=json.loads(Path('/workspace/engineering/pr302-next-refresh-readonly/current-evidence-and-bounded-refresh-proposal.json').read_text())
for v in prep['source_nine_bindings'].values():assert hashlib.sha256((r/v['path']).read_bytes()).hexdigest()==v['sha256']
result={'source_parent':left,'actual_target':right,'common_base':base,'resolved_tree':tree,'ordered_merge_parents':[left,right],'leaf_counts':{'left':len(L),'right':len(R),'union':len(U)},'deleted_parent_leaves':[],'noncombined_leaf_failures':failures,'combined_paths':combined,'generator_top_level_AST_exact_parent_union':True,'generator_block_count':len(selected),'canonical_parent_changed_blocks_retained':docretained,'novel_source_delta':'canonical nine-sample/fullproducer/testedtuple lesson only','all_nine_RCC_source_inputs_equal_historical_S43a':True,'three_actual_case_selectors_raw_summary_helper_profile_publication_contracts_unchanged':True,'producer268_delta':deltas,'selected5_equal_native':True,'native92498_reuse':'UNQUALIFIED_CHANGED_ADAPTER_NO_EXCLUSIONS','control_candidate_pin':'historicalS43a unchanged pendingSprimeindependentreview','actual_run':'NONE'}
(out/'source-union-preservation-proof.json').write_text(json.dumps(result,indent=2)+'\n');print('resolved leaf/AST union retained;9input bytes same43a;268native delta adapter only;5selected exact')
