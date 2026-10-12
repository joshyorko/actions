import ast,copy,difflib,hashlib,json,stat,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
R=Path('/workspace/engineering/pr308');D=Path('/workspace/engineering/pr308-persistent-fixture-private-source');HEAD='b614864ba9da55c13662894b6ef3c8515d9fdb25';TREE='6fa4f5c1e9837a0d893868255575b355b3977fae'
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
oldpath=D/'original-test_source_staging_rcc_consumer.py';newpath=D/'test_source_staging_rcc_consumer.py';old=ast.parse(oldpath.read_text());new=ast.parse(newpath.read_text())
def funcs(tree):return {n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
o=funcs(old);n=funcs(new);name='test_staged_package_executes_in_managed_rcc_runtime'
for key,node in o.items():
 if key!=name:assert ast.dump(node,include_attributes=False)==ast.dump(n[key],include_attributes=False),key
helper=copy.deepcopy(n['_run_staged_package_managed_worker']);assert helper.args.kwonlyargs[0].arg=='persistent' and ast.literal_eval(helper.args.kw_defaults[0]) is False
helper.args.kwonlyargs=[];helper.args.kw_defaults=[];helper.name=name
class Default(ast.NodeTransformer):
 def visit_If(self,node):
  if isinstance(node.test,ast.Name) and node.test.id=='persistent':return []
  if isinstance(node.test,ast.UnaryOp) and isinstance(node.test.op,ast.Not) and isinstance(node.test.operand,ast.Name) and node.test.operand.id=='persistent':
   return [self.visit(x) for x in node.body]
  return self.generic_visit(node)
 def visit_IfExp(self,node):
  if isinstance(node.test,ast.Name) and node.test.id=='persistent':return self.visit(node.orelse)
  return self.generic_visit(node)
 def visit_Assign(self,node):
  if any(isinstance(t,ast.Attribute) and isinstance(t.value,ast.Name) and t.value.id=='settings' and t.attr=='reuse_processes' for t in node.targets):
   assert isinstance(node.value,ast.Name) and node.value.id=='persistent';node.value=ast.Constant(False)
  return self.generic_visit(node)
helper=Default().visit(helper)
assert ast.dump(helper,include_attributes=False)==ast.dump(o[name],include_attributes=False),'Default shared fixture differs from original body/marks/actionbytes/evidence contract'
wrapper=n[name]
assert ast.dump(wrapper.args,include_attributes=False)==ast.dump(o[name].args,include_attributes=False)
assert [ast.dump(x,include_attributes=False) for x in wrapper.decorator_list]==[ast.dump(x,include_attributes=False) for x in o[name].decorator_list]
call=wrapper.body[-1];assert isinstance(call,ast.Expr) and isinstance(call.value,ast.Call) and call.value.func.id=='_run_staged_package_managed_worker' and not call.value.keywords
assert [x.id for x in call.value.args]==['tmp_path','monkeypatch']
newwrapper=n['test_staged_package_persistent_worker_reuses_one_approved_lease'];assert [ast.dump(x,include_attributes=False) for x in newwrapper.decorator_list]==[ast.dump(x,include_attributes=False) for x in o[name].decorator_list]
newcall=newwrapper.body[-1].value;assert newcall.keywords[0].arg=='persistent' and ast.literal_eval(newcall.keywords[0].value) is True
for module in [old,new]:
 imports=[x for x in module.body if isinstance(x,(ast.Import,ast.ImportFrom))]
 if module is old:oldimports=ast.dump(ast.Module(body=imports,type_ignores=[]),include_attributes=False)
 else:assert ast.dump(ast.Module(body=imports,type_ignores=[]),include_attributes=False)==oldimports
assert git('rev-parse','HEAD').decode().strip()==HEAD and git('rev-parse','HEAD^{tree}').decode().strip()==TREE and not git('status','--porcelain=v1')
entries=[]
for raw in git('ls-tree','-r','-z',HEAD).split(b'\0'):
 if not raw:continue
 meta,namebytes=raw.split(b'\t',1);mode,kind,blob=meta.decode().split();name=namebytes.decode();p=R/name;assert kind=='blob';body=git('cat-file','blob',blob)
 assert p.read_bytes()==body,name;assert bool(p.stat().st_mode&0o111)==(mode=='100755'),name
 entries.append({'path':name,'mode':mode,'blob':blob,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
proof={'status':'PASS_COMPLETE_B614_SOURCE_UNTOUCHED_AND_ORIGINAL_DEFAULT_AST_EQUIVALENT','head':HEAD,'tree':TREE,'clean':True,'entries':entries,'typed_original_leaves':len(entries),'original_non_target_definitions_whole_AST_exact':len(o)-1,'original_module_imports_AST_exact':True,'shared_default_body_AST_exact_after_only_persistent_false_specialization':True,'original_default_action_bytes_assertions_evidence_and_onecall_nonreuse_exact':True,'original_public_wrapper_signature_and_all_three_marks_exact':True,'new_public_wrapper_distinct_sixcall_persistent_true_and_same_three_marks':True,'no_production_changes':True,'constructor':bind(__file__)}
p=D/'immutable-complete-b614-untouched-and-private-default-contract-proof.json'
with p.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
p.chmod(0o600)
patch=''
for relative,original,candidate in [('action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py',oldpath,newpath),('docs/skills/repository-operations.md',D/'original-repository-operations.md',D/'repository-operations.md')]:
 assert (R/relative).read_bytes()==original.read_bytes()==git('show',HEAD+':'+relative)
 patch+='diff --git a/'+relative+' b/'+relative+'\n'+''.join(difflib.unified_diff(original.read_text().splitlines(keepends=True),candidate.read_text().splitlines(keepends=True),fromfile='a/'+relative,tofile='b/'+relative))
p=D/'frozen-two-path-persistent-fixture-source.patch';p.write_text(patch);p.chmod(0o600)
subprocess.run(['git','apply','--check',str(p)],cwd=R,check=True)
subprocess.run(['git','apply','--numstat',str(p)],cwd=R,check=True)
assert not git('status','--porcelain=v1')
print(json.dumps({'patch':bind(p),'proof':bind(D/'immutable-complete-b614-untouched-and-private-default-contract-proof.json'),'typed_leaves':len(entries)}))
