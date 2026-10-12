import hashlib,json,os,re,stat,struct,zipfile,zlib
from pathlib import Path,PurePosixPath
R=Path('/dev/shm/actions-rcc-compatibility-originals-20261011')
O=Path('/workspace/engineering/rcc-original-acquisition-independent-review')
Q=Path('/workspace/engineering/rcc-compatibility-next-wave-readonly')
SRC='727c1ff8b679cdbbe12836e53c87734a1edb0071'
OWNER=R/'OWNERFINAL-three-original-RCC-acquisition-data-qualification.json'
def H(b):return hashlib.sha256(b).hexdigest()
def bind(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
def emit(n,d):
 p=O/n
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
 p.chmod(0o600);return bind(p)
a=OWNER.read_bytes();assert len(a)==26884 and H(a)=='0da97bfc63a5e47de1c900e8d37ec55261d8b7ef6f68069a74167afc344c72ad'
d=json.loads(a);refs=[]
for b in d['bindings']:
 p=Path(b['path']);v=bind(p);assert v==b;refs.append(v)
assert len(refs)==76
assert not OWNER.is_symlink()
for p in [R/'released-18.19.5-original-asset549249380.bin',R/'original-artifact-11689755940.zip',R/'original-artifact-11689851536.zip']:
 assert stat.S_ISREG(p.lstat().st_mode) and stat.S_IMODE(p.stat().st_mode)==0o600
p=R/'selected-native-source727-linux-amd64-rcc';assert stat.S_ISREG(p.lstat().st_mode) and stat.S_IMODE(p.stat().st_mode)==0o700
api=json.loads((Q/'rcc-native-38105340592-artifacts.private.json').read_bytes());run=json.loads((Q/'rcc-native-38105340592-run.private.json').read_bytes());src=json.loads((Q/'rcc-source-727.private.json').read_bytes());rel=json.loads((Q/'rcc-release-18.19.5.private.json').read_bytes());tag=json.loads((Q/'rcc-18.19.5-ref.private.json').read_bytes())
assert run['id']==38105340592 and run['head_sha']==SRC and run['status']=='completed' and run['conclusion']=='success' and run['run_attempt']==1
assert src['sha']==SRC and src['tree']['sha']=='cfae5c5ee9df0e5031e8e9ae37040b5c98ac6152'
assert [x['sha'] for x in src['parents']]==['07db6221a3540d227f2106eccf69fe0e7c11fee0','324524fffa4bd0f76c618f9fbb6ede30e733b2ff']
assets={x['id']:x for x in api['artifacts']};releaseasset=next(x for x in rel['assets'] if x['id']==549249380)
assert rel['tag_name']=='v18.19.5' and rel['draft'] is False and releaseasset['size']==22360226 and releaseasset['digest']=='sha256:1a617ad7c736fa67c605e20e5ebe3c7d54b02cd548f733e05c809cf49a48db1e'
assert tag['object']['sha']=='d1aec7d0bb897a81274423c7a6bb747233f9c263'
archive_rows={};payload={};expanded=0
for aid,count,expectedbytes,expectsha in [(11689755940,5,49089276,'88f406c654de1155e717ded1534fa058ca1c5375007109f2a06364d3a5036ac2'),(11689851536,7,185396,'ec8d7cc46646fcfca7a228392e1bc2cb53341d838563802abd7d306c1f07eaba')]:
 p=R/f'original-artifact-{aid}.zip';b=bind(p);assert b['bytes']==expectedbytes and b['sha256']==expectsha
 art=assets[aid];assert art['size_in_bytes']==expectedbytes and art['digest']=='sha256:'+expectsha and art['expired'] is False
 assert art['workflow_run']['id']==38105340592 and art['workflow_run']['head_sha']==SRC
 rows=[];names=set()
 with zipfile.ZipFile(p) as z:
  infos=z.infolist();assert len(infos)==count
  for i in infos:
   name=i.filename;pp=PurePosixPath(name);assert name not in names;names.add(name)
   assert name and not pp.is_absolute() and '\\' not in name and ':' not in name and '\x00' not in name and not i.is_dir()
   assert all(c not in ('','.','..') for c in name.split('/'))
   mode=i.external_attr>>16;assert stat.S_IFMT(mode) in (0,stat.S_IFREG) and not i.flag_bits&1
   h=hashlib.sha256();crc=0;n=0;keep=pp.name in ('rcc-linux64','SHA256SUMS','native-runtime-receipt.json','jat-class-consumer-receipt.json','native-runtime-robot-evidence.json');parts=[]
   with z.open(i) as f:
    for b in iter(lambda:f.read(1048576),b''):
     h.update(b);crc=zlib.crc32(b,crc);n+=len(b);expanded+=len(b)
     assert expanded+71634898<=209715200
     if keep:parts.append(b)
   assert n==i.file_size and crc&0xffffffff==i.CRC
   rows.append({'name':name,'bytes':n,'sha256':h.hexdigest(),'mode':mode,'ZIP_CRC32':i.CRC,'compressed_bytes':i.compress_size,'method':i.compress_type,'creator_system':i.create_system,'original_header_extra_sha256':H(i.extra),'header_flags':i.flag_bits})
   if keep:
    assert pp.name not in payload;payload[pp.name]=b''.join(parts)
 assert rows==json.loads((R/f'original-artifact-{aid}-complete-admitted-members-v2.private.json').read_bytes());archive_rows[str(aid)]=rows
assert expanded==86540625
sums={}
for line in payload['SHA256SUMS'].decode('ascii').splitlines():
 m=re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.-]+)',line);assert m and m[2] not in sums;sums[m[2]]=m[1]
