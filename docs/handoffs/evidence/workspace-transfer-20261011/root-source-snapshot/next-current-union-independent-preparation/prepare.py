from pathlib import Path
import difflib
import hashlib
import itertools
import json
import re
import subprocess
import yaml

OWNED=Path('/workspace/engineering/next-current-union-preparation-owned')
OUT=Path('/workspace/engineering/next-current-union-independent-preparation')
TARGET='1c7585fe8bb3cb9476c3997570bd3f04466f2bbc'
HEADS={309:'41d4ee41190d7d3f3969212471863c70852295ba',308:'483e3e735c268b08acba1fd3930a9a34e0deaa91',299:'80ba4c3adce0d0f5fd8a7040d271ab19433e4042'}
AUDITS={309:114383217609,308:114389876996,299:114392667473}
GUIDE='docs/skills/repository-operations.md'
PRIOR={309:Path('/workspace/engineering/pr309-independent-current-review/source-control-prepush-review.json'),308:Path('/workspace/engineering/pr308-independent-current-review/independent-current-source-review.json'),299:Path('/workspace/engineering/pr299-independent-current-review/independent-current-source-review.json')}
def git(n,*args):return subprocess.check_output(['git','-C',f'/workspace/engineering/pr{n}',*args])
def binding(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def tree(n,x):
 d={}
 for row in git(n,'ls-tree','-rz',x).split(b'\0'):
  if row:
   m,p=row.split(b'\t',1);d[p.decode()]=dict(zip(['mode','kind','blob'],[x.decode()for x in m.split()]))
 return d
def globmatch(value,pattern):
 expression=re.escape(pattern).replace(r'\*\*','DOUBLESTAR').replace(r'\*','[^/]*').replace('DOUBLESTAR','.*').replace(r'\?','[^/]')
 return re.fullmatch(expression,value)is not None
def trigger_selected(trigger,paths):
 if trigger is None:return True
 branches=trigger.get('branches');eligible=branches is None or any(globmatch('integration/community-release-20261008',x)for x in branches)
 required=trigger.get('paths');return eligible and (required is None or any(globmatch(p,x)for p in paths for x in required))
assert json.loads((OWNED/'live-target.json').read_text())['commit']['sha']==TARGET
sims=json.loads((OWNED/'ordinary-union-simulation.json').read_text());assert len(sims)==3
producer=json.loads(Path('/workspace/engineering/native292-owned/producer-input-inventory.json').read_text())
tests=json.loads(Path('/workspace/engineering/native292-owned/selected-test-inventory.json').read_text())
rows=[]
for sim in sims:
 n=sim['pr'];h=HEADS[n];candidate=sim['auto_tree'];assert sim['returncode']==0 and sim['source']==h and sim['target']==TARGET
 assert not git(n,'status','--porcelain')and git(n,'rev-parse','HEAD').decode().strip()==h
 source,target,union=map(lambda x:tree(n,x),[h,TARGET,candidate])
 assert set(source)<=set(union)and set(target)<=set(union)
 ancestor=git(n,'merge-base',h,TARGET).decode().strip();base=tree(n,ancestor);simple=0;both=[]
 for path in set(base)|set(source)|set(target):
  a,b,c=source.get(path),target.get(path),base.get(path)
  if a==b:e=a
  elif a==c:e=b
  elif b==c:e=a
  else:both.append(path);continue
  assert union.get(path)==e,path;simple+=1
 assert both==[GUIDE]
 guide=git(n,'show',candidate+':'+GUIDE).decode()
 for original in [h,TARGET]:
  added=[l[1:]for l in git(n,'diff','--unified=0',ancestor,original,'--',GUIDE).decode().splitlines()if l.startswith('+')and not l.startswith('+++')and l[1:].strip()]
  assert all(line in guide for line in added)
 source_owned=[p for p in source if source[p]!=base.get(p)and not p.startswith('docs/')]
 assert all(union[p]==source[p]for p in source_owned)
 assert all(union[p]==target[p]for p in union if p.startswith('.github/'))
 leaf=p=OUT/f'pr{n}-prospective-complete-leaf-modes-blobs.json';leaf.write_text(json.dumps(union,indent=2,sort_keys=True)+'\n')
 source_delta=git(n,'diff','--name-only',TARGET,candidate).decode().splitlines()
 assert not any(p.startswith('.github/')for p in source_delta)
 differences=[]
 for path,e in producer.items():
  current={**union[path],'sha256':hashlib.sha256(git(n,'show',candidate+':'+path)).hexdigest()}
  if current!=e:differences.append({'path':path,'historical':e,'prospective':current})
 assert len(differences)==(6 if n==299 else 0)
 assert all(union[path]['blob']==e['blob']and union[path]['mode']==e['mode']and hashlib.sha256(git(n,'show',candidate+':'+path)).hexdigest()==e['sha256']for path,e in tests.items())
 added_inputs=[p for p in union if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/'))and p not in producer]
 assert len(added_inputs)==(6 if n==299 else 0)
 if n==299:assert all(union[p]==source[p]for p in added_inputs)
 workflows=[];excluded=[]
 for path in union:
  if not path.startswith('.github/workflows/')or not path.endswith(('.yaml','.yml')):continue
  d=yaml.safe_load(git(n,'show',candidate+':'+path));on=d.get('on',d.get(True,{}))
  if isinstance(on,list):on={x:None for x in on}
  if not isinstance(on,dict)or 'pull_request'not in on:continue
  selected=trigger_selected(on['pull_request'],source_delta)
  info={'path':path,'pull_request':on['pull_request'],'job_keys':list(d.get('jobs',{}))}
  shapes={}
  for key,job in d.get('jobs',{}).items():
   matrix=job.get('strategy',{}).get('matrix')
   if not matrix:count=1
   else:
    axes={key:values for key,values in matrix.items()if key not in ('include','exclude')}
    if not axes:count=len(matrix.get('include',[]))
    else:
     combos=[dict(zip(axes,values))for values in itertools.product(*axes.values())]
     combos=[c for c in combos if not any(all(c.get(k)==v for k,v in x.items())for x in matrix.get('exclude',[]))]
     additions=[x for x in matrix.get('include',[])if not any(all(c.get(k)==v for k,v in x.items()if k in axes)for c in combos)]
     count=len(combos)+len(additions)
   shapes[key]={'matrix':matrix,'declared_job_count':count}
  info['declared_matrix_shapes']=shapes;info['declared_job_count']=sum(x['declared_job_count']for x in shapes.values())
  if selected:workflows.append(info)
  else:excluded.append(info)
 expected_paths={'.github/workflows/ai-audit.yml','.github/workflows/coverage-gate.yml','.github/workflows/actions_runtime_tests.yml','.github/workflows/actions_runtime_pypi_release.yml','.github/workflows/frontend-build-unauthenticated.yml','.github/workflows/developer_toolkit.yml'}
 assert {x['path']for x in workflows}==expected_paths
 declared_counts={'.github/workflows/ai-audit.yml':1,'.github/workflows/coverage-gate.yml':1,'.github/workflows/actions_runtime_tests.yml':3,'.github/workflows/actions_runtime_pypi_release.yml':5,'.github/workflows/frontend-build-unauthenticated.yml':3,'.github/workflows/developer_toolkit.yml':6}
 assert {x['path']:x['declared_job_count']for x in workflows}==declared_counts
 runmeta=json.loads((OWNED/f'runs{n}.json').read_text());assert {r['path']for r in runmeta['workflow_runs']}==expected_paths
 checks=json.loads((OWNED/f'checks{n}.json').read_text());assert checks['total_count']==len(checks['check_runs'])and all(c['head_sha']==h for c in checks['check_runs'])
 observed=[]
 for run in runmeta['workflow_runs']:
  j=json.loads((OWNED/f'pr{n}-run-{run["id"]}-jobs.json').read_text())
  assert j['total_count']==len(j['jobs'])and j['total_count']<=declared_counts[run['path']]
  assert all(x['head_sha']==h for x in j['jobs'])
  observed.append({'run':run['id'],'workflow':run['path'],'head':run['head_sha'],'created_at':run['created_at'],'status':run['status'],'conclusion':run['conclusion'],'jobs_observed':len(j['jobs']),'jobs_expected_when_fully_created':declared_counts[run['path']]})
 oldcontrol=json.loads((OWNED/f'pr{n}-current-prospective-control.json').read_text())
 assert [x['sha']for x in oldcontrol['parents']]==['fbde0d3a248c47c9964851355f96575c89a87329',h]
 assert oldcontrol['tree']['sha']==git(n,'rev-parse',h+'^{tree}').decode().strip()
 assert oldcontrol['tree']['sha']!=candidate
 log=OWNED/f'audit-job-{AUDITS[n]}-original-decoded.log';content=log.read_text();assert oldcontrol['sha']in content
 assert f'HEAD is now at {oldcontrol["sha"][:7]}'in content
 pr=json.loads((OWNED/f'pr{n}.json').read_text());assert pr['head']['sha']==h and pr['state']=='open'
 scoped={309:'route census/startup-barrier/uncategorized-route rejection + existing auth,CORS,browser-session/early-reject controls; realrequest/native qualification remains separate',308:'candidatePoetry/version/filename/uniqueMETADATA negative controls + bounded supervisedprocess receipt/cleanup controls; actualRCCoptin remainsNOT_RUN',299:'run_outputs interprocessclaim/publication, provider identity/no-follow/negativecleanup, migration/legacycache/manifest exclusion controls + sharedRun/alias/resource-history controls; actualpublictransport/backend/native remainseparate'}[n]
 held={309:['Registration/classificationbeforeUvicorn isnotrequestcredential/method/mount/sideeffect authorization or optionaltransport coverage; #152fullacceptanceHOLD.'],308:['Syntheticcandidateversion controls are not newactualPoetrywheel/RCC/provider/warmcache/frozen behavior; earlier67e82/e339wrapperexit-1 retained.'],299:['Sixchangedplussixaddedproductioninputs relativeold92498 invalidateoldnative qualification; do notexclude paths.','PostgreSQL rowlock/order/BIGINT semantics needactualbackend; SQLite notparity.','ScopedRun legacySQL/cache/websocket/request-ID/artifact/analytics exclusions and publicWorkspacegrants/HTTPRangeHEAD/Windowsprovider/multiadapterlifecycle needmeasuredacceptance.','Historical2999cb first90startup/89.28variables/89.259previousmarksum/cleanupunknown retained;311passnotrepair.','PR300refresh remainsblocked untilactual299acceptedmerge; thenordinaryrefresh300ontoreadbackactualmerged299source.']}[n]
 rows.append({'pr':n,'same_existing_branch':pr['head']['ref'],'head':h,'old_head_tree':oldcontrol['tree']['sha'],'live_target':TARGET,'live_target_tree':'35a5168a3904ba41e29047fec2a4cd3b50880a78','common_ancestor':ancestor,'prospective_ordinary_tree':candidate,'simulation_only_no_commit':True,'no_conflicts':True,'complete_leafset':binding(leaf),'prospective_leaf_count':len(union),'source_and_target_no_deletion':True,'independent_nonconflicting_union_paths_checked':simple,'only_both_changed_path':both,'both_guide_addedblocks_retained':True,'original_owned_non_doc_paths':source_owned,'original_owned_non_doc_modes_blobs_preserved':True,'complete_delta_vs_target':source_delta,'full_github_generator_workflows_exact_target':True,'native268_comparison':{'matches':268-len(differences),'differences':differences,'additional_production_inputs_outside268':[{'path':p,'mode_blob':union[p],'sha256':hashlib.sha256(git(n,'show',candidate+':'+p)).hexdigest()}for p in added_inputs]},'selected5_mode_blob_sha_match':True,'producer_parity_scope':'trackedinputsourceparityonly; noactualnative/newwheel/managedorigin/releasequalification'if n!=299 else'OLD_NATIVE_ARTIFACT_NOT_QUALIFIED299','observed_current_checks':{'total':checks['total_count'],'success':sum(c['conclusion']=='success'for c in checks['check_runs']),'failure':sum(c['conclusion']=='failure'for c in checks['check_runs']),'nonterminal':sum(c['status']!='completed'for c in checks['check_runs']),'optional_copilot_setup_seen':sum(c['name']=='copilot-setup-steps'for c in checks['check_runs'])},'observed_head_runs':observed,'old_API_control_bound':{'sha':oldcontrol['sha'],'tree':oldcontrol['tree']['sha'],'ordered_parents':[x['sha']for x in oldcontrol['parents']],'metadata_still_old_base':'fbde evennamedtarget advanced'},'actual_old_audit_checkout_log_private':binding(log),'audit_checkout_limit':'Only auditjob originalcheckout independentlydecoded here; no claim everyotherjoblog/native receipt reviewed','expected_future_PR_workflows':workflows,'expected_future_PR_declared_job_count':19,'filtered_out_future_PR_workflows':excluded,'configured_CI_scope':'sixmatrixworkflows19jobs, optionalcopilotsetupseparate; manualRCC/frozen/provider/recoveryand fullprivate-releasegraph notimplied','smallest_refresh':['rootcapturesactualtargetatdispatchagain; iftargetadvancedrecomputeprospective','ordinarymerge actualconfirmedtarget INTOsameexistingbranch; retainall acceptedhistory/receipts','no newimplementation requiredbythiscleanunion; preservebothguide lessons','canonicalgenerator all8outputs exact pluscomplete.github/treeproof','freshToolkit/scoped'+scoped+'/fullconfiguredRuntime nonintegration/lintRuffformatIsort/typechecks/diffcheck onexactfrozenunion','independent source reviewbefore normalexpectedexistingbranchpush','freshfull19declaredhostedjobs andcompletehead/control/tree/target/review/thread/draft/policy readback beforemerge; norelabeloldCI'], 'scoped_acceptance_and_holds':held,'prior_accepted_source_review':binding(PRIOR[n]),'branch_worktree_unchanged':True})
guide=git(309,'show',TARGET+':'+GUIDE).decode();anchor='### Live pull-request base identity\n\n';assert guide.count(anchor)==1
delta='''After a target advances, a PR payload can retain both its old base SHA and an
old synthetic merge commit. Authenticate that commit's ordered parents and
tree, then compute the complete ordinary union against the live named target;
a green old-head rollup does not validate the new union. A clean prospective
merge is source availability only until it is committed, independently reviewed
and tested on its exact source/control tuple.

Derive expected pull-request jobs from the prospective diff against the live
target and the combined workflow's branch/path filters. An imported generator
change identical to the target is absent from that PR diff; do not demand an
untriggered Core job or omit a triggered artifact job. The owning operational
guide itself triggers Runtime package-artifact PR CI. Reconcile each selected
workflow's complete matrix, including a publisher job created only after its
build dependencies finish; treat Copilot setup as a separate control-plane job.
Native input parity and five unchanged acceptance tests remain scoped source
evidence, not new execution. Changes or new production modules invalidate old
artifact qualification even when selected tests still match. Refresh a stacked
consumer only after its actual dependency merge is accepted and read back.

'''
patch=OUT/'canonical-prospective-source-and-CI-filter-proposed.patch';patch.write_text(''.join(difflib.unified_diff(guide.splitlines(True),guide.replace(anchor,anchor+delta,1).splitlines(True),fromfile='a/'+GUIDE,tofile='b/'+GUIDE)))
result={'verdict':'GO_BOUNDED_READ_ONLY_NEXT_SOURCE_REFRESH_PREPARATION_309_THEN308_THEN299; HOLD_CURRENT_MERGE_NEW_EXECUTION_AND300_DEPENDENT_REFRESH','scope':'No branch/worktree/source mutations, checkout, actualtests/native/provider/retry, newwriter or upstream report. gitmerge-tree wrote only simulation objects insharedGitobjectstore; alltrackedworktree/HEADs unchanged.','actual_target':{'head':TARGET,'tree':'35a5168a3904ba41e29047fec2a4cd3b50880a78','authenticated_ref_binding':binding(OWNED/'live-target.json')},'priority':'309/308 sourceparity/filter readinessfirst,299 source/route/provider/transportholdnext; rootdispatch subjectto310sourcefreeze/V4heavyownership and max2writers','prospective_candidates':rows,'raw_authenticated_snapshot_bindings':[binding(p)for p in sorted(OWNED.glob('*.json'))],'no_old_green_carry':True,'next_target_advance_rule':'Recompute againstactualtarget if anyotherPRintegrates before dispatch; supplied1c758trees notauthorityfor laterbase.','canonical_documentation':{'canonical_file':GUIDE,'exact_proposed_delta':binding(patch),'disposition':'PROPOSED durable actualtarget-simulation/filter/native-stacklesson; no code/doc repo mutation','durable_learning':'cachedsynthetic metadata can remainold; fullordinary sourceunion+pathfilter expectedjobs mustbindactualtarget, andnative sourceparity cannot admit modified oradded production artifact; stackedrefreshneedsactualdependencymerge','evidence':'authenticated1c758 ref/old3APIcontrols andoriginalauditlogs;3cleancompleteordinarytrees/independentleaf+modes+blobs/268+5comparisons; combinedactualtarget workflowfilters+6matrices19jobs','stale_ambiguity':'PRcurrentmerge field meanslivebase; allgreen20includingcopilotmeansnewunion19gate; importedgen automaticallytriggersCoredespitenodiff; selected5matchproves299oldartifact;299sourcepreppermits300refresh','remaining_uncertainty':'futureactualtarget/sourcecommit andfreshsource/hosted/reviewpolicygates;308actualRCC/private,309requestauth/optionaltransport,299backend/native/publictransport/Windowsprovider/multiadapter; fullprivate-releasegraph','upstream':'none'}}
out=OUT/'independent-next-current-union-preparation.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(binding(out)))
