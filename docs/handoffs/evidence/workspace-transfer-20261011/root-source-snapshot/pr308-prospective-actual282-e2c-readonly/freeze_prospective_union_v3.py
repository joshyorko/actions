from pathlib import Path
import ast,copy,difflib,hashlib,json,os,stat,subprocess
O=Path(__file__).parent;R='/workspace/engineering/pr308';S='396925cb3d6527af1768b7f5333f9653c005fc55';T='e2c81adce7858d5a952991ba9a8b7f72e902038a';B='a54c982462d1e7ad011d8152bfc299d997503fb3';M='929410b09fff3521c554cf935411c71f9e2e6b95'
def git(*a):return subprocess.check_output(['git','-C',R,*a])
def blob(x,p):return git('show',x+':'+p)
def leaves(x):return {p.decode():{'mode':i.decode().split()[0],'object':i.decode().split()[2]} for z in git('ls-tree','-r','-z',x).split(b'\0') if z for i,p in [z.split(b'\t',1)]}
def frozen(name,value,mode=0o444):
 p=O/name;b=value.encode() if isinstance(value,str) else (json.dumps(value,indent=2,sort_keys=True)+'\n').encode();fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,mode)
 with os.fdopen(fd,'wb') as f:f.write(b)
 os.chmod(p,mode);return p
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(p.lstat().st_mode))}
b,s,t,m=map(leaves,[B,S,T,M]);sc={p for p in set(b)|set(s) if b.get(p)!=s.get(p)};tc={p for p in set(b)|set(t) if b.get(p)!=t.get(p)};novel=[p for p in m if m[p]!=s.get(p) and m[p]!=t.get(p)]
assert len(m)==1440 and not (set(s)|set(t))-set(m)
assert sorted(novel)==['.github/workflows/_gen_workflows.py','docs/skills/repository-operations.md']
for p in (set(s)|set(t))-(sc&tc):
 expected=t.get(p) if p in tc else s.get(p);assert m.get(p)==expected,p
P='.github/workflows/_gen_workflows.py'
def flattened(raw):
 result={}
 def add(nodes,prefix=''):
  for i,n in enumerate(nodes):
   if isinstance(n,ast.ClassDef):
    c=copy.deepcopy(n);c.body=[];key=prefix+'class:'+n.name;result[key+'/header']=ast.dump(c,include_attributes=False);add(n.body,key+'/');continue
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):key='function:'+n.name
   elif isinstance(n,ast.Assign):key='assign:'+','.join(ast.dump(x,include_attributes=False) for x in n.targets)
   elif isinstance(n,ast.AnnAssign):key='assign:'+ast.dump(n.target,include_attributes=False)
   else:key=type(n).__name__+':'+str(i)
   key=prefix+key;assert key not in result;result[key]=ast.dump(n,include_attributes=False)
 add(ast.parse(raw).body);return result
ba,sa,ta,ma=map(lambda x:flattened(blob(x,P)),[B,S,T,M]);cs={p for p in set(ba)|set(sa) if ba.get(p)!=sa.get(p)};ct={p for p in set(ba)|set(ta) if ba.get(p)!=ta.get(p)};both=cs&ct
for p in both:assert sa.get(p)==ta.get(p),('GENERATOR_OVERLAP',p)
expected=dict(ba)
for v,changed in [(sa,cs),(ta,ct)]:
 for p in changed:
  if p in v:expected[p]=v[p]
  else:expected.pop(p,None)
assert ma==expected,'WHOLE_GENERATOR_AST'
P='docs/skills/repository-operations.md';base=blob(B,P).decode();merged=blob(M,P).decode();chunks={}
for label,x in [('source',S),('target',T)]:
 parent=blob(x,P).decode();seq=difflib.SequenceMatcher(None,base.splitlines(keepends=True),parent.splitlines(keepends=True),autojunk=False);added=[]
 for op,a1,a2,z1,z2 in seq.get_opcodes():
  if op in ('insert','replace'):
   block=''.join(parent.splitlines(keepends=True)[z1:z2]);assert block in merged,(label,'GUIDE_BLOCK');added.append({'lines':z2-z1,'sha256':hashlib.sha256(block.encode()).hexdigest()})
 chunks[label]=added
assert m['.gitattributes']==t['.gitattributes']
old_rules=blob(S,'.gitattributes').decode().splitlines();new_rules=blob(M,'.gitattributes').decode().splitlines();assert all(line in new_rules for line in old_rules)
for p in ['action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py','action_server/src/actions/server/_rcc_runtime_adapter.py','action_server/scripts/verify_dakota_rcc_acceptance.py']:
 assert m[p]==s[p],('ACCEPTED_SOURCE_CHANGED',p)
