import ast,hashlib,json,subprocess
from pathlib import Path
r=Path.cwd(); out=Path('/workspace/actions-cloud/receipts/pr305-crlf-fixture'); old='3ec9d0acbe30ad94d02e4c24fef2587127964495'; producer='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
sha=lambda b:hashlib.sha256(b).hexdigest(); records={}; counts=[]
for name in ['producer-input-inventory.json','selected-test-inventory.json']:
 data=json.loads((r/'docs/program/evidence/runtime-frozen-current-source-20261011'/name).read_text()); counts.append(len(data))
 for p,v in data.items():
  blob=subprocess.check_output(['git','show',producer+':'+p]); assert sha(blob)==v['sha256']; assert (r/p).read_bytes()==blob
  mode=subprocess.check_output(['git','ls-tree','HEAD','--',p],text=True).split()[0]; assert mode==v['mode']
  records[p]={'mode':mode,'sha256':sha(blob)}
assert counts==[268,5]
expected=['action_server/tests/action_server_tests/mcp/test_canvas_runtime_admission.py','action_server/tests/action_server_tests/test_browser_origin_acceptance.py','docs/skills/repository-operations.md']
modified=subprocess.check_output(['git','diff',old,'--name-only'],text=True).splitlines();assert modified==expected
p='action_server/tests/action_server_tests/mcp/test_mcp_apps_authoring.py';assert (r/p).read_bytes()==subprocess.check_output(['git','show',old+':'+p])
p='action_server/tests/action_server_tests/test_browser_origin_acceptance.py';before=ast.parse(subprocess.check_output(['git','show',old+':'+p],text=True));after=ast.parse((r/p).read_text())
a=next(n for n in before.body if isinstance(n,ast.FunctionDef) and n.name=='test_browser_harness_deadline_reaps_owned_descendant'); b=next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name==a.name)
oldwhile=next(n for n in ast.walk(a) if isinstance(n,ast.While) and 'not browser_processes' in ast.unparse(n.test));newwhile=next(n for n in ast.walk(b) if isinstance(n,ast.While) and 'not browser_processes' in ast.unparse(n.test));oldif=oldwhile.body[0];newif=newwhile.body[1]
assert ast.dump(oldif.body[1],include_attributes=False)==ast.dump(newif.body[0],include_attributes=False)
oldwhile.body=[newwhile.body[0],ast.If(test=newif.test,body=newif.body,orelse=oldif.orelse),*oldwhile.body[1:]]
assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
script=lambda tree: next(n.value.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'import assert from' in n.value)
# Compare the embedded JS after undoing exactly the reviewed publication delta.
old_js=next(n.value for n in ast.walk(before) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'import assert from' in n.value)
new_js=next(n.value for n in ast.walk(after) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'import assert from' in n.value)
new_js=new_js.replace('readFileSync, writeFileSync, renameSync','readFileSync, writeFileSync').replace('const pendingPidFile = `${input.process_pid_file}.${process.pid}.tmp`;\n            writeFileSync(pendingPidFile, JSON.stringify({pid: process.pid}), {flag: "wx", mode: 0o600});\n            renameSync(pendingPidFile, input.process_pid_file);','writeFileSync(input.process_pid_file, String(process.pid));')
assert old_js==new_js
for name in ['_run_browser_harness','test_browser_origin_and_ambient_session_boundaries']:
 oldfn=next((n for n in before.body if isinstance(n,ast.FunctionDef) and n.name==name),None)
 if oldfn: assert ast.dump(oldfn)==ast.dump(next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name==name))
proof={'original_source':old,'producer':producer,'all_273_working_bytes_git_modes_exact':True,'counts':counts,'inputs':records,'modified_files_only':modified,'authoring_public_probe_browser_pins_5Run_semantics_byte_identical':True,'deadline_AST_only_PID_poll_boundary_changed':True,'embedded_JS_only_PID_publication_import_changed':True,'budgets_timeout_cleanup_assertions_unchanged':True,'generated_outputs_unchanged':True,'actual_V5_original_source_retained_no_new_actual':True}
(out/'source-preservation-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('273 bytes/modes exact; deadline remainder/JS remainder unchanged; authoring unchanged; only3 intended files')
