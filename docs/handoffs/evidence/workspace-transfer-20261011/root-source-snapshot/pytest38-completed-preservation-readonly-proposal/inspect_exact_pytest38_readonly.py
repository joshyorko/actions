import collections,datetime,hashlib,json,os,pathlib,re,stat,time
D=pathlib.Path('/workspace/engineering/pytest38-completed-preservation-readonly-proposal');ROOT=pathlib.Path('/tmp/pytest-of-agent/pytest-38');OWNER=pathlib.Path('/workspace/engineering/root-pr282-current1299-one-configured-sourcefull/OWNERFINAL-root-current1299-configured-SOURCEFULL-PASS.json')
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=pathlib.Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def verify(r):
 p=pathlib.Path(r['path']);assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
 if 'mode' in r:assert oct(stat.S_IMODE(p.stat().st_mode))==r['mode']
 return bind(p)
def meta(p):
 s=p.lstat();return {'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'mtime_ns':s.st_mtime_ns,'device':s.st_dev,'inode':s.st_ino,'nlink':s.st_nlink,'allocated_bytes':s.st_blocks*512}
def snapshot():
 assert ROOT.is_dir() and not ROOT.is_symlink();result={};rmeta=meta(ROOT)
 for parent,dirs,files in os.walk(ROOT,followlinks=False):
  for name in sorted(dirs+files):
   p=pathlib.Path(parent)/name;s=p.lstat();r=meta(p);relative=p.relative_to(ROOT).as_posix()
   if stat.S_ISLNK(s.st_mode):r.update(kind='symlink',target=os.readlink(p))
   elif stat.S_ISDIR(s.st_mode):r['kind']='directory'
   elif stat.S_ISREG(s.st_mode):r.update(kind='file',bytes=s.st_size,sha256=sha(p));assert p.lstat().st_mtime_ns==s.st_mtime_ns and p.lstat().st_size==s.st_size
   elif stat.S_ISFIFO(s.st_mode):r['kind']='fifo'
   else:raise AssertionError('UNSUPPORTED_SPECIAL_TYPE')
   assert r['uid']==r['gid']==1000;result[relative]=r
 return {'root_metadata':rmeta,'members':dict(sorted(result.items()))}
def handles():
 matches=[];inaccessible=collections.Counter();accessible=collections.Counter();vanished=0
 def inside(s):
  s=s.removesuffix(' (deleted)');return s==str(ROOT) or s.startswith(str(ROOT)+'/')
 for proc in pathlib.Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:
   v=os.readlink(proc/'cwd');accessible['cwd']+=1
   if inside(v):matches.append({'pid':int(proc.name),'kind':'cwd'})
  except PermissionError:inaccessible['cwd']+=1
  except (FileNotFoundError,ProcessLookupError):vanished+=1;continue
  except OSError:inaccessible['cwd_other']+=1
  try:fds=list((proc/'fd').iterdir());accessible['fd_dirs']+=1
  except PermissionError:inaccessible['fd_dirs']+=1;continue
  except (FileNotFoundError,ProcessLookupError):vanished+=1;continue
  except OSError:inaccessible['fd_dirs_other']+=1;continue
  for fd in fds:
   try:
    v=os.readlink(fd);accessible['fd_links']+=1
    if inside(v):matches.append({'pid':int(proc.name),'kind':'fd','fd':fd.name})
   except PermissionError:inaccessible['fd_links']+=1
   except (FileNotFoundError,ProcessLookupError):vanished+=1
   except OSError:inaccessible['fd_links_other']+=1
 return {'accessible':dict(accessible),'inaccessible_UNKNOWN':dict(inaccessible),'process_churn_disappeared':vanished,'matches':matches,'universal_quiescence':'UNKNOWN_NOT_CLAIMED'}
assert sha(OWNER)=='e82889eb300600a4d2e6c6367881b4e9b22445b4285b268b935b746956b8b662';owner=json.loads(OWNER.read_bytes());assert owner['counts']['passed']==1349 and owner['counts']['skipped']==12;assert owner['status']=='PASS_CURRENT1299_CONFIGURED_SOURCEFULL';refs=[verify(owner[k]) for k in ('complete_private_census','original_raw_log','original_terminal','root_outer_terminal')]
terminal=json.loads(pathlib.Path(owner['original_terminal']['path']).read_bytes());outer=json.loads(pathlib.Path(owner['root_outer_terminal']['path']).read_bytes());assert terminal['status']=='PASS' and terminal['primary_returncode']==terminal['post_returncode']==0;assert outer['root_outer_returncode']==0 and outer['attempts']==1
rootdir=OWNER.parent;release=rootdir/'root-one-release.json';command=rootdir/'root-one-command.json';assert rootdir.is_dir();assert not (ROOT/'.lock').exists();assert set(p.name for p in ROOT.iterdir())=={'popen-gw0','popen-gw1'};assert all(not (ROOT/w/'.lock').exists() for w in ('popen-gw0','popen-gw1'))
old_siblings=sorted(p.name for p in ROOT.parent.iterdir() if p!=ROOT);h1=handles();assert not h1['matches'];first=snapshot();second=snapshot();assert first==second;h2=handles();assert not h2['matches'];assert not (ROOT/'.lock').exists();assert meta(ROOT)==first['root_metadata']
rows=first['members'];counts=collections.Counter(r['kind'] for r in rows.values());groups=collections.defaultdict(list)
for p,r in rows.items():
 if r['kind']=='file':groups[(r['device'],r['inode'])].append(p)
hardlinks=[{'paths':ps,'recorded_nlink':rows[ps[0]]['nlink'],'outside_link_count_unknown_or_observed':max(0,rows[ps[0]]['nlink']-len(ps))} for ps in groups.values() if len(ps)>1 or rows[ps[0]]['nlink']>1]
# Correlation is explicitly weaker than per-path source ownership proof.
census=json.loads(pathlib.Path(owner['complete_private_census']['path']).read_bytes());assert len(census)==1361;stems=collections.defaultdict(set)
for r in census:
 node=r['nodeid'];name=node.split('::')[-1];stems[r['worker']].add(re.sub(r'\W','_',name)[:30])
correlation=[]
for worker in ('gw0','gw1'):
 for p in (ROOT/('popen-'+worker)).iterdir():
  name=p.name;clean=name[:-7] if name.endswith('current') else re.sub(r'\d+$','',name);is_case=clean in stems[worker];correlation.append({'relative':p.relative_to(ROOT).as_posix(),'kind':rows[p.relative_to(ROOT).as_posix()]['kind'],'name_matches_bounded_pytest_node_normalization':is_case,'mtime_ns':p.lstat().st_mtime_ns})
start=release.stat().st_mtime_ns;end=pathlib.Path(owner['root_outer_terminal']['path']).stat().st_mtime_ns;assert start<end
# Raw complete log references to namespace are observations, not authoritative artifact bindings.
raw=pathlib.Path(owner['original_raw_log']['path']).read_text();raw_mentions=raw.count(str(ROOT))
# Scope-bounded authoritative metadata pointer check: external frozen OWNER/FROZEN JSON packets, not all source/caches.
scanned=[];pointers=[];skipped_big=[]
for base in (pathlib.Path('/workspace/engineering'),pathlib.Path('/workspace/actions-cloud/receipts')):
 for parent,dirs,files in os.walk(base,followlinks=False):
  dirs[:]=[n for n in dirs if n not in ('.git','.venv','node_modules','dist','wheelhouse','site-packages','__pycache__','private-original-assets','frozen-layout') and not pathlib.Path(parent,n).is_symlink()]
  for n in files:
   if not n.endswith('.json') or not n.startswith(('OWNERFINAL','FROZEN')):continue
   p=pathlib.Path(parent,n)
   if p.stat().st_size>2*1024*1024:skipped_big.append({'path':str(p),'bytes':p.stat().st_size});continue
   b=p.read_bytes();scanned.append({'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
   if str(ROOT).encode() not in b:continue
   try:x=json.loads(b)
   except ValueError:continue
   def walk(x):
    if isinstance(x,dict):
     q=x.get('path')
     if isinstance(q,str) and (q==str(ROOT) or q.startswith(str(ROOT)+'/')):pointers.append({'receipt':str(p),'referenced_path':q,'bound_SHA':x.get('sha256'),'bound_bytes':x.get('bytes')})
     for v in x.values():walk(v)
    elif isinstance(x,list):
     for v in x:walk(v)
   walk(x)
assert not pointers
inventory={'schema':1,'exact_root':str(ROOT),'original_owner_UID_GID':[1000,1000],'first_and_second_complete_body_metadata_snapshots_equal':True,'first':first,'second_canonical_snapshot_SHA256':hashlib.sha256(json.dumps(second,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'internal_hardlink_groups':hardlinks}
p=D/'private-complete-two-stable-pytest38-body-metadata-inventory.json';assert not p.exists();p.write_text(json.dumps(inventory,sort_keys=True,separators=(',',':'))+'\n');p.chmod(0o600)
private={'schema':1,'owner_sourceFULL':bind(OWNER),'bound_full_originals':refs,'release':bind(release),'command':bind(command),'inventory':bind(p),'member_counts':dict(counts),'member_total':len(rows),'file_bytes':sum(r.get('bytes',0) for r in rows.values()),'unique_regular_inode_body_bytes':sum(rows[ps[0]]['bytes'] for ps in groups.values()),'allocated_bytes_recorded_including_root':sum(r['allocated_bytes'] for r in rows.values())+first['root_metadata']['allocated_bytes'],'internal_hardlink_groups':len(hardlinks),'external_hardlink_count':sum(g['outside_link_count_unknown_or_observed'] for g in hardlinks),'root_real_0700_UIDGID1000':first['root_metadata']['mode']==0o700 and first['root_metadata']['uid']==first['root_metadata']['gid']==1000,'lock_absent_root_and_worker_roots':True,'current_sourcefull_owner_terminal_complete':True,'source_origin':'CORRELATION_ONLY_NOT_EXACT_ORIGIN_PROOF','top_level_worker_case_correlations':correlation,'correlation_counts':dict(collections.Counter(r['name_matches_bounded_pytest_node_normalization'] for r in correlation)),'release_mtime_ns':start,'root_full_outer_terminal_mtime_ns':end,'temporary_worker_entry_mtimes_in_run_window':sum(start<=r['mtime_ns']<=end for r in correlation),'temporary_worker_entry_mtimes_total':len(correlation),'raw_sourcefull_log_namespace_mentions':raw_mentions,'accessible_handle_snapshot_before':h1,'accessible_handle_snapshot_after':h2,'authoritative_OWNER_FROZEN_metadata_pointer_scope':{'scanned_receipts':len(scanned),'skipped_larger_than2MiB':skipped_big,'matched_bound_path_pointers':pointers,'unscanned_and_all_other_global_aliases':'UNKNOWN_NO_UNIVERSAL_REFERENCE_CENSUS'},'scanned_frozen_receipt_bindings':scanned,'prior_sibling_name_inventory_unchanged':old_siblings==sorted(p.name for p in ROOT.parent.iterdir() if p!=ROOT),'prior_sibling_names':old_siblings,'current_tmp_available_bytes':os.statvfs('/tmp').f_bavail*os.statvfs('/tmp').f_frsize,'no_archive_or_remove_or_extract_executed':True,'upstream_disposition':'none'}
p=D/'private-readonly-source-correlation-isolation-and-accessible-reference-proof.json';assert not p.exists();p.write_text(json.dumps(private,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'proof':bind(p),'inventory':bind(D/'private-complete-two-stable-pytest38-body-metadata-inventory.json'),'member_total':len(rows),'member_counts':dict(counts),'allocated_bytes':private['allocated_bytes_recorded_including_root'],'file_bytes':private['file_bytes'],'case_correlation':private['correlation_counts'],'pointer_scope_scanned':len(scanned),'large_receipt_scope_UNKNOWN':len(skipped_big),'handle_matches':len(h1['matches'])+len(h2['matches']),'inaccessible_UNKNOWN':[h1['inaccessible_UNKNOWN'],h2['inaccessible_UNKNOWN']],'tmp_free':private['current_tmp_available_bytes']}))
