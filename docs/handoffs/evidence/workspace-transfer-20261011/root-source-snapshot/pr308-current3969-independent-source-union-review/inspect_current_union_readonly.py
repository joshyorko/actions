import ast
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

ROOT=Path('/workspace/engineering/pr308');OUT=Path(__file__).resolve().parent
HEAD='396925cb3d6527af1768b7f5333f9653c005fc55'
SOURCE='2058b1b185a79c04b24eaf46a73d278ba4f689e5'
TARGET='a54c982462d1e7ad011d8152bfc299d997503fb3'
ORIGINAL='e4ff080375a8422bb656e52d218f198521dda078'
ENV=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a],env=ENV)
def sha(b):return hashlib.sha256(b).hexdigest()
def bind(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def tree(c):
 result={}
 for line in git('ls-tree','-rz',c).split(b'\0'):
  if line:
   meta,path=line.split(b'\t');mode,kind,oid=meta.decode().split();result[path.decode()]=(mode,kind,oid)
 return result
owner=Path('/workspace/engineering/root-pr308-public-home-mode-patch-ordinary-a54-adoption/OWNERFINAL-root-exact-public-home-mode-patch-and-ordinary-a54-adoption.json')
assert sha(owner.read_bytes())=='012e6f45673c20650e0fcb06e99052534117714d7b48f0e0b395501c73880cc4'
assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[HEAD,'84f850f0d4e08b21afcd8220413ce94322370acf']
assert git('show','-s','--format=%P',HEAD).decode().strip().split()==[SOURCE,TARGET]
assert git('show','-s','--format=%P',SOURCE).decode().strip()==ORIGINAL
assert not git('status','--porcelain')
base=git('merge-base',SOURCE,TARGET).decode().strip()
tb,ts,tt,th=map(tree,[base,SOURCE,TARGET,HEAD])
assert len(th)==1426
fixture='action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'
guide='docs/skills/repository-operations.md'
assert set(p for p in set(tree(ORIGINAL))|set(ts) if tree(ORIGINAL).get(p)!=ts.get(p))=={fixture,guide}
proposed=Path('/workspace/engineering/rcc-current-e4ff-cache-mode-private-v8-proposal/proposed_test_source_staging_rcc_consumer_v2.py').read_bytes()
assert git('show',SOURCE+':'+fixture)==proposed and git('show',HEAD+':'+fixture)==proposed
combined=[];ordinary=0
for path in set(tb)|set(ts)|set(tt)|set(th):
 b,s,t,h=[x.get(path) for x in [tb,ts,tt,th]]
 if s==t:expected=s
 elif s==b:expected=t
 elif t==b:expected=s
 else:combined.append(path);continue
 assert h==expected;ordinary+=1
assert set(combined)=={'.github/workflows/_gen_workflows.py',guide}
def flattened(text):
 out={}
 def visit(body,prefix=''):
  for i,node in enumerate(body):
   if isinstance(node,ast.ClassDef):
    header=copy.deepcopy(node);header.body=[];out[prefix+node.name+'.CLASS']=ast.dump(header,include_attributes=False)
    visit(node.body,prefix+node.name+'.')
   else:
    key=node.name if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) else 'NODE'+str(i)
    out[prefix+key]=ast.dump(node,include_attributes=False)
 visit(ast.parse(text).body);return out
gen='.github/workflows/_gen_workflows.py'
db,ds,dt,dh=[flattened(git('show',c+':'+gen))for c in [base,SOURCE,TARGET,HEAD]]
cs={k for k in set(db)|set(ds)if db.get(k)!=ds.get(k)}
ct={k for k in set(db)|set(dt)if db.get(k)!=dt.get(k)}
assert not cs&ct
expected=dict(db)
for delta,data in [(cs,ds),(ct,dt)]:
 for key in delta:
  if key in data:expected[key]=data[key]
  else:expected.pop(key)
assert expected==dh
guides=[git('show',c+':'+guide).decode()for c in [base,SOURCE,TARGET,HEAD]]
chunks={}
for label,text in zip(['SOURCE','TARGET'],guides[1:3]):
 changes=[''.join(text.splitlines(True)[j1:j2]) for op,i1,i2,j1,j2 in difflib.SequenceMatcher(None,guides[0].splitlines(True),text.splitlines(True),autojunk=False).get_opcodes()if op in ('insert','replace')]
 assert all(chunk in guides[3]for chunk in changes);chunks[label]=len(changes)
assert chunks=={'SOURCE':6,'TARGET':3}
nativecfg=Path('/workspace/engineering/pr305-current5306-SOURCEFULL-preexecution-executable-v4/frozen-current-source-full-inputs.json')
nc=json.loads(Path(json.loads(nativecfg.read_bytes())['original_native_config']).read_bytes());nr=Path(nc['native_original_root'])
assert len(nc['native_original_members'])==1192
assert {p.relative_to(nr).as_posix()for p in nr.rglob('*')}=={p['path']for p in nc['native_original_members']}
for row in nc['native_original_members']:
 p=nr/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert not p.is_symlink()and sha(p.read_bytes())==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir()and not p.is_symlink()
 else:assert os.readlink(p)==row['link_target']
inventory=[]
cat=subprocess.Popen(['git','-C',str(ROOT),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,env=ENV)
for path,(mode,kind,oid)in sorted(th.items()):
 assert kind=='blob';cat.stdin.write((oid+'\n').encode());cat.stdin.flush();header=cat.stdout.readline().decode().split();size=int(header[2]);body=cat.stdout.read(size);assert cat.stdout.read(1)==b'\n'
 p=ROOT/path;fs=os.readlink(p).encode()if mode=='120000'else p.read_bytes();assert fs==body
 if mode!='120000':assert bool(p.lstat().st_mode&0o111)==(mode=='100755')
 inventory.append(dict(path=path,mode=mode,blob=oid,bytes=size,sha256=sha(body),fs_mode=stat.S_IMODE(p.lstat().st_mode)))
cat.stdin.close();assert cat.wait()==0
assert not git('status','--porcelain')
q=OUT/'private-current3969-complete-source-Git-FS-body-mode-inventory.json'
with q.open('x')as f:json.dump(inventory,f,indent=2,sort_keys=True);f.write('\n')
q.chmod(0o600)
result={'status':'PASS_CURRENT3969_TYPED_SOURCE_PATCH_AND_ORDINARY_UNION_ONLY_GATES_PENDING','source':HEAD,'tree':'84f850f0d4e08b21afcd8220413ce94322370acf','parents':[SOURCE,TARGET],'common_base':base,'root_owner':bind(owner),'complete_Git_FS_body_modes':1426,'ordinary_parent_choice_paths':ordinary,'combined_paths':combined,'generator_AST_source_changed_keys':sorted(cs),'generator_AST_target_changed_keys':sorted(ct),'generator_whole_AST_disjoint_union_exact':True,'all_guide_parent_changed_blocks_preserved':chunks,'patch2058_only_two_paths':True,'patched_fixture_entire_bytes_exact_accepted_proposal':True,'default_and_original_AST_preservation':'Bound previousindependentPUBLIC761b review; wholefixtureexactacceptedproposal.','native_original1192_body_modes_member_set_exact':True,'private_inventory':bind(q),'LIGHT_SOURCEFULL_current_native_CI':'PENDING_OWNER_FROZEN_QUALIFICATION_NO_CARRY','execution_imports_tests_gate_mutations':False}
q=OUT/'independent-current3969-source-union-proof.json'
with q.open('x')as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
q.chmod(0o600);print(json.dumps(bind(q)))
