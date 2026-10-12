import ast,copy,hashlib,json,subprocess
from pathlib import Path
root=Path.cwd();out=Path('/workspace/engineering/pr306-windows-v2-source');parent='e281cbc05dcf2e42d9b37d8879ad986803e6a5e7';git=lambda *a:subprocess.check_output(['git',*a]);allowed=['action_server/tests/action_server_tests/native_startup_diagnostics.py','action_server/tests/action_server_tests/test_native_startup_diagnostics.py','docs/skills/repository-operations.md'];changed=git('diff',parent,'--name-only').decode().splitlines();assert sorted(changed)==sorted(allowed)
def tree(ref):
 d={}
 for e in git('ls-tree','-rz',ref).split(b'\0'):
  if e:
   m,p=e.split(b'\t',1);mode,kind,blob=m.decode().split();d[p.decode()]=(mode,kind,blob)
 return d
leaves=tree(parent)
for p,(mode,kind,blob) in leaves.items():
 if p not in allowed:
  assert (root/p).read_bytes()==git('cat-file','blob',blob),p
  assert ('100755' if (root/p).stat().st_mode&0o111 else '100644')==mode,p
p=allowed[0];before=ast.parse(git('show',parent+':'+p));after=ast.parse((root/p).read_text());current=copy.deepcopy(after)
current.body=[n for n in current.body if not (isinstance(n,ast.ClassDef) and n.name=='DeliveredObservations') and not (isinstance(n,ast.FunctionDef) and n.name=='observe_owned_start') and not (isinstance(n,ast.Import) and any(x.name=='math' for x in n.names))]
for node in current.body:
 if isinstance(node,ast.FunctionDef) and node.name=='observe_start':
  i=next(i for i,x in enumerate(node.args.kwonlyargs) if x.arg=='delivered');node.args.kwonlyargs.pop(i);node.args.kw_defaults.pop(i)
  emit=next(x for x in node.body if isinstance(x,ast.FunctionDef) and x.name=='emit');t=emit.body[0];assert isinstance(t,ast.Try);assert isinstance(t.body[0],ast.If);t.body.pop(0);t.handlers[0].body=[ast.Pass()]
  t=next(x for x in node.body if isinstance(x,ast.Try));t.finalbody=[x for x in t.finalbody if not (isinstance(x,ast.If) and ast.unparse(x.test)=='delivered is not None')]
 if isinstance(node,ast.FunctionDef) and node.name=='install':
  calls=[x for x in ast.walk(node) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='observe_owned_start'];assert len(calls)==1;c=calls[0];c.func.id='observe_start';assert ast.unparse(c.args[0])=='monkeypatch';c.args.pop(0)
assert ast.dump(before)==ast.dump(current),'Unexpected change to original observer logic'
p=allowed[1];before=ast.parse(git('show',parent+':'+p));after=ast.parse((root/p).read_text());b={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)};a={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)};assert all(a[k]==v for k,v in b.items())
p=allowed[2];old=git('show',parent+':'+p).decode();new=(root/p).read_text();anchor='stream cleanup, which remains owned by the unchanged starter.\n';start=new.index(anchor)+len(anchor);end=new.index('These synthetic observer checks',start);addition=new[start:end];assert new[:start]+new[end:]==old;assert len(addition)>1000;(out/'exact-canonical-V2-added-paragraphs.md').write_text(addition);(out/'exact-canonical-V2-delta.patch').write_text(subprocess.check_output(['git','diff',parent,'--',p],text=True))
result={'parent_merge':parent,'only_three_authorized_paths':changed,'all_other_leaf_bodies_modes_exact':len(leaves)-3,'total_leaves':len(leaves),'original_observer_AST_exact_after_removing_only_delivered_optional_fields_and_owned_wrapper_call':True,'original_old_test_functions_AST_exact':list(b),'new_test_functions':len(set(a)-set(b)),'original_NODES_enabled_snapshot_stderr_summary_file_identity_command_summary_unchanged':True,'original80_88_90_20_50ms_sample_cleanup_join_budgets_unchanged':True,'all_production_DB_guard_fixtures_othercases_toolkit_manifests_lockfiles_workflows_generator_unchanged':True,'production_DB_module_sha256':hashlib.sha256((root/'action_server/src/actions/server/_database.py').read_bytes()).hexdigest(),'canonical_delta':'36 new lines only; original ordinary merged guide byte-exact after removal','actual_native_provider_browser_execution':'NONE_NEW','host_visibility':'delivered stream and actual returned owned cleanup only; native RCC internals/Future/emitter unavailable'}
(out/'implementation-scope-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
