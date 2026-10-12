import ast,collections,datetime,hashlib,json,os,stat,subprocess,time
from pathlib import Path
R=Path('/workspace/engineering/pr307');F=Path(__file__).resolve().parent;D=R/'devutils'
PARENT='00b1bb9974b73f2da65e49c9048774c84df286ba'
DIAG=Path('/workspace/engineering/pr307-current00b1-token-once3-ACTUALFAIL-independent-review/OWNERFINAL-independent-original-current00b1-token-once3-ACTUALFAIL-and-owning-Isort-four-leaf-proposal.json')
def row(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),mode=oct(stat.S_IMODE(s.st_mode)))
def put(n,v,mode=0o400):
 p=F/n
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 p.chmod(mode);return row(p)
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def exact(r):assert row(r['path'])==r
assert git('rev-parse','HEAD').decode().strip()==PARENT and not git('status','--porcelain')
assert row(DIAG)['sha256']=='a5d9de122535a9d7075a33f37b656e74b99206190db647e11aeb54856149a6e2'
v=json.loads(DIAG.read_text());leaves=v['minimal_authorized_source_proposal']['only_four_import_sort_leaves'];assert len(leaves)==4
refs=[row(DIAG)]+v['settings_provenance']['bindings'];[exact(r) for r in refs]
oldcfg=json.loads(Path('/workspace/engineering/pr307-current00b1-token-light-once3-PREEXECUTION-NOTRUN/immutable-one-TOKEN-LIGHT-once3-inputs.json').read_text());oldproof=json.loads(Path(oldcfg['source_proof']['path']).read_text())
for r in oldcfg['bindings']:exact(r)
original={}
for rel in leaves:
 p=R/rel;b=p.read_bytes();original[rel]=b;s=F/('original-'+p.name);s.write_bytes(b);s.chmod(0o400)
put('original-source-and-tool-settings-before-format.json',{'source':PARENT,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'all_source_rows':oldproof['all_git_FS_body_and_exec_mode_exact'],'four_leaves':[row(R/r) for r in leaves],'tools_and_settings':refs+[row(D/'.venv/bin/ruff')],'original_once3':row(DIAG)})
args=[str(Path(x).relative_to('devutils')) for x in leaves]
def run(name,argv):
 t=time.monotonic();a=F/(name+'.stdout.private');b=F/(name+'.stderr.private')
 with a.open('xb') as out,b.open('xb') as err:
  os.chmod(a,0o600);os.chmod(b,0o600);p=subprocess.run(argv,cwd=D,stdout=out,stderr=err,timeout=60,check=False);out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
 q=put(name+'.original-terminal.json',{'argv':argv,'cwd':str(D),'timeout_seconds':60,'returncode':p.returncode,'elapsed_seconds':time.monotonic()-t,'stdout':row(a),'stderr':row(b),'capture':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 assert p.returncode==0,(name,p.returncode,q);return q
results=[run('own-isort-version',[str(D/'.venv/bin/isort'),'--version-number']),run('own-isort-src-settings-show-config',[str(D/'.venv/bin/isort'),'--settings-path','src','--show-config',*args])]
results.append(run('exact-four-own-configured-isort-format',[str(D/'.venv/bin/isort'),'--settings-path','src',*args]))
# Non-import trees and imported bindings are compared by AST block identity, not import statement ordering.
def structure(b):
 t=ast.parse(b);imports={}
 def walk(value,path):
  if isinstance(value,list):
   out=[];n=0
   for item in value:
    if isinstance(item,(ast.Import,ast.ImportFrom)):
     key='/'.join(path);z=imports.setdefault(key,[])
     for alias in item.names:z.append((type(item).__name__,getattr(item,'module',None),getattr(item,'level',0),alias.name,alias.asname))
    else:out.append(walk(item,path+[str(n)]));n+=1
   return out
  if isinstance(value,ast.AST):return (type(value).__name__,[(k,walk(v,path+[k])) for k,v in ast.iter_fields(value)])
  return value
 non=walk(t,['module']);return non,{k:sorted(v,key=repr) for k,v in imports.items()}
proof=[]
for rel in leaves:
 a=structure(original[rel]);b=structure((R/rel).read_bytes());assert a==b,rel
 s=F/('formatted-'+Path(rel).name);s.write_bytes((R/rel).read_bytes());s.chmod(0o400)
 proof.append({'path':rel,'non_import_AST':'EXACT','per_AST_block_import_binding_multisets':'EXACT','imports':a[1],'original_snapshot':row(F/('original-'+Path(rel).name)),'formatted_snapshot':row(s)})
for r in oldproof['all_git_FS_body_and_exec_mode_exact']:
 p=R/r['path'];s=p.lstat();raw=os.readlink(p).encode() if r['mode']=='120000' else p.read_bytes();assert bool(s.st_mode&0o111)==(r['mode']=='100755') if r['mode']!='120000' else stat.S_ISLNK(s.st_mode)
 if r['path'] not in leaves:assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],r['path']
assert set(git('diff','--name-only').decode().splitlines())==set(leaves)
put('exact-four-import-scope-and-all-other1438-body-mode-proof.json',{'source_parent':PARENT,'source_count':1442,'only_four_leaves':leaves,'unchanged_other_body_mode_pairs':1438,'four_proofs':proof,'side_effect_order_limit':'Import ordering changes can affect third-party import side effects. Imported bindings per exact AST block and all non-import code are proven equal; universal import side-effect equivalence is not claimed. Changes are configured import normalization only.'})
results.append(run('four-own-Ruff-check',[str(D/'.venv/bin/ruff'),'check',*args]))
results.append(run('four-own-Ruff-format-CHECK',[str(D/'.venv/bin/ruff'),'format','--check','--config','ruff.toml',*args]))
results.append(run('four-own-Isort-CHECK',[str(D/'.venv/bin/isort'),'--settings-path','src','--check',*args]))
results.append(run('four-source-diff-check',['git','diff','--check']))
put('OWNER-precommit-exact-four-own-Isort-and-matched-Ruff-checks-PASS.json',{'schema':1,'status':'BOUNDED_FOUR_LEAF_FORMAT_AND_STATIC_CHECKS_PASS_NO_TESTS','parent':PARENT,'four_leaves':leaves,'original_once3_FAIL':row(DIAG),'actual_command_results':results,'sourceproof':row(F/'exact-four-import-scope-and-all-other1438-body-mode-proof.json'),'gate_scopes':'Only four leaf static checks, not full configured lint/test suite; once4/FULL/OAuth authority/native/release still NOT_RUN/HOLD','upstream_disposition':'none'})
print('Four-leaf import scope preservation and bounded Ruff/Isort checks PASS; no tests or gateway run.')
