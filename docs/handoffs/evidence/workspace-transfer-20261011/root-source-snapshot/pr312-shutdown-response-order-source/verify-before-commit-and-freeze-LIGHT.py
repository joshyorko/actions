import ast, hashlib, json, os, stat, subprocess
from pathlib import Path
R=Path('/workspace/engineering/runtime-checkout-eol')
D=Path('/workspace/engineering/pr312-shutdown-response-order-source')
PARENT='77065131a0aee63d2b1f8621476374bdde3c7b65'
ALLOWED={'action_server/src/actions/server/_server.py','docs/skills/repository-operations.md','action_server/tests/action_server_tests/test_shutdown_response_order.py'}
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
pre=json.loads((D/'immutable-pre-edit-original770-all1423-and-source-final-CI-retention.json').read_text())
assert git('rev-parse','HEAD').decode().strip()==PARENT
assert git('branch','--show-current').decode().strip()=='fix/runtime-checkout-eol-20261011'
for row in pre['distinct_preserved_refs']:
 p=Path(row['path']);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],p
assert pre['ref_count']==len(pre['distinct_preserved_refs'])
entries={x['path']:x for x in pre['entries']};unchanged=0
for name,row in entries.items():
 p=R/name;data=p.read_bytes();assert bool(p.stat().st_mode&0o111)==(row['mode']=='100755'),name
 if name not in ALLOWED:
  assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],name;unchanged+=1
 assert git('show',PARENT+':'+name)==git('cat-file','blob',row['blob']),name
assert unchanged==len(entries)-2
new='action_server/tests/action_server_tests/test_shutdown_response_order.py'
assert new not in entries and not ((R/new).stat().st_mode&0o111)
status=git('status','--porcelain=v1','-z').decode().split('\0');changed={x[3:] for x in status if x}
assert changed==ALLOWED,changed
old=ast.parse(git('show',PARENT+':action_server/src/actions/server/_server.py').decode())
now=ast.parse((R/'action_server/src/actions/server/_server.py').read_text())
old_start=next(n for n in old.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=='start_server')
now_start=next(n for n in now.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=='start_server')
imp=next(n for n in now_start.body if isinstance(n,ast.ImportFrom) and n.module=='fastapi')
assert sum(a.name=='BackgroundTasks' for a in imp.names)==1
imp.names=[a for a in imp.names if a.name!='BackgroundTasks']
def shutdown(root):return next(n for n in ast.walk(root) if isinstance(n,ast.FunctionDef) and n.name=='shutdown')
ns=shutdown(now_start);osd=shutdown(old_start)
assert ns.args.args[0].arg=='background_tasks' and ast.dump(ns.args.args[0].annotation)=='Name(id=\'BackgroundTasks\', ctx=Load())'
ns.args.args.pop(0)
expected=ast.parse('background_tasks.add_task(_thread.interrupt_main)').body[0]
assert ast.dump(ns.body[-1],include_attributes=False)==ast.dump(expected,include_attributes=False)
ns.body[-1]=osd.body[-1]
assert ast.dump(old,include_attributes=False)==ast.dump(now,include_attributes=False)
assert ast.dump(ast.parse((D/'test-shutdown-before-configured-format.py').read_text()),include_attributes=False)==ast.dump(ast.parse((R/new).read_text()),include_attributes=False)
reuse=json.loads((D/'own-Bootstrap-reuse-inputs-and-origins.json').read_text())
assert reuse['measured_inputs']==30 and len(reuse['own5actual_prefix_and_source_origin_assertions'])==5
for name,sh in reuse['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/name)==sh
for name,row in reuse['own5venvs_current_config_and_python'].items():assert sha(R/name/'.venv/pyvenv.cfg')==row['config_sha256'] and str((R/name/'.venv/bin/python').resolve())==row['python_resolved']
rcc='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
assert sha('/workspace/actions-cloud/bin/rcc')==rcc and stat.S_IMODE(Path('/workspace/actions-cloud/bin/rcc').stat().st_mode)==0o700
assert sha(R/'action_server/src/actions/server/bin/rcc-18.19.3')==rcc and stat.S_IMODE((R/'action_server/src/actions/server/bin/rcc-18.19.3').stat().st_mode)==0o711
proof={'status':'PASS_BEFORE_COMMIT','parent':PARENT,'unchanged_parent_leaves':unchanged,'complete_parent_leaves':len(entries),'new_test_added':1,'allowed_paths':sorted(ALLOWED),'all_original_bound_refs_exact':len(pre['distinct_preserved_refs']),'whole_original_server_AST_exact_after_only_injection_and_task_call_normalization':True,'formatted_test_whole_AST_exact':True,'own30_and_five_prefix_origins':True,'primary_rcc0700_and_fixture0711_exact':True,'original_EOLog_diff_paths':git('diff','--name-only','a0d258a16095b95b1bf9000cb1201cddfaff4779',PARENT).decode().splitlines(),'source_natural_client_and_exit_predicates_not_modified':True,'constructor':bind(__file__),'upstream_disposition':'none'}
p=D/'immutable-before-commit-LIGHT-preservation-proof.json'
with p.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
p.chmod(0o600);print(json.dumps(bind(p)))
