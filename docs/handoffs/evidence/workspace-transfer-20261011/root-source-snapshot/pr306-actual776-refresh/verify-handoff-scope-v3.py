import ast,copy,hashlib,json,subprocess
from pathlib import Path
root=Path('/workspace/engineering/pr306');out=Path('/workspace/engineering/pr306-actual776-refresh');parent='d3c4cee69ea715779bb28ada0d8fea2ccb72e0d7'
def git(*args):return subprocess.check_output(['git','-C',str(root),*args])
def original(p):return git('show',parent+':'+p)
def dump(n):return ast.dump(n,include_attributes=False)
cli='action_server/tests/action_server_tests/test_cli_mcp_resource_history.py';reg='action_server/tests/action_server_tests/mcp/test_resource_history.py';guide='docs/skills/repository-operations.md'
a=ast.parse(original(cli));b=ast.parse((root/cli).read_bytes());helper=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name=='_resource_handoff_is_published');b.body.remove(helper)
oldnative=next(n for n in a.body if isinstance(n,ast.FunctionDef) and n.name=='test_cli_resource_owner_history_across_reload_and_restart');newnative=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name==oldnative.name)
def handoff_loop(f,new):
 return next(n for n in ast.walk(f) if isinstance(n,ast.For) and any(isinstance(t,ast.Name) and t.id==('_resource_handoff_is_published' if new else '_route_is_listed') for t in ast.walk(n)) and isinstance(n.iter,ast.Name) and n.iter.id=='_TRANSITIONS')
x=handoff_loop(oldnative,False);y=handoff_loop(newnative,True);assert len(x.body)==len(y.body)+1
assert dump(ast.Module(body=x.body[2:],type_ignores=[]))==dump(ast.Module(body=y.body[1:],type_ignores=[]))
y.body[:1]=copy.deepcopy(x.body[:2]);assert dump(a)==dump(b)
probe=ast.parse((out/'test_handoff_probe_v2.py').read_bytes());ph=next(n for n in probe.body if isinstance(n,ast.FunctionDef) and n.name=='full_handoff');nh=copy.deepcopy(helper);nh.name=ph.name;nh.returns=None;nh.args.args[0].annotation=None; assert len(nh.body)==len(ph.body)+1; nh.body[1:3]=copy.deepcopy(ph.body[1:2]); assert dump(ph)==dump(nh)
a=ast.parse(original(reg));b=ast.parse((root/reg).read_bytes());assert len(b.body)==len(a.body)+1;assert dump(a)==dump(ast.Module(body=b.body[:-1],type_ignores=[]));assert b.body[-1].name=='test_cross_package_handoff_waits_for_previous_declarations_to_disappear'
changed=set(git('diff',parent,'--name-only').decode().split());assert changed<={cli,reg,guide}
head=git('rev-parse','HEAD').decode().strip();refs={'current_head':head,'reviewed_ordinary_parent':parent,'allowed_three_paths':sorted(changed),'CLI_whole_original_AST_restored_after_reversing_only_first_wait_and_removing_new_helper':True,'new_helper_AST_exact_executed_probe_after_reversing_only_two_explicit_fixed_response_assertions':True,'all_original_resource_history_regression_AST_exact':True,'new_regression_function':b.body[-1].name,'all_other_worktree_tracked_bytes_exact_parent':True,'all_owned_90_20_80_88_deadlines_and_precision_observer_original_bytes_preserved':True,'hosted_failure_cause':'UNKNOWN','current_selected_resource_history_changed':True,'old_native_control_selector_qualification':'HOLD; one selectedtest changed; producer also twochanges'}
paths=[v.decode() for v in git('ls-files','-z').split(b'\0') if v];allhash={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
for p in paths:
 if p not in changed:assert (root/p).read_bytes()==original(p),p
refs['current_all_tracked_bytes_sha256']=allhash
(out/'current-handoff-source-scope.json').write_text(json.dumps(refs,indent=2)+'\n');print('COMPLETE_ORIGINAL_AST_EXCEPT_APPROVED_FIRST_WAIT_HELPER_AND_ONE_REGRESSION=PASS;PRODUCTION_OBSERVER_AND_ALL_OTHER_PATHS_EXACT')
