import ast
import datetime
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile
import time

OUT=Path('/workspace/engineering/capacity-recovery-batch15-independent-review')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for data in iter(lambda:f.read(1048576),b''):h.update(data)
 return h.hexdigest()
def binding(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(row):assert binding(row['path'])==row;return row
def load(p):return json.loads(Path(p).read_bytes())
def write(name,data):
 p=OUT/name;assert not p.exists();p.write_text(json.dumps(data,indent=2)+'\n');p.chmod(0o444);return binding(p)

safe_path=Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch15.json')
safe_binding=binding(safe_path);assert safe_binding['bytes']==1962 and safe_binding['sha256']=='644b9afe894a710251bcf0780ac67bc4eb6c0a197f8d73656761ea3ddd80e879'
safe=load(safe_path);private=check(safe['private_inventory_binding']);script=check(safe['recovery_script_binding']);log=check(safe['terminal_log_binding'])
assert stat.S_IMODE(Path(private['path']).stat().st_mode)==0o600
assert stat.S_IMODE(Path(private['path']).parent.stat().st_mode)==0o700
records=load(private['path'])['records'];assert len(records)==1
record=records[0];name=Path(record['original_namespace']).name
assert name=='7a5f87608714acdd' and Path(record['original_namespace']).parent==Path('/workspace/actions-cloud/robocorp/temp')
assert record['expanded_removed'] and record['archive_verified_before_original_removal'] and not Path(record['original_namespace']).exists()
archive=Path(record['archive']);assert archive.parent==Path(private['path']).parent and archive.name==name+'.tar.gz'
assert not archive.is_symlink() and stat.S_IMODE(archive.stat().st_mode)==0o600
assert archive.stat().st_size==record['archive_bytes'] and sha(archive)==record['archive_sha256']
inventory=record['inventory'];assert len(inventory)==record['verified_members']==safe['recorded_members']==15082
seen=set();payloads={};hardlinks={};counts={'file':0,'directory':0,'symlink':0,'fifo':0,'hardlink_headers':0};root_header=0;recycle=False;logical_bytes=0
started=time.monotonic()
with gzip.open(archive,'rb') as compressed:
 with tarfile.open(fileobj=compressed,mode='r|') as tf:
  for member in tf:
   if member.name==name:assert member.isdir();root_header+=1;continue
   assert member.name.startswith(name+'/')
   relative=member.name[len(name)+1:];path=PurePosixPath(relative)
   assert relative and not path.is_absolute() and '..' not in path.parts and relative not in seen and relative in inventory
   seen.add(relative);row=inventory[relative]
   assert member.mode==row['mode'] and member.uid==row['uid'] and member.gid==row['gid']
   kind=row['kind'];counts[kind]+=1
   if kind=='file':
    if member.islnk():
     assert member.linkname.startswith(name+'/');target=member.linkname[len(name)+1:];p=PurePosixPath(target)
     assert target and not p.is_absolute() and '..' not in p.parts and target in inventory and inventory[target]['kind']=='file'
     hardlinks[relative]=target;counts['hardlink_headers']+=1
    else:
     assert member.isfile();stream=tf.extractfile(member);h=hashlib.sha256();size=0;marker=b''
     for data in iter(lambda:stream.read(1048576),b''):
      h.update(data);size+=len(data)
      if relative=='recycle.now':marker+=data
     assert size==row['bytes'] and h.hexdigest()==row['sha256'];payloads[relative]=(size,h.hexdigest());logical_bytes+=size
     if relative=='recycle.now':assert marker.strip()==b'True';recycle=True
   elif kind=='directory':assert member.isdir()
   elif kind=='symlink':assert member.issym() and member.linkname==row['target']
   elif kind=='fifo':assert member.isfifo()
   else:raise AssertionError('unexpected member kind')
 while compressed.read(1048576):pass
assert root_header==1 and seen==set(inventory) and recycle
for relative in hardlinks:
 target=relative;visited=set()
 while target in hardlinks:
  assert target not in visited;visited.add(target);target=hardlinks[target]
 assert target in payloads and payloads[target]==(inventory[relative]['bytes'],inventory[relative]['sha256'])
 logical_bytes+=inventory[relative]['bytes']
print(json.dumps({'new_members_verified':len(seen),'internal_hardlinks':len(hardlinks),'gzip_EOF_verified':True}),flush=True)

prior_final=Path('/workspace/engineering/capacity-recovery-batch14-independent-review/OWNERFINAL-independent-batch14-archive-preservation-review.json')
prior=load(prior_final);check(prior['owner_final_safe']);check(prior['independent_archive_stream_proof']);check(prior['independent_prior_reference_proof'])
prior_refs=load(prior['independent_prior_reference_proof']['path'])
summaries=prior_refs['prior_summaries13_exact_hash_sizes']+[prior['owner_final_safe']]
archive_rows=[];indices=[]
assert len(summaries)==14
for row in summaries:
 check(row);summary=load(row['path'])
 idx=summary['private_inventory_binding'] if 'private_inventory_binding' in summary else summary['complete_private_inventory'];check(idx);indices.append(idx)
 for a in summary['archives'] if 'archives' in summary else summary['recovery_records']:
  path=Path(a['archive']);assert not path.is_symlink() and stat.S_IMODE(path.stat().st_mode)==0o600
  assert path.stat().st_size==a['archive_bytes'] and sha(path)==a['archive_sha256']
  archive_rows.append({'ordinal':len(archive_rows)+1,'bytes':a['archive_bytes'],'sha256':a['archive_sha256']})
assert len(indices)==14 and len(archive_rows)==33
review_refs=prior_refs['prior_review_bindings_exact']+[binding(prior_final),prior['independent_archive_stream_proof'],prior['independent_prior_reference_proof']]
for row in review_refs:check(row)
runner=check(prior_refs['original_V5runner_hash_size_exact'])
assert runner['sha256']=='09cdc6b19f5d3d9cc94fadca23373108868521e0378d33960146b1a8522e88ad'
failed=list(Path('/workspace/actions-cloud/robocorp/temp').glob('563d*'));assert len(failed)==1 and failed[0].is_dir()

prior_stream=load(prior['independent_archive_stream_proof']['path']);check(prior_stream['script'])
def normalized(p):
 t=ast.parse(Path(p).read_bytes());names=set()
 for n in t.body:
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['DEST','STAGE','NAMES']:
   key=n.targets[0].id;names.add(key)
   if key in ['DEST','STAGE']:
    assert isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='Path' and len(n.value.args)==1 and isinstance(n.value.args[0],ast.Constant) and isinstance(n.value.args[0].value,str) and not n.value.keywords
    n.value.args[0].value='NORMALIZED'
   else:
    assert isinstance(n.value,ast.List) and all(isinstance(e,ast.Constant) and isinstance(e.value,str) for e in n.value.elts)
    n.value.elts=[ast.Constant('NORMALIZED')]
 assert names=={'DEST','STAGE','NAMES'};return ast.dump(t,include_attributes=False)
assert normalized(script['path'])==normalized(prior_stream['script']['path'])
code=Path(script['path']).read_text();position=code.index('for name in NAMES:')
assert code.index('verify(archive, name, entries)',position)<code.index('assert inventory(root) == entries',position)<code.index('reject_live_handles(root)',code.index('assert inventory(root) == entries',position))<code.index('shutil.rmtree(root)')
assert "(root / 'recycle.now').read_text().strip() == 'True'" in code
rows=[json.loads(line) for line in Path(log['path']).read_text().splitlines() if line.startswith('{')]
assert len(rows)==1 and rows[0]['completed_namespace_archived']==name and rows[0]['verified_members']==15082
assert 'RECOVERY_COMPLETE_PRIVATE_ARCHIVES_PRESERVE_ALL_MEMBERS' in Path(log['path']).read_text()
patch=check(prior_refs['canonical_exact_accepted_patch'])
assert patch['sha256']=='7d07065b5bb7742698919997c8c6621cc20d00494741eb5365251ffb09f2d208'
paragraph=''.join(line[1:] for line in Path(patch['path']).read_text().splitlines(keepends=True) if line.startswith('+') and not line.startswith('+++'))
assert paragraph in Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
stream_proof=write('independent-one-archive-stream-proof.json',{'status':'PASS_RECORDED_ARCHIVE_MEMBER_PRESERVATION','root_safe':safe_binding,'private_index':private,'script':script,'terminal_log':log,'archive_bytes':record['archive_bytes'],'archive_sha256':record['archive_sha256'],'members':15082,'kinds':counts,'internal_hardlink_payloads_verified':len(hardlinks),'logical_regular_bytes':logical_bytes,'root_header_count_only':root_header,'member_bytes_SHA_size_mode_UID_GID_symlink_targets_exact':True,'gzip_EOF_CRC_ISIZE':True,'recycle_marker_True':True,'expanded_namespace_absent':True,'script_AST_batch14_exact_except_DEST_STAGE_NAMES':True,'retained_script_index_log_order_preserved':'Archive verified/inventory stable/live-handle guard before exact removal in retained script. No independent historical process census replay.','stream_seconds':round(time.monotonic()-started,3),'upstream_disposition':'none'})
prior_proof=write('independent-prior33-archives14-indices-preservation-proof.json',{'prior33_archive_hash_size_mode0600_exact':archive_rows,'prior14_complete_indices_hash_size_exact':indices,'prior14_safe_summary_bindings_exact':summaries,'prior_review_bindings_exact':review_refs,'V5runner_09cdc_exact':runner,'failed563d_exists_only':True,'failed_namespace_contents_state_or_historical_handle_census_not_qualified':True,'canonical7d070_exact_reuse':patch,'current_canonical_paragraph_verbatim':True,'no_prior_archive_extract_or_payload_replay':True,'upstream_disposition':'none'})
final={'schema':'actions-batch15-independent-capacity-preservation-review/v1','status':'GO_SCOPED_BATCH15_RECORDED_ARCHIVE_AND_PRIOR_REFERENCE_PRESERVATION_ONLY','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owner_safe':safe_binding,'independent_archive_stream_proof':stream_proof,'independent_prior_reference_proof':prior_proof,'counts':{'new_archives':1,'new_recorded_members':15082,'new_internal_hardlinks':len(hardlinks),'new_logical_regular_file_bytes':logical_bytes,'prior_archives':33,'prior_indices':14,'prior_summaries':14,'total_retained_archives':34,'total_retained_indices':15},'recorded_member_types':counts,'verified':{'archive_member_byte_SHA_size_mode_UID_GID_symlink_internal_hardlink_content':True,'gzip_EOF_CRC_ISIZE':True,'completion_recycle_True':True,'archive_and_private_index_mode0600_parent0700':True,'expanded_original_absent':True,'batch14_AST_equivalence_except3literal_configuration_values':True,'original_V5runner_09cdc':True,'all_prior_archive_index_safe_summary_review_hashes':True,'failed563d_existence_only':True},'capacity_scope':'Root-recorded free2605572096B is that recovery observation; later environment copies/current free space are not measured or approved by this archive review. Existing /dev/shm mount used; no infrastructure created by reviewer.','limitations':['Retained archive/index/script/log qualification only; no historical expanded filesystem/live-handle census replay','No ACL/xattr/inode/rootmetadata/precise TAR nanosecond timestamp claim','No failed563d contents/state verification or retroactive source/consumer/failed-gate acceptance','No recovery/removal/restore/extraction/copy/installer/actual/native/provider/test/download by reviewer','No private member paths/payloads or oversized inventory keys included in safe receipts'],'documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md','Exact_delta_or_reuse':patch,'Durable_learning':'Same verified7d070 archive/inventory preservation algorithm retains complete recorded member bytes and metadata before exact completed scratch removal, separately preserving failed namespace existence and historical observation limits.','Evidence':'15082 streamed members; internal hardlinks; gzipCRC/ISIZE EOF; all prior33 archives/14 indices/source script/log/summary/review hashes and V5runner; AST exact accepted batch14 algorithm except3config literals.','Stale_or_ambiguous_guidance_removed':'No guidance removed; retained lesson prevents preservation from implying unrecorded metadata, historical full process census or a failed gate PASS.','Remaining_uncertainty':'Historical full handle census, ACL/xattrs/inode/rootmetadata/precise TARmtime and failed563d contents/state remain unqualified. Consumer capacity/serialization separately belongs to root.','Disposition':'Verified exact accepted7d070 paragraph remains verbatim in canonical guide; no cosmetic duplication.'},'upstream_disposition':'none'}
print(json.dumps({'owner_final':write('OWNERFINAL-independent-batch15-preservation-review.json',final)}),flush=True)
