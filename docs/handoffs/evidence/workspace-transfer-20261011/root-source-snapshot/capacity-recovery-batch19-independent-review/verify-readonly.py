import ast,datetime,gzip,hashlib,json,os,stat,subprocess,tarfile,time
from collections import defaultdict
from pathlib import Path,PurePosixPath
O=Path(__file__).parent
started=time.monotonic()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for z in iter(lambda:f.read(1048576),b''):h.update(z)
 return h.hexdigest()
def bind(p):p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def check(r):assert bind(r['path'])=={k:r[k] for k in ('path','bytes','sha256')},r['path'];return r
def load(p):return json.loads(Path(p).read_bytes())
def freeze(n,x):
 p=O/n
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
 p.chmod(0o600);return bind(p)
safe=Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch19.json');assert sha(safe)=='6b7998bff1c7c0b2ccada06452c6e7eabae4c20c47b5027331f0b16fbda3377a' and safe.stat().st_size==1868
s=load(safe);check(s['private_complete_inventory']);check(s['actual_script']);assert s['actual_script']['sha256']=='48fd7e4c79e55b80ceda0b63c1d1da87feeb368cefee265d5c12bad6ad940840'
p=Path(s['private_complete_inventory']['path']);assert stat.S_IMODE(p.stat().st_mode)==0o600 and stat.S_IMODE(p.parent.stat().st_mode)==0o700
records=load(p)['records'];assert len(records)==1;r=records[0];name='c3b676a701cf3ae2';assert r['original_namespace']==str(Path('/workspace/actions-cloud/robocorp/temp')/name)==s['original_namespace'] and r['expanded_removed'] and r['archive_verified_before_original_removal'] and not Path(r['original_namespace']).exists()
a=Path(r['archive']);assert a.parent==p.parent and a.name==name+'.tar.gz' and not a.is_symlink() and stat.S_IMODE(a.stat().st_mode)==0o600
assert bind(a)==s['archive'] and a.stat().st_size==r['archive_bytes'] and sha(a)==r['archive_sha256']
inv=r['inventory'];assert len(inv)==r['verified_members']==s['verified_members']==16121
seen=set();payload={};links={};counts={'file':0,'directory':0,'symlink':0,'fifo':0,'hardlink_headers':0};rootheaders=0;recycle=False;logical=0
with gzip.open(a,'rb') as gz:
 with tarfile.open(fileobj=gz,mode='r|') as tf:
  for m in tf:
   if m.name==name:assert m.isdir();rootheaders+=1;continue
   assert m.name.startswith(name+'/');rel=m.name[len(name)+1:];parts=PurePosixPath(rel);assert rel and not parts.is_absolute() and '..' not in parts.parts and rel not in seen and rel in inv;seen.add(rel);row=inv[rel]
   assert (m.mode,m.uid,m.gid)==(row['mode'],row['uid'],row['gid']);kind=row['kind'];counts[kind]+=1
   if kind=='file':
    if m.islnk():
     assert m.linkname.startswith(name+'/');target=m.linkname[len(name)+1:];pt=PurePosixPath(target);assert target and not pt.is_absolute() and '..' not in pt.parts and target in inv and inv[target]['kind']=='file';links[rel]=target;counts['hardlink_headers']+=1
    else:
     assert m.isfile();h=hashlib.sha256();size=0;marker=b'';stream=tf.extractfile(m)
     for z in iter(lambda:stream.read(1048576),b''):
      h.update(z);size+=len(z)
      if rel=='recycle.now':marker+=z
     assert size==row['bytes'] and h.hexdigest()==row['sha256'];payload[rel]=(size,h.hexdigest());logical+=size
     if rel=='recycle.now':assert marker.strip()==b'True';recycle=True
   elif kind=='directory':assert m.isdir()
   elif kind=='symlink':assert m.issym() and m.linkname==row['target']
   elif kind=='fifo':assert m.isfifo()
   else:raise AssertionError('unapproved type')
 while gz.read(1048576):pass
assert rootheaders==1 and seen==set(inv) and recycle
for rel in links:
 target=rel;visited=set()
 while target in links:assert target not in visited;visited.add(target);target=links[target]
 assert target in payload and payload[target]==(inv[rel]['bytes'],inv[rel]['sha256']);logical+=inv[rel]['bytes']
print('PASS_NEW_ARCHIVE_16121_RECORDED_MEMBERS_GZIP_EOF',flush=True)
parent=s['algorithm_parent'];assert sha(parent['path'])==parent['sha256']
def normscript(path):
 t=ast.parse(Path(path).read_bytes());configs=set();count=0
 for n in t.body:
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in {'DEST','STAGE','NAMES'}:
   k=n.targets[0].id;configs.add(k)
   if k=='NAMES':assert isinstance(n.value,ast.List);n.value.elts=[ast.Constant('NORMALIZED')]
   else:assert isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='Path';n.value.args=[ast.Constant('NORMALIZED')]
  else:count+=1
 assert configs=={'DEST','STAGE','NAMES'};return ast.dump(t,include_attributes=False),count
