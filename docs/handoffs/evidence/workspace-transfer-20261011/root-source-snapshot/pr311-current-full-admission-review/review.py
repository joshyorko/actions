from pathlib import Path
import hashlib
import json
import subprocess
import difflib
import yaml

REPO='/workspace/engineering/pr311'
OWNED=Path('/workspace/engineering/pr311-current-full-admission-owned')
OUT=Path('/workspace/engineering/pr311-current-full-admission-review')
HEAD='d75b25fb4c354e5c95bc0f639b426d6ff402104b'
TARGET='fbde0d3a248c47c9964851355f96575c89a87329'
CONTROL='e3c52c5cf3f2a4437a54af137f59264cc77d91ae'
def read(n):return json.loads((OWNED/n).read_text())
def binding(p):
 b=p.read_bytes();return {'path':str(p),'size':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def git(*a):return subprocess.check_output(['git','-C',REPO,*a])
def tree(x):
 result={}
 for row in git('ls-tree','-rz',x).split(b'\0'):
  if row:
   meta,path=row.split(b'\t',1);result[path.decode()]=tuple(v.decode()for v in meta.split())
 return result
pr=read('pr.json');g=read('graphql-admission.json')['data']['repository']['pullRequest']
assert pr['head']['sha']==g['headRefOid']==HEAD and pr['draft']==g['isDraft']==True
assert pr['base']['ref']=='integration/community-release-20261008'
assert g['potentialMergeCommit']=={'oid':CONTROL,'tree':{'oid':'35a5168a3904ba41e29047fec2a4cd3b50880a78'},'parents':{'nodes':[{'oid':TARGET},{'oid':HEAD}]}}
assert g['mergeable']=='MERGEABLE' and g['mergeStateStatus']=='CLEAN'
assert read('actual-base-branch.json')['commit']['sha']==TARGET
assert g['baseRefOid']==pr['base']['sha']=='ba85aac7324ea4463bfba8c5f8586e27706dc2fe'
assert read('reviews.json')==[]
for k in ['reviews','reviewThreads']:
 assert g[k]['totalCount']==0 and not g[k]['pageInfo']['hasNextPage'] and not g[k]['nodes']
assert g['baseRef']['branchProtectionRule'] is None and read('actual-base-rules.json')==[]
assert read('actual-base-protection.json')['message']=='Resource not accessible by integration'
assert read('statuses.json')['statuses']==[]
checks=read('checks.json');assert checks['total_count']==len(checks['check_runs'])==23
assert all(c['head_sha']==HEAD and c['status']=='completed' and c['conclusion']=='success' for c in checks['check_runs'])
runs=read('all-head-runs.json');assert runs['total_count']==len(runs['workflow_runs'])==7
source_admission=read('actual-control-source-admission.json')
for e in source_admission:
 p=Path(e['path']);raw=p.read_bytes();assert binding(p)=={k:e[k]for k in ['path','size','sha256']}
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==e['blob']
expected={
 '.github/workflows/ai-audit.yml':['audit'],
 '.github/workflows/coverage-gate.yml':['coverage'],
 '.github/workflows/frontend-build-unauthenticated.yml':[f'Build Action Server binary without credentials ({x})'for x in ['ubuntu-22.04','windows-2022','macos-15']],
 '.github/workflows/actions_core_tests.yml':[f'build ({x}-py3.10-devmode)'for x in ['ubuntu','windows','macos']]+['candidate-wheel'],
 '.github/workflows/actions_runtime_tests.yml':[f'build ({x}-py3.12-devmode)'for x in ['ubuntu','windows','macos']],
 '.github/workflows/actions_runtime_pypi_release.yml':['build-sdist (ubuntu-py3.12)']+[f'build-wheels ({x})'for x in ['ubuntu-22.04','windows-2022','macos-15']]+['publish (3.12)'],
 '.github/workflows/developer_toolkit.yml':None,
}
assert set(x['path']for x in runs['workflow_runs'])==set(expected)
observed=[];ids=set()
for run in runs['workflow_runs']:
 assert run['head_sha']==HEAD and run['event']=='pull_request' and run['status']=='completed' and run['conclusion']=='success' and run['run_attempt']==1
 jobs=read(f"run-{run['id']}-jobs.json");assert jobs['total_count']==len(jobs['jobs'])
 assert all(j['head_sha']==HEAD and j['status']=='completed' and j['conclusion']=='success'for j in jobs['jobs'])
 document=yaml.safe_load((OWNED/'actual-control-source'/run['path']).read_text())
 # Inspect actual authenticated workflow declarations rather than relying on display counts.
 decl=document['jobs'];names=[j['name']for j in jobs['jobs']]
 if run['path'].endswith('developer_toolkit.yml'):
  matrix=decl['toolkit']['strategy']['matrix']['include'];assert len(matrix)==len(names)==6
  for m in matrix:
   prefix=f"toolkit ({m['lane']}, {m['rcc_version']}, {m['os']}, {m['asset']}, {m['sha256'][:12]}"
   assert sum(n.startswith(prefix)for n in names)==1
 else:
  assert sorted(names)==sorted(expected[run['path']])
 if run['path'].endswith('actions_core_tests.yml'):assert len(decl['build']['strategy']['matrix']['name'])==3 and 'candidate-wheel'in decl
 if run['path'].endswith('actions_runtime_tests.yml'):assert len(decl['build']['strategy']['matrix']['name'])==3
 if run['path'].endswith('actions_runtime_pypi_release.yml'):
  assert len(decl['build-wheels']['strategy']['matrix']['os'])==3
  publication=[s for s in decl['publish']['steps']if s['name']=='Publish verified artifacts'];assert len(publication)==1 and "github.event_name == 'push'"in publication[0]['if']
  j=[j for j in jobs['jobs']if j['name']=='publish (3.12)'][0]
  assert [s for s in j['steps']if s['name']=='Publish verified artifacts'][0]['conclusion']=='skipped'
 for j in jobs['jobs']:
  assert j['id']not in ids;ids.add(j['id'])
  assert sum(c['id']==j['id'] and c['check_suite']['id']==run['check_suite_id']for c in checks['check_runs'])==1
 observed.append({'run':run['id'],'workflow':run['path'],'suite':run['check_suite_id'],'jobs':[{'id':j['id'],'name':j['name'],'conclusion':j['conclusion']}for j in jobs['jobs']]})
assert len(ids)==23
actualjson=read('actual-control-tree.json');assert actualjson['sha']==g['potentialMergeCommit']['tree']['oid']and actualjson['truncated']is False
actual={x['path']:(x['mode'],x['type'],x['sha'])for x in actualjson['tree']if x['type']!='tree'}
base=git('merge-base',HEAD,TARGET).decode().strip();b,s,t=map(tree,[base,HEAD,TARGET]);checked=0;both=[]
for p in set(b)|set(s)|set(t):
 u,v,w=s.get(p),t.get(p),b.get(p)
 if u==v:e=u
 elif u==w:e=v
 elif v==w:e=u
 else:both.append(p);continue
 assert actual.get(p)==e,p;checked+=1
assert set(actual)==set(s)|set(t)and checked==1407 and len(actual)==1409
assert set(both)=={'.github/workflows/_gen_workflows.py','docs/skills/repository-operations.md'}
for label,sha in [('base',base),('head',HEAD),('target',TARGET)]:
 (OUT/f'generator-{label}.py').write_bytes(git('show',sha+':.github/workflows/_gen_workflows.py'))
merged=subprocess.run(['git','merge-file','--stdout',str(OUT/'generator-head.py'),str(OUT/'generator-base.py'),str(OUT/'generator-target.py')],capture_output=True)
assert merged.returncode==0
assert merged.stdout==(OWNED/'actual-control-source/.github/workflows/_gen_workflows.py').read_bytes()
actualguide=(OWNED/'actual-control-source/docs/skills/repository-operations.md').read_text()
for sha in [HEAD,TARGET]:
 additions=[x[1:]for x in git('diff','--unified=0',base,sha,'--','docs/skills/repository-operations.md').decode().splitlines()if x.startswith('+')and not x.startswith('+++')and x[1:].strip()]
 assert all(x in actualguide for x in additions)
windows=Path('/workspace/engineering/pr311-current-d75-windows-independent-review/independent-current-terminal-readback.json')
assert binding(windows)['sha256']=='3b4e84132a7be9e36892e41f4f31120ddd359a794acaff576f6b1b56334f97ed'
v2=Path('/workspace/engineering/windows-next-observation-independent-review/independent-v2-design-review.json')
assert binding(v2)['sha256']=='95f44464acd56e278a87890e0c5f24da9b38cbfb044f925f48bbf1c2221355e3'
delta='''A complete green pull-request rollup admits its observed source/control tuple,
not a later integration target. Reconcile every declared matrix job with its
workflow run and check suite; a job named `publish` on a pull request can retain
verified artifacts while its push-only registry upload remains skipped. Check
draft state, reviews and conversation threads separately. A protection endpoint
that denies access is an unverified policy surface, not permission to bypass
repository or campaign acceptance requirements.

After a dependency integrates, refresh the existing source branch by an ordinary
merge with the actual target commit. Preserve source history and historical
receipts, inspect the complete prospective union, and regenerate all canonical
workflow outputs before fresh configured and hosted gates. A passing current
Windows startup can justify deferring a diagnostic-only observation proposal;
it does not establish a timeout cause, full descendant cleanup, or acceptance of
a different branch's earlier failure. Keep design-only acceptance separate from
implementation and execution authorization.

'''
anchor='### Live pull-request base identity\n\n';assert actualguide.count(anchor)==1
proposed=actualguide.replace(anchor,anchor+delta,1)
patch=OUT/'canonical-full-admission-and-dependency-refresh-proposed.patch'
patch.write_text(''.join(difflib.unified_diff(actualguide.splitlines(True),proposed.splitlines(True),fromfile='a/docs/skills/repository-operations.md',tofile='b/docs/skills/repository-operations.md')))
receipt={
 'verdict':'GO_EXACT_D75_E3C52_FBDE_OBSERVED_SOURCE_UNION_AND_COMPLETE23_CURRENT_CI; HOLD_MERGE_PENDING310_TARGET_DEPENDENCY_AND_DRAFT_FRESH_ADMISSION',
 'scope':'read-only complete source/CI/readiness review and future minimal samebranch refresh proposal; no writer/implementation/native rerun/merge/review submission',
 'exact_tuple':{'source_head':HEAD,'source_tree':'22c984ea5ce5275803308790c519263e7027b40c','actual_control':CONTROL,'actual_tree':'35a5168a3904ba41e29047fec2a4cd3b50880a78','ordered_actual_parents':[TARGET,HEAD],'named_target':'integration/community-release-20261008','live_target':TARGET,'stale_PR_payload_base':base},
 'complete_current_CI':{'checks':23,'all_success':True,'workflow_runs':7,'no_legacy_commit_statuses':True,'declared_job_inventory':observed,'scope':'all7triggered workflows fulldeclared matrix shapes matched actualauthenticated workflow blobs/checksuites; no optional manual/private acceptance assumed','publish_job_registry_upload':'push-only upload skipped on actualpullrequest, artifact verifier/canary jobgreen is not registrypublication'},
 'complete_source_union':{'actual_authenticated_leaves':1409,'nonconflicting_leaf_modes_blobs_verified':1407,'both_parent_changed_paths':both,'combined_generator_matches_external_clean_git_merge_file':True,'both_parent_canonical_guide_additions_retained':True,'source_checkpoint_d75_and_original1151_ancestry_preserved':True},
 'reviews_threads_policy':{'isDraft':True,'submitted_reviews':0,'review_threads':0,'unresolved_threads':0,'pagination_complete':True,'reviewDecision':g['reviewDecision'],'mergeable':g['mergeable'],'mergeStateStatus':g['mergeStateStatus'],'live_target_rules':[],'GraphQL_branchProtectionRule':None,'REST_protection':'403Resource not accessible by integration; do not infer waivedpolicies','repository_AGENTS':'required relevant source/static/hosted gates and durable operational guidance; campaign requires accepted source/reviews/exacttarget admission'},
 'current_windows_readback':binding(windows),'retained_windows_V2_design_only':binding(v2),'V2_disposition':'DEFER_IMPLEMENTATION_AND_ACTUAL_RUN current6formerlyfailednodesPASS; preserve approveddesign95f for later scopedneed without inferring rootcause/cleanup',
 'minimal_after310_refresh':{'pr_and_branch':'samePR311/test/runtime-installed-wheel-import-guard-20261010','starts_from':HEAD,'dependency_barrier':'310actualintegrationfirst; no mergewhile310pending','target':'readactual namedtarget commit/tree AFTER accepted310integration, do not guess futuretuple','operation':'ordinary merge actualtarget INTO existingd75branch, retain d75/1151 history; no replacementbranch/squash/acceptedimplementationduplication','preserve':['production behavior/90readiness20cleanup','installedwheel guard acceptance','original1151eightJSON/81breceipt','currentd75fourJSON/3b4receipt','approvedWindowsV2design95f remainsdeferred'],'required_beforepush':['exactorderedparents/completeuniontree/leafmode preservation review','combined canonicalgenerator/eightoutputs exactroundtrip','scopedmeaningful guard/diagnostic controls and relevantfullconfiguredtests/lint/typechecks; sourcechanges assessedagainstnewtarget','canonicalguidance preserves limits and exactnewreceipt'],'required_beforemerge':['freshfullcurrentunionhostedexpectedjobs/checks includingWindowsintegration','exacthead/source/control/tree/targetreadback; nocurrentd75green relabeling','draftready/review/thread/policy admission underrootexistingauthorization','artifactproducer scope recomputed againstcurrenttarget if claimingretainednative or wheel qualification']},
 'held_limits':['No rootcause/completecleanup/coldrepeatability claim from currentpass.','Older2999cb and original1151 failures remain historical, not repaired by otherbranchpass.','No acceptanceoflater310target or full311 merge now.','Private01f/fafb/frozenv6spec-runner/fullissue/releasegraph remain separateHOLD.','PolicyREST403 disclosed; rules[]/GraphQLnull are observations, not campaigngatewaivers.'],
 'authenticated_raw_bindings':[binding(p)for p in sorted(OWNED.glob('*.json'))],
 'canonical_documentation':{'canonical_file':'docs/skills/repository-operations.md','exact_proposed_delta':binding(patch),'disposition':'PROPOSED to integrationagent; nosource mutation; historical/currentreadbackproposals retained','durable_learning':'declared completeCI and policy surfaces admit actualtuple; dependencytargetrefresh requires samebranch sourceunion andfreshgates; PRpublishjob is not registryupload; greenWindows can deferdesign withoutcauseclaim','evidence':'23exactheadchecks/7declaredworkflowmatrices/complete1409leafcontrol/reviews0threads0/draft/policyresponses/3b4Windowsreadback/95fdesign','stale_ambiguity':'greenrolluporCLEAN permitslaterbase merge; PRpublishjobmeanspublished; noobservedprotection grantsgatewaiver; design-onlyGOrequiresimplementationaftercurrentpass','remaining_uncertainty':'future310integrationtuple/newuniongates/draftadmission/protectionRESTsurface/historicalcause/fullcleanup/private-releaseacceptance','upstream':'none'},
}
p=OUT/'independent-current-full-admission-review.json';p.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(binding(p)))
