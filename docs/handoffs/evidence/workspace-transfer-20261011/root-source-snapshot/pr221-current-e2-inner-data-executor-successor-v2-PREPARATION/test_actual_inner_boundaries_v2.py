"""Service-free controls of frozen real inspector functions; never package imports."""
import ast,base64,csv,gzip,hashlib,io,json,os,stat,tarfile,types,zipfile
from pathlib import Path
import pytest
EXECUTOR=Path(__file__).parent/'inspect_current_e2_inner_once_v2.py'
EXECUTOR_SHA='d83a7aae88a98a694310e6a1e60de2ea7e362604ee8c5d345cc6a38b4591177c'
WHEEL='actions_runtime-1.0.3-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl'
ROOT='actions_runtime-1.0.3.dist-info/'
SDROOT='actions_runtime-1.0.3/'

@pytest.fixture(scope='module')
def ctx():
 data=EXECUTOR.read_bytes();assert hashlib.sha256(data).hexdigest()==EXECUTOR_SHA
 tree=ast.parse(data)
 module=ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.Assign,ast.FunctionDef))],type_ignores=[])
 ns={'__file__':str(EXECUTOR),'__name__':'CONTROL_REAL_AST_NOT_MAIN'}
 exec(compile(module,str(EXECUTOR),'exec'),ns)
 ns['configure_source']()
 package={p.removeprefix('action_server/src/'):ns['git']('cat-file',kind,oid) for p,(mode,kind,oid) in ns['GIT_FILES'].items() if p.startswith('action_server/src/actions/')}
 assert len(package)==217 and sum(p.endswith('.py') for p in package)==202
 package['actions/server/_oauth2_config.py']=b"FILE_CONTENTS = {'actions_config':'', 'default_user_config':''}\n"
 deps=[]
 for name,item in ns['EXPECTED_DEPS'].items():
  extras='['+','.join(item['extras'])+']' if item['extras'] else ''
  terms=','.join(op+'.'.join(map(str,v)) for op,v in item['constraints'])
  deps.append('Requires-Dist: '+name+extras+' ('+terms+')')
 metadata=('Metadata-Version: 2.1\nName: actions-runtime\nVersion: 1.0.3\nRequires-Python: >=3.12,<3.14\n'+'\n'.join(deps)+'\n\n').encode()
 wh=b'Wheel-Version: 1.0\nRoot-Is-Purelib: false\n'+b''.join(('Tag: cp312-cp312-'+p+'\n').encode() for p in ['manylinux_2_5_x86_64','manylinux1_x86_64','manylinux_2_17_x86_64','manylinux2014_x86_64'])
 ep=b'[console_scripts]\naction-server = actions.server.cli:main\n'
 return ns,package,metadata,wh,ep

def wheel_payload(ctx):
 ns,package,metadata,wh,ep=ctx
 return dict(package)|{'actions/server/bin/rcc-18.19.3':b'synthetic-data-not-executable',ROOT+'METADATA':metadata,ROOT+'WHEEL':wh,ROOT+'entry_points.txt':ep}

def make_wheel(payload,record_poison=None):
 payload=dict(payload)
 rows=[[p,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(b).digest()).decode().rstrip('='),str(len(b))] for p,b in payload.items()]+[[ROOT+'RECORD','','']]
 if record_poison=='missing':rows.pop(0)
 elif record_poison=='extra':rows.append(['actions/foreign','sha256=x','1'])
 elif record_poison=='duplicate':rows.append(rows[0])
 elif record_poison=='malformed':rows[0]=rows[0][:2]
 elif record_poison=='hash':rows[0][1]='sha256=wrong'
 elif record_poison=='size':rows[0][2]=str(int(rows[0][2])+1)
 elif record_poison=='selfhash':rows[-1][1]='sha256=wrong'
 elif record_poison=='foreignblank':rows[0][1]=rows[0][2]=''
 out=io.StringIO();csv.writer(out).writerows(rows);payload[ROOT+'RECORD']=out.getvalue().encode()
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for p,b in payload.items():
   i=zipfile.ZipInfo(p);i.create_system=3;i.external_attr=(stat.S_IFREG|0o644)<<16;z.writestr(i,b,compress_type=zipfile.ZIP_DEFLATED)
 return buf.getvalue()

