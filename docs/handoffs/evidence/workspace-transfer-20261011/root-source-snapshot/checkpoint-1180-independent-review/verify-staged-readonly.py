import collections
import hashlib
import json
import pathlib
import re
import stat
import subprocess

W = pathlib.Path('/workspace/engineering/campaign-checkpoint')
OUT = pathlib.Path('/workspace/engineering/checkpoint-1180-independent-review')
PFX = 'docs/program/evidence/wave11/current-engineering-20261011/'
def sha(b): return hashlib.sha256(b).hexdigest()
def git(*args): return subprocess.check_output(['git', '--no-optional-locks', *args], cwd=W)
def save(n,d):
    p=OUT/n
    with p.open('x') as f: json.dump(d,f,indent=2,sort_keys=True); f.write('\n')
    p.chmod(0o444)
    return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
ownerpath=pathlib.Path('/workspace/engineering/checkpoint-1180-staged-identity.json')
ownerbytes=ownerpath.read_bytes(); owner=json.loads(ownerbytes)
assert len(ownerbytes)==1195 and sha(ownerbytes)=='33287890a920eb440cb4f0d3e682ec572375a0d111bccad5567f93b71613aa39'
assert git('rev-parse','HEAD').decode().strip()==owner['base']
assert git('branch','--show-current').decode().strip()==owner['branch']
assert not git('diff','--name-only')
indexraw=git('ls-files','-s','-z'); assert sha(indexraw)==owner['index_sha256']
namesraw=git('diff','--cached','--name-only','-z'); assert sha(namesraw)==owner['staged_names_sha256']
entries={}
for row in indexraw.split(b'\0'):
    if not row: continue
    fields,p=row.split(b'\t',1); mode,blob,stage=fields.decode().split();assert stage=='0'
    entries[p.decode()]={'mode':mode,'blob':blob,'type':'blob'}
parent={}
for row in git('ls-tree','-rz','HEAD').split(b'\0'):
    if row:
        fields,p=row.split(b'\t',1);mode,typ,blob=fields.decode().split();parent[p.decode()]={'mode':mode,'blob':blob,'type':typ}
changed={p for p in set(entries)|set(parent) if entries.get(p)!=parent.get(p)}
assert changed==set(namesraw.decode().strip('\0').split('\0'))
manifestbytes=git('show',':'+PFX+'manifest.json');manifest=json.loads(manifestbytes)
assert len(manifestbytes)==owner['manifest']['bytes'] and sha(manifestbytes)==owner['manifest']['sha256']
old=json.loads(git('show','HEAD:'+PFX+'manifest.json'))
assert len(old)==644 and len(manifest)==1180 and all(manifest[k]==v for k,v in old.items())
new={k:v for k,v in manifest.items() if k not in old}
assert len(new)==536 and sum(v['bytes'] for v in new.values())==27405588
planpath=pathlib.Path('/workspace/engineering/checkpoint-current-engineering-after309-frozen-input-plan.json')
plan=json.loads(planpath.read_bytes()); assert plan==new
assert changed=={PFX+k for k in new}|{PFX+'README.md',PFX+'manifest.json','docs/skills/repository-operations.md'}
# Compare the already-created frozen tree object; do not write a Git tree.
treeraw=git('ls-tree','-rz',owner['tree']); tree={}
for row in treeraw.split(b'\0'):
    if row:
        fields,p=row.split(b'\t',1);mode,typ,blob=fields.decode().split();tree[p.decode()]={'mode':mode,'blob':blob,'type':typ}
assert tree==entries
source_records=[];privacy_hits=[];url_hosts=collections.Counter();bound={}; objects={}
pattern=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|[?&](?:X-Amz-Signature|sig)=|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
def walk(obj,payload):
    if isinstance(obj,dict):
        dig=obj.get('sha256',obj.get('expected_sha256'))
        path=obj.get('path',obj.get('source'))
        if isinstance(path,str) and path.startswith('/') and isinstance(dig,str) and re.fullmatch('[0-9a-f]{64}',dig):
            size=obj.get('bytes',obj.get('expected_bytes')); size=size if isinstance(size,int) and not isinstance(size,bool) else None
            key=(path,dig,size);bound.setdefault(key,set()).add(payload)
        for value in obj.values(): walk(value,payload)
    elif isinstance(obj,list):
        for value in obj: walk(value,payload)
for name,record in manifest.items():
    entry=entries[PFX+name]; assert entry['mode']=='100644' and entry['type']=='blob'
    data=git('show',':'+PFX+name)
    assert len(data)==record['bytes'] and sha(data)==record['sha256']
    copy=W/(PFX+name); assert copy.read_bytes()==data and not(copy.stat().st_mode & 0o111)
    src=pathlib.Path(record['source'])
    if src.is_file():
        original=src.read_bytes(); assert original==data,(name,'source mismatch'); disposition='named_original_exact'
    else:
        assert name=='pr290-actual-integration.json' and name in old
        disposition='inherited_authenticated_nonfile_source_label_exact_parent_blob'
    if name in old: assert parent[PFX+name]==entry
    source_records.append({'payload':name,**entry,**record,'source_disposition':disposition})
    if name in new:
        assert pathlib.Path(name).suffix in ('.json','.patch')
        assert pathlib.Path(record['source']).suffix in ('.json','.patch')
        assert not any(s in pathlib.Path(record['source']).name for s in ('.raw.','.private.','.request.','private-'))
        text=data.decode()
        if pattern.search(text):privacy_hits.append(name)
        for host in re.findall(r'https?://([^/\s\"<>]+)',text):url_hosts[host]+=1
        if name.endswith('.json'):
            obj=json.loads(data);objects[name]=obj;walk(obj,name)
