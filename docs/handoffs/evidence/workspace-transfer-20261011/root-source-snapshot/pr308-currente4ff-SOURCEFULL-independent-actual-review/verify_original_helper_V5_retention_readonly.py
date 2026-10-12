import pathlib,json,hashlib,stat
D=pathlib.Path('/workspace/engineering/pr308-currente4ff-SOURCEFULL-independent-actual-review')
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=pathlib.Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def check(r):
 p=pathlib.Path(r['path']);assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
 if 'mode' in r:assert oct(stat.S_IMODE(p.stat().st_mode))==r['mode']
 return bind(p)
config=pathlib.Path('/workspace/engineering/rcc-compatibility-actual-runner-readonly-preparation/FROZEN-control3-current-b614-actual-config-v2.json');cfg=json.loads(config.read_bytes());row=next(r for r in cfg['bindings'] if pathlib.Path(r['path']).name=='after-source-retained-native-helper-browser-and-V5-proof.json');bound=check(row);x=json.loads(pathlib.Path(row['path']).read_bytes());refs=[]
for k in ('original_manifest','original_inventory','original_assets_zip','original_frozen_executable','browser','historical_V5_checkpoint','historical_V5_independent_review','immutable_proposal'):refs.append(check(x[k]))
helpers={}
for k,v in x['frozen_helper_original_and_snapshot_bindings'].items():
 helpers[k]={a:check(v[a]) for a in ('original','snapshot')};assert helpers[k]['original']['sha256']==helpers[k]['snapshot']['sha256'];assert helpers[k]['original']['mode']==helpers[k]['snapshot']['mode']=='0o444'
proposal=json.loads(pathlib.Path(x['immutable_proposal']['path']).read_bytes());runner=pathlib.Path(proposal['runner']['path']);assert sha(runner)=='09cdc6b19f5d3d9cc94fadca23373108868521e0378d33960146b1a8522e88ad';runnerbinding=bind(runner)
cp=json.loads(pathlib.Path(x['historical_V5_checkpoint']['path']).read_bytes());assert len(cp['raw_receipts_private_do_not_commit'])==18 and len(cp['frozen_posthashes'])==50;raw=[check(r) for r in cp['raw_receipts_private_do_not_commit']];frozen=[]
for r in cp['frozen_posthashes']:
 assert r['matches'] is True and r['sha256']==r['expected_sha256'];p=pathlib.Path(r['path']);assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes'];frozen.append(bind(p))
proof={'schema':1,'status':'PASS_ORIGINAL_HELPER_BROWSER_NATIVE_V5_RETENTION_READONLY','bound_original_retention_receipt':bound,'original8_artifact_browser_and_V5_receipt_bindings':refs,'all4_original_and_snapshot_helper_pairs':helpers,'historical_V5_runner':runnerbinding,'historical_raw18_original_bytes_SHA':raw,'historical_frozen50_original_bytes_SHA':frozen,'modes':'original/snapshot helpers0444 exactly; other original retained rows record no original modes, current observed modes recorded without inventing historical comparisons','no_native_or_browser_or_V5_execution':True,'historical_V5_scope':'original3ec source/currentproof not retargeted to e4ff, no broader acceptance upgrade','upstream_disposition':'none'}
p=D/'independent-original-native-helper-browser-V5-retention-supplement.json';assert not p.exists();p.write_text(json.dumps(proof,indent=2)+'\n');p.chmod(0o600);print(json.dumps(bind(p)))
