from pathlib import Path,PurePosixPath
import hashlib,json,os,stat,tarfile,time,gzip,ast
D=Path('/workspace/engineering/capacity-recovery-batch14-independent-review');R=D/'independent-two-archive-stream-proof.json';started=time.monotonic()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def binding(p):return {'path':str(p),'bytes':Path(p).stat().st_size,'sha256':sha(p)}
private=Path('/dev/shm/actions-completed-scratch-recovery-batch14/private-complete-inventory-and-recovery.json');log=Path('/tmp/actions-capacity-recovery-batch14.log');assert 'RECOVERY_COMPLETE_PRIVATE_ARCHIVES_PRESERVE_ALL_MEMBERS' in log.read_text();summary={'archives':[]}
assert stat.S_IMODE(private.stat().st_mode)==0o600 and stat.S_IMODE(private.parent.stat().st_mode)==0o700
records=json.loads(private.read_text())['records'];assert len(records)==2
expected_names={'6626d6008afef362','1748c6a354c4f0e0'}
assert {Path(r['original_namespace']).name for r in records}==expected_names
counts=[];total=0
for record in records:
 root=Path(record['original_namespace']);name=root.name;assert root.parent==Path('/workspace/actions-cloud/robocorp/temp') and not root.exists() and record['expanded_removed'] and record['archive_verified_before_original_removal']
 archive=Path(record['archive']);assert archive.parent==private.parent and archive.name==name+'.tar.gz' and not archive.is_symlink() and stat.S_IMODE(archive.stat().st_mode)==0o600
 assert archive.stat().st_size==record['archive_bytes'] and sha(archive)==record['archive_sha256']
 summary['archives'].append({k:record[k] for k in ('archive_bytes','archive_sha256','verified_members','archive_verified_before_original_removal','expanded_removed')})
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
 counts.append({'archive_ordinal':len(counts)+1,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'root_directory_header':root_seen,'members_verified':len(inventory),'kinds':types,'resolved_internal_hardlink_data_verified':len(links),'logical_regular_file_bytes_verified':bytes_verified,'completed_recycle_marker_verified':True,'expanded_namespace_absent':True})
 with gzip.open(archive,'rb') as gf:
  while gf.read(1024*1024):pass
 counts[-1]['gzip_EOF_CRC_ISIZE_verified']=True
 total+=len(inventory)
 print(json.dumps({'verified_archive_ordinal':len(counts),'members':len(inventory),'internal_hardlinks':len(links)}),flush=True)
assert total==sum(r["verified_members"] for r in records)

assert total==30318
root_safe=Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch14.json')
assert root_safe.stat().st_size==2420 and sha(root_safe)=='88a81e8424dec8d5ef57b5ea37422273d6e1a24f90082f25630f177c9dd04619'
safe=json.loads(root_safe.read_text())
assert binding(private)==safe['private_inventory_binding']
script=Path('/tmp/actions-capacity-recovery-batch14.py'); assert binding(script)==safe['recovery_script_binding']
assert binding(log)==safe['terminal_log_binding']
priorD=Path('/workspace/engineering/capacity-recovery-batch13-independent-review')
priorFinal=priorD/'independent-frozen-batch13-archive-preservation-review.json'
assert sha(priorFinal)=='ec86ff74f126f71ecac8e760300c454ace4aa55d1089b9b02b826b9522152488'
prior=json.loads(priorFinal.read_text());assert binding(prior['recovery_script']['path'])==prior['recovery_script']
def norm(p):
 t=ast.parse(Path(p).read_bytes()); config={}
 for n in t.body:
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['DEST','STAGE','NAMES']:
   name=n.targets[0].id;config[name]=ast.dump(n.value,include_attributes=False)
   if name in ['DEST','STAGE']:
    assert isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='Path' and len(n.value.args)==1 and isinstance(n.value.args[0],ast.Constant) and isinstance(n.value.args[0].value,str) and not n.value.keywords
    n.value.args[0].value='NORMALIZED'
   else:
    assert isinstance(n.value,ast.List) and all(isinstance(a,ast.Constant) and isinstance(a.value,str) for a in n.value.elts)
    n.value.elts=[ast.Constant('NORMALIZED')]
 assert set(config)=={'DEST','STAGE','NAMES'}
 return ast.dump(t,include_attributes=False)
