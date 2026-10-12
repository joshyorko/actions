import ast,copy,difflib,hashlib,json,os,stat,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
D=Path('/workspace/engineering/pr308-owned-package-cache-private-source');O=Path(__file__).parent;R=Path('/workspace/engineering/pr308');SOURCE='b614864ba9da55c13662894b6ef3c8515d9fdb25';TREE='6fa4f5c1e9837a0d893868255575b355b3977fae'
def bind(p):
 p=Path(p);h=hashlib.sha256()
 with p.open('rb') as f:
  for z in iter(lambda:f.read(1024*1024),b''):h.update(z)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest(),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*args],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
def dump(n):return ast.dump(n,include_attributes=False)
ownerpath=D/'OWNERFINAL-private-current-b614-owned-package-cache-two-path-source-patch.json';owner=json.loads(ownerpath.read_text());assert bind(ownerpath)['bytes']==19191 and bind(ownerpath)['sha256']=='10a7fe7e20545a0f5947e330cee87c21a88ab06cf2ef57eae610cad10186d8a2'
assert len(owner['references'])==51
for row in owner['references']:assert bind(row['path'])==row,row['path']
assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[SOURCE,TREE] and git('status','--porcelain')==b''
index=owner['source']['checkout_index_before_and_after'];assert bind(index['path'])==index
inv=json.loads((D/'private-original-b614-complete-tracked-body-mode-inventory.json').read_text());assert len(inv)==1421
actual={}
for rec in git('ls-tree','-r','-z','HEAD').split(b'\0'):
 if not rec:continue
 meta,p=rec.split(b'\t');mode,kind,oid=meta.decode().split();actual[os.fsdecode(p)]=(mode,oid)
assert len(actual)==1421
for row in inv:
 name=row['path'];p=R/name;mode,oid=actual[name];assert mode==row['git_mode'] and oid==row['git_blob']
 z=os.fsencode(os.readlink(p)) if mode=='120000' else p.read_bytes()
 assert len(z)==row['bytes'] and hashlib.sha256(z).hexdigest()==row['body_sha256'] and git('cat-file','blob',oid)==z
 assert mode=='120000' or bool(p.stat().st_mode&0o111)==(mode=='100755')
# Reproduce the exact two-file patch in memory, without application.
patch=b''
paths=[('test_source_staging_rcc_consumer.py','action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'),('repository-operations.md','docs/skills/repository-operations.md')]
for local,path in paths:
 old=(D/('original-'+local)).read_bytes();assert old==git('show',SOURCE+':'+path)
 new=(D/local).read_bytes();patch+=''.join(difflib.unified_diff(old.decode().splitlines(keepends=True),new.decode().splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path)).encode()
assert patch==(D/'owned-package-cache-two-path.patch').read_bytes() and hashlib.sha256(patch).hexdigest()=='aa2b0b1d008a717915764a4ddc97b8a60386b10afe63824ef23b4b487e2ece21'
old=ast.parse((D/'original-test_source_staging_rcc_consumer.py').read_bytes());new=ast.parse((D/'test_source_staging_rcc_consumer.py').read_bytes())
od={n.name:n for n in old.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};nd={n.name:n for n in new.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};selected={'test_published_artifact_details_preserves_one_rcc_identity_pair','test_staged_package_executes_in_managed_rcc_runtime'};removed=[]
for name,node in od.items():
 n=copy.deepcopy(nd[name]);kept=[]
 for child in n.body:
  if name in selected and isinstance(child,ast.If) and 'ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG' in ast.unparse(child.test):
   assert ast.unparse(child.test)=="os.environ.get('ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG') is not None" and not child.orelse
   expected="_prepare_owned_rcc_test_package_cache(tmp_path, rcc_version, rcc_sha256"+(", managed_home=managed_home)" if name.startswith('test_staged') else ")")
   assert len(child.body)==1 and dump(child.body[0])==dump(ast.parse(expected).body[0]);removed.append(name)
  else:kept.append(child)
 n.body=kept;assert dump(n)==dump(node),name
