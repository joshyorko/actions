from pathlib import Path
import difflib,hashlib,json,os,stat,subprocess
R=Path('/workspace/engineering/pr305');O=Path('/workspace/engineering/pr305-current-a54-source-LIGHT')
def git(*args,cwd=R):return subprocess.check_output(['git','-C',str(cwd),*args])
def sha(raw):return hashlib.sha256(raw).hexdigest()
def row(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
head=git('rev-parse','HEAD').decode().strip();parents=git('show','-s','--format=%P','HEAD').decode().split();base=git('merge-base',*parents).decode().strip();assert base=='e3c29cde8878307912e55ed09b6436c0f91d06d5'
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
assert git('status','--porcelain')==b''
result={'status':'PASS_BOTH_PARENT_CANONICAL_GUIDE_BLOCKS','head':head,'ordered_parents':parents,'mergebase':base,'guides':proof,'exact_imported_patch':row(O/'exact-imported-a54-canonical-guide-delta.patch'),'scope':'Exact automatic union imports verified accepted generated-asset/checkout-byte and ASGI send-ordering lessons; current source gates remain separate from native/client delivery/release qualification.'}
p=O/'verified-both-parent-canonical-guide-block-preservation.json';assert not p.exists();p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');p.chmod(0o600);print(json.dumps({'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}))