proof={'scope':'READONLY_PROSPECTIVE_GIT_MERGE_TREE_NO_CHECKOUT_OR_GATES','source':S,'source_tree':git('rev-parse',S+'^{tree}').decode().strip(),'target':T,'target_tree':git('rev-parse',T+'^{tree}').decode().strip(),'target_ordered_parents':git('show','-s','--format=%P',T).decode().strip().split(),'merge_base':B,'prospective_tree':M,'typed_counts':{'base':len(b),'source':len(s),'target':len(t),'prospective':len(m),'parent_exact_leaves':len(m)-len(novel)},'deletions':[],'text_conflicts':[],'source_changed_paths':sorted(sc),'target_changed_paths':sorted(tc),'combined_novel_blobs':novel,'generator_whole_AST_disjoint_parent_union':True,'generator_changed_keys':{'source':sorted(cs),'target':sorted(ct),'same_value_overlap':sorted(both)},'guide_exact_parent_added_replaced_chunks':chunks,'public_mode_fixture_adapter_harness_exact_source_body_mode':True,'LF_rules_preserved':True,'gitattributes':{'exact_target_blob_mode':True,'all_original_source_lines_preserved':True,'addition':'target accepted canvas.html whitespace/linguist rule; seven Runtime LF rules unchanged'},'accepted_target_generated_package_changes':['action_server/src/actions/server/templates/action-templates.yaml','action_server/src/actions/server/templates/action-templates.zip','action_server/src/actions/server/templates/zips/canvas-query.zip'],'default_primary_Rcc3_download_build_pins':'Source paths/body preserved; no binary execution or new version qualification','prospective_complete_typed_inventory':m}
frozen('prospective-complete-parent-union-proof.json',proof)
old=blob(S,P).decode();anchor='transfer old test results to the new union.\n';assert old.count(anchor)==1
lesson='\nAn automatic Git merge can combine workflow-generator and guide blobs without\na textual conflict. Verify the complete generator AST against both parents and\nretain each accepted guide change; regenerate and compare every owned workflow.\nA conflict-free prospective tree is preparation evidence, not new source gates.\n'
new=old.replace(anchor,anchor+lesson);frozen('canonical-automatic-generator-union-proposed.patch',''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/docs/skills/repository-operations.md',tofile='b/docs/skills/repository-operations.md')))
assert git('rev-parse','HEAD').decode().strip()==S and not git('status','--porcelain')
for p in O.iterdir():
 if p.is_file():os.chmod(p,0o400 if p.suffix in ('.stdout','.stderr') else 0o444)
owner={'status':'READONLY_NEXT_READY_ORDINARY_REFRESH_PLAN_NO_ADOPTION_OR_GATES','source':S,'target':T,'prospective_tree':M,'prospective_typed_leaves':1440,'conflicts':[],'ready_dependency':'Root accepts B28 original storage/data post0 before ordinary source refresh; archiver current396 before/post guard untouched','ordinary_commit_required':'Root same existing PR308 branch merge current396 with actuale2c; no replacement branch/rebase/reset; preserve orderedparents and exact prospective tree','new_gate_plan':['Derive committed source/tree and complete1440 Git/FSexec inventory independently after root adoption; retain all old source blobs/receipts, including originalV7/V8 templates and authorized historical8dc archive alias without relabel.','Doctor/prepared30input+5concreteownorigins+activation19/primary3hash0711; no installer. New Toolkit/scoped controls each uniqueABSENTowned basetemp outside numberedparent, retentionALL, reject inheritedADDOPTS; never share basetemp between invocations.','Source LIGHT static/scoped/Toolkit/gen8+allYAML coverage derive actualcount; no prior396 qualification carry.','Named new SOURCEFULL preexecution/rootrelease/independentreview with explicitworker2 unchangedconfiguredRuntime task and original deadlines/floors. No full execution until distinct root serialization/capacity authorization.','Qualified actual config/sourceFULL must bind new source and freshly independently accepted proofs. PrivateV8 template is source-only; source-count/actualroot assembly pending. No RCC/native/provider/5/6 promotion.'],'source_Rcc_default_mode_patch':'Exact source body/mode retained in prospective tree','bindings':[bind(p) for p in sorted(O.iterdir()) if p.is_file()],'documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','durable_learning':'Automatic conflict-free generator merge may contain novel combined blobs; explicit whole AST and guide-chunk union validation is still required.','evidence':'merge-tree exit0;1438 exactparent leaves plus2combined blobs; whole generatorAST and guidechunks proof','stale_ambiguity_removed':'No text conflict does not mean all resulting files are one parent blob or old gates apply.','remaining_uncertainty':'Root adoption/committedtuple/newLIGHT/FULL/actual configuration and native functionality remainNOTRUN.'},'upstream_disposition':'none'}
f=frozen('OWNERFINAL-readonly-current396-actuale2c-prospective-ordinary-refresh-plan.json',owner,0o400);print(json.dumps(bind(f)))
