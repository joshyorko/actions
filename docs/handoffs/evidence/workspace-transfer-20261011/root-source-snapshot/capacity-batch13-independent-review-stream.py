from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,gzip,stat,ast,time,os,collections
START=time.monotonic();O=Path('/workspace/engineering/capacity-recovery-batch13-independent-review');O.mkdir(mode=0o700,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def binding(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def exact(v):p=Path(v['path']);assert p.is_file() and p.stat().st_size==v['bytes'] and sha(p)==v['sha256'];return v
safe=Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch13.json');assert safe.stat().st_size==2244 and sha(safe)=='e95c0d759973dde731805be7ea41a79b79fcd01a84cce1be6c9e470d17c0a6fb';S=json.loads(safe.read_bytes());index=exact(S['private_inventory_binding']);script=exact(S['recovery_script_binding']);log=exact(S['terminal_log_binding']);I=json.loads(Path(index['path']).read_bytes());assert len(I['records'])==2
A=ast.parse(Path(script['path']).read_bytes());B=ast.parse(Path('/tmp/actions-capacity-recovery-batch12.py').read_bytes());assert len(A.body)==len(B.body);changes=[]
for a,b in zip(A.body,B.body):
 if ast.dump(a,include_attributes=False)!=ast.dump(b,include_attributes=False):
  assert isinstance(a,ast.Assign) and isinstance(b,ast.Assign) and ast.dump(ast.Assign(a.targets,ast.Constant(None)),include_attributes=False)==ast.dump(ast.Assign(b.targets,ast.Constant(None)),include_attributes=False)
  class EraseConstants(ast.NodeTransformer):
   def visit_Constant(self,node): return ast.Constant(None)
  assert ast.dump(EraseConstants().visit(ast.parse(ast.unparse(a.value),mode='eval')),include_attributes=False)==ast.dump(EraseConstants().visit(ast.parse(ast.unparse(b.value),mode='eval')),include_attributes=False)
  changes.extend(t.id for t in a.targets if isinstance(t,ast.Name))
assert sorted(changes)==['DEST','NAMES','STAGE']
aggregates=[];total=0
for r in I['records']:
 names={Path(v['original_namespace']).name for v in S['archives']};namespace=Path(r['original_namespace']).name;assert namespace in names and namespace in {'1664205128f89d2a','e9752d23b1fadd92'};parent=Path(r['original_namespace']);assert parent.parent==Path('/workspace/actions-cloud/robocorp/temp') and not parent.exists();archive=Path(r['archive']);assert stat.S_IMODE(archive.stat().st_mode)==0o600 and archive.stat().st_size==r['archive_bytes'] and sha(archive)==r['archive_sha256'];assert r['archive_verified_before_original_removal'] is True and r['expanded_removed'] is True
 safeentry=next(v for v in S['archives'] if v['original_namespace']==r['original_namespace']);assert all(safeentry[k]==r[k] for k in ['archive','archive_bytes','archive_sha256','verified_members']);inventory=r['inventory'];seen=set();payloadhash={};links={};kindcounts=collections.Counter();logicalbytes=0;headers=0;roots=0
 with gzip.open(archive,'rb') as compressed:
  with tarfile.open(fileobj=compressed,mode='r|') as tar:
   for m in tar:
    headers+=1;parts=PurePosixPath(m.name).parts;assert parts and parts[0]==namespace and not PurePosixPath(m.name).is_absolute() and '..' not in parts
    if len(parts)==1:assert m.isdir();roots+=1;continue
    rel=str(PurePosixPath(*parts[1:]));assert rel in inventory and rel not in seen;seen.add(rel);v=inventory[rel];assert (m.mode,m.uid,m.gid)==(v['mode'],v['uid'],v['gid']);kindcounts[v['kind']]+=1
    if m.isfile():
     assert v['kind']=='file' and m.size==v['bytes'];h=hashlib.sha256();size=0;f=tar.extractfile(m);assert f is not None
     while True:
      b=f.read(1024*1024)
      if not b:break
      h.update(b);size+=len(b)
     f.close();assert size==v['bytes'] and h.hexdigest()==v['sha256'];payloadhash[rel]=(size,h.hexdigest());logicalbytes+=size
     if rel=='recycle.now':assert v['bytes']==4 and v['sha256']==hashlib.sha256(b'True').hexdigest()
    elif m.islnk():
     assert v['kind']=='file';target=PurePosixPath(m.linkname);assert not target.is_absolute() and '..' not in target.parts and target.parts[0]==namespace;links[rel]=str(PurePosixPath(*target.parts[1:]))
    elif m.isdir():assert v['kind']=='directory'
    elif m.issym():assert v['kind']=='symlink' and m.linkname==v['target']
    elif m.isfifo():assert v['kind']=='fifo'
    else:raise AssertionError('unexpected_archive_member_kind')
  # Reach gzip EOF to verify original trailer CRC/size; no extraction/restoration.
  while compressed.read(1024*1024):pass
 assert seen==set(inventory) and len(seen)==r['verified_members'] and roots==1
 def resolve(name,active):
  assert name not in active
  if name in payloadhash:return payloadhash[name]
  assert name in links;return resolve(links[name],active|{name})
 for name,target in links.items():
  size,digest=resolve(name,set());v=inventory[name];assert size==v['bytes'] and digest==v['sha256'];logicalbytes+=size
 assert 'recycle.now' in inventory and inventory['recycle.now']['kind']=='file' and inventory['recycle.now']['bytes']==4 and inventory['recycle.now']['sha256']==hashlib.sha256(b'True').hexdigest()
 total+=len(seen);aggregates.append({'original_namespace':r['original_namespace'],'archive':r['archive'],'archive_bytes':r['archive_bytes'],'archive_sha256':r['archive_sha256'],'recorded_members':len(seen),'tar_headers':headers,'root_headers_excluded_from_metadata_admission':roots,'member_kind_counts':dict(kindcounts),'internal_hardlink_headers':len(links),'logical_regular_file_bytes_verified':logicalbytes,'gzip_CRC_and_size_trailer_verified':True,'all_inventory_names_exact_unique':True,'all_recorded_member_kind_mode_UID_GID_exact':True,'all_regular_and_internal_hardlink_size_SHA_exact':True,'symlink_targets_exact_no_dereference':True,'completed_recycle_true_marker_verified':True,'original_expanded_namespace_currently_absent':True})
assert total==31189==S['recorded_members'];assert stat.S_IMODE(Path(index['path']).stat().st_mode)==0o600 and stat.S_IMODE(Path(index['path']).parent.stat().st_mode)==0o700
result={'root_safe':binding(safe),'private_index_binding':index,'script_binding':script,'log_binding':log,'AST_exact_batch12_except3_configuration_values':changes,'archives':aggregates,'all31189_recorded_members_exact':True,'review_seconds':round(time.monotonic()-START,3),'private_payloads_member_names_and_configuration_not_in_safe_stdout':True,'limitations':['Historical before-removal verification order is retained source/log/index evidence,not independently replayed pre-removal filesystem','No historical complete handlecensus,ACL,xattr,inode,rootmetadata,preciseTARmtime,or failedgateGO'],'no_extract_restore_remove_GC_source_gate_actual_mutation':True,'upstream_disposition':'none'}
p=O/'independent-two-archive-stream-preservation-proof.json';p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');p.chmod(0o600);print(json.dumps({'proof':binding(p),'recorded_members':total,'archive_count':len(aggregates),'archive_payload_sha256':[v['archive_sha256'] for v in aggregates],'review_seconds':result['review_seconds']}))
