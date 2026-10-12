import hashlib,json,os,pathlib,stat,subprocess,collections,time
OUT=pathlib.Path('/workspace/engineering/obsolete-accepted-checkout-disk-environment-investigation');root=pathlib.Path('/workspace/engineering/runtime-checkout-eol/actions/.venv');checkout=root.parent.parent
prefix=str(root);kinds=collections.Counter();identity={};logical=0;allocated=0;metadata=hashlib.sha256();syms=[];extension=collections.Counter();entry_count=0
for p in [root,*sorted(root.rglob('*'))]:
 m=p.lstat();kind='file' if stat.S_ISREG(m.st_mode) else 'directory' if stat.S_ISDIR(m.st_mode) else 'symlink' if stat.S_ISLNK(m.st_mode) else 'other';assert kind!='other';r=str(p.relative_to(root)) if p!=root else '.'
 record={'relative':r,'kind':kind,'mode':stat.S_IMODE(m.st_mode),'uid':m.st_uid,'gid':m.st_gid,'dev':m.st_dev,'inode':m.st_ino,'nlink':m.st_nlink,'size':m.st_size,'blocks512':m.st_blocks,'mtime_ns':m.st_mtime_ns}
 metadata.update((json.dumps(record,sort_keys=True,separators=(',',':'))+'\n').encode());kinds[kind]+=1;entry_count+=1
 key=(m.st_dev,m.st_ino);slot=identity.setdefault(key,[m.st_nlink,0,m.st_blocks*512,kind]);slot[1]+=1
 if kind=='file':
  logical+=m.st_size;ext=p.suffix if p.suffix in ['.py','.pyc','.so','.json','.zip'] else 'other';extension[ext]+=m.st_size
 if kind=='symlink':
  target=os.readlink(p);dest=p.resolve();syms.append({'relative':r,'link_string_sha256':hashlib.sha256(target.encode()).hexdigest(),'target_outside_selected_prefix':not dest.is_relative_to(root),'target_exists':dest.exists(),'resolved_target_device':dest.stat().st_dev,'target_bytes':dest.stat().st_size})
allocated=sum(v[2] for v in identity.values());hard=sum(v[1]>1 and v[3]=='file' for v in identity.values());external=sum(v[0]!=v[1] and v[3]=='file' for v in identity.values());assert external==hard==0
cfgs=[pathlib.Path('/workspace/engineering/rcc-current8d49-qualified-V9-entry-bootstrap-preparation/FROZEN-current8d49-control3-qualified-V9-entry-config-v2.json'),pathlib.Path('/workspace/engineering/pr307-currente2-concrete-LIGHT-PREEXECUTION-v2/immutable-one-LIGHT-inputs.json'),pathlib.Path('/workspace/engineering/pr308-current8d49-SOURCEFULL-preexecution/frozen-current8d49-source-FULL-inputs.json')]
refs=[];allpaths=[]
def paths(v):
 if isinstance(v,str) and v.startswith('/') and '\n' not in v:allpaths.append(v)
 elif isinstance(v,dict):
  for x in v.values():paths(x)
 elif isinstance(v,list):
  for x in v:paths(x)
