from pathlib import Path
import json,subprocess,fnmatch,itertools,hashlib,yaml,re
D=Path('/workspace/engineering/current299308-ci-independent-review');base='integration/community-release-20261008'
def api(path):return json.loads(subprocess.check_output(['gh','api',path]))
def match(path,patterns):
 selected=False
 for p in patterns:
  neg=p.startswith('!');pat=p[1:] if neg else p
  if fnmatch.fnmatchcase(path,pat):selected=not neg
 return selected
for num in [299,308]:
 v=json.loads((D/f'pr{num}-complete-current-CI-inventory.json').read_text());head=v['PR']['head']['sha'];root=Path('/workspace/engineering/pr'+str(num));changed=[];pages=[];page=1
 while True:
  x=api(f'repos/joshyorko/actions/pulls/{num}/files?per_page=100&page={page}');changed.extend(e['filename'] for e in x);pages.append({'page':page,'count':len(x)})
  if len(x)<100:break
  page+=1
 observed={r['path']:r for r in v['runs']['items']};predicted={};ignored=[]
 for file in sorted((root/'.github/workflows').glob('*.yml')):
  y=yaml.safe_load(file.read_text());rel=file.relative_to(root).as_posix();ev=y.get('on',{});ev={e:None for e in ev} if isinstance(ev,list) else {ev:None} if isinstance(ev,str) else ev
  if 'pull_request' not in ev:ignored.append({'path':rel,'reason':'no pull_request event'});continue
  cond=ev['pull_request'] or {}
  if 'branches' in cond and not match(base,cond['branches']):ignored.append({'path':rel,'reason':'branch filter excludes named base'});continue
  if 'branches-ignore' in cond and match(base,cond['branches-ignore']):ignored.append({'path':rel,'reason':'branch-ignore excludes named base'});continue
  if 'paths' in cond and not any(match(p,cond['paths']) for p in changed):ignored.append({'path':rel,'reason':'paths filters exclude complete current diff'});continue
  if 'paths-ignore' in cond and all(match(p,cond['paths-ignore']) for p in changed):ignored.append({'path':rel,'reason':'all current changed paths ignored'});continue
  count=0;jobs={}
  for key,j in y['jobs'].items():
   mat=j.get('strategy',{}).get('matrix',{});axes={k:vv for k,vv in mat.items() if k not in ['include','exclude']};configs=[dict(zip(axes,values)) for values in itertools.product(*axes.values())] if axes else [{}]
   configs=[c for c in configs if not any(all(c.get(k)==z for k,z in e.items()) for e in mat.get('exclude',[]))]
   if not axes and mat.get('include'):configs=list(mat['include'])
   # All existing include entries annotate corresponding Cartesian dimensions here.
   for inc in mat.get('include',[]) if axes else []:
    if not any(all(c.get(k)==z for k,z in inc.items() if k in axes) for c in configs):configs.append(inc)
   jobs[key]={'expected_job_instances':len(configs),'checkout_steps':[{ 'uses':s['uses'],'ref':s.get('with',{}).get('ref','DEFAULT_PR_MERGE_CHECKOUT')} for s in j.get('steps',[]) if 'uses' in s and s['uses'].startswith('actions/checkout@')],'if':j.get('if'),'publish_step_conditions':[{ 'name':s.get('name'),'if':s.get('if')} for s in j.get('steps',[]) if s.get('name') in ['Check Runtime publish credential','Publish verified artifacts']]};count+=len(configs)
  predicted[rel]={'name':y['name'],'expected_jobs':count,'jobs':jobs,'source_file_sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
 assert set(predicted)==set(observed),(num,set(predicted)-set(observed),set(observed)-set(predicted))
 assert sum(e['expected_jobs'] for e in predicted.values())==19
 actual_ids=set();suiteids=set()
 for rel,p in predicted.items():
  run=observed[rel];assert run['event']=='pull_request' and run['head_sha']==head;val=v['run_jobs'][str(run['id'])];assert len(val['items'])==p['expected_jobs'];p['actual_run_id']=run['id'];p['job_ids']=[j['id'] for j in val['items']];suiteids.add(run['check_suite_id']);actual_ids.update(p['job_ids'])
  assert all(j['head_sha']==head for j in val['items'])
 checks=v['head_checks']['items'];assert len(checks)==19 and {c['id'] for c in checks}==actual_ids;assert all(c['head_sha']==head and c['check_suite']['id'] in suiteids for c in checks)
 merge=v['prospective_merge_git'];assert [p['sha'] for p in merge['parents']]==['774438b130afb2ead9bbc1c1b76cb6f91e72150a',head] and merge['tree']['sha']==v['head_git']['tree']['sha']
 out={'PR':num,'head':head,'prospective_merge':merge['sha'],'tree':merge['tree']['sha'],'ordered_merge_parents':[p['sha'] for p in merge['parents']],'complete_PRfiles_pages':pages,'changed_paths':changed,'predicted_six_workflows_expected19jobs':predicted,'all19complete_check_runs_equal_exact_actual_current_jobs':True,'all_runs_and_jobs_head_sha_exact_current':True,'ignored_workflows':ignored,'checkout_boundary':'Default PRmerge checkout configured for required build/source jobs; current merge ref/tree/parents authenticated. No raw job logs/artifacts downloaded to independently measure actual checkout; API job/head identity+source configuration establishes control tuple only.','publication_limit':'publish job is inventory/Twine/dryrun gate; credential/upload step is push-only, does not publish on PR.'};p=D/f'pr{num}-exact-expected-workflow-and-check-bindings.json';p.write_text(json.dumps(out,indent=2)+'\n');print(num,'EXPECTED6/19_AND_COMPLETE_CURRENT_CHECK_MATCH_PASS',hashlib.sha256(p.read_bytes()).hexdigest())
