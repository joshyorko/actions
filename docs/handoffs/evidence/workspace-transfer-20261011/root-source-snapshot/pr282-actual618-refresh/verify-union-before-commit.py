import ast,hashlib,json,subprocess
from pathlib import Path
r=Path('/workspace/engineering/pr282');o=Path('/workspace/engineering/pr282-actual618-refresh')
a='c75dfa6969c2c562a59a967e2e674fea6c8af457';b='6181b044c75de35386f1ae30e71725398b6a7feb';orig='9c8f1c95caeded6495877280ed1465fd9850b254'
def g(*x):return subprocess.check_output(['git','-C',str(r),*x])
def leaves(ref):return {n.decode():m.decode().split() for row in g('ls-tree','-rz',ref).split(b'\0') if row for m,n in [row.split(b'\t',1)]}
A,B,N,O=map(leaves,(a,b,'92498aff',orig));stages=g('ls-files','-sz').split(b'\0');assert all(row.split(b'\t')[0].split()[-1]==b'0' for row in stages if row)
C={n.decode():[m.decode().split()[0],'blob',m.decode().split()[1]] for row in stages if row for m,n in [row.split(b'\t',1)]}
assert A.keys()|B.keys()==C.keys();novel=sorted(p for p in C if C[p] not in (A.get(p),B.get(p)));assert set(novel)<={'docs/skills/repository-operations.md'}
for p,v in C.items():assert (r/p).read_bytes()==g('cat-file','blob',v[2]),p;assert bool((r/p).stat().st_mode&0o111)==(v[0]=='100755'),p
gen='.github/workflows/_gen_workflows.py'
def parts(data):
 t=ast.parse(data);return {getattr(n,'name',str(i)):ast.dump(n,include_attributes=False) for i,n in enumerate(t.body)}
pa,pb,pc=map(parts,(g('show',a+':'+gen),g('show',b+':'+gen),(r/gen).read_bytes()));assert pa.keys()|pb.keys()==pc.keys()
for name,value in pc.items():
 if value in (pa.get(name),pb.get(name)):continue
 ta,tb,tc=[next(n for n in ast.parse(d).body if getattr(n,'name',None)==name) for d in (g('show',a+':'+gen),g('show',b+':'+gen),(r/gen).read_bytes())];assert isinstance(tc,ast.ClassDef)
 def methods(t):return {getattr(n,'name',str(i)):ast.dump(n,include_attributes=False) for i,n in enumerate(t.body)}
 ma,mb,mc=map(methods,(ta,tb,tc));assert ma.keys()|mb.keys()==mc.keys();assert all(v in (ma.get(k),mb.get(k)) for k,v in mc.items())
owned=['action_server/tests/action_server_tests/mcp/test_canvas_query_template.py','action_server/tests/contract_tests/test_source_staging.py','action_server/tests/contract_tests/test_source_read.py']
assert all(C[p]==A[p]==O[p] for p in owned)
assert hashlib.sha256((r/owned[0]).read_bytes()).hexdigest()=='edc7ccfb85bd20bc89775f73ee45039bcf4c501fe6dae9a5ebd81a80e16eda4e'
deps={f'{p}/{n}' for p in ('actions','action_server','actions-http-helper') for n in ('pyproject.toml','poetry.lock')}
inputs=lambda d:sorted(p for p in d if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
ni,ci=inputs(N),inputs(C);assert not(set(ni)-set(ci));changed=[p for p in ni if C[p]!=N[p]];added=sorted(set(ci)-set(ni))
five=sorted(p for p in C if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')));assert len(five)==5 and all(C[p]==N[p]==A[p]==B[p] for p in five)
nine=json.loads(Path('/workspace/engineering/pr282-actual776-refresh/accepted302-nine-source-preservation.json').read_text())['nine_sample'];D=leaves('d642a3ac24f8da85101538bdfdf59b509fd74bfb')
for row in nine.values():p=row['path'];assert C[p]==B[p]==D[p]==row['mode_blob'];assert hashlib.sha256((r/p).read_bytes()).hexdigest()==row['sha256']
(o/'accepted-nine-RCC-source-sample.json').write_text(json.dumps({'status':'PASS_NINE_SAMPLE_CURRENT_EQUALS_D642_AND_618','nine_sample':nine,'scope':'nine sample not wholeproducer/full134'},indent=2)+'\n')
base=g('merge-base',a,b).decode().strip();docs=['docs/skills/repository-operations.md','docs/skills/provenance-observability.md']
for p in docs:
 current=(r/p).read_text()
 for parent in (a,b):
  additions=[l[1:] for l in g('diff','--unified=0',base,parent,'--',p).decode().splitlines() if l.startswith('+') and not l.startswith('+++')];assert all(l in current for l in additions if l.strip()),(p,parent)
(o/'exact-both-parent-canonical-import.patch').write_bytes(g('diff',a,'--','docs/skills'))
prior=Path('/workspace/engineering/pr282-actual776-refresh/frozen-source-receipt.json');assert hashlib.sha256(prior.read_bytes()).hexdigest()=='58ae1c1657c4cc310d1b43c70391b4b7038499d6d07cb215112761fa81621977';refs=list(json.loads(prior.read_text())['evidence_files'].values())
for row in refs:
 data=Path(row['path']).read_bytes();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],row['path']
proof={'ordered_parents':[a,b],'parent_leaf_counts':[len(A),len(B)],'current_leaf_count':len(C),'typed_union':C,'complete_parent_union_no_deletions':True,'novel_combined_paths':novel,'all_nondoc_modes_bytes_selected_parent_exact':True,'generator_AST_parent_union_exact':True,'generator_top_statement_count':len(pc),'generator_actual_source_equal_parent_A':C[gen]==A[gen],'generator_target_equal_parent_B':C[gen]==B[gen],'original_Canvas3_exact9c':{p:C[p] for p in owned},'current_producer':{'historical':len(ni),'current':len(ci),'matching':len(ni)-len(changed),'changed':changed,'added':added,'typed_inventory':{p:C[p] for p in ci}},'five_selected_separate':{p:C[p] for p in five},'native_current_qualification':'UNQUALIFIED: measured full producer differences, no exclusions or oldactual carry','both_parent_canonical_accepted_added_lines_retained':docs,'measured_prior_reference_count':len(refs),'prior_refs':refs,'before_commit_current_sha256':{p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in C}}
(o/'ordinary-union-and-original-Canvas-retention-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('Complete',len(C),'parent union; measured',len(refs),'old refs exact; producer',len(ci),'match',len(ni)-len(changed),'changed',len(changed),'added',len(added),'five SELECTED separate; no actual')
