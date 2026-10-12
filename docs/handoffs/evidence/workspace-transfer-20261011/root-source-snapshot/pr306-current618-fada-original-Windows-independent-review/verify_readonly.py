from pathlib import Path
import ast,collections,hashlib,json,re,stat,subprocess
O=Path('/workspace/engineering/pr306-current618-fada-original-Windows-failure-owned');D=Path('/workspace/engineering/pr306-current618-fada-original-Windows-independent-review');R=Path('/workspace/engineering/pr306');SOURCE='fada8e068f61f6e0e380ec4685eed2f4cf0b9ade';ACTUAL='522b7bc6e7e9207dac0c745b49d90907ecdf3080';API='3dae00de315bfa9d909cc2a546f717da342c329b';TARGET='6181b044c75de35386f1ae30e71725398b6a7feb';TREE='a31db4434c7bbe69bf572626d2174f64f9ff2f39'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(e):assert bind(e['path'])=={k:e[k] for k in ['path','bytes','sha256']}
def git(*a):return subprocess.check_output(['git','-C',str(R),*a],stderr=subprocess.PIPE)
owner=O/'OWNERFINAL-original306-fada-Windows-readiness-failure-v6.json';assert owner.stat().st_size==22555 and sha(owner)=='8c7dd3ed54418c4e69456e831d710b6436fdc4969be7b55fdb4d94d2b19d9427';v=json.loads(owner.read_text());assert len(v['evidence'])==33
for e in v['evidence']:check(e)
check(v['original_decoded_log']);log=Path(v['original_decoded_log']['path']);assert log.stat().st_size==821618 and sha(log)=='4b7d014d43ace9a16f78061efc366efd0e1c51a42cbf3e0649209356b1c06cd7' and stat.S_IMODE(log.stat().st_mode)==0o600
raw=log.read_text().splitlines();lines=[re.sub(r'^\d{4}-\d\d-\d\dT\S+\s+','',re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',s)) for s in raw]
assert 'log -1' in lines[111] and ACTUAL in re.findall(r'\b[0-9a-f]{40}\b',lines[112])
assert git('show','-s','--format=%H %T %P',ACTUAL).decode().split()==[ACTUAL,TREE,TARGET,SOURCE]
assert git('rev-parse',SOURCE+'^{tree}').decode().strip()==TREE and git('ls-tree','-rz',ACTUAL)==git('ls-tree','-rz',SOURCE)
assert sum(bool(row) for row in git('ls-tree','-rz',ACTUAL).split(b'\0'))==1419
ci=json.loads(Path(v['CI_metadata_owner']['path']).read_text());check(v['CI_metadata_owner']);subject=next(s for s in ci['subjects'] if s['PR']==306);assert subject['synthetic_Git']=={'sha':API,'tree':TREE,'ordered_parents':[TARGET,SOURCE],'complete_typed_source_API_tree_equal_local_source':True,'leaf_count':1419} and API!=ACTUAL
private=json.loads(Path(v['complete_individual_outcome_census']['path']).read_text());check(v['complete_individual_outcome_census']);results=[]
for name,start,end,expected in [('source',1701,4332,{'PASSED':1154,'SKIPPED':142}),('binary',4393,4566,{'PASSED':126,'FAILED':5,'SKIPPED':19})]:
 rows=[]
 for i in range(start,end):
  text=lines[i-1]
  if '.py::' not in text:continue
  tokens=list(re.finditer(r'PASSED|SKIPPED|FAILED|ERROR',text))
  if not tokens:continue
  token=tokens[-1];m=re.search(r'((?:[A-Za-z0-9_.-]+[/\\])*[A-Za-z0-9_-]+\.py::)',text);assert m;node=text[m.start():token.start() if token.start()>m.start() else len(text)].strip().replace('\\','/');node=re.sub(r'\s+\[\s*\d+%\]\s*$','',node).strip();rows.append({'line':i,'node':node,'status':token.group()})
 assert rows==private[name] and dict(collections.Counter(e['status'] for e in rows))==expected
 summaryLine=4332 if name=='source' else 6813;summary=lines[summaryLine-1]
 if name=='source':assert '1154 passed, 142 skipped' in summary and 'deselected' not in summary
 else:assert '5 failed, 126 passed, 19 skipped, 1299 deselected' in summary
 results.append({'phase':name,'counts':expected,'total':len(rows),'deselected':None if name=='source' else 1299,'duration_seconds':410.31 if name=='source' else 1639.03,'complete_individual_nodes_equal_original_private_census':True,'terminal_summary_reconciled':True})
failed=[e['node'] for e in private['binary'] if e['status']=='FAILED'];assert failed==v['diagnosis']['failed_integration_nodes'] and len(failed)==5
sourceProof=json.loads(Path(v['source_AST_proof']['path']).read_text());check(v['source_AST_proof']);assert len(sourceProof)==8
for e in sourceProof:
 check(e['private_snapshot']);body=git('show',ACTUAL+':'+e['source_path']);assert body==git('show',SOURCE+':'+e['source_path'])==Path(e['private_snapshot']['path']).read_bytes() and hashlib.sha256(body).hexdigest()==e['body_sha256']
 functions=[{'name':n.name,'line':n.lineno,'end_line':n.end_lineno,'AST_sha256':hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest()} for n in ast.walk(ast.parse(body)) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))];assert functions==e['functions_AST']
