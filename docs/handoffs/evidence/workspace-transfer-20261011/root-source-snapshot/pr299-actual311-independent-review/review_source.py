from pathlib import Path
import ast, hashlib, json, subprocess
R=Path('/workspace/engineering/pr299'); O=Path('/workspace/engineering/pr299-actual311-refresh'); D=Path('/workspace/engineering/pr299-actual311-independent-review')
H='2ad0fd6a899d26aa92d719390f639a76b89fb6f3'; T='ae973b037c3370ce605c8b7b0db813e0ff48a6fa'; M='a5b389269fcfb363fdfafbfe91a2f3172d410326'; MT='0f5a438ef06a22a1efabe155aba471f68a44c537'; OLD='80ba4c3adce0d0f5fd8a7040d271ab19433e4042'; BASE='1c7585fe8bb3cb9476c3997570bd3f04466f2bbc'; ORIGINAL='9cb61c52fce35201221b55707d73da9e9b0840a6'; GUIDE='docs/skills/repository-operations.md'
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
def tree(x):
 result={}
 for row in git('ls-tree','-rz',x).split(b'\0'):
  if row:
   meta,path=row.split(b'\t',1);result[path.decode()]=[v.decode() for v in meta.split()]
 return result
r=json.loads((O/'frozen-source-receipt.json').read_text()); assert bind(O/'frozen-source-receipt.json')['sha256']=='9fd78d3a30c666e6da12e9aef3bc870c8cb654d3f43d1d1d02d92db405729829'
assert git('log','-1','--format=%H %T %P',H).decode().strip()==f'{H} {T} {M}'
assert git('log','-1','--format=%H %T %P',M).decode().strip()==f'{M} {MT} {OLD} {BASE}'
assert git('rev-parse','HEAD').decode().strip()==H and not git('status','--porcelain')
assert git('branch','--show-current').decode().strip()==r['branch']
old,target,merge,current,original=map(tree,[OLD,BASE,M,H,ORIGINAL]); assert set(old)<=set(merge) and set(target)<=set(merge)
assert {p for p in current if current[p]!=merge.get(p)}=={GUIDE} and len(current)==1419
ancestor=git('merge-base',OLD,BASE).decode().strip(); common=tree(ancestor);both=[];checked=0
for p in set(common)|set(old)|set(target):
 s,t,b=old.get(p),target.get(p),common.get(p)
 if s==t:e=s
 elif s==b:e=t
 elif t==b:e=s
 else:both.append(p);continue
 assert merge.get(p)==e,p;checked+=1
assert both==[GUIDE]
for sha in [OLD,BASE]:
 adds=[s[1:] for s in git('diff','--unified=0',ancestor,sha,'--',GUIDE).decode().splitlines() if s.startswith('+') and not s.startswith('+++') and s[1:].strip()]
 assert all(line in git('show',M+':'+GUIDE).decode() for line in adds)
owned=r['original23_source_test_modes_blobs_exact9cb_and80ba'];assert len(owned)==23
for p,e in owned.items():assert current[p]==merge[p]==old[p]==original[p]==e and (R/p).read_bytes()==git('show',H+':'+p)
assert all(current[p]==target[p] for p in current if p.startswith('.github/'))
for e in r['gate_logs'].values():assert bind(e['path'])==e
for k in ['source_proof','source_inspector','bootstrap_reuse','original_bootstrap','generator_roundtrip']:
 e=r[k];assert bind(e['path'])==e
for e in r['old_receipts_own_original_identities']:assert bind(e['path'])==e
proof=json.loads(Path(r['source_proof']['path']).read_text()); expected=json.loads(Path(proof['independent_prospective_leafset']['path']).read_text())
# Original independently simulated complete union list admits every mode/blob.
if 'leaves' in expected:expected=expected['leaves']
assert merge=={p:[e["mode"],e["kind"],e["blob"]] for p,e in expected.items()}
reference=json.loads(Path('/workspace/engineering/native292-owned/producer-input-inventory.json').read_text()); selected=json.loads(Path('/workspace/engineering/native292-owned/selected-test-inventory.json').read_text())
changed={p:current[p] for p,e in reference.items() if current[p]!=[e['mode'],e['kind'],e['blob']]};assert len(changed)==6 and set(changed)==set(r['producer_comparison']['historical6changed'])
producer_paths={p for p in current if any(p.startswith(pkg+'/src/') or p in [pkg+'/poetry.lock',pkg+'/pyproject.toml'] for pkg in ['action_server','actions','actions-http-helper'])}
assert len(producer_paths)==274 and producer_paths-set(reference)==set(r['producer_comparison']['historical6added'])
assert all(current[p]==old[p]==original[p] for p in producer_paths)
for p,e in reference.items():
 if p not in changed:assert current[p]==[e['mode'],e['kind'],e['blob']] and hashlib.sha256(git('show',H+':'+p)).hexdigest()==e['sha256']
