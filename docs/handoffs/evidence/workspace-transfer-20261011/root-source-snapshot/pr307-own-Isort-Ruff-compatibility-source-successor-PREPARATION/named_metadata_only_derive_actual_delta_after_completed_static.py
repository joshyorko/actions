import ast,hashlib,json,os,stat,subprocess
from pathlib import Path
R=Path('/workspace/engineering/pr307');D=R/'devutils';F=Path(__file__).resolve().parent;OLD=Path('/workspace/engineering/pr307-four-leaf-own-Isort-child-SOURCE-PREPARATION')
def row(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def put(n,v):
 p=F/n
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
put('original-post-static-guessed-five-modified-paths-inspector-FAIL.json',{'schema':1,'status':'METADATA_INSPECTOR_FAIL_NOT_GATE_RETRY','original_script':row(F/'run_owned_config_and_four_leaves_then_complete_static_checks.py'),'failed_assertion':'Expected all originalfour formattertargets plus config to remain novel5pathdelta; final fixtures.py instead converged exact00b1 original, so actualdiff4paths. Original complete static0 results unchanged.','original_failure':'AssertionError at line47 after every configured static check returned0; no tests/gateway/full','correction':'Derive actualmodifiedset while preserving alloriginal4scope/nonimportbindings; no gates rerun.'})
old=json.loads((OLD/'original-source-and-tool-settings-before-format.json').read_text());allowed={'devutils/pyproject.toml'}|{r['path'].removeprefix(str(R)+'/') for r in old['four_leaves']};changed=set(git('diff','--name-only').decode().splitlines());assert changed<=allowed and 'devutils/pyproject.toml' in changed
proof=[]
for r in old['all_source_rows']:
 p=R/r['path'];s=p.lstat();b=os.readlink(p).encode() if r['mode']=='120000' else p.read_bytes();assert bool(s.st_mode&0o111)==(r['mode']=='100755') if r['mode']!='120000' else stat.S_ISLNK(s.st_mode)
 if r['path'] not in changed:assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['path']
 proof.append({**r,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
assert len(proof)==1442 and len(changed)==4
for n in ['own-Isort-resolved-settings','own-Isort-original-four-format','complete-Devutils-own-Ruff-CHECK','complete-Devutils-own-Ruff-format-CHECK','complete-Devutils-own-Isort-CHECK']:assert json.loads((F/(n+'.original-terminal.json')).read_text())['returncode']==0
settings=json.loads((F/'own-Isort-resolved-settings.stdout.private').read_text());assert settings['profile']=='' and settings['line_length']==88 and settings['multi_line_output']=='VERTICAL_HANGING_INDENT' and settings['include_trailing_comma'] and settings['use_parentheses']
append=json.loads((F/'exact-owning-Isort-config-append.json').read_text());assert (D/'pyproject.toml').read_bytes()==(F/'original-owning-Devutils-pyproject.toml').read_bytes()+append['exact_append'].encode()
# Prior script completed all four AST comparisons and wrote final snapshots before its derived-path-count assertion.
script=ast.parse((F/'run_owned_config_and_four_leaves_then_complete_static_checks.py').read_text());fn=next(n for n in script.body if isinstance(n,ast.FunctionDef) and n.name=='structure');ns={'ast':ast};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<owned AST-only structure>', 'exec'),ns)
for p in old['four_leaves']:
 rel=p['path'].removeprefix(str(R)+'/');a=(OLD/('original-'+Path(rel).name)).read_bytes();b=(R/rel).read_bytes();assert ns['structure'](a)==ns['structure'](b)
git('diff','--check')
owner=put('OWNER-precommit-named-derived-four-path-owning-settings-static-PASS.json',{'schema':1,'status':'SOURCE_SETTINGS_AND_IMPORT_FORMAT_STATIC_PASS_NO_GATE_TESTS','parent':'00b1bb9974b73f2da65e49c9048774c84df286ba','modified_paths':sorted(changed),'formatter_targets':list(old['four_leaves']),'unchanged_formatted_fixture':'devutils/src/devutils/fixtures.py EXACT parentbytes; no novelpatch retained','all_other_body_modes_exact':1442-len(changed),'all_source_rows':proof,'original_once3_and_conflict':row(OLD/'OWNERFINAL-original-four-leaf-Isort-format-and-owning-Ruff-conflict-HOLD.json'),'actual_static_checks':{n:row(F/(n+'.original-terminal.json')) for n in ['complete-Devutils-own-Ruff-CHECK','complete-Devutils-own-Ruff-format-CHECK','complete-Devutils-own-Isort-CHECK']},'settings_exact':row(F/'own-Isort-resolved-settings.stdout.private'),'non_import_AST_and_import_bindings':'EXACT all4formattertargets per AST block','config_only':'Originalownpyproject plus exact4 Isortsettings; no Runtime profile/lock/dependency/gate changes','metadata_fail':row(F/'original-post-static-guessed-five-modified-paths-inspector-FAIL.json'),'once4_full_native_authority':'NOT_RUN_HOLD','upstream_disposition':'none'})
print(json.dumps(owner))