sections=[('resource',4566,4990),('template',4990,5388),('prompt',5388,6045),('resource_history',6045,6430),('generation_drain',6430,6814)];failureRows=[]
for (name,start,end),f in zip(sections,v['diagnosis']['failures']):
 assert name==f['scenario'];part=lines[start-1:end-1];timeout=[i for i in range(start,end) if re.search(r'^E\s+.*\bTimeoutError\b',lines[i-1])];notes=[i for i in range(start,end) if 'cleanup did not fully complete' in lines[i-1] and re.search(r'^E\s+',lines[i-1])];assert timeout==f['timeout_trace_lines'] and notes==f['cleanup_incomplete_secondary_note_lines']
 assert f['first_start_timeout'] and f['native_readiness_budget_seconds']==90 and f['failure_cleanup_budget_seconds']==20 and f['reached_catalog_history_generation_assertions'] is False
 for e in f['source_start_call_stack']:assert re.search(r':'+str(e['source_line'])+r'\b',lines[e['log_line']-1])
 complete=[{'line':i,'call_seconds':float(re.search(r'took\s*:?\s*(\d+\.\d+)s',lines[i-1]).group(1))} for i in range(start,end) if 'variables' in lines[i-1] and re.search(r'took\s*:?\s*(\d+\.\d+)s',lines[i-1])];assert complete==f['RCC_variables_completion']
 failureRows.append({'scenario':name,'first_readiness_timeout_before_semantics':True,'budget_seconds':90,'secondary_cleanup_budget_seconds':20,'cleanup':False if notes else 'UNKNOWN','variables_reported_call_duration_seconds':[x['call_seconds'] for x in complete]})
assert sum(x['cleanup'] is False for x in failureRows)==2 and sum(x['cleanup']=='UNKNOWN' for x in failureRows)==3 and [x['variables_reported_call_duration_seconds'] for x in failureRows]==[[],[],[87.2],[],[]]
patch=Path(v['Documentation_improvement']['Exact_patch']['path']);check(v['Documentation_improvement']['Exact_patch']);assert patch.stat().st_size==486 and sha(patch)=='50ad18bce0a30cbfb1cb346d1768729b67ea20125796a6558bb57e1594ef2aec'
assert patch.read_text()==v['Documentation_improvement']['Exact_proposed_delta']
existing=v['Documentation_improvement']['Verified_existing_result_token_delta']['patch'];check(existing);guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text();delta=''.join(s[1:] for s in Path(existing['path']).read_text().splitlines(keepends=True) if s.startswith('+') and not s.startswith('+++'));assert delta.strip() in guide
assert v['diagnosis']['phase_census'][0]['deselected'] is None and 'UNREPORTED/null' in v['construction_predecessor_disposition']['qualification'];check(v['construction_predecessor_disposition']['original_v4_owner'])
result={'schema':'actions.independent-original306-fada-Windows-log-diagnosis/v1','verdict':'GO_BOUNDED_FAILURE_CENSUS_AND_CANONICAL_PROPOSAL_ONLY_ENGINEERING_ACCEPTANCE_HOLD','owner_final':bind(owner),'subject':{'source':SOURCE,'actual_original_runner':ACTUAL,'ordered_parents':[TARGET,SOURCE],'tree':TREE,'later_frozen_API_merge_ref':API,'run':38130109466,'job':114442488607},'original_log':bind(log),'all33bindings_verified':True,'complete1419_typed_Git_source_equal_original_checkout':True,'complete_phase_census':results,'failed_nodes':failed,'failure_scope':failureRows,'primary':'FIVE_FIRST90s_NATIVE_READY_TIMEOUTS_BEFORE_CATALOG_HISTORY_GENERATION_DRAIN_SEMANTICS','limits':['Two original20s cleanup-incomplete notes are failures; otherthree cleanupUNKNOWN, no universal cleanup or activeprocess cause inferred','One reported87.20s holotree variables caller completion is not a hang/cache/pipe/deadlock or readiness-cause proof','Current latermerge3dae is distinct from executed522b even with equalorderedparents/fulltree; no checkoutrelabel','Construction-onlyv4 source-deselected153 claim retained and corrected to UNREPORTED/null; no sourcefull currentactual acceptance','New startupartifact snapshot content remains separate from this original log-only review; no unpublished mutable worker files sampled'],'no_source_changes_tests_acquisition_ref_mutation_or_new_execution':True,'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md','Exact_proposal':bind(patch),'Disposition':'ACCEPT exact50ad five-line originalrunner/latermerge identity lesson after independent review; ownerproposal now qualified, prior premature acceptance message is not approval evidence','Durable_learning_captured':'Bind original failure to actualjob checkout and immutable parents/fulltree; retain later currentmerge metadata separately despite content equality; reconcile each phase terminal outcomes independently','Evidence':'Original log112/113 plus Git522b/1419equalfada; frozenAPI3dae sameparents/tree distinctSHA; all1296source and150integration outcomes reconciled; originaltimeouts/cleanup/caller-duration scope','Stale_or_ambiguous_guidance_removed':'Rejects latermerge-ref identity reassignment, five-failure semanticfix inference,87.20hang inference and unreportedsource deselectcount','Remaining_uncertainty':'Readiness preparationcause, unsampledprocess/streamstate, cleanupdetails and whole306native/private/release acceptance remain unresolved; separatestartupartifact reviewed independently'},'upstream_disposition':'none'}
p=D/'OWNERFINAL-independent-original306-fada-Windows-failure-review.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'OWNERFINAL':bind(p)}))
