from pathlib import Path
import ast,hashlib,json,subprocess,zipfile
B=Path('/workspace/engineering/pr221-current618-linux-consumer-preflight');R=Path('/workspace/engineering/pr282');D=B/'linux-platform-input-v5'
def bind(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
fail=B/'OWNERFINAL-original-current618-consumer-gateway-failure.json';assert bind(fail)['sha256']=='6f29ccd4b905b0036e6347aac23c12bda82cb6a719a1e7da0008eec951c0e773'
v4=B/'immutable-current618-linux-consumer-preexecution-proposal-v4.json';v=json.loads(v4.read_text());assert bind(v4)['sha256']=='da926a733e60108fd2943add0a60a0bf6d365afbb1d489bf986a0624ecda65c0'
refs={}
for p in B.rglob('*'):
 if p.is_file() and '__pycache__' not in p.parts:refs[str(p)]=bind(p)
for row in v['all_private_preexecution_files_and_preserved_originals']:
 assert bind(row['path'])==row;refs[row['path']]=row
for p in Path('/workspace/engineering/pr221-current618-linux-consumer-independent-preexecution-review').glob('*.json'):refs[str(p)]=bind(p)
for row in json.loads(fail.read_text()).values():
 if isinstance(row,dict) and {'path','bytes','sha256'} <= set(row):assert bind(row['path'])==row;refs[row['path']]=row
assert not Path(json.loads(fail.read_text())['attempt_namespace']).exists()
assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
rows=[]
for z in subprocess.check_output(['git','-C',str(R),'ls-tree','-rz','HEAD']).split(b'\0'):
 if not z:continue
 m,p=z.split(b'\t');mode,kind,blob=m.decode().split();p=p.decode();b=(R/p).read_bytes();assert b==subprocess.check_output(['git','-C',str(R),'show','HEAD:'+p]);assert bool((R/p).stat().st_mode&0o111)==(mode=='100755');rows.append({'path':p,'mode':mode,'blob':blob,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
assert len(rows)==1433
(B/'v5-original-ref-and-harness-before-preparation-proof.json').write_text(json.dumps({'all_existing_original_refs':sorted(refs.values(),key=lambda x:x['path']),'harness_head':subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD']).decode().strip(),'all1433_harness_typed_bodies_execbits':rows,'original_gateway_failure_worker_never_began':True},indent=2)+'\n')
m=json.loads((B/'input-and-source-admission-v4.json').read_text());archive=Path(m['original_archive']['path_private']);assert bind(archive)['sha256']=='fc4018e6e7ed4a0e47c4f5888d36d55655216ca22ebd965f29ce9f1130938f8c';D.mkdir(mode=0o700,exist_ok=False);copies=[]
with zipfile.ZipFile(archive) as z:
 assert len(z.infolist())==2
 for row in m['outer_inventory']:
  p=archive.parent/row['path'];data=p.read_bytes();assert data==z.read(row['path']) and len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'];q=D/p.name;q.write_bytes(data);q.chmod(0o600);copies.append({'original':bind(p),'dedicated_copy':bind(q),'copy_mode':'0600','original_ZIP_member':row['path'],'original_ZIP_bytes_equal':True})
old=m['original_selected_wheel']['private_path'];new=str(D/Path(old).name);m['original_selected_wheel']['private_path']=new
mp=B/'input-and-source-admission-v5.json';assert not mp.exists();mp.write_text(json.dumps(m,indent=2)+'\n');mp.chmod(0o600)
p=B/'installed-consumer-runner-v5.py';assert not p.exists();s=(B/'installed-consumer-runner-v4.py').read_text();s=s.replace(old,new).replace('installed-linux-current618-90a785d8-2','installed-linux-current618-90a785d8-3').replace('input-and-source-admission-v4.json','input-and-source-admission-v5.json').replace(v['input_manifest']['sha256'],bind(mp)['sha256']);p.write_text(s);p.chmod(0o600)
a=lambda text:{n.name:ast.dump(n) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};assert len(a(s))==9 and a(s)==a((B/'installed-consumer-runner-v4.py').read_text())
for src,dst,replaces in [('test_current_input_admission_v4.py','test_current_input_admission_v5.py',{'input-and-source-admission-v4.json':'input-and-source-admission-v5.json'}),('test_installed_consumer_runner_v4.py','test_installed_consumer_runner_v5.py',{'installed-consumer-runner-v4.py':'installed-consumer-runner-v5.py'}),('test_current_input_provenance_v4.py','test_current_input_provenance_v5.py',{'input-and-source-admission-v4.json':'input-and-source-admission-v5.json'})]:
 s=(B/src).read_text()
 for k,x in replaces.items():s=s.replace(k,x)
 q=B/dst;assert not q.exists();q.write_text(s);q.chmod(0o600)
(B/'isolated-original-Linux-pair-v5-copies-and-runner-scope.json').write_text(json.dumps({'copies':copies,'original_archive':bind(archive),'immutable_v4':bind(v4),'new_manifest':bind(mp),'new_runner':bind(p),'all9_runner_function_ASTs_exact_v4':True,'only_runner_parameter_deltas':['WHEEL dedicated Linux path','ATTEMPT suffix3','SOURCES input_manifest path and SHA'],'all_other_globals_and_budgets_unchanged':True,'actual_consumer_executed':False},indent=2)+'\n')
print('Prepared exact original Linux pair0700/0600; v5 parameter-only runner,9function ASTs unchanged; originals retained')
