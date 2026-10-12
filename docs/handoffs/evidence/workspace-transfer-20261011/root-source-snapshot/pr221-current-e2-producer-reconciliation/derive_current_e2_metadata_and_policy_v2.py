import ast,json,hashlib,stat,subprocess,yaml,fnmatch,collections,itertools,tomllib
from pathlib import Path
O=Path(__file__).parent;P=O/'private-metadata';R='/workspace/engineering/pr282'
H='e2c81adce7858d5a952991ba9a8b7f72e902038a';B='a70993fafc99a9f94041485542d5a720797ca394';T='afe2679cc93bf27fa5021c7698ee7ad3ee21a1b9';A='a54c982462d1e7ad011d8152bfc299d997503fb3'
def g(*a):return subprocess.check_output(['git','--no-optional-locks','-C',R,*a])
def load(n):return json.loads((P/(n+'.decoded-pages.json')).read_bytes())
def bind(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),mode=oct(stat.S_IMODE(p.stat().st_mode)))
def save(n,d):
 p=O/n;p.open('x').write(json.dumps(d,indent=2)+'\n');p.chmod(0o600);return bind(p)
pr0=load('pr-begin')[0];pr1=load('pr-end')[0]
assert pr0['head']['sha']==pr1['head']['sha']==H and pr0['base']['sha']==pr1['base']['sha']==B
for prefix,sha in [('head',H),('base',B)]:assert load(prefix+'-ref-begin')[0]['object']['sha']==load(prefix+'-ref-end')[0]['object']['sha']==sha
assert pr0['state']==pr1['state']=='open' and pr0['draft'] is pr1['draft'] is True
hc=load('head-commit')[0];sc=load('intended-synthetic-commit')[0]
assert hc['sha']==H and hc['tree']['sha']==T and [x['sha'] for x in hc['parents']]==[A,'1299cc4bb6586f467d36ca124faaaaa77362695f']
assert sc['tree']['sha']==T and [x['sha'] for x in sc['parents']]==[B,H]
checks=[c for p in load('checks') for c in p['check_runs']];runs=[r for p in load('runs') for r in p['workflow_runs']]
assert len(checks)==load('checks')[0]['total_count'] and len(runs)==load('runs')[0]['total_count']
assert all(x['head_sha']==H for x in checks+runs)
assert len({x['id'] for x in checks})==len(checks) and len({x['id'] for x in runs})==len(runs)
changed=g('diff','--name-only',B,H).decode().splitlines();push_witness=g('diff','--name-only',A,H).decode().splitlines()
def matches(paths,patterns):
 if not patterns:return True
 hits=set()
 for pat in patterns:
  negative=pat.startswith('!');pat=pat.removeprefix('!')
  for p in paths:
   if fnmatch.fnmatchcase(p,pat):
    if negative:hits.discard(p)
    else:hits.add(p)
 return bool(hits)
flows=[];observed_jobs=[];runtime_jobs=[];full_source=[]
for path in g('ls-tree','-r','--name-only',H,'.github/workflows').decode().splitlines():
 if not path.endswith(('.yml','.yaml')):continue
 body=g('show',H+':'+path);d=yaml.safe_load(body);events=d.get('on',d.get(True));pr=(events.get('pull_request') if isinstance(events,dict) else None)
 eligible=isinstance(events,dict) and 'pull_request' in events and matches(changed,(pr or {}).get('paths',[]))
 rows=[]
 for name,j in d.get('jobs',{}).items():
  matrix=j.get('strategy',{}).get('matrix',{});dimensions={k:v for k,v in matrix.items() if k not in ('include','exclude')};combos=[dict(zip(dimensions,vs)) for vs in itertools.product(*dimensions.values())] if dimensions else ([] if matrix.get('include') else [{}])
  combos=[c for c in combos if not any(all(c.get(k)==v for k,v in ex.items()) for ex in matrix.get('exclude',[]))]
  for inc in matrix.get('include',[]):
   compatible=[c for c in combos if all(k not in dimensions or c[k]==v for k,v in inc.items())]
   if compatible:
    for c in compatible:c.update(inc)
   else:combos.append(inc)
  rows.append(dict(id=name,matrix_count=len(combos),needs=j.get('needs',[]),condition=j.get('if'),matrix=matrix))
 flow=dict(path=path,source_blob=g('rev-parse',H+':'+path).decode().strip(),source_body_SHA256=hashlib.sha256(body).hexdigest(),PR_eligible=eligible,events=events,declared_jobs=rows)
 if eligible:flows.append(flow)
 full_source.append(flow)
