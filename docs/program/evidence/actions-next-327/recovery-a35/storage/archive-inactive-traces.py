from pathlib import Path
import gzip,hashlib,json,os,shutil,stat
import psutil
base=Path('/workspace/actions-recovery-327/evidence')
groups=['a30-frozen-portable','a33-source-task-joined','a34-source-task-host-joined','a33-source-historical','a33-source-historical-corrected','a32-source-review-final','a32-source-provider-detached','a30-source-joined']
paths=[p for group in groups for p in (base/group/'log').glob('*.robolog')]
assert paths and all(p.is_relative_to(base) for p in paths)
opened=set()
for proc in psutil.process_iter(['pid','uids']):
 try:
  if proc.uids().real==os.getuid():opened.update(f.path for f in proc.open_files())
 except (psutil.NoSuchProcess,psutil.AccessDenied):continue
assert not set(map(str,paths))&opened,'trace still open'
def digest(path,compressed=False):
 h=hashlib.sha256()
 with (gzip.open(path,'rb') if compressed else path.open('rb')) as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
receipt={'purpose':'lossless archival of inactive task-created raw traces; human-readable HTML and all other evidence remain unchanged','before_free':shutil.disk_usage(base).free,'archives':[]}
for p in paths:
 before=p.lstat();assert stat.S_ISREG(before.st_mode) and before.st_uid==os.getuid() and before.st_nlink==1 and not p.is_symlink()
 target=p.with_suffix(p.suffix+'.gz');assert not target.exists()
 rawhash=digest(p)
 with p.open('rb') as src,target.open('xb') as dst:
  with gzip.GzipFile(filename='',fileobj=dst,mode='wb',compresslevel=6,mtime=0) as zipped:shutil.copyfileobj(src,zipped,1024*1024)
 assert digest(target,True)==rawhash
 after=p.stat();assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
 receipt['archives'].append({'original':str(p.relative_to(base)),'archive':str(target.relative_to(base)),'original_sha256':rawhash,'archive_sha256':digest(target),'original_bytes':before.st_size,'archive_bytes':target.stat().st_size})
 p.unlink()
receipt['after_free']=shutil.disk_usage(base).free
(base/'inactive-trace-archives.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'files':len(paths),'original_bytes':sum(x['original_bytes'] for x in receipt['archives']),'archive_bytes':sum(x['archive_bytes'] for x in receipt['archives']),'free_bytes':receipt['after_free']}))
