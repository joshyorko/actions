import ast,collections,gzip,hashlib,json,os,pathlib,stat,subprocess,tarfile
D=pathlib.Path('/workspace/engineering/capacity-recovery-batch25-independent-actual-review'); P=pathlib.Path('/workspace/engineering/capacity-recovery-batch25-proposal'); R=pathlib.Path('/workspace/engineering/root-B25-one-existing-tmp-recovery')
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_bytes())
def bind(p):
 p=pathlib.Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def verify(r):
 p=pathlib.Path(r['path']);assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'];assert oct(stat.S_IMODE(p.stat().st_mode))==r['mode'];return bind(p)
owner_path=R/'OWNERFINAL-root-one-B25-existing-tmp-volume-terminal.json';owner=load(owner_path);assert owner_path.stat().st_size==639 and sha(owner_path)=='982881775d8e85ef30b475caafd5f12a8bba562d787b6f660cb87b94cd9abb8f';assert owner['returncode']==0 and owner['attempts']==1 and owner['source_origin']=='UNREPORTED';assert owner['post_source_original_native_guard']=='PASS'
release_path=R/'root-one-distinct-B25-release.json';release=load(release_path);assert sha(release_path)==owner['release_sha256'];assert release['names']==['ad13a81675676d7b'] and release['attempts']==1
proposal_path=P/'OWNERFINAL-batch25-existing-tmp-volume-only-successor-v3-NOT_RUN.json';proposal=load(proposal_path);assert sha(proposal_path)==release['proposal_sha256'];assert proposal['destination']=='/tmp/actions-completed-scratch-recovery-batch25';assert proposal['source_origin']=='UNREPORTED'
review_path=pathlib.Path('/workspace/engineering/capacity-recovery-batch25-independent-preexecution-review/OWNERFINAL-independent-B25-existing-tmp-destination-only-successor-preexecution-review.json');assert sha(review_path)==release['review_sha256'];assert load(review_path)['status']=='GO_CONDITIONAL_DESTINATION_ONLY_B25_EXISTING_TMP_PREEXECUTION'
for k in ('original_owner','original_script','original_independent','script'):verify(proposal[k])
script=pathlib.Path(proposal['script']['path']);assert sha(script)==release['script_sha256'];oldscript=pathlib.Path(proposal['original_script']['path']);a=ast.parse(oldscript.read_bytes());b=ast.parse(script.read_bytes());assert len(a.body)==len(b.body)==19;changed=[]
for na,nb in zip(a.body,b.body):
 if ast.dump(na,include_attributes=False)!=ast.dump(nb,include_attributes=False):changed.append(na.targets[0].id)
