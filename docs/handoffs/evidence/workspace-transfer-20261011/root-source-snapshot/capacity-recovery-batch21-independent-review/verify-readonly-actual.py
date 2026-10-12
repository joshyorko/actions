import ast,gzip,hashlib,json,os,stat,subprocess,sys,tarfile,time
from pathlib import Path,PurePosixPath
from collections import defaultdict
BATCH=int(sys.argv[1]);assert BATCH in (20,21);OUT=Path('/workspace/engineering')/f'capacity-recovery-batch{BATCH}-independent-review';OUT.mkdir(mode=0o700,exist_ok=True)
START=time.monotonic();BASE=Path('/workspace/actions-cloud/robocorp/temp');NAMES={20:['6bb7d57b503d838a','9710d7e7a03133a6'],21:['e8634afd9d863388']}[BATCH]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for z in iter(lambda:f.read(1048576),b''):h.update(z)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(r):assert bind(r['path'])=={k:r[k] for k in ('path','bytes','sha256')};return r
def load(p):return json.loads(Path(p).read_bytes())
def normAST(p):
 t=ast.parse(Path(p).read_text());seen=set()
 for n in t.body:
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('DEST','STAGE','NAMES'):
   k=n.targets[0].id;seen.add(k)
   if k=='NAMES':assert isinstance(n.value,ast.List);n.value=ast.List(elts=[ast.Constant('NORMALIZED')],ctx=ast.Load())
   else:assert isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='Path';n.value.args=[ast.Constant('NORMALIZED')]
 assert seen=={'DEST','STAGE','NAMES'};return ast.dump(t,include_attributes=False)
proposal=Path('/workspace/engineering/capacity-recovery-batch20-proposal/OWNERFINAL-batch20-exact-two-completed-scratch-preexecution-proposal.json') if BATCH==20 else Path('/workspace/engineering/capacity-recovery-batch21-proposal/OWNERFINAL-batch21-exact-one-completed-origin-UNREPORTED-preexecution-proposal.json')
pr=load(proposal);check(pr['script']);check(pr['algorithm_parent']);assert normAST(pr['script']['path'])==normAST(pr['algorithm_parent']['path'])==normAST('/tmp/actions-capacity-recovery-batch16.py')
private=Path(f'/dev/shm/actions-completed-scratch-recovery-batch{BATCH}/private-complete-inventory-and-recovery.json');private_before=bind(private);assert stat.S_IMODE(private.stat().st_mode)==0o600 and stat.S_IMODE(private.parent.stat().st_mode)==0o700
records=load(private)['records'];assert [Path(r['original_namespace']).name for r in records]==NAMES
results=[]
for record,name in zip(records,NAMES):
 assert Path(record['original_namespace'])==BASE/name and not (BASE/name).exists() and record['expanded_removed'] is True and record['archive_verified_before_original_removal'] is True
 archive=Path(record['archive']);assert archive.parent==private.parent and archive.name==name+'.tar.gz' and not archive.is_symlink() and stat.S_IMODE(archive.stat().st_mode)==0o600
 assert archive.stat().st_size==record['archive_bytes'] and sha(archive)==record['archive_sha256']
 inv=record['inventory'];assert len(inv)==record['verified_members'];seen=set();content={};links={};rootcount=0;marker=False;logical=0;counts={'file':0,'symlink':0,'directory':0,'fifo':0,'hardlink_headers':0}
 with gzip.open(archive,'rb') as gz:
  with tarfile.open(fileobj=gz,mode='r|') as tf:
   for m in tf:
    if m.name==name:assert m.isdir();rootcount+=1;continue
    assert m.name.startswith(name+'/');relative=m.name[len(name)+1:];p=PurePosixPath(relative)
    assert relative and not p.is_absolute() and '..' not in p.parts and relative not in seen and relative in inv
    seen.add(relative);row=inv[relative];assert (m.mode,m.uid,m.gid)==(row['mode'],row['uid'],row['gid']);assert abs(m.mtime-row['mtime_ns']/1e9)<=1e-6
    kind=row['kind'];counts[kind]+=1
    if kind=='file':
     if m.islnk():
      assert m.linkname.startswith(name+'/');target=m.linkname[len(name)+1:];p=PurePosixPath(target);assert target and not p.is_absolute() and '..' not in p.parts and target in inv and inv[target]['kind']=='file';links[relative]=target;counts['hardlink_headers']+=1
     else:
      assert m.isfile();stream=tf.extractfile(m);h=hashlib.sha256();size=0;rawmarker=b''
      for b in iter(lambda:stream.read(1048576),b''):
       h.update(b);size+=len(b)
       if relative=='recycle.now':rawmarker+=b
      assert size==row['bytes'] and h.hexdigest()==row['sha256'];content[relative]=(size,h.hexdigest());logical+=size
      if relative=='recycle.now':assert rawmarker.strip()==b'True';marker=True
    elif kind=='symlink':assert m.issym() and m.linkname==row['target']
    elif kind=='directory':assert m.isdir()
    elif kind=='fifo':assert m.isfifo()
    else:raise AssertionError('Unsupported recorded member type')
  while gz.read(1048576):pass
 assert rootcount==1 and seen==set(inv) and marker
 for rel in links:
  target=rel;visited=set()
  while target in links:assert target not in visited;visited.add(target);target=links[target]
  assert target in content and content[target]==(inv[rel]['bytes'],inv[rel]['sha256']);logical+=inv[rel]['bytes']
 results.append({'ordinal':len(results)+1,'archive':bind(archive),'recorded_members':len(inv),'kinds':counts,'logical_regular_bytes':logical,'all_member_payloads_sizes_metadata_types_links_exact':True,'mtime_float_representation_agrees_with_original_ns_within_1us':True,'gzip_EOF_CRC_ISIZE':True,'True_completion_marker':True,'expanded_original_absent':True})
 print(json.dumps({'archive_ordinal':len(results),'members':len(inv),'hardlink_headers':len(links),'status':'PASS'}),flush=True)