assert len(removed)==2 and set(removed)==selected
assert [dump(n) for n in old.body if not isinstance(n,(ast.FunctionDef,ast.ClassDef))]==[dump(n) for n in new.body if not isinstance(n,(ast.FunctionDef,ast.ClassDef))]
helper=nd['_prepare_owned_rcc_test_package_cache'];text=ast.unparse(helper)
# All guard predicates precede the sole symlink_to side effect; cases forward no other cache alias.
mounts=[n for n in ast.walk(helper) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='symlink_to'];assert len(mounts)==1
assert ast.unparse(mounts[0])=='link.symlink_to(cache, target_is_directory=True)'
required=['PACKAGE_CACHE_CONFIG_KEYS','PACKAGE_CACHE_SCHEMA','PACKAGE_CACHE_APPROVED_BINARY','PACKAGE_CACHE_SOURCE_BINDING','PACKAGE_CACHE_MARKER_SCHEMA','PACKAGE_CACHE_COLD_FIRST_PUBLICATION','PACKAGE_CACHE_PUBLICATION_SOURCE','PACKAGE_CACHE_PUBLICATION_BINARY','PACKAGE_CACHE_PUBLICATION_INVOCATION','PACKAGE_CACHE_EXISTING_MOUNT']
for name in required:assert name in text
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in {'setenv','rmtree','unlink','rename','symlink_to'} for n in ast.walk(helper) if n not in mounts)
helper_code=ast.unparse(helper);assert 'holotree' not in helper_code and 'provider' not in helper_code
# Fixture call positions: admitted binary before cold-cache check, and mount before only staged env switch.
publication=nd['test_published_artifact_details_preserves_one_rcc_identity_pair'];stage=nd['test_staged_package_executes_in_managed_rcc_runtime'];pub_code=ast.unparse(publication);stage_code=ast.unparse(stage)
assert pub_code.index('_verify_selected_rcc_fixture')<pub_code.index('_prepare_owned_rcc_test_package_cache')<pub_code.index('start_provider(')<pub_code.index('publish_artifact_details(')
assert stage_code.index('_verify_selected_rcc_fixture')<stage_code.index('_prepare_owned_rcc_test_package_cache')<stage_code.index("monkeypatch.setenv('ACTIONS_HOME'")
# Derive exact permanent case counts, then validate the original recorded results independently.
permanent=[n for n in new.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_owned_rcc_package_cache')];assert len(permanent)==5
for n in permanent:assert all('integration' not in ast.unparse(d) and 'real_rcc' not in ast.unparse(d) for d in n.decorator_list)
poisons=nd['test_owned_rcc_package_cache_rejects_poison_before_mount'];decor=next(x for x in poisons.decorator_list if isinstance(x,ast.Call));poison_names=ast.literal_eval(decor.args[1]);assert len(poison_names)==29 and len(set(poison_names))==29
assert 'assert calls == []' in ast.unparse(poisons)
positive=ast.unparse(nd['test_owned_rcc_package_cache_preserves_cold_first_and_shared_download_only']);assert "assert calls == [(managed / 'pkgs', (shared,), {'target_is_directory': True})]" in positive
counts=1+len(poison_names)+1+2+1;assert counts==34
censuses={}
for name in ['RED-v2-junit.xml','marker-scalar-RED-junit.xml','final-v3-private-GREEN-junit.xml']:
 root=ET.parse(D/name).getroot();cases=list(root.iter('testcase'));fail=[n.find('failure') for n in cases if n.find('failure') is not None];censuses[name]={'cases':len(cases),'pass':sum(n.find('failure') is None and n.find('error') is None and n.find('skipped') is None for n in cases),'fail':len(fail),'error':len(list(root.iter('error'))),'skip':len(list(root.iter('skipped'))),'DID_NOT_RAISE':sum('DID NOT RAISE' in f.get('message','') for f in fail),'FileExistsError':sum('FileExistsError' in f.get('message','') for f in fail)}
assert censuses['RED-v2-junit.xml']=={'cases':31,'pass':1,'fail':30,'error':0,'skip':0,'DID_NOT_RAISE':29,'FileExistsError':1}
assert censuses['marker-scalar-RED-junit.xml']=={'cases':34,'pass':32,'fail':2,'error':0,'skip':0,'DID_NOT_RAISE':2,'FileExistsError':0}
assert censuses['final-v3-private-GREEN-junit.xml']=={'cases':34,'pass':34,'fail':0,'error':0,'skip':0,'DID_NOT_RAISE':0,'FileExistsError':0}
assert json.loads((D/'final-v3-static-terminal.json').read_text())['returncode']==0
log=(D/'final-v3-configured-private-static-and-controls.private.log').read_text();assert '34 passed, 16 deselected, 2 warnings' in log and 'Success: no issues found in 1 source file' in log and 'ruff check' in log and 'isort' in log
check=subprocess.run(['git','--no-optional-locks','-C',str(R),'apply','--check',str(D/'owned-package-cache-two-path.patch')],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False);assert check.returncode==0
assert bind(index['path'])==index and git('status','--porcelain')==b''
for row in owner['references']:assert bind(row['path'])==row
out={'status':'PASS_INDEPENDENT_PRIVATE_PATCH_SOURCE_AND_RECORDED_CONTROLS_NO_TEST_EXECUTION','source':owner['source'],'all51references_bytes_modes_exact':True,'all1421Git_FS_body_exec_exact':True,'two_file_patch_reproduced_in_memory_exact':bind(D/'owned-package-cache-two-path.patch'),'old13functions_AST_default_exact':len(od),'old_module_nonfunction_AST_exact':True,'only_two_guarded_fixture_calls':sorted(removed),'permanent_case_count_derived':counts,'poison_names':poison_names,'original_XML_censuses':censuses,'recorded_static_returncode':0,'read_only_git_apply_check':check.returncode,'publication_onepublish_and_staged_percase_home_provider_and_origin_AST_unchanged':True,'guard_contract':'Bound fixed approved measured binary/version and current environment Git source, root/marker ownership+modes+containment; cold first; matching publicationPASS before sole staged pkgs link; no global/cache/holotree/provider alias','limits':['Source-only patch not applied; composition with separately reviewed persistent fixture patch needs new exact source review/full/runner','No native binary, provider, tests or product imports executed by reviewer','Peak/storage reduction and RCC symlink support prospective, not proved by Linux synthetic controls','Current source/controls do not upgrade original failed control3 or not-run5/7276'],'canonical_delta':'Exact11line proposed cache/cold-scope paragraph accepted for root integration; no whole cold-install or actualpeak claim','upstream_disposition':'none'}
p=O/'independent-private-patch-source-and-control-proof.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');p.chmod(0o444);print(json.dumps(bind(p)))