assert changed==['DEST'];assert 'extractall' not in script.read_text();assert proposal['bounded_future_argv']==['env','-u','PYTHONOPTIMIZE','timeout','--signal=TERM','--kill-after=10s','600s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',str(script)]
log=pathlib.Path(owner['original_log']['path']);assert log.stat().st_size==owner['original_log']['bytes'] and sha(log)==owner['original_log']['sha256']
snapshot_path=P/'private-complete-candidate-two-stable-inventories-v2.json';snap=load(snapshot_path);assert snap['first']==snap['second'];expected=snap['first'];assert len(expected)==16157
index_path=pathlib.Path('/tmp/actions-completed-scratch-recovery-batch25/private-complete-inventory-and-recovery.json');index=load(index_path);assert stat.S_IMODE(index_path.stat().st_mode)==0o600 and len(index['records'])==1;record=index['records'][0];assert record['inventory']==expected;assert record['archive_verified_before_original_removal'] is True and record['expanded_removed'] is True;assert record['verified_members']==16157;assert record['original_namespace']==snap['original_namespace'];assert not pathlib.Path(record['original_namespace']).exists();assert not pathlib.Path('/tmp/actions-completed-scratch-recovery-batch25-stage').exists()
archive=pathlib.Path(record['archive']);assert archive.stat().st_size==record['archive_bytes'] and sha(archive)==record['archive_sha256'];assert stat.S_IMODE(archive.stat().st_mode)==0o600
root='ad13a81675676d7b';seen=set();seen_members={};types=collections.Counter();hardlinks=0;root_seen=0
with gzip.open(archive,'rb') as gz:
 with tarfile.open(fileobj=gz,mode='r|') as t:
  for m in t:
   if m.name==root:assert m.isdir();root_seen+=1;continue
   assert m.name.startswith(root+'/');rel=m.name[len(root)+1:];assert rel in expected and rel not in seen;seen.add(rel);e=expected[rel];assert m.mode==e['mode'] and m.uid==e['uid'] and m.gid==e['gid'];types[e['kind']]+=1
   if m.isdir():assert e['kind']=='directory';seen_members[m.name]={'kind':'directory'}
   elif m.issym():assert e['kind']=='symlink' and m.linkname==e['target'];seen_members[m.name]={'kind':'symlink','target':m.linkname}
   elif m.isfifo():assert e['kind']=='fifo';seen_members[m.name]={'kind':'fifo'}
   elif m.islnk():
    assert e['kind']=='file' and m.linkname.startswith(root+'/');link=seen_members[m.linkname];assert link['kind']=='file' and link['bytes']==e['bytes'] and link['sha256']==e['sha256'];seen_members[m.name]=link;hardlinks+=1
   else:
    assert m.isfile() and e['kind']=='file' and m.size==e['bytes'];h=hashlib.sha256();count=0
    f=t.extractfile(m)
    for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk);count+=len(chunk)
    assert count==e['bytes'] and h.hexdigest()==e['sha256'];seen_members[m.name]={'kind':'file','bytes':count,'sha256':h.hexdigest()}
 # Consume gzip trailer/EOF to require finite valid compressed stream CRC.
 while gz.read(1048576):pass
assert seen==set(expected) and root_seen==1;assert dict(types)=={'file':12214,'directory':3447,'symlink':488,'fifo':8}
priorpath=P/'private-prior50-original-archives24-indices-current-hash-retention-v2.json';prior=load(priorpath);assert len(prior['archives'])==50 and len(prior['indices'])==24
for r in prior['archives']:
 p=pathlib.Path(r['archive']);assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'];assert stat.S_IMODE(p.stat().st_mode)==r['mode']
for r in prior['indices']:
 p=pathlib.Path(r['path']);assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
assert pathlib.Path('/workspace/actions-cloud/robocorp/temp/563d2fb1ce3978fd').exists() if pathlib.Path('/workspace/actions-cloud/robocorp/temp/563d2fb1ce3978fd').exists() else any(p.name.startswith('563d') for p in pathlib.Path('/workspace/actions-cloud/robocorp/temp').iterdir())
V5=pathlib.Path('/workspace/actions-cloud/receipts/pr305-writer/immutable-runner-v5.py')
# Pin the actual historical V5 runner from the current LIGHT accepted predecessor evidence, not guessed path.
if not V5.exists():
 candidates=list(pathlib.Path('/workspace/engineering').glob('pr305*/**/*runner-v5.py'))
 candidates+=list(pathlib.Path('/workspace/actions-cloud/receipts').glob('**/*runner-v5.py'))
 V5=next(p for p in candidates if sha(p)=='09cdc6b19f5d3d9cc94fadca23373108868521e0378d33960146b1a8522e88ad')
assert sha(V5)=='09cdc6b19f5d3d9cc94fadca23373108868521e0378d33960146b1a8522e88ad'
lightpath=pathlib.Path('/workspace/engineering/pr308-currente4ff-independent-SOURCE-LIGHT-review/OWNERFINAL-independent-current-e4ff-owned-cache-ordinary-source-LIGHT-review.json');assert sha(lightpath)=='66a2819f6231928140574e590d3a68146d29c1f965609caa14dd65f705b8a33d';light=load(lightpath);assert light['decision']=='GO_CURRENT_E4FF_SOURCE_LIGHT_ONLY';proofpath=pathlib.Path(light['independent_proof']['path']);verify(light['independent_proof']);proof=load(proofpath)
repo=pathlib.Path('/workspace/engineering/pr308');git=lambda *a:subprocess.check_output(['git','--no-optional-locks','-C',str(repo),*a]);assert git('rev-parse','HEAD').decode().strip()==light['source']['commit'] and not git('status','--porcelain')
currentowner=load(light['owner_LIGHT']['path']);invpath=next(pathlib.Path(r['path']) for r in currentowner['frozen_bindings'] if pathlib.Path(r['path']).name=='private-current-e4ff-complete-source-body-mode-inventory.json')
for r in load(invpath):
 p=repo/r['path'];bb=os.readlink(p).encode() if p.is_symlink() else p.read_bytes();assert hashlib.sha256(bb).hexdigest()==r['sha256'];assert stat.S_IMODE(p.lstat().st_mode)==r['fs_mode']
