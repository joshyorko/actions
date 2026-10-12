import ast,datetime,gzip,hashlib,json,os,stat,subprocess,tarfile,time
from pathlib import Path,PurePosixPath
OUT=Path('/workspace/engineering/capacity-recovery-batch17-independent-review')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for data in iter(lambda:f.read(1048576),b''):h.update(data)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(row):assert bind(row['path'])==row;return row
def load(p):return json.loads(Path(p).read_bytes())
def write(n,d):
 p=OUT/n
 with p.open('x') as f:f.write(json.dumps(d,indent=2)+'\n')
 p.chmod(0o444);return bind(p)
safe_path=Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch17.json');safe_binding=bind(safe_path);assert safe_binding['bytes']==2870 and safe_binding['sha256']=='54a76a7d0ea2f325fe2486a3e33487799de7bd04c29b6ab2d1daa36b73c763d2'
safe=load(safe_path);private=check(safe['private_inventory_binding']);script=check(safe['recovery_script_binding']);log=check(safe['terminal_log_binding']);assert script['sha256']=='0e7fb3c7bada95d89631beee6fe99dfceca5a4c02d96426b6605d4645f213831'
assert stat.S_IMODE(Path(private['path']).stat().st_mode)==0o600 and stat.S_IMODE(Path(private['path']).parent.stat().st_mode)==0o700
records=load(private['path'])['records'];names=['05b825944b9d3b9c','26f60264fb01e721','990480ceb42cd661'];assert len(records)==3 and [Path(r['original_namespace']).name for r in records]==names
results=[];started=time.monotonic()
for record,summary,name in zip(records,safe['archives'],names):
 assert {k:v for k,v in record.items() if k!='inventory'}==summary
 assert Path(record['original_namespace']).parent==Path('/workspace/actions-cloud/robocorp/temp') and not Path(record['original_namespace']).exists() and record['expanded_removed'] and record['archive_verified_before_original_removal']
 archive=Path(record['archive']);assert archive.parent==Path(private['path']).parent and archive.name==name+'.tar.gz' and not archive.is_symlink() and stat.S_IMODE(archive.stat().st_mode)==0o600
 assert archive.stat().st_size==record['archive_bytes'] and sha(archive)==record['archive_sha256']
 inv=record['inventory'];assert len(inv)==record['verified_members'];seen=set();payloads={};links={};root=0;recycle=False;counts={'file':0,'directory':0,'symlink':0,'fifo':0,'hardlink_headers':0};logical=0
 with gzip.open(archive,'rb') as compressed:
  with tarfile.open(fileobj=compressed,mode='r|') as tf:
   for member in tf:
    if member.name==name:assert member.isdir();root+=1;continue
    assert member.name.startswith(name+'/');relative=member.name[len(name)+1:];p=PurePosixPath(relative)
    assert relative and not p.is_absolute() and '..' not in p.parts and relative not in seen and relative in inv
    seen.add(relative);row=inv[relative];assert member.mode==row['mode'] and member.uid==row['uid'] and member.gid==row['gid'];kind=row['kind'];counts[kind]+=1
    if kind=='file':
     if member.islnk():
      assert member.linkname.startswith(name+'/');target=member.linkname[len(name)+1:];p=PurePosixPath(target);assert target and not p.is_absolute() and '..' not in p.parts and target in inv and inv[target]['kind']=='file';links[relative]=target;counts['hardlink_headers']+=1
     else:
      assert member.isfile();stream=tf.extractfile(member);h=hashlib.sha256();size=0;marker=b''
      for data in iter(lambda:stream.read(1048576),b''):
       h.update(data);size+=len(data)
       if relative=='recycle.now':marker+=data
      assert size==row['bytes'] and h.hexdigest()==row['sha256'];payloads[relative]=(size,h.hexdigest());logical+=size
      if relative=='recycle.now':assert marker.strip()==b'True';recycle=True
    elif kind=='directory':assert member.isdir()
    elif kind=='symlink':assert member.issym() and member.linkname==row['target']
    elif kind=='fifo':assert member.isfifo()
    else:raise AssertionError('unsupported recorded type')
  while compressed.read(1048576):pass
 assert root==1 and seen==set(inv) and recycle
 for relative in links:
  target=relative;visited=set()
  while target in links:assert target not in visited;visited.add(target);target=links[target]
  assert target in payloads and payloads[target]==(inv[relative]['bytes'],inv[relative]['sha256']);logical+=inv[relative]['bytes']
 results.append({'ordinal':len(results)+1,'archive_sha256':record['archive_sha256'],'archive_bytes':record['archive_bytes'],'members':len(seen),'kinds':counts,'logical_bytes':logical,'all_recorded_payload_sha_size_mode_uid_gid_symlink_and_hardlink_content_exact':True,'completion_marker_True':True,'gzip_EOF_CRC_ISIZE':True,'expanded_namespace_absent':True})
 print(json.dumps({'verified_archive_ordinal':len(results),'members':len(seen),'hardlinks':len(links)}),flush=True)
