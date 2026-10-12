"""Data-only exact original-row archive aliases; no extraction or restoration."""
import gzip,hashlib,json,os,stat,tarfile
from pathlib import Path,PurePosixPath

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()

def binding(row):
 p=Path(row['path']);s=p.lstat()
 assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 assert s.st_size==row['bytes'] and sha(p)==row['sha256'] and oct(stat.S_IMODE(s.st_mode))==row['mode']

def metadata(s,e):
 assert stat.S_IMODE(s.st_mode)==e['mode'] and s.st_uid==e['uid'] and s.st_gid==e['gid'] and s.st_mtime_ns==e['mtime_ns']

def validate_original_rows_or_alias(plan):
 binding(plan['original_inventory_binding'])
 inventory=json.loads(Path(plan['original_inventory_binding']['path']).read_bytes())
 rows=[a['original_row'] for a in plan['aliases']]
 assert len(rows)==9 and len({r['path'] for r in rows})==9
 assert all(r in inventory['files'] for r in rows)
 root=Path(plan['original_root']);assert not root.is_symlink()
 if root.exists():
  assert root.is_dir() and not root.is_symlink()
  metadata(root.lstat(),plan['expected_root_metadata'])
  assert set(str(x.relative_to(root)) for x in root.rglob('*'))==set(a['member'][len(plan['archive_label'])+1:] for a in plan['aliases'])
  for alias in plan['aliases']:
   row=alias['original_row'];p=Path(row['path'])
   assert p.is_relative_to(root) and str(PurePosixPath(plan['archive_label'])/p.relative_to(root))==alias['member']
   binding(row);metadata(p.lstat(),alias['expected_member_metadata'])
  return {'mode':'EXACT_ORIGINAL_PHYSICAL_ROWS','rows':9}
 mapping=Path(plan['mapping_path']);assert mapping.is_file() and not mapping.is_symlink() and stat.S_IMODE(mapping.stat().st_mode)==0o600
 assert mapping.stat().st_size<=16777216
 data=json.loads(mapping.read_bytes())
 assert data['schema']=='DURABLE_FIXED_ORIGINAL_ROW_ARCHIVE_ALIASES' and data['aliases']==plan['aliases']
 assert data['plan_sha256']==plan['_verified_plan_sha256']
 assert data['full_index']['path']==plan['full_index_path'] and data['archive']['path']==plan['archive_path']
 binding(data['full_index']);binding(data['archive'])
 for path in [mapping,Path(data['full_index']['path']),Path(data['archive']['path'])]:
  assert path.stat().st_uid==plan['expected_root_metadata']['uid'] and path.stat().st_gid==plan['expected_root_metadata']['gid']
 assert data['full_index']['mode']==data['archive']['mode']=='0o600'
 with gzip.open(plan['full_index_path'],'rb') as stream:
  raw=stream.read(33554433);assert len(raw)<=33554432 and stream.read(1)==b''
 full=json.loads(raw);assert full['status']=='EXACT_FIVE_COMPLETED8D49_OWNED_ROOTS_ALL_STAGED_BEFORE_REMOVAL' and len(full['records'])==5
 record=full['records'][plan['archive_label']]
 assert record['original_namespace']==plan['original_root'] and record['future_destination']==plan['archive_path']
 assert record['archive_bytes']==data['archive']['bytes'] and record['archive_sha256']==data['archive']['sha256'] and record['verified'] is True
 assert record['snapshot']['root']==plan['expected_root_metadata']
 # Entire gzip EOF forces CRC/ISIZE verification even after TAR end markers.
 with gzip.open(plan['archive_path'],'rb') as stream:
  total=0
  for block in iter(lambda:stream.read(1048576),b''):
   total+=len(block);assert total<=sum(a['original_row']['bytes'] for a in plan['aliases'])+1048576
 with tarfile.open(plan['archive_path'],'r:gz') as tar:
  members=tar.getmembers();names=[m.name for m in members]
  assert len(names)==len(set(names))==10 and set(names)=={plan['archive_label']}|{a['member'] for a in plan['aliases']}
  for m in members:
   path=PurePosixPath(m.name);assert not path.is_absolute() and '..' not in path.parts and str(path)==m.name
  directory=tar.getmember(plan['archive_label']);expected_root=plan['expected_root_metadata']
  assert directory.isdir() and directory.mode==expected_root['mode'] and directory.uid==expected_root['uid'] and directory.gid==expected_root['gid']
  from decimal import Decimal
  assert Decimal(directory.pax_headers['mtime'])*1000000000==expected_root['mtime_ns']
  for alias in plan['aliases']:
   row=alias['original_row'];e=alias['expected_member_metadata'];m=tar.getmember(alias['member'])
   assert record['snapshot']['entries'][m.name[len(plan['archive_label'])+1:]]==e
   assert m.isfile() and m.size==row['bytes'] and m.mode==e['mode'] and m.uid==e['uid'] and m.gid==e['gid']
   assert Decimal(m.pax_headers['mtime'])*1000000000==e['mtime_ns']
   h=hashlib.sha256();count=0
   f=tar.extractfile(m)
   for block in iter(lambda:f.read(1048576),b''):count+=len(block);h.update(block);assert count<=row['bytes']
   assert count==row['bytes'] and h.hexdigest()==row['sha256']
 return {'mode':'VERIFIED_ARCHIVE_MEMBER_DATA_ALIAS_ORIGINAL_PATH_ABSENT','rows':9,'original_paths_restored':False,'original_inventory_rewritten':False}
