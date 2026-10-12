import ast,hashlib,json,os,stat,subprocess,time
from pathlib import Path
R=Path('/workspace/engineering/pr307');D=R/'devutils';F=Path(__file__).resolve().parent;OLD=Path('/workspace/engineering/pr307-four-leaf-own-Isort-child-SOURCE-PREPARATION')
leaves=['src/devutils/fixtures.py','tests/test_http_helper_tests_workflow.py','tests/test_runtime_conformance.py','tests/test_invoke_utils.py']
def row(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def put(n,v):
 p=F/n
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
def run(name,argv):
 t=time.monotonic();a=F/(name+'.stdout.private');b=F/(name+'.stderr.private')
 with a.open('xb') as out,b.open('xb') as err:
  os.chmod(a,0o600);os.chmod(b,0o600);p=subprocess.run(argv,cwd=D,stdout=out,stderr=err,timeout=60,check=False);out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
 q=put(name+'.original-terminal.json',{'argv':argv,'cwd':str(D),'timeout_seconds':60,'returncode':p.returncode,'elapsed_seconds':time.monotonic()-t,'stdout':row(a),'stderr':row(b)});assert p.returncode==0,(name,p.returncode,q);return q
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD']).decode().strip()=='00b1bb9974b73f2da65e49c9048774c84df286ba'
results=[run('own-Isort-resolved-settings',[str(D/'.venv/bin/isort'),'--settings-path','src','--show-config',*leaves])]
results.append(run('own-Isort-original-four-format',[str(D/'.venv/bin/isort'),'--settings-path','src',*leaves]))
results.append(run('complete-Devutils-own-Ruff-CHECK',[str(D/'.venv/bin/ruff'),'check','src','tests']))
results.append(run('complete-Devutils-own-Ruff-format-CHECK',[str(D/'.venv/bin/ruff'),'format','--check','--config','ruff.toml','src','tests']))
results.append(run('complete-Devutils-own-Isort-CHECK',[str(D/'.venv/bin/isort'),'--check','src','tests']))
# Preserve non-import tree and import binding multiset in each exact AST block, ignoring only changed import order.
def structure(b):
 imports={}
 def walk(value,path):
  if isinstance(value,list):
   out=[];n=0
   for item in value:
    if isinstance(item,(ast.Import,ast.ImportFrom)):
     z=imports.setdefault('/'.join(path),[])
     for a in item.names:z.append((type(item).__name__,getattr(item,'module',None),getattr(item,'level',0),a.name,a.asname))
    else:out.append(walk(item,path+[str(n)]));n+=1
   return out
  if isinstance(value,ast.AST):return(type(value).__name__,[(k,walk(v,path+[k])) for k,v in ast.iter_fields(value)])
  return value
 non=walk(ast.parse(b),['module']);return non,{k:sorted(v,key=repr) for k,v in imports.items()}
proof=[]
for rel in leaves:
 a=(OLD/('original-'+Path(rel).name)).read_bytes();b=(D/rel).read_bytes();assert structure(a)==structure(b),rel
 p=F/('final-configured-'+Path(rel).name);p.write_bytes(b);p.chmod(0o400)
 proof.append({'path':'devutils/'+rel,'original_snapshot':row(OLD/('original-'+Path(rel).name)),'final_snapshot':row(p),'per_AST_block_import_binding_multisets':'EXACT','non_import_AST':'EXACT'})
old=json.loads((OLD/'original-source-and-tool-settings-before-format.json').read_text())
changed=set(['devutils/'+x for x in leaves]+['devutils/pyproject.toml']);unchanged=0
for r in old['all_source_rows']:
 p=R/r['path'];s=p.lstat();b=os.readlink(p).encode() if r['mode']=='120000' else p.read_bytes();assert bool(s.st_mode&0o111)==(r['mode']=='100755') if r['mode']!='120000' else stat.S_ISLNK(s.st_mode)
 if r['path'] not in changed:assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['path'];unchanged+=1
assert unchanged==1437 and set(subprocess.check_output(['git','-C',str(R),'diff','--name-only']).decode().splitlines())==changed
settings=json.loads((F/'own-Isort-resolved-settings.stdout.private').read_text());assert settings['line_length']==88 and str(settings['multi_line_output'])=='VERTICAL_HANGING_INDENT' and settings['include_trailing_comma'] is True and settings['use_parentheses'] is True and settings['profile']==''
append=json.loads((F/'exact-owning-Isort-config-append.json').read_text());assert (D/'pyproject.toml').read_bytes()==(F/'original-owning-Devutils-pyproject.toml').read_bytes()+append['exact_append'].encode()
results.append(run('exact-source-diff-check',['git','diff','--check']))
put('OWNER-precommit-owning-Isort-config-four-leaves-and-complete-static-PASS.json',{'schema':1,'status':'COMPLETE_DEVUTILS_STATIC_CHECKS_PASS_FORMAT_ONLY_NO_TESTS','parent':'00b1bb9974b73f2da65e49c9048774c84df286ba','source_count':1442,'original_four_leaf_scope':leaves,'only_additional_authorized_config_path':'devutils/pyproject.toml','unchanged_other_body_mode_pairs':1437,'configuration_delta':row(F/'exact-owning-Isort-config-append.json'),'original_fixture_gate_conflict':row(OLD/'OWNERFINAL-original-four-leaf-Isort-format-and-owning-Ruff-conflict-HOLD.json'),'proofs':proof,'resolved_settings':row(F/'own-Isort-resolved-settings.stdout.private'),'actual_static_results':results,'side_effect_order_limit':'Imported module/name/alias/relativelevel multisets per AST block and non-import code exact; arbitrary import side effects remain untested. No tests/native/import product/gateway/full/once4.','upstream_disposition':'none'})
print('Explicit Devutils-owned settings: all src/tests Ruff check, Ruff format CHECK and Isort CHECK PASS; only four formatted leaves plus config changed.')
