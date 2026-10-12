import hashlib,json,os,subprocess
from pathlib import Path
r=Path('/workspace/engineering/runtime-checkout-eol');o=Path('/workspace/engineering/pr312-actual309-refresh')
def git(*args):return subprocess.check_output(['git',*args],cwd=r)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inv(ref):
 out={}
 for rec in git('ls-tree','-rz',ref).split(b'\0'):
  if rec:
   meta,p=rec.split(b'\t');mode,kind,blob=meta.decode().split();out[p.decode()]={'mode':mode,'type':kind,'blob':blob}
 return out
head=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip();parents=git('show','-s','--format=%P','HEAD').decode().split()
assert head=='77065131a0aee63d2b1f8621476374bdde3c7b65' and tree=='edf1801e565692fb3f07b809b3a95b27981fe2fe'
assert parents==['92e6deda5c252a503510c4b6261a86cb51f73cb6','a0d258a16095b95b1bf9000cb1201cddfaff4779']
assert git('status','--porcelain')==b''
a,b=map(inv,parents);m=inv(head);assert len(m)==1423 and set(m)==set(a)|set(b)
for p,row in m.items():
 f=r/p;body=f.read_bytes();blob=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest();assert blob==row['blob'],p;assert bool(f.stat().st_mode&0o111)==(row['mode']=='100755'),p
 if not p.startswith('docs/'):
  assert row==a.get(p) or row==b.get(p),p
source_delta=git('diff','--name-only','6181b044c75de35386f1ae30e71725398b6a7feb',parents[0]).decode().splitlines();assert len(source_delta)==7
for p in source_delta:
 if not p.startswith('docs/'):assert m[p]==a[p],p
textpaths=['action_server/frontend/apps/runtime/index.html','action_server/src/actions/server/README.md','action_server/src/actions/server/bin/.gitignore','action_server/src/actions/server/index.html','action_server/src/actions/server/templates/action-templates.yaml','action_server/src/actions/server/vendored_deps/README.md']
selected=sorted(p for p in a if (p.startswith('action_server/src/') and p.endswith('.py')) or p in textpaths);assert len(selected)==207
for p in selected:assert m[p]==a[p],p
for p in ['action_server/tests/action_server_tests/test_auth_route_inventory.py','action_server/tests/action_server_tests/test_auth_route_enforcement.py']:assert m[p]==b[p],p
path='docs/skills/repository-operations.md';diff=git('diff','--unified=0','6181b044c75de35386f1ae30e71725398b6a7feb',parents[0],'--',path).decode();lesson='\n'.join(line[1:] for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++'))+'\n';assert len(lesson.splitlines())==16
combined=git('show',head+':'+path).decode();assert combined.count(lesson)==1;assert combined.replace(lesson,'',1)==git('show',parents[1]+':'+path).decode()
old=Path('/workspace/engineering/runtime-checkout-eol-source/OWNERFINAL-runtime-checkout-eol-SOURCEFINAL.json');assert sha(old)=='b0d51fbc7fb87c88fc0f65af090634cc44c7cfb311e00de7b56472160b074189';refs=json.loads(old.read_text())['immutable_evidence_bindings'];assert len(refs)==62
for row in refs:
 p=Path(row['path']);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],p
pin=r/'action_server/src/actions/server/bin/rcc-18.19.3';assert sha(pin)=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428';assert pin.stat().st_mode&0o777==0o711
result={'status':'PASS_COMPLETE_COMMITTED_UNION_AND_RETAINED_SOURCE','head':head,'tree':tree,'ordered_parents':parents,'typed_count':len(m),'complete_Git_FS_bodies_executable_modes_exact':True,'all_parent_paths_retained':True,'no_novel_non_doc_blob_or_mode':True,'source_seven_delta_paths':source_delta,'all207_original_selected_inputs_modes_exact':True,'all2_target_auth_tests_modes_exact':True,'guide_exact_source16_lines_and_complete_target_document_preserved':True,'sourceFINAL62_refs_exact':True,'ignored_RCC0711_exact':True,'typed_leaves':m,'selected207':selected,'documentation_exact_imported_lesson':lesson,'free_bytes':os.statvfs(r).f_bavail*os.statvfs(r).f_frsize}
(o/'committed-complete-union-pre-light.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS_COMMITTED1423_GIT_FS207_SOURCE62_REFS_RCC0711')
