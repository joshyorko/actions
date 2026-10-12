from pathlib import Path,PurePosixPath
import hashlib,json,os,stat,tarfile,time
D=Path('/workspace/engineering/capacity-recovery-batch2-independent-review');R=Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch2.json');started=time.monotonic()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def binding(p):return {'path':str(p),'bytes':Path(p).stat().st_size,'sha256':sha(p)}
assert sha(R)=='30bcb73c25914e33eb0705cdb5367cc1a07cfba5f0890eaf8d365876186f3537';summary=json.loads(R.read_text());private=Path(summary['private_inventory_binding']['path']);assert binding(private)==summary['private_inventory_binding']
assert stat.S_IMODE(private.stat().st_mode)==0o600 and stat.S_IMODE(private.parent.stat().st_mode)==0o700
records=json.loads(private.read_text())['records'];assert len(records)==2
expected_names={'6b455050c1f6a22d','ce8f66eb0879d4bc'}
assert {Path(r['original_namespace']).name for r in records}==expected_names
counts=[];total=0
for record in records:
 root=Path(record['original_namespace']);name=root.name;assert root.parent==Path('/workspace/actions-cloud/robocorp/temp') and not root.exists() and record['expanded_removed'] and record['archive_verified_before_original_removal']
 archive=Path(record['archive']);assert archive.parent==private.parent and archive.name==name+'.tar.gz' and not archive.is_symlink() and stat.S_IMODE(archive.stat().st_mode)==0o600
 assert archive.stat().st_size==record['archive_bytes'] and sha(archive)==record['archive_sha256']
 public=next(r for r in summary['archives'] if r['original_namespace']==str(root));assert all(public[k]==record[k] for k in public)
 inventory=record['inventory']; assert len(inventory)==record['verified_members']; seen={}; data={};links={};types={'file':0,'directory':0,'symlink':0,'fifo':0,'hardlink_headers':0}; root_seen=0;recycle=False;bytes_verified=0
 with tarfile.open(archive,'r|gz') as tf:
  for m in tf:
   if m.name==name:
    assert m.isdir();root_seen+=1;continue
   assert m.name.startswith(name+'/');relative=m.name[len(name)+1:];pp=PurePosixPath(relative)
   assert relative and not pp.is_absolute() and '..' not in pp.parts and relative not in seen and relative in inventory
   seen[relative]=True;e=inventory[relative];assert m.mode==e['mode'] and (m.uid,m.gid)==(e['uid'],e['gid'])
   kind=e['kind'];types[kind]+=1
   if kind=='file':
    if m.islnk():
     assert m.linkname.startswith(name+'/');dest=m.linkname[len(name)+1:];q=PurePosixPath(dest);assert dest and not q.is_absolute() and '..' not in q.parts and dest in inventory and inventory[dest]['kind']=='file';links[relative]=dest;types['hardlink_headers']+=1
    else:
     assert m.isfile();stream=tf.extractfile(m);h=hashlib.sha256();size=0;marker=b''
     for b in iter(lambda:stream.read(1024*1024),b''):
      h.update(b);size+=len(b)
      if relative=='recycle.now':marker+=b
     assert size==e['bytes'] and h.hexdigest()==e['sha256'];data[relative]=(size,h.hexdigest());bytes_verified+=size
     if relative=='recycle.now':assert marker.strip()==b'True';recycle=True
   elif kind=='symlink':assert m.issym() and m.linkname==e['target']
   elif kind=='directory':assert m.isdir()
   elif kind=='fifo':assert m.isfifo()
   else:raise AssertionError('unsupported inventory member category')
 assert root_seen==1 and set(seen)==set(inventory) and recycle
 for rel in links:
  dest=rel;cycle=set()
  while dest in links:
   assert dest not in cycle;cycle.add(dest);dest=links[dest]
  assert dest in data
  e=inventory[rel];assert data[dest]==(e['bytes'],e['sha256']);bytes_verified+=e['bytes']
 counts.append({'namespace':name,'archive':binding(archive),'root_directory_header':root_seen,'members_verified':len(inventory),'kinds':types,'resolved_internal_hardlink_data_verified':len(links),'logical_regular_file_bytes_verified':bytes_verified,'completed_recycle_marker_verified':True,'expanded_namespace_absent':True})
 total+=len(inventory)
 print(json.dumps({'completed_archive':name,'members':len(inventory),'internal_hardlinks':len(links)}),flush=True)
assert total==30078
# Read-only original tool ordering and bounds, not execution of that cleanup script.
tool=Path('/tmp/actions-capacity-recovery-batch2.py');source=tool.read_text();assert source.index('verify(archive, name, entries)',source.index('for name in NAMES:'))<source.index('shutil.rmtree(root)')
assert 'assert inventory(root) == entries' in source and 'reject_live_handles(root)' in source and "(root / 'recycle.now').read_text().strip() == 'True'" in source
result={'verdict':'GO_SCOPED_PRIVATE_ARCHIVE_DATA_AND_RECORDED_MEMBER_METADATA_PRESERVATION; NOT_ACCEPTANCE_OR_BACKUP_OF_UNRECORDED_METADATA','summary':binding(R),'private_inventory':binding(private),'private_inventory_mode':'0600','archives_parent_mode':'0700','two_archives':counts,'all30078_inventory_member_names_exact_unique':True,'regular_and_hardlink_bytes_size_SHA256_exact':True,'member_mode_uid_gid_exact':True,'symlink_targets_exact_without_dereferencing':True,'internal_hardlink_targets_bounded_to_same_archive_and_payloads_exact':True,'completed_recycle_now_true_markers_verified':True,'existing_two_expanded_namespaces_absent':True,'source_recovery_script':binding(tool),'historical_ordering':'Existing script verifies archive, rechecks full inventory and live handles, then writes retained inventory and removes only exact completed namespace; initial regular-only rejection reportedly removed nothing. Independent review does not rerun script or reconstruct historical live fd observation.','limitations':['Expanded originals intentionally removed; original byte identity is independently checked against retained pre-removal complete inventory and archive summary, not surviving expanded files.','Inventory does not record original inode equivalence, root-directory metadata, ACL/xattrs or full nanosecond archive mtime roundtrip; independent GO covers named30078 member bytes/modes/uidgid/symlink targets and archived internal-hardlink data, not unspecified metadata.','Prior no-live-fd/cwd precondition and untouched-other-path claims are supported by recorded scope/script, not a retroactive independent full filesystem/process census.','No private archive contents/member names or full89k inventory admitted to Git or tool output; only safe six-namespace aggregate fields and hashes.','Source/native/consumer/cache/venv unchanged historical assertion not a fresh hash of concurrently mutating source writers. Failed ENOSPC gates remain failed; new bounded gate replay required.'],'review_seconds':round(time.monotonic()-started,3),'upstream':'none'}
p=D/'independent-batch2-archive-preservation-review.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(binding(p)),flush=True)
