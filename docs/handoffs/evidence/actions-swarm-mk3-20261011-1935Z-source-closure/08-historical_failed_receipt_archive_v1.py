"""Data-only exact historical receipt alias; no restoration or execution."""
import gzip,hashlib,json,stat,tarfile
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def check_current_file(row):
 p=Path(row['path']);assert p.is_file() and not p.is_symlink()
 assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
 assert oct(stat.S_IMODE(p.stat().st_mode))==row['mode']

def verify_exact_historical_receipt(row, mapping_binding):
 # One operator-reviewed alias only; preserve original path/hash provenance.
 maprow=mapping_binding
 check_current_file(maprow)
 mapping=json.loads(Path(maprow['path']).read_text())
 assert mapping['status']=='EXACT_HISTORICAL_FAILED_MEMBER_PRESERVATION_MAPPING_NOT_ACTUAL_ACCEPTANCE'
 assert type(mapping['schema']) is int and mapping['schema']==1
 assert row==mapping['original_binding']
 assert not Path(row['path']).exists() and not Path(row['path']).is_symlink()
 assert mapping['original_status']=='FAIL' and mapping['original_cleanup']=='FAIL_UNCHANGED'
 assert mapping['all_original49132_members_preserved'] is True and mapping['original_path_absent'] is True and mapping['no_original_path_restoration'] is True
 for key in ('archive','complete_index','expanded_removal','root_original_terminal'):check_current_file(mapping[key])
 archive=Path(mapping['archive']['path']);seen=set();found=None
 from pathlib import PurePosixPath
 with gzip.open(archive,'rb') as decoded:
  with tarfile.open(fileobj=decoded,mode='r|') as tar:
   for member in tar:
    path=PurePosixPath(member.name)
    assert not path.is_absolute() and '..' not in path.parts and member.name not in seen
    seen.add(member.name)
    if member.name==mapping['member']:
     assert found is None and member.isfile() and not member.islnk() and not member.issym()
     assert member.size==row['bytes']==1696 and member.mode==0o600
     assert member.uid==mapping['member_uid']==1000 and member.gid==mapping['member_gid']==1000
     stream=tar.extractfile(member);assert stream is not None
     found=stream.read(1697);assert len(found)==1696 and hashlib.sha256(found).hexdigest()==row['sha256']
  while decoded.read(1024*1024):pass  # Force gzip EOF/CRC/ISIZE verification.
 assert found is not None
 payload=json.loads(found);assert payload['status']=='FAIL' and payload['outcome']['cleanup']['status']=='FAIL'
 return {'original_binding':row,'archive':mapping['archive'],'member':mapping['member'],'original_status':'FAIL','qualification':'HISTORICAL_PRESERVATION_ONLY_NO_ACTUAL_ACCEPTANCE'}