for p in cfgs:
 b=p.read_bytes();d=json.loads(b);paths(d);refs.append({'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
# Follow only finite concrete source inventories/qualified config used by current FULL data guard.
s=json.loads(cfgs[-1].read_bytes())
for k in ('source_inventory','original_qualified_config','original_native_config'):
 p=pathlib.Path(s[k]);b=p.read_bytes();d=json.loads(b);paths(d);refs.append({'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
active_source=pathlib.Path(s['source_root']);source_rows=json.loads(pathlib.Path(s['source_inventory']).read_bytes());allpaths.extend(str(active_source/r['path']) for r in source_rows)
n=json.loads(pathlib.Path(s['original_native_config']).read_bytes());allpaths.extend(str(pathlib.Path(n['native_original_root'])/r['path']) for r in n['native_original_members']);allpaths.extend(str(active_source/r['path']) if isinstance(r,dict) and 'path' in r else str(active_source/r) for r in s['prepared_inputs'])
lexical_matches=sum(pathlib.Path(p).is_relative_to(root) for p in allpaths);resolved_matches=sum(pathlib.Path(p).resolve().is_relative_to(root.resolve()) for p in allpaths);assert lexical_matches==resolved_matches==0
# Accessible observation only: no signal, wait, reap, package import or loaded-code execution.
proc={'processes_sampled':0,'candidate_cwd_fd_exe_cmdline_maps_matches':0,'inaccessible_or_racing_observations':0};matches=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 proc['processes_sampled']+=1
 for item in ['cwd','exe']:
  try:
   dest=os.readlink(p/item)
   if dest==prefix or dest.startswith(prefix+'/'):proc['candidate_cwd_fd_exe_cmdline_maps_matches']+=1;matches.append(item)
  except (OSError,PermissionError):proc['inaccessible_or_racing_observations']+=1
 try:
  for fd in (p/'fd').iterdir():
   try:
    dest=os.readlink(fd)
    if dest==prefix or dest.startswith(prefix+'/'):proc['candidate_cwd_fd_exe_cmdline_maps_matches']+=1;matches.append('fd')
   except OSError:proc['inaccessible_or_racing_observations']+=1
 except OSError:proc['inaccessible_or_racing_observations']+=1
 try:
  if prefix.encode() in (p/'cmdline').read_bytes():proc['candidate_cwd_fd_exe_cmdline_maps_matches']+=1;matches.append('cmdline')
 except OSError:proc['inaccessible_or_racing_observations']+=1
 try:
  with (p/'maps').open() as f:
   if any(prefix in line for line in f):proc['candidate_cwd_fd_exe_cmdline_maps_matches']+=1;matches.append('maps')
 except OSError:proc['inaccessible_or_racing_observations']+=1
assert proc['candidate_cwd_fd_exe_cmdline_maps_matches']==0
# Worktree identity and absence from tracked source, not deletion authority.
env=os.environ.copy();env['GIT_OPTIONAL_LOCKS']='0';git=lambda *args:subprocess.check_output(['git','--no-optional-locks',*args],cwd=checkout,env=env).decode().strip();head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}');assert head=='ec70a2928461941c129b1c05332dc441070e0184' and tree=='47a1e4fceb22fd15eaee1ca380ad6c005abfdde6';assert not git('status','--porcelain=v1');assert not git('ls-files','--','actions/.venv');subprocess.run(['git','--no-optional-locks','merge-base','--is-ancestor',head,'e2c81adce7858d5a952991ba9a8b7f72e902038a'],cwd=checkout,env=env,check=True)
mounts={}
for p in ('/workspace','/tmp','/dev/shm'):
 v=os.statvfs(p);mounts[p]={'device':pathlib.Path(p).stat().st_dev,'available_bytes':v.f_bavail*v.f_frsize,'filesystem':subprocess.check_output(['stat','-f','-c','%T',p],text=True).strip()}
mem={'current':int(pathlib.Path('/sys/fs/cgroup/memory.current').read_text()),'maximum':int(pathlib.Path('/sys/fs/cgroup/memory.max').read_text())};nativefloor=1288490189;partial=134201221;budgetbreak=mounts['/workspace']['available_bytes']+allocated-nativefloor-partial
exact_delta='An ignored environment in a completed checkout is a separate preservation subject, not a completed pytest namespace. Bind its accepted checkout, exact prefix and current dependency/overlap observations; retain interpreter symlinks and editable-source dependencies for restoration at the original path. Measure disk allocation and compressed net gain separately from tmpfs and cgroup memory, and authorize any environment removal only through a distinct bounded preservation plan.\n'
proposal=OUT/'proposed-canonical-completed-environment-preservation-and-mount-budget.txt';proposal.write_text(exact_delta);proposal.chmod(0o400)
r={'schema':1,'decision':'CONCRETE_DISK_ENVIRONMENT_PRESERVATION_CANDIDATE_ONLY_NO_OPERATION','candidate':str(root),'accepted_checkout_source':head,'accepted_checkout_tree':tree,'accepted_integration_descendant':'e2c81adce7858d5a952991ba9a8b7f72e902038a','clean_worktree':True,'tracked_candidate_members':0,'selected_environment_metadata_only':{'members_excluding_root':entry_count-1,'member_kinds_excluding_root':{**dict(kinds),'directory':kinds['directory']-1},'allocated_unique_inode_bytes_including_root_and_symlinks':allocated,'logical_regular_bytes':logical,'internal_regular_hardlink_groups':hard,'external_regular_hardlink_groups':external,'external_interpreter_symlinks':syms,'metadata_stream_fingerprint_sha256':metadata.hexdigest(),'body_hashes':'NOT_MEASURED_THIS_INVESTIGATION_REQUIRED_FOR_PRESERVATION_PLAN','logical_bytes_by_fixed_extension_category':dict(extension)},'current_dependency_scope':{'metadata_configs_and_concrete_inventories':refs,'absolute_path_rows_including_source1440_native1192_and_prepared30_scanned':len(allpaths),'candidate_lexical_matches':lexical_matches,'candidate_resolved_matches':resolved_matches,'all_current_PR308_and_PR307_selected_prefixes_separate':True,'older_receipt_json_mentions_not_transitive_live_guard_authority':True},'process_observation':{**proc,'universal_quiescence':'UNKNOWN','signals_waits_reaps':'NONE','matches_categories':matches},'mounts':mounts,'cgroup_memory_snapshot':mem,'budget':{'native_workspace_floor':nativefloor,'hypothetical_retained_TMP_partial_to_disk_bytes':partial,'maximum_environment_archive_plus_indices_for_floor_after_exact_partial_relocation_bytes':budgetbreak,'compression_size':'UNKNOWN_NOT_RUN','suggested_future_finite_archive_cap_bytes':100663296,'suggested_future_combined_index_cap_bytes':16777216,'prospective_margin_if_both_caps_used_and_same_free_snapshot':budgetbreak-100663296-16777216,'actual_gain_floor_or_RAM_recovery_promise':False},'required_next_bounded_gate':['Root selects this exact completed ignored prefix under an environment-specific plan; existing recycle-marker scratch algorithm is not automatic authority','Freeze complete regular body hashes plus types/UIDGID/modes/PAXnsmtime/symlinks/inode partition/root metadata and require two stable snapshots/external links0','Revalidate exact current source/native/environment/owner critical dependencies and accessible cwd/fd/exe/cmdline/maps; unreadable scope remains UNKNOWN and requires explicit scoped policy','Private archive on existing workspace disk only, finite actual compressed/footer cap and combined index cap, exact all-member verify/fsync/index before any environment removal; stop keeping original on cap failure','Retain alias/restoration recipe at original prefix with cached interpreter/editable source dependencies; preserve tracked worktree/Git/receipts/current environments entirely','No pip/Poetry/RCC install, test/native runtime, blanket cache cleanup or operation in this investigation; root release and independent PREEXEC/ACTUAL review required','Measure actual reclaimed disk and fresh native/tmp/cgroup floors afterward before separately authorized exact archive relocation/native execution'],'limits':['Old environment may be needed for future historical replay; archive restoration is required rather than replacement installation','Overlay allocated blocks are measured, future actual statvfs gain is unmeasured','Selected-prefix symlink target interpreter is outside archive and must be retained','This investigation gives a candidate, not verified lossless archive or authorized removal','Process observations are point-in-time and inaccessible scope is not universal inactivity','RAM/cgroup recovery is separate from disk capacity and cannot be inferred from directory allocation'],'documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta':exact_delta,'durable_learning':'Completed ignored environment differs from recycle-marked test scratch and has external interpreter restoration dependencies; measure overlay/tmpfs/cgroup resources independently','evidence':'Clean accepted ec70 checkout,6457 ignored environment members/zero hardlinks/three external interpreter symlinks; current consumed path scan0; workspace overlaydev27 versus tmpfsdev33/26','stale_or_ambiguous_guidance_removed':'Completed checkout or ignored .venv status alone is not removal authority; disk gain is not RAM or native floor qualification','remaining_uncertainty':'Complete body baseline, actual compression and reclaim, historical restoration dependency policy and inaccessible live process scope unqualified'},'upstream_disposition':'none','read_only':True}
p=OUT/'OWNERFINAL-one-obsolete-accepted-checkout-disk-environment-candidate-readonly-investigation.json';p.write_bytes((json.dumps(r,indent=2,sort_keys=True)+'\n').encode());p.chmod(0o400);print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'allocated':allocated,'prospective_cap_margin':budgetbreak-100663296-16777216,'observed_process_matches':proc['candidate_cwd_fd_exe_cmdline_maps_matches']},sort_keys=True))
