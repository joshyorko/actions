"""Validate this exact public-only RCC catalog export before supported import."""
import gzip,hashlib,json,posixpath,re,zipfile
from pathlib import Path,PurePosixPath
HASH='REQUIRED_FRESH_ARCHIVE_SHA256'
SIZE=0
ROOT=Path('/tmp/actions327-a44-offline-v1/compiler')
CATALOGS={'05bce139c5c902c0v12.linux_amd64','4240e3dcbf7fa40dv12.linux_amd64'}
def validate(path):
 import sys
 if sys.flags.optimize:raise RuntimeError('Optimized Python disables qualification checks')
 assert path.is_file() and path.stat().st_size==SIZE
 assert hashlib.sha256(path.read_bytes()).hexdigest()==HASH
 summary={'archive_sha256':HASH,'archive_bytes':path.stat().st_size,'catalogs':[],'links':0,'files':0}
 with zipfile.ZipFile(path) as z:
  names=z.namelist();assert len(names)==len(set(names))
  assert sum(i.file_size for i in z.infolist())<100*1024**2
  assert {n.removeprefix('catalog/') for n in names if n.startswith('catalog/')}==CATALOGS
  for name in names:
   assert not name.startswith('/') and '..' not in PurePosixPath(name).parts
   assert re.fullmatch(r'library/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{64}',name) or name in {'catalog/'+n for n in CATALOGS}
  for catalog in sorted(CATALOGS):
   with gzip.GzipFile(fileobj=__import__('io').BytesIO(z.read('catalog/'+catalog))) as stream:
    raw=stream.read(8*1024**2+1);assert len(raw)<=8*1024**2
   d=json.loads(raw)
   assert Path(d['path']).parent==ROOT/'robocorp/holotree'
   assert Path(d['path']).name==d['identity'] and d['platform']=='linux_amd64'
   assert d['rcc']=='v18.19.3'
   def walk(node,prefix=''):
    for kind in ('files','subdirs'):
     for name,value in node.get(kind,{}).items():
      assert name not in ('','.','..') and '/' not in name and value['name']==name
      if kind=='subdirs':walk(value,prefix+name+'/');continue
      summary['files']+=1
      if 'symlink' in value:
       target=posixpath.normpath(posixpath.join(prefix,value['symlink']))
       assert target!='..' and not target.startswith(('../','/'))
       summary['links']+=1
   walk(d['tree']);summary['catalogs'].append({'name':catalog,'path':d['path']})
 return summary
if __name__=='__main__':
 import sys
 print(json.dumps(validate(Path(sys.argv[1])),indent=2))
