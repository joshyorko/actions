import ast,hashlib,json,subprocess
from pathlib import Path
root=Path.cwd();out=Path('/workspace/engineering/pr306-v2-precision-successor');old='cf6352e253c70095c8e09904e730fc18a42f9a65';git=lambda *args:subprocess.check_output(['git',*args]);owned=['action_server/tests/action_server_tests/native_startup_diagnostics.py','action_server/tests/action_server_tests/test_native_startup_diagnostics.py','docs/skills/repository-operations.md'];assert sorted(git('diff',old,'--name-only').decode().splitlines())==sorted(owned)
p=owned[0];before=ast.parse(git('show',old+':'+p));after=ast.parse((root/p).read_text());without=lambda t:[ast.dump(n) for n in t.body if not (isinstance(n,ast.ClassDef) and n.name=='DeliveredObservations')];assert without(before)==without(after)
bc=next(n for n in before.body if isinstance(n,ast.ClassDef) and n.name=='DeliveredObservations');ac=next(n for n in after.body if isinstance(n,ast.ClassDef) and n.name=='DeliveredObservations');methods=lambda c:{n.name:ast.dump(n) for n in c.body if isinstance(n,ast.FunctionDef)};b,a=methods(bc),methods(ac);changed_methods=[k for k in b if b[k]!=a.get(k)];assert sorted(changed_methods)==sorted(['__init__','_offset','line','process_start_returned','summary']);assert set(a)-set(b)=={'_instant'};assert all(b[k]==a[k] for k in ['_record','_count','cleanup_returned','cleanup_raised','start_finished'])
p=owned[1];bt={n.name:ast.dump(n) for n in ast.parse(git('show',old+':'+p)).body if isinstance(n,ast.FunctionDef)};at={n.name:ast.dump(n) for n in ast.parse((root/p).read_text()).body if isinstance(n,ast.FunctionDef)};assert all(at[k]==v for k,v in bt.items())
leaves={}
for entry in git('ls-tree','-rz',old).split(b'\0'):
 if entry:
  m,p=entry.split(b'\t',1);leaves[p.decode()]=m.decode().split()
for p,(mode,kind,blob) in leaves.items():
 if p not in owned:
  assert (root/p).read_bytes()==git('cat-file','blob',blob),p
  assert ('100755' if (root/p).stat().st_mode&0o111 else '100644')==mode,p
p=owned[2];prior=git('show',old+':'+p).decode();current=(root/p).read_text();replacement='''match does not establish predeadline delivery. Compare private, unrounded
monotonic instants and round only displayed offsets: rounding before adding
the budget can falsely classify an equal or later arrival as earlier. Exact
equality is not before the lower bound. A positive comparison establishes only
delivery before that conservative bound, not completion before the actual
readiness deadline. Future state, native ready-log''';assert current.replace(replacement,'match does not establish predeadline delivery. Future state, native ready-log')==prior
r={'parent_immutable_cf6352':old,'only_three_owned_paths':owned,'all_other_leaf_bodies_modes_exact':len(leaves)-3,'whole_observer_module_except_DeliveredObservations_AST_exact_parent':True,'unchanged_class_loss_privacy_cleanup_methods':['_record','_count','cleanup_returned','cleanup_raised','start_finished'],'allowed_precision_methods_changed':changed_methods+['_instant'],'original58controls_and_helper_function_ASTs_exact':True,'new_boundary_test_functions':sorted(set(at)-set(bt)),'private_raw_clock_fields_not_serialized':'match_instants/start_return_instant used only comparator; displayed offsets round3decimals; progress schema unchanged','all90_20_80_88_50ms_budgets_kwargs_callback_hook_Process_class_restoration_original_tuple_exception_unchanged':True,'all_production_DBguard_test_database_267otherproducer5selectors_native_helper_workflow_manifest_lockfile_bytes_unchanged':True,'canonical_delta':'5added precisionlines; all originalcf paragraphs retained except explicit tightened lowerbound sentence; no diary','native_actual_execution':'NONE'}
(out/'precision-successor-scope-proof.json').write_text(json.dumps(r,indent=2)+'\n');(out/'exact-precision-canonical-delta.patch').write_text(subprocess.check_output(['git','diff',old,'--',p],text=True));print(json.dumps(r,indent=2))
