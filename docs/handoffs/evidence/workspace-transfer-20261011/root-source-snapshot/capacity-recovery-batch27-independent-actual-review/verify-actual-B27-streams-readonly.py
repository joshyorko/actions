from pathlib import Path, PurePosixPath
import gzip
import hashlib
import json
import os
import stat
import subprocess
import tarfile

OUT=Path('/workspace/engineering/capacity-recovery-batch27-independent-actual-review')
BASE=Path('/workspace/engineering/capacity-recovery-batch27-proposal')
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()
proposal=BASE/'OWNERFINAL-batch27-exact-three-completed-existing-tmp-preexecution-proposal-v2.json'
assert sha(proposal)=='dabe89c9b8d05c714207c7880b30195baf90c341fd3ecc657b9143545d6d2673'
p=json.loads(proposal.read_bytes())
assert sha(p['script']['path'])==p['script']['sha256']
before=json.loads(Path(p['private_proof_bindings'][2]['path']).read_bytes())
assert before['first']==before['second']
private_index=Path('/tmp/actions-completed-scratch-recovery-batch27/private-complete-inventory-and-recovery.json')
assert sha(private_index)=='e1cc9d4260af8ca52eb72c1e673dde763be4eada602c3a29bf3ae62b5b5e353f'
assert stat.S_IMODE(private_index.stat().st_mode)==0o600
index=json.loads(private_index.read_bytes());assert len(index['records'])==3
members=0;archive_rows=[]
for row,name in zip(index['records'],p['names_exact_allowlist']):
    assert row['original_namespace']=='/workspace/actions-cloud/robocorp/temp/'+name
    assert not Path(row['original_namespace']).exists()
    assert row['archive_verified_before_original_removal'] is True and row['expanded_removed'] is True
    assert row['inventory']==before['first'][name]
    archive=Path(row['archive'])
    assert archive==private_index.parent/(name+'.tar.gz')
    assert not archive.is_symlink() and archive.stat().st_size==row['archive_bytes']
    assert stat.S_IMODE(archive.stat().st_mode)==0o600
    assert sha(archive)==row['archive_sha256']
    # gzip footer/CRC/ISIZE and concatenated stream validation, without extraction.
    with gzip.open(archive,'rb') as compressed:
        for _ in iter(lambda:compressed.read(1048576),b''):pass
    with tarfile.open(archive,'r:gz') as tar:
        raw=tar.getmembers();assert len({m.name for m in raw})==len(raw)
        assert all(not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts for m in raw)
        root_member=next(m for m in raw if m.name==name);assert root_member.isdir()
        entries={m.name[len(name)+1:]:m for m in raw if m.name!=name}
        assert set(entries)==set(row['inventory'])
        for rel,expected in row['inventory'].items():
            member=entries[rel]
            assert member.name==name+'/'+rel
            assert member.mode==expected['mode'] and member.uid==expected['uid'] and member.gid==expected['gid']
            if expected['kind']=='file':
                assert member.isfile() or member.islnk()
                if member.islnk():
                    target=PurePosixPath(member.linkname)
                    assert not target.is_absolute() and '..' not in target.parts
                    assert member.linkname in {m.name for m in raw}
                stream=tar.extractfile(member);assert stream is not None
                h=hashlib.sha256();size=0
                for block in iter(lambda:stream.read(1048576),b''):h.update(block);size+=len(block)
                assert size==expected['bytes'] and h.hexdigest()==expected['sha256']
            elif expected['kind']=='symlink':assert member.issym() and member.linkname==expected['target']
            elif expected['kind']=='directory':assert member.isdir()
            elif expected['kind']=='fifo':assert member.isfifo()
            else:raise AssertionError('Unknown recorded type')
    members+=len(row['inventory'])
    assert row['verified_members']==len(row['inventory'])
    archive_rows.append({'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(row['inventory'])})
assert members==15195
ret=json.loads(Path(p['private_proof_bindings'][4]['path']).read_bytes())
assert len(ret['archives'])==58 and len(ret['indices'])==26
for row in ret['archives']+ret['indices']:
    path=Path(row.get('path',row.get('archive')))
    assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
    assert oct(stat.S_IMODE(path.stat().st_mode))==row['mode']
current=Path('/workspace/engineering/pr308')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=current,text=True).strip()==p['current_source_owner_context']['head']
assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=current,text=True).strip()==p['current_source_owner_context']['tree']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=current)
count=0
for entry in subprocess.check_output(['git','ls-tree','-rz','HEAD'],cwd=current).split(b'\0'):
    if not entry:continue
    meta,rel=entry.split(b'\t',1);mode,kind,obj=meta.split();assert kind==b'blob'
    leaf=current/os.fsdecode(rel);st=leaf.lstat();raw=os.readlink(leaf).encode() if mode==b'120000' else leaf.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==obj.decode()
    if mode!=b'120000':assert bool(st.st_mode&0o111)==(mode==b'100755')
    count+=1
