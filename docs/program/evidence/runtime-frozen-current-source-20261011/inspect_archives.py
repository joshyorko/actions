import hashlib,json,os,posixpath,stat,subprocess,sys,tarfile,zipfile
from pathlib import Path,PurePosixPath,PureWindowsPath
ROOT=Path('/workspace/engineering/native292-owned')
REPO=Path('/workspace/engineering/pr290')
PRODUCER='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
CANDIDATE='ba85aac7324ea4463bfba8c5f8586e27706dc2fe'
HEAD='2f631e5403ae3ff0b37af2416dc19a98bdc04a84'
CONTROL='88c97efbdfea4a4ddc297b9cc495d212383c617d'
BUILD_TREE='80e5c77513f6abf5d07005ee3aee47d49efd927f'
INPUTS=('action_server/src','actions/src','actions-http-helper/src','action_server/pyproject.toml','action_server/poetry.lock','actions/pyproject.toml','actions/poetry.lock','actions-http-helper/pyproject.toml','actions-http-helper/poetry.lock')
TESTS=tuple('action_server/tests/action_server_tests/'+x for x in ('test_cli_mcp_catalog_rollback.py','test_cli_live_reload_multi_package.py','test_cli_successful_generation_drain.py','test_cli_multi_package_sync.py','test_cli_mcp_resource_history.py'))
SCRIPTS=('archive_native_artifact_provenance.py','write_native_artifact_manifest.py','verify_frozen_catalog_artifact.py','verify_frozen_catalog_wrapper_artifact.py','verify_frozen_catalog_harness.py')
def hbytes(b):return hashlib.sha256(b).hexdigest()
def streamhash(s):
 d=hashlib.sha256();size=0
 for b in iter(lambda:s.read(1024*1024),b''):d.update(b);size+=len(b)
 return d.hexdigest(),size
def measure(p):
 with p.open('rb') as s:h,n=streamhash(s)
 return {'path':str(p),'size':n,'sha256':h}
def git(*args):return subprocess.check_output(['git','-C',str(REPO),*args])
def entries(ref,paths):
 out={}
 for r in git('ls-tree','-r','-z',ref,'--',*paths).split(b'\0'):
  if r:
   meta,p=r.split(b'\t',1);mode,kind,blob=meta.decode().split();out[p.decode()]={'mode':mode,'kind':kind,'blob':blob}
 return out
def safe(name):
 p=PurePosixPath(name);w=PureWindowsPath(name)
 assert not p.is_absolute() and not w.drive and '\\' not in name and p.parts and '..' not in p.parts
 return name
api=json.loads((ROOT/'build-artifacts.json').read_text())
records={}
for name,aid in [('provenance.zip',11686643166),('wrapper.zip',11686533628)]:
 rec=measure(ROOT/name);a=next(x for x in api['artifacts'] if x['id']==aid)
 assert rec['size']==a['size_in_bytes'] and rec['sha256']=='%s'%a['digest'].removeprefix('sha256:') and not a['expired']
 rec.update(artifact_id=aid,artifact_name=a['name'])
 with zipfile.ZipFile(ROOT/name) as z:
  ms=z.infolist();assert len(ms)==1
  m=ms[0];safe(m.filename);assert not m.is_dir() and not m.flag_bits&1 and m.create_system==3 and stat.S_IFMT(m.external_attr>>16)==stat.S_IFREG
  rec['member']={'name':m.filename,'mode':stat.S_IMODE(m.external_attr>>16),'size':m.file_size,'compressed_size':m.compress_size}
  with z.open(m) as s:d,n=streamhash(s)
  assert n==m.file_size;rec['member']['sha256']=d
 records[name]=rec
assert records['provenance.zip']['member']['name']=='native-artifact-provenance.tar'
assert records['wrapper.zip']['member']['name']=='action-server' and records['wrapper.zip']['member']['mode']==0o755
with tarfile.open(ROOT/'native-artifact-provenance.tar','r:') as t:
 ms=t.getmembers();assert len(ms)<2000 and sum(m.size for m in ms)<256*1024*1024
 assert len(ms)==len({m.name for m in ms});by={safe(m.name):m for m in ms}
 mb=t.extractfile('output/native-artifact-manifest.json').read();ib=t.extractfile('output/native-artifact-tree-inventory.json').read()
 man=json.loads(mb);inv=json.loads(ib);assert man['schema_version']==1 and man['source_sha']==PRODUCER and man['workflow_run_id']=='38098225250' and man['workflow_run_attempt']=='1' and man['platform']=='Linux' and man['architecture']=='x86_64'
 prefix='dist/action-server/'
 assert set(by)=={'dist/action-server','output/native-artifact-manifest.json','output/native-artifact-tree-inventory.json'}|{prefix+e['path'] for e in inv}
 measured={}
 for e in inv:
  safe(e['path']);m=by[prefix+e['path']];assert m.mode==e['mode']
  if e['kind']=='directory':assert m.isdir() and e['content_sha256'] is None
  elif e['kind']=='symlink':
   assert m.issym() and m.linkname==e['link_target'];safe(m.linkname)
   n=posixpath.normpath(posixpath.join(posixpath.dirname(e['path']),m.linkname));assert not n.startswith('../')
   target=by[prefix+n];assert target.isfile() or target.isdir()
   if target.isfile():
    with t.extractfile(target) as s:d,n=streamhash(s)
    assert d==e['content_sha256']
  elif e['kind']=='file':
   assert m.isfile()
   with t.extractfile(m) as s:d,n=streamhash(s)
   assert n==m.size and d==e['content_sha256'];measured[e['path']]={'size':n,'sha256':d,'mode':m.mode}
  else:raise AssertionError('unexpected entry kind')
 assert inv==sorted(inv,key=lambda e:e['path'])
 tree=hashlib.sha256();embedded=hashlib.sha256()
 for e in inv:
  relative=e['path'].encode();tree.update(relative+b'\0'+str(e['mode']&0o777).encode()+b'\0')
  if e['kind']=='symlink':tree.update(b'link\0'+e['link_target'].encode()+b'\0')
  elif e['kind']=='directory':tree.update(b'directory\0')
  else:tree.update(b'file\0'+bytes.fromhex(e['content_sha256']))
  if e['content_sha256'] is not None:embedded.update(relative+b'\0'+bytes.fromhex(e['content_sha256']))
 for a in man['artifacts'].values():assert a['frozen_package_tree_sha256']==tree.hexdigest() and a['embedded_files_sha256']==embedded.hexdigest()
 assert measured['action-server']['sha256']==man['artifacts']['frozen']['sha256']
 assert records['wrapper.zip']['member']['sha256']==man['artifacts']['go-wrapper']['sha256']
 tarrec=measure(ROOT/'native-artifact-provenance.tar');assert tarrec['sha256']==records['provenance.zip']['member']['sha256']
 archive={'manifest_sha256':hbytes(mb),'inventory_sha256':hbytes(ib),'inventory_entries':len(inv),'tar_members':len(ms),'tar':tarrec,'frozen_binary':measured['action-server'],'package_tree_sha256':tree.hexdigest(),'embedded_files_sha256':embedded.hexdigest(),'manifest':man,'checks':'All ZIP container bytes and TAR file bytes, paths, modes, symlink targets, exact member set, inventory and aggregate digests verified; no binary execution or executable extraction.'}
