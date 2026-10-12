import datetime
import hashlib
import json
import pathlib
import subprocess

R=pathlib.Path('/workspace/engineering/checkpoint-1180-independent-review')
W=pathlib.Path('/workspace/engineering/campaign-checkpoint')
PFX='docs/program/evidence/wave11/current-engineering-20261011/'
HEAD='62f4e180f6c894777ebc8ed3a729e88d2f6531d6'
PARENT='bd023f9fd2ea8007031c2bd4f909cab4546dabe1'
TREE='a7cb47cef9eae2ce3b219bb807b535582c67804e'
BRANCH='handoff/actions-swarm-mk3-wave8-20261010'
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):
    p=pathlib.Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def git(*a):return subprocess.check_output(['git','--no-optional-locks',*a],cwd=W)
def write(n,d):
    p=R/n
    with p.open('x') as f:json.dump(d,f,indent=2,sort_keys=True);f.write('\n')
    p.chmod(0o444);return ref(p)
rootpath=pathlib.Path('/workspace/engineering/checkpoint-1180-root-normal-commit-push.json')
root=json.loads(rootpath.read_bytes());assert ref(rootpath)['bytes']==644 and ref(rootpath)['sha256']=='443e3e8953610ce4497194fcd279cbfeda12b431df71e2bbe3c56b19e71da4ca'
stagepath=R/'OWNERFINAL-independent-staged1180-checkpoint-review.json'
stage=json.loads(stagepath.read_bytes());assert ref(stagepath)['bytes']==7640 and ref(stagepath)['sha256']=='05a681ba01187612607981fc30674912f7432ef37d8ecef86c33c241acab22cb'
assert root['head']==HEAD and root['tree']==TREE and root['parent']==PARENT and root['normal_push'] is True
assert git('show','-s','--format=%H%n%T%n%P','HEAD').decode().splitlines()==[HEAD,TREE,PARENT]
assert git('branch','--show-current').decode().strip()==BRANCH
assert not git('status','--porcelain=v1')
api_ref=R/'authenticated-named-branch-commit-readback.private.json'
api_commit=R/'authenticated-committed-Git-object-readback.private.json'
named=json.loads(api_ref.read_bytes());commit=json.loads(api_commit.read_bytes())
assert named['ref']=='refs/heads/'+BRANCH and named['object']['type']=='commit' and named['object']['sha']==HEAD
assert commit['sha']==HEAD and commit['tree']['sha']==TREE and [x['sha'] for x in commit['parents']]==[PARENT]
assert ref(api_ref)=={'path':str(api_ref),'bytes':455,'sha256':'8e694d85d3afea4be1e21c9e8896ef87165cd855f7933f3626553361c4f022a1'}
assert ref(api_commit)=={'path':str(api_commit),'bytes':1151,'sha256':'fabc1714092544fb3ba81634ce9916c5650b14bd5d53218f28cbd7ce2ea9ae9a'}
remote=write('authenticated-committed-remote-identity-safe-proof.json',{'status':'EXACT_GIT_NAMED_REMOTE_AND_SEPARATE_AUTHENTICATED_API_READBACK','named_Git_readback':{'command':['git','--no-optional-locks','-C',str(W),'ls-remote','--heads','origin',BRANCH],'original_tool_stdout_sha256':sha((HEAD+'\trefs/heads/'+BRANCH+'\n').encode()),'observed_sha':HEAD,'scope':'Original independent command output observed before these API reads; no cached API alias substitution.'},'authenticated_named_ref':ref(api_ref),'authenticated_Git_commit':ref(api_commit),'head':HEAD,'tree':TREE,'ordered_parents':[PARENT],'no_remote_ref_mutation':True})
tree={}
for row in git('ls-tree','-rz','HEAD').split(b'\0'):
    if row:
        metadata,path=row.split(b'\t',1);mode,typ,blob=metadata.decode().split();tree[path.decode()]={'mode':mode,'type':typ,'blob':blob}
old={}
for row in git('ls-tree','-rz',PARENT).split(b'\0'):
    if row:
        metadata,path=row.split(b'\t',1);mode,typ,blob=metadata.decode().split();old[path.decode()]={'mode':mode,'type':typ,'blob':blob}
index=git('ls-files','-s','-z');assert sha(index)==stage['subject']['semantic_index_sha256']
manifest_bytes=git('show','HEAD:'+PFX+'manifest.json');manifest=json.loads(manifest_bytes)
oldmanifest=json.loads(git('show',PARENT+':'+PFX+'manifest.json'))
assert len(manifest)==1180 and len(oldmanifest)==644 and all(manifest[k]==v for k,v in oldmanifest.items())
added={k:v for k,v in manifest.items() if k not in oldmanifest};assert len(added)==536 and sum(v['bytes'] for v in added.values())==27405588
changed={p for p in set(tree)|set(old) if tree.get(p)!=old.get(p)}
assert changed=={PFX+n for n in added}|{PFX+'README.md',PFX+'manifest.json','docs/skills/repository-operations.md'} and len(changed)==539
stageproof=json.loads((R/'all1180-original-copy-typed-staged-byte-proof-v3.json').read_bytes())
stage_records={x['payload']:x for x in stageproof['records']};records=[]
for name,record in manifest.items():
    p=PFX+name;entry=tree[p];assert entry['mode']=='100644' and entry['type']=='blob'
    b=git('show','HEAD:'+p);assert len(b)==record['bytes'] and sha(b)==record['sha256']
    assert (W/p).read_bytes()==b and not ((W/p).stat().st_mode & 0o111)
    source=pathlib.Path(record['source'])
    if source.is_file():assert source.read_bytes()==b
    else:assert name=='pr290-actual-integration.json' and name in oldmanifest
    assert stage_records[name]['blob']==entry['blob'] and stage_records[name]['mode']==entry['mode']
    if name in oldmanifest:assert old[p]==entry
    records.append({'payload':name,**entry,**record})
