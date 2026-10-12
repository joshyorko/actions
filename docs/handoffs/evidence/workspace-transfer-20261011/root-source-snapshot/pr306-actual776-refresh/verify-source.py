import hashlib,json,subprocess
from pathlib import Path
root=Path('/workspace/engineering/pr306');out=Path('/workspace/engineering/pr306-actual776-refresh')
old='1a3ab0b580710f776fd2075d39e04720c71541ff';target='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0';merge='d3c4cee69ea715779bb28ada0d8fea2ccb72e0d7'
def git(*args):return subprocess.check_output(['git','-C',str(root),*args])
def leaves(ref):return {name.decode():meta.decode().split() for row in git('ls-tree','-rz',ref).split(b'\0') if row for meta,name in [row.split(b'\t',1)]}
a,b,c=map(leaves,(old,target,merge));guide='docs/skills/repository-operations.md'
assert git('show','-s','--format=%P',merge).decode().split()==[old,target]
assert not(a.keys()-c.keys()) and not(b.keys()-c.keys())
assert {p for p in c if c[p] not in (a.get(p),b.get(p))}<={guide}
assert all((root/p).read_bytes()==git('show',merge+':'+p) for p in c if c[p][1]=='blob')
owned=['action_server/src/actions/server/_database.py','action_server/tests/action_server_tests/test_database.py','action_server/tests/action_server_tests/native_startup_diagnostics.py','action_server/tests/action_server_tests/test_native_startup_diagnostics.py']
assert all(c[p]==a[p] for p in owned)
assert all(c[p]==b[p] for p in b if p.startswith('.github/'))
native=git('rev-parse','92498aff').decode().strip();n=leaves(native)
deps={f'{p}/{s}' for p in ['actions','action_server','actions-http-helper'] for s in ['pyproject.toml','poetry.lock']}
producer=lambda d:sorted(p for p in d if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
base=producer(n);current=producer(c);changed=[p for p in base if c[p]!=n[p]];added=sorted(set(current)-set(base));removed=sorted(set(base)-set(current));assert len(base)==268
five=sorted(p for p in n if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')));assert len(five)==5;assert all(c[p]==a[p]==b[p]==n[p] for p in five)
assert changed==['action_server/src/actions/server/_database.py','action_server/src/actions/server/_rcc_runtime_adapter.py'] and not added and not removed
assert c['action_server/src/actions/server/_rcc_runtime_adapter.py']==b['action_server/src/actions/server/_rcc_runtime_adapter.py']
assert git('rev-parse',merge+'^{tree}').decode().strip()==(out/'merge-tree.log').read_text().strip()
patch=git('diff',old,merge,'--',guide);(out/'canonical-imported-accepted-delta.patch').write_bytes(patch)
# Source-parent-only guide additions/imports must retain original precision block.
oldtext=git('show',old+':'+guide).decode();newtext=git('show',merge+':'+guide).decode()
for line in oldtext.splitlines():
 if 'private unrounded' in line or 'conservative lower bound' in line:assert line in newtext
r={'head':merge,'tree':git('rev-parse',merge+'^{tree}').decode().strip(),'ordered_parents':[old,target],'leaf_counts':{'old':len(a),'target':len(b),'current':len(c)},'all_parent_leaves_retained':True,'no_novel_nondoc_leaf':True,'owned_DB_and_precision_observer_exact_old':{p:c[p] for p in owned},'whole_github_exact_actual776':True,'native_producer':native,'historical268_inputs':{p:n[p] for p in base},'current268_inputs':{p:c[p] for p in current},'historical_changes':{p:{'original':n[p],'current':c[p]} for p in changed},'added':added,'removed':removed,'historical_matches':len(base)-len(changed),'five_selectors':{p:c[p] for p in five},'five_selectors_exact_native_old_target':True,'native_qualification':'HOLD: two production inputs differ; no inventory exclusion or old native carry','canonical_imported_delta_sha256':hashlib.sha256(patch).hexdigest(),'all_current_tracked_bytes_exact_commit':True}
(out/'source-union-proof.json').write_text(json.dumps(r,indent=2)+'\n');print('UNION_LEAVES',len(c),'NATIVE268',len(changed),'CHANGES;FIVE_EXACT;OWNED_OLD_AND_TARGET_BYTES=PASS')