assert sum(r['members'] for r in results)==safe['recorded_members']==14076
prior_final=Path('/workspace/engineering/capacity-recovery-batch16-independent-review/OWNERFINAL-independent-batch16-preservation-review.json');prior=load(prior_final)
for key in ['owner_safe','current_Linux_v5_preservation','independent_archive_stream_proof','independent_prior_reference_proof']:check(prior[key])
prior_refs=load(prior['independent_prior_reference_proof']['path']);summaries=prior_refs['prior15_safe_summary_bindings_exact']+[prior['owner_safe']];assert len(summaries)==16
prior_archive_count=0;indices=[]
for row in summaries:
 check(row);d=load(row['path']);idx=d.get('private_inventory_binding',d.get('complete_private_inventory'));check(idx);indices.append(idx)
 for a in d.get('archives',d.get('recovery_records')):
  p=Path(a['archive']);assert not p.is_symlink() and stat.S_IMODE(p.stat().st_mode)==0o600 and p.stat().st_size==a['archive_bytes'] and sha(p)==a['archive_sha256'];prior_archive_count+=1
assert prior_archive_count==35
for row in prior_refs['prior_review_bindings_exact']:check(row)
check(prior_refs['V5runner_09cdc_exact']);failed=list(Path('/workspace/actions-cloud/robocorp/temp').glob('563d*'));assert len(failed)==1 and failed[0].is_dir()
consumer=load(prior['current_Linux_v5_preservation']['path'])
for k in ['owner','independent_actual','preexecution_owner']:check(consumer[k])
for row in consumer['original_actual_measurement_bindings']+consumer['preexecution_refs']:check(row)
assert len(consumer['original_actual_measurement_bindings'])==16 and len(consumer['preexecution_refs'])==153
prior_stream=load(prior['independent_archive_stream_proof']['path']);check(prior_stream['script'])
def norm(p):
 t=ast.parse(Path(p).read_bytes());keys=set()
 for n in t.body:
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['DEST','STAGE','NAMES']:
   key=n.targets[0].id;keys.add(key)
   if key=='NAMES':assert isinstance(n.value,ast.List) and all(isinstance(x,ast.Constant) and isinstance(x.value,str) for x in n.value.elts);n.value.elts=[ast.Constant('NORMALIZED')]
   else:assert isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='Path' and len(n.value.args)==1 and isinstance(n.value.args[0],ast.Constant) and not n.value.keywords;n.value.args[0].value='NORMALIZED'
 assert keys=={'DEST','STAGE','NAMES'};return ast.dump(t,include_attributes=False)
assert norm(script['path'])==norm(prior_stream['script']['path'])
code=Path(script['path']).read_text();pos=code.index('for name in NAMES:');assert code.index('verify(archive, name, entries)',pos)<code.index('assert inventory(root) == entries',pos)<code.index('reject_live_handles(root)',code.index('assert inventory(root) == entries',pos))<code.index('shutil.rmtree(root)')
rows=[json.loads(l) for l in Path(log['path']).read_text().splitlines() if l.startswith('{')];assert len(rows)==3 and [x['completed_namespace_archived'] for x in rows]==names and [x['verified_members'] for x in rows]==[11643,322,2111]
assert 'RECOVERY_COMPLETE_PRIVATE_ARCHIVES_PRESERVE_ALL_MEMBERS' in Path(log['path']).read_text()
light=check({'path':'/workspace/engineering/pr312-actual309-refresh/OWNERFINAL-pr312-actual309-refresh-LIGHT.json','bytes':13643,'sha256':'7606ad32b0f85aa7ad835f0970aeebddf7c750908a7426d16fb0f219db4ecef0'});light_data=load(light['path'])
for row in light_data['immutable_evidence_bindings']:check(row)
check(light_data['prior_SOURCEFINAL']);old=load(light_data['prior_SOURCEFINAL']['path'])
for row in old['immutable_evidence_bindings']:check(row)
r=Path('/workspace/engineering/runtime-checkout-eol');git=lambda *a:subprocess.check_output(['git',*a],cwd=r)
assert git('status','--porcelain')==b'' and git('rev-parse','HEAD').decode().strip()==light_data['head']=='77065131a0aee63d2b1f8621476374bdde3c7b65' and git('rev-parse','HEAD^{tree}').decode().strip()==light_data['tree']=='edf1801e565692fb3f07b809b3a95b27981fe2fe'
count=0
for rec in git('ls-tree','-rz','HEAD').split(b'\0'):
 if rec:
  meta,p=rec.split(b'\t');mode,kind,blob=meta.decode().split();p=r/p.decode();body=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==blob and bool(p.stat().st_mode&0o111)==(mode=='100755');count+=1
