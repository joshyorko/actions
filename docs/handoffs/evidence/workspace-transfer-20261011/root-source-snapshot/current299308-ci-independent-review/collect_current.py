import json,subprocess,concurrent.futures,datetime,re
from pathlib import Path
D=Path('/workspace/engineering/current299308-ci-independent-review');R='repos/joshyorko/actions'
def api(path):
 p=subprocess.run(['gh','api',path],capture_output=True,text=True)
 if p.returncode: return {'read_error':p.stderr.strip()[:500],'exit':p.returncode}
 return json.loads(p.stdout)
def paged(path,key=None):
 arr=[];pages=[];page=1
 while True:
  x=api(path+('&' if '?' in path else '?')+f'per_page=100&page={page}')
  if isinstance(x,dict) and 'read_error' in x:return {'error':x,'pages':pages}
  y=x[key] if key else x;pages.append({'page':page,'count':len(y),'declared_total':x.get('total_count') if isinstance(x,dict) else None});arr.extend(y)
  if len(y)<100:break
  page+=1;assert page<=20
 return {'pages':pages,'items':arr}
def check(x):return {k:x.get(k) for k in ['id','name','head_sha','status','conclusion','started_at','completed_at','details_url','html_url','check_suite']}
def run(x):return {k:x.get(k) for k in ['id','name','path','head_branch','head_sha','status','conclusion','event','run_number','run_attempt','created_at','updated_at','html_url','check_suite_id']}
def job(x):return {k:x.get(k) for k in ['id','run_id','run_attempt','name','status','conclusion','head_sha','started_at','completed_at','html_url','runner_name','runner_group_name','steps']}
def one(n):
 p=json.loads((D/f'pr{n}-initial-PR.json').read_text());head=p['head']['sha'];merge=p['merge_commit_sha'];fields={}
 calls={'head_checks':(f'{R}/commits/{head}/check-runs?filter=all','check_runs'),'merge_checks':(f'{R}/commits/{merge}/check-runs?filter=all','check_runs'),'statuses':(f'{R}/commits/{head}/statuses',None),'reviews':(f'{R}/pulls/{n}/reviews',None),'runs':(f'{R}/actions/runs?head_sha={head}','workflow_runs')}
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as e:
  fs={e.submit(paged,*spec):key for key,spec in calls.items()}
  for f in concurrent.futures.as_completed(fs):fields[fs[f]]=f.result()
 for key in ['head_checks','merge_checks']:fields[key]['items']=[check(x) for x in fields[key].get('items',[])]
 fields['statuses']['items']=[{k:x.get(k) for k in ['id','state','context','created_at','updated_at','target_url']} for x in fields['statuses'].get('items',[])]
 fields['reviews']['items']=[{k:x.get(k) for k in ['id','state','commit_id','submitted_at','author_association']} for x in fields['reviews'].get('items',[])]
 fullruns=fields['runs'].get('items',[]);fields['runs']['items']=[run(x) for x in fullruns]
 jobs={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as e:
  fs={e.submit(paged,f'{R}/actions/runs/{x["id"]}/jobs?filter=all','jobs'):x['id'] for x in fullruns}
  for f in concurrent.futures.as_completed(fs):
   val=f.result();val['items']=[job(x) for x in val.get('items',[])];jobs[str(fs[f])]=val
 fields['run_jobs']=jobs
 for label,sha in [('head_git',head),('prospective_merge_git',merge)]:
  x=api(f'{R}/git/commits/{sha}');fields[label]={k:x.get(k) for k in ['sha','tree','parents']} if 'read_error' not in x else x
 fields['PR']=p;fields['observedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();out=D/f'pr{n}-complete-current-CI-inventory.json';out.write_text(json.dumps(fields,indent=2)+'\n')
 print(json.dumps({'PR':n,'head_checks':len(fields['head_checks']['items']),'merge_checks':len(fields['merge_checks']['items']),'reviews':len(fields['reviews']['items']),'statuses':len(fields['statuses']['items']),'runs':[(x['id'],x['name'],x['status'],x['conclusion']) for x in fields['runs']['items']],'failed_or_pending_jobs':[(runid,x['id'],x['name'],x['status'],x['conclusion']) for runid,v in jobs.items() for x in v['items'] if x['conclusion'] not in ['success','skipped']],'out':str(out)}),flush=True)
for n in [299,308]:one(n)
