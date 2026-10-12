import hashlib,json,os,re,subprocess
from pathlib import Path
R=Path('/workspace/engineering/pr309');S=Path('/workspace/engineering/pr309-actual776-refresh');D=Path('/workspace/engineering/pr309-actual776-independent-review');P=Path('/workspace/engineering/pr309-issue152-request-enforcement-successor')
H='5130638dc68161c3cfc1a437bacf0467d7cecb42';T='3c2c8ad1c9a067ec774eafd6f5d254cb8703213b';A='9475a30fbe8645fd0c6b9c2746182f7a78631059';B='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0';N='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def read(p):return json.loads(Path(p).read_text())
def leaves(ref):return {n.decode():m.decode().split() for z in git('ls-tree','-rz',ref).split(b'\0') if z for m,n in [z.split(b'\t',1)]}
F=S/'immutable-current776-refresh-source-checkpoint.json';assert sha(F)=='437aafe5f58d667b11d1456fd5860bfd80a4c429515fa47c815dcdfbaeb0b159';f=read(F)
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse','HEAD^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A,B]
assert git('status','--porcelain')==b''
assert git('merge-tree','--write-tree',A,B).decode().strip()==T
refs=[]
for receipt in [f,read(P/'immutable-request-enforcement-source-checkpoint.json')]:
 for r in receipt['evidence_references']:
  v=bind(r['path']); assert v['sha256']==r['sha256'] and v['bytes']==r['bytes'];refs.append(v)
assert len(refs)==60
a,b,c,n=map(leaves,[A,B,H,N]);assert len(c)==1411 and set(c)==set(a)|set(b)
novel=[p for p in c if c[p] not in [a.get(p),b.get(p)]];assert novel==['docs/skills/repository-operations.md']
before=read(S/'before-one-authorized-current-full-source.json');assert set(before['leaves'])==set(c)
for p,v in c.items():
 x=(R/p).read_bytes();assert x==git('cat-file','blob',v[2]) and sha(R/p)==before['leaves'][p]['sha256'] and v==before['leaves'][p]['mode_blob'];assert bool(os.stat(R/p).st_mode&0o111)==(v[0]=='100755')