assert not privacy_hits
proof=save('all1180-original-copy-typed-staged-byte-proof.json',{'schema':'independent_readonly_staged1180_byte_proof','owner':{'path':str(ownerpath),'bytes':len(ownerbytes),'sha256':sha(ownerbytes)},'base':owner['base'],'tree':owner['tree'],'semantic_index_sha256':sha(indexraw),'staged_names_sha256':sha(namesraw),'staged_paths':len(changed),'all_other_parent_entries_unchanged':True,'prior644_manifest_records_blobs_modes_exact':True,'new536_bytes':27405588,'records':source_records,'frozen_plan':{'path':str(planpath),'bytes':planpath.stat().st_size,'sha256':sha(planpath.read_bytes())},'privacy_token_signed_URL_hits':[],'new536_extensions':dict(collections.Counter(pathlib.Path(k).suffix for k in new)),'URL_hosts':dict(url_hosts)})
print(json.dumps({'primary_proof':proof,'unique_new_nested_bindings':len(bound),'staged_paths':len(changed),'new_extensions':dict(collections.Counter(pathlib.Path(k).suffix for k in new)),'url_host_count':len(url_hosts)}))
# Hash each current path once; never import or execute referenced candidate code.
cache={};results=[]
for (path,dig,size),owners in sorted(bound.items()):
    p=pathlib.Path(path)
    if path not in cache:
        if p.is_file():
            h=hashlib.sha256()
            with p.open('rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
            cache[path]=(p.stat().st_size,h.hexdigest())
        else:cache[path]=None
    actual=cache[path]
    status='EXACT' if actual and actual[1]==dig and (size is None or actual[0]==size) else ('ABSENT' if actual is None else 'NONCURRENT_ALIAS')
    results.append({'path':path,'expected_bytes':size,'expected_sha256':dig,'status':status,'payloads':sorted(owners),'actual_bytes':actual[0] if actual else None,'actual_sha256':actual[1] if actual else None})
nested=save('new536-nested-original-binding-readback.json',{'unique_bindings':len(bound),'unique_current_paths_hashed':len(cache),'counts':dict(collections.Counter(r['status'] for r in results)),'results':results,'scope':'Historical cleaned installed trees and changed source aliases require explicit retained measurement/Git-original dispositions; exact bytes alone do not expand acceptance.'})
print(json.dumps({'nested_proof':nested,'nested_counts':dict(collections.Counter(r['status'] for r in results))}))
patch=git('diff','--cached','--','docs/skills/repository-operations.md')
save('exact-staged-canonical74-delta.patch',{}) if False else None
pp=OUT/'exact-staged-canonical74-delta.patch';pp.write_bytes(patch);pp.chmod(0o444)
adds=[x[1:] for x in patch.decode().splitlines() if x.startswith('+') and not x.startswith('+++')]
removes=[x for x in patch.decode().splitlines() if x.startswith('-') and not x.startswith('---')]
assert len(adds)==74 and not removes
guide=git('show',':docs/skills/repository-operations.md').decode();blocks=[]
for prefix in ['Verified reuse of package environments','Runtime’s configured','A captured-tree cleanup','A current PR merge ref','Evaluate workflow path filters','Verbose pytest output','When qualifying generated Runtime','Archive size and digest','Before a retained-wheel consumer']:
    candidates=[]
    for name in new:
        if name.endswith('.patch'):
            lines=(W/(PFX+name)).read_text().splitlines()
            added=[s[1:] for s in lines if s.startswith('+') and not s.startswith('+++')]
            if any(s.startswith(prefix) for s in added):
                block='\n'.join(added).strip('\n')
                if block in guide:candidates.append({'payload':name,'source':manifest[name]['source'],'bytes':manifest[name]['bytes'],'sha256':manifest[name]['sha256'],'added_lines':len(added),'exact_text_in_staged_guide':True})
    assert candidates,prefix
    blocks.append({'first_line':prefix,'accepted_exact_proposals':candidates})
canonical=save('canonical74-and-README-scope-proof.json',{'canonical_delta':{'path':str(pp),'bytes':len(patch),'sha256':sha(patch),'added_lines':74,'removed_lines':0,'blocks':blocks},'README_delta_sha256':sha(git('diff','--cached','--',PFX+'README.md')),'README_scope':'a0d actual309 and current/source/CI/platform/consumer/private/release holds; unchanged644 history and unrecovered22524B alias explicitly retained','upstream_disposition':'none'})
assert sha(git('ls-files','-s','-z'))==owner['index_sha256'] and sha(git('diff','--cached','--name-only','-z'))==owner['staged_names_sha256']
print(json.dumps({'canonical_proof':canonical,'index_post_exact':True}))
