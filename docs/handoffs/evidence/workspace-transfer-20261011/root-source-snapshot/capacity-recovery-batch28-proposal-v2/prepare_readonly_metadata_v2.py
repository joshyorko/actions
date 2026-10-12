import os,stat,json,hashlib,subprocess,itertools,time
from pathlib import Path
from collections import Counter,defaultdict
OUT=Path(__file__).parent; BASE=Path('/workspace/actions-cloud/robocorp/temp')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def record(p):
 p=Path(p);s=p.lstat();return {'path':str(p),'bytes':s.st_size,'sha256':sha(p),'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid}
def write(n,d):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(d,sort_keys=True,separators=(',',':'))+'\n');p.chmod(0o600);return record(p)
def metadata(root,body=False):
 rows={};seen=set();a=l=0;kinds=Counter();groups=defaultdict(list)
 for p in [root]+sorted(root.rglob('*')):
  s=p.lstat();key=(s.st_dev,s.st_ino);r={'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'mtime_ns':s.st_mtime_ns,'device':s.st_dev,'inode':s.st_ino,'nlink':s.st_nlink,'allocated':s.st_blocks*512}
  if key not in seen:a+=r['allocated'];seen.add(key)
  if stat.S_ISREG(s.st_mode):
   r.update(kind='file',bytes=s.st_size);l+=s.st_size;groups[key].append((str(p.relative_to(root)),s.st_nlink))
   if body:r['sha256']=sha(p)
  elif stat.S_ISDIR(s.st_mode):r['kind']='directory'
  elif stat.S_ISLNK(s.st_mode):r.update(kind='symlink',target=os.readlink(p))
  elif stat.S_ISFIFO(s.st_mode):r['kind']='fifo'
  else:raise AssertionError('Unsupported member type')
  kinds[r['kind']]+=1;rows[str(p.relative_to(root))]=r
 external=[g for g in groups.values()if any(n!=len(g)for _,n in g)]
 return {'name':root.name,'allocated':a,'logical':l,'members':len(rows)-1,'kinds':dict(kinds),'root':rows['.'],'rows':rows if body else None,'internal_hardlink_groups':[g for g in groups.values()if len(g)>1],'external_hardlink_groups':external}
def handles(names):
 roots=[str(BASE/n)for n in names];matches=[];unknown=0;readable=0
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  links=[p/'cwd']
  try:links+=list((p/'fd').iterdir())
  except PermissionError:unknown+=1
  except FileNotFoundError:continue
  for link in links:
   try:t=os.readlink(link);readable+=1
   except PermissionError:unknown+=1;continue
   except OSError:continue
   if any(t==r or t.startswith(r+'/')for r in roots):matches.append({'pid':p.name,'link':str(link),'target':t})
 return {'accessible_links':readable,'inaccessible':unknown,'matches':matches,'universal_quiescence':'UNKNOWN'}
archives=sorted(set(Path('/tmp').glob('actions-completed-scratch-recovery*/*.tar.gz'))|set(Path('/dev/shm').glob('actions-completed-scratch-recovery*/*.tar.gz')))
indices=sorted(set(Path('/tmp').glob('actions-completed-scratch-recovery*/private-complete-inventory-and-recovery.json'))|set(Path('/dev/shm').glob('actions-completed-scratch-recovery*/private-complete-inventory-and-recovery.json')))
assert len(archives)==61 and len(indices)==27
excluded={p.name.removesuffix('.tar.gz')for p in archives}|{'563d911e4172f035'}
candidates=[]
for p in BASE.iterdir():
 if p.name in excluded or p.is_symlink()or not p.is_dir():continue
 try:
  if(p/'recycle.now').read_text().strip()!='True':continue
 except(OSError,UnicodeError):continue
 r=metadata(p);assert not r['external_hardlink_groups'];r['marker']='True';candidates.append(r)
candidates.sort(key=lambda r:(-r['allocated'],r['name']));target=419430400
count=next(i for i in range(1,len(candidates)+1)if sum(r['allocated']for r in candidates[:i])>=target)
max_previous=sum(r['allocated']for r in candidates[:count-1])
chosen=list(candidates[:count]); examinations=0;budget=50000;swap_count=0
while sum(r['allocated']for r in chosen)>target and examinations<budget:
 best=None;present={r['name']for r in chosen};total=sum(r['allocated']for r in chosen)
 for i,r in enumerate(chosen):
  for q in candidates:
   if q['name']in present:continue
   examinations+=1
   value=total-r['allocated']+q['allocated']
   if target<=value<total:
    key=(value,q['name'],r['name'])
    if best is None or key<best[0]:best=(key,i,q)
   if examinations>=budget:break
  if examinations>=budget:break
 if best is None:break
 chosen[best[1]]=best[2];swap_count+=1
names=sorted(r['name']for r in chosen)
selection=write('private-complete-completed-candidate-census-and-exact-selection.json',{'candidates':candidates,'count':len(candidates),'allocated_total':sum(r['allocated']for r in candidates),'target':target,'minimum_count':count,'max_fewer_count_allocated':max_previous,'bounded_single_replacement_examinations':examinations,'budget':budget,'swaps':swap_count,'selection':chosen,'names':names,'sum_exact_target':sum(r['allocated']for r in chosen)==target,'global_minimum_sum_claim':sum(r['allocated']for r in chosen)==target,'all512MiB_impossible':sum(r['allocated']for r in candidates)<536870912})
print(json.dumps({'phase':'SELECTED','count':count,'allocated':sum(r['allocated']for r in chosen),'logical':sum(r['logical']for r in chosen),'members':sum(r['members']for r in chosen),'bounded_examinations':examinations,'global_sum_optimal':sum(r['allocated']for r in chosen)==target }),flush=True)
h1=handles(names);assert not h1['matches']
first={n:metadata(BASE/n,True)for n in names}
for n,d in first.items():assert(BASE/n/'recycle.now').read_text().strip()=='True' and not d['external_hardlink_groups']
prior=[record(p)for p in archives+indices]
print(json.dumps({'phase':'PRIOR_REHASHED','archives':len(archives),'indices':len(indices)}),flush=True)
ctxpath=Path('/workspace/engineering/pytest38-completed-preservation-private-source/private-current396-data-only-guard-and-exact-pytest38-inputs.json');ctx=json.loads(ctxpath.read_text());R=Path(ctx['source_root'])
assert subprocess.check_output(['git','--no-optional-locks','-C',str(R),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[ctx['current_head'],ctx['current_tree']]
assert not subprocess.check_output(['git','--no-optional-locks','-C',str(R),'status','--porcelain=v1'])
for r in ctx['current_rows']:
 p=R/r['path'];b=os.readlink(p).encode()if r['mode']=='120000'else p.read_bytes();assert len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256']and stat.S_IMODE(p.lstat().st_mode)==r['fs_mode']
for name,h in ctx['prepared_inputs'].items():assert sha(R/name)==h
native=Path(ctx['native_root'])
for r in ctx['native_members']:
 p=native/r['path'];assert stat.S_IMODE(p.lstat().st_mode)==r['mode']
 if r['kind']=='file':assert sha(p)==r['content_sha256']
 elif r['kind']=='symlink':assert os.readlink(p)==r['link_target']
 else:assert p.is_dir()and not p.is_symlink()
assert{p.relative_to(native).as_posix()for p in native.rglob('*')}=={r['path']for r in ctx['native_members']}
retained=[record(p)for p in [ctxpath,Path('/workspace/engineering/pr308-native-home-mode-current-a54-SOURCE-LIGHT/OWNERFINAL-current396925-public-native-home-mode-and-a54-union-SOURCE_LIGHT.json'),Path('/workspace/engineering/rcc-current-e4ff-control3-actual-independent-review/OWNERFINAL-independent-original-current-e4ff-control3-cache-mode-actual-failure-review.json'),Path('/workspace/engineering/root-failed-control3-one-byte-preservation-v4/root-exact-historical-failed-member-archive-mapping.json')]]
failed_owner=json.loads(Path(retained[2]['path']).read_text());write('private-failed2-owner-binding-data.json',failed_owner)
# Exact failed2 stable file set captured for later execution guards; owner references are separately preserved.
failed=Path('/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-2')
failed_refs=[record(p)for p in sorted(failed.glob('*'))if p.is_file()and not p.is_symlink()]
assert any(r['sha256']=='d4ebd4111e362d3ac3f8dc519d3826ad19c71e1d06dffe7dd959a4ebd2b45ca8'for r in failed_refs)
assert Path(ctx['failed563_existence_only']).exists()
second={n:metadata(BASE/n,True)for n in names};assert first==second
h2=handles(names);assert not h2['matches']
assert [record(p)for p in archives+indices]==prior
for r in retained+failed_refs:assert record(r['path'])==r
inventory=write('private-two-complete-selected-body-metadata-inventories.json',{'first':first,'second_sha256':hashlib.sha256(json.dumps(second,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'two_complete_snapshots_equal':True,'first_sha256':hashlib.sha256(json.dumps(first,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'handles_before':h1,'handles_after':h2})
ret=write('private-all61-original-archives27-indices-current-source-native-failed2-retention.json',{'prior':prior,'source_guard_input':retained,'current_head':ctx['current_head'],'current_tree':ctx['current_tree'],'current_source_leaves':len(ctx['current_rows']),'prepared_inputs':len(ctx['prepared_inputs']),'native_members':len(ctx['native_members']),'failed2_original_files':failed_refs,'failed563':'EXISTENCE_ONLY','all_before_after_equal':True})
relocations=[{'archive':r,'allocated':Path(r['path']).stat().st_blocks*512}for r in prior[:len(archives)]if str(r['path']).startswith('/tmp/')and 100*1024*1024<=r['bytes']<=200*1024*1024]
capacity={p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in ['/workspace','/tmp','/dev/shm']}
summary={'selection':selection,'inventory':inventory,'retention':ret,'selected_names':names,'allocated':sum(r['allocated']for r in chosen),'logical':sum(r['logical']for r in chosen),'members':sum(r['members']for r in chosen),'minimal_count':count,'metadata_census_count':len(candidates),'complete_total_allocated':sum(r['allocated']for r in candidates),'capacity':capacity,'handles':[h1,h2],'relocation_candidates':relocations,'current_head':ctx['current_head'],'current_tree':ctx['current_tree'],'native':len(ctx['native_members']),'source_leaves':len(ctx['current_rows']),'failed2_file_count':len(failed_refs)}
write('private-final-readonly-summary.json',summary)
print(json.dumps({'phase':'READONLY_PREPARATION_PASS','selected_count':count,'members':summary['members'],'allocated':summary['allocated'],'prior_archives':61,'prior_indices':27,'source':summary['source_leaves'],'native':summary['native'],'relocation_candidates':len(relocations),'capacity':capacity}),flush=True)
