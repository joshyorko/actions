from pathlib import Path
import ast
import hashlib
import json
import subprocess

REPO='/workspace/engineering/pr306'
OWNED=Path('/workspace/engineering/pr306-refresh-preparation')
OUT=Path('/workspace/engineering/pr306-independent-current-review')
HEAD='c38e22c74290dca391617e9693fcf5b2968956df'
TREE='75dfe6916d4a4e8c07a1b76aafea13540bc7afe1'
MERGE='0babc41dbcf2024682be1d89c49ad1a102377c83'
OLD='1421fcf85c1b681aef1fe58fe2902f776f208167'
TARGET='1c7585fe8bb3cb9476c3997570bd3f04466f2bbc'
GUIDE='docs/skills/repository-operations.md'
DB='action_server/src/actions/server/_database.py'
TEST='action_server/tests/action_server_tests/test_database.py'
def git(*args):return subprocess.check_output(['git','-C',REPO,*args])
def binding(p):
 raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def tree(x):
 d={}
 for row in git('ls-tree','-rz',x).split(b'\0'):
  if row:
   meta,p=row.split(b'\t',1);d[p.decode()]=tuple(v.decode()for v in meta.split())
 return d
def functions(raw):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
receipt=OWNED/'frozen-source-receipt.json';assert binding(receipt)['sha256']=='cf34ca2aec87e1b6d0db6313683ce37a53bdd8fb0488f05bf61fe075ebc0b030'
r=json.loads(receipt.read_text())
assert git('log','-1','--format=%H %T %P',HEAD).decode().strip()==f'{HEAD} {TREE} {MERGE}'
assert git('show','-s','--format=%P',MERGE).decode().strip()==f'{OLD} {TARGET}'
assert not git('status','--porcelain')and git('rev-parse','HEAD').decode().strip()==HEAD
old,target,merged,current=map(tree,[OLD,TARGET,MERGE,HEAD])
assert len(target)==len(merged)==len(current)==1409 and len(old)==1385
assert set(old)<=set(merged)and set(target)<=set(merged)
assert {p for p in current if current[p]!=merged[p]}=={GUIDE}
assert sum(current[p]==merged[p]for p in merged)==1408
owned={GUIDE,DB,TEST};assert all(current[p]==target[p]for p in target if p not in owned)
assert current[DB]==merged[DB]==old[DB]
assert current[DB][2]=='6fd267165834f60968ee10a8653dd084a39ad521'
ancestor=git('merge-base',OLD,TARGET).decode().strip();base=tree(ancestor);checked=0;both=[]
for p in set(base)|set(old)|set(target):
 s,t,b=old.get(p),target.get(p),base.get(p)
 if s==t:e=s
 elif s==b:e=t
 elif t==b:e=s
 else:both.append(p);continue
 assert merged.get(p)==e,p;checked+=1
for p in both:
 if p==GUIDE:continue
 for label,sha in [('base',ancestor),('old',OLD),('target',TARGET)]:
  (OUT/f'{Path(p).name}-{label}').write_bytes(git('show',sha+':'+p))
 m=subprocess.run(['git','merge-file','--stdout',str(OUT/f'{Path(p).name}-old'),str(OUT/f'{Path(p).name}-base'),str(OUT/f'{Path(p).name}-target')],capture_output=True)
 assert m.returncode==0 and m.stdout==git('show',HEAD+':'+p)
oldfunctions=functions(git('show',OLD+':'+TEST));newfunctions=functions(git('show',HEAD+':'+TEST));targetfunctions=functions(git('show',TARGET+':'+TEST))
selected=['test_database_transactions_nested','test_nested_transaction_savepoint_start_failure_preserves_error_and_counter']
assert all(oldfunctions[n]==newfunctions[n]for n in selected)
assert all(targetfunctions[n]==newfunctions[n]for n in targetfunctions)
assert set(newfunctions)-set(targetfunctions)=={selected[1]}
testbody=git('show',HEAD+':'+TEST).decode()
for needle in ['sqlite3.SQLITE_SAVEPOINT','connection.set_authorizer(deny_savepoint_start)','nested_body_entered = True','sqlite3.DatabaseError','recovery_nesting.append','[("recovered",)]']:
 assert needle in testbody
for e in r['gate_logs'].values():assert binding(Path(e['path']))==e
for name in ['source_proof','source_inspector','generator_roundtrip','read_only_preparation','historical_read_only_doc_proposal']:
 e=r[name];assert binding(Path(e['path']))==e