def set_reference(ns,name,data):
 ns['CURRENT_INNER']={'outer_original':{'sha256':'synthetic-fixture-no-original-overwrite'},'member':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def inspect_wheel(ctx,data):
 ns=ctx[0];set_reference(ns,WHEEL,data);return ns['inspect_wheel'](WHEEL,data,'Linux')

def make_sdist(ctx,poison=None):
 ns,package,metadata,wh,ep=ctx
 payload={SDROOT+'src/'+p:b for p,b in package.items()}|{SDROOT+'PKG-INFO':metadata,SDROOT+'pyproject.toml':ns['git']('show',ns['SOURCE']+':action_server/pyproject.toml')}
 if poison=='RCC':payload[SDROOT+'src/actions/server/bin/rcc-18.19.3']=b'not-native'
 elif poison=='missing':payload.pop(SDROOT+'src/actions/server/README.md')
 elif poison=='foreign':payload[SDROOT+'src/actions/server/foreign.py']=b''
 elif poison=='case':payload[SDROOT+'src/actions/server/readme.md']=b''
 elif poison=='root':payload['foreign-root/item']=b''
 buf=io.BytesIO()
 with tarfile.open(fileobj=buf,mode='w') as t:
  for p,b in payload.items():
   m=tarfile.TarInfo(p);m.mode=0o644;m.size=len(b)
   if poison in ('link','fifo') and p.endswith('/README.md'):
    m.type=tarfile.SYMTYPE if poison=='link' else tarfile.FIFOTYPE;m.linkname='other';m.size=0;t.addfile(m)
   elif poison=='singlecap' and p.endswith('/README.md'):
    m.size=64*1024*1024+1;t.addfile(m)
   else:t.addfile(m,io.BytesIO(b))
 data=gzip.compress(buf.getvalue())
 if poison=='CRC':data=data[:-8]+bytes([data[-8]^1])+data[-7:]
 if poison=='ISIZE':data=data[:-4]+bytes([data[-4]^1])+data[-3:]
 return data

def inspect_sdist(ctx,data):
 ns=ctx[0];name='actions_runtime-1.0.3.tar.gz';set_reference(ns,name,data);return ns['inspect_sdist'](name,data)

def test_complete_current_layout_wheel_and_sdist_baseline(ctx):
 w=inspect_wheel(ctx,make_wheel(wheel_payload(ctx)));s=inspect_sdist(ctx,make_sdist(ctx))
 assert w['package_member_count']==219 and w['package_python_member_count']==203
 assert w['record']['rows']==223 and w['record']['hashed_rows']==222
 assert w['source_comparison']['body_equal_count']==217 and s['source_comparison']['body_equal_count']==217
 assert w['generated_input_authority']==s['generated_input_authority']=='HOLD'

@pytest.mark.parametrize('poison',['missing','extra','duplicate','malformed','hash','size','selfhash','foreignblank'])
def test_RECORD_poison_independent_restored_baseline(ctx,poison):
 with pytest.raises((AssertionError,ValueError,KeyError)):inspect_wheel(ctx,make_wheel(wheel_payload(ctx),poison))
 assert inspect_wheel(ctx,make_wheel(wheel_payload(ctx)))['record']['rows']==223

@pytest.mark.parametrize('poison',['missing','foreign','wrongRCC','metadata','tag','entrypoint'])
def test_wheel_source_generated_metadata_poisons(ctx,poison):
 p=wheel_payload(ctx)
 if poison=='missing':p.pop('actions/server/README.md')
 elif poison=='foreign':p['actions/server/foreign.py']=b''
 elif poison=='wrongRCC':p['actions/server/bin/rcc-18.19.3.exe']=p.pop('actions/server/bin/rcc-18.19.3')
 elif poison=='metadata':p[ROOT+'METADATA']=p[ROOT+'METADATA'].replace(b'Version: 1.0.3',b'Version: 1.0.4')
 elif poison=='tag':p[ROOT+'WHEEL']=p[ROOT+'WHEEL'].replace(b'cp312',b'cp313')
 elif poison=='entrypoint':p[ROOT+'entry_points.txt']=b'[console_scripts]\naction-server = foreign:main\n'
 with pytest.raises((AssertionError,ValueError,KeyError)):inspect_wheel(ctx,make_wheel(p))
 assert inspect_wheel(ctx,make_wheel(wheel_payload(ctx)))['source_comparison']['body_equal_count']==217

@pytest.mark.parametrize('poison',['RCC','missing','foreign','case','root','link','fifo','singlecap','CRC','ISIZE'])
def test_sdist_restored_baseline_poisons(ctx,poison):
 with pytest.raises((AssertionError,ValueError,KeyError,tarfile.TarError,gzip.BadGzipFile,EOFError)):inspect_sdist(ctx,make_sdist(ctx,poison))
 assert inspect_sdist(ctx,make_sdist(ctx))['source_comparison']['body_equal_count']==217

class ReadReached(Exception):pass
class HeadersOnly:
 def __init__(self,infos):self.infos=infos;self.reads=[]
 def infolist(self):return self.infos
 def read(self,i):self.reads.append(i.filename);raise ReadReached

def header(name,size=0,mode=stat.S_IFREG|0o644):
 i=zipfile.ZipInfo(name);i.file_size=size;i.external_attr=mode<<16;return i

@pytest.mark.parametrize('poison',['special','encrypted','traversal','absolute','backslash','case','duplicate','directorysize','singlecap','sumcap','entrycap'])
def test_all_ZIP_headers_refused_before_any_payload_read(ctx,poison):
 rows=[header('valid')]
 if poison=='special':rows.append(header('bad',mode=stat.S_IFIFO|0o600))
 elif poison=='encrypted':i=header('bad');i.flag_bits=1;rows.append(i)
 elif poison=='traversal':rows.append(header('../bad'))
 elif poison=='absolute':rows.append(header('/bad'))
 elif poison=='backslash':rows.append(header('bad\\file'))
 elif poison=='case':rows.append(header('VALID'))
 elif poison=='duplicate':rows.append(header('valid'))
 elif poison=='directorysize':rows.append(header('bad/',1,stat.S_IFDIR|0o700))
 elif poison=='singlecap':rows.append(header('bad',64*1024*1024+1))
 elif poison=='sumcap':rows=[header('a',64*1024*1024),header('b',64*1024*1024),header('c',1)]
 elif poison=='entrycap':rows=[header('f'+str(i)) for i in range(5001)]
 spy=HeadersOnly(rows)
 with pytest.raises(AssertionError):ctx[0]['zip_payload'](spy)
 assert spy.reads==[]

@pytest.mark.parametrize('boundary',['single64','sum128','entry5000'])
def test_exact_ZIP_cap_header_boundaries_admitted(ctx,boundary):
 rows=[header('a',64*1024*1024)] if boundary=='single64' else [header('a',64*1024*1024),header('b',64*1024*1024)] if boundary=='sum128' else [header('f'+str(i)) for i in range(5000)]
 spy=HeadersOnly(rows)
 with pytest.raises(ReadReached):ctx[0]['zip_payload'](spy)
 assert len(spy.reads)==1

@pytest.mark.parametrize('poison',['member','size','digest'])
def test_inner_reference_identity_poison(ctx,poison):
 ns=ctx[0];set_reference(ns,'owned',b'body')
 if poison=='member':ns['CURRENT_INNER']['member']='foreign'
 elif poison=='size':ns['CURRENT_INNER']['bytes']=5
 else:ns['CURRENT_INNER']['sha256']='0'*64
 with pytest.raises(AssertionError):ns['immutable_inner_reference']('owned',b'body')

def test_body_and_mode_differences_remain_HOLD_without_normalization(ctx):
 p=wheel_payload(ctx);p['actions/server/README.md']+=b'changed'
 r=inspect_wheel(ctx,make_wheel(p));assert r['source_comparison']['body_difference_count']==1 and r['generated_input_authority']=='HOLD'
 ns=ctx[0];source=ns['git']('show',ns['SOURCE']+':action_server/src/actions/server/README.md')
 r=ns['source_compare']({'actions/server/README.md':(source,stat.S_IFREG|0o755,3)},'','action_server/src/')
 assert r['comparisons'][0]['executable_bit_equal'] is False

@pytest.mark.parametrize('poison',['mode','symlink','directory','array'])
def test_real_private_release_guard(ctx,tmp_path,poison):
 ns=ctx[0];p=tmp_path/'release';p.write_text('{}');p.chmod(0o600)
 assert ns['read_private_root_release'](p)=={}
 if poison=='mode':p.chmod(0o644)
 elif poison=='symlink':q=tmp_path/'link';q.symlink_to(p);p=q
 elif poison=='directory':p=tmp_path
 elif poison=='array':p.write_text('[]')
 with pytest.raises(RuntimeError):ns['read_private_root_release'](p)

@pytest.mark.parametrize('poison',['optimize','env'])
def test_real_unoptimized_guard(ctx,monkeypatch,poison):
 ns=ctx[0];ns['execution_environment_admission']()
 if poison=='optimize':monkeypatch.setattr('sys.flags',types.SimpleNamespace(optimize=1))
 else:monkeypatch.setenv('PYTHONOPTIMIZE','0')
 with pytest.raises(RuntimeError,match='UNOPTIMIZED_INTERPRETER_REQUIRED'):ns['execution_environment_admission']()


def test_output_cap_preserves_existing_receipts_and_creates_no_overcap_file(ctx,tmp_path):
 ns=ctx[0];oldout,oldwritten=ns['OUT'],ns['written'];ns['OUT']=tmp_path;ns['written']=0
 try:
  row=ns['write']('baseline.json',{'baseline':True});assert Path(row['path']).is_file()
  ns['written']=ns['OUTPUT_CAP']
  with pytest.raises(AssertionError):ns['write']('overcap.json',{})
  assert not (tmp_path/'overcap.json').exists() and Path(row['path']).is_file()
 finally:ns['OUT'],ns['written']=oldout,oldwritten
