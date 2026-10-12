import ast
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

OUT = Path('/workspace/engineering/capacity-recovery-batch27-independent-preexecution-review')
PROP = Path('/workspace/engineering/capacity-recovery-batch27-proposal/OWNERFINAL-batch27-exact-three-completed-existing-tmp-preexecution-proposal-v2.json')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
assert sha(PROP)=='dabe89c9b8d05c714207c7880b30195baf90c341fd3ecc657b9143545d6d2673'
p=json.loads(PROP.read_bytes())
def bind(v):
    path=Path(v['path']);assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size==v['bytes'] and sha(path)==v['sha256']
    assert oct(stat.S_IMODE(path.stat().st_mode))==v['mode']
for key in ('script','algorithm_parent','accepted_B26_identical_algorithm','metadata_selection_proof','metadata_prepare_constructor','metadata_selection_constructor','constructor','previous_unannounced_construction_owner_retained','supplement_constructor'):
    bind(p[key])
for row in p['private_proof_bindings']:bind(row)
bind(p['Documentation_improvement']['Exact_delta_or_verified_reuse'])
def normalize(path):
    tree=ast.parse(Path(path).read_text()); assignments={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('DEST','STAGE','NAMES'):
            assignments[node.targets[0].id]=node.value
            node.value=ast.Constant(value='NORMALIZED_CONFIGURATION_ONLY')
    return ast.dump(tree,include_attributes=False),assignments
base,_=normalize(p['algorithm_parent']['path'])
for key in ('script','accepted_B26_identical_algorithm'):
    norm,config=normalize(p[key]['path']);assert norm==base
_,config=normalize(p['script']['path'])
assert ast.literal_eval(config['NAMES'])==p['names_exact_allowlist']
for key,field in [('DEST','destination_existing_tmp_volume'),('STAGE','unused_distinct_STAGE')]:
    assert ast.literal_eval(config[key].args[0])==p[field]
    assert not Path(p[field]).exists()
inventory_data=json.loads(Path(p['private_proof_bindings'][2]['path']).read_bytes())
supplement=json.loads(Path(p['supplemental_hardlink_metadata']['path']).read_bytes())
assert inventory_data['first']==inventory_data['second']
assert supplement['first']==supplement['second']
tree=ast.parse(Path(p['script']['path']).read_text())
module=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('sha','inventory','reject_live_handles')],type_ignores=[])
scope={'hashlib':hashlib,'Path':Path,'stat':stat,'os':os}
exec(compile(module,'<readonly-inventory-functions>','exec'),scope)
members=0
for name in p['names_exact_allowlist']:
    root=Path('/workspace/actions-cloud/robocorp/temp')/name
    assert root.is_dir() and not root.is_symlink()
    assert (root/'recycle.now').read_text().strip()=='True'
    scope['reject_live_handles'](root)
    actual=scope['inventory'](root);assert actual==inventory_data['first'][name]
    members+=len(actual)
    current={}
    for path in sorted(root.rglob('*')):
        st=path.lstat();kind=actual[str(path.relative_to(root))]['kind']
        current[str(path.relative_to(root))]={'dev':st.st_dev,'ino':st.st_ino,'nlink':st.st_nlink,'kind':kind}
    assert current==supplement['first'][name]
assert members==15195
ret=json.loads(Path(p['private_proof_bindings'][4]['path']).read_bytes())
assert len(ret['archives'])==58 and len(ret['indices'])==26
retained_bytes=0
for row in ret['archives']+ret['indices']:
    path=Path(row.get('path',row.get('archive')))
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
    assert oct(stat.S_IMODE(path.stat().st_mode))==row['mode']
    retained_bytes+=path.stat().st_size
source=Path('/workspace/engineering/pr308')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==p['current_source_owner_context']['head']
assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=source,text=True).strip()==p['current_source_owner_context']['tree']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=source)
entries=subprocess.check_output(['git','ls-tree','-rz','HEAD'],cwd=source).split(b'\0')
count=0
for entry in entries:
    if not entry:continue
    meta,path=entry.split(b'\t',1);mode,kind,obj=meta.split();assert kind==b'blob'
    leaf=source/os.fsdecode(path);st=leaf.lstat()
    raw=os.readlink(leaf).encode() if mode==b'120000' else leaf.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==obj.decode()
    if mode!=b'120000':assert bool(st.st_mode&0o111)==(mode==b'100755')
    count+=1
assert count==1423
config=Path('/workspace/engineering/rcc-compatibility-current-e4ff-qualified-config-successor/FROZEN-current-e4ff-control3-owned-cache-SOURCE-QUALIFIED-v4.json')
assert sha(config)=='1411879501e1ef2bd5aec7fbf9627457aa840badc8e86be980c25b207ee9d5dc'
cfg=json.loads(config.read_bytes());native_root=Path(cfg['native_original_root'])
assert len(cfg['native_original_members'])==1192
for row in cfg['native_original_members']:
    leaf=native_root/row['path'];st=leaf.lstat()
    assert stat.S_IMODE(st.st_mode)==row['mode']
    if row['kind']=='file':assert sha(leaf)==row['content_sha256']
    elif row['kind']=='symlink':assert os.readlink(leaf)==row['link_target']
    elif row['kind']=='directory':assert leaf.is_dir() and not leaf.is_symlink()
    else:raise AssertionError('Unexpected native member kind')
for rel,digest in cfg['prepared_inputs'].items():assert sha(source/rel)==digest
bind(p['failed_control3_separate_original_root_archive_preservation_mapping'])
mapping=json.loads(Path(p['failed_control3_separate_original_root_archive_preservation_mapping']['path']).read_bytes())
assert Path('/workspace/actions-cloud/robocorp/temp/563d0b75fd30e860').exists() or any(x.name.startswith('563d') for x in Path('/workspace/actions-cloud/robocorp/temp').iterdir())
failed=Path('/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-2/OWNERFINAL-one-version-actual-result.json')
assert sha(failed)=='d4ebd4111e362d3ac3f8dc519d3826ad19c71e1d06dffe7dd959a4ebd2b45ca8'
import shutil
space={key:shutil.disk_usage(path).free for key,path in [('workspace','/workspace'),('tmp','/tmp'),('shm','/dev/shm')]}
assert space['tmp']>=p['conservative_capacity_prerequisite']['fresh_required_tmp_available_bytes']
proof={'schema':1,'status':'READONLY_PREEXECUTION_VERIFIED','proposal_sha256':sha(PROP),'script_sha256':p['script']['sha256'],'complete_source_leaves':count,'native_members':1192,'prepared_inputs':len(cfg['prepared_inputs']),'selected_names':p['names_exact_allowlist'],'complete_members':members,'prior_archives':58,'prior_indices':26,'prior_retained_bytes_rehashed':retained_bytes,'fresh_capacity_observation':space,'no_observed_accessible_handles':True,'inaccessible_process_visibility':'UNKNOWN','origin':'UNREPORTED','archive_or_removal_executed':False}
out=OUT/'independent-exact-B27-readonly-proof.json';assert not out.exists();out.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');out.chmod(0o400)
print(json.dumps({'proof_bytes':out.stat().st_size,'proof_sha256':sha(out)}))
