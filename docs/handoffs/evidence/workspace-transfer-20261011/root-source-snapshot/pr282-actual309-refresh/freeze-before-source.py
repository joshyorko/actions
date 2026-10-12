from pathlib import Path
import hashlib,json,os,stat,subprocess
R=Path('/workspace/engineering/pr282');D=Path('/workspace/engineering/pr282-actual309-refresh');D.chmod(0o700);S='e736f846557ed1d603348e97c5eb80060d62e3e2';TARGET='a0d258a16095b95b1bf9000cb1201cddfaff4779'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def inv(ref):
 out={}
 for rec in git('ls-tree','-rz',ref).split(b'\0'):
  if rec:
   a,p=rec.split(b'\t',1);out[p.decode()]=a.decode().split()
 return out
assert git('rev-parse','HEAD').decode().strip()==S and git('branch','--show-current').decode().strip()=='feat/canvas-template-20261010' and not git('status','--porcelain')
owner=Path('/workspace/engineering/pr282-actual618-refresh/frozen-source-receipt.json');assert sha(owner)=='78f41d01e5a1bdfe4df059f7cc797c7a8a80a840b9d12b8d95fad6a98816db71';o=json.loads(owner.read_text());assert o['head']==S
source=inv(S);assert len(source)==1433
fs=[]
for p,row in source.items():
 mode,kind,blob=row;f=R/p;body=os.readlink(f).encode() if mode=='120000' else f.read_bytes();assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==blob
 if mode!='120000':assert bool(f.stat().st_mode&0o111)==(mode=='100755')
 fs.append({'path':p,'mode':mode,'type':kind,'blob':blob,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'current_FS_mode':oct(stat.S_IMODE(f.lstat().st_mode))})
# Preserve bound immutable receipt graphs, with independently observed CURRENT modes; no invented historical baselines.
refs={};historical_git_bindings=[];historical_UNAVAILABLE=[];expanded=set();depth_limit=6
queue=[(o,0)]
def scan(v,depth):
 if isinstance(v,dict):
  if {'path','bytes','sha256'}<=set(v) and Path(v['path']).is_absolute():
   p=Path(v['path'])
   if not p.exists():
    assert str(p).startswith('/workspace/work/'),str(p)
    historical_UNAVAILABLE.append({'original_recorded_binding':v,'scope':'Referenced historical oldworkspace original UNAVAILABLE; parent immutableJSON binding retained, no reconstructed bytes/positive admission'})
    return
   q=bind(p)
   if q['bytes']!=v['bytes'] or q['sha256']!=v['sha256']:
    rel=p.relative_to('/workspace/engineering/pr305').as_posix();body=subprocess.check_output(['git','-C','/workspace/engineering/pr305','show','3ec9d0acbe30ad94d02e4c24fef2587127964495:'+rel]);assert len(body)==v['bytes'] and hashlib.sha256(body).hexdigest()==v['sha256'],str(p)
    historical_git_bindings.append({'original_recorded_binding':v,'immutable_source':'3ec9d0acbe30ad94d02e4c24fef2587127964495','original_body_bytes':len(body),'original_body_sha256':hashlib.sha256(body).hexdigest(),'current_mutable_path_binding':q,'scope':'Historical immutableGitbody retained; currentworkingguide advanced legitimately and is not oldbody baseline'})
   refs[str(p)]=q
   if p.suffix=='.json' and p.stat().st_size<1000000 and str(p) not in expanded and depth<depth_limit:
    expanded.add(str(p));queue.append((json.loads(p.read_text()),depth+1))
  for vv in v.values():scan(vv,depth)
 elif isinstance(v,list):
  for vv in v:scan(vv,depth)
while queue:
 v,depth=queue.pop(0);scan(v,depth)
