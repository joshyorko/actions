from pathlib import Path
import hashlib,json,os,stat,subprocess
R=Path('/workspace/engineering/pr282');D=Path('/workspace/engineering/pr282-actual309-refresh');HEAD='c35ee2e279eaefe55b16aecdb80da04c590aff7c'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
before=json.loads((D/'FROZEN-before-source-original-e736-bindings.json').read_text());union=json.loads((D/'FROZEN-staged-automatic-a0d-union-proof.json').read_text());terminal=json.loads((D/'one-root-released-LIGHT-final-terminal.json').read_text());assert terminal['status']=='ALL_EIGHT_LIGHT_SCOPES_PASS' and len(terminal['records'])==8
assert git('rev-parse','HEAD').decode().strip()==HEAD and git('rev-parse','HEAD^{tree}').decode().strip()==union['expected_tree'] and not git('status','--porcelain')
fs=[]
for name,row in union['typed_union'].items():
 mode,kind,blob=row;p=R/name;body=os.readlink(p).encode() if mode=='120000' else p.read_bytes();assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==blob
 if mode!='120000':assert bool(p.stat().st_mode&0o111)==(mode=='100755')
 fs.append({'path':name,'mode':mode,'type':kind,'blob':blob,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'current_FS_mode':oct(stat.S_IMODE(p.lstat().st_mode))})
assert len(fs)==1435
fsmap={v['path']:v for v in fs}
for v in before['source_FS_rows']:assert fsmap[v['path']]['current_FS_mode']==v['current_FS_mode']
for v in before['all_bound_refs_current_bytes_modes']:assert bind(v['path'])==v
owner=json.loads(Path(before['historical_owner']['path']).read_text());native=json.loads(Path(owner['retained_owned_artifacts']['original1192_native_helper0444_browser_V5']['after']['path']).read_text());proposal=json.loads(Path(native['immutable_proposal']['path']).read_text());layout=Path(proposal['native']['layout'])/'dist/action-server';inventory=json.loads(Path(native['original_inventory']['path']).read_text());assert len(inventory)==1192 and {p.relative_to(layout).as_posix() for p in layout.rglob('*')}=={v['path'] for v in inventory}
for row in inventory:
 p=layout/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert sha(p)==row['content_sha256'] and not p.is_symlink()
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert p.is_symlink() and os.readlink(p)==row['link_target']
for group in native['frozen_helper_original_and_snapshot_bindings'].values():
 for key in ('original','snapshot'):v=group[key];assert sha(v['path'])==v['sha256']
 assert stat.S_IMODE(Path(group['snapshot']['path']).stat().st_mode)==0o444
v5=json.loads(Path(native['historical_V5_checkpoint']['path']).read_text());assert len(v5['raw_receipts_private_do_not_commit'])==18 and len(v5['frozen_posthashes'])==50
for v in v5['raw_receipts_private_do_not_commit']:assert sha(v['path'])==v['sha256']
for v in v5['frozen_posthashes']:
 if sha(v['path'])!=v['sha256']:
  rel=Path(v['path']).relative_to('/workspace/engineering/pr305').as_posix();body=subprocess.check_output(['git','-C','/workspace/engineering/pr305','show','3ec9d0acbe30ad94d02e4c24fef2587127964495:'+rel]);assert hashlib.sha256(body).hexdigest()==v['sha256']
for key in ['original_assets_zip','original_frozen_executable','browser','historical_V5_checkpoint','historical_V5_independent_review','immutable_proposal']:v=native[key];assert sha(v['path'])==v['sha256']
prepared=json.loads((D/'own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert prepared['measured_inputs']==30 and len(prepared['own5actual_prefix_and_source_origin_assertions'])==5
for name,h in prepared['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/name)==h
for name,row in prepared['own5venvs_current_config_and_python'].items():assert sha(R/name/'.venv/pyvenv.cfg')==row['config_sha256']
result={'status':'PASS_POST_ONE_LIGHT_SOURCE_ORIGINAL_BYTES_AND_MODES','head':HEAD,'tree':union['expected_tree'],'source_count':1435,'all_current_FS_bodies_and_Git_execbits_exact':True,'all1433_old_FS_modes_unchanged':True,'source_FS_rows':fs,'all441_current_bound_reference_bytes_modes_exact':True,'historical_UNAVAILABLE10_bindings_retained_no_reconstruction':before['historical_UNAVAILABLE_original_bindings'],'original_native1192_full_member_set_bodies_modes_links_exact':True,'original_helpers0444_browser_Node_raw18_frozen50_exact_or_authoritative_original_Git':True,'prepared30_and_five_actual_prefix_origin_verified':True,'historical_producer275_plus_five_native_UNQUALIFIED':True,'no_full_source_or_actual_consumer_native_browser_provider_execution':True,'gateway_cleanup_scope':'Source gateway success is not a universal descendant/reaping/cleanup acceptance claim','Upstream_disposition':'none'}
p=D/'FROZEN-post-LIGHT-complete-source-original-bytes-modes.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'source_count':1435,'original_references':441,'native_members':1192}))
