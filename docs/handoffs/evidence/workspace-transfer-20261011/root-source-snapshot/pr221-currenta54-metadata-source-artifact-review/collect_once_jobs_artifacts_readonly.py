import concurrent.futures,json,os,pathlib,subprocess
D=pathlib.Path(__file__).parent/'private-metadata';os.umask(0o077);runs=[r for p in json.loads((D/'workflow-runs-v2.decoded-pages.json').read_bytes()) for r in p['workflow_runs']];queries=[]
for r in runs:
 queries += [(f"jobs-run-{r['id']}",f"repos/joshyorko/actions/actions/runs/{r['id']}/jobs?filter=latest&per_page=100"),(f"artifacts-run-{r['id']}",f"repos/joshyorko/actions/actions/runs/{r['id']}/artifacts?per_page=100")]
def one(q):
 n,e=q;p=D/(n+'.original.json');assert not p.exists();cp=subprocess.run(['gh','api',e,'--paginate'],capture_output=True,timeout=45);p.write_bytes(cp.stdout);(D/(n+'.private.stderr')).write_bytes(cp.stderr);assert cp.returncode==0,(n,cp.returncode);s=cp.stdout.decode();pages=[];dec=json.JSONDecoder()
 while s.strip():s=s.lstrip();v,k=dec.raw_decode(s);pages.append(v);s=s[k:]
 (D/(n+'.decoded-pages.json')).write_text(json.dumps(pages,indent=2)+'\n');return {'name':n,'pages':len(pages),'bytes':len(cp.stdout)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results=list(ex.map(one,queries))
print(json.dumps({'requests':len(results),'all_returncode_zero':True,'pages':sum(r['pages'] for r in results)}))
