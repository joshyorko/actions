import ast,hashlib,json,subprocess
from pathlib import Path
root=Path('/workspace/engineering/pr282');out=Path('/workspace/engineering/pr282-actual774-refresh')
old='9c8f1c95caeded6495877280ed1465fd9850b254';target='774438b130afb2ead9bbc1c1b76cb6f91e72150a';merge='e9641caaa1f11414fe92874eb40e159cb48604a6';prepared='71f60ee8b931cb968866db5a8f45ba2056d18ed8'
def git(*args):return subprocess.check_output(['git','-C',str(root),*args])
def leaves(ref):
 return {name.decode():meta.decode().split() for row in git('ls-tree','-rz',ref).split(b'\0') if row for meta,name in [row.split(b'\t',1)]}
a,b,c=map(leaves,(old,target,merge));guide='docs/skills/repository-operations.md'
assert git('show','-s','--format=%P',merge).decode().split()==[old,target]
assert not (a.keys()-c.keys()) and not (b.keys()-c.keys())
combined={p for p in c if c[p] not in (a.get(p),b.get(p))};assert combined <= {guide};assert git('merge-tree','--write-tree',old,target).decode().splitlines()[0]==git('rev-parse',merge+'^{tree}').decode().strip()
assert all((root/p).read_bytes()==git('show',merge+':'+p) for p in c if p != guide and c[p][1]=='blob')
owned='action_server/tests/action_server_tests/mcp/test_canvas_query_template.py';assert c[owned]==a[owned];assert hashlib.sha256((root/owned).read_bytes()).hexdigest()=='edc7ccfb85bd20bc89775f73ee45039bcf4c501fe6dae9a5ebd81a80e16eda4e'
deps={f'{p}/{n}' for p in ('actions','action_server','actions-http-helper') for n in ('pyproject.toml','poetry.lock')}
inputs=sorted(p for p in b if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
native=git('rev-parse','92498aff').decode().strip();n=leaves(native)
five=sorted(p for p in b if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')))
assert len(inputs)==268 and len(five)==5
assert all(c[p]==a[p]==b[p]==n[p] for p in five)
changed_inputs=[p for p in inputs if c[p]!=n[p]]
current_inputs=sorted(p for p in c if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
added_inputs=sorted(set(current_inputs)-set(inputs))
assert changed_inputs==['action_server/src/actions/server/templates/action-templates.yaml','action_server/src/actions/server/templates/action-templates.zip']
assert added_inputs==['action_server/src/actions/server/templates/zips/canvas-query.zip']
assert all(c[p]==a[p] for p in current_inputs)
assert all(c[p]==b[p]==n[p] for p in inputs if p not in changed_inputs)
import yaml
old_yaml=yaml.safe_load(git('show',old+':.github/workflows/actions_runtime_tests.yml'));union_yaml=yaml.safe_load(git('show',merge+':.github/workflows/actions_runtime_tests.yml'));step_name='Verify Canvas published-Core Runtime and browser acceptance';find_step=lambda y:next(step for step in y['jobs']['build']['steps'] if step.get('name')==step_name);assert find_step(old_yaml)==find_step(union_yaml);assert c['.github/workflows/actions_runtime_frozen_catalog_rollback.yml']==b['.github/workflows/actions_runtime_frozen_catalog_rollback.yml']
test='action_server/tests/contract_tests/test_source_staging.py'
assert c[test]==a[test] and (root/test).read_bytes()==git('show',old+':'+test)
assert all(c[p]==a[p] for p in c if p.startswith('.github/'))
assert git('show',old+':.github/workflows/_gen_workflows.py')==(root/'.github/workflows/_gen_workflows.py').read_bytes()
# Resolve the authoritative filenames from the Git leafset rather than assuming package layout.
production_paths=[p for p in inputs if p.endswith(('/source_staging.py','/source_read.py'))]
assert len(production_paths)==2
production={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in production_paths}
assert all(c[p]==a[p]==b[p]==n[p] for p in production_paths)
proof={'ordinary_merge':merge,'tree':git('rev-parse',merge+'^{tree}').decode().strip(),'ordered_parents':[old,target],'leaves':{'old':len(a),'target':len(b),'union':len(c)},'no_deletions':True,'no_novel_nondoc_union_leaf':True,'unchanged_canvas_helper':{owned:c[owned]},'producer':native,'historical_producer_count':len(inputs),'current_producer_count':len(current_inputs),'producer_inputs':{p:c[p] for p in current_inputs},'producer_input_inventory_sha256':hashlib.sha256(json.dumps({p:c[p] for p in current_inputs},sort_keys=True,separators=(',',':')).encode()).hexdigest(),'all269_current_producer_leaves_exact_original282':True,'historical_producer_differences':{'changed':changed_inputs,'added':added_inputs,'matching':len(inputs)-len(changed_inputs)},'old_native_qualification':'NOT_QUALIFIED_COMPLETE_CURRENT_INVENTORY_DIFFERS','five':{p:c[p] for p in five},'whole_github_exact_ordinary_union_after_test_fix':True,'old_canvas_admission_step_exact_including39predicates_diagnostics_version_preflight':True,'target_frozen_workflow_exact':True,'combined_parent_paths':sorted(combined),'current_nondoc_bytes_exact_merge':True,'production_staging_and_read_sha256':production,'staging_test_entire_mode_blob_bytes_exact_original9c':True}
(out/'source-union-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
reuse_paths=list(json.loads(Path('/workspace/engineering/pr310-current-refresh/bootstrap-reuse.json').read_text())['inputs_sha256'])
checked={}
for p in reuse_paths:
 data=(root/p).read_bytes();assert data==git('show',prepared+':'+p);checked[p]=hashlib.sha256(data).hexdigest()
assert all((root/p/'.venv/pyvenv.cfg').exists() for p in ('actions','action_server','actions-http-helper','devutils','work-items'))
log=Path('/workspace/actions-cloud/receipts/pr282-writer/bootstrap.log');digest=hashlib.sha256(log.read_bytes()).hexdigest();reuse=json.loads(Path('/workspace/engineering/pr282-version-frozen-source-proof.json').read_text())['bootstrap_reuse'];assert digest==reuse['log_sha256'];assert 'SUCCESS' in log.read_text()
(out/'bootstrap-reuse.json').write_text(json.dumps({'prepared_source':prepared,'original_log':str(log),'sha256':digest,'input_count':len(checked),'inputs':checked,'own_five_package_environments_present':True,'no_installer':True},indent=2)+'\n')
print('SOURCE_UNION_269_ORIGINAL_INPUTS_266_NATIVE_MATCH_2_CHANGED_1_ADD_FIVE_SELECTORS_PREPARED_REUSE=PASS')