eligible={f['path']:f for f in flows};prruns=[r for r in runs if r['event']=='pull_request'];aux=[r for r in runs if r['event']!='pull_request']
assert set(r['path'] for r in prruns)==set(eligible) and len(prruns)==len(eligible)==13
assert sum(j['matrix_count'] for f in flows for j in f['declared_jobs'])==34
for r in runs:
 pages=load(f"jobs-run-{r['id']}");jobs=[j for p in pages for j in p['jobs']];assert len(jobs)==pages[0]['total_count']
 f=next(f for f in full_source if f['path']==r['path']);expected=sum(x['matrix_count'] for x in f['declared_jobs'])
 assert len(jobs)<=expected
 observed_jobs.extend(jobs)
 r['safe_jobs']=[dict(id=j['id'],name=j['name'],status=j['status'],conclusion=j['conclusion']) for j in jobs]
 if r['path']=='.github/workflows/actions_runtime_pypi_release.yml':runtime=r;runtime_jobs=jobs;assert len(jobs)==expected==5
assert {x['id'] for x in checks}=={x['id'] for x in observed_jobs},'POINT_IN_TIME_JOB_CHECK_ID_DIFFERENCE'
assert len(aux)==1 and aux[0]['event']=='push' and aux[0]['path']=='.github/workflows/copilot-setup-steps.yml'
cf=next(f for f in full_source if f['path']==aux[0]['path']);patterns=cf['events']['push']['paths'];witness=[p for p in push_witness if any(fnmatch.fnmatchcase(p,pat) for pat in patterns)]
assert witness
publisher=next(j for j in runtime_jobs if j['name']=='publish (3.12)');assert runtime['status']=='completed' and runtime['conclusion']=='success' and all(j['conclusion']=='success' for j in runtime_jobs)
steps={s['name']:s['conclusion'] for s in publisher['steps']}
for key in ['Verify exact Runtime artifact inventory','Verify Runtime artifacts','Canary local Runtime verifier','Upload artifact: action_server/dist/*']:assert steps[key]=='success'
for key in ['Verify merged tag provenance and version','Check Runtime publish credential','Publish verified artifacts']:assert steps[key]=='skipped'
arts=[a for p in load('runtime-artifacts') for a in p['artifacts']];assert len(arts)==load('runtime-artifacts')[0]['total_count']==5
producer_names={'Linux-wheels':'build-wheels (ubuntu-22.04)','macOS-wheels':'build-wheels (macos-15)','Windows-wheels':'build-wheels (windows-2022)','action-server-dist':'build-sdist (ubuntu-py3.12)','actions-runtime-dist':'publish (3.12)'}
safearts=[]
for a in arts:
 assert a['workflow_run']['id']==runtime['id'] and a['workflow_run']['head_sha']==H and a['expired'] is False
 j=next(j for j in runtime_jobs if j['name']==producer_names[a['name']]);safearts.append(dict(artifact_id=a['id'],name=a['name'],ZIP_size_API_bytes=a['size_in_bytes'],ZIP_digest_API=a['digest'],expired=a['expired'],run_id=runtime['id'],source_head=H,producer_job_id=j['id'],producer_job_name=j['name'],producer_status=j['status'],producer_conclusion=j['conclusion'],API_created_at=a['created_at'],association='Owning source upload step and run metadata; original checkout/log UNKNOWN'))