assert normscript(s['actual_script']['path'])==normscript(parent['path']);assert normscript(parent['path'])[1]==16
code=Path(s['actual_script']['path']).read_text();i=code.index('for name in NAMES:');assert code.index('verify(archive, name, entries)',i)<code.index('assert inventory(root) == entries',i)<code.index('reject_live_handles(root)',code.index('assert inventory(root) == entries',i))<code.index('shutil.rmtree(root)')
# Build all prior safe summary/index/archive bindings from the immutable accepted chain.
prior16=load('/workspace/engineering/capacity-recovery-batch16-independent-review/OWNERFINAL-independent-batch16-preservation-review.json');pr=load(prior16['independent_prior_reference_proof']['path'])
summaries=pr['prior15_safe_summary_bindings_exact']+[prior16['owner_safe']]
for n in [17,18]:summaries.append(bind(f'/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch{n}.json'))
assert len(summaries)==18
prior_archives=0;indices=[];prior_safe_rows=[]
for row in summaries:
 check(row);x=load(row['path']);idx=x.get('private_inventory_binding',x.get('complete_private_inventory'));check(idx);assert stat.S_IMODE(Path(idx['path']).stat().st_mode)==0o600;indices.append(idx);prior_safe_rows.append(row)
 for ar in x.get('archives',x.get('recovery_records')):
  path=Path(ar['archive']);assert not path.is_symlink() and stat.S_IMODE(path.stat().st_mode)==0o600 and path.stat().st_size==ar['archive_bytes'] and sha(path)==ar['archive_sha256'];prior_archives+=1
assert prior_archives==39
for row in pr['prior_review_bindings_exact']:check(row)
for n in [16,17,18]:
 q=Path(f'/workspace/engineering/capacity-recovery-batch{n}-independent-review/OWNERFINAL-independent-batch{n}-preservation-review.json');qr=load(q)
 for key in ['owner_safe','independent_archive_stream_proof','independent_prior_reference_proof','current_Linux_v5_preservation','safe_owner','independent_proof']:
  if key in qr:check(qr[key])
check(pr['V5runner_09cdc_exact']);assert pr['V5runner_09cdc_exact']['sha256']=='09cdc6b19f5d3d9cc94fadca23373108868521e0378d33960146b1a8522e88ad'
consumer=load(prior16['current_Linux_v5_preservation']['path'])
for key in ['owner','independent_actual','preexecution_owner']:check(consumer[key])
for row in consumer['original_actual_measurement_bindings']+consumer['preexecution_refs']:check(row)
assert len(consumer['original_actual_measurement_bindings'])==16 and len(consumer['preexecution_refs'])==153
failed=list(Path('/workspace/actions-cloud/robocorp/temp').glob('563d*'));assert len(failed)==1 and failed[0].is_dir()
print('PASS_PRIOR39_ARCHIVES18_INDICES_AND_FROZEN_REFS',flush=True)
# Recompute entire relocated default cache using only its reviewed pure helper definitions, never the old verifier main.
cache_script=Path('/workspace/engineering/root-failed300-default-cache-independent-actual-review/verify-readonly-actual.py');tree=ast.parse(cache_script.read_bytes());helpers=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'info','inventory','norm','partition'}];assert len(helpers)==4;ns={'Path':Path,'stat':stat,'os':os,'sha':sha,'defaultdict':defaultdict};exec(compile(ast.Module(body=helpers,type_ignores=[]),str(cache_script)+':pure-readonly-inventory-functions', 'exec'),ns)
cache_owner=load('/workspace/engineering/root-failed300-default-cache-preservation-actual/OWNERFINAL-root-whole-default-cache-preservation-actual.json');check(cache_owner['private_complete_inventories']);old=load(cache_owner['private_complete_inventories']['path'])['frozen_original'];dest=Path(cache_owner['physical_destination']);source=Path('/home/agent/.robocorp/pkgs');assert source.is_symlink() and os.readlink(source)==str(dest)
current=ns['inventory'](dest);assert ns['norm'](current)==ns['norm'](old) and ns['partition'](current)==ns['partition'](old)==[];assert len(current['entries'])==416
assert not os.path.lexists(cache_owner['removed_only_verified_expanded_backup'])
# Current source300 and old refs/input scope only; no writer-owned worktree replay.
full=Path(s['full_source_receipt']['path']);assert sha(full)==s['full_source_receipt']['sha256'];f=load(full)
for row in f['all110_original_and_LIGHT_references']:check(row)
proof=load(f['complete1423_body_Git_FS_mode_inventory']['path']);R=Path('/workspace/engineering/pr300');assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD']).decode().strip()==f['head'];assert subprocess.check_output(['git','-C',str(R),'status','--porcelain'])==b''
for row in proof['all1423']:
 path=R/row['path'];z=os.readlink(path).encode() if row['mode']=='120000' else path.read_bytes();assert len(z)==row['bytes'] and hashlib.sha256(z).hexdigest()==row['sha256'];assert row['mode']=='120000' or bool(path.stat().st_mode&0o111)==(row['mode']=='100755')
