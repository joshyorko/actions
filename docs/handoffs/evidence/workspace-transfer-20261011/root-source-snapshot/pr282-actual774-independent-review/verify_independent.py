from pathlib import Path
import json,hashlib,subprocess,stat,os
R=Path('/workspace/engineering/pr282');S=Path('/workspace/engineering/pr282-actual774-refresh');D=Path('/workspace/engineering/pr282-actual774-independent-review');H='e9641caaa1f11414fe92874eb40e159cb48604a6';T='6ec12ad4150a1f0d37fb418d5a956e8268a4ffcc';A='9c8f1c95caeded6495877280ed1465fd9850b254';B='774438b130afb2ead9bbc1c1b76cb6f91e72150a';N='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def bind(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def leaves(c):return {n.decode():m.decode().split() for row in git('ls-tree','-rz',c).split(b'\0') if row for m,n in [row.split(b'\t',1)]}
p=S/'frozen-source-receipt.json';assert bind(p)['sha256']=='6c8490d1836eb816d6631b86f28e2b8a6a667f5e89bfb812c6c81cc536fb71ff';v=json.loads(p.read_text());refs=[]
def inspect(x):
 if isinstance(x,dict):
  if {'path','bytes','sha256'}<=x.keys() and isinstance(x['path'],str):assert bind(x['path'])=={k:x[k] for k in ('path','bytes','sha256')};refs.append(bind(x['path']))
  for z in x.values():inspect(z)
 elif isinstance(x,list):
  for z in x:inspect(z)
inspect(v);assert git('status','--porcelain')==b'' and git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A,B];assert git('merge-tree','--write-tree',A,B).decode().splitlines()[0]==T
a,b,c,n=map(leaves,(A,B,H,N));assert len(c)==1423 and a.keys()<=c.keys() and b.keys()<=c.keys();novel={p for p in c if c[p] not in (a.get(p),b.get(p))};assert novel<={'docs/skills/repository-operations.md'}
for p,e in c.items():
 if e[1]=='blob' and e[0]!='120000':assert (R/p).read_bytes()==git('show',H+':'+p)
 elif e[0]=='120000':assert os.readlink(R/p).encode()==git('show',H+':'+p)
assert all(c[p]==a[p] for p in c if p.startswith('.github/'))
proof=json.loads((S/'source-union-proof.json').read_text());inputs=proof['producer_inputs'];assert len(inputs)==269
for p,e in inputs.items():assert c[p]==a[p]==e
oldprod={p:e for p,e in n.items() if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in {f'{k}/{f}' for k in ('actions','action_server','actions-http-helper') for f in ('pyproject.toml','poetry.lock')}};assert len(oldprod)==268
changed=sorted(p for p in oldprod if c[p]!=oldprod[p]);added=sorted(inputs.keys()-oldprod.keys());assert changed==v['native_producer_qualification']['changed'] and added==v['native_producer_qualification']['added'];assert len(changed)==2 and len(added)==1
five=proof['five'];assert len(five)==5
for p,e in five.items():assert e==c[p]==a[p]==b[p]==n[p]
for p,sha in v['stage_read_production_bytes_exact_a0_9c_target_native'].items():assert c[p]==a[p]==b[p]==n[p] and bind(R/p)['sha256']==sha
staging='action_server/tests/contract_tests/test_source_staging.py';helper='action_server/tests/action_server_tests/mcp/test_canvas_query_template.py';assert c[staging]==a[staging] and c[helper]==a[helper];ret=json.loads((S/'retained-source-helper-proof.json').read_text());inspect(ret);assert ret['helper_original']['sha256']==ret['305_frozen_snapshot']['sha256']=='edc7ccfb85bd20bc89775f73ee45039bcf4c501fe6dae9a5ebd81a80e16eda4e';assert stat.S_IMODE(Path(ret['305_frozen_snapshot']['path']).stat().st_mode)==0o444
reuse=json.loads((S/'bootstrap-reuse.json').read_text());assert reuse['input_count']==len(reuse['inputs'])==24
for p,e in reuse['inputs'].items():assert bind(R/p)['sha256']==e
own=json.loads((S/'own-env-origin-proof.json').read_text());assert len(own['records'])==5
for e in own['records']:
 assert e['own_prefix'] and e['own_source'] and Path(e['prefix'])==R/e['package']/'.venv' and Path(e['source']).is_relative_to(R/e['package']/'src');assert bind(e['source'])['sha256']==e['source_sha256'] and bind(Path(e['prefix'])/'pyvenv.cfg')['sha256']==e['venv_config_sha256']
patch=git('diff',A,H,'--','docs/skills/repository-operations.md','docs/skills/work-items.md');assert patch==(S/'canonical-imported-delta.patch').read_bytes();(D/'canonical-reviewed-imported-delta.patch').write_bytes(patch)
for file,text in [('toolkit.log','152 passed'),('scoped.log','75 passed'),('scoped.log','4 passed, 24 deselected'),('full-source.log','1167 passed, 12 skipped, 15 warnings in 135.61s'),('static.log','Success: no issues found in 338 source files'),('static.log','302 files already formatted')]:assert text in (S/file).read_text()
state=json.loads((S/'after-full-state-readback.json').read_text());assert state['head']==H and state['complete_descendant_reaping_proven'] is False and state['kill_or_cleanup_performed'] is False;assert len(state['fixed_allowlisted_ps_readback'])==2
for line in state['fixed_allowlisted_ps_readback']:
 fields=line.split();assert fields[1:3]==['1','Z']
roundtrip=json.loads((S/'generator-roundtrip.json').read_text());assert roundtrip['before']==roundtrip['after'] and len(roundtrip['before'])==26 and roundtrip['all_tracked_yaml_count']==30
res={'head':H,'tree':T,'ordered_parents':[A,B],'clean':True,'Gitmerge_tree_equals_frozen_complete_tree':True,'full1423_leaves_modes_blobs_present_and_workingbytes_exact':True,'novel_leafs_only_resolvedguide':sorted(novel),'whole_github_generator_controller_Canvas39strictpredicates_versionmeasurement_rawmetadata_diagnostic_bytes_exact9c':True,'current269producer_inputs_exact9c_vs92498_266matches2changed1added_UNQUALIFIED':True,'selected5separate_exactold_target_native':True,'production_source_read_and_stage_exactold_target_native':True,'staging_whole_test_body_exact9c_with4_boundary_controls_and_originalcleanupassertions':True,'edc7helper_original305snapshot_exactreadonly':True,'own24prepared_inputs_and5concrete_module_prefix_bindings_exact':True,'all_nested_hashbindings_exact':refs,'actual_original_gate_log_summaries_match_frozen_receipt':True,'recorded_sourcePASS_not_complete_gateway_reaping_two_immediate_PPID1_Z':True,'canonical_imported_delta':bind(D/'canonical-reviewed-imported-delta.patch'),'native_browser_provider_gate_execution_or_source_mutation':'NONE'};p=D/'independent-complete-source-byte-proof.json';p.write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':bind(p)['sha256'],'nested_bindings':len(refs)},indent=2))