aggregate=next(a for a in safearts if a['name']=='actions-runtime-dist');assert aggregate['artifact_id']==11708952448
source=g('show',H+':action_server/scripts/publish_verified_runtime.py').decode();tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(getattr(t,'id',None)=='EXPECTED_WHEEL_TAGS' for t in n.targets));comp=node.value
pythons=ast.literal_eval(comp.generators[0].iter);platforms=ast.literal_eval(comp.generators[1].iter.func.value)
version=tomllib.loads(g('show',H+':action_server/pyproject.toml').decode())['tool']['poetry']['version'];assert version=='1.0.3'
policy=dict(schema=1,source=H,source_tree=T,source_path='action_server/scripts/publish_verified_runtime.py',source_blob=g('rev-parse',H+':action_server/scripts/publish_verified_runtime.py').decode().strip(),source_body_bytes=len(source.encode()),source_body_SHA256=hashlib.sha256(source.encode()).hexdigest(),artifact_prefix='actions_runtime',distribution_version=version,manifest_name='actions-runtime-manifest.sha256',wheel_slots=[dict(python='cp'+p,abi='cp'+p,platform_label=k,exact_platform_tag_set=list(v)) for p in pythons for k,v in platforms.items()],wheel_count=6,sdist_count=1,outer_regular_members=8,source_constants_derivation='Immutable AST literal Python/platform generators; owning verifier body retained by SHA; no imported publishing code.',compressed_byte_ceiling=100663296,expanded_byte_ceiling=134217728,single_member_byte_ceiling=67108864)
policy_ref=save('frozen-current-e2-publisher-outer-archive-policy.json',policy)
sourceproof=save('private-current-e2-workflow-filter-matrix-needs-proof.json',dict(source=H,tree=T,PR_changed_paths=changed,PR_eligible_workflows=flows,declared_PR_job_count=34,observed_aux_push=aux[0]['id'],aux_push_filter_witness_paths=witness,aux_push_before_limit='Root normal integration owner and first-parent a54/e2 diff provide filter witness; original push webhook before payload not acquired.',all_workflow_source_bindings=full_source))
counts=lambda rows:dict(collections.Counter((r['status']+' / '+str(r['conclusion'])) for r in rows))
metadata=dict(schema=1,status='CURRENT_E2_PRODUCER_METADATA_READY_FULL_CI_PENDING_NO_ACQUISITION',source=H,tree=T,actual_source_ordered_parents=[x['sha'] for x in hc['parents']],base=B,intended_synthetic=dict(sha=sc['sha'],tree=sc['tree']['sha'],ordered_parents=[x['sha'] for x in sc['parents']],actual_builder_checkout='UNKNOWN_NO_ORIGINAL_BUILDER_LOG_ACQUIRED'),PR_draft=pr0['draft'],PR_state=pr0['state'],named_ref_bracket_stable=True,declared_PR_flows=13,declared_PR_jobs=34,observed_aux_push=1,total_observed_runs=len(runs),checks_count=len(checks),checks_counts=counts(checks),jobs_count=len(observed_jobs),jobs_counts=counts(observed_jobs),different_endpoint_time_counts_kept_separate=True,pending_check_ids=[c['id'] for c in checks if c['status']!='completed'],pending_jobs=[dict(id=j['id'],name=j['name'],status=j['status'],conclusion=j['conclusion']) for j in observed_jobs if j['status']!='completed'],workflow_source_proof=sourceproof,workflow_runs=[dict(id=r['id'],path=r['path'],event=r['event'],head_sha=r['head_sha'],attempt=r['run_attempt'],status=r['status'],conclusion=r['conclusion'],jobs=r['safe_jobs']) for r in runs],Runtime_producer_run=runtime['id'],Runtime_producer_jobs=[dict(id=j['id'],name=j['name'],status=j['status'],conclusion=j['conclusion']) for j in runtime_jobs],publisher_verification_steps=steps,original_Runtime_artifacts_metadata=safearts,selected_original_aggregate=aggregate,publisher_policy=policy_ref,owned_artifact_search='PENDING_BEFORE_PROPOSAL_FREEZE',previous_a54_PREPs='EXACT_HISTORICAL_UNKNOWN_NOT_RUN_NO_ACQUISITION_NO_RUNTIME_FAILURE_INVENTED',artifact_bytes_inner_manifest_RECORD_OAuth_source_authority_consumer='UNKNOWN_NOT_ACQUIRED_NOT_ADMITTED',publication='TAG_CREDENTIAL_AND_PUBLISH_STEPS_SKIPPED_NO_REGISTRY_ADMISSION',API_original_bindings=[bind(p) for p in sorted(P.iterdir()) if p.is_file()],upstream_disposition='none')
save('safe-current-e2-producer-metadata-reconciliation.json',metadata)
print(json.dumps(dict(status=metadata['status'],checks=metadata['checks_counts'],jobs=metadata['jobs_counts'],aggregate=aggregate['artifact_id'],bytes=aggregate['ZIP_size_API_bytes'],sha256=aggregate['ZIP_digest_API'])))