assert count==1423
patch=check(prior_refs['canonical7d070_exact_reuse']);paragraph=''.join(l[1:] for l in Path(patch['path']).read_text().splitlines(keepends=True) if l.startswith('+') and not l.startswith('+++'));assert paragraph in Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
proof=write('independent-three-archive-stream-and-preservation-proof.json',{'status':'PASS_SCOPED_RECORDED_ARCHIVE_MEMBER_AND_REFERENCE_PRESERVATION','safe_owner':safe_binding,'private_index':private,'recovery_script':script,'terminal_log':log,'three_archive_results':results,'new_recorded_members':14076,'prior_archives_hash_size_mode_exact':35,'prior_indices_hash_size_exact':16,'Linux_v5_actual16_and_preexecution153_bindings_exact':True,'original_V5runner09cdc_exact':True,'failed563d_existence_only':True,'batch16_recovery_algorithm_AST_exact_except_DEST_STAGE_NAMES':True,'retained_script_order_archive_fullinventory_reinventory_live_guard_before_removal':True,'source312_LIGHT':light,'source312_current1423_Git_FS_exec_and_old62_refs_exact':True,'canonical7d070_verbatim_reuse':patch,'elapsed_seconds':round(time.monotonic()-started,3),'no_archive_extraction_mutation_source_or_gate_execution':True})
final={'schema':'actions-batch17-independent-capacity-preservation-review/v1','status':'GO_SCOPED_BATCH17_PRESERVATION_PREREQUISITE_ONLY_NO_FULL_AUTHORIZATION','safe_owner':safe_binding,'independent_proof':proof,'counts':{'new_archives':3,'new_members':14076,'prior_archives':35,'prior_indices':16,'total_preserved_archives':38,'total_preserved_indices':17},'all_recorded_bytes_modes_UID_GID_symlinks_internal_hardlinks_and_gzip_EOF_CRC_ISIZE':True,'all_three_completion_markers_True':True,'all_three_expanded_names_absent':True,'source312_current770_treeedf180_clean1423_exact':True,'current_workspace_free_bytes':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize,'limitations':['No historical expanded filesystem or complete live-handle census replay','No ACL/xattr/inode/rootmetadata/precise TAR nanosecond timestamps claim','Failed563d existence only; no failure state or contents qualification','Consumer installed temp already removed; original observations hash-preserved only','No restore/extraction/removal/archive mutation/source edit/gates/actual/native execution','Root fresh capacity/serialization/full authorization remains separate'],'Documentation improvement':{'Canonical file changed or proposed':'docs/skills/repository-operations.md; exact accepted7d070 paragraph verified verbatim, no cosmetic duplicate','Durable learning captured':'Require complete recorded archive bytes/metadata and resolved hardlink content before completed scratch removal; preserve failed and historical observation limits separately','Evidence':'14076 streamed members/gzip EOF and AST-equivalent17 algorithm;35prior archives/16indices,169Linuxconsumer references,312current1423 and62oldsource refs exact','Stale or ambiguous guidance removed':'No archive preservation equated with full handle census, failed-gate acceptance, current consumer installation or full-test authorization','Remaining uncertainty':'Historical ACL/xattrs/inodes/rootmetadata/precise timestamps/live handles and failed563d contents remain unqualified; root owns full capacity/serialization authorization'},'upstream_disposition':'none'}
print(json.dumps({'OWNERFINAL':write('OWNERFINAL-independent-batch17-preservation-review.json',final)}),flush=True)
