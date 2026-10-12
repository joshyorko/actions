import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

OUT = Path('/workspace/engineering/pr282-actual618-independent-source-review')
B = Path('/workspace/engineering/pr282-actual618-refresh')
cache = {}
def digest(p):
    p = Path(p); s = p.stat(); key = (str(p),s.st_size,s.st_mtime_ns)
    if key not in cache:
        h = hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
        cache[key] = h.hexdigest()
    return cache[key]
def load(p): return json.loads(Path(p).read_bytes())
def check(row):
    assert digest(row['path']) == row['sha256']
    if 'bytes' in row: assert Path(row['path']).stat().st_size == row['bytes']

retention = load(B/'retained-native-helper-browser-and-V5-proof.json')
for key in ['original_manifest','original_inventory','original_assets_zip','original_frozen_executable','browser','historical_V5_checkpoint','historical_V5_independent_review','immutable_proposal']: check(retention[key])
proposal = load(retention['immutable_proposal']['path'])
check(proposal['helper_bindings'])
helpers = load(proposal['helper_bindings']['path'])
assert len(helpers) == 4
for row in helpers.values():
    assert digest(row['original_path']) == digest(row['snapshot_path']) == row['sha256']
    assert stat.S_IMODE(Path(row['snapshot_path']).stat().st_mode) == 0o444
native = proposal['native']; check(native['inventory']);check(native['manifest'])
inventory = load(native['inventory']['path']); root = Path(native['layout'])/'dist/action-server'
assert len(inventory) == 1192
actual = []
for path in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()):
    s = path.lstat()
    if path.is_symlink(): kind='symlink'; target=path.readlink().as_posix()
    elif path.is_dir(): kind='directory';target=None
    elif path.is_file(): kind='file';target=None
    else: raise AssertionError('unexpected inventory kind')
    actual.append({'path':path.relative_to(root).as_posix(),'kind':kind,'mode':stat.S_IMODE(s.st_mode),'link_target':target,'content_sha256':digest(path) if path.is_file() else None})
assert actual == inventory
manifest = load(native['manifest']['path'])
assert manifest['source_sha'] == native['producer'] == '92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
assert digest(Path(native['layout'])/manifest['artifacts']['frozen']['path']) == native['frozen_sha256']
assert digest('/workspace/engineering/pr310/action_server/go-wrapper/assets/assets.zip') == native['assets_sha256']
checkpoint = load(retention['historical_V5_checkpoint']['path'])
raw = checkpoint['raw_receipts_private_do_not_commit']; frozen = checkpoint['frozen_posthashes']
assert len(raw) == 18 and len(frozen) == 50
for row in raw: check(row)
historical_git_bindings = 0; current = 0
for row in frozen:
    assert row['sha256'] == row['expected_sha256']
    if digest(row['path']) == row['sha256']:
        assert Path(row['path']).stat().st_size == row['bytes']; current += 1
    else:
        relative = Path(row['path']).relative_to('/workspace/engineering/pr305').as_posix()
        body = subprocess.check_output(['git','--no-optional-locks','-C','/workspace/engineering/pr305','show','3ec9d0acbe30ad94d02e4c24fef2587127964495:'+relative])
        assert len(body) == row['bytes'] and hashlib.sha256(body).hexdigest() == row['sha256']; historical_git_bindings += 1
driver = proposal['driver'];check(driver['frontend_lock']);check(driver['accepted_selection_receipt'])
assert digest(driver['browser']) == driver['browser_sha256']
recorded_driver = load(B/'raw18-frozen50-Node-frontend-retained-after.json')
assert digest(driver['node']) == recorded_driver['prepared_node_binary_sha256']
assert Path(driver['prepared_node_modules']).is_dir()
assert load(B/'raw18-frozen50-Node-frontend-retained-during-source.json') == recorded_driver
assert retention == load(B/'retained-native-helper-browser-and-V5-proof-after.json')
assert retention == load(B/'retained-native-helper-browser-and-V5-proof-root-released-pre.json')
assert recorded_driver == load(B/'raw18-frozen50-Node-frontend-retained-root-released-pre.json')
review = load(retention['historical_V5_independent_review']['path'])
assert review['source']['head'] == '3ec9d0acbe30ad94d02e4c24fef2587127964495'
assert review['checkpoint']['sha256'] == retention['historical_V5_checkpoint']['sha256']
proof = {'status':'PASS_READ_ONLY_RETAINED_ORIGINAL_BYTES_AND_MODES','native_producer':native['producer'],'native_tree':native['tree'],'native_entries':len(inventory),'all_original_inventory_kinds_modes_targets_digests_exact':True,'manifest_assets_frozen_hashes_exact':True,'four_helpers_original_snapshot_exact':True,'snapshot_mode':'0444','browser_Node_frontend_lock_selection_hashes_exact':True,'raw_private_receipts':len(raw),'frozen_refs':len(frozen),'current_external_exact':current,'historical_source_Git_binding_exact':historical_git_bindings,'all_before_root_release_after_proofs_identical':True,'original_actual_source':'3ec9d0acbe30ad94d02e4c24fef2587127964495','limits':['No native artifact or process launch; no publication/download/build','No current275 producer equivalence to historical268','No upgrade of original browser_version38/39 cause/values or two adopted-zombie observations','Captured DEBUG executable selection is not live PID identity','No full Core wheel/cold-registry or private/Workspace/ChatGPT/release qualification'],'upstream_disposition':'none'}
dest = OUT/'independent-original-artifact-retention-proof.json'; assert not dest.exists(); dest.write_text(json.dumps(proof,indent=2)+'\n');dest.chmod(0o444)
print(json.dumps({'status':proof['status'],'bytes':dest.stat().st_size,'sha256':digest(dest),'native_entries':1192,'raw_receipts':18,'frozen_refs':50}))