refs[str(owner)]=bind(owner)
prep=Path('/workspace/engineering/pr282-actual618-refresh/own-Bootstrap-reuse-inputs-and-origins.json');p=json.loads(prep.read_text());prepared_record=p;assert len(p['inputs_exact_prepared_git_bytes_sha256'])==30 and len(p['own5actual_prefix_and_source_origin_assertions'])==5
for name,h in p['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/name)==h
for pkg,v in p['own5venvs_current_config_and_python'].items():assert sha(R/pkg/'.venv/pyvenv.cfg')==v['config_sha256'] and str((R/pkg/'.venv/bin/python').resolve())==v['python_resolved']
for row in p['own5actual_prefix_and_source_origin_assertions']:assert Path(row['origin']).is_file() and Path(row['origin']).is_relative_to(R) and Path(row['prefix']).resolve().is_relative_to(R)
rcc=R/'action_server/src/actions/server/bin/rcc-18.19.3';assert sha(rcc)=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428' and stat.S_IMODE(rcc.stat().st_mode)==0o711
# Record historical artifacts exactly, no execution; use direct pure byte/mode reads.
native=json.loads(Path(o['retained_owned_artifacts']['original1192_native_helper0444_browser_V5']['after']['path']).read_text());proposal=json.loads(Path(native['immutable_proposal']['path']).read_text());layout=Path(proposal['native']['layout'])/'dist/action-server';inventory=json.loads(Path(native['original_inventory']['path']).read_text());assert len(inventory)==1192 and {p.relative_to(layout).as_posix() for p in layout.rglob('*')}=={v['path'] for v in inventory}
for row in inventory:
 p=layout/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert sha(p)==row['content_sha256'] and not p.is_symlink()
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert p.is_symlink() and os.readlink(p)==row['link_target']
for group in native['frozen_helper_original_and_snapshot_bindings'].values():
 for key in ('original','snapshot'):
  v=group[key];assert bind(v['path'])['sha256']==v['sha256'];refs[v['path']]=bind(v['path'])
 assert stat.S_IMODE(Path(group['snapshot']['path']).stat().st_mode)==0o444
v5=json.loads(Path(native['historical_V5_checkpoint']['path']).read_text());assert len(v5['raw_receipts_private_do_not_commit'])==18 and len(v5['frozen_posthashes'])==50
for v in v5['raw_receipts_private_do_not_commit']:assert bind(v['path'])['sha256']==v['sha256'];refs[v['path']]=bind(v['path'])
for v in v5['frozen_posthashes']:
 if sha(v['path'])!=v['sha256']:
  rel=Path(v['path']).relative_to('/workspace/engineering/pr305').as_posix();body=subprocess.check_output(['git','-C','/workspace/engineering/pr305','show','3ec9d0acbe30ad94d02e4c24fef2587127964495:'+rel]);assert hashlib.sha256(body).hexdigest()==v['sha256']
for key in ['original_assets_zip','original_frozen_executable','browser','historical_V5_checkpoint','historical_V5_independent_review','immutable_proposal']:
 v=native[key];assert bind(v['path'])['sha256']==v['sha256'];refs[v['path']]=bind(v['path'])
result={'status':'FROZEN_BEFORE_SOURCE_NO_GATE','head':S,'tree':git('rev-parse',S+'^{tree}').decode().strip(),'branch':'feat/canvas-template-20261010','target':TARGET,'target_tree':git('rev-parse',TARGET+'^{tree}').decode().strip(),'source_full_count':1433,'source_typed':source,'source_FS_rows':fs,'historical_owner':bind(owner),'all_bound_refs_current_bytes_modes':list(refs.values()),'historical_UNAVAILABLE_original_bindings':historical_UNAVAILABLE,'historical_mutable_source_bindings_retained_in_immutable_Git':historical_git_bindings,'binding_graph_depth_limit':depth_limit,'scope':'All discovered immutable receipt graph bindings preserved through six nestedlevels; source/native/artifact bodies independently verified, no reexecution or qualificationcarry','prepared30_five_recorded_configs_origins':bind(prep),'prepared_inputs':prepared_record,'owned_RCC':bind(rcc),'primary_managed_RCC':bind('/workspace/actions-cloud/bin/rcc'),'original_native1192_mode_bytes':True,'original_helpers0444_browser_Node_raw18_frozen50_retained':True,'original_historical_producer_scope':o['current_producer'],'dispatch_count_correction':'Authoritative1433leaves/275production+5selected;259oldmatch9changed7added vsold268. Parent dispatch274+5 was copied fromanotherbranch, corrected before anymerge.','actual_gates':'NOT_RUN_BY_THIS_WRITER; LIGHT awaits explicit rootslotrelease/full/browser/native/provider remainHOLD','Upstream_disposition':'none'}
p=D/'FROZEN-before-source-original-e736-bindings.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'source_count':1433,'historical_refs':len(refs),'producer':275}))
