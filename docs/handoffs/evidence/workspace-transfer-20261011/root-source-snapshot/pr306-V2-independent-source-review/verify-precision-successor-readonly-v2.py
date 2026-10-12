import ast,collections,hashlib,json,pathlib,re,subprocess
repo=pathlib.Path('/workspace/engineering/pr306');out=pathlib.Path('/workspace/engineering/pr306-V2-independent-source-review');ev=pathlib.Path('/workspace/engineering/pr306-v2-precision-successor')
head='1a3ab0b580710f776fd2075d39e04720c71541ff';parent='cf6352e253c70095c8e09904e730fc18a42f9a65';sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(repo),*a])
def blob(ref,p):return git('show',ref+':'+p)
def tree(ref):
 d={}
 for x in git('ls-tree','-rz',ref).split(b'\0'):
  if x:
   m,p=x.split(b'\t',1);d[p.decode()]=tuple(m.decode().split())
 return d
def ref(p):
 p=pathlib.Path(p);b=p.read_bytes();return {'path':str(p),'size':len(b),'sha256':sha(b)}
cpp=ev/'precision-successor-frozen-source-checkpoint.json';assert sha(cpp.read_bytes())=='3036e4b8e5121e5bce8e3bee93e41137b5636f2d155d94b290759e54ec4d7923';cp=json.loads(cpp.read_text())
verified=[]
for v in cp['evidence_files']:
 p=pathlib.Path(v['path']);b=p.read_bytes();assert len(b)==v['bytes'] and sha(b)==v['sha256'];verified.append(ref(p))
original=pathlib.Path('/workspace/engineering/pr306-windows-v2-source/implementation-V2-frozen-source-checkpoint.json');assert sha(original.read_bytes())=='f542bc04747ea8fd8741c309f26de523ee347c8aee82320931f44accf9681be0';oldcp=json.loads(original.read_text())
for v in oldcp['evidence_files'].values():
 p=pathlib.Path(v['path']);b=p.read_bytes();assert len(b)==v['size'] and sha(b)==v['sha256'];verified.append(ref(p))
for p,v in oldcp['immutable_references'].items():
 b=pathlib.Path(p).read_bytes();assert len(b)==v['size'] and sha(b)==v['sha256'];verified.append(ref(p))
old_review=out/'independent-original-cf6352-source-review-HOLD.json';assert sha(old_review.read_bytes())=='24a0d2c1bf0e0cfa18a141dbbfb0952e0fdf297ff7b93be25c58ea681a08cba7'
proposal=out/'exact-precision-canonical-proposal.patch';assert sha(proposal.read_bytes())=='e2f885f8ad15a734f3d824afe8cce956a6e1d9488b51426bdf238b4f26e1f3a0'
assert git('show','-s','--format=%T',head).decode().strip()==cp['tree'];assert git('show','-s','--format=%P',head).decode().strip()==parent
assert git('rev-parse','HEAD').decode().strip()==head and git('branch','--show-current').decode().strip()=='fix/database-savepoint-admission-20261010';assert git('status','--porcelain')==b''
h,p=tree(head),tree(parent);allowed=cp['scope_proof']['only_three_owned_paths'];assert len(h)==len(p)==1409 and set(h)==set(p);changed=[x for x in h if h[x]!=p[x]];assert sorted(changed)==sorted(allowed);assert sum(h[x]==p[x] for x in h)==1406
obs,test,guide=allowed
b=ast.parse(blob(parent,obs));a=ast.parse(blob(head,obs));class_b=next(x for x in b.body if isinstance(x,ast.ClassDef) and x.name=='DeliveredObservations');class_a=next(x for x in a.body if isinstance(x,ast.ClassDef) and x.name=='DeliveredObservations')
assert ast.dump(ast.Module(body=[x for x in b.body if x is not class_b],type_ignores=[]))==ast.dump(ast.Module(body=[x for x in a.body if x is not class_a],type_ignores=[]))
methods_b={x.name:x for x in class_b.body if isinstance(x,ast.FunctionDef)};methods_a={x.name:x for x in class_a.body if isinstance(x,ast.FunctionDef)}
changed_methods=[]
for name in methods_b:
 if name not in methods_a or ast.dump(methods_b[name])!=ast.dump(methods_a[name]):changed_methods.append(name)
