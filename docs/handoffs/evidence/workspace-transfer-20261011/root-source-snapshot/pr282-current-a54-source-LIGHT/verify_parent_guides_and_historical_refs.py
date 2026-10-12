from pathlib import Path
import difflib,hashlib,json,os,stat,subprocess
R=Path('/workspace/engineering/pr282');O=Path('/workspace/engineering/pr282-current-a54-source-LIGHT')
def git(*args,cwd=R):return subprocess.check_output(['git','-C',str(cwd),*args])
def sha(raw):return hashlib.sha256(raw).hexdigest()
def row(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
head=git('rev-parse','HEAD').decode().strip();parents=git('show','-s','--format=%P','HEAD').decode().split();base=git('merge-base',*parents).decode().strip();assert base=='a0d258a16095b95b1bf9000cb1201cddfaff4779'
proof=[]
for path in ['docs/skills/repository-operations.md','docs/skills/provenance-observability.md']:
 ancestor=git('show',base+':'+path).decode();current=(R/path).read_text();groups=[]
 for parent in parents:
  text=git('show',parent+':'+path).decode();blocks=[]
  for kind,a,b,c,d in difflib.SequenceMatcher(a=ancestor.splitlines(True),b=text.splitlines(True),autojunk=False).get_opcodes():
   if kind in ('insert','replace'):
    block=''.join(text.splitlines(True)[c:d]);assert block in current,(path,parent,kind);blocks.append({'kind':kind,'lines':d-c,'bytes':len(block.encode()),'sha256':sha(block.encode())})
  groups.append({'parent':parent,'changed_blocks_present_exact':blocks})
 proof.append({'path':path,'base':base,'current_sha256':sha(current.encode()),'both_parent_groups':groups})
patch=git('diff',parents[0],head,'--','docs/skills/repository-operations.md','docs/skills/provenance-observability.md');p=O/'exact-imported-a54-canonical-guide-delta.patch';p.write_bytes(patch);p.chmod(0o600)
old=json.loads(Path('/workspace/engineering/pr282-actual309-refresh/FROZEN-before-source-original-e736-bindings.json').read_text());assert len(old['all_bound_refs_current_bytes_modes'])==441
current=[];historical=[]
for expected in old['all_bound_refs_current_bytes_modes']:
 p=Path(expected['path']);assert p.is_file();observed=row(p)
 if observed==expected:current.append(observed);continue
 assert str(p)=='/workspace/engineering/pr305/docs/skills/repository-operations.md'
 source='3ec9d0acbe30ad94d02e4c24fef2587127964495';body=git('show',source+':docs/skills/repository-operations.md',cwd=Path('/workspace/engineering/pr305'));assert sha(body)==expected['sha256'] and len(body)==expected['bytes']
 historical.append({'original_binding':expected,'disposition':'ORIGINAL_GIT_BODY_VERIFIED_CURRENT_WORKTREE_ADVANCED','immutable_source':source,'Git_path':'docs/skills/repository-operations.md','current_binding':observed,'not_claimed':'Current mutable guide body equality to old original'})
assert len(current)==440 and len(historical)==1
oldowner=Path('/workspace/engineering/pr282-actual309-refresh/OWNERFINAL-current-c35e-ordinary-a0d-source-LIGHT-full-and-actual-HOLD.json');assert sha(oldowner.read_bytes())=='79513104c6a9b9bc67d6b1d58ce2993bead4cc8db156dee99ab0dada3ecd12b8'
for expected in json.loads(oldowner.read_text())['evidence_bindings']:
 assert row(expected['path'])==expected
assert git('status','--porcelain')==b''
proof={'status':'PASS_BOTH_PARENT_GUIDE_BLOCKS_AND_TYPED_HISTORICAL_RETENTION','head':head,'ordered_parents':parents,'mergebase':base,'guides':proof,'exact_imported_patch':row(O/'exact-imported-a54-canonical-guide-delta.patch'),'historical441':{'current_exact':440,'immutable_Git_classification':historical,'historical_UNAVAILABLE_original_bindings':old['historical_UNAVAILABLE_original_bindings']},'original_c35_OWNER_and_evidence_files_unchanged':True,'claims':'Historical Git body classification is preservation, not current mutable path equality. No reconstructed unavailable evidence.'}
p=O/'verified-both-parent-canonical-and-historical-reference-preservation.json';p.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');p.chmod(0o600);print(json.dumps({'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size,'current_refs':440,'historical_Git':1,'guide_paths':2}))
