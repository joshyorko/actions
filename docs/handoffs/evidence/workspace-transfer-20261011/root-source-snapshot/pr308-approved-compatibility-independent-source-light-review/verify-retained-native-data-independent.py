import hashlib,json,stat
from pathlib import Path
B=Path('/workspace/engineering/pr308-rcc-compatibility-source');O=Path('/workspace/engineering/pr308-approved-compatibility-independent-source-light-review')
def H(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def verify(v):p=Path(v['path']);assert p.stat().st_size==v['bytes'] and H(p)==v['sha256']
a=json.loads((B/'after-source-retained-native-helper-browser-and-V5-proof.json').read_bytes());proposal=json.loads(Path(a['immutable_proposal']['path']).read_bytes());root=Path(proposal['native']['layout'])/'dist/action-server'
for key in ['original_manifest','original_inventory','original_assets_zip','original_frozen_executable','browser','historical_V5_checkpoint','historical_V5_independent_review','immutable_proposal']:verify(a[key])
for row in a['frozen_helper_original_and_snapshot_bindings'].values():
 for v in row.values():verify(v)
 assert Path(row['snapshot']['path']).stat().st_mode&0o777==0o444
expected=json.loads(Path(a['original_inventory']['path']).read_bytes());actual=[]
for p in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()):
 mode=stat.S_IMODE(p.lstat().st_mode)
 if p.is_symlink():kind='symlink';target=p.readlink().as_posix()
 elif p.is_dir():kind='directory';target=None
 elif p.is_file():kind='file';target=None
 else:raise AssertionError('unexpected typed entry')
 actual.append({'path':p.relative_to(root).as_posix(),'kind':kind,'mode':mode,'link_target':target,'content_sha256':H(p) if p.is_file() else None})
assert len(actual)==1192 and actual==expected
out=O/'safe-independent-original1192-native-helper-browser-retention.json';d={'status':'PASS_DATA_RETENTION_ONLY','all1192_original_typed_mode_symlink_content_records_exact':True,'helper_original_and0444_snapshot_pairs_exact':True,'original_manifest_inventory_assets_executable_browser_hashes_exact':True,'historical_V5_source':a['historical_V5_source'],'current_source_native_qualification':'UNQUALIFIED; no native/browser/helper payload invocation or proof relabel','before_after_retention_proofs_equal':(B/'before-source-retained-native-helper-browser-and-V5-proof.json').read_bytes()==(B/'after-source-retained-native-helper-browser-and-V5-proof.json').read_bytes()}
with out.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
out.chmod(0o600);print(json.dumps({'path':str(out),'bytes':out.stat().st_size,'sha256':H(out)}))
