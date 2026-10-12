import hashlib,json,os,re,stat
from pathlib import Path
root=Path('/workspace/successor-evidence');out=Path('/workspace/actions-checkpoint/docs/handoffs/evidence/successor-stop-20261012');out.mkdir(parents=True,exist_ok=True)
pruned={'.venv','__pycache__','node_modules','.git','site-packages','pkgs','holotree','hololib','lib','lib64','bin','Scripts','data','datadir','robots','journals','cache'}
extensions={'.py','.sh','.bat','.ps1','.yaml','.yml','.toml','.md','.patch','.json'}
secret=re.compile(rb'github_pat_[A-Za-z0-9_]+|ghp_[A-Za-z0-9]+|AKIA[A-Z0-9]{16}|[?&](?:x-amz-signature|sig|token)=[^\s\"\']+',re.I)
private_name=re.compile(r'(?:decoded.*private|transport|connector-private|artifact-download|toolkit-vars|toolkit-variables|\.private|secret|token|credentials)',re.I)
source_rows=[];excluded=[];json_rows=[]
def h(b):return hashlib.sha256(b).hexdigest()
def private_fields(v):
 if isinstance(v,dict):
  for k,x in v.items():
   if k in {'download_url','file_uri','access_token','refresh_token','clientSecret','client_secret','api_key','password'}:return True
   if k in {'content','stdout','stderr'} and isinstance(x,str) and len(x)>200:return True
   if private_fields(x):return True
 if isinstance(v,list):return any(private_fields(x) for x in v)
 return False
for d,dirs,files in os.walk(root,followlinks=False):
 dirs[:]=[n for n in dirs if n not in pruned and not n.endswith('.dist-info') and not (Path(d)/n).is_symlink()]
 for n in files:
  p=Path(d)/n;relative=p.relative_to(root);st=p.lstat()
  if not stat.S_ISREG(st.st_mode) or p.suffix not in extensions:continue
  if st.st_size>8*1024*1024:
   excluded.append({'path':str(relative),'bytes':st.st_size,'reason':'large local artifact, not exported'});continue
  b=p.read_bytes();reason=None
  if p.suffix=='.json':
   if private_name.search(str(relative)):reason='private transport/environment/operational metadata name'
   else:
    try:v=json.loads(b)
    except Exception:reason='non-JSON local output'
    else:
     if private_fields(v):reason='private transport/credential/raw output fields'
  if secret.search(b):reason='credential or signed-URL pattern; original kept local'
  if reason:
   excluded.append({'path':str(relative),'bytes':len(b),'sha256':h(b),'reason':reason});continue
  category='receipts' if p.suffix=='.json' else 'source-copies'
  dest=out/category/relative;dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists():assert dest.read_bytes()==b,str(relative)
  else:dest.write_bytes(b)
  row={'path':str(dest.relative_to(out)),'original':str(p),'bytes':len(b),'sha256':h(b),'original_mode':oct(stat.S_IMODE(st.st_mode)),'git_export_mode':'100644','kind':category}
  (json_rows if category=='receipts' else source_rows).append(row)
manifest={'source_copies':source_rows,'safe_json':json_rows,'excluded_local_only':excluded,'scope':'Reviewed non-environment source/configuration and safe receipts. Source copies are inert evidence, never portable execution grants. No logs/binaries/archives/databases/environments transferred.'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'source_copies':len(source_rows),'safe_json':len(json_rows),'excluded':len(excluded),'bytes':sum(v['bytes'] for v in source_rows+json_rows)}))
