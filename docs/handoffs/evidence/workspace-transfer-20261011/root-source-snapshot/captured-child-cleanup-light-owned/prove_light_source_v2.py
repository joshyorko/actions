import ast
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path('/workspace/engineering/captured-child-cleanup')
OUT = Path('/workspace/engineering/captured-child-cleanup-light-owned')
PARENT = 'a0d258a16095b95b1bf9000cb1201cddfaff4779'


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def bind(path):
    path=Path(path)
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':digest(path)}


def entries(revision, paths=()):
    result={}
    for record in git('ls-tree','-r','-z',revision,'--',*paths).split(b'\0'):
        if record:
            meta,path=record.split(b'\t',1);mode,kind,blob=meta.decode().split()
            result[path.decode()]={'mode':mode,'kind':kind,'blob':blob}
    return result


def inventory(root):
    result={}
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            p=Path(directory)/name;s=p.lstat()
            row={'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid}
            if stat.S_ISLNK(s.st_mode):row.update(kind='symlink',target=os.readlink(p))
            elif stat.S_ISDIR(s.st_mode):row.update(kind='directory')
            elif stat.S_ISREG(s.st_mode):row.update(kind='file',bytes=s.st_size,sha256=digest(p))
            else:raise AssertionError('unexpected source environment kind')
            result[str(p.relative_to(root))]=row
    return result


head=git('rev-parse','HEAD').decode().strip()
parents=git('show','-s','--format=%P',head).decode().split()
assert parents==[PARENT]
assert git('status','--porcelain')==b''
before=entries(PARENT);after=entries(head)
changed=sorted(p for p in before if before[p]!=after.get(p))
added=sorted(set(after)-set(before))
assert changed==['action_server/src/actions/server/_common/process.py','docs/skills/repository-operations.md']
assert added==['action_server/tests/action_server_tests/common_tests/test_captured_process_tree_deadline.py']
assert set(before)<=set(after)
path=changed[0];original=git('show',PARENT+':'+path);current=(ROOT/path).read_bytes()
assert hashlib.sha256(original).hexdigest()=='f432e65a488bf06862e548dc45342d3c1fb5ea7fcc26f6371d98aae124ffc082'
a=ast.parse(original);b=ast.parse(current)
fn=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name=='force_kill_process_tree_until')
inserted=[n for n in fn.body if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp)
          and isinstance(n.test.values[0],ast.Name) and n.test.values[0].id=='wrapper_reaped']
assert len(inserted)==1
fn.body.remove(inserted[0])
assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
guide=ROOT/changed[1]
proposal=Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned/canonical-captured-tree-unused-deadline-proposed.patch')
assert digest(proposal)=='36cc60d3263af329268d80c32f28fdd6ae5909fd71d9fc7bd60ba59c3dd04f93'
added_lines=[line[1:] for line in proposal.read_text().splitlines(True) if line.startswith('+') and not line.startswith('+++')]
assert len(added_lines)==12
oldguide=git('show',PARENT+':'+changed[1]).decode()
lesson=''.join(added_lines)
anchor='`crash_unverified` classification across retries until the reader is joined.\n'
assert oldguide.count(anchor)==1
assert guide.read_text()==oldguide.replace(anchor,anchor+lesson)
verifier=ROOT/'action_server/scripts/verify_frozen_catalog_harness.py'
ns={}
for node in ast.parse(verifier.read_text()).body:
    if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name):
        name=node.targets[0].id
        if name=='INPUT_PATHS':ns[name]=ast.literal_eval(node.value)
tests=json.loads((ROOT/'docs/program/evidence/runtime-frozen-current-source-20261011/selected-test-inventory.json').read_bytes())
producer=entries(head,ns['INPUT_PATHS']);parentproducer=entries(PARENT,ns['INPUT_PATHS'])
native=entries('92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e',ns['INPUT_PATHS'])
assert len(native)==268
producer_changes=sorted(p for p in producer if producer[p]!=parentproducer.get(p))
assert producer_changes==[path]
selected=entries(head,tuple(tests));parentselected=entries(PARENT,tuple(tests))
nativeselected=entries('92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e',tuple(tests))
assert selected==parentselected and len(selected)==5
native_diff=sorted(p for p in native if native[p]!=producer.get(p))
native_added=sorted(set(producer)-set(native))
selector_diff=sorted(p for p in selected if selected[p]!=nativeselected.get(p))
original_owner=Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned/OWNERFINAL-original-cleanup-deterministic-control-v2.json')
old=json.loads(original_owner.read_bytes());assert digest(original_owner)=='ab1d68eded83108fa58c32046f2d2c2b8dfa92972b6fedf7a66a4cb72ab87c22'
for item in old['bindings']:assert bind(item['path'])==item
copy=json.loads((OUT/'own-five-environment-copy-proof.json').read_bytes())
postenv=[]
for item in copy['environments']:
    record=json.loads(Path(item['inventory']['path']).read_bytes())
    source=Path('/workspace/engineering/pr306')/item['package']/'.venv'
    assert inventory(source)==record['original_complete_inventory']
    postenv.append({'package':item['package'],'source_original_complete_inventory_exact':True,'members':item['members']})
for filename,data in [('current-producer-input-inventory.json',producer),('current-five-selected-test-inventory.json',selected)]:
    p=OUT/filename
    with p.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
    p.chmod(0o600)
r={'head':head,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'parents':parents,
   'parent_leaf_count':len(before),'current_leaf_count':len(after),'all_parent_leaves_retained':True,
   'changed':changed,'added':added,'source_parent_body_sha256':hashlib.sha256(original).hexdigest(),
   'source_current_body_sha256':hashlib.sha256(current).hexdigest(),
   'whole_source_module_AST_exact_after_removing_one_added_wait_block':True,
   'legacy_stop_startup_readers20_2_and_result_properties_unchanged':True,
   'whole_GitHub_and_all_other_parent_blobs_modes_exact':True,
   'canonical_exact12line_accepted_patch':bind(proposal),'canonical_patch_applied_exactly':True,
   'current_producer_count':len(producer),'original_native_count':len(native),
   'only_new_producer_delta_from_actual_parent':producer_changes,
   'native_changed_original_paths':native_diff,'native_added_paths':native_added,
   'five_selectors_unchanged_actual_parent':True,'native_selector_differences':selector_diff,
   'old_native_qualification':'UNQUALIFIED_CHANGED_PRODUCTION_INPUTS_NO_EXCLUSIONS_OR_REPIN',
   'original_control_owner':bind(original_owner),'all_original31_references_unchanged':True,
   'source_original_five_environment_complete_inventories_after_LIGHT':postenv,
   'capacity_observation_only':os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize}
p=OUT/'LIGHT-immutable-source-and-preservation-proof.json'
with p.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
p.chmod(0o600)
print(json.dumps({'head':head,'tree':r['tree'],'producer_count':len(producer),'native_changes':len(native_diff),'native_additions':len(native_added),'selector_changes':len(selector_diff),'all_parent_leaves_retained':True}))
