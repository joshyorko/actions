import ast,copy,hashlib,json,os,re,subprocess
from pathlib import Path
R=Path('/workspace/engineering/pr308');S=Path('/workspace/engineering/pr308-accepted-public-guard-source');D=Path('/workspace/engineering/pr308-accepted-public-guard-independent-source-review')
H='7eb5bce946750555ab009f77592862920a901506';T='3ff76037779763d0461ff3a755b900c9ed83dcf8';M='bc4296014fed571b478bc86911217e5f1dbcdc01';A='4ca431b51b018b947fac6f096ca3cdc21028dd28';B='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0';G='639b591a19d80688afcfabf62d6f4bff8b8a0d69';N='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
script='action_server/scripts/verify_dakota_rcc_acceptance.py';test='action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py';guide='docs/skills/repository-operations.md'
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def read(p):return json.loads(Path(p).read_text())
def leaves(ref):return {n.decode():m.decode().split() for z in git('ls-tree','-rz',ref).split(b'\0') if z for m,n in [z.split(b'\t',1)]}
def tree(ref,path):return ast.parse(git('show',ref+':'+path))
def dump(v):return ast.dump(v,include_attributes=False)
def functions(v):return {n.name:n for n in v.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
F=S/'SOURCE-frozen-checkpoint.json';assert sha(F)=='523e46db8f4ea12dfbb0afbe8f6d2ce675cb0aedd79658b8b4d2585f151afb8b';f=read(F);assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse','HEAD^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[M];assert git('status','--porcelain')==b''
assert git('show','-s','--format=%P',M).decode().split()==[A,B] and git('merge-tree','--write-tree',A,B).decode().strip()==git('rev-parse',M+'^{tree}').decode().strip()
a,b,m,c,n=map(leaves,[A,B,M,H,N]);assert len(c)==1409 and set(c)==set(m)==set(a)|set(b)
assert {p for p in m if m[p] not in [a.get(p),b.get(p)]}<={guide}
changed=sorted(p for p in c if c[p]!=m[p]);assert changed==sorted([script,test,guide]);assert sum(c[p]==m[p] for p in c)==1406
refs=[]
for r in f['evidence']:
 v=bind(r['path']);assert v['bytes']==r['size'] and v['sha256']==r['sha256'];refs.append(v)
assert len(refs)==31
pre=read(S/'pre-source-and-ordinary-union-checkpoint.json');assert pre['pre_source_Git_mode_blob_table']==a and pre['ordinary_union_mode_blob_table']==m
prehash=read(S/'final-pre-full-source-hashes-and-capacity.json')['tracked_sha256'];assert set(prehash)==set(c)
for p,v in c.items():
 assert (R/p).read_bytes()==git('cat-file','blob',v[2]) and sha(R/p)==prehash[p] and bool(os.stat(R/p).st_mode&0o111)==(v[0]=='100755')
orig,current,accepted=map(lambda ref:tree(ref,script),[M,H,G]);newhelpers=set(functions(current))-set(functions(orig));assert newhelpers=={'_private_deadline_receipt_file','record_supervisor_deadline_failure'}
for name in newhelpers:assert dump(functions(current)[name])==dump(functions(accepted)[name])
def timeout_handler(v):return [n for n in ast.walk(v) if isinstance(n,ast.ExceptHandler) and dump(n.type)==dump(ast.parse('subprocess.TimeoutExpired',mode='eval').body)]
current_timeout=timeout_handler(functions(current)["main"]);assert len(current_timeout)==1 and dump(current_timeout[0])==dump(timeout_handler(functions(accepted)["main"])[0]);assert not timeout_handler(functions(orig)["main"])
stripped=copy.deepcopy(current);stripped.body=[x for x in stripped.body if not(isinstance(x,ast.FunctionDef) and x.name in newhelpers)]
for x in ast.walk(functions(stripped)["main"]):
 if isinstance(x,ast.Try):x.handlers=[v for v in x.handlers if not(v.type is not None and dump(v.type)==dump(ast.parse('subprocess.TimeoutExpired',mode='eval').body))]
assert dump(stripped)==dump(orig)
original_test,new_test,accepted_test=map(lambda ref:tree(ref,test),[M,H,G]);newfunctions=set(functions(new_test))-set(functions(original_test));assert len(newfunctions)==7
for name in newfunctions:assert dump(functions(new_test)[name])==dump(functions(accepted_test)[name])
stripped_test=copy.deepcopy(new_test);stripped_test.body=[v for v in stripped_test.body if not(isinstance(v,ast.FunctionDef) and v.name in newfunctions) and not(isinstance(v,ast.Import) and [x.name for x in v.names]==['hashlib'])];assert dump(stripped_test)==dump(original_test)
constants={name:ast.literal_eval(v.value) for v in current.body if isinstance(v,ast.Assign) for target in v.targets if isinstance(target,ast.Name) for name in [target.id] if name in {'CLI_WATCHDOG_SECONDS','CLEANUP_GRACE_SECONDS'}};assert constants=={'CLI_WATCHDOG_SECONDS':2465,'CLEANUP_GRACE_SECONDS':10}
actual=[(name,node) for name,node in functions(original_test).items() if 'ACTIONS_REAL_RCC_ACCEPTANCE' in ast.unparse(node)];assert len(actual)==1;actual_name,actual_ast=actual[0];assert dump(functions(new_test)[actual_name])==dump(actual_ast) and 'acceptance_status' in ast.unparse(actual_ast) and '"FAIL"' in git('show',M+':'+test).decode()
producer=read(S/'producer-inputs-and-pre-full-source-checkpoint.json');deps={f'{p}/{q}' for p in ('actions','action_server','actions-http-helper') for q in ('pyproject.toml','poetry.lock')};inputs=sorted(p for p in b if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
five=sorted(p for p in b if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')));assert len(inputs)==268 and len(five)==5 and producer['producer_inputs']=={p:c[p] for p in inputs} and producer['selected_tests']=={p:c[p] for p in five}
assert all(c[p]==b[p] for p in inputs+five) and all(c[p]==n[p] for p in five);producer_delta=[p for p in inputs if c[p]!=n[p]];assert producer_delta==['action_server/src/actions/server/_rcc_runtime_adapter.py']
reuse=read(S/'own-Bootstrap-reuse-inputs-and-origins.json');assert len(reuse['inputs_exact_prepared_git_bytes_sha256'])==30
for p,digest in reuse['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/p)==digest
assert sha(reuse['original_bootstrap_log'])==reuse['original_bootstrap_log_sha256'];assert len(reuse['own5actual_prefix_and_source_origin_assertions'])==5
for package in reuse['own5venvs_current_config_and_python']:
 origin=read(S/f'origin-{package}.json');assert origin['prefix']==str(R/package/'.venv') and Path(origin['origin']).is_relative_to(R/package/'src')
red=(S/'guard-RED.log').read_text();green=(S/'guard-GREEN.log').read_text();assert '16 failed, 3 passed, 38 deselected' in red and '19 passed, 38 deselected' in green
assert 'AssertionError' in red and 'watchdog_timeout' in red
full=(S/'full-configured-source.log').read_text();assert '1190 passed, 13 skipped, 15 warnings in 129.13s' in full and '2 workers' in full and 'actual main robot run" was SUCCESS' in full
cases=re.findall(r'\[gw\d+\].*?PASSED (?:\S*/)?test_dakota_rcc_acceptance\.py::(test_parent_[^\n]+)',full);assert len(cases)==len(set(cases))==19
light=(S/'scoped-static-corrected.log').read_text();assert '133 passed, 1 skipped, 3 deselected' in light and '301 files already formatted' in light and 'Success: no issues found in 337 source files' in light
assert '96 passed' in (S/'toolkit.log').read_text()
gen=read(S/'generator-roundtrip.json');assert gen['before']==gen['after']==gen['sha256'] and len(gen['before'])==26 and len(gen['generated_workflows'])==8;all_yaml={**gen['before'],**gen['additional_yaml_parsed_and_bytes_preserved']};assert len(all_yaml)==30
for p,digest in all_yaml.items():assert sha(R/p)==digest
patch=git('diff',M,H,'--',guide);assert patch==(S/'exact-implemented-canonical-delta.patch').read_bytes();(D/'canonical-reviewed-implemented-delta.patch').write_bytes(patch)
result={'status':'INDEPENDENT_FROZEN_SOURCE_S_SCOPE_PROOF','head':H,'tree':T,'sole_parent':M,'ordinary_ordered_parents':[A,B],'clean':True,'complete1409_ordinary_union_merge_tree_exact_no_deletions':True,'only3_changed_source_paths':changed,'all1406_other_mode_blob_pairs_exact':True,'all1409_current_working_bytes_modes_executable_bits_exact_Git_pre_full':True,'frozen_checkpoint':bind(F),'all31_original_refs_hash_size_exact':refs,'exact639_reused_helper_AST_names':sorted(newhelpers),'exact639_reused_timeout_handler_AST':True,'exact639_seven_fixture_control_AST_names':sorted(newfunctions),'all_original308_module_and_test_AST_after_removing_guard_only_exact':True,'original_live_negative_test_AST':actual_name,'original_deadline_constants':constants,'candidate_test_bound_seconds':2510,'original_negative_candidate_versions_argv_assertions_UNCHANGED_NOTRUN':True,'full268_target_current_modeblob_equal_old92498_one_unqualified_adapter_delta':producer_delta,'five_selected_modeblobs_equal_oldnative_target_current':five,'own30_prepared_input_hashes_original_bootstrap_log_and_five_origin_records_exact':True,'RED16failed3pass_GREEN19_original_raw_log_verified':True,'current_full1190_13_15_129_13_two_workers_RCCsuccess_and19_individuallyPASS':True,'scoped133_1actualskip_3integration_deselect_lint301_type337_Toolkit96_gen8_all30_raw_records_current_bytes_verified':True,'canonical_exact_delta':bind(D/'canonical-reviewed-implemented-delta.patch'),'limits':['SOURCE GO authorizes separate CONTROL preparation only; no push/hostedactual/integration.','Guard service-free19controls does not execute2465watchdog/2510CLItest or turn negativeofflinecontract into positivecandidateacceptance.','Oldnative92498 adapter change UNQUALIFIED; whole639native/profile implementation excluded; private01f/frozen-v6 absent/full134/release HOLD.']}
p=D/'independent-frozen-S-source-proof.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(bind(p),indent=2))
