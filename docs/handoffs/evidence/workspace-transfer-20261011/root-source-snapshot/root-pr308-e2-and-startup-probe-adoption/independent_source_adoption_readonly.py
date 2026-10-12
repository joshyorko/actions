from pathlib import Path
import ast,difflib,hashlib,json,os,stat,subprocess
OUT=Path('/workspace/engineering/pr308-current095-source-adoption-independent-review');OUT.mkdir(mode=0o700,exist_ok=True)
ROOT=Path('/workspace/engineering/pr308');env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(ROOT),*a],env=env)
def binding(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def exact(r):assert binding(r['path'])==r
def rows(ref):
 out={}
 for line in git('ls-tree','-rz',ref).split(b'\0'):
  if line:
   left,path=line.split(b'\t',1);mode,kind,oid=left.decode().split();assert kind=='blob';out[path.decode()]=(mode,oid)
 return out
owner=Path('/workspace/engineering/root-pr308-e2-and-startup-probe-adoption/OWNERFINAL-root-ordinary-e2-and-startup-probe-source-adoption.json');assert binding(owner)['sha256']=='edf047d2aeaa3b74b42cfaa3879146dfee4ee740bb9797f0f6d47c821bd39107';o=json.loads(owner.read_bytes())
private=Path('/workspace/engineering/pr308-isolated-version-probe-independent-review/OWNERFINAL-independent-private-isolated-default-version-probe-three-path-source-patch-review.json');assert binding(private)['sha256']=='108fd72da96150681b3d70cc75e5ffba47912db3f402a1f77bddbc9986fc846b';accepted=json.loads(private.read_bytes());exact(accepted['patch_binding']);exact(accepted['owner_binding']);exact(accepted['proof_binding'])
old,target,merge,current=o['source_before'],o['target'],o['ordinary_merge'],o['commit']
assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[current,o['tree']] and not git('status','--porcelain=v1')
assert git('show','-s','--format=%P',merge).decode().strip().split()==[old,target]
assert git('show','-s','--format=%P',current).decode().strip().split()==[merge]
assert git('rev-parse',merge+'^{tree}').decode().strip()==o['ordinary_tree']==accepted['source_contexts']['required_ordinary_current_target_union_tree']
assert o['tree']==accepted['source_contexts']['expected_exact_three_path_patch_tree']
l,r,m,c=rows(old),rows(target),rows(merge),rows(current)
assert len(c)==len(m)==1440 and set(m)==set(l)|set(r) and set(c)==set(m)
novel=[p for p in m if m[p] not in [l.get(p),r.get(p)]]
assert set(novel)=={'.github/workflows/_gen_workflows.py','docs/skills/repository-operations.md'}
changed=[p for p in c if c[p]!=m[p]];assert changed==accepted['verified_exact_scope']['changed_paths']
assert sum(c[p]==m[p] for p in c)==1437
# Complete typed bodies and current physical modes, no imports or source execution.
for path,(mode,oid) in c.items():
 body=git('cat-file','blob',oid);actual=ROOT/path
 if mode=='120000':assert actual.is_symlink() and os.readlink(actual).encode()==body
 else:
  assert actual.is_file() and not actual.is_symlink() and actual.read_bytes()==body
  assert bool(actual.stat().st_mode&0o111)==(mode=='100755')
# Generator union takes complete top-level nodes from the two real parents.
gen='.github/workflows/_gen_workflows.py'
def normalized(x):return ast.dump(x,include_attributes=False)
left=ast.parse(git('show',old+':'+gen));right=ast.parse(git('show',target+':'+gen));combined=ast.parse(git('show',merge+':'+gen))
assert len(combined.body)==len(left.body)==len(right.body)==32
assert all(normalized(x) in {normalized(y) for y in left.body+right.body} for x in combined.body)
assert git('show',merge+':'+gen)==git('show',current+':'+gen)
# All independently authored guide chunks relative to actual common base survive ordinary union.
guide='docs/skills/repository-operations.md';base=git('merge-base',old,target).decode().strip();base_lines=git('show',base+':'+guide).decode().splitlines(keepends=True);merged=git('show',merge+':'+guide).decode();chunk_counts={}
for ref in [old,target]:
 lines=git('show',ref+':'+guide).decode().splitlines(keepends=True);chunks=[]
 for tag,i,j,k,l0 in difflib.SequenceMatcher(a=base_lines,b=lines,autojunk=False).get_opcodes():
  if tag in ['replace','insert'] and k<l0:chunks.append(''.join(lines[k:l0]))
 assert all(chunk in merged for chunk in chunks);chunk_counts[ref]=len(chunks)
# Exact already reviewed candidate adapter and permanent regression bodies.
packet=Path(accepted['owner_binding']['path']);packetbody=json.loads(packet.read_bytes())
for row in packetbody['bindings']:exact(row)
for repo,file in [('action_server/src/actions/server/_rcc_runtime_adapter.py','proposed_rcc_runtime_adapter.py'),('action_server/tests/action_server_tests/test_rcc_runtime_adapter.py','proposed_test_rcc_runtime_adapter.py')]:
 assert (ROOT/repo).read_bytes()==(packet.parent/file).read_bytes()
# Exact literal unified guide replacement applied independently without git apply/index mutation.
canon=Path(accepted['documentation_improvement']['exact_delta_binding']['path']);exact(accepted['documentation_improvement']['exact_delta_binding']);patch=canon.read_text().splitlines(keepends=True);hunk=False;before=[];after=[]
for line in patch:
 if line.startswith('@@'):hunk=True;continue
 if not hunk:continue
 if line.startswith(' '):before.append(line[1:]);after.append(line[1:])
 elif line.startswith('-'):before.append(line[1:])
 elif line.startswith('+'):after.append(line[1:])
old_chunk=''.join(before);new_chunk=''.join(after);assert merged.count(old_chunk)==1
expected=merged.replace(old_chunk,new_chunk,1);assert expected.encode()==(ROOT/guide).read_bytes()
# Typed mode and complete non-patch preservation, including workflows/build/downloader/pins.
assert all(c[p]==m[p] for p in c if p not in changed)
assert all(c[p][0]==m[p][0] for p in changed)
assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[current,o['tree']] and not git('status','--porcelain=v1')
proof={'schema':1,'status':'PASS_CURRENT095_SOURCE_ADOPTION_ONLY','source_head':current,'source_tree':o['tree'],'ordinary_merge':merge,'ordered_merge_parents':[old,target],'sole_child_parent':merge,'ordinary_tree':o['ordinary_tree'],'complete_typed_Git_FS_union':1440,'other_exact_body_mode_pairs':1437,'deleted_leaves':0,'novel_source_paths':changed,'combined_merge_paths':novel,'generator_top_level_nodes_exact_parent_selected':32,'guide_common_base':base,'all_parent_added_or_replaced_chunks_preserved':chunk_counts,'guide_child':'EXACT_ACCEPTED_FOUR_LINE_REPLACEMENT','adapter_test_bytes':'EXACT_REVIEWED_PRIVATE_PROPOSED_BODIES','frozen_private_refs':len(packetbody['bindings']),'patch_SHA':accepted['patch_binding']['sha256'],'root_owner_binding':binding(owner),'accepted_private_review_binding':binding(private),'current_source_clean_before_after':True,'reviewer_operations':'Read-only complete Git/FS bodies/typed modes, frozen refs, source AST and literal patch application in memory; no source/index/ref/gate/native/import/download mutation.','qualification':'SOURCE_ADOPTION_ONLY; current LIGHT/FULL/CONTROL/native/currentCI not carried','upstream_disposition':'none'}
p=OUT/'independent-current095-complete-source-adoption-proof.json'
with p.open('x') as w:json.dump(proof,w,sort_keys=True,indent=2);w.write('\n')
p.chmod(0o400);print(json.dumps(binding(p)))
