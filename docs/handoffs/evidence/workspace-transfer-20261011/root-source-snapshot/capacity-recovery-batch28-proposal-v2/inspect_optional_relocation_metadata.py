import os,json,hashlib,stat,tarfile,gzip
from pathlib import Path
O=Path(__file__).parent
s=json.loads((O/'private-final-readonly-summary.json').read_text());r=json.loads(Path(s['retention']['path']).read_text())['prior']
a=min((x for x in r if x['path'].startswith('/tmp/')and x['path'].endswith('.tar.gz')and x['bytes']>=134217728),key=lambda x:(x['bytes'],x['path']));p=Path(a['path']);index=p.parent/'private-complete-inventory-and-recovery.json';ix=json.loads(index.read_text());record=next(x for x in ix['records']if x['archive']==str(p));entries=record['inventory'];name=p.name.removesuffix('.tar.gz');seen={};root_count=0;hardlinks=0;kinds={}
def sha(q):
 h=hashlib.sha256()
 with Path(q).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(q):
 q=Path(q);z=q.lstat();return {'path':str(q),'bytes':z.st_size,'sha256':sha(q),'mode':stat.S_IMODE(z.st_mode),'uid':z.st_uid,'gid':z.st_gid,'mtime_ns':z.st_mtime_ns,'device':z.st_dev,'inode':z.st_ino,'nlink':z.st_nlink,'allocated':z.st_blocks*512}
before=bind(p);assert all(before[k]==a[k]for k in ('bytes','sha256','mode','uid','gid'))
assert before['bytes']==record['archive_bytes']and before['sha256']==record['archive_sha256']and record['expanded_removed'] is True
with tarfile.open(p,'r|gz')as t:
 for m in t:
  if m.name==name:root_count+=1;assert root_count==1 and m.isdir();continue
  assert m.name.startswith(name+'/');rel=m.name[len(name)+1:];assert rel not in seen and rel in entries and '..'not in Path(rel).parts and not Path(rel).is_absolute()
  e=entries[rel];assert (m.mode,m.uid,m.gid)==(e['mode'],e['uid'],e['gid']);k=e['kind'];kinds[k]=kinds.get(k,0)+1
  if k=='file':
   if m.islnk():
    target=m.linkname;assert target.startswith(name+'/');target=target[len(name)+1:];assert target in seen;assert seen[target].get('bytes')==e['bytes']and seen[target].get('sha256')==e['sha256'];hardlinks+=1
   else:
    assert m.isfile();h=hashlib.sha256();n=0;stream=t.extractfile(m)
    for b in iter(lambda:stream.read(1048576),b''):h.update(b);n+=len(b)
    assert n==e['bytes']and h.hexdigest()==e['sha256']
  elif k=='directory':assert m.isdir()
  elif k=='symlink':assert m.issym()and m.linkname==e['target']
  elif k=='fifo':assert m.isfifo()
  else:raise AssertionError('Unsupported type')
  seen[rel]=e
assert set(seen)==set(entries)and root_count==1 and len(seen)==record['verified_members']
with gzip.open(p,'rb')as f:
 for b in iter(lambda:f.read(1048576),b''):pass
assert bind(p)==before
out={'status':'READONLY_SINGLE_ORIGINAL_ARCHIVE_RELOCATION_CANDIDATE_PROVEN_NO_COPY_REMOVE','archive_original':before,'index_original':bind(index),'verified_original_member_count':len(seen),'root_headers':root_count,'kinds':kinds,'internal_hardlink_headers':hardlinks,'whole_gzip_EOF_CRC_ISIZE':True,'whole_SHA_before_after_equal':True,'old_NS_tar_precision':'NOT_CLAIMED; byte-identical future archive copy preserves observed original TAR bytes','future_destination':'/workspace/engineering/retained-capacity-archives-B28-relocation/dd09121ba364f685.tar.gz','original_index_and_all_other_archives':'remain unchanged and in place; old exact archive path becomes historical only after separately reviewed mapping and one authorized source removal','NOT_RUN':['copy','destination_creation','source_removal','restoration','native','installer','gateway']}
p=O/'private-optional-single-original-archive-relocation-readonly-full-member-proof.json';assert not p.exists();p.write_text(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n');p.chmod(0o600)
print(json.dumps({'status':'READONLY_ORIGINAL_RELOCATION_CANDIDATE_PASS','archive_bytes':before['bytes'],'members':len(seen),'gzipEOF':True,'hardlink_headers':hardlinks,'proof_bytes':p.stat().st_size,'proof_sha256':sha(p)}))