assert set(changed_methods)=={'__init__','_offset','line','process_start_returned','summary'}
assert set(methods_a)-set(methods_b)=={'_instant'}
for name in ['_record','_count','cleanup_returned','cleanup_raised','start_finished']:assert ast.dump(methods_b[name])==ast.dump(methods_a[name])
text=blob(head,obs).decode();assert 'instant < self.start_return_instant + 90' in text and 'offset < self.start_return_offset + 90' not in text
assert 'return instant' in ast.unparse(methods_a['_instant']) and 'round' not in ast.unparse(methods_a['_instant'])
assert 'self.match_instants[channel][position]' in ast.unparse(methods_a['summary'])
assert not any(isinstance(n,ast.Constant) and n.value in ('start_return_instant','match_instants') for n in ast.walk(methods_a['summary']))
old_ast=ast.parse(blob(parent,test));new_ast=ast.parse(blob(head,test));old_funcs={x.name:ast.dump(x) for x in old_ast.body if isinstance(x,ast.FunctionDef)};new_funcs={x.name:ast.dump(x) for x in new_ast.body if isinstance(x,ast.FunctionDef)}
assert all(new_funcs[k]==v for k,v in old_funcs.items())
added=set(new_funcs)-set(old_funcs);assert added=={'test_ready_lower_bound_uses_exact_instants_not_rounded_display','test_reported_rounding_counterexample_stays_postbound','test_unknown_start_return_clock_keeps_deadline_classification_unknown'}
assert [ast.dump(x) for x in old_ast.body if not isinstance(x,ast.FunctionDef)]==[ast.dump(x) for x in new_ast.body if not isinstance(x,ast.FunctionDef)]
# Examine the immutable regression test contract; do not import/replay its source.
f=next(x for x in new_ast.body if isinstance(x,ast.FunctionDef) and x.name=='test_ready_lower_bound_uses_exact_instants_not_rounded_display');decorators=[ast.unparse(x) for x in f.decorator_list]
assert any('[0.0, 1000.125, 1048576.0, 1000000000.0]' in x for x in decorators)
assert any('[-0.0001, 0.0, 0.0001]' in x for x in decorators)
scalar=[]
for origin in (0.0,1000.125,1048576.0,1000000000.0):
 start=origin+2.06651;bound=start+90.0
 for delta in (-0.0001,0.0,0.0001):
  arrival=bound+delta;truth=arrival<bound;assert truth==(delta<0)
  scalar.append({'origin':origin,'delta':delta,'strict_raw_before_bound':truth})
assert (92.06661 < 2.06651+90) is False
patch=git('diff',parent,head,'--',guide);declared=(ev/'exact-precision-canonical-delta.patch').read_bytes();assert patch==declared
newguide=blob(head,guide).decode();oldguide=blob(parent,guide).decode();needle='match does not establish predeadline delivery. Future state, native ready-log\n';replacement='match does not establish predeadline delivery. Compare private, unrounded\nmonotonic instants and round only displayed offsets: rounding before adding\nthe budget can falsely classify an equal or later arrival as earlier. Exact\nequality is not before the lower bound. A positive comparison establishes only\ndelivery before that conservative bound, not completion before the actual\nreadiness deadline. Future state, native ready-log\n';assert oldguide.count(needle)==1 and oldguide.replace(needle,replacement,1)==newguide
assert len(newguide.splitlines())-len(oldguide.splitlines())==5
# Full preserved scope means native producer/selected files remain bound exactly to the original review.
prod=json.loads(pathlib.Path(oldcp['evidence_files']['current-full-producer-and-selected5-preservation.json']['path']).read_text())
assert len(prod['current268_input_full_records'])==268
native=tree(prod['native_producer']);deltas=[]
for path,v in prod['current268_input_full_records'].items():
 assert h[path]==(v['mode'],v['kind'],v['blob']) and sha(blob(head,path))==v['sha256']
 if h[path]!=native[path]:deltas.append(path)
