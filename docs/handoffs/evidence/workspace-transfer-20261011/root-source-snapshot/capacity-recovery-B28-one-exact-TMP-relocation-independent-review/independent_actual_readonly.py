from pathlib import Path
import ast,collections,gzip,hashlib,json,os,stat,subprocess,tarfile,time
OUT=Path('/workspace/engineering/capacity-recovery-B28-one-exact-TMP-relocation-independent-review')
BASE=Path('/workspace/engineering/capacity-recovery-B28-one-exact-TMP-relocation-source')
ACT=Path('/workspace/engineering/root-B28-one-exact-TMP-relocation-owned')
ROOT=Path('/workspace/engineering/root-B28-one-exact-TMP-relocation-outer-owned')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def binding(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 return {'path':str(p),'bytes':s.st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(s.st_mode))}
def exact(r):
 b=binding(r['path']);assert all(b[k]==r[k] for k in ['path','bytes','sha256'])
 assert int(b['mode'],8)==(int(r['mode'],8) if isinstance(r['mode'],str) else r['mode'])
 s=Path(r['path']).lstat()
 for k in ['uid','gid']:
  if k in r:assert getattr(s,'st_'+k)==r[k]
def meta(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 return {'path':str(p),'bytes':s.st_size,'sha256':sha(p),'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'mtime_ns':s.st_mtime_ns,'device':s.st_dev,'inode':s.st_ino,'nlink':s.st_nlink,'allocated':s.st_blocks*512}
start=time.monotonic()
owner=ROOT/'OWNERFINAL-root-one-original-exact-TMP-relocation.json';assert binding(owner)['sha256']=='bc6fa7297f84d3696b34f46d9abad750fb0649cdd83d21c29098ad8f2a960de3'
o=json.loads(owner.read_bytes());assert o['operation_exit']==o['root_data_post_exit']==0 and o['one_attempt'] is True and o['no_retry'] is True
pre=OUT/'OWNERFINAL-independent-one-exact-TMP-archive-relocation-PREEXECUTION-review.json';p=json.loads(pre.read_bytes());assert binding(pre)['sha256']=='29d2a990b25df39923f85db5b7c0daa1a0bedae57978107c9afff9b6c76c7798'
original=Path(p['proposal_binding']['path']);sup=Path(p['metadata_successor_binding']['path']);d=json.loads(sup.read_bytes())
for r in d['frozen_bindings']:exact(r)
script=Path(p['script_binding']['path']);exact(p['script_binding']);tree=ast.parse(script.read_bytes());constants={}
for n in tree.body:
 if isinstance(n,ast.Assign):
  for t in n.targets:
   if isinstance(t,ast.Name) and t.id in ['BINDINGS','ORIGINAL']:constants[t.id]=ast.literal_eval(n.value)
for r in constants['BINDINGS'].values():exact(r)
rel=Path('/workspace/engineering/root-B28-one-exact-TMP-relocation-release.json');assert binding(rel)['sha256']=='44d9360badd9847559bb12970b78b74272735c2897d7be061d16837ddca72bcd'
r=json.loads(rel.read_bytes());assert json.loads((ACT/'consumed-root-release.json').read_bytes())==r
assert r['schema']=='ROOT_ONE_EXACT_B28_ARCHIVE_RELOCATION_RELEASE' and r['one_attempt'] is True and r['no_retry'] is True
assert r['root_argv']==p['bounded_command']['operation_argv'] and r['proposal_binding']==p['proposal_binding'] and r['script_binding']==p['script_binding']
for k in ['independent_preexec_binding','B28_actual_terminal_binding','B28_independent_actual_binding']:exact(r[k])
assert r['independent_preexec_binding']==binding(pre)
assert r['root_envelope']=={'timeout_seconds':900,'TERM_kill_after_seconds':10} and r['operation_envelope']=={'timeout_seconds':600,'TERM_kill_after_seconds':10}
assert r['source_scope']=='396_STORAGE_BYTE_RELOCATION_NOT_NATIVE_OR_INTEGRATION_QUALIFICATION'
act=json.loads(Path(r['B28_independent_actual_binding']['path']).read_bytes());assert act['decision']=='GO_B28_V2_ACTUAL_STORAGE_PRESERVATION' and act['actual_terminal_binding']==r['B28_actual_terminal_binding']
post=Path('/workspace/engineering/root-B28-one-exact-TMP-relocation-postguard.py');assert binding(post)['sha256']=='58880e80665e6546ef9c99961491d1059261a77c0811b96269802a64b9d841ba'
pcode=post.read_text();assert "'__name__':'ROOT_VERIFIED_RELOCATION_DATA_ONLY_POST'" in pcode and "guard['protected'](config)" in pcode
mapping=ACT/'exact-original-path-to-new-physical-archive.json';assert binding(mapping)['sha256']=='ce1450945a28a00611dff941ddcb0c414f281b7f32bbe004eb200435baa04f7f';m=json.loads(mapping.read_bytes());assert m['original']==constants['ORIGINAL'] and m['original_index_binding']==constants['BINDINGS']['index'] and m['original_index_unchanged'] is True
old=Path(m['original']['path']);dest=Path(m['new_physical']['path']);assert not old.exists() and not old.is_symlink();assert meta(dest)==m['new_physical']
for k in ['bytes','sha256','mode','uid','gid','mtime_ns','nlink']:assert m['original'][k]==m['new_physical'][k]
assert stat.S_IMODE(dest.parent.stat().st_mode)==0o700
index=Path(m['original_index_binding']['path']);exact(m['original_index_binding']);assert meta(index)==d['original_index']
records=json.loads(index.read_bytes())['records'];matches=[x for x in records if x['archive']==str(old)];assert len(matches)==1
rec=matches[0];assert rec['expanded_removed'] is True and rec['archive_sha256']==m['original']['sha256'] and rec['archive_bytes']==m['original']['bytes'];expected=rec['inventory'];seen={};types=collections.Counter();roots=links=0;name=old.name.removesuffix('.tar.gz')
with tarfile.open(dest,'r|gz') as stream:
 for item in stream:
  if item.name==name:roots+=1;assert roots==1 and item.isdir();continue
  assert item.name.startswith(name+'/');relative=item.name[len(name)+1:];assert relative in expected and relative not in seen and '..' not in Path(relative).parts
  row=expected[relative];assert (item.mode,item.uid,item.gid)==(row['mode'],row['uid'],row['gid']);types[row['kind']]+=1
  if row['kind']=='file':
   if item.islnk():
    assert item.linkname.startswith(name+'/');target=item.linkname[len(name)+1:];assert target in seen and seen[target]['kind']=='file';assert (seen[target]['bytes'],seen[target]['sha256'])==(row['bytes'],row['sha256']);links+=1
   else:
    assert item.isfile();h=hashlib.sha256();size=0
    for block in iter(lambda:stream.extractfile(item).read(0),b''):pass
    f=stream.extractfile(item)
    for block in iter(lambda:f.read(1048576),b''):h.update(block);size+=len(block)
    assert size==row['bytes'] and h.hexdigest()==row['sha256']
  elif row['kind']=='directory':assert item.isdir()
  elif row['kind']=='symlink':assert item.issym() and item.linkname==row['target']
  elif row['kind']=='fifo':assert item.isfifo()
  else:raise AssertionError('unknown member')
  seen[relative]=row
assert roots==1 and len(seen)==14805 and set(seen)==set(expected) and links==3
with gzip.open(dest,'rb') as f:
 for block in iter(lambda:f.read(1048576),b''):pass
assert meta(dest)==m['new_physical'];exact(m['original_index_binding'])
c=json.loads(Path(constants['BINDINGS']['config']['path']).read_bytes());alias_changes=0
for key in ['immutable_files','qualified237_bindings']:
 for row in c[key]:
  if row['path']==str(old):row['path']=str(dest);alias_changes+=1
assert alias_changes==1
root=Path(c['source_root']);env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(root),*a],env=env)
assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[c['source_head'],c['source_tree']] and not git('status','--porcelain=v1')
entries=[]
for entry in git('ls-tree','-rz',c['source_head']).split(b'\0'):
 if entry:
  left,path=entry.split(b'\t',1);bits=left.decode().split();entries.append((bits[0],bits[2],path.decode()))