prepared=load(f['prepared_inputs']['record']['path']);assert len(prepared['all30_current_inputs_exact_prepared_Git_bytes'])==30
for path,h in prepared['all30_current_inputs_exact_prepared_Git_bytes'].items():assert sha(R/path)==h
for pkg,row in prepared['five_own_environment_configs'].items():assert sha(R/pkg/'.venv/pyvenv.cfg')==row['config_sha256'] and str((R/pkg/'.venv/bin/python').resolve())==row['python_resolved']
helpers=load('/workspace/actions-cloud/receipts/pr305-runner/frozen-helper-bindings.json')
for row in helpers.values():assert sha(row['snapshot_path'])==row['sha256'] and stat.S_IMODE(Path(row['snapshot_path']).stat().st_mode)==0o444
patch=check(pr['canonical7d070_exact_reuse']);paragraph=''.join(line[1:] for line in Path(patch['path']).read_text().splitlines(keepends=True) if line.startswith('+') and not line.startswith('+++'));assert paragraph in Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
r={'schema':'actions-batch19-independent-preservation-review-v1','verdict':'GO_SCOPED_RECORDED_ARCHIVE_AND_RETAINED_PRIOR_PRESERVATION_ONLY','safe_owner':bind(safe),'private_index':s['private_complete_inventory'],'actual_algorithm':s['actual_script'],'algorithm_parent':parent,'archive':s['archive'],'counts':{'new_archives':1,'new_members':16121,'new_kind_counts':counts,'new_logical_file_bytes':logical,'prior_archives_hash_size_mode_exact':39,'prior_indices_hash_size_exact':18,'cumulative_archives':40,'cumulative_indices':19},'verified':{'all_recorded_payload_SHA_size_mode_UID_GID_symlink_and_resolved_hardlink_content':True,'gzip_EOF_CRC_ISIZE':True,'completion_marker_True':True,'private_index0600_parent0700_archive0600':True,'expanded_named_namespace_absent':True,'all16_nonconfig_AST_same_parent_only_DEST_STAGE_NAMES':True,'archive_verification_then_reinventory_then_handle_guard_then_removal_order':True,'original_V5runner09cdc_and_actual16_preexecution153_bindings':True,'failed563d_existence_only':True,'whole_relocated_defaultcache416_current_normalized_bytes_mode_uid_gid_mtime_symlinks_hardlink_partition':True,'source3001423_fs_mode_refs110_inputs30_five_configs_and_helpers0444':True},'limits':['No extraction/copy/removal/gateway/source edits/native/actual/test/retry performed','Historical expanded source/pre-removal handle census cannot be replayed; accessiblecwdFD observations exclude permission/transient/maps/externalusers limitations','No rootmetadata/mtime nanosecond/ACL/xattr/inode equivalence claim for TAR','No original full-log namespace provenance link supplied; UNREPORTED/no gate upgrade','Failed563d existence only; no unbaselined contents/current mutable writer inputs qualification','Capacity observation is no new gate authority; root fresh checks/serialization/distinctrelease required'],'current_free_bytes_observation':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize,'elapsed_seconds':round(time.monotonic()-started,3),'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md existing exact7d070 paragraph','Exact_delta_or_reuse':patch,'Disposition':'Verified existing accepted paragraph verbatim; no redundant capacity diary delta needed','Durable_learning_captured':'Preserve complete recorded scratch byte/metadata evidence before exact completed namespace removal, while separating observed handle and gate authority limits.','Evidence':'16121 streamed members+CRC/EOF; prior39archives18indices; wholecache416 bytes; current3001423/110refs/30inputs; ASTsame16nodes','Stale_or_ambiguous_guidance_removed':'No preservation result recast as native gate, historical process census or missing full-log provenance qualification.','Remaining_uncertainty':'Historical handles and TAR unrecorded metadata/provenance remain unqualified; separate futuregate authority required'},'Upstream_disposition':'none','constructor':bind(__file__)}
print(json.dumps({'OWNERFINAL':freeze('OWNERFINAL-independent-batch19-preservation-review.json',r)}),flush=True)