# Original native data remains an immutable input, with failed-result reference archive-backed through V4 mapping.
configpath=next(pathlib.Path(r['path']) for r in currentowner['frozen_bindings'] if pathlib.Path(r['path']).name=='FROZEN-control3-current-b614-actual-config-v2.json');cfg=load(configpath);native=pathlib.Path(cfg['native_original_root']);assert len(cfg['native_original_members'])==1192
for r in cfg['native_original_members']:
 p=native/r['path'];assert stat.S_IMODE(p.lstat().st_mode)==r['mode']
 if r['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==r['link_target']
 elif r['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert p.is_file() and not p.is_symlink() and sha(p)==r['content_sha256']
map_path=pathlib.Path(proof['archive_mapping']['path']);verify(proof['archive_mapping']);mapping=load(map_path)
for k in ('archive','complete_index','expanded_removal','root_original_terminal'):verify(mapping[k])
assert not pathlib.Path(mapping['original_binding']['path']).exists()
lesson=pathlib.Path('/workspace/engineering/capacity-recovery-independent-review/canonical-completed-scratch-preservation-proposed.patch');assert sha(lesson)=='7d07065b5bb7742698919997c8c6621cc20d00494741eb5365251ffb09f2d208'
out={'schema':1,'status':'PASS_ONE_B25_COMPLETED_NAMESPACE_PRESERVATION_DATA_REVIEW','owner':bind(owner_path),'release':bind(release_path),'destination_only_successor':bind(proposal_path),'accepted_preexecution':bind(review_path),'executed_script':bind(script),'script_AST_difference_from_accepted_B25':['DEST_only_existing_tmp_volume'],'original_process_log':bind(log),'root_returncode':0,'root_elapsed_seconds':owner['elapsed_seconds'],'root_attempts':1,'source_origin':'UNREPORTED','archive':bind(archive),'complete_index':bind(index_path),'frozen_two_inventories':bind(snapshot_path),'all16157_original_member_record_pairs_exact':True,'member_counts':dict(types),'resolved_internal_hardlink_members':hardlinks,'gzip_EOF_CRC_and_compressed_hash':'PASS','root_tar_entry':{'count':1,'kind':'directory','scope':'root original metadata not admitted'},'expanded_namespace_absent':True,'unused_stage_absent':True,'prior50_archive_bytes_hash_modes_and24_indices_exact':True,'prior_inventory':bind(priorpath),'failed563d':'EXISTENCE_ONLY_NOT_OPENED','original_V5_runner':bind(V5),'current_e4ff_LIGHT':bind(lightpath),'current_source1423_FS_modes_and_bodies_reverified':True,'original_native1192_reverified':True,'original_failed3_alias':'absent as designed; exact V4 archive/index/removal/root terminal unchanged, original FAIL not relabeled','archive_mapping':bind(map_path),'limits':['No new universal handle/quiescence claim','No historical source-origin inference','No ACL/xattr/inode or original root metadata proof','No nanosecond TAR timestamp preservation claim','No native/consumer/gate acceptance upgrade'], 'canonical_verified_reuse':bind(lesson),'upstream_disposition':'none'}
f=D/'independent-one-B25-preservation-data-proof.json';assert not f.exists();f.write_text(json.dumps(out,indent=2)+'\n');f.chmod(0o600);print(json.dumps(bind(f)))
