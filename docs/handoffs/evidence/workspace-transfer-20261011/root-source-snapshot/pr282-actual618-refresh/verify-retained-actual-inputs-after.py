import hashlib,json,types
from pathlib import Path
out=Path('/workspace/engineering/pr282-actual618-refresh')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
proposal_path=Path('/workspace/actions-cloud/receipts/pr305-runner/immutable-runner-proposal-v5.json');assert sha(proposal_path)=='f915a178adfa23833fe7a2e047e9c0b98f995fdd4b95730e1bb522e5f48fe7ee';proposal=json.loads(proposal_path.read_text())
bindings_path=Path(proposal['helper_bindings']['path']);assert sha(bindings_path)==proposal['helper_bindings']['sha256'];bindings=json.loads(bindings_path.read_text());observed={}
for name,row in bindings.items():
 assert sha(row['original_path'])==row['sha256'] and sha(row['snapshot_path'])==row['sha256'];assert Path(row['snapshot_path']).stat().st_mode&0o777==0o444
 observed[name]={'original':bind(row['original_path']),'snapshot':bind(row['snapshot_path'])}
p=Path(bindings['native_inventory']['snapshot_path']);data=p.read_bytes();m=types.ModuleType('verified_frozen_native_inventory');exec(compile(data,str(p),'exec'),m.__dict__)
native=proposal['native'];inventory_path=Path(native['inventory']['path']);assert sha(inventory_path)==native['inventory']['sha256'];inventory=json.loads(inventory_path.read_text());assert len(inventory)==1192
layout=Path(native['layout']);assert m.packaged_tree_inventory(layout/'dist/action-server')==inventory
manifest_path=Path(native['manifest']['path']);assert sha(manifest_path)==native['manifest']['sha256'];manifest=json.loads(manifest_path.read_text());assert manifest['source_sha']==native['producer']
assert sha(layout/manifest['artifacts']['frozen']['path'])==native['frozen_sha256'];assert sha(Path('/workspace/engineering/pr310/action_server/go-wrapper/assets/assets.zip'))==native['assets_sha256']
retained=json.loads(Path('/workspace/actions-cloud/receipts/pr305-crlf-fixture/retained-native-helper-browser-verification.json').read_text());assert sha(retained['browser'])==retained['browser_sha256']
actual_review_path=Path('/workspace/engineering/pr305-v5-independent-runner-review/independent-actual-v5-review.json');assert sha(actual_review_path)=='1848613d69513e20039cee94efe960a3609fff451a582c7a33552c8fa4df1108';review=json.loads(actual_review_path.read_text());assert sha(review['checkpoint']['path'])==review['checkpoint']['sha256'];assert review['source']['head']=='3ec9d0acbe30ad94d02e4c24fef2587127964495'
(out/'retained-native-helper-browser-and-V5-proof-after.json').write_text(json.dumps({'read_only':True,'no_binary_or_browser_or_actual_execution':True,'all1192_original_inventory_entries_exact':True,'native_producer_original':native['producer'],'original_manifest':bind(manifest_path),'original_inventory':bind(inventory_path),'original_assets_zip':bind(Path('/workspace/engineering/pr310/action_server/go-wrapper/assets/assets.zip')),'original_frozen_executable':bind(layout/manifest['artifacts']['frozen']['path']),'frozen_helper_original_and_snapshot_bindings':observed,'browser':bind(retained['browser']),'historical_V5_checkpoint':bind(review['checkpoint']['path']),'historical_V5_independent_review':bind(actual_review_path),'historical_V5_source':review['source'],'current_source_execution_status':'NOT_RUN; original3ec actual identity preserved, not relabelled to prospective actual776 refresh','immutable_proposal':bind(proposal_path)},indent=2)+'\n')
print('READ_ONLY_ORIGINAL1192_NATIVE_HELPER_BROWSER_V5_RETENTION=PASS')