for path,digest in r['retained_prior_receipts'].items():assert binding(Path(path))['sha256']==digest
full=(OWNED/'full-source.log').read_text();assert '+ poetry run invoke test-not-integration'in full and '1151 passed, 13 skipped, 15 warnings'in full and 'actual main robot run" was SUCCESS'in full
scoped=(OWNED/'database-scoped.log').read_text();assert 'CURRENT_SOURCE_AND_OWN_PACKAGE_PREFIX=PASS'in scoped and '2 passed'in scoped and '16 passed'in scoped
dbcomplete=(OWNED/'database-complete-source.log').read_text();assert '61 passed, 12 skipped'in dbcomplete
static=(OWNED/'static.log').read_text()
for needle in ['+ poetry run invoke lint','poetry run isort --check src tests','301 files already formatted','+ poetry run invoke typecheck','Success: no issues found in 337 source files','actual main robot run" was SUCCESS']:assert needle in static
assert '69 passed'in (OWNED/'toolkit.log').read_text()
roundtrip=json.loads((OWNED/'generator-roundtrip.json').read_text());assert roundtrip['status']=='PASS'and roundtrip['all_tracked_yaml_before_after_identical']
assert len(roundtrip['sha256'])==26
for path,digest in roundtrip['sha256'].items():assert hashlib.sha256(git('show',HEAD+':'+path)).hexdigest()==digest and current[path]==target[path]
assert all(current[p]==target[p]for p in current if p.startswith('.github/'))
comparisons=[]
for name,n,diffs in [('producer-input-inventory.json',268,[DB]),('selected-test-inventory.json',5,[])]:
 inv=json.loads(Path('/workspace/engineering/native292-owned',name).read_text());assert len(inv)==n;changed=[]
 for path,e in inv.items():
  observed={'mode':current[path][0],'kind':current[path][1],'blob':current[path][2],'sha256':hashlib.sha256(git('show',HEAD+':'+path)).hexdigest()}
  if observed!=e:changed.append({'path':path,'historical':e,'current':observed})
 assert [x['path']for x in changed]==diffs
 comparisons.append({'inventory':name,'entries':n,'matches':n-len(changed),'differences':changed})
guide=git('show',HEAD+':'+GUIDE)
oldparagraph=git('show',OLD+':'+GUIDE).split(b'For nested database transactions,')[1].split(b'Actions Core pull requests')[0]
oldparagraph=b'For nested database transactions,'+oldparagraph
mergeguide=git('show',MERGE+':'+GUIDE);assert mergeguide.count(oldparagraph)==1 and mergeguide.replace(oldparagraph,b'',1)==git('show',TARGET+':'+GUIDE)
projected=guide
for marker in [b'Keep backend fault injection explicit:',b'RCC environment creation reporting `SUCCESS`']:
 start=projected.index(marker);end=projected.index(b'\n\n',start)+2;projected=projected[:start]+projected[end:]
