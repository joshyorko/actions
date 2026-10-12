import ast,hashlib,json,pathlib,stat,copy,os
O=pathlib.Path('/workspace/engineering/pr307-currente2-concrete-LIGHT-PREEXECUTION')
B=pathlib.Path('/workspace/engineering/pr307-currente2-concrete-LIGHT-PREEXECUTION-v2')
OUT=pathlib.Path('/workspace/engineering/pr307-current2314-concrete-LIGHT-independent-review')
def sha(b):return hashlib.sha256(b).hexdigest()
def bind(p):
 p=pathlib.Path(p);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b),'mode':oct(stat.S_IMODE(m.st_mode))}
def exact(r):
 a=bind(r['path']);assert all(a[k]==r[k] for k in ('bytes','sha256','mode'));return a
owner=bind(B/'OWNERFINAL-current2314-concrete-LIGHT-PREEXECUTION-v2.json');assert owner['sha256']=='f5242f221043785c61916793ffec05c4d3dee9820642c9de210ef435298d3e4d'
d=json.loads(pathlib.Path(owner['path']).read_bytes());old=json.loads((O/'OWNERFINAL-current2314-concrete-LIGHT-PREEXECUTION.json').read_bytes())
refs=[owner];refs.extend(exact(d[k]) for k in ('launcher','config','controlled_staged_Invoke','activation','source_union_owner'))
c=json.loads(pathlib.Path(d['config']['path']).read_bytes());oc=json.loads((O/'immutable-one-LIGHT-inputs.json').read_bytes());assert c['bindings'][:len(oc['bindings'])]==oc['bindings'];assert len(c['bindings'])==10
assert {k:v for k,v in c.items() if k!='bindings'}=={k:v for k,v in oc.items() if k!='bindings'}
refs.extend(exact(r) for r in c['bindings']);assert d['controlled_staged_Invoke']==old['controlled_staged_Invoke'];assert d['bounds']==old['bounds']
olds=ast.parse((O/'launch_one_owned_light.py').read_bytes());news=ast.parse(pathlib.Path(d['launcher']['path']).read_bytes());of={n.name:n for n in olds.body if isinstance(n,ast.FunctionDef)};nf={n.name:n for n in news.body if isinstance(n,ast.FunctionDef)}
assert set(of)==set(nf)
for name in set(of)-{'guard','main'}:assert ast.dump(of[name],include_attributes=False)==ast.dump(nf[name],include_attributes=False),name
assert [ast.dump(x,include_attributes=False) for x in nf['guard'].body[10:]]==[ast.dump(x,include_attributes=False) for x in of['guard'].body]
# Exact main delta: wider global declaration and capture the already authenticated self hash.
main=copy.deepcopy(nf['main']);main.body[0].names.remove('SELF_EXPECTED');assign=[i for i,x in enumerate(main.body) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SELF_EXPECTED' for t in x.targets)];assert len(assign)==1;main.body.pop(assign[0]);assert ast.dump(main,include_attributes=False)==ast.dump(of['main'],include_attributes=False)
# All top-level statements except three explicitly declared binding changes stay exact.
def norm(t):
 t=copy.deepcopy(t);t.body=[x for x in t.body if not(isinstance(x,ast.Assign) and any(isinstance(y,ast.Name) and y.id=='SELF_EXPECTED' for y in x.targets))]
 for x in t.body:
  if isinstance(x,ast.Assign) and any(isinstance(y,ast.Name) and y.id=='CONFIG_SHA' for y in x.targets):x.value=ast.Constant('BOUND_CONFIG_SHA')
  if isinstance(x,ast.FunctionDef) and x.name in ('guard','main'):x.body=[ast.Pass()]
 return ast.dump(t,include_attributes=False)
assert norm(olds)==norm(news)
assert not pathlib.Path('/workspace/engineering/pr307-current2314-light-once-owned').exists();assert not pathlib.Path(d['argv_adoption_after_activation'][6]).exists()
hold=bind(OUT/'OWNERFINAL-independent-current2314-original-concrete-LIGHT-PREEXECUTION-HOLD.json');assert hold['sha256']=='dae98f18b25c57226293253132572bd5c56f2c6e30d877a281dc5973bf8e8f95'
proof={'schema':'INDEPENDENT_NAMED_CURRENT2314_LIGHT_V2_DELTA_PROOF','owner':owner,'bindings_verified':refs,'original_HOLD':hold,'config_only_delta':'three appended immutable original owner/config/launcher bindings','launcher_only_delta':'new configSHA, SELF_EXPECTED initialized/captured authenticated root selfSHA, ten AST prefix guard statements for config/self/activation/prefix/optimization before/finally','all_other_function_AST_exact':sorted(set(of)-{'guard','main'}),'main_AST_exact_after_declared_capture_normalization':True,'all_other_top_level_AST_exact':True,'commands_bounds_outputroots_controlled_stage_code_unchanged':True,'tests_or_imports_or_gates_run':False}
p=OUT/'independent-named-v2-concrete-LIGHT-delta-proof.json';p.write_bytes((json.dumps(proof,indent=2,sort_keys=True)+'\n').encode());p.chmod(0o400)
r={'schema':1,'decision':'GO_CURRENT2314_LIGHT_PREEXECUTION','status':'INDEPENDENT_CONCRETE_LIGHT_V2_PREEXECUTION_GO_ONLY','source':d['source'],'tree':d['tree'],'proposal_binding':owner,'launcher':d['launcher'],'config':d['config'],'controlled_staged_Invoke':d['controlled_staged_Invoke'],'delta_proof':bind(p),'original_HOLD':hold,'root_release_schema':d['root_release_schema'],'argv_adoption_after_activation':d['argv_adoption_after_activation'],'authorization':'Only ROOT distinct exact one release, filling release SHA and this immutable review path/hash into bound argv; this review executes nothing','fresh_conditions':d['fresh_conditions'],'bounds':d['bounds'],'verified':'Full original source1442/prepared30/five metadata/15old refs/ignored output preservation and technical interface facts retained from original review; named v2 closes config/self before/finally gap; source clean at original current inspection','limits':['Current LIGHT outcomes and five actual import origin probes NOT_RUN','No FULL/native/real OAuth acquisition/installed consumer/release acceptance','Outer SIGKILL may prevent finally: such outcome remains incomplete HOLD','Fallback owned process-group wait is bounded and does not establish complete descendant or reader cleanup','Current2314/e2 source-only subject must be rebracketed before root launch; no refreshed target/CI carry'],'documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta':(OUT/'proposed-canonical-launcher-selfbinding-before-finally.txt').read_text(),'durable_learning':'Entry-only selfbinding must be distinguished from all-input before/finally preservation; named v2 now implements the latter for config and launcher','evidence':'Original f650 guard lacks self/config checks, named5cfd prefix guard adds exact checks while all other functions and commands are AST-identical','stale_or_ambiguous_guidance_removed':'Initial binding is not mislabeled as always-post coverage','remaining_uncertainty':'Execution, post preservation outcome, origin probes, source-authority and FULL/freshCI remain unobserved'},'upstream_disposition':'none','read_only':True}
p=OUT/'OWNERFINAL-independent-current2314-concrete-LIGHT-PREEXECUTION-v2-GO.json';p.write_bytes((json.dumps(r,indent=2,sort_keys=True)+'\n').encode());p.chmod(0o400);print(json.dumps(bind(p),sort_keys=True))