rows=archive_rows['11689755940'];binaries={PurePosixPath(x['name']).name:x for x in rows if PurePosixPath(x['name']).name!='SHA256SUMS'}
assert len(sums)==4 and set(sums)==set(binaries) and all(sums[k]==v['sha256'] for k,v in binaries.items())
assert payload['rcc-linux64']==(R/'selected-native-source727-linux-amd64-rcc').read_bytes()
for name in ['SHA256SUMS','native-runtime-receipt.json','jat-class-consumer-receipt.json','native-runtime-robot-evidence.json']:
 assert payload[name]==(R/('selected-original-'+name)).read_bytes()
receipt=json.loads(payload['native-runtime-receipt.json']);jat=json.loads(payload['jat-class-consumer-receipt.json']);robot=json.loads(payload['native-runtime-robot-evidence.json']);nativehash=H(payload['rcc-linux64'])
assert nativehash=='be55dadc391ae4ac7dd38356755a1698c595fdf41bd4a0141f8df7cc9d29f00e'
for t in [receipt,jat]:
 assert t['schemaVersion']==1 and t['commitSha']==SRC and t['platform']=='linux_amd64'
 assert t['binary']['sha256']==nativehash and t['binary']['version']=='v18.19.6'
 assert t['binary']['runtimeGOOS']==t['binary']['expectedGOOS']=='linux' and t['binary']['runtimeGOARCH']==t['binary']['expectedGOARCH']=='amd64'
assert receipt['robotExactBinary']==robot and robot['binarySha256']==nativehash and robot['binaryVersion']=='v18.19.6'
# Native and JAT are distinct executed fixtures; shared binary/source identity does not imply equal artifact/lifecycle payloads.
assert all(isinstance(t[k],dict) for t in [receipt,jat] for k in ['exactBinaryCLI','sourceAPI'])
def go_metadata(raw):
 assert raw[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',raw,18)[0]==62
 magic=b'\xff Go buildinf:';assert raw.count(magic)==1
 i=raw.index(magic);assert raw[i+14]==8 and raw[i+15]&2;cursor=i+32
 def string():
  nonlocal cursor
  length=0;shift=0
  while True:
   v=raw[cursor];cursor+=1;length|=(v&127)<<shift
   if v<128:break
   shift+=7;assert shift<64
  assert 0<=length<16777216 and cursor+length<=len(raw)
  out=raw[cursor:cursor+length];cursor+=length;return out
 go=string().decode('ascii');module=string()
 revision=re.findall(rb'build\tvcs.revision=([0-9a-f]{40})(?:\n|$)',module);modified=re.findall(rb'build\tvcs.modified=(true|false)(?:\n|$)',module)
 assert len(revision)==len(modified)==1
 return {'ELF_machine':'amd64','Go_version':go,'module_info_sha256':H(module),'revision':revision[0].decode('ascii'),'modified':modified[0]==b'true'}
linux=go_metadata(payload['rcc-linux64']);release_raw=(R/'released-18.19.5-original-asset549249380.bin').read_bytes();release=go_metadata(release_raw)
assert len(release_raw)==22360226 and H(release_raw)==releaseasset['digest'][7:]
assert linux['Go_version']=='go1.26.9' and linux['revision']==SRC and linux['modified'] is False
assert release['Go_version']=='go1.26.5' and release['revision']==tag['object']['sha'] and release['modified'] is True
assert json.loads((R/'original-data-inspection-exit.json').read_bytes())['exit_code']==1
assert json.loads((R/'original-data-inspection-v2-exit.json').read_bytes())['exit_code']==0
assert all(bind(Path(v['path']))==v for v in refs)
private=emit('complete-private-independent-byte-and-archive-proof.json',{'owner':bind(OWNER),'references':refs,'archive_inventory':archive_rows,'released5':release,'candidate727':linux,'all76_references_prepost_exact':True})
safe=emit('safe-independent-original-acquisition-readback.json',{'owner':bind(OWNER),'status':'PASS_ORIGINAL_BYTES_ARCHIVE_ADMISSION_AND_CANDIDATE727_DATA_IDENTITY_ONLY','reference_count':len(refs),'original_count':3,'original_bytes':71634898,'archive_count':2,'archive_member_count':12,'expanded_bytes':expanded,'allCRC_size_SHA_modes_safe_unique_nonlink_headers':True,'four_binary_SHA256SUMS_matches':True,'candidate_selected_bytes':22384802,'candidate_selected_sha256':nativehash,'candidate_source':SRC,'candidate_VCS_modified':False,'released5_bytes':len(release_raw),'released5_sha256':H(release_raw),'released5_VCS_modified':True,'released5_clean_D1_source_equivalence':'UNKNOWN','candidate_native_jat_Robot_source_binary_platform_chain':True,'private_proof':private,'data_only_no_binary_execution':True,'reviewer_probe_history':['A read-only schema probe guessed headers filename without original-artifact prefix; corrected bound path, no mutation.','Initial independent reader incorrectly required distinct native and JAT lifecycle payload equality. They share measured binary/source identity but have separate artifact/lease/materialization results. Original reader retained; successor removes only that erroneous equality. No acquisition or product gate repeated.']})
print(json.dumps({'status':'PASS_DATA_ONLY','safe_proof':safe,'reference_count':len(refs),'ZIP_members':12,'released5_modified':True,'candidate_modified':False}))
