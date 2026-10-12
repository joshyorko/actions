import datetime,hashlib,json,os,stat,subprocess,time
from collections import Counter,defaultdict
from pathlib import Path
OUT=Path('/workspace/engineering/root-failed300-default-cache-readonly-preparation');PRIVATE=Path('/tmp/root-failed300-default-cache-readonly-preparation-20261011');ROOT=Path('/home/agent/.robocorp/pkgs');DEST=Path('/dev/shm/actions-root-failed300-default-cache-preservation-20261011')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def write(p,data,mode):
 with p.open('x') as f:f.write(json.dumps(data,indent=2)+'\n')
 p.chmod(mode);return bind(p)
def info(p):
 s=p.lstat();return {'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'mtime_ns':s.st_mtime_ns,'device':s.st_dev,'inode':s.st_ino,'nlink':s.st_nlink,'allocated_bytes':getattr(s,'st_blocks',0)*512}
def inventory():
 assert ROOT.is_dir() and not ROOT.is_symlink();out={};pending=[ROOT]
 while pending:
  base=pending.pop()
  for p in sorted(base.iterdir()):
   s=p.lstat();d=info(p)
   if stat.S_ISDIR(s.st_mode):d['kind']='directory';pending.append(p)
   elif stat.S_ISREG(s.st_mode):d.update(kind='file',bytes=s.st_size,sha256=sha(p));assert info(p)=={k:v for k,v in d.items() if k not in ['kind','bytes','sha256']},'file changed during inspection'
   elif stat.S_ISLNK(s.st_mode):d.update(kind='symlink',target=os.readlink(p))
   elif stat.S_ISFIFO(s.st_mode):d['kind']='fifo'
   else:raise AssertionError('unsupported filesystem object type')
   out[p.relative_to(ROOT).as_posix()]=d
 return {'root':info(ROOT),'entries':out}
def handles():
 matches=[];errors=Counter();observed=0
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  links=[p/'cwd']
  try:links.extend((p/'fd').iterdir())
  except (PermissionError,FileNotFoundError) as e:errors[type(e).__name__]+=1
  for link in links:
   try:target=os.readlink(link);observed+=1
   except (FileNotFoundError,PermissionError,OSError) as e:errors[type(e).__name__]+=1;continue
   if target==str(ROOT) or target.startswith(str(ROOT)+'/'):matches.append({'pid':p.name,'link':str(link),'target':target})
 return {'matches':matches,'observed_links':observed,'unavailable_counts':dict(errors),'scope':'Observed /proc cwd and fd symlink targets only; not a complete process/maps or historical handle census'}
assert not DEST.exists() and not DEST.is_symlink()
first_handles=handles();started=time.monotonic();first=inventory();second=inventory();assert first==second,'directory changed between complete inventories';last_handles=handles()
private=write(PRIVATE/'complete-source-inventory-and-observed-handles.json',{'source':str(ROOT),'first_inventory':first,'second_inventory':second,'first_handles':first_handles,'last_handles':last_handles,'history_and_pre_failed_attempt_baseline':'UNKNOWN; preserve whole exact current directory, including any older contents'},0o600)
entries=first['entries'];kinds=Counter(x['kind'] for x in entries.values());groups=defaultdict(list)
for p,row in entries.items():
 if row['kind']=='file':groups[(row['device'],row['inode'])].append(p)
external=[]
for rows in groups.values():
 if entries[rows[0]]['nlink']>len(rows):external.append({'internal_count':len(rows),'reported_link_count':entries[rows[0]]['nlink']})
terminal_path=Path('/workspace/engineering/pr300-current74-owner-full-contract-adoption/current74-one-reviewed-configured-full-terminal.json');terminal=json.loads(terminal_path.read_text());assert terminal['returncode']==4 and terminal['log']['bytes']==80268 and terminal['log']['sha256']=='38029425f98c3416b3dd8ad82a90f9ca96ba2e2f1818e9024286854a61bdf684';assert bind(terminal['log']['path'])==terminal['log'];text=Path(terminal['log']['path']).read_text(errors='replace')
root_post=Path('/workspace/engineering/pr300-current74-owner-full-contract-adoption/root-current74-postfull-complete-source-and-reference-readback.json');post=json.loads(root_post.read_text());assert post['tracked_count']==1423 and post['all_original_and_LIGHT_refs_inputs_modes_exact']
assert bind(post['terminal']['path'])==post['terminal']
free=lambda p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize
logical=sum(x['bytes'] for x in entries.values() if x['kind']=='file');physical=sum(entries[rows[0]]['bytes'] for rows in groups.values());copy_budget=physical+max(67108864,physical//10)
sourcefacts={'status':'PASS_READ_ONLY_STABLE_WHOLE_DEFAULT_CACHE_INVENTORY','source':str(ROOT),'destination_parent_not_created':str(DEST),'entries':len(entries),'kinds':dict(kinds),'logical_regular_bytes':logical,'unique_inode_regular_bytes':physical,'allocated_bytes_unique_inodes':sum(entries[rows[0]]['allocated_bytes'] for rows in groups.values()),'internal_hardlink_classes':sum(len(rows)>1 for rows in groups.values()),'external_hardlink_relation_candidate_inode_count':len(external),'external_hardlink_relation_counts_no_paths':external,'source_root_metadata':{k:v for k,v in first['root'].items() if k not in ['device','inode']},'source_two_complete_body_metadata_inventory_passes_exact':True,'no_observed_live_cwd_fd_first':not first_handles['matches'],'no_observed_live_cwd_fd_last':not last_handles['matches'],'observed_handle_unavailable_counts_first':first_handles['unavailable_counts'],'observed_handle_unavailable_counts_last':last_handles['unavailable_counts'],'handle_census_scope':first_handles['scope'],'private_complete_inventory':private,'workspace_free_bytes':free('/workspace'),'existing_devshm_free_bytes':free('/dev/shm'),'required_copy_budget_bytes_including_10percent_or64MiB':copy_budget,'existing_devshm_space_sufficient':free('/dev/shm')>=copy_budget,'private_inventory_seconds':round(time.monotonic()-started,3),'historical_default_cache_ownership_or_new_only_files':'UNKNOWN; no pre-run baseline; whole directory mandatory','original_failed300_terminal':bind(terminal_path),'original_raw_log':terminal['log'],'root_post_failed300_source_and_refs':bind(root_post),'observed_original_log_categories':{'default_home_path_present':'/home/agent/.robocorp' in text,'managed_home_path_present':'/workspace/actions-cloud/robocorp' in text,'ENOSPC_or_no_space_literal_present':any(x in text for x in ['ENOSPC','No space left on device','no space left on device']),'pytest_test_session_marker_present':'test session starts' in text,'pytest_worker_creation_marker_present':'created: ' in text and ' workers' in text},'production_or_pytest_failure_attribution':False,'mutations_performed':'Only owned evidence files; no source/cache symlink/copy/removal/gate/installer/execution'}
sourceproof=write(OUT/'safe-whole-default-cache-inspection-proof.json',sourcefacts,0o444)
plan={'status':'PROPOSAL_ONLY_ROOT_EXACT_MUTATION_RELEASE_REQUIRED','source':str(ROOT),'unique_existing_mount_preservation_root':str(DEST),'physical_copy':str(DEST/'pkgs'),'copy_action':['mkdir -m700 unique preservation parent; reject if preexisting','cp -a --preserve=all --no-dereference /home/agent/.robocorp/pkgs uniqueParent/pkgs (existing GNUcp; no install)','Reinventory source and destination completely: exact relative set/body SHA+sizes/types/modes/UID/GID/mtime_ns/symlink targets/root metadata and internal hardlink equivalence partitions','Recheck original stable against frozen private inventory and no observed live cwd/FD; STOP on change/unknown live handle or inability to preserve metadata','Rename ONLY original pkgs directory to unique same-parent task-owned backup; create absolute symlink at original logical pkgs path pointing to verified preserved /dev/shm physical copy','Before any expanded backup removal, verify original logical path resolves to physical copy, complete logical inventory still equals frozen source contract, and renamed backup inventory remains frozen-original exact','Recheck no observed live handles into original/backup; remove ONLY renamed expanded original after all verification; preserve verified whole physical copy and complete private recovery receipt','If symlink creation/logical verification fails: retain physical copy and expanded backup; remove only task-created symlink if present and restore exact original directory name; preserve primary failure and any secondary rollback error'],'transaction_limits':'No atomic directory-to-symlink exchange assumed: two operations leave a brief path gap; require quiescent cache and root-controlled no other default-cache users. Concurrent external access cannot be proved absent by observed cwd/FD alone.','source_guards':sourceproof,'history_policy':'No pre-attempt inventory: preserve ALL current entries, never infer new-only ownership or garbage collect; do not touch failedtemp dcdb2bb109728a05, old563d, managedhome, environments, native/private inputs, logs, or source','cross_mount_inode_policy':'Internal hardlink equivalence preserved; inode numbers necessarily change across mounts; external hardlink relations require explicit root disposition if any measured','copy_budget_bytes':copy_budget,'outer_copy_and_complete_verification_bound_proposal_seconds':600,'one_copy_no_retry_or_package_reinstall':True,'optional_compressed_backup':'Deferred; verified full physical copy suffices for this narrow preservation; no large duplicate archive planned','future_gate_preflight':'Activate reviewed managed gateway in the SAME launcher environment; assert allowlisted effective RCC home and pinned executable before any root gate. Separate root-reviewed preexecution proposal and ONE future gate authorization; no automatic retry.'}
proposal=write(OUT/'bounded-whole-default-cache-preservation-proposal.json',plan,0o444)
print(json.dumps({'safe_inspection':sourceproof,'proposal':proposal,'entry_count':len(entries),'logical_bytes':logical,'internal_hardlink_classes':sourcefacts['internal_hardlink_classes'],'external_hardlink_candidates':len(external),'no_observed_live_handles':not first_handles['matches'] and not last_handles['matches'],'existing_devshm_free_bytes':sourcefacts['existing_devshm_free_bytes'],'workspace_free_bytes':sourcefacts['workspace_free_bytes']}),flush=True)