sourcefacts=read('/workspace/engineering/pr309-issue152-request-enforcement/before-source-pinned28-checkpoint.json')['source_facts'];facts=[v for v in sourcefacts if v['path']!='docs/skills/repository-operations.md'];assert len(facts)==27
for v in facts:assert c[v['path']]==a[v['path']] and c[v['path']][2]==v['git_blob'] and sha(R/v['path'])==v['sha256']
owned='action_server/tests/action_server_tests/test_auth_route_enforcement.py';assert c[owned]==a[owned] and sha(R/owned)=='dd7d3093f62fdd966e4cc07ad44d9043b3d8839bfb45f535843d94b893a277b8'
census='action_server/tests/action_server_tests/test_auth_route_inventory.py';assert c[census]==a[census]
deps={f'{p}/{q}' for p in ('actions','action_server','actions-http-helper') for q in ('pyproject.toml','poetry.lock')};inputs=sorted(p for p in b if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
five=sorted(p for p in b if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')));assert len(inputs)==268 and len(five)==5
assert all(c[p]==b[p] for p in inputs+five) and all(c[p]==n[p] for p in five)
changed=[p for p in inputs if c[p]!=n[p]];assert changed==['action_server/src/actions/server/_rcc_runtime_adapter.py']
rcc=read(S/'current-nine-RCC-bindings-and-full-old-producer-delta.json');candidate=leaves(rcc['reviewed_source_candidate'])
for v in rcc['nine_exact_source_target_bindings'].values():assert c[v['path']]==b[v['path']]==candidate[v['path']]==v['mode_blob'] and sha(R/v['path'])==v['sha256']
production=[p for p in a if p.startswith('action_server/src/')];assert len(production)==209;assert [p for p in production if c[p]!=a[p]]==changed
reuse=read(S/'ordinary-merge-complete-union-and-bootstrap-reuse.json')['own_bootstrap'];assert len(reuse['inputs'])==24
for p,digest in reuse['inputs'].items():assert sha(R/p)==digest
origins=[]
for line in (S/'current-own-five-environment-origins.log').read_text().splitlines():
 if line.startswith('{"package":'):
  v=json.loads(line);assert v['own_prefix'] and v['own_source'];package=v['package']; assert v['prefix']==str(R/package/'.venv') and Path(v['source']).is_relative_to(R/package/'src'); origins.append(v)
assert {v['package'] for v in origins}=={'actions','action_server','actions-http-helper','devutils','work-items'}
full=(S/'current-full-configured-source.log').read_text();assert '1245 passed, 13 skipped, 15 warnings in 146.04s' in full and '2 workers' in full and 'actual main robot run" was SUCCESS' in full
cases=re.findall(r'\[gw\d+\].*?PASSED (?:\S*/)?test_auth_route_enforcement\.py::([^\n]+)',full);cases=[s.strip() for s in cases];terminal=read(S/'terminal-full-source-and-postconditions.json');assert len(cases)==len(set(cases))==73 and sorted(cases)==sorted(s.strip() for s in terminal['new_named_passed_cases'])
counts={'matrix':sum(s.startswith('test_real_assembled_credential_matrix') for s in cases),'dispatch_denial':sum(s.startswith('test_dispatch_denied') for s in cases),'native_ASGI_WS':sum(s.startswith('test_native_asgi_websocket') for s in cases),'private_file':sum(s.startswith('test_assembled_mount') for s in cases),'public':sum(s.startswith('test_intentional_public') for s in cases),'local':sum(s.startswith('test_intentional_local') for s in cases)};assert list(counts.values())==[54,6,6,3,2,2]
light=(S/'current-scoped-static-generator.log').read_text();assert '225 passed, 1 skipped, 4 deselected' in light and '303 files already formatted' in light and 'Success: no issues found in 339 source files' in light and 'ALL_WORKFLOW_OUTPUTS_AND_DEPENDABOT_ROUNDTRIP=PASS' in light
assert '96 passed in 21.61s' in (S/'current-ToolkitTest.log').read_text()
gen=read(S/'generator-roundtrip.json');assert gen['before']==gen['after']==gen['sha256'] and len(gen['before'])==26 and len(gen['generated_workflows'])==8
all_yaml={**gen['before'],**gen['additional_yaml_parsed_and_bytes_preserved']};assert len(all_yaml)==30 and set(all_yaml)=={p for p in c if p.startswith('.github/') and p.endswith(('.yaml','.yml'))}
for p,digest in all_yaml.items():assert sha(R/p)==digest
patches=[]
for parent,name in [(A,'canonical-imported-target-delta-vs-auth-parent.patch'),(B,'canonical-imported-combined-delta-vs-target.patch')]:
 x=git('diff',parent,H,'--','docs/skills/repository-operations.md');assert x==(S/name).read_bytes();dest=D/name;dest.write_bytes(x);patches.append(bind(dest))
oldguidepatch=(P/'exact-current-canonical-delta-v2.patch').read_text();added=[s[1:] for s in oldguidepatch.splitlines() if s.startswith('+') and not s.startswith('+++')];assert len(added)==31
currentguide=(R/'docs/skills/repository-operations.md').read_text();assert '\n'.join(added) in currentguide
result={'status':'INDEPENDENT_EXACT_CURRENT776_SOURCE_PROOF','head':H,'tree':T,'ordered_parents':[A,B],'clean':True,'merge_tree_exact_ordinary_union_1411_no_deletions_only_novel_guide':True,'all1411_current_working_sha_mode_blob_executable_bits_exact_before_and_Git':True,'checkpoint':bind(F),'all60_current21_prior39_reference_bindings':refs,'original_prior92214_source_GO_retained':True,'new608line_test_census_and27_non_guide_sourcefacts_exact_original9475':True,'original_mutations_narrowly_reused_auth_test_parity_only':True,'original209_production_parity_historical_current209_imported_adapter_diff':changed,'producer268_old92498_delta':changed,'five_selected_inputs_exact_old_native_target_current':five,'nine_RCC_bindings_exact_current_target_d642':True,'own24_inputs_and_five_recorded_source_prefix_origins_verified':origins,'current_full1245_13_15_146_04_two_workers_RCC_success_raw_log_verified':True,'all73_named_actual_source_cases_PASS':counts,'scoped225_1skip_4actual_deselect_lint303_type339_Toolkit96_gen8_all30_current_bytes':True,'exact_canonical_parent_import_deltas':patches,'original31_auth_guide_addedlines_contiguously_preserved':True,'no_new_execution_or_source_mutation_push_merge':True,'limits':['Fresh exact513/current776 hosted CI remains required; source push GO only.','Original9475 209-production mutation equality is historical; current adapter differs.','Old92498 native producer unqualified; full152/196/Workspace/backend/private/ChatGPT/release remain HOLD.']}
p=D/'independent-exact-current776-source-proof.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(bind(p),indent=2))
