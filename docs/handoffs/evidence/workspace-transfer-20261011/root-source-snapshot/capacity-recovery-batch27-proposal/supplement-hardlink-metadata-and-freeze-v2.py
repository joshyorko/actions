from pathlib import Path
import ast,hashlib,json,os,shutil,stat
O=Path('/workspace/engineering/capacity-recovery-batch27-proposal');BASE=Path('/workspace/actions-cloud/robocorp/temp')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def save(n,d):
 p=O/n;assert not p.exists();p.write_text(json.dumps(d,indent=2)+'\n');p.chmod(0o600);return bind(p)
old=O/'OWNERFINAL-batch27-exact-three-completed-existing-tmp-preexecution-proposal.json';d=json.loads(old.read_text());original=bind(old);assert original['sha256']=='29552ecfe225e807bee12ac77b00439ed0b42c7244f469d6d7d7c6f798cf7966'
inv=json.loads((O/'private-complete-all-three-body-mode-mtime-UIDGID-type-link-inventories-before-after.json').read_text());assert inv['first']==inv['second']
parents=[Path('/tmp/actions-capacity-recovery-batch19.py'),Path('/tmp/actions-capacity-recovery-batch26.py'),Path('/tmp/actions-capacity-recovery-batch27.py')]
def norm(p):return [ast.dump(n,include_attributes=False)for n in ast.parse(p.read_bytes()).body if not(isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in {'NAMES','DEST','STAGE'}for t in n.targets))]
assert norm(parents[0])==norm(parents[1])==norm(parents[2])and len(norm(parents[2]))==16
first={};second={};counts={}
for destination in [first,second]:
 for name,rows in inv['first'].items():
  root=BASE/name;assert root.is_dir()and not root.is_symlink()and(root/'recycle.now').read_text().strip()=='True';entries={}
  for relative,expected in rows.items():
   p=root/relative;s=p.lstat();assert stat.S_IMODE(s.st_mode)==expected['mode']and s.st_uid==expected['uid']and s.st_gid==expected['gid']and s.st_mtime_ns==expected['mtime_ns']
   kind=expected['kind'];assert {'file':stat.S_ISREG,'directory':stat.S_ISDIR,'symlink':stat.S_ISLNK,'fifo':stat.S_ISFIFO}[kind](s.st_mode)
   if kind=='file':assert s.st_size==expected['bytes']and sha(p)==expected['sha256']
   if kind=='symlink':assert os.readlink(p)==expected['target']
   entries[relative]={'dev':s.st_dev,'ino':s.st_ino,'nlink':s.st_nlink,'kind':kind}
  assert {p.relative_to(root).as_posix()for p in root.rglob('*')}==set(rows)
  destination[name]=entries
assert first==second
for name,rows in first.items():
 grouped={}
 for relative,row in rows.items():
  if row['kind']=='file':grouped.setdefault((row['dev'],row['ino']),[]).append(relative)
 counts[name]={'regular_files':sum(r['kind']=='file'for r in rows.values()),'internal_observed_shared_inode_groups':sum(len(group)>1 for group in grouped.values()),'regular_files_nlink_gt1':sum(r['kind']=='file'and r['nlink']>1 for r in rows.values()),'fifo_members':sum(r['kind']=='fifo'for r in rows.values())}
row=save('private-two-complete-observed-device-inode-link-count-supplement-v2.json',{'first':first,'second':second,'equal':True,'counts':counts,'scope':'Current observed per-member device/inode/nlink relations supplement the repeated complete body/mode/mtime/UIDGID/type/link snapshots. They are not archive restoration guarantees for original inode identity or external hardlink topology; FIFO coverage is actual member count, not manufactured presence.'})
for r in d['private_proof_bindings']+[d['script'],d['algorithm_parent'],d['accepted_B26_identical_algorithm']]:assert bind(r['path'])==r
assert not Path(d['destination_existing_tmp_volume']).exists()and not Path(d['unused_distinct_STAGE']).exists();assert(BASE/'563d911e4172f035').is_dir()
d['schema']='capacity-batch27-owner-preexecution-proposal-v2';d['previous_unannounced_construction_owner_retained']=original;d['supplemental_hardlink_metadata']=row;d['supplemental_hardlink_counts']=counts;d['all_exact_complete_member_device_inode_nlink_snapshots_equal']=True;d['supplement_constructor']=bind(__file__);d['existing_tmp_available_observation']=shutil.disk_usage('/tmp').free;d['workspace_available_observation']=shutil.disk_usage('/workspace').free;d['existing_shm_available_observation']=shutil.disk_usage('/dev/shm').free;assert d['existing_tmp_available_observation']>=d['conservative_capacity_prerequisite']['fresh_required_tmp_available_bytes']
d['limitations'].append('Observed device/inode/nlink equality is preexecution identity evidence only; no original inode, external hardlink topology or post-restoration equality claim. Actual selected FIFO count is zero.')
d['private_proof_bindings'].append(row)
p=O/'OWNERFINAL-batch27-exact-three-completed-existing-tmp-preexecution-proposal-v2.json';assert not p.exists();p.write_text(json.dumps(d,indent=2)+'\n');p.chmod(0o400);assert bind(old)==original
print(json.dumps({'OWNERFINAL':bind(p),'script':bind(parents[2]),'names':d['names_exact_allowlist'],'members':d['complete_members_before_after'],'allocated_observation':d['total_allocated_unique_blocks_observation'],'logical':d['total_regular_logical_bytes'],'tmp_required':d['conservative_capacity_prerequisite']['fresh_required_tmp_available_bytes'],'tmp_available':d['existing_tmp_available_observation'],'workspace_available':d['workspace_available_observation'],'shm_available':d['existing_shm_available_observation'],'hardlink_type_counts':counts,'archive_execution':'NOT_RUN'}))
