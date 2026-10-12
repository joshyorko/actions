import ast,copy,hashlib,json,os,re,stat,subprocess
from pathlib import Path
D=Path('/workspace/engineering/rcc-compatibility-transport-failure-metadata-v6-private-source')
R=Path('/workspace/engineering/rcc-compatibility-actual-runner-readonly-preparation')
OUT=Path('/workspace/engineering/rcc-transport-v6-independent-source-review')
def h(p):
 x=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):x.update(b)
 return x.hexdigest()
def bind(p):
 p=Path(p);return {'path':str(p),'sha256':h(p),'bytes':p.stat().st_size,'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def verify(row):
 obs=bind(row['path']);assert all(obs[k]==v for k,v in row.items() if k in obs),(row['path'],obs)
 return obs
def dump(n):return ast.dump(n,include_attributes=False)
def fn(tree,name):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
def namedassign(n,name):return isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)
def callstmt(n,name):return isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id==name
ownerpath=D/'OWNERFINAL-private-transport-v6-original-exception-and-observed-ownership-source.json'
owner=json.loads(ownerpath.read_bytes());assert bind(ownerpath)['sha256']=='aa052e89bf03bbfcd2009a5d962cad40086474d89d76956f2f206ea648e8a54d'
refs=[verify(row) for row in owner['bindings']];assert len(refs)==34
prior=json.loads((D/'before-v6-complete263-and-original-failure-bindings.json').read_bytes())
for row in prior['original263']+prior['original_failure']:verify(row)
assert len(prior['original263'])==263 and len(prior['original_failure'])==12
old=ast.parse((R/'actual_transport_v5.py').read_bytes());new=ast.parse((R/'actual_transport_v6.py').read_bytes())
original_new=copy.deepcopy(new)
allowedfuncs={'original_helper_facts','make_safe_result','require_transport_binding'}
new.body=[n for n in new.body if not (isinstance(n,ast.FunctionDef) and n.name in allowedfuncs) and not(isinstance(n,ast.Import) and len(n.names)==1 and n.names[0].name=='traceback')]
e=fn(new,'execute_one');assert [a.arg for a in e.args.kwonlyargs]==['retain_exception'];assert dump(e.args.kw_defaults[0])==dump(ast.Constant(None));e.args.kwonlyargs=[];e.args.kw_defaults=[]
e.body=[n for n in e.body if not(namedassign(n,'helper_facts') or namedassign(n,'exception_retention_failure'))]
t=next(n for n in e.body if isinstance(n,ast.Try)).body[0]
t.body=[n for n in t.body if not namedassign(n,'helper_facts')]
t.handlers[0].body=[n for n in t.handlers[0].body if not(namedassign(n,'helper_facts') or (isinstance(n,ast.If) and ast.unparse(n.test)=='retain_exception is not None'))]
ret=e.body[-1].value;pair=[(k,v) for k,v in zip(ret.keys,ret.values) if k.value not in ['original_helper_facts','secondary_exception_retention_failure_class']];ret.keys=[k for k,v in pair];ret.values=[v for k,v in pair]
m=fn(new,'main');om=fn(old,'main')
m.body=[n for n in m.body if not(namedassign(n,'observed_supervisor_identity') or namedassign(n,'last_observed_process_tree') or(isinstance(n,ast.FunctionDef) and n.name=='retain_error') or callstmt(n,'require_transport_binding'))]
o=fn(m,'observe');o.body=[n for n in o.body if not((isinstance(n,ast.If) and ast.unparse(n.test)=='not observed_supervisor_identity') or(isinstance(n,ast.Assign) and any(isinstance(t,ast.Subscript) and ast.unparse(t.value)=='last_observed_process_tree' for t in n.targets)))]
for i,n in enumerate(m.body):
 if namedassign(n,'result'):assert [k.arg for k in n.value.keywords]==['retain_exception'];n.value.keywords=[]
 if namedassign(n,'safe'):assert ast.unparse(n.value.func)=='make_safe_result';m.body[i]=copy.deepcopy(next(n for n in om.body if namedassign(n,'safe')))
mt=next(n for n in m.body if isinstance(n,ast.Try));ot=next(n for n in om.body if isinstance(n,ast.Try));assert len(ot.body)==len(mt.body)+2;mt.body[2:2]=copy.deepcopy(ot.body[2:4])
assert dump(old)==dump(new)
# Exact inherited-control source, with only the intended module import changed.
a=ast.parse((D/'original-test_actual_transport_v5.py').read_bytes());b=ast.parse((R/'test_actual_transport_v6_inherited_controls.py').read_bytes())
for n in b.body:
 if isinstance(n,ast.Import):
  for alias in n.names:
   if alias.name=='actual_transport_v6':assert alias.asname=='T';alias.name='actual_transport_v5'
