import ast,datetime,hashlib,json,os,stat,subprocess
from pathlib import Path
B=Path('/workspace/engineering/pr308-known-nine-18-semantic-concrete-preexecution-NOTRUN')

def row(p):
 p=Path(p);st=p.lstat();assert stat.S_ISREG(st.st_mode) and not p.is_symlink();raw=p.read_bytes()
 return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mode':oct(stat.S_IMODE(st.st_mode))}
def put(name,data):
 p=B/name
 with p.open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
cf=row(B/'FROZEN-known-nine-18-semantic-15s-config-v2-NOTRUN.json');c=json.loads(Path(cf['path']).read_text());lf=row(B/'run_known_nine_18_semantic_once_NOTRUN.py')
assert cf['sha256']=='b9010e2996df0285971f2c7ce31c4da04a6e7672505aa4240cb2b049aaae823d'
for r in c['original_bindings']:assert row(r['path'])==r
plan=json.loads(Path(c['plan_binding']['path']).read_text())
# Locate original phases by the explicit label/kind identity, independent of plan nesting.
def all_dicts(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from all_dicts(v)
 elif isinstance(x,list):
  for v in x:yield from all_dicts(v)
originals=[x for x in all_dicts(plan) if 'argv' in x and 'predicate' in x and 'kind' in x]
assert len(originals)==18
source=Path(c['test_source']['path']);assert row(source)==c['test_source'];body=source.read_text();tree=ast.parse(body);lines=body.splitlines()
for i,p in enumerate(c['phases']):
 o=next(x for x in originals if x['label']==p['label'] and x['kind']==p['kind'])
 argv=o['argv'].copy();assert argv.count('120s')==1;argv[argv.index('120s')]='15s';assert p['argv']==argv
 for k in set(o)&set(p)-{'argv','parent_seconds'}:assert o[k]==p[k],k
 assert p['parent_seconds']==30 and p['kind']==('RED' if i%2==0 else 'RESTORED_GREEN')
 assert p['test']==c['case_order'][i//2]
 assert p['predicate']['assertion_source']==lines[p['predicate']['source_line']-1].strip()
 funcs=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.lineno<=p['predicate']['source_line']<=n.end_lineno]
 assert min(funcs,key=lambda n:n.end_lineno-n.lineno).name==p['predicate']['source_function']
 assert any(isinstance(n,ast.Assert) and n.lineno==p['predicate']['source_line'] for n in ast.walk(tree))
 assert p['argv'].count(str(source)+'::'+p['test'])==1
 assert ('RCC_RELOAD_PRIVATE_MUTANT='+p['label'] in p['argv'])==(p['kind']=='RED')
 assert Path(p['output_parent']).parent==Path(c['root_once'])
 assert not Path(p['output_parent']).exists() and not Path(p['output_parent']).is_symlink()
assert len(set(p['output_parent'] for p in c['phases']))==18
assert len(c['activation'])==18 and len(c['path_prefix2'])==2 and len(c['origins'])==5
assert 18*30+2*135+5*30==960 and c['outer_seconds']==1200 and c['root_parent_seconds']==1230
ast.parse(Path(lf['path']).read_text())
# Complete current source Git and physical body/mode verification; no product imports.
guardcfg=next(r for r in c['original_bindings'] if r['sha256']=='5dc48075c8a2c91042f38a4c4c8941e9eb7f5c0feb82dcc93917cb8ec76c9f25')
g=json.loads(Path(guardcfg['path']).read_text());root=Path(g['source_root'])
def git(*args):return subprocess.check_output(['git','-C',str(root),*args])
assert git('rev-parse','HEAD').decode().strip()==c['source']
assert git('rev-parse','HEAD^{tree}').decode().strip()==c['tree']
assert not git('status','--porcelain','--untracked-files=no')
entries={}
for x in git('ls-tree','-rz','HEAD').split(b'\0'):
 if x:
  m,k,o=x.split(b'\t',1)[0].decode().split();p=x.split(b'\t',1)[1].decode();entries[p]=(m,k,o)
assert len(entries)==len(g['source_body_modes'])==1440
assert set(entries)=={r['path'] for r in g['source_body_modes']}
for r in g['source_body_modes']:
 assert entries[r['path']]==(r['mode'],'blob',r['object'])
 p=root/r['path'];s=p.lstat();assert stat.S_IMODE(s.st_mode)==r['fs_mode']
 raw=os.readlink(p).encode() if stat.S_ISLNK(s.st_mode) else p.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==r['sha256']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==r['object']
assert not Path(c['root_once']).exists() and not Path(c['root_once']).is_symlink()
assert not Path(c['root_release_path']).exists() and not Path(c['root_release_path']).is_symlink()
canonical=Path('/workspace/engineering/pr308-nine-real-private-catalog-lock-source-successor-final-v4-NOTRUN/canonical-reload-control-copy-and-lock-boundaries-proposed.patch')
assert row(canonical)['sha256']=='5584b00182d7504808065195f3373f80eb450fa5370811d434d66ad0c5b9a7d5'
proof=put('immutable-static-current-source-phase-map-and-closure-proof.json',{'schema':1,'status':'STATIC_PREPARATION_ONLY_PASS_NOT_EXECUTED','source':c['source'],'tree':c['tree'],'source_leaves':1440,'source_clean':True,'all_original_bindings':len(c['original_bindings']),'phases':18,'test_names':9,'exact_original_argv_delta':'120s -> 15s; parent30; all other phase fields exact','full_source_function_line_assertion_map':'PASS','launcher_ast_parse':'PASS_NO_IMPORT_EXECUTION','fallback_sum_seconds':960,'outer_seconds':1200,'root_parent_seconds':1230,'config_binding':cf,'launcher_binding':lf,'baseline_dependency':c['baseline_dependency'],'canonical_5584_reuse':row(canonical),'actual_controls':'NOT_RUN','native':'NOT_RUN','snapshot_oracle_sensitivity':'NOT_RUN_SEPARATE_GATE','capture':datetime.datetime.now(datetime.timezone.utc).isoformat()})
release={'schema':1,'scope':c['required_release_scope'],'source':c['source'],'tree':c['tree'],'config_binding':cf,'launcher_binding':lf,'baseline_dependency':c['baseline_dependency'],'serialized_no_other_heavy_or_storage_mutations':True,'independent_review':None}
contract=put('concrete-ROOT-distinct-release-command-and-independent-review-contract-NOTRUN.json',{'schema':1,'status':'UNEXECUTABLE_TEMPLATE_REQUIRES_DISTINCT_REAL_INDEPENDENT_REVIEW_AND_ROOT_RELEASE','source':c['source'],'tree':c['tree'],'config_binding':cf,'launcher_binding':lf,'root_release_path':c['root_release_path'],'root_release_required_physical':'regular nonsymlink 0600 UID/GID1000; exact path; fsynced SHA-bound ROOT file','unexecutable_root_release_template':release,'compatible_independent_review_required':{'schema':1,'status':c['required_review_status'],'source':c['source'],'tree':c['tree'],'config_sha256':cf['sha256'],'launcher_sha256':lf['sha256']},'root_argv':['env','-u','PYTHONOPTIMIZE','-u','PYTEST_ADDOPTS','-u','RCC_RELOAD_PRIVATE_MUTANT','timeout','--signal=TERM','--kill-after=10s','1200s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',lf['path'],'--release',c['root_release_path'],'--release-sha256','ROOT_REAL_DISTINCT_RELEASE_SHA256'],'root_parent_seconds':1230,'expected_activation18':c['activation'],'expected_PATH_prefix2':c['path_prefix2'],'guards':'readonly original V9 before + five concrete own origin probes + always post; no native main or capacity floor','phase_admission':'exact rc/JUnit/known full source assertion frame; fresh unmutated GREEN follows each RED; wrong failure stops; no retry','output_root_must_be_absent':c['root_once'],'all18_fresh_phase_output_parents':[p['output_parent'] for p in c['phases']],'phase_times':'15 TERM10; parent30','source_adoption':'NONE','tests':'NOT_RUN'})
refs=[row(p) for p in sorted(B.iterdir()) if p.is_file()]
owner=put('OWNERFINAL-known-nine-18-semantic-concrete-15s-RED-fresh-GREEN-PREEXEC-NOTRUN.json',{'schema':1,'status':'PREPARED_KNOWN9_18_SEMANTIC_SOURCE_CONTROL_PREEXECUTION_NOT_RUN','source':c['source'],'tree':c['tree'],'source_leaves':1440,'source_clean':True,'config_binding':cf,'launcher_binding':lf,'ROOT_contract':contract,'static_proof':proof,'baseline_actual_prerequisite':c['baseline_dependency'],'phase_count':18,'RED_known_case_count':9,'fresh_unmutated_GREEN_case_count':9,'all_refs':refs,'original_plan_120s_and_3600':'UNCHANGED','initial_metadata_count_inspector_failure':row(B/'OWNERFINAL-original-count-schema-inspector-FAIL-NOTRUN.json'),'original_unadopted_launcher_draft':row(B/'original-unadopted-launcher-draft-before-static-hardening.py'),'actual_tests':'NOT_RUN','native':'NOT_RUN','snapshot_oracle_sensitivity':'NOT_RUN_SEPARATE_REQUIRED','ROOT_release':'NOT_CREATED','actual_output_root':'ABSENT','scope':'SOURCE semantic mutant discrimination only; no native generation/drain/provider/backend/reaping/private/release qualification or product adoption','documentation':{'disposition':'REUSE_ACCEPTED_5584_COPY_LOCK_BOUNDARY_AND_KNOWN_SEMANTIC_ASSERTION_PLAN','exact_delta_binding':row(canonical),'evidence':'real accepted e54 nine baseline; immutable a577 source; exact nine function/line/assertion mapping; failclosed wrong assertion/timeouts; source/body/mode unchanged','remaining_uncertainty':'all18 semantic phases unexecuted; snapshot oracle sensitivity unexecuted; actual assertion logs/JUnits require independent original-outcome review'},'upstream_disposition':'none'})
for r in refs:assert row(r['path'])==r
print(json.dumps(owner))
