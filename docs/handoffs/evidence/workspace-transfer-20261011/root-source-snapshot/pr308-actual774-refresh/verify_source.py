import hashlib,json,subprocess
from pathlib import Path
root=Path('/workspace/engineering/pr308');out=Path('/workspace/engineering/pr308-actual774-refresh')
old='9025a1e44bb05992e9f220842bfaf16a99ebd04f';target='774438b130afb2ead9bbc1c1b76cb6f91e72150a';merge='4ca431b51b018b947fac6f096ca3cdc21028dd28';prepared='493ecbd2c9163786675cc0cc9b3853e6e75ca196'
def git(*args):return subprocess.check_output(['git','-C',str(root),*args])
def leaves(ref):
 return {name.decode():meta.decode().split() for row in git('ls-tree','-rz',ref).split(b'\0') if row for meta,name in [row.split(b'\t',1)]}
a,b,c=map(leaves,(old,target,merge));guide='docs/skills/repository-operations.md'
assert git('show','-s','--format=%P',merge).decode().split()==[old,target]
prep=Path('/workspace/engineering/current-live-admission-20261011/new774-prospective-299-308-309-union-review.json');assert hashlib.sha256(prep.read_bytes()).hexdigest()=='a96af432c5d58f8395a79597bda4357e2e7a38c6561945c3f43b8c784bfe02a5';assert git('rev-parse',merge+'^{tree}').decode().strip()==json.loads(prep.read_text())['subjects']['308']['prospective_tree']
assert not (a.keys()-c.keys()) and not (b.keys()-c.keys())
assert {p for p in c if c[p] not in (a.get(p),b.get(p))}<={guide}
assert all((root/p).read_bytes()==git('show',merge+':'+p) for p in c if p!=guide and c[p][1]=='blob')
owned=['action_server/scripts/verify_dakota_rcc_acceptance.py','action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py'];assert all(c[p]==a[p] for p in owned)
deps={f'{p}/{n}' for p in ('actions','action_server','actions-http-helper') for n in ('pyproject.toml','poetry.lock')}
inputs=sorted(p for p in b if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
native=git('rev-parse','92498aff').decode().strip();n=leaves(native)
five=sorted(p for p in b if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')))
assert len(inputs)==268 and len(five)==5
assert all(c[p]==a[p]==b[p]==n[p] for p in inputs+five)
assert all(c[p]==b[p] for p in b if p.startswith('.github/'))
proof={'ordinary_merge':merge,'tree':git('rev-parse',merge+'^{tree}').decode().strip(),'ordered_parents':[old,target],'leaves':{'old':len(a),'target':len(b),'union':len(c)},'no_deletions':True,'no_novel_nondoc_leaf':True,'owned_candidate_verifier_and_tests':{p:c[p] for p in owned},'producer':native,'producer_count':len(inputs),'producer_inputs':{p:c[p] for p in inputs},'producer_input_inventory_sha256':hashlib.sha256(json.dumps({p:c[p] for p in inputs},sort_keys=True,separators=(',',':')).encode()).hexdigest(),'all268_exact_old_target_producer':True,'five':{p:c[p] for p in five},'whole_github_exact_target':True,'current_nondoc_bytes_exact_merge':True}
(out/'source-union-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
reuse_paths=list(json.loads(Path('/workspace/engineering/pr310-current-refresh/bootstrap-reuse.json').read_text())['inputs_sha256'])
checked={}
for p in reuse_paths:
 data=(root/p).read_bytes();assert data==git('show',prepared+':'+p);checked[p]=hashlib.sha256(data).hexdigest()
assert all((root/p/'.venv/pyvenv.cfg').exists() for p in ('actions','action_server','actions-http-helper','devutils','work-items'))
log=Path('/workspace/engineering/pr308-refresh-owned/bootstrap.log');digest=hashlib.sha256(log.read_bytes()).hexdigest();assert digest=='8812f8f47f040dee39b872299c8cc91d5380fcca9831b646647c7654c525b756';assert 'OK' in log.read_text()
(out/'bootstrap-reuse.json').write_text(json.dumps({'prepared_source':prepared,'original_log':str(log),'sha256':digest,'input_count':len(checked),'inputs':checked,'own_five_package_environments_present':True,'no_installer':True},indent=2)+'\n')
print('SOURCE_UNION_AND_268_PLUS_FIVE_AND_24_INPUT_PREPARED_REUSE=PASS')