for p,e in selected.items():assert current[p]==old[p]==target[p]==[e['mode'],e['kind'],e['blob']] and hashlib.sha256(git('show',H+':'+p)).hexdigest()==e['sha256']
assert len(selected)==5
reuse=json.loads(Path(r['bootstrap_reuse']['path']).read_text());assert reuse['input_count']==len(reuse['inputs'])==24 and reuse['own_five_package_environments_present'] and reuse['no_installer']
for p,sha in reuse['inputs'].items():
 raw=git('show',H+':'+p);assert raw==git('show',reuse['prepared_source']+':'+p)==(R/p).read_bytes() and hashlib.sha256(raw).hexdigest()==sha
assert all((R/p/'.venv/pyvenv.cfg').exists() for p in ['actions','action_server','actions-http-helper','devutils','work-items'])
assert 'actual main robot run" was SUCCESS' in Path(reuse['original_log']).read_text()
for name, needles in {'full-source.log':['1200 passed, 13 skipped, 15 warnings','+ poetry run invoke test-not-integration','/workspace/engineering/pr299/action_server/.venv/bin/python'], 'scoped.log':['189 passed, 1 skipped, 12 deselected'], 'static.log':['+ poetry run invoke lint','poetry run isort --check src tests','311 files already formatted','+ poetry run invoke typecheck','Success: no issues found in 347 source files'], 'toolkit.log':['69 passed'], 'doctor.log':['RCC developer toolkit checks passed.']}.items():
 text=(O/name).read_text();assert 'actual main robot run" was SUCCESS' in text
 for needle in needles:assert needle in text,needle