assert bind(private)==private_before
# Preserve separately reviewed batch20 exact index/two archives before aggregate count.
safe20=load('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch20.json');assert bind('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch20.json')['sha256']=='1d651c9a8d8421d7566c1e1f085136df525a3e783dd5667748960301bc59053a';check(safe20['private_inventory'])
for r20 in safe20['records']:
 a20=Path(r20['archive']);assert a20.stat().st_size==r20['archive_bytes'] and sha(a20)==r20['archive_sha256'] and stat.S_IMODE(a20.stat().st_mode)==0o600
assert len(safe20['records'])==2
# Independently rehash all420 prior baseline bindings and preserve current mode.
baseline_path=Path('/workspace/engineering/capacity-recovery-batch20-proposal/private-readonly-preparation-proof.json');baseline=load(baseline_path)
for row in baseline['refs_current_bytes_modes']:
 check(row)
 if 'current_mode' in row:assert oct(stat.S_IMODE(Path(row['path']).stat().st_mode))==row['current_mode']
assert baseline['prior_archives']==40 and baseline['prior_indices']==19
# Read original accepted cache inventory with only independent pure helper functions.
cache_script=Path('/workspace/engineering/root-failed300-default-cache-independent-actual-review/verify-readonly-actual.py');helpers=[n for n in ast.parse(cache_script.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name in ('info','inventory','norm','partition')];assert len(helpers)==4
ns={'Path':Path,'stat':stat,'os':os,'sha':sha,'defaultdict':defaultdict};exec(compile(ast.Module(body=helpers,type_ignores=[]),str(cache_script)+':independent-readonly-functions','exec'),ns)
co=load('/workspace/engineering/root-failed300-default-cache-preservation-actual/OWNERFINAL-root-whole-default-cache-preservation-actual.json');check(co['private_complete_inventories']);original=load(co['private_complete_inventories']['path'])['frozen_original'];physical=Path(co['physical_destination']);logical=Path('/home/agent/.robocorp/pkgs');assert logical.is_symlink() and os.readlink(logical)==str(physical);current=ns['inventory'](physical);assert len(current['entries'])==416 and ns['norm'](current)==ns['norm'](original) and ns['partition'](current)==ns['partition'](original)
# Check both unrelated frozen source trees without claiming their gates or runtime outcomes.
def sourceFS(root,count,head=None):
 root=Path(root);assert not subprocess.check_output(['git','status','--porcelain'],cwd=root)
 if head:assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==head
 measured=0
 for rec in subprocess.check_output(['git','ls-tree','-rz','HEAD'],cwd=root).split(b'\0'):
  if not rec:continue
  meta,n=rec.split(b'\t',1);mode,kind,oid=meta.decode().split();p=root/n.decode();data=os.readlink(p).encode() if mode=='120000' else p.read_bytes()
  assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid
  if mode!='120000':assert bool(p.stat().st_mode&0o111)==(mode=='100755')
  measured+=1
 assert measured==count
sourceFS('/workspace/engineering/captured-child-cleanup',1422)
sourceFS('/workspace/engineering/pr308',1421,'b614864ba9da55c13662894b6ef3c8515d9fdb25')
light=Path('/workspace/engineering/pr308-rcc-compatibility-source/OWNERFINAL-current-a0d-approved-RCC-compatibility-SOURCE-LIGHT.json');assert sha(light)=='336cfca277d8e3b08035af8057e77af580fc7a5cbeb54226ae2140abedb79bba';ld=load(light);assert len(ld['frozen_bindings'])==71
for row in ld['frozen_bindings']:check(row)
native=Path('/workspace/engineering/pr310-runner-qualification-owned');inv=load(native/'output/native-artifact-tree-inventory.json');assert len(inv)==1192;assert {p.relative_to(native/'dist/action-server').as_posix() for p in (native/'dist/action-server').rglob('*')}=={r['path'] for r in inv}
for row in inv:
 p=native/'dist/action-server'/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert sha(p)==row['content_sha256']
 elif row['kind']=='symlink':assert os.readlink(p)==row['link_target'] and sha(p)==row['content_sha256']
 else:assert p.is_dir() and not p.is_symlink()
for row in load('/workspace/actions-cloud/receipts/pr305-runner/frozen-helper-bindings.json').values():assert sha(row['snapshot_path'])==row['sha256'] and stat.S_IMODE(Path(row['snapshot_path']).stat().st_mode)==0o444
failed=list(BASE.glob('563d*'));assert len(failed)==1 and failed[0].is_dir()
# Recorded removal-order and prior preserved hashes are reviewed, not historical /proc state replayed.
code=Path(pr['script']['path']).read_text();pos=code.index('for name in NAMES:');assert code.index('verify(archive, name, entries)',pos)<code.index('assert inventory(root) == entries',pos)<code.index('reject_live_handles(root)',code.index('assert inventory(root) == entries',pos))<code.index('shutil.rmtree(root)')
canonical=check(baseline['canonical']);paragraph=''.join(l[1:] for l in Path(canonical['path']).read_text().splitlines(keepends=True) if l.startswith('+') and not l.startswith('+++'));assert paragraph in Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
proof={'status':'PASS_SCOPED_ARCHIVE_AND_REFERENCE_PRESERVATION','batch':BATCH,'proposal':bind(proposal),'private_index':private_before,'script':check(pr['script']),'archive_results':results,'new_archives':len(results),'new_members':sum(r['recorded_members'] for r in results),'prior40archives19indices420baseline_refs':{'proof':bind(baseline_path),'all_exact':True},'whole_default_cache416_normalized_metadata_body_and_hardlinkpartition_exact':True,'source3081421_clean71refs_exact':True,'cleanup_source1422_currentFS_Git_exec_exact':True,'native1192_and_helpers0444_exact':True,'failed563d_existence_only':True,'source_origin':'UNREPORTED' if BATCH==21 else 'root bounded completed scratch allowlist; not independent new functionality proof','canonical_exact_verified_reuse':canonical,'scope_limits':['No historical live handle or expanded filesystem census replay','TAR representable mtime checked within1us; no precise nanosecond/rootmetadata/ACL/xattr/inode proof','No restore/extract/delete/archive/source/gateway/native/provider/test execution','Historical consumer refs are retained observations, not current installed-temp proof','Root separately owns fresh capacity, serialization and full execution authorization'],'fresh_workspace_bytes':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize,'seconds':round(time.monotonic()-START,3),'upstream_disposition':'none'}
f=OUT/'independent-actual-stream-and-preservation-proof.json';assert not f.exists();f.write_text(json.dumps(proof,indent=2)+'\n');f.chmod(0o444);print(json.dumps({'proof':bind(f),'new_members':proof['new_members'],'status':proof['status']}))
