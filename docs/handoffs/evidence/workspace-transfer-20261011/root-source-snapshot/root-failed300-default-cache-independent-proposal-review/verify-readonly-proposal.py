import datetime,hashlib,json,os,posixpath,stat,subprocess
from collections import Counter,defaultdict
from pathlib import Path
D=Path('/workspace/engineering/root-failed300-default-cache-readonly-preparation');O=Path(__file__).resolve().parent;ROOT=Path('/home/agent/.robocorp/pkgs')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(v):assert bind(v['path'])=={k:v[k] for k in ('path','bytes','sha256')},v['path']
def info(p):
 s=p.lstat();return {'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'mtime_ns':s.st_mtime_ns,'device':s.st_dev,'inode':s.st_ino,'nlink':s.st_nlink,'allocated_bytes':getattr(s,'st_blocks',0)*512}
def inventory():
 result={};pending=[ROOT];assert ROOT.is_dir() and not ROOT.is_symlink()
 while pending:
  base=pending.pop()
  for p in sorted(base.iterdir()):
   s=p.lstat();row=info(p)
   if stat.S_ISDIR(s.st_mode):row['kind']='directory';pending.append(p)
   elif stat.S_ISREG(s.st_mode):
    row.update(kind='file',bytes=s.st_size,sha256=sha(p));assert info(p)=={k:v for k,v in row.items() if k not in ('kind','bytes','sha256')}
   elif stat.S_ISLNK(s.st_mode):row.update(kind='symlink',target=os.readlink(p))
   else:raise AssertionError('unexpected kind')
   result[str(p.relative_to(ROOT))]=row
 return {'root':info(ROOT),'entries':result}
def handles():
 matched=[];unavailable=Counter();seen=0
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  paths=[p/'cwd']
  try:paths.extend((p/'fd').iterdir())
  except (PermissionError,FileNotFoundError) as exc:unavailable[type(exc).__name__]+=1
  for path in paths:
   try:target=os.readlink(path);seen+=1
   except OSError as exc:unavailable[type(exc).__name__]+=1;continue
   if target==str(ROOT) or target.startswith(str(ROOT)+'/'):matched.append(p.name)
 return {'observed_matching_process_count':len(set(matched)),'observed_matching_links':len(matched),'observed_links':seen,'unavailable_counts':dict(unavailable),'scope':'point-in-time cwd/fd links only; maps and inaccessible/transient processes not excluded'}
ownerpath=D/'OWNERFINAL-default-failed300-cache-preservation-readonly-proposal.json';owner=bind(ownerpath);assert owner['bytes']==6158 and owner['sha256']=='58938c98c04f7c3498339583e011d744d770fd5f5fe1ad413e54cee32f65eabc';a=json.loads(ownerpath.read_bytes())
for v in a['immutable_evidence_bindings']:check(v)
for key in ('bounded_proposal','stable_complete_inspection','private_complete_source_inventory','original_failed300_terminal','original_failed300_raw_log','root_post_failure_source_and_refs'):check(a[key])
proposal=json.loads(Path(a['bounded_proposal']['path']).read_bytes());assert a['bounded_proposal']['sha256']=='8371a8691748c3af7a986f4ad59033569087a85a1f65f2850a79f176ae96a65e'
private=json.loads(Path(a['private_complete_source_inventory']['path']).read_bytes());assert private['first_inventory']==private['second_inventory']
now=inventory();assert now==private['first_inventory']
counts=Counter(r['kind'] for r in now['entries'].values());assert len(now['entries'])==416 and counts=={'file':362,'directory':38,'symlink':16}
logical=sum(r['bytes'] for r in now['entries'].values() if r['kind']=='file');assert logical==1132159923
classes=defaultdict(list)
for n,r in now['entries'].items():
 if r['kind']=='file':classes[(r['device'],r['inode'])].append(n)
assert not [v for v in classes.values() if len(v)>1] and not [v for v in classes.values() if now['entries'][v[0]]['nlink']>len(v)]
symlinks=[(n,r) for n,r in now['entries'].items() if r['kind']=='symlink'];assert len(symlinks)==16
for n,r in symlinks:
 assert not r['target'].startswith('/')
 resolved=posixpath.normpath(posixpath.join(str(ROOT),posixpath.dirname(n),r['target']))
 assert resolved.startswith(str(ROOT)+'/')
 # Existing relative symlink topology remains within relocated tree; no external-relative-parent rebinding needed.
observed=handles();assert observed['observed_matching_links']==0
DEST=Path(proposal['unique_existing_mount_preservation_root']);assert not os.path.lexists(DEST)
free=lambda p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize
assert free('/dev/shm')>=proposal['copy_budget_bytes']==1245375915
assert proposal['pre_execution_conditions']['root_controls_no_other_default_cache_users']
assert proposal['pre_execution_conditions']['original_two_pass_frozen_inventory_hash']==a['private_complete_source_inventory']['sha256']
assert proposal['outer_copy_and_complete_verification_bound_proposal_seconds']==600 and proposal['one_copy_no_retry_or_package_reinstall']
assert proposal['copy_command_proposal']==['timeout','--signal=TERM','--kill-after=10s','600s','cp','-a','--preserve=all','--no-dereference',str(ROOT),str(DEST/'pkgs')]
assert 'root mode/UID/GID/mtime_ns' in proposal['copy_action'][2] and 'logical path is exactly the task-created symlink' in proposal['copy_action'][5]
assert 'retain physical copy and expanded backup' in proposal['copy_action'][-1] and 'quiescent cache' in proposal['transaction_limits']
terminal=json.loads(Path(a['original_failed300_terminal']['path']).read_bytes());assert terminal['returncode']==4 and terminal['elapsed_seconds']==18.849684864995652
text=Path(a['original_failed300_raw_log']['path']).read_text(errors='replace');assert '/home/agent/.robocorp' in text and '/workspace/actions-cloud/robocorp' not in text and any(x in text for x in ('ENOSPC','No space left on device','no space left on device')) and 'test session starts' not in text
post=json.loads(Path(a['root_post_failure_source_and_refs']['path']).read_bytes());assert post['tracked_count']==1423 and post['all_original_and_LIGHT_refs_inputs_modes_exact'] and post['head']==terminal['head']
R=Path('/workspace/engineering/pr300');assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()==terminal['head'] and not subprocess.check_output(['git','status','--porcelain'],cwd=R)
originalsource=Path('/workspace/engineering/pr300-issue86-assembled-transport-source-successor/immutable-current74-complete1423-Git-FS-mode-bindings.json');rows=json.loads(originalsource.read_bytes())['all1423'];assert len(rows)==1423
for row in rows:
 p=R/row['path'];b=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'];assert row['mode']=='120000' or bool(p.stat().st_mode&0o111)==(row['mode']=='100755')
canonical=D/'canonical-exact-launcher-managed-RCC-home-preflight-proposed.patch';assert sha(canonical)=='811befd4b06df317ddfaee02dca3d5418568840183ecfb0ddc9e7d087fb89a6e'
lines=[n[1:] for n in canonical.read_text().splitlines() if n.startswith('+') and not n.startswith('+++')];assert len(lines)==8 and len([n for n in lines if n.strip()])==7
assert 'export ROBOCORP_HOME="$ACTIONS_CLOUD_ROOT/robocorp"' in Path('/workspace/actions-cloud/activate.sh').read_text()
result={'verdict':'GO_BOUNDED_WHOLE_CACHE_PRESERVATION_DESIGN_FOR_ROOT_EXACT_MUTATION_RELEASE','owner':owner,'proposal':a['bounded_proposal'],'reviewed_at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'read_only_original_complete_source416_and_root_metadata_exact':True,'private_inventory_binding':a['private_complete_source_inventory'],'retained_original_counts':{'file':362,'directory':38,'symlink':16,'entries':416,'logical_regular_bytes':logical,'internal_hardlink_classes':0,'external_hardlink_candidates':0,'all16_relative_symlinks_stay_inside_tree':True},'current_observed_handles':observed,'original_process_census_limits':a['scope']['proc_permission_unavailable'],'quiescence_requirement':'Root controls no other default-cache users and no default-home RCC launches throughoutcopy/verification/rename/symlink/removal; fresh observations remain incomplete and never prove global absence. GO does not remove this explicit precondition.','existing_mount_destination_absent':True,'fresh_devshm_available_bytes':free('/dev/shm'),'workspace_available_bytes_observation':free('/workspace'),'reviewed_transition_contract':['One unique700 parent on existing exec/devshm; one cp-a preserve-all no-dereference of ENTIREcache; no cachefilter/download/install','Verify originalsource and physicalcopy complete relative members/body SHA+sizes/kinds/mode/uidgid/mtime_ns/symlinktargets/rootmetadata/internal hardlink partitions against frozenprivateinventory BEFORE changing logicalpath','Reject changes/newhardlinks/metadatafailure/observedusage; do not compare cross-mountinode/device/allocatedblocks/ctime/atime as preserved equal facts','Only same-parent unique backup rename then exact absolute logical symlink; brief non-atomic gap requires root quiescence','Before removing ONLY verifiedexpandedbackup require exactownedrootlink, complete followed-rootlogicalinventory and renamedbackupinventory/sourcecontract equality, fresh observedhandlecensus','On pre-removalfailure retainphysicalcopy+backup, removeONLYownedlinkifpresent and restoreoriginalname; preserveprimary/rollbackerrors. After verifiedbackupremoval complete physicalcopy retained; furtherrollback needs copyback and freshspace.','600overall copy+verification proposal and600TERM+10 copy fallback must remain bounded in concrete root recipe; no automatic retry/gate permission'], 'source_failure_disposition':{'originalRCCreturncode':4,'elapsed_seconds':terminal['elapsed_seconds'],'pytest_started':False,'default_home_setup_ENOSPC_observed':True,'raw_original_log':a['original_failed300_raw_log'],'source1423_body_modes_unchanged_independently_verified':True,'status':'Original configuredfullattempt remainsFAIL; setup failure does not admit pytest gate or show application regression'},'remaining_HOLD':['Exact root mutation execution and independent complete post-readback/source+logical+physical verification','Any future300 full needs separately reviewed same-launcher managedactivation/preconditions and distinctONErelease','No pre-failure ownership/new-onlybaseline, global process/maps/historicalhandle or unrecordedACL/xattr/atime/ctime equivalence','Failedtempsdcdb/old563d/managedhome/source/prepared/native/private untouched; no productionpin/provider/native/browser/full134/release qualification'], 'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md','Exact_delta':bind(canonical),'Disposition':'Accept exact7content-line source-backed managed-home preflight proposal (plus blankseparator); root may integrate at owning Cloud gateway anchor. No reviewer/source edit.','Durable_learning_captured':'Pinned RCC executable identity alone does not bind outerhome/cache; managedactivation must reach exactlauncherenvironment before anysetup; failedbeforecollectiongateway is notpytest evidence.','Evidence':'Original380294/RCC4/default-home ENOSPC/no pytest marker; activate.sh reviewedexport; current1423source+oldrefs intact; stablewholecache416.','Stale_or_ambiguous_guidance_removed':'Dispatcher shell-independent semantics do not eliminate outerRCC activation/home requirements; complete whole-cache preservation doesnot infer new-only ownership or restore failedfull toPASS.','Remaining_uncertainty':'No historicalbaseline/globalcensus/actualmove/futuremanagedfull yet; limitedprocessavailability and non-atomicpathgap retained.'},'upstream_disposition':'none','review_actions':'stdlib/Git/source/AST/text/hash/lstat/processlink reads only; no copy/removal/cache/source/gates/network/download execution','immutable_constructor':bind(__file__)}
out=O/'OWNERFINAL-independent-default-failed300-whole-cache-preservation-proposal-review.json';assert not out.exists();out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');out.chmod(0o600);print(json.dumps(bind(out)))
