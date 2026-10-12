import ast,json,hashlib,subprocess,os,stat
from pathlib import Path
R=Path('/workspace/engineering/pr306');O=Path('/workspace/engineering/pr306-actual299-refresh')
OLD='662014533d8104c1998bce26d91211140acc08e5';TARGET='6181b044c75de35386f1ae30e71725398b6a7feb';AUTO='a31db4434c7bbe69bf572626d2174f64f9ff2f39'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def leaves(ref):return {n.decode():m.decode().split() for row in git('ls-tree','-rz',ref).split(b'\0') if row for m,n in [row.split(b'\t',1)]}
def body(ref,p):return git('show',ref+':'+p)
def functions(ref,p):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(body(ref,p)).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
a,b,c=map(leaves,[OLD,TARGET,AUTO]);assert set(c)==set(a)|set(b)
assert git('show','-s','--format=%P','HEAD').decode().split()==[OLD,TARGET]
assert git('rev-parse','HEAD^{tree}').decode().strip()==AUTO
assert git('status','--porcelain')==b''
assert git('write-tree').decode().strip()==AUTO
rows={}
for p,(mode,kind,blob) in c.items():
 assert kind=='blob'
 path=R/p
 if mode=='120000':data=os.readlink(path).encode();assert path.is_symlink()
 else:data=path.read_bytes();assert stat.S_ISREG(path.stat().st_mode);assert bool(path.stat().st_mode&0o111)==(mode=='100755')
 assert data==body(AUTO,p),p
 if p in a:assert a[p][0]==mode
 if p in b:assert b[p][0]==mode
 rows[p]={'mode':mode,'blob':blob,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
protected=[p for p in a if 'native_startup_diagnostics' in p or p.endswith('test_cli_mcp_resource_history.py') or p=='action_server/src/actions/server/_database.py']
assert len(protected)==5,protected
assert all(c[p]==a[p] for p in protected)
reg='action_server/tests/action_server_tests/mcp/test_resource_history.py';db='action_server/tests/action_server_tests/test_database.py'
proof={}
for p,imported in [(reg,'test_v13_migration_preserves_exact_keys_but_starts_empty_routing_history'),(db,'test_migrate')]:
 x,y,z=map(lambda ref:functions(ref,p),[OLD,TARGET,AUTO]);assert set(z)==set(x)|set(y)
 for n,v in x.items():assert z[n]==(y[n] if n==imported else v),(p,n)
 for n,v in y.items():
  if n not in x:assert z[n]==v,(p,n)
 proof[p]={'original_functions':len(x),'target_functions':len(y),'union_functions':len(z),'sole_target_imported_existing_function':imported,'all_other_original_function_class_ASTs_exact':True,'all_target_new_ASTs_exact':True}
assert 'test_cross_package_handoff_waits_for_previous_declarations_to_disappear' in functions(AUTO,reg)
assert {p:v for p,v in c.items() if p.startswith('.github/')}=={p:v for p,v in b.items() if p.startswith('.github/')}
n=leaves('92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e');deps={f'{p}/{s}' for p in ['actions','action_server','actions-http-helper'] for s in ['pyproject.toml','poetry.lock']};prod=lambda m:sorted(p for p in m if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
oldprod,currentprod=map(prod,[n,c]);changed=[p for p in oldprod if c[p]!=n[p]];added=sorted(set(currentprod)-set(oldprod));five=sorted(p for p in c if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')));assert len(five)==5
selectorchanges=[p for p in five if c[p]!=n[p]]
assert len(oldprod)==268 and len(currentprod)==274 and len(changed)==8 and len(added)==6
assert selectorchanges==['action_server/tests/action_server_tests/test_cli_mcp_resource_history.py']
for guide in ['docs/skills/repository-operations.md','docs/skills/provenance-observability.md']:(O/('immediate-pre-full-canonical-imported-'+Path(guide).stem+'.patch')).write_bytes(git('diff',OLD,AUTO,'--',guide))
r={'source_original':OLD,'target_actual299':TARGET,'expected_complete_auto_merge_tree':AUTO,'complete_union_leaf_count':len(c),'both_parent_leaf_counts':{'original':len(a),'target':len(b)},'all_paths_body_modes_and_filesystem_exec_bits_exact_auto_tree':rows,'original_protected_five_exact':{p:c[p] for p in protected},'overlapping_tests_complete_AST_reconciliation':proof,'both_parent_guides_exact_deterministic_Git_auto_merge_no_novel_child':True,'all_GitHub_exact_actual299':True,'production':{'historical268':268,'current_production':len(currentprod),'oldmatches':268-len(changed),'changed':changed,'added':added,'selected_five_separate':{p:c[p] for p in five},'one_selected_change':selectorchanges,'current_all274':{p:c[p] for p in currentprod},'qualification':'UNQUALIFIED for old92498 native and full backend/private/publication acceptance'},'status':'BEFORE_FULL_COMMITTED_SOURCE_PASS_FULL_NOT_RUN','upstream_disposition':'none'}
(O/'immediate-pre-full-complete-committed-source-proof.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'complete_leaf_count':len(c),'precommit_inspector':'PASS','protected':len(protected),'overlap_complete_ASTs':'PASS','current_production':len(currentprod),'old_native':'UNQUALIFIED'}))
