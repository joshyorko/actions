import ast,difflib,hashlib,json,os,subprocess,tempfile,zipfile
from pathlib import Path
r=Path('/workspace/engineering/pr302'); evidence=Path('/workspace/engineering/pr302-actual310-source-refresh'); out=Path('/workspace/engineering/pr302-Sprime-independent-source-review')
sha=lambda b:hashlib.sha256(b).hexdigest()
cp=evidence/'source-Sprime-frozen-checkpoint.json'; assert sha(cp.read_bytes())=='61a0d394e75fd605936acec528aac87a9f768025ee8e5e82db667628eb090c74'; c=json.loads(cp.read_bytes())
def git(*a):return subprocess.check_output(['git','-C',str(r),*a])
def text(*a):return git(*a).decode().strip()
def blob(ref,p):return git('show',ref+':'+p)
def leaves(ref):
 return {n.decode():tuple(h.decode().split()) for h,n in (x.split(b'\t',1) for x in git('ls-tree','-rz',ref).split(b'\0') if x)}
head=c['source_Sprime'];left,right=c['ordered_parents'];tree=c['source_tree'];base=text('merge-base',left,right)
assert text('rev-parse','HEAD')==head and text('rev-parse','HEAD^{tree}')==tree
assert text('show','-s','--format=%P',head).split()==[left,right]
assert text('branch','--show-current')==c['branch']; assert not git('status','--porcelain')
B,L,R,U=map(leaves,[base,left,right,head]); combined=[]
assert set(U)==set(L)|set(R) and (len(L),len(R),len(U))==(1406,1409,1409)
for p in set(B)|set(L)|set(R):
 b,l,rv=B.get(p),L.get(p),R.get(p)
 if l==rv:expected=l
 elif l==b:expected=rv
 elif rv==b:expected=l
 else:combined.append(p);continue
 assert U.get(p)==expected,p
assert set(combined)=={'.github/workflows/_gen_workflows.py','docs/skills/repository-operations.md'}
verified={}
for k,v in c['evidence_files'].items():
 data=Path(v['path']).read_bytes(); assert len(data)==v['size'] and sha(data)==v['sha256'],k;verified[k]=v
# Every current tracked blob/mode agrees with the frozen tree, including generated outputs.
for p,(mode,kind,oid) in U.items():
 if kind=='blob':
  raw=(r/p).read_bytes(); assert raw==blob(head,p),p
  if mode in ('100644','100755'):assert bool((r/p).stat().st_mode&0o111)==(mode=='100755'),p

def blocks(raw):
 result={}
 for i,n in enumerate(ast.parse(raw).body):
  key=(type(n).__name__,getattr(n,'name',None))
  if isinstance(n,ast.Assign):key=('assign',ast.dump(n.targets[0]))
  elif isinstance(n,(ast.Import,ast.ImportFrom)):key=('import',ast.dump(n))
  elif isinstance(n,ast.Expr):key=('expr',i)
  elif isinstance(n,ast.If):key=('if',ast.dump(n.test))
  assert key not in result;result[key]=ast.dump(n)
 return result
p='.github/workflows/_gen_workflows.py';bb,ll,rr,uu=[blocks(blob(ref,p)) for ref in [base,left,right,head]]
assert set(uu)==set(ll)|set(rr) and len(uu)==32
for key in set(bb)|set(ll)|set(rr):
 b,l,rv=bb.get(key),ll.get(key),rr.get(key)
 if l==rv:expected=l
 elif l==b:expected=rv
 elif rv==b:expected=l
 else:raise AssertionError(('overlapping generator AST',key))
 assert uu.get(key)==expected,key
assert uu['ClassDef','ActionServerRccProviderRollback']==ll['ClassDef','ActionServerRccProviderRollback']
assert U['.github/workflows/actions_runtime_rcc_provider_rollback.yml']==L['.github/workflows/actions_runtime_rcc_provider_rollback.yml']
patch=Path('/workspace/engineering/pr302-next-refresh-readonly/canonical-nine-source-bindings-proposed.patch'); assert sha(patch.read_bytes())=='fef37515784cbf9fbb003ecca90ec0acb78d8e319bf2fd0ce2c2c1805ff955e6'
addition=''.join(x[1:]+'\n' for x in patch.read_text().splitlines() if x.startswith('+') and not x.startswith('+++')).encode()
p='docs/skills/repository-operations.md'; union=blob(head,p); assert union.count(addition)==1; stripped=union.replace(addition,b'',1)
# Independent three-way merge-file writes only our owned temp files, never an index/ref.
with tempfile.TemporaryDirectory(dir=out,prefix='doc-union-') as tmp:
 ps=[Path(tmp)/n for n in ['left','base','right']]
 for dest,ref in zip(ps,[left,base,right]):dest.write_bytes(blob(ref,p))
 m=subprocess.run(['git','merge-file','-p',*(str(x) for x in ps)],capture_output=True)
 assert m.returncode==0 and m.stdout==stripped,'canonical union differs from ordinary parent merge plus accepted paragraph'
