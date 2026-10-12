import ast,hashlib,json,os,stat,subprocess,tomllib
from pathlib import Path
D=Path('/workspace/engineering/pr307-current9760-owning-settings-independent-SOURCE-and-once4-review');P=Path('/workspace/engineering/pr307-current9760-token-light-once4-PREEXECUTION-NOTRUN');W=Path('/workspace/engineering/pr307')
S='9760d5ec44876558c4941c4c3190abc8d92d14a1';T='0d33ebaac258e069ef7045a29b4a3904740f6307';OLD='00b1bb9974b73f2da65e49c9048774c84df286ba'
def sha(b):return hashlib.sha256(b).hexdigest()
def binding(p):
 p=Path(p);st=p.lstat();assert stat.S_ISREG(st.st_mode) and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b),'mode':oct(stat.S_IMODE(st.st_mode))}
def exact(r):
 b=binding(r['path']);assert all(b[k]==r[k] for k in ['bytes','sha256','mode']);return b
def load(p):return json.loads(Path(p).read_bytes())
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(W),*args],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
def tree(ref):
 rows={}
 for line in git('ls-tree','-r','-z',ref).split(b'\0'):
  if line:
   meta,name=line.split(b'\t',1);mode,kind,oid=meta.split();rows[name.decode()]=(mode.decode(),oid.decode())
 return rows
class ImportBlocks(ast.NodeTransformer):
 def generic_visit(self,node):
  node=super().generic_visit(node)
  for field,values in ast.iter_fields(node):
   if isinstance(values,list) and values and all(isinstance(v,ast.stmt) for v in values):
    out=[];i=0
    while i<len(values):
     if not isinstance(values[i],(ast.Import,ast.ImportFrom)):out.append(values[i]);i+=1;continue
     imports=[]
     while i<len(values) and isinstance(values[i],(ast.Import,ast.ImportFrom)):
      n=values[i];imports.extend(('import' if isinstance(n,ast.Import) else 'from',getattr(n,'module',None),getattr(n,'level',None),a.name,a.asname) for a in n.names);i+=1
     out.append(ast.Expr(value=ast.Constant(value=repr(sorted(imports,key=repr)))))
    setattr(node,field,out)
  return node
