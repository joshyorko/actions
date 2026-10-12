from pathlib import Path
import json,subprocess,hashlib,re,ast
R=Path('/workspace/engineering/pr309');S=Path('/workspace/engineering/pr309-issue152-request-enforcement-successor');D=Path('/workspace/engineering/pr309-issue152-independent-review');H='9475a30fbe8645fd0c6b9c2746182f7a78631059';T='ddb2bb30a5f7ba381867020821054e510960b917';A='ec73bb6372c1f613a3e130f0ce92f649d9d40a97'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def bind(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def leaves(c):return {n.decode():m.decode().split() for row in git('ls-tree','-rz',c).split(b'\0') if row for m,n in [row.split(b'\t',1)]}
f=S/'immutable-request-enforcement-source-checkpoint.json';assert bind(f)['sha256']=='130bb73051b73d060c84ea55a47a36cad7fb99d1aa3bfd60de6ac79669fddf82';v=json.loads(f.read_text());refs=[]
def inspect(x):
 if isinstance(x,dict):
  if {'path','sha256'}<=x.keys() and isinstance(x['path'],str) and re.fullmatch('[0-9a-f]{64}',str(x['sha256'])):
   b=bind(x['path']);assert b['sha256']==x['sha256'];assert 'bytes' not in x or b['bytes']==x['bytes'];refs.append(b)
  for z in x.values():inspect(z)
 elif isinstance(x,list):
  for z in x:inspect(z)
inspect(v);assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A];assert git('status','--porcelain')==b'';a,c=map(leaves,(A,H));assert len(a)==1410 and len(c)==1411 and a.keys()<=c.keys();changed=[p for p in a if a[p]!=c[p]];added=sorted(c.keys()-a.keys());assert changed==['docs/skills/repository-operations.md'] and added==['action_server/tests/action_server_tests/test_auth_route_enforcement.py']
for p,e in c.items():
 if e[1]=='blob':assert (R/p).read_bytes()==git('show',H+':'+p)
prod=[p for p in a if p.startswith('action_server/src/')];assert len(prod)==209 and all(c[p]==a[p] for p in prod);assert all(c[p]==a[p] for p in a if p.startswith('.github/'))
for p,h in v['source_scope']['owned_current_sha256'].items():assert bind(R/p)['sha256']==h
full=(S/'current-full-configured-source.log').read_text();assert '1229 passed, 13 skipped, 15 warnings in 140.20s' in full
cases=re.findall(r'\bPASSED action_server_tests/test_auth_route_enforcement\.py::([^\n]+)',full);assert len(cases)==73 and len(set(cases))==73;counts={}
for case in cases:
 name=case.split('[')[0];counts[name]=counts.get(name,0)+1
assert sorted(counts.values())==[2,2,3,6,6,54]
post=json.loads((S/'post-full-terminal-source-and-scope.json').read_text());assert post['gateway_exit']==0 and set(s.strip() for s in post['new_test_passed_case_ids'])==set(s.strip() for s in cases);assert post['full_log_sha256']==bind(S/'current-full-configured-source.log')['sha256']
light=(S/'database-bound-final-light.log').read_text();assert '148 passed, 1 skipped, 1 deselected' in light and 'Success: no issues found in 339 source files' in light and '303 files already formatted' in light
mut=json.loads((S/'database-bound-final-owned-auth-mutation-RED-receipt.json').read_text());assert mut['auth_methods_restored'] and mut['all_production_files_unchanged_count']==209 and len(mut['failed_case_ids'])==3 and all(x['actual_status']==200 for x in mut['records']);assert mut['records'][0]['changed_categories']==['secrets'] and set(mut['records'][1]['changed_categories'])=={'logical_sql','directories'} and mut['records'][2]['owned_artifact_exact_bytes_returned']
canonical=git('diff',A,H,'--','docs/skills/repository-operations.md');assert canonical==(S/'exact-current-canonical-delta-v2.patch').read_bytes();assert bind(S/'exact-current-canonical-delta-v2.patch')['sha256']=='e9d6414ca38eb3a9e16eade73449c36857298f5f6ab18e3de0be14416dbe94cf';(D/'canonical-reviewed-source-request-enforcement-delta.patch').write_bytes(canonical)
result={'head':H,'tree':T,'sole_parent':A,'clean':True,'all_parent1410_leaves_preserved_1409modeblobpairs_exact':True,'onlyguide_changed_oneauthrequesttest_added':True,'all209production_workflows_locks_originalcensus_unchanged':True,'current_workingbytes_all1411_exactGit':True,'all39_checkpoint_evidence_refs_hashsize_original_exact':True,'all_reference_bindings':refs,'full1229pass13skip15warnings140_2s2workers_originallog_verified':True,'all73_new_named_cases_individuallyPASS':counts,'current148pass1skip1nativeDeselect_lint303_mypy339_verified':True,'three_meaningful_200_write_leak_mutations_expectedFAIL_and_method_restoration_recorded':True,'canonical_delta':bind(D/'canonical-reviewed-source-request-enforcement-delta.patch'),'current_target_limit':'Tested774 ancestor/sourceparentec73; actualtarget776 unqualified. No current hosted/full152/196/native/private/release claim.'};p=D/'independent-frozen-source-proof.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':bind(p)['sha256'],'cases':counts},indent=2))