retained={}
for ref in [left,right]:
 bl=blob(base,p).decode().splitlines(True);pl=blob(ref,p).decode().splitlines(True);count=0
 for tag,a,b,j,k in difflib.SequenceMatcher(a=bl,b=pl).get_opcodes():
  if tag in ['replace','insert']:assert ''.join(pl[j:k]).encode() in stripped;count+=1
 retained[ref]=count
assert sorted(retained.values())==[4,5]
assert U['docs/skills/work-items.md']==R['docs/skills/work-items.md']
S=c['preserved_prior_acceptance']['S']; nine={}
for name,v in c['preserved_prior_acceptance']['source_nine'].items():
 p=v['path']; raw=blob(head,p); assert sha(raw)==v['sha256'] and raw==blob(S,p) and U[p]==L[p] and U[p]==leaves(S)[p];nine[name]=v
inv=json.loads((r/'docs/program/evidence/runtime-frozen-current-source-20261011/producer-input-inventory.json').read_bytes()); selected=json.loads((r/'docs/program/evidence/runtime-frozen-current-source-20261011/selected-test-inventory.json').read_bytes()); assert len(inv)==268 and len(selected)==5
changed=[]
for p,v in inv.items():
 assert U[p][0]==v['mode']
 digest=sha(blob(head,p))
 if digest!=v['sha256']: changed.append({'path':p,'native_sha256':v['sha256'],'source_union_sha256':digest})
assert changed==c['source_union_proof']['producer268_delta']
for p,v in selected.items():assert sha(blob(head,p))==v['sha256'] and U[p][0]==v['mode']
# Full prepared input set, actual venv configuration and previously measured source origins.
boot=json.loads((evidence/'own-bootstrap-reuse-complete-gateway-proof.json').read_bytes());decl=json.loads(Path(boot['declared_gateway_build_inventory_source']).read_bytes())['inputs_sha256']; inputs=boot['all_current_bytes_equal_prepared_source'];old=boot['all19inputs_exact']
assert len(inputs)==30 and len(old)==19 and len(decl)==24 and set(inputs)==set(old)|set(decl) and len(set(old)&set(decl))==13
assert sha(Path(boot['prior_bootstrap']).read_bytes())==boot['prior_bootstrap_sha256']
assert not boot['new_installs'] and not boot['new_Bootstrap_executed']
for p,v in inputs.items():
 assert v['prior19_subset_input']==(p in old) and v['declared24_gateway_build_input']==(p in decl)
 assert sha(blob(head,p))==v['sha256'] and blob(head,p)==blob(S,p) and U[p]==leaves(S)[p]
 if p in old:assert old[p]==v['sha256']
 if p in decl:assert decl[p]==v['sha256']
assert len(boot['all5ownenvs'])==5
for v in boot['all5ownenvs']:
 cfg=Path(v['venv'])/'pyvenv.cfg'; assert sha(cfg.read_bytes())==v['configuration_sha256'] and cfg.read_text()==v['configuration'];assert str((Path(v['venv'])/'bin/python').resolve())==v['python_resolved']
origins=json.loads((evidence/'own-five-prefix-and-source-origins.json').read_bytes());assert len(origins['five_measured_origins'])==5 and origins['own_source_and_venv_prefix_assertions_passed'] and not origins['product_execution']
for v in origins['five_measured_origins']:
 assert v['origin'].startswith(str(r)+'/') and v['prefix'].startswith(str(r)+'/') and v['prefix'].endswith('/.venv') and Path(v['origin']).exists() and Path(v['python']).exists()
# Gates are readbacks of frozen logs; this review does not invoke package/toolkit/product code.
def log(name):return (evidence/name).read_text()
terminal='actual main robot run" was SUCCESS'
for name in ['Doctor.log','ToolkitTest.log','scoped-static-regeneration-corrected.log','own-origins-and-full-source.log']:assert terminal in log(name),name
assert 'RCC developer toolkit checks passed.' in log('Doctor.log')
assert '96 passed in 22.40s' in log('ToolkitTest.log')
scoped=log('scoped-static-regeneration-corrected.log'); assert '109 passed, 4 skipped, 4 warnings in 5.56s' in scoped and '301 files already formatted' in scoped and 'Success: no issues found in 337 source files' in scoped
assert 'poetry run invoke lint' in scoped and 'poetry run isort --check src tests' in scoped
assert scoped.count('Writing to ')==8 and scoped.count('Writing dependabot config to')==1
full=log('own-origins-and-full-source.log');assert '1169 passed, 13 skipped, 15 warnings in 129.49s' in full and '2 workers' in full and 'test-not-integration' in full
assert str(r/'action_server/.venv') in full and str(r/'action_server/src/actions/server/_rcc_runtime_adapter.py') in full
# Immutable original historical archive, all seven raw member records and candidate/control tuple.
a=c['preserved_prior_acceptance']['artifact'];raw=Path(a['local_path']).read_bytes();assert len(raw)==a['size'] and sha(raw)==a['sha256']
with zipfile.ZipFile(a['local_path']) as z:
 assert set(z.namelist())=={v['member'] for v in a['members']}
 for v in a['members']:data=z.read(v['member']);assert len(data)==v['size'] and sha(data)==v['sha256']
 summary=json.loads(z.read('rcc-provider-rollback-evidence/acceptance-summary.json'))