assert count==1423
cfg=json.loads(Path('/workspace/engineering/rcc-compatibility-current-e4ff-qualified-config-successor/FROZEN-current-e4ff-control3-owned-cache-SOURCE-QUALIFIED-v4.json').read_bytes())
assert len(cfg['native_original_members'])==1192
for row in cfg['native_original_members']:
    leaf=Path(cfg['native_original_root'])/row['path'];st=leaf.lstat();assert stat.S_IMODE(st.st_mode)==row['mode']
    if row['kind']=='file':assert sha(leaf)==row['content_sha256']
    elif row['kind']=='symlink':assert os.readlink(leaf)==row['link_target']
    else:assert row['kind']=='directory' and leaf.is_dir()
for rel,digest in cfg['prepared_inputs'].items():assert sha(current/rel)==digest
assert Path('/workspace/actions-cloud/robocorp/temp/563d911e4172f035').exists()
failed=Path('/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-2/OWNERFINAL-one-version-actual-result.json')
assert sha(failed)=='d4ebd4111e362d3ac3f8dc519d3826ad19c71e1d06dffe7dd959a4ebd2b45ca8'
old=Path('/workspace/engineering/root-B27-one-existing-tmp-recovery/OWNERFINAL-root-one-B27-existing-tmp-volume-terminal.json')
old_result=json.loads(old.read_bytes());assert old_result['primary_returncode'] is None and old_result['error_class']=='KeyError'
assert not (old.parent/'original-command-terminal.json').exists()
term=Path('/workspace/engineering/root-B27-one-existing-tmp-recovery-named-v2/OWNERFINAL-root-one-B27-named-metadata-existing-tmp-terminal.json')
assert sha(term)=='2a0d859cd511fc3bfdd7906d7a0131fca8ee88ff64bb5e320eff8242a2823e7b'
t=json.loads(term.read_bytes());assert t['archive_attempts']==1 and t['primary_returncode']==0 and t['post_guard']==0 and t['status']=='PRESERVATION_ONLY_PASS'
command=json.loads((term.parent/'original-command-terminal.json').read_bytes());assert command=={'returncode':0,'archive_attempts':1}
proof={'schema':1,'status':'INDEPENDENT_B27_PRESERVATION_ONLY_GO','archives':archive_rows,'new_members':members,'prior_archives58_indices26_rehashed':True,'current_source1423_body_modes':True,'native1192_prepared30':True,'original_failed563_exists_only':True,'small_failed_RCC_original_unchanged':True,'original_rootwrapper_primary_not_started':True,'named_root_archive_attempts':1,'recorded_primary0_post0':True,'no_extraction_or_mutation_or_native_by_reviewer':True,'unrecorded_root_metadata_and_exact_TAR_mtime_and_otherUID_quiescence':'UNKNOWN'}
out=OUT/'independent-B27-original-actual-stream-proof.json';assert not out.exists();out.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');out.chmod(0o400)
print(json.dumps({'path':str(out),'bytes':out.stat().st_size,'sha256':sha(out)}))