assert norm(script)==norm(prior['recovery_script']['path'])
source=script.read_text();start=source.index('for name in NAMES:')
assert source.index('verify(archive, name, entries)',start)<source.index('assert inventory(root) == entries',start)<source.index('reject_live_handles(root)',source.index('assert inventory(root) == entries',start))<source.index('shutil.rmtree(root)')
assert "(root / 'recycle.now').read_text().strip() == 'True'" in source
rows=[json.loads(line) for line in log.read_text().splitlines() if line.startswith('{')];assert len(rows)==2
for record,row in zip(records,rows):
 assert row['completed_namespace_archived']==Path(record['original_namespace']).name and row['verified_members']==record['verified_members'] and row['archive_bytes']==record['archive_bytes']
proof={'verdict':'PASS_RECORDED_ARCHIVE_PRESERVATION_ONLY','owner_final_safe':binding(root_safe),'private_index':binding(private),'script':binding(script),'terminal_log':binding(log),'archives':counts,'total_recorded_members':total,'AST_batch13_exact_except_DEST_STAGE_NAMES_constant_values':True,'historical_ordering_preserved_in_script_index_and_log':True,'historical_ordering_limit':'After-removal retained proof; no independent historical expanded filesystem or process census replay','private_index_mode':'0600','archive_parent_mode':'0700','review_seconds':round(time.monotonic()-started,3),'upstream_disposition':'none'}
R.write_text(json.dumps(proof,indent=2)+'\n');R.chmod(0o600)
print(json.dumps({'archive_stream_proof':binding(R)}),flush=True)
# Rehash prior13 safe summaries, retained archives and complete index bytes only.
priorProof=priorD/'independent-prior29-archives12-indices-and-original-reference-proof.json';assert binding(priorProof)==prior['independent_prior_reference_proof']
pp=json.loads(priorProof.read_text()); assert len(pp['prior_safe_summaries_exact_retained_hashes'])==12
summaries=pp['prior_safe_summaries_exact_retained_hashes']+[prior['owner_final_safe_summary']]
indices=[];archiveSummaries=[]
for e in summaries:
 assert binding(e['path'])==e
 j=json.loads(Path(e['path']).read_text()); ik='private_inventory_binding' if 'private_inventory_binding' in j else 'complete_private_inventory';ak='archives' if 'archives' in j else 'recovery_records'
 idx=j[ik];assert binding(idx['path'])==idx;indices.append(idx)
 for a in j[ak]:
  ap=Path(a['archive']);assert not ap.is_symlink() and stat.S_IMODE(ap.stat().st_mode)==0o600 and ap.stat().st_size==a['archive_bytes'] and sha(ap)==a['archive_sha256']
  archiveSummaries.append({'archive_ordinal':len(archiveSummaries)+1,'bytes':a['archive_bytes'],'sha256':a['archive_sha256']})