roundtrip=json.loads(Path(r['generator_roundtrip']['path']).read_text());assert roundtrip['before']==roundtrip['after'] and len(roundtrip['before'])==26
for p,sha in roundtrip['before'].items():assert hashlib.sha256(git('show',H+':'+p)).hexdigest()==sha
patch=D/'canonical-integrated-actual311-delta.patch';patch.write_bytes(git('diff',M,H,'--',GUIDE)); doc=r['documentation_improvement'];assert bind(doc['Exact_delta']['path'])==doc['Exact_delta'] and patch.read_bytes()==Path(doc['Exact_delta']['path']).read_bytes()
assert git('diff','--numstat',M,H).decode().strip()=='9\t0\t'+GUIDE
subprocess.check_call(['git','-C',str(R),'diff','--check',M,H])
service=git('show',H+':action_server/src/actions/server/run_outputs/service.py').decode(); syntax=ast.parse(service)
cls=next(x for x in syntax.body if isinstance(x,ast.ClassDef) and x.name=='RunOutputService');resolve=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='resolve'); outer=next(x for x in resolve.body if isinstance(x,ast.With));tx=outer.body[0];assert isinstance(tx,ast.With) and isinstance(outer.body[1],ast.Expr) and isinstance(outer.body[1].value,ast.Yield)
assert '_lock_workspace(self.db, workspace_id)' in ast.get_source_segment(service,tx) and 'self._authorize(actor, snapshot, "read")' in ast.get_source_segment(service,tx) and 'provider.open(output.object_ref, output.digest, output.size)' in ast.get_source_segment(service,tx)
readcls=next(x for x in syntax.body if isinstance(x,ast.ClassDef) and x.name=='ResolvedOutput');read=next(x for x in readcls.body if isinstance(x,ast.FunctionDef) and x.name=='read');assert ast.unparse(read.body[0])=='return self._reader.read(size)'
test=git('show',H+':action_server/tests/action_server_tests/run_outputs/test_service.py').decode();testast=ast.parse(test);neg=next(x for x in testast.body if isinstance(x,ast.FunctionDef) and x.name=='test_revocation_and_other_workspace_deny_before_provider_access');negsource=ast.get_source_segment(test,neg)
for s in ['pytest.fail("unauthorized resolver reached provider")','monkeypatch.setattr(provider, "open", forbidden)','control.revoke(actor, snap.deployment)']:assert s in negsource
assert negsource.count('pytest.raises(AccessDenied)')==3
result={'verdict':'GO_NORMAL_GUARDED_EXISTING_REF_PUSH_EXACT_2ad0fd6a; HOLD_FRESH_HOSTED_MERGE_NATIVE_BACKEND_TRANSPORT_FULL_ACCEPTANCE','scope':'Read-only frozen source and evidence inspection; no source mutation or actual gate execution','source':{'head':H,'tree':T,'parent':M,'ordinary_merge_tree':MT,'ordered_parents':[OLD,BASE],'existing_branch':r['branch'],'clean':True},'independent_preservation':{'complete_prospective_leafset_exact':proof['independent_prospective_leafset'],'final_leaf_count':len(current),'ordinary_nonconflicting_threeway_paths_verified':checked,'both_parent_guides_retained':True,'original23_modes_blobs_exact9cb80ba':True,'final_1418_non_doc_modes_blobs_exact_tested_union':True,'complete_github_exact_actual_target':True},'native_inputs':{'current274_exact_original299':True,'historical268_matching':262,'changed6':changed,'added6':r['producer_comparison']['historical6added'],'selected5_exact':True,'qualification':'HOLD: no old92498 native/artifact qualification from 262 matches or selector parity'},'behavior_review':{'resolver':'Workspace locking, actor authorization, publication/output checks and provider reader acquisition occur in same transaction; yield is after transaction exit but inside owned ExitStack; read delegates without grant recheck. Revocation affects future resolutions, not an already acquired reader.','meaningful_negative':'Existing real service test replaces provider.open with fail sentinel; denied principal, wrong Workspace and revoked grant each raise AccessDenied before provider access. No active-stream revocation test or public transport qualification claimed.'},'fresh_source_gates':r['gates'],'verified_owner_receipt':bind(O/'frozen-source-receipt.json'),'verified_gate_logs':r['gate_logs'],'verified_source_proof':r['source_proof'],'verified_bootstrap_reuse':r['bootstrap_reuse'],'verified_original_bootstrap':r['original_bootstrap'],'historical_receipts_preserved':r['old_receipts_own_original_identities'],'canonical_documentation':{'canonical_file':GUIDE,'exact_integrated_delta':bind(patch),'disposition':'GO_INTEGRATED: exact source-backed reader-acquisition versus active-stream revocation clarification; no duplicate implementation needed','evidence':'Direct unchanged resolver/reader AST and existing provider sentinel test; exact original23 preservation; logged189 scoped/1200 configured source checks; all26 workflows unchanged','stale_ambiguity':'Durable handles and restart/read success do not qualify active-stream revocation or public authenticated transport','remaining_uncertainty':'Real PostgreSQL lock/BIGINT ordering, authenticated public transport/HTTP Range HEAD, Windows provider and complete multi-adapter native/lifecycle gates remain open; fullprivate134 and Runtime release gates unchanged','upstream':'none'},'held_gates':['Fresh exact-head current-target complete19 declared hosted jobs plus reviews/threads/draft/policies before merge; old fbde80ba green is historical. Recompute ordinary union and gates if actual target advances.','Actual native producer/build/provider/browser gates; old92498 has6 changed+6 added production leaves and is unqualified.','No source union clears original29990s FIRST startup failure or historical311six failures; original receipts source-bound, cause and cleanup dimensions remain limited.','Real PostgreSQL and public authenticated transport, HTTP Range/HEAD, full multi-adapter lifecycle, private metadata chain remain HOLD.','PR300 must wait actual299 accepted integration; no refresh/retarget authorized by this source GO.','No whole acceptance graph or Runtime publication claim.'],'not_run':['Tests/gates by independent reviewer','Native/provider/backend/browser/artifact acceptance','Push/merge/publication','PR300 refresh'],'upstream':'none'}
p=D/'independent-frozen-source-review.json';p.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(bind(p)))