assert entries==[(x['mode'],x['oid'],x['path']) for x in c['source_rows']] and len(entries)==1426
for row in c['source_rows']:
 f=root/row['path'];body=os.readlink(f).encode() if row['mode']=='120000' else f.read_bytes();assert len(body)==row['bytes'] and hashlib.sha256(body).hexdigest()==row['sha256'] and stat.S_IMODE(f.lstat().st_mode)==row['fs_mode']
for path,digest in c['prepared30'].items():assert sha(root/path)==digest
for row in c['immutable_files']:exact(row)
native=Path(c['native_root'])
for row in c['native_members']:
 f=native/row['path'];assert stat.S_IMODE(f.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert f.is_file() and not f.is_symlink() and sha(f)==row['content_sha256']
 elif row['kind']=='directory':assert f.is_dir() and not f.is_symlink()
 else:assert f.is_symlink() and os.readlink(f)==row['link_target']
assert {f.relative_to(native).as_posix() for f in native.rglob('*')}=={x['path'] for x in c['native_members']} and len(c['native_members'])==1192
history=alias=0
for row in c['qualified237_bindings']:
 if row['path']==c['failed1_mapping']['original_binding']['path']:assert row==c['failed1_mapping']['original_binding'];alias+=1
 elif row['path']==c['historical_fixture_path']:
  body=git('show',c['historical_fixture_source']+':'+Path(row['path']).relative_to(root).as_posix());assert len(body)==row['bytes'] and hashlib.sha256(body).hexdigest()==row['sha256'];history+=1
 else:exact(row)
assert history==alias==1 and len(c['qualified237_bindings'])==237
failed=c['failed1_mapping'];assert not Path(failed['original_binding']['path']).exists();found=0
with tarfile.open(failed['archive']['path'],'r|gz') as stream:
 for item in stream:
  if item.name==failed['member']:
   body=stream.extractfile(item).read();assert len(body)==failed['original_binding']['bytes'] and hashlib.sha256(body).hexdigest()==failed['original_binding']['sha256'] and (item.mode,item.uid,item.gid)==(0o600,1000,1000) and json.loads(body)['status']=='FAIL';found+=1;break
assert found==1 and Path(c['failed563_existence_only']).exists()
terminal=json.loads((ACT/'original-one-relocation-terminal.json').read_bytes());assert terminal=={'native':'NOT_RUN','protected_post':'PASS','source_removed':True,'status':'PASS_EXACT_STORAGE_RELOCATION_ONLY'}
operation=json.loads((ROOT/'one-original-relocation-operation-original-terminal.json').read_bytes());assert operation['returncode']==0 and operation['parent_timeout_seconds']==640 and operation['argv']==r['root_argv']
postterm=json.loads((ROOT/'root-independent-all-outcome-data-post-original-terminal.json').read_bytes());assert postterm['returncode']==0 and postterm['parent_timeout_seconds']==135
outer=json.loads((ROOT/'original-root-outer-terminal.json').read_bytes());assert outer['exit_code']==0 and outer['one_attempt'] is True and outer['no_retry'] is True
before=json.loads((ACT/'protected-before.json').read_bytes());after=json.loads((ACT/'protected-after.json').read_bytes());rootpost=json.loads((ROOT/'root-independent-all-outcome-data-post.stdout.private.log').read_bytes());assert before==after==rootpost['protected'] and rootpost['status']=='ROOT_INDEPENDENT_ALL_OUTCOME_DATA_POST_PASS' and rootpost['physical']=='EXACT_VERIFIED_NEW_ARCHIVE_ALIAS_ORIGINAL_PATH_ABSENT'
for r0 in constants['BINDINGS'].values():exact(r0)
proof={'schema':1,'status':'PASS_INDEPENDENT_ACTUAL_ONE_EXACT_ARCHIVE_RELOCATION_DATA_ONLY','source_head':c['source_head'],'source_tree':c['source_tree'],'source_leaves':1426,'native_members':1192,'prepared_inputs':len(c['prepared30']),'immutable_files':len(c['immutable_files']),'qualified_originals':237,'immutable_tar_gz_rows':sum(x['path'].endswith('.tar.gz') for x in c['immutable_files']),'immutable_complete_index_rows':sum(x['path'].endswith('private-complete-inventory-and-recovery.json') for x in c['immutable_files']),'new_archive':{'bytes':m['new_physical']['bytes'],'sha256':m['new_physical']['sha256'],'all_new_physical_fields':'EXACT_MAPPING','original_SHA_body_modeUIDGID_mtime_nlink':'EXACT','members':len(seen),'types':dict(types),'root_headers':roots,'internal_hardlink_headers':links,'whole_gzip_CRC_ISIZE':True},'old_archive_path':'ABSENT','original_index':'ALL_RECORDED_PHYSICAL_METADATA_SHA_UNCHANGED','historical_fixture':1,'original_failed1_alias':'FAIL_UNCHANGED','original_failed563':'EXISTENCE_ONLY_UNCHANGED','alias_rows':1,'driver_and_independent_root_posts':'BOTH_PASS_MATCH_PROTECTED_COUNTS','operation_outer_post_returncodes':[0,0,0],'review_seconds':round(time.monotonic()-start,3),'reviewer_operations':'Read-only SHA/archive stream/data comparisons/AST/source Git metadata. No copy/unlink/import/gate/native/download/source mutation.','universal_quiescence':'UNKNOWN','native_qualification':'NONE','TAR_nanosecond_precision':'UNCHANGED_ORIGINAL_UNKNOWN_NOT_REQUALIFIED'}
f=OUT/'independent-actual-exact-relocation-stream-and-protected-input-proof.json'
with f.open('x') as w:json.dump(proof,w,indent=2,sort_keys=True);w.write('\n')
f.chmod(0o400);print(json.dumps(binding(f)))