assert summary['source']['candidate_sha']==S and summary['source']['candidate_tree']==c['preserved_prior_acceptance']['S_tree']
assert summary['source']['workflow_control_sha']==left and summary['source']['workflow_control_tree']==c['preserved_prior_acceptance']['C_tree']
assert summary['source']['files_sha256']=={name:v['sha256'] for name,v in nine.items()}
assert summary['test']['junit']=={'tests':3,'failures':0,'errors':0,'skipped':0} and summary['test']['exit_code']==0
assert c['control_Cprime'].startswith('NOT_AUTHORED')
assert text('rev-parse',S+'^{tree}')==c['preserved_prior_acceptance']['S_tree']
assert text('rev-parse',left+'^{tree}')==c['preserved_prior_acceptance']['C_tree']
# Observe frozen source again before releasing the control writer.
assert text('rev-parse','HEAD')==head and not git('status','--porcelain')
result={'status':'GO_SPRIME_SOURCE_FOR_CONTROL_AUTHORING_ONLY','source':{'head':head,'tree':tree,'ordered_parents':[left,right],'branch':c['branch'],'clean':True},'review_operations':'READ_ONLY_GIT_BLOB_AST_HASH_AND_FROZEN_LOG_READBACK; external evidence only; no gateway/product/test/regeneration execution','frozen_checkpoint':{'path':str(cp),'sha256':sha(cp.read_bytes())},'independent_verified':{'1409_exact_parent_leaf_union':True,'no_parent_deletions_or_novel_nondocumentation':True,'32_generator_top_level_AST_parent_union':True,'RCC_class_and_generated_workflow_exact_old_control':True,'canonical_ordinary_parent_merge_plus_exact_fef9_lesson':True,'canonical_retained_parent_blocks':retained,'all1409_current_working_bytes_modes_match_frozen_tree':True,'nine_source_bodies_modes_exact_S43a':True,'three_selectors_profile_one_publish_raw_summary_Core102_contracts_unchanged':True,'producer268_changed_adapter_only':changed,'selected5_body_modes_equal_native':True,'bootstrap_reuse_inputs':{'prior':19,'declared':24,'overlap':13,'unique':30,'unchanged_prepared_git_bytes_modes':True,'five_actual_origin_prefix_records_and_existing_venv_configs':True,'new_install':False},'Doctor':'PASS','ToolkitTest':'96PASS','scoped':'109PASS4optinSKIP4warnings','configured_full':'1169PASS13SKIP15warnings/129.49s/2workers','configured_lint':'Ruff/format301/Isort PASS; optionalmdl unavailable','typecheck':'337filesSUCCESS','regeneration_frozen_log_and_current_outputs':'8workflows+dependabot','original_7_member_artifact_hashes_unchanged':True},'evidence_files':verified,'historical_scope':{'S':S,'S_tree':c['preserved_prior_acceptance']['S_tree'],'C':left,'C_tree':c['preserved_prior_acceptance']['C_tree'],'artifact_id':a['id'],'artifact_sha256':a['sha256'],'original_summary_source_nine_candidate_control_and_threecase_counts_verified':True,'old26checks':'originalba04/testedmerge63cf only; no new exactunion qualification'},'next_gate':'Root-authorized separate Cprime must pin immutable d642 source/tree fdf2; new control and fresh tested merge require independent review and hosted acceptance. This GO only releases control authoring, never push/actual/merge.','HOLDs':['native92498 changed-adapter reuse UNQUALIFIED; no exclusions/new native proof','new currentSprime/Cprime hosted three-case/fulltestedmergeCI','private01f/frozenv6/full134135/metadata/supervisor','Windows/Core103/fullrelease/publication'],'Documentation_improvement':c['Documentation_improvement'],'Upstream_disposition':'none','retained_306':'fd8621/4d08V2activation-fit proposal remains read-only/design-only; no306 writer or actual retry'}
# Exact accepted delta retained in review evidence; no cosmetic second proposal.
(out/'canonical-nine-source-bindings-verified.patch').write_bytes(patch.read_bytes())
result['canonical_review_disposition']='Accepted fef9 patch integrated byte-exact once in frozenSprime; existing parent lessons retained. Independent review rejects any extension to artifact/native/current-CI qualification.'
result['review_script_sha256']=sha(Path(__file__).read_bytes())
f=out/'independent-Sprime-source-review-v2.json';f.write_text(json.dumps(result,indent=2)+'\n');f.chmod(0o444)
print(json.dumps({'status':result['status'],'receipt':str(f),'sha256':sha(f.read_bytes()),'size':f.stat().st_size}))