owner=exact({'path':str(P/'OWNERFINAL-current9760-owning-Isort-settings-SOURCE-and-fresh-once4-PREEXEC-NOTRUN.json'),'bytes':7292,'mode':'0o400','sha256':'7616d9820f33e3b920262ab501229e4695527820b2dd2fcdd53bdf9858b19e8e'});o=load(owner['path']);assert o['source']==S and o['tree']==T
for r in o['new_bindings']:exact(r)
cfg=load(o['config']['path']);proof=load(o['sourceproof']['path']);st=load(o['static_proof']['path']);contract=load(o['ROOT_contract']['path']);allrows=[exact(r) for r in cfg['bindings']];assert len(allrows)==176
hist=[exact(r) for r in proof['retained_original_evidence']];assert len(hist)==157
assert git('rev-parse','HEAD').decode().strip()==S and git('rev-parse',S+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',S).decode().strip()==OLD
assert not git('status','--porcelain')
new,old=tree(S),tree(OLD);assert len(new)==len(old)==1442 and set(new)==set(old)
changed=[p for p in sorted(new) if new[p]!=old[p]];assert changed==sorted(o['source_changed_paths']) and len(changed)==4
for rel,(mode,oid) in new.items():
 p=W/rel;blob=git('cat-file','blob',oid);m=p.lstat()
 if mode=='120000':assert p.is_symlink() and os.readlink(p).encode()==blob
 else:assert stat.S_ISREG(m.st_mode) and p.read_bytes()==blob and bool(m.st_mode&0o111)==(mode=='100755')
for rel in changed:
 assert new[rel][0]==old[rel][0]
 if rel.endswith('.py'):
  a=ImportBlocks().visit(ast.parse(git('show',OLD+':'+rel).decode()));b=ImportBlocks().visit(ast.parse((W/rel).read_text()));assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
assert new['devutils/src/devutils/fixtures.py']==old['devutils/src/devutils/fixtures.py']
a=tomllib.loads(git('show',OLD+':devutils/pyproject.toml').decode());b=tomllib.loads((W/'devutils/pyproject.toml').read_text());expected={'line_length':88,'multi_line_output':3,'include_trailing_comma':True,'use_parentheses':True};assert b['tool'].pop('isort')==expected and a==b
assert len(proof['prepared30_current_source_inputs'])==30; priorproof=load(proof['original_prepared30_label_and_bytes']['path']); oldprep=priorproof['prepared30_exact_original307_head'];oldprep={r['path']:r for r in oldprep};delta=[]
for r in proof['prepared30_current_source_inputs']:
 raw=(W/r['path']).read_bytes();assert sha(raw)==r['sha256'] and len(raw)==r['bytes']
 prior=oldprep[r['path']]
 if (r['sha256'],r['bytes'])!=(prior['sha256'],prior['bytes']):delta.append(r['path'])
assert delta==['devutils/pyproject.toml']
for r in proof['five_existing_venvs_config_only']:exact(r['pyvenv_config'])
checks=[]
for row in st['complete_Devutils_static_checks']:
 exact(row);term=load(row['path']);assert term['returncode']==0;checks.append({'original_terminal':row,'command':term.get('command',term.get('argv')),'returncode':0})
# These are original observed checks, not reviewer re-execution.
for checksrow in checks:assert checksrow['command'] is not None
script=Path(o['launcher']['path']).read_text();priorlauncher=Path('/workspace/engineering/pr307-current00b1-token-light-once3-PREEXECUTION-NOTRUN/launch_one_owned_token_light_once3_format_child.py').read_text();normalized=script
for oldliteral,newliteral in reversed(st['changed_launcher_literals']):normalized=normalized.replace(newliteral,oldliteral)
assert normalized==priorlauncher and ast.dump(ast.parse(normalized))==ast.dump(ast.parse(priorlauncher))
module=ast.parse(script);constants={}
for n in module.body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
  try:constants[n.targets[0].id]=ast.literal_eval(n.value)
  except (ValueError,TypeError):pass
assert constants['SOURCE']==S and constants['TREE']==T and constants['CONFIG_SHA']==o['config']['sha256']
assert "CONFIG=BASE/'immutable-one-TOKEN-LIGHT-once4-inputs.json'" in script
assert Path(o['config']['path']).parent==Path(o['launcher']['path']).parent
assert not Path(contract['attempt_root']).exists() and not Path(contract['root_release_path']).exists()
assert len(cfg['managed_activation_expected'])==18 and cfg['managed_activation_expected']['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
assert contract['independent_review_required']=={'config_sha256':o['config']['sha256'],'decision':'GO_CURRENT9760_TOKEN_LIGHT_ONCE4_GATEWAY_PREEXECUTION','launcher_sha256':o['launcher']['sha256'],'source':S,'tree':T}
assert contract['budgets']['phase_count']==9 and contract['budgets']['primary_phase_budget']==780 and contract['budgets']['outer']==900
for r in cfg['forbidden_generated_outputs']:
 p=Path(r['path'])
 if r['exists']:exact(r['binding'])
 else:assert not p.exists() and not p.is_symlink()
canon=exact(o['documentation']['exact_delta']); source_result={'schema':1,'status':'INDEPENDENT_CURRENT9760_OWNING_DEVUTILS_SETTINGS_SOURCE_GO','decision':'GO_CURRENT9760_OWNING_ISORT_SETTINGS_SOURCE_ONLY','source':S,'tree':T,'parent':OLD,'owner_binding':owner,'actual_source_review':{'clean':True,'full_typed_Git_FS_body_exec_mode_count':1442,'unchanged_other_body_modes':1438,'changed_four_paths':changed,'fixtures_exact_original_bytes':True,'test_import_contiguous_block_positions_binding_multisets_nonimport_AST':'EXACT','Isort_four_explicit_settings':expected,'all_other_TOML_dependency_build_tables_locks_gates':'EXACT','original_prepared30_history_retained':exact(proof['original_prepared30_label_and_bytes']),'current_source30_changed_rows':delta,'other29_inputs_exact':True,'existing_own_five_config_bindings_exact':True},'actual_observed_owning_compatibility_checks':checks,'original_conflict':exact(st['retained_original_conflict']),'original_collector_guessed_five_FAIL':exact(st['collector_guessedfive_failure']),'corrected_metadata_no_gate_replay':exact(st['named_metadata_only_correction']),'all_new_owner_bindings_exact':len(o['new_bindings']),'all_current_config_consumed_bindings_exact':176,'all_retained_original_evidence_exact':157,'limits':{'once4':'NOT_RUN; fresh ROOT release and independent PREEXEC review required','wholeDevutils_Runtime_FULL':'MANDATORY_NOT_RUN','actual_OAuth_content_authority_native_private_release_CI_merge':'HOLD','generic_Devutils_toolkit_release_tasks':'UNCHANGED; only explicitly authorized TOKENLIGHT compatibility checks','import_side_effects':'No universal semantic equivalence claim; only binding/block/nonimport AST plus original observed checks'},'Documentation improvement':{'Canonical file changed or proposed':'docs/skills/repository-operations.md, owning formatter paragraph','Durable learning captured':'Explicit owning Isort width88/vertical-parenthesized/trailing-comma settings resolve measured GRID79 versus Ruff conflict without profile borrowing, lock/dependency changes or gate suppression; keep source inputs history distinct after config-only metadata change.','Exact proposed delta':canon,'Evidence':[st['retained_original_conflict'],*st['complete_Devutils_static_checks'],o['sourceproof']],'Stale or ambiguous guidance removed':'Sorting only imports is not enough when configured tools disagree. A target that converges to its original bytes is preserved and is not a required novel path. TOKENLIGHT checks do not redefine generic toolkit release gates.','Remaining uncertainty':'Fresh once4, complete source suites, current CI and OAuth/native/release acceptance remain unqualified.'},'Upstream disposition':'none','operations':'Read-only stdlib parsing/hashing and no-optional-locks Git metadata. No imports/tests/source/ref/index/gateway/native/download/push/merge.'}
sourceout=D/'OWNERFINAL-independent-current9760-owning-Isort-Ruff-compatible-settings-SOURCE-GO.json';assert not sourceout.exists();sourceout.write_text(json.dumps(source_result,indent=2,sort_keys=True)+'\n');sourceout.chmod(0o400)
pre_result={'schema':1,'status':'INDEPENDENT_CURRENT9760_TOKEN_LIGHT_ONCE4_PREEXECUTION_GO','decision':'GO_CURRENT9760_TOKEN_LIGHT_ONCE4_GATEWAY_PREEXECUTION','source':S,'tree':T,'config_sha256':o['config']['sha256'],'launcher_sha256':o['launcher']['sha256'],'source_independent_review':binding(sourceout),'owner_binding':owner,'config_binding':o['config'],'launcher_binding':o['launcher'],'ROOT_contract_binding':o['ROOT_contract'],'exact_ROOT_argv_template':contract['ROOT_exact_argv'],'root_release_path':contract['root_release_path'],'required_ROOT_release':{'schema':1,'decision':'RELEASE_ONE_CURRENT9760_TOKEN_LIGHT_ONCE4_ONLY','source':S,'tree':T,'config_sha256':o['config']['sha256'],'launcher_sha256':o['launcher']['sha256'],'independent_review':{'path':'THIS_IMMUTABLE_REVIEW_PATH','sha256':'THIS_IMMUTABLE_REVIEW_SHA256'}},'execution_admissibility':{'one_distinct_ROOT_release':'Regular nonsymlink0600 ownedUID/primaryGID, strict exact body hash, fresh unconsumed output/release','fresh_capacity_workspace_floor_bytes':cfg['light_workspace_floor_bytes'],'activation':'All18 expected exports +PATH first/actions-cloud/bin; cached Toolkit prefix/no optimize/own origins/current30 inputs','ROOT_external_before_and_always_post':'Strict exact independent review, release, parent self/config/launcher/owner/new/current/original bound rows rehashed before and every outcome; capture original raw stdout/stderr and durable terminal even on failure. Child consumes ROOT review/release only initially; child finally self/config/176/source30/ownfive/history157 guard is not a substitute for external parent closure. Derive actual ROOT row count from new binding union, not old96.','native_or_full_serialization':'No concurrent heavy gateway. No installation, credential acquisition or inherited operator token/version selectors. ROOT owns execution.'},'verified_static_envelope':{'actual_selected_CONFIG_path_and_body':'EXACT','whole_launcher_text_AST_inverse_except_declared_ten_literals':'EXACT','declared_data_key_change':'prepared30_exact_original307_head -> prepared30_current_source_inputs, cardinality30 and exact data predicates preserved','current_prepared30_one_changed_row':'devutils/pyproject.toml, non-dependency Isort table only; old30 retained as historical, five ownvenv config identities exact','all_176_consumed_bindings_and_157_history':'EXACT','fresh_output_and_release':'ABSENT','original_fail_chain':'Retained once1, once2Ruff, once3Isort and measured GRID/Ruff incompatibility FAIL. No success relabel.','strict_RED':'Two exact missing-token semantic failures, checked inner1 plus actual Toolkit frame and gateway10. All unexpected failures/errors/timeouts reject.','budgets':contract['budgets'],'forced_fallback_cleanup_or_readers':'No universal cleanup guarantee; original final descendant/reader facts may remain UNKNOWN; every failure must be retained'},'actual_current_once4':'NOT_RUN','normal_existing_branch_push':'Requires ROOT policy and accepted actual current TOKENLIGHT; this PREEXEC GO is not actual-source/FULL/CI/merge approval','whole_affected_FULL_OAuth_authority_native_private_release':'HOLD','Documentation improvement':source_result['Documentation improvement'],'Upstream disposition':'none','operations':source_result['operations']}
out=D/'OWNERFINAL-independent-current9760-owning-settings-TOKEN-LIGHT-once4-PREEXECUTION-GO.json';assert not out.exists();out.write_text(json.dumps(pre_result,indent=2,sort_keys=True)+'\n');out.chmod(0o400);print(json.dumps(binding(sourceout)));print(json.dumps(binding(out)))