assert git('rev-parse',PRODUCER+'^{tree}').decode().strip()==BUILD_TREE and git('rev-parse',CANDIDATE+'^{tree}').decode().strip()==BUILD_TREE
source=entries(CANDIDATE,INPUTS);control=entries(CONTROL,INPUTS);tests=entries(CANDIDATE,TESTS);control_tests=entries(CONTROL,TESTS)
assert source==control and tests==control_tests
assert git('diff','--name-only',CONTROL,'--',*INPUTS,*TESTS)==b''
for p,e in {**source,**tests}.items():
 assert e['kind']=='blob';b=git('show',CANDIDATE+':'+p);assert b==(REPO/p).read_bytes();e['sha256']=hbytes(b)
(ROOT/'producer-input-inventory.json').write_text(json.dumps(source,indent=2)+'\n')
(ROOT/'selected-test-inventory.json').write_text(json.dumps(tests,indent=2)+'\n')
w=hashlib.sha256()
for p in man['artifacts']['go-wrapper']['wrapper_source_files']:
 b=git('show',PRODUCER+':action_server/'+p);assert b==(REPO/'action_server'/p).read_bytes();w.update(p.encode()+b'\0'+bytes.fromhex(hbytes(b)))
assert w.hexdigest()==man['artifacts']['go-wrapper']['wrapper_source_sha256']
receipt={'schema':'native292-byte-source-admission/v1','status':'PASS_READ_ONLY_BYTE_AND_SOURCE_PARITY','executed_binaries':False,'candidate_sha':CANDIDATE,'candidate_tree':BUILD_TREE,'native_build_source_sha':PRODUCER,'native_build_source_tree':BUILD_TREE,'pr292_head_sha':HEAD,'pr292_head_tree':git('rev-parse',HEAD+'^{tree}').decode().strip(),'control_sha':CONTROL,'control_tree':git('rev-parse',CONTROL+'^{tree}').decode().strip(),'control_runtime_tree':git('rev-parse',CONTROL+':action_server/src/actions/server').decode().strip(),'workflow_run_id':'38098225250','workflow_run_attempt':'1','archives':records,'archive_measurements':archive,'source_parity':{'input_paths':INPUTS,'input_entries':len(source),'exact_complete_input_inventory_equal':True,'selected_test_files':tests,'worktree_matches_control_inputs_and_tests':True,'input_inventory':measure(ROOT/'producer-input-inventory.json'),'test_inventory':measure(ROOT/'selected-test-inventory.json'),'wrapper_source_sha256':w.hexdigest()},'verification_tools':{'python':sys.version,'executable':sys.executable,'git':git('--version').decode().strip(),'inspector':measure(Path(__file__)),'canonical_reference_scripts':{s:measure(REPO/'action_server/scripts'/s) for s in SCRIPTS}},'limits':['No frozen or wrapper executable was run.','Manifest checks Git HEAD only, not clean build input attestation.','The built Core/dependency component bytes have manifest inventory digests but no independent published-wheel origin proof in this inspection.','assets.zip bytes are named and hashed by the build manifest but not separately retained in these archives; no independent assets.zip reconstruction is claimed.','This pair is from sibling Build Unauthenticated run38098225250, not Tests run38098225220.','Existing a47 verification guards and historical receipts remain unchanged.']}
(ROOT/'byte-source-review.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'receipt':measure(ROOT/'byte-source-review.json'),'status':receipt['status'],'archives':records,'frozen':archive['frozen_binary'],'manifest_sha256':archive['manifest_sha256'],'inventory_sha256':archive['inventory_sha256'],'package_tree_sha256':tree.hexdigest(),'embedded_files_sha256':embedded.hexdigest(),'inventory_entries':len(inv),'source_entries':len(source),'test_files':tests},indent=2))
