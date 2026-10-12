import json,hashlib,stat,os,subprocess
from pathlib import Path
OUT=Path(__file__).parent
READ=Path('/workspace/engineering/pytest38-completed-preservation-readonly-proposal')
SOURCE=Path('/workspace/engineering/pr308')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 return dict(path=str(p),bytes=s.st_size,sha256=sha(p),mode=oct(stat.S_IMODE(s.st_mode)))
def save(n,d):
 p=OUT/n;p.open('x').write(json.dumps(d,sort_keys=True,separators=(',',':'))+'\n');p.chmod(0o600);return bind(p)
proposal=READ/'OWNERFINAL-exact-completed-pytest38-bounded-storage-preservation-proposal.json';assert sha(proposal)=='a38007f37e1e319f2bce9752f369b5cb88a2a83700c93db37bd4ef81571d005a';owner=json.loads(proposal.read_bytes())
original_inputs=Path('/workspace/engineering/rcc-control3-failed-owned-preservation-proposal/frozen-preservation-inputs-v4.json');old=json.loads(original_inputs.read_bytes());transport=json.loads(Path(old['transport_config']['path']).read_bytes());progress=json.loads(Path(old['source_progress']['path']).read_bytes())
retained={r['path']:r for r in old['bindings']}
for key in ['private_proof','private_complete_inventory','readonly_inspector','owner_sourceFULL']:
 r=owner[key];assert bind(r['path'])==r;retained[r['path']]=r
for r in owner['bound_original_sourcefull_records']:assert bind(r['path'])==r;retained[r['path']]=r
for r in [bind(proposal),bind(original_inputs),owner['documentation_improvement']['accepted_principle'],owner['documentation_improvement']['exact_new_delta']]:retained[r['path']]=r
previous=Path('/workspace/engineering/capacity-recovery-batch27-proposal/private-all58-original-archives26-indices-current-SHA-mode-retention.json');prior=json.loads(previous.read_bytes());arcs=[]
for row in prior['archives']:r=dict(path=row['archive'],bytes=row['bytes'],sha256=row['sha256'],mode=row['mode']);arcs.append(r)
indices=prior['indices'][:];p=Path('/tmp/actions-completed-scratch-recovery-batch27/private-complete-inventory-and-recovery.json');indices.append(bind(p));new=json.loads(p.read_bytes())
for r in new['records']:
 assert r['archive_verified_before_original_removal'] and r['expanded_removed'] and not Path(r['original_namespace']).exists()
 arcs.append(dict(path=r['archive'],bytes=r['archive_bytes'],sha256=r['archive_sha256'],mode='0o600'))
assert len(arcs)==61 and len(indices)==27
for r in arcs+indices:assert bind(r['path'])==r;retained[r['path']]=r
mapping_path=Path('/workspace/engineering/root-failed-control3-one-byte-preservation-v4/root-exact-historical-failed-member-archive-mapping.json');mapping=json.loads(mapping_path.read_bytes());retained[str(mapping_path)]=bind(mapping_path)
for key in ['archive','complete_index','expanded_removal','root_original_terminal']:
 r=mapping[key];assert bind(r['path'])==r;retained[r['path']]=r
head=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD']).decode().strip();tree=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD^{tree}']).decode().strip();assert head=='396925cb3d6527af1768b7f5333f9653c005fc55' and tree=='84f850f0d4e08b21afcd8220413ce94322370acf';assert subprocess.check_output(['git','-C',str(SOURCE),'status','--porcelain'])==b''
rows=[]
for item in subprocess.check_output(['git','-C',str(SOURCE),'ls-tree','-r','-z',head]).split(b'\x00'):
 if not item:continue
 meta,name=item.split(b'\t',1);mode,kind,oid=meta.decode().split();assert kind=='blob';path=name.decode();p=SOURCE/path
 body=subprocess.check_output(['git','-C',str(SOURCE),'cat-file','blob',oid]);fs=os.fsencode(os.readlink(p)) if mode=='120000' else p.read_bytes();assert body==fs
 rows.append(dict(path=path,mode=mode,oid=oid,bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),fs_mode=stat.S_IMODE(p.lstat().st_mode)))
assert len(rows)==1426
historical=progress['body_modes'];assert len(historical)==1423
for r in retained.values():assert bind(r['path'])==r
cfg=dict(schema=1,readonly_proposal=bind(proposal),owner_proposal=bind(proposal),
 original_inventory=owner['private_complete_inventory'],root_uid_gid=[1000,1000],
 root_original=owner['root_recorded_identity'],source_root=str(SOURCE),current_head=head,current_tree=tree,
 current_rows=rows,historical_head=progress['head'],historical_tree=progress['tree'],historical_rows=historical,
 current_SOURCEFULL='NOT_QUALIFIED',prepared_inputs=transport['prepared_inputs'],
 native_root=transport['native_original_root'],native_members=transport['native_original_members'],
 retained_files=sorted(retained.values(),key=lambda r:r['path']),prior_archives_count=61,prior_indices_count=27,
 failed563_existence_only='/workspace/actions-cloud/robocorp/temp/563d911e4172f035',
 failed_archive=mapping['archive'],failed_result_member='actions-rcc-compatibility-actual-control3-20261011-1/OWNERFINAL-one-version-actual-result.json',
 failed_result_sha256='8dc25bb1b99503af386d12d32c0637aa3503617c6f97d66a83f4643969934d4c',failed_result_bytes=1696,
 fixed_destination='/tmp/actions-completed-pytest38-preservation-one-owned',
 fixed_stage='/tmp/actions-completed-pytest38-preservation-one-owned-stage',
 maximum_archive=335544320,remaining_reserve=134217728,required_tmp=469762048,
 future_inner_seconds=600,inner_kill_grace=10,future_outer_seconds=900,outer_kill_grace=10,
 source_origin='CORRELATION_ONLY',universal_quiescence='UNKNOWN')
config=save('private-current396-data-only-guard-and-exact-pytest38-inputs.json',cfg)
print(json.dumps(dict(config=config,current_source=head,current_tree=tree,current_rows=len(rows),historical_rows=len(historical),native=len(transport['native_original_members']),retained_files=len(retained),prior_archives=61,prior_indices=27)))
