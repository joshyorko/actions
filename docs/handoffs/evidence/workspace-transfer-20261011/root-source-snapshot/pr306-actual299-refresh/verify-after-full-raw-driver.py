import hashlib,json,pathlib,subprocess
root=pathlib.Path('/workspace/engineering/pr305');out=pathlib.Path('/workspace/engineering/pr306-actual299-refresh');base=pathlib.Path('/workspace/actions-cloud/receipts/pr305-runner')
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
checkpoint=base/'actual-v5-passed-checkpoint-corrected.json';assert sha(checkpoint)=='28b2af71d1ac7b5dd0bbd7bf7518845a2c3d208c6700fd102914cffaf449dca3';d=json.loads(checkpoint.read_text());p=json.loads((base/'immutable-runner-proposal-v5.json').read_text());raw=d['raw_receipts_private_do_not_commit'];assert len(raw)==18
for row in raw:assert pathlib.Path(row['path']).stat().st_size==row['bytes'] and sha(row['path'])==row['sha256']
checks=[]
for row in d['frozen_posthashes']:
 path=pathlib.Path(row['path']);observed=sha(path);expected=row['sha256'];assert expected==row['expected_sha256'];category='retained_external_bytes'
 if observed!=expected:
  relative=path.relative_to(root).as_posix();blob=subprocess.check_output(['git','-C',str(root),'show','3ec9d0acbe30ad94d02e4c24fef2587127964495:'+relative]);assert hashlib.sha256(blob).hexdigest()==expected;category='historical305Gitbody_retained_original3ec_current_union_changed'
 checks.append({'expected_sha256':expected,'observed_sha256':observed,'category':category})
assert len(checks)==50
lock=p['driver']['frontend_lock'];assert sha(lock['path'])==lock['sha256'];assert sha(p['driver']['browser'])==p['driver']['browser_sha256'];assert pathlib.Path(p['driver']['prepared_node_modules']).is_dir()
node_sha=sha(p['driver']['node']);r={'status':'READ_ONLY_ORIGINAL_V5_RAW_AND_DRIVER_RETAINED','raw18_original_hash_sizes_exact':True,'frozen50_counts':{category:sum(x['category']==category for x in checks) for category in set(x['category'] for x in checks)},'frozen50_hash_checks':checks,'frontend_lock_sha256':lock['sha256'],'browser_sha256':p['driver']['browser_sha256'],'prepared_node_binary_sha256':node_sha,'prepared_node_modules_directory_retained':True,'not_executed':'NoNode/browser/native/product launch; metadata/files only. V5 original3ec retained, no new sourceactual admission.'}
dest=out/'after-full-raw18-frozen50-Node-frontend-retained.json';dest.write_text(json.dumps(r,indent=2)+'\n');dest.chmod(0o444);print(json.dumps({'raw18_original_hashes_exact':True,'frozen50_counts':r['frozen50_counts'],'node_frontend_browser_hashes_measured':True,'proof_sha256':sha(dest)}))
