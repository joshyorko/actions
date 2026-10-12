import hashlib,json,subprocess
from pathlib import Path
root=Path('/workspace/engineering/pr299');out=Path('/workspace/engineering/pr299-actual776-refresh')
old='5db93e2251cf039ef81780730098da1b255d8d2e';target='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0';merge='3155fc55ea7d47afbc547fddc963b5860462924b';prepared='a99c21df257949006f0e55e14243e2fcac27c138'
def git(*args):return subprocess.check_output(['git','-C',str(root),*args])
def leaves(ref):
 return {name.decode():meta.decode().split() for row in git('ls-tree','-rz',ref).split(b'\0') if row for meta,name in [row.split(b'\t',1)]}
a,b,c=map(leaves,(old,target,merge));guide='docs/skills/repository-operations.md'
assert git('show','-s','--format=%P',merge).decode().split()==[old,target]
assert not (a.keys()-c.keys()) and not (b.keys()-c.keys())
assert {p for p in c if c[p] not in (a.get(p),b.get(p))}<={guide}
assert all((root/p).read_bytes()==git('show',merge+':'+p) for p in c if p!=guide and c[p][1]=='blob')
prior=json.loads(Path('/workspace/engineering/pr299-actual311-refresh/source-union-proof.json').read_text());owned=list(prior['original23_owned_source_tests']);original299=leaves('9cb61c52fce35201221b55707d73da9e9b0840a6');assert len(owned)==23;assert all(c[p]==a[p]==original299[p] for p in owned)
assert git('rev-parse',merge+'^{tree}').decode().strip()==(out/'merge-tree.log').read_text().strip()

deps={f'{p}/{n}' for p in ('actions','action_server','actions-http-helper') for n in ('pyproject.toml','poetry.lock')}
native=git('rev-parse','92498aff').decode().strip();n=leaves(native)
inputs=sorted(p for p in n if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
five=sorted(p for p in b if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')))
assert len(inputs)==268 and len(five)==5
current_inputs=sorted(p for p in c if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps);added=sorted(set(current_inputs)-set(inputs));changed=[p for p in inputs if c[p]!=n[p]];assert len(changed)==7 and len(added)==6 and len(current_inputs)==274;assert all(c[p]==a[p]==original299[p] for p in current_inputs if p!='action_server/src/actions/server/_rcc_runtime_adapter.py');assert c['action_server/src/actions/server/_rcc_runtime_adapter.py']==b['action_server/src/actions/server/_rcc_runtime_adapter.py'];assert all(c[p]==a[p]==b[p]==n[p] for p in five)
assert all(c[p]==b[p] for p in b if p.startswith('.github/'))
proof={'ordinary_merge':merge,'tree':git('rev-parse',merge+'^{tree}').decode().strip(),'ordered_parents':[old,target],'leaves':{'old':len(a),'target':len(b),'union':len(c)},'no_deletions':True,'no_novel_nondoc_leaf':True,'original23_owned_source_tests':{p:c[p] for p in owned},'producer':native,'producer_count':len(inputs),'producer_inputs':{p:c[p] for p in inputs},'producer_input_inventory_sha256':hashlib.sha256(json.dumps({p:c[p] for p in inputs},sort_keys=True,separators=(',',':')).encode()).hexdigest(),'all273_current_entries_except_imported302adapter_exact_old':True,'imported302_adapter_exact_actual776':True,'historical_producer_changed_seven':{p:{'historical':n[p],'current':c[p]} for p in changed},'historical_producer_added_six':{p:c[p] for p in added},'current_producer_count':len(current_inputs),'complete_current274_producer_inputs':{p:c[p] for p in current_inputs},'complete_current274_inventory_sha256':hashlib.sha256(json.dumps({p:c[p] for p in current_inputs},sort_keys=True,separators=(',',':')).encode()).hexdigest(), 'own_premerge_merge_tree_binding':{'path':str(out/'merge-tree.log'),'sha256':hashlib.sha256((out/'merge-tree.log').read_bytes()).hexdigest()},'historical261_retained_exact':True,'all5_selected_tests_exact_old_target_native':True,'historical_native_qualification':'HOLD:7 changed and6 added producer leaves; no inventory exclusions or old artifact carry','five':{p:c[p] for p in five},'whole_github_exact_target':True,'current_nondoc_bytes_exact_merge':True}
(out/'source-union-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
reuse_paths=list(json.loads(Path('/workspace/engineering/pr310-current-refresh/bootstrap-reuse.json').read_text())['inputs_sha256'])
checked={}
for p in reuse_paths:
 data=(root/p).read_bytes();assert data==git('show',prepared+':'+p);checked[p]=hashlib.sha256(data).hexdigest()
assert all((root/p/'.venv/pyvenv.cfg').exists() for p in ('actions','action_server','actions-http-helper','devutils','work-items'))
log=Path('/workspace/engineering/pr299-refresh-owned/bootstrap.log');digest=hashlib.sha256(log.read_bytes()).hexdigest();assert digest=='8bdeac2f153ad303d8c3b68743517072374630ef3af2b488fb52824a006fab69';assert 'OK' in log.read_text()
(out/'bootstrap-reuse.json').write_text(json.dumps({'prepared_source':prepared,'original_log':str(log),'sha256':digest,'input_count':len(checked),'inputs':checked,'own_five_package_environments_present':True,'no_installer':True},indent=2)+'\n')
print('SOURCE_UNION_AND_268_PLUS_FIVE_AND_24_INPUT_PREPARED_REUSE=PASS')