assert len(indices)==13 and len(archiveSummaries)==31
reviewRefs=pp['prior_review_binding_checks']+[binding(priorFinal),prior['independent_archive_stream_proof'],prior['independent_prior_reference_proof']]
for e in reviewRefs:assert binding(e['path'])==e
assert binding(prior['private_complete_index']['path'])==prior['private_complete_index']
runner=prior['prior_immutable_baselines']['original_V5runner'];assert binding(runner['path'])==runner
failed=list(Path('/workspace/actions-cloud/robocorp/temp').glob('563d*'));assert len(failed)==1 and failed[0].is_dir()
patch=Path('/workspace/engineering/capacity-recovery-independent-review/canonical-completed-scratch-preservation-proposed.patch');assert sha(patch)=='7d07065b5bb7742698919997c8c6621cc20d00494741eb5365251ffb09f2d208'
paragraph=''.join(line[1:] for line in patch.read_text().splitlines(keepends=True) if line.startswith('+') and not line.startswith('+++'))
guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md');assert paragraph in guide.read_text()
refs={'prior_archives31_exact_hash_size_mode0600':archiveSummaries,'prior_indices13_exact_hash_sizes':indices,'prior_summaries13_exact_hash_sizes':summaries,'prior_review_bindings_exact':reviewRefs,'original_V5runner_hash_size_exact':runner,'failed563d_exists_only':True,'failed_scope':'Directory existence only; no baseline contents/state/SHA claim or failed gate reclassification','canonical_exact_accepted_patch':binding(patch),'canonical_verbatim_current_guide':True,'no_old_archives_extracted_or_payload_replayed':True,'upstream_disposition':'none'}
refPath=D/'independent-prior31-archives13-indices-preservation-proof.json';refPath.write_text(json.dumps(refs,indent=2)+'\n');refPath.chmod(0o600)
final={'schema':'actions.independent-completed-scratch-batch14-preservation-review/v1','verdict':'GO_SCOPED_BATCH14_ARCHIVE_AND_PRIOR_REFERENCE_PRESERVATION_ONLY','owner_final_safe':binding(root_safe),'independent_archive_stream_proof':binding(R),'independent_prior_reference_proof':binding(refPath),'counts':{'new_archives':2,'new_members':total,'new_internal_hardlinks':sum(a['resolved_internal_hardlink_data_verified'] for a in counts),'new_logical_regular_bytes':sum(a['logical_regular_file_bytes_verified'] for a in counts),'prior_archives':31,'prior_indices':13,'prior_summaries':13,'total_retained_archives':33,'total_retained_indices':14},'safe_archive_aggregates':counts,'verified':{'gzip_EOF_CRC_ISIZE':True,'all30318_unique_recorded_members':True,'bytes_size_SHA_mode_UID_GID':True,'symlink_targets_exact_without_dereference':True,'internal_hardlink_payloads_same_archive':True,'completion_markers_True':True,'two_expanded_namespaces_absent':True,'AST_same_batch13_except_three_allowed_constants':True,'existing_mount_only':True,'private_index_and_archive_modes0600_parent0700':True,'prior31_archives13_indices_and_safe_receipts_exact':True,'original_V5runner09cdc_exact':True,'failed563d_exists_only':True},'limitations':['After-removal retained archive/index/source/log qualification; no historical expanded filesystem or complete live handle census replay','No ACL/xattr/inode/rootmetadata/precise TAR mtime qualification','No source/native/consumer/cache/venv/provider/release or original failed gate admission','No recovery/deletion/restore/extraction/download/gate/native/source/ref operation by reviewer; own safe review outputs only','No member inventory keys or private payloads included in safe receipts'],'documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md','Exact_delta_disposition':'Accept existing exact7d070 paragraph verbatim in owning guide; same verified algorithm gives no new durable lesson requiring cosmetic duplication','Accepted_patch':binding(patch),'Durable_learning_captured':'Retain full recorded byte/member metadata archives and inventories before exact completed scratch removal; keep failed namespaces and historical process observations separate','Evidence':'30318 members including internal hardlinks and gzipEOF; complete byte/mode/UID/GID/symlink comparisons; script AST parity batch13; prior31 archive/13 index/safe-summary hashes; V5runner exact','Stale_or_ambiguous_guidance_removed':'No guidance removed; retained paragraph prevents archive preservation from implying unrecorded metadata, historical full handle census or failed gate PASS','Remaining_uncertainty':'Historical full process census, ACL/xattrs/inode/rootmetadata/precise TARmtime and failed563d contents/state remain unqualified'},'upstream_disposition':'none'}
f=D/'OWNERFINAL-independent-batch14-archive-preservation-review.json';assert not f.exists();f.write_text(json.dumps(final,indent=2)+'\n');f.chmod(0o600);print(json.dumps({'owner_final':binding(f)}),flush=True)