assert deltas==['action_server/src/actions/server/_database.py']
selected=json.loads(blob(head,'docs/program/evidence/runtime-frozen-current-source-20261011/selected-test-inventory.json'));assert len(selected)==5
for path,v in selected.items():assert h[path]==native[path]==(v['mode'],v['kind'],v['blob']) and sha(blob(head,path))==v['sha256']
github=[x for x in h if x.startswith('.github/')];assert len(github)==34 and all(h[x]==p[x] for x in github);assert len([x for x in github if x.endswith(('.yaml','.yml'))])==30 and len([x for x in github if x.endswith('.yml')])==29
boot=json.loads((ev/'own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert len(boot['inputs_exact_prepared_git_bytes_sha256'])==30
for path,digest in boot['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(blob(head,path))==digest
for package,v in boot['own5venvs_current_config_and_python'].items():
 env=repo/package/'.venv';assert sha((env/'pyvenv.cfg').read_bytes())==v['config_sha256'];assert str((env/'bin/python').resolve())==v['python_resolved']
for path,digest in cp['source_after_full_equals_before'].items():assert sha(blob(head,path))==sha((repo/path).read_bytes())==digest
log_patterns={'fractional-boundary-preimplementation-RED.log':r'9 failed, 5 passed, 58 deselected','fractional-boundary-and-original-controls-GREEN.log':r'72 passed','current-scoped-configured-static.log':r'94 passed','current-generator-and-complete-DB.log':r'61 passed, 12 skipped','current-ToolkitTest.log':r'69 passed','current-full-configured-source.log':r'1216 passed, 13 skipped'}
for name,pattern in log_patterns.items():assert re.search(pattern,(ev/name).read_text()),name
assert '337 source files' in (ev/'current-scoped-configured-static.log').read_text()
result={'status':'GO_SOURCE_ONLY_FOR_NORMAL_EXISTING_PR306_BRANCH_PUSH','source':{'branch':'fix/database-savepoint-admission-20261010','head':head,'tree':cp['tree'],'ordered_parents':[parent],'clean_readback':True},'verified_source_checkpoint':ref(cpp),'verified_new_evidence_files':len(cp['evidence_files']),'verified_original_evidence_files':36,'verified_original_immutable_references':5,'evidence':verified,'preservation':{'total_leaves':1409,'other_leaf_body_mode_exact':1406,'authorized_three_paths':allowed,'whole_module_outside_DeliveredObservations_AST_exact':True,'unchanged_loss_privacy_cleanup_methods':['_record','_count','cleanup_returned','cleanup_raised','start_finished'],'changed_precision_methods':changed_methods+['_instant'],'original58controls_helper_imports_AST_exact':True,'new_boundary_functions':sorted(added),'all_original_process_callback_and_cleanup_wrapper_AST_exact':True,'all90_20_80_88_50ms_other30s_budgets_and_original_tuple_exception_identity_unchanged':True,'producer_inputs':268,'native_producer_delta':deltas,'selected_tests_body_mode_equal_native':5,'github_leaves_preserved':34,'yaml_yml_inventory':30,'original_yml_roundtrip_scope':29,'bootstrap_input_digests':30,'own_environment_configs':5,'before_after_full_committed_three_source_sha256':cp['source_after_full_equals_before']},'precision_finding_disposition':{'original_HOLD':ref(old_review),'status':'RESOLVED_FOR_THIS_SUCCESSOR_SOURCE_ONLY','fix':'Private absolute raw monotonic start and delivered match instants classify strict less-than; display offsets alone rounded3. No offset subtraction or display-rounding feeds comparator.','meaningful_TDD':'Original source RED9/5/58deselected; current72 observer controls =original58+14 new cases. Four origins xpre/equal/post12 plus reportedcounterexample and unavailable-clock; exact equality/post-boundFalse; actual source never imported/executed by reviewer.','independent_scalar_control_summary':scalar,'unknown_and_scope':'Missing start measurement remainsNone; report excludes private instants. Pre-conservative-bound delivery does not prove Future readiness, native emission or actual deadline success.'},'current_frozen_validation':cp['validation'],'original_result_identity':'cf6352/f542/HOLD24a/full1202 retained unchanged; successor1216 bound separately. No historical Windows failures or native proof relabeled.','remaining_HOLDs':['Fresh exact source hosted CI and actual bounded two-node V2 native observation absent','Original six first readiness failures remain historical; no native child pipe/forwarding/emitter/Future/rootcause established','Native92498 productionDB delta UNQUALIFIED; no new native artifact/build/retry','Broader PostgreSQL/privatefull134/metadata/OAuth/release/coldinstallation gates unchanged','This is normal existing branch source push GO only; root owns push and any separately authorized future actual or merge'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':guide+'; exact implemented5line precision delta in this successor','Durable_learning_captured':'Strict deadline classification uses private unrounded monotonic instants, serialized offsets display only; equalityFalse and conservative lower-bound scope explicit.','Evidence':[ref(ev/'exact-precision-canonical-delta.patch'),ref(cpp),ref(old_review),'Original9RED/current72GREEN14new boundary cases, immutable comparator and pure scalar classifications across4origins'], 'Stale_or_ambiguous_guidance_removed':'cf6352 could claim predeadline from rounded offsets; successor now implements raw comparator and exact guide explains equality/positive lower-bound limits.','Remaining_uncertainty':'Actual Windows observation, readiness Future/native emitter/internal transport and cause remain unavailable; sourceGO not actual/release/private admission.','Prior_proposal_disposition':'e2f885f8 independently proposed precision lesson ADAPTED/INTEGRATED; source-backed strict equality/conservative-bound clarification added. Original36line ae0e988c operational lesson otherwise retained byte-exact.'},'Upstream_disposition':'none; local Actions observer correction, no confirmed RCC upstream defect or external mutation','review_execution':'Read-only Git/AST/hash/frozen log and standard-library scalar arithmetic; no source imports, gateway/tests/replay/native/provider/browser/install/push/merge.'}
p=out/'independent-precision-successor-source-review-GO.json';p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o444);pathlib.Path(__file__).chmod(0o444);print(json.dumps({'receipt':ref(p),'status':result['status'],'head':head,'tree':cp['tree'],'canonical_patch':ref(ev/'exact-precision-canonical-delta.patch')},indent=2))
