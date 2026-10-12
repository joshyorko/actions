from pathlib import Path
import hashlib,json,os,stat,subprocess
R=Path('/workspace/engineering/pr282');D=Path('/workspace/engineering/pr282-actual309-refresh');A='e736f846557ed1d603348e97c5eb80060d62e3e2';B='a0d258a16095b95b1bf9000cb1201cddfaff4779'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def inv(ref):
 out={}
 for rec in git('ls-tree','-rz',ref).split(b'\0'):
  if rec:
   a,p=rec.split(b'\t',1);out[p.decode()]=a.decode().split()
 return out
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
a,b=inv(A),inv(B);tree=git('write-tree').decode().strip();m=inv(tree);assert len(m)==1435 and set(m)==set(a)|set(b)
assert git('rev-parse','HEAD').decode().strip()==A and git('rev-parse','MERGE_HEAD').decode().strip()==B
for path,row in m.items():
 p=R/path;mode,typ,blob=row;body=os.readlink(p).encode() if mode=='120000' else p.read_bytes();assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==blob
 if mode!='120000':assert bool(p.stat().st_mode&0o111)==(mode=='100755')
 if path!='docs/skills/repository-operations.md':assert row==a.get(path) or row==b.get(path)
for path,row in a.items():
 if path!='docs/skills/repository-operations.md':assert m[path]==row
added=sorted(set(m)-set(a));assert added==['action_server/tests/action_server_tests/test_auth_route_enforcement.py','action_server/tests/action_server_tests/test_auth_route_inventory.py']
for path in added:assert m[path]==b[path]
changed=sorted(p for p in a if m[p]!=a[p]);assert changed==['docs/skills/repository-operations.md']
base=git('merge-base',A,B).decode().strip();blocks=[]
for path in ['docs/skills/repository-operations.md','docs/skills/provenance-observability.md']:
 text=git('show',tree+':'+path).decode()
 for parent in (A,B):
  diff=git('diff','--unified=0',base,parent,'--',path).decode();chunk=[]
  for line in diff.splitlines(True)+['END']:
   if line.startswith('+') and not line.startswith('+++'):chunk.append(line[1:])
   elif chunk:
    block=''.join(chunk);assert block in text;blocks.append({'file':path,'parent':parent,'lines':len(chunk),'sha256':hashlib.sha256(block.encode()).hexdigest()});chunk=[]
old=json.loads(Path('/workspace/engineering/pr282-actual618-refresh/frozen-source-receipt.json').read_text());prod=old['current_producer'];assert prod['current']==275
for p,row in prod['typed_inventory'].items():assert m[p]==row
for p,row in old['five_selected_tests_separate'].items():assert m[p]==row
for p,row in a.items():
 if p.startswith('.github/'):assert m[p]==row
# Complete source identity implies the entire Canvas helper/generator/workflow/39predicates and9RCC inputs unchanged.
patch=git('diff',A,tree,'--','docs/skills');pp=D/'exact-both-parent-canonical-import.patch';assert not pp.exists();pp.write_bytes(patch);pp.chmod(0o600)
result={'status':'PASS_AUTOMATIC_FULL_PARENT_UNION_BEFORE_COMMIT','ordered_parents':[A,B],'expected_tree':tree,'count':1435,'all1433_old_leaves_retained_except_owningguide_exact':True,'no_novel_application_body_mode':True,'added_exact_target_auth_tests':added,'changed_exact_source_guide':changed,'typed_union':m,'both_parent_guide_additions_retained':blocks,'whole_GitHub_original_source_exact':True,'entire_Canvas_original_helpers_tests_generator_workflow39predicates_unchanged':True,'nine_RCC_sample_source_unchanged':True,'current_production':275,'historical_production':268,'oldmatches':259,'changed':9,'added':7,'selected_tests_separate':5,'combined280not_oldnative_qualified':True,'construction_history_before_merge_retained':str(D/'initial-pre-source-inspector-construction-history.json'),'source_LIGHT_gates_NOT_RUN':True,'Upstream_disposition':'none'}
p=D/'FROZEN-staged-automatic-a0d-union-proof.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'tree':tree,'count':1435}))