patch=git('diff',PARENT,HEAD,'--','docs/skills/repository-operations.md')
assert patch==(R/'exact-staged-canonical74-delta.patch').read_bytes()
assert len([x for x in patch.splitlines() if x.startswith(b'+') and not x.startswith(b'+++')])==74
assert not [x for x in patch.splitlines() if x.startswith(b'-') and not x.startswith(b'---')]
can=json.loads((R/'canonical74-and-README-scope-proof.json').read_bytes())
assert sha(git('diff',PARENT,HEAD,'--',PFX+'README.md'))==can['README_delta_sha256']
for p in ['docs/skills/repository-operations.md',PFX+'README.md',PFX+'manifest.json']:
    assert tree[p]['mode']=='100644' and (W/p).read_bytes()==git('show','HEAD:'+p) and not((W/p).stat().st_mode & 0o111)
proof=write('complete1180-committed-original-and-reviewed-stage-byte-proof.json',{'head':HEAD,'tree':TREE,'sole_parent':PARENT,'all1180_committed_original_copy_blobs_modes':records,'prior644_manifest_records_and_typed_blobs_exact':True,'new536_bytes':27405588,'changed_paths':539,'other_parent_typed_entries_unchanged':True,'exact_reviewed_stage_entry_serialization':sha(index),'canonical74_patch_exact':ref(R/'exact-staged-canonical74-delta.patch'),'README_diff_exact_reviewed_stage':True,'nested_full_repeat':'Not repeated: every committed manifest record/blob is byte-identical to independently reviewed stage; exact retained nested readback/dispositions remain bound unchanged.'})
bound=[ref(R/n) for n in ['OWNERFINAL-independent-staged1180-checkpoint-review.json','all1180-original-copy-typed-staged-byte-proof-v3.json','new536-nested-original-binding-readback.json','precise-historical-nested-alias-and-measurement-dispositions.json','new536-safe-content-and-declared-scope-proof.json','canonical74-and-README-scope-proof.json','exact-staged-canonical74-delta.patch']]
for expected in stage['proof_bindings']:
    assert ref(expected['path'])==expected
assert not git('status','--porcelain=v1') and sha(git('ls-files','-s','-z'))==stage['subject']['semantic_index_sha256']
result={'schema':'ownerfinal_independent_committed_and_authenticated_remote1180_readback','status':'GO_COMMITTED_REMOTE_1180_CHECKPOINT_ONLY_NO_ACCEPTANCE_UPGRADE','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'subject':{'branch':BRANCH,'head':HEAD,'tree':TREE,'sole_parent':PARENT,'worktree_clean':True},'root_normal_commit_push':ref(rootpath),'independent_staged_review':ref(stagepath),'admission':{'named_Git_remote_exact':True,'separate_authenticated_named_ref_API_exact':True,'separate_authenticated_commit_tree_parent_API_exact':True,'complete1180_manifest_copies_named_originals_Git_blobs_typed_modes_exact':True,'prior644_preserved':True,'new536_bytes':27405588,'539_changes_exact_stage':True,'canonical74_additions_zero_removals_exact_stage':True,'README_scope_exact_stage':True,'all_other_parent_entries_unchanged':True,'private_exclusions_exact_stage':True},'preserved_historical_scopes':{'current_nested_exact':5370,'cleaned_installed_member_measurements':196,'historical_noncurrent_aliases':26,'unrecovered_manifest22524B_SHAa483':'Remains unrecovered; no reconstructed alias or predecessor construction admission.','pre_Ruff_renderer':'Original19364/ade8 construction observation not recovered, not a frozen actual pin.','historical_issue86':'Two source784 Git blobs are historical proposal inputs; later authorized source work remains separate.','zero_byte_logger':'Historical construction observations subsequently appended; not current terminal log bindings.','original_tested_checkout':'Original012cd8 object absent locally; retained API/tree/original log proof remains distinct from actuala0d/source831 common Git objects.'},'documentation_improvement':stage['documentation_improvement'],'remaining_holds':stage['remaining_holds'],'no_Git_source_index_ref_collector_gate_actual_download_mutation':True,'proof_bindings':bound+[remote,proof,ref(__file__)],'upstream_disposition':'none'}
final=write('OWNERFINAL-independent-committed-remote1180-checkpoint-review.json',result)
print(json.dumps(final,sort_keys=True))