assert projected==mergeguide and b'A successful cold `holotree variables`' not in guide
patch=OUT/'canonical-integrated-current-database-bootstrap-delta.patch';patch.write_bytes(git('diff',MERGE,HEAD,'--',GUIDE));e=r['documentation_improvement']['Exact_delta'];assert binding(Path(e['path']))==e and patch.read_bytes()==Path(e['path']).read_bytes()
assert git('diff','--numstat',MERGE,HEAD).decode().strip()==f'20\t0\t{GUIDE}'
subprocess.check_call(['git','-C',REPO,'diff','--check',MERGE,HEAD])
assert not Path(REPO,'action_server/setup.py').exists()
pgpath=next(Path(p)for p in r['retained_prior_receipts']if p.endswith('pg_review.json'));pg=json.loads(pgpath.read_text());assert pg['source']['head']==OLD and pg['source']['module_sha256']==hashlib.sha256(git('show',HEAD+':'+DB)).hexdigest()
assert 'already-aborted'in pg['scope']and 'No healthy-transaction'in pg['scope']
windows=Path(r['retained_windows']['log']);assert binding(windows)['sha256']=='2608e02752145c7dc50b002df9208fb33c64b955da03106411b9d0404c3f93ee'
wt=windows.read_text(encoding='utf-8-sig');assert '87.81'in wt and '989 passed, 94 skipped'in wt and '1 failed, 129 passed, 18 skipped, 1086 deselected'in wt
result={
 'verdict':'GO_NORMAL_PUSH_EXACT_C38_CURRENT306_SOURCE_REFRESH; HOLD_FRESH_HOSTED_MERGE_CURRENT_NATIVE_HEALTHY_POSTGRES_AND_FULL84_RELEASE',
 'scope':'read-only exact ordinaryrefresh/source/rawreceipts review; no reviewer source/test/provider/Postgres/native/run mutation',
 'source':{'head':HEAD,'tree':TREE,'parent':MERGE,'ordinary_merge_tree':'a9221f5b0ff2f959b26ed2c5532bb39d24bed7de','ordered_ordinary_parents':[OLD,TARGET],'actual_target_tree':'35a5168a3904ba41e29047fec2a4cd3b50880a78','same_branch':r['branch'],'clean':True},
 'independent_preservation':{'target_and_final_leaves':1409,'original_leaves':1385,'no_source_or_target_deletions':True,'nonowned_paths_complete_modes_blobs_equal_target':True,'original_Database_blob_retained':current[DB],'both_original_regression_ASTs_preserved':selected,'all_target_test_function_ASTs_retained':True,'only_new_test_vs_target':selected[1],'ordinary_nonconflicting_3way_paths_checked':checked,'both_parent_changed_paths':both,'non_doc_both_changed_external_clean_merge_file_byteequal':True,'oldguideparagraph_plus_entire_target_guide_preserved':True,'final_only_delta':'20canonicalguide lines','final_non_doc_mode_blob_pairs_identical_to_tested_union':1408,'complete_github_generator_workflows_exact_actualtarget':True},
 'source_behavior':'Originalacceptedfix publishesnestedtransaction depth only AFTER SAVEPOINT creation succeeds. MeaningfulSQLite authorizerDENY exercisescreationfailure beforebody and asserts originalDBError/sqliteerrorchain, noenteredbody, counterszero, noopenconnectiontransaction andsameconnection nested recovery; accepted successfulrollback control unchanged. No new production implementation.',
 'actual_current_validation':{'Doctor':'PASS','freshownBootstrap':'PASS','toolkit':69,'own_Database_origin_and_package_prefix':'asserted in rawfocused log','transaction_focus':2,'complete_database_source_pass':61,'actual_PostgreSQL_skips':12,'configured_source_pass':1151,'configured_source_existing_skips':13,'warnings':15,'configured_lint':'Ruffcheck/format301/IsortPASS','configured_typecheck_source_files':337,'tracked_all_yaml_dependabot_roundtrip':26,'canonicaldiffcheck':'PASS','tests_source':'0babc ordinaryunion+final20workingguide lines; frozen c38 only guide and1408othermode/blobpairs exact'},
 'producer_scope':comparisons,'old_native92498_qualification':'NOT_QUALIFIED_current306 changes _database.py; no exclusion/relabeling oforiginalartifact',
 'original_worker_receipt':binding(receipt),'verified_raw_worker_logs':r['gate_logs'],'verified_source_proof':r['source_proof'],'verified_source_inspector':r['source_inspector'],'verified_historical_acceptance':r['retained_prior_receipts'],
 'PostgreSQL_limit':'Retained4cf source1421 PostgreSQL17.11/psycopg3.3.4 already-abortedtransactionSAVEPOINT25P02 recovery is same_Database_bytes only; not currentunion/newexecution or healthytransactiondenial/full84. TwelvecurrentbackendtestsSKIPPED; no newservice/run.',
 'historical_TDD_limit':r['retained_TDD_limits'],'historical_Windows_limit':'Retainededdec/source1421 original989/94source and1FAIL129PASS18SKIP1086DESELECTnative; templateFIRSTstartup beforecollisionassertions,87.81RCCvariables/87.799previousmarksum; oldselftestlacksaccepted20cleanup; no sourcefix/regressionfailure/rootcause/fullownedcleanup inferred. No currentnative retry. Fullrawlog remainsPRIVATE.',
 'ephemeral_setup_py':r['ephemeral_setup_py'],
 'held_gates':['Fresh exactc38 currentunion hostedcompletecheck/review/target/policy gates beforemerge; originalgreen failuresnotcarried.','Changedproductiondatabaseinvalidatesold92498currentnative qualification evenwithfive selectedtestsunchanged.','ActualhealthyPostgreSQLSAVEPOINTdenial/full84 acceptance remainsOPEN;12currentPGskips notpassingbackend.','HistoricalWindows startupownership/cause/fullcleanup unknown; later311pass doesnotrepair306source-boundfailure.','Private01f/fafb/frozenv6spec-runner/fullissue and Runtimepublication gates remainHOLD.'],
 'canonical_documentation':{'canonical_file':GUIDE,'exact_integrated_delta':binding(patch),'disposition':'INTEGRATEDc38doconly20line addendum retainingoldfixandactualtargetlessons; reviewrequestedremovalofunqualifiedcold adjective applied','durable_learning':'healthySQLiteSAVEPOINTauthorizationdenial differsfromalreadyabortedPostgreSQLrecovery; RCCcreationSUCCESS differsfromRuntime ready-port admission/reachedtests','evidence':'sameacceptedDatabase/regressionAST50f/6982;historicalPG4cf moduleidentity scopedactualrecovery;historicalWindows2608 logstartup; current2+61/12+1151/13+69 sourcegates/static/26YAMLroundtrip','stale_ambiguity':'sourcepass orabortedPGcase proveshealthyPGdenial/full84; environmentSUCCESS provesRuntime ready/reachedcatalogassertions; coldprivateenvironment implieswholecache qualification; sourceunion clearsoldfailure/relabelsoldnative','remaining_uncertainty':'currentexacthosted/native/currentartifact/healthyPGfull84/historicalownedstartupcausecleanup/private-releaseacceptance; unavailabletransientsetupbytes','upstream':'none'},
}
p=OUT/'independent-current-source-review.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(binding(p)))