assert dump(a)==dump(b)
counts={}
for name in ['test_actual_transport_failure_metadata_v6.py','test_actual_transport_failure_metadata_v6_additional.py','test_actual_transport_v6_inherited_controls.py']:
 tree=ast.parse((R/name).read_bytes());counts[name]=sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_') for n in ast.walk(tree))
assert list(counts.values())==[9,5,36]
red=(D/'original-v5-exception-path-RED.private.log').read_text();green=(D/'final-v6-integrated-50-servicefree-controls.private.log').read_text()
assert len(re.findall(r'^FAIL: test_',red,re.M))==8 and 'Ran 9 tests' in red and 'FAILED (failures=8)' in red
assert 'Ran 50 tests' in green and green.rstrip().endswith('OK')
assert json.loads((D/'original-v5-exception-path-RED-terminal.json').read_text())['returncode']==1
assert json.loads((D/'final-v6-integrated-50-servicefree-controls-terminal.json').read_text())['returncode']==0
# Retain-source/native data readback only; no product or test imports.
c=json.loads((R/'FROZEN-control3-current-b614-actual-config-v2.json').read_bytes());repo=Path(c['source_root']);env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],env=env,stderr=subprocess.PIPE)
assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[owner['source'],owner['tree']]
assert git('status','--porcelain')==b''
for row in c['source_body_modes']:
 p=repo/row['path'];data=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes()
 assert hashlib.sha256(data).hexdigest()==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode']
assert len(c['source_body_modes'])==1421
for row in c['native_original_members']:
 p=Path(c['native_original_root'])/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert p.is_file() and not p.is_symlink() and h(p)==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert p.is_symlink() and os.readlink(p)==row['link_target']
assert len(c['native_original_members'])==1192
assert {p.relative_to(c['native_original_root']).as_posix() for p in Path(c['native_original_root']).rglob('*')}=={r['path'] for r in c['native_original_members']}
for path,sha in c['prepared_inputs'].items():assert h(repo/path)==sha
assert len(c['prepared_inputs'])==30
proof={'status':'GO_PRIVATE_TRANSPORT_METADATA_SOURCE_ONLY','owner':bind(ownerpath),'new_transport':bind(R/'actual_transport_v6.py'),'verification':{'owner_bindings':34,'original_retained_bindings':263,'original_failed_state_bindings':12,'source_body_modes':1421,'native_original_members':1192,'prepared_inputs':30,'whole_v5_AST_equality_after_exact_metadata_and_self_binding_projection':True,'inherited_36_test_AST_exact_after_import_only_rebinding':True,'original_RED':{'fail':8,'pass':1,'errors':0},'final_recorded_GREEN':{'pass':50,'errors':0,'skip':0},'control_groups':counts},'source':{'commit':owner['source'],'tree':owner['tree'],'control':owner['control'],'control_tree':owner['control_tree']},'review_findings':[],'limits':['No tests, helper, gateway, native binaries or actual process executed by reviewer.','Preserved sampled maximum64 last observed entries are not a final descendant census.','Unobserved supervisor/command identities remain null; helper final-census and reader facts remain null/UNKNOWN.','Original helper attrs retained independently; capacity remains primary and cleanup FAIL remains separate.','Raw exception text/traceback remain private; retention failure adds only secondary class.','Named v6 requires exact content-bound successor config before state/process startup; old8c5 release does not qualify v6.','No approval for new source/config/command retarget or actual run.'],'documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','accepted_exact_patch':bind(D/'canonical-retain-original-transport-failure-and-observed-ownership-proposed.patch'),'durable_learning':'Keep original helper facts and previously observed ownership on failure; never substitute sampled captures for final survivors/readers; pin each transport successor separately.','evidence':'Independent whole AST comparison, exact pinned helper exception fields,9+5+36 source controls and recorded8FAIL1PASS to50PASS.','stale_or_ambiguous_guidance_removed':'Failure classification cannot erase ownership observations or imply absent reader/final-census proof.','remaining_uncertainty':'v6 actual persistence/readback and separately reviewed source/config/command successor remain unqualified.'},'upstream_disposition':'none','references':refs+[bind(D/'before-v6-complete263-and-original-failure-bindings.json')]}
path=OUT/'OWNERFINAL-independent-private-transport-v6-metadata-source-review.json';assert not path.exists();path.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');path.chmod(0o600);print(json.dumps(bind(path)))
