"""Real private alias verifier over nine synthetic members; never selected roots."""
import copy,gzip,hashlib,io,json,os,stat,tarfile,tempfile,unittest
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
ns={'__name__':'actual_private_alias_verifier'}
exec(compile((HERE/'exact_original_row_archive_aliases.py').read_bytes(),str(HERE/'exact_original_row_archive_aliases.py'),'exec'),ns)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def row(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p),'mode':oct(p.stat().st_mode&0o777)}
def mtime_ns(n):return str(Decimal(n)/Decimal(1000000000))
class AliasClosure(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='synthetic-nine-alias-',dir=HERE);self.base=Path(self.temp.name);self.root=self.base/'fake-original-root';self.root.mkdir(mode=0o700)
  aliases=[];entries={}
  for i in range(9):
   p=self.root/f'member{i}.txt';p.write_bytes(b'FAKE-'+str(i).encode());p.chmod(0o600)
   s=p.stat();e={'mode':0o600,'mtime_ns':s.st_mtime_ns,'uid':s.st_uid,'gid':s.st_gid,'kind':'file','bytes':s.st_size,'sha256':digest(p)}
   entries[p.name]=e;aliases.append({'original_row':row(p),'member':'Runtime50-robot-output/'+p.name,'expected_member_metadata':e})
  s=self.root.stat();rootmeta={'uid':s.st_uid,'gid':s.st_gid,'mode':0o700,'mtime_ns':s.st_mtime_ns}
  inv=self.base/'immutable-original-inventory.json';inv.write_text(json.dumps({'files':[a['original_row'] for a in aliases]+[{'fixed_fake_other_row':i} for i in range(9)]}));inv.chmod(0o400)
  self.plan={'original_inventory_binding':row(inv),'original_root':str(self.root),'archive_path':str(self.base/'fake-nine.tar.gz'),'full_index_path':str(self.base/'fake-full-index.json.gz'),'mapping_path':str(self.base/'fake-alias-map.json'),'archive_label':'Runtime50-robot-output','expected_root_metadata':rootmeta,'aliases':aliases,'_verified_plan_sha256':'a'*64}
  self.record={'original_namespace':str(self.root),'future_destination':self.plan['archive_path'],'verified':True,'snapshot':{'root':rootmeta,'entries':entries}}
 def tearDown(self):self.temp.cleanup()
 def physical(self):return ns['validate_original_rows_or_alias'](self.plan)
 def archive(self,poison=None):
  archive=Path(self.plan['archive_path'])
  with tarfile.open(archive,'w:gz',format=tarfile.PAX_FORMAT) as tar:
   root=tarfile.TarInfo('Runtime50-robot-output');root.type=tarfile.DIRTYPE;root.mode=0o700;root.uid=self.plan['expected_root_metadata']['uid'];root.gid=self.plan['expected_root_metadata']['gid'];root.pax_headers={'mtime':mtime_ns(self.plan['expected_root_metadata']['mtime_ns'])};tar.addfile(root)
   for index,a in enumerate(self.plan['aliases']):
    meta=a['expected_member_metadata'];m=tarfile.TarInfo(a['member']);m.mode=meta['mode'];m.uid=meta['uid'];m.gid=meta['gid'];m.pax_headers={'mtime':mtime_ns(meta['mtime_ns'])};data=('FAKE-'+str(index)).encode();m.size=len(data)
    if index==0 and poison:
     if poison=='uid':m.uid+=1
     if poison=='mode':m.mode=0o644
     if poison=='mtime':m.pax_headers['mtime']=mtime_ns(meta['mtime_ns']+1)
     if poison=='body':data=b'EVIL-0'
     if poison=='traversal':m.name='Runtime50-robot-output/../member0.txt'
     if poison=='symlink':m.type=tarfile.SYMTYPE;m.linkname='/fake-escape';m.size=0
    tar.addfile(m,io.BytesIO(data) if m.isfile() else None)
    if index==0 and poison=='duplicate':tar.addfile(m,io.BytesIO(data))
  archive.chmod(0o600);self.record['archive_bytes']=archive.stat().st_size;self.record['archive_sha256']=digest(archive)
  records={key:{} for key in ['ToolkitTest','original27-log','fixture42-GREEN-log','fixture51-TEMPORAL-log']};records['Runtime50-robot-output']=self.record
  index=Path(self.plan['full_index_path'])
  with gzip.open(index,'wb') as f:f.write(json.dumps({'status':'EXACT_FIVE_COMPLETED8D49_OWNED_ROOTS_ALL_STAGED_BEFORE_REMOVAL','records':records}).encode())
  index.chmod(0o600)
  mapping={'schema':'DURABLE_FIXED_ORIGINAL_ROW_ARCHIVE_ALIASES','aliases':self.plan['aliases'],'plan_sha256':'a'*64,'full_index':row(index),'archive':row(archive)}
  q=Path(self.plan['mapping_path']);q.write_text(json.dumps(mapping));q.chmod(0o600)
  if self.root.exists():self.root.rename(self.base/'synthetic-hidden-original')
  return mapping
 def test_valid_nine_original_physical_rows(self):self.assertEqual(self.physical()['rows'],9)
 def test_valid_nine_archive_aliases_preserve_absent_original_paths(self):
  self.archive();r=self.physical();self.assertEqual(r['rows'],9);self.assertFalse(r['original_paths_restored']);self.assertFalse(self.root.exists())
 def test_missing_partial_physical_file_cannot_fall_back(self):
  (self.root/'member0.txt').rename(self.root/'unowned-extra.txt')
  with self.assertRaises(AssertionError):self.physical()
 def test_body_poison(self):
  self.archive('body')
  with self.assertRaises(AssertionError):self.physical()
 def test_mode_poison(self):
  self.archive('mode')
  with self.assertRaises(AssertionError):self.physical()
 def test_UID_poison(self):
  self.archive('uid')
  with self.assertRaises(AssertionError):self.physical()
 def test_nanosecond_mtime_poison(self):
  self.archive('mtime')
  with self.assertRaises(AssertionError):self.physical()
 def test_unknown_member_traversal_poison(self):
  self.archive('traversal')
  with self.assertRaises(AssertionError):self.physical()
 def test_duplicate_member_poison(self):
  self.archive('duplicate')
  with self.assertRaises(AssertionError):self.physical()
 def test_symlink_member_poison(self):
  self.archive('symlink')
  with self.assertRaises(AssertionError):self.physical()
 def test_whole_archive_SHA_poison(self):
  self.archive();p=Path(self.plan['archive_path']);p.write_bytes(p.read_bytes()+b'junk')
  with self.assertRaises(AssertionError):self.physical()
 def test_fixed_original_row_cannot_be_rebound(self):
  self.archive();self.plan['aliases'][0]['original_row']['sha256']='0'*64
  with self.assertRaises(AssertionError):self.physical()
 def test_one_alias_omitted_cannot_appear_complete(self):
  self.archive();self.plan['aliases'].pop()
  with self.assertRaises(AssertionError):self.physical()
 def test_missing_fixed_alias_map_refused(self):
  self.archive();Path(self.plan['mapping_path']).rename(self.base/'synthetic-hidden-map')
  with self.assertRaises(AssertionError):self.physical()
 def test_wrong_plan_identity_refused(self):
  self.archive();self.plan['_verified_plan_sha256']='b'*64
  with self.assertRaises(AssertionError):self.physical()
 def test_corrupt_CRC_rejected_after_rebinding_outer_SHA(self):
  mapping=self.archive();p=Path(self.plan['archive_path']);raw=bytearray(p.read_bytes());raw[-8]^=1;p.write_bytes(raw)
  mapping['archive']=row(p);self.record['archive_sha256']=digest(p)
  index=Path(self.plan['full_index_path']);records={k:{} for k in ['ToolkitTest','original27-log','fixture42-GREEN-log','fixture51-TEMPORAL-log']};records['Runtime50-robot-output']=self.record
  with gzip.open(index,'wb') as f:f.write(json.dumps({'status':'EXACT_FIVE_COMPLETED8D49_OWNED_ROOTS_ALL_STAGED_BEFORE_REMOVAL','records':records}).encode())
  mapping['full_index']=row(index);Path(self.plan['mapping_path']).write_text(json.dumps(mapping))
  with self.assertRaises(gzip.BadGzipFile):self.physical()
if __name__=='__main__':unittest.main(verbosity=2)
