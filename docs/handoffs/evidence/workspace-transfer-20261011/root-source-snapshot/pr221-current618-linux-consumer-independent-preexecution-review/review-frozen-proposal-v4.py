import ast
import copy
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import stat

B=Path('/workspace/engineering/pr221-current618-linux-consumer-preflight')
O=Path('/workspace/engineering/pr221-current618-linux-consumer-independent-preexecution-review')
R=Path('/workspace/engineering/pr282')
def sha(data):return hashlib.sha256(data).hexdigest()
def binding(row):
 p=Path(row['path']);data=p.read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256'];return row
def load(p):return json.loads(Path(p).read_bytes())
def tree(p):return ast.parse(Path(p).read_bytes())
def dump(node):return ast.dump(node,include_attributes=False)
def functions(p):return {n.name:n for n in tree(p).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a])
def assigned(t,name):return next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id==name for x in n.targets))

final=binding({'path':str(B/'immutable-current618-linux-consumer-preexecution-proposal-v4.json'),'bytes':39398,'sha256':'da926a733e60108fd2943add0a60a0bf6d365afbb1d489bf986a0624ecda65c0'})
d=load(final['path'])
for key,expected in [('runner','06f64db20bba0554f570d4653f11fb7bccc7b98ec2e7de7085ab90fd8ba7333b'),('input_gate','1edf96b6b801de5e7b8c1c7c284a636cec44bc06fcb45adb6e1781e519b3a8f6'),('input_manifest','798f11c5416e57d6d0fa39c79c9524fc52e2e022496c1c3f12b3c902facc61d3')]:
 binding(d[key]);assert d[key]['sha256']==expected
binding(d['previous_held_v3_proposal']);binding(d['previous_independent_HOLD'])
old=load(d['previous_held_v3_proposal']['path']);original_review=load(d['previous_independent_HOLD']['path'])
assert d['previous_independent_HOLD']['sha256']=='61929d78c9f98ef9d333447b0e09f3f18fcad4f84167b0bf256accab0b98189b'
assert len(d['all_private_preexecution_files_and_preserved_originals'])==60
for row in d['all_private_preexecution_files_and_preserved_originals']:binding(row)
for row in old['all_private_preexecution_files_and_preserved_originals']:binding(row)
for row in d['historical776_consumer_and_original84fail1_controls_preserved']:binding(row)
assert len(old['all_private_preexecution_files_and_preserved_originals'])==36 and len(d['historical776_consumer_and_original84fail1_controls_preserved'])==29
for key in ['runner','input_gate','input_manifest']:binding(old[key])
owner=load(binding(d['artifact_data_ownerfinal'])['path'])
assert d['artifact_data_ownerfinal']['sha256']=='9b406fdf505871e6790d7a4233d0b8c075ae6f170f2c5b7a954bbca0f0d46236'
assert len(owner['evidence'])==24
for row in owner['evidence']:binding(row)
inspection_ref=binding(owner['complete_original_member_inventories']);inspection=load(inspection_ref['path'])
assert inspection_ref==d['independent_provenance_expectation']['complete_inspection']
m=load(d['input_manifest']['path']);old_manifest=load(old['input_manifest']['path'])
artifact=next(a for a in inspection['artifacts'] if a['file']['path']==m['original_archive']['path_private'] and a['file']['bytes']==m['original_archive']['bytes'] and a['file']['sha256']==m['original_archive']['sha256'])
expected={'id':artifact['id'],'run':owner['producer']['run_id'],'job':artifact['job_id']}
assert expected=={'id':11697353355,'run':38126987514,'job':114433293243}
assert inspection['run_id']==expected['run']
assert d['independent_provenance_expectation']['derived_identity']==expected
for field,producer_field in [('id','artifact_id'),('run','run_id'),('job','job_id')]:
 assert type(m['original_archive'][field]) is int and type(m['producer_tuple'][producer_field]) is int
 assert m['original_archive'][field]==m['producer_tuple'][producer_field]==expected[field]
restored=copy.deepcopy(m);restored['schema']=old_manifest['schema']
for key in ['id','run','job']:restored['original_archive'][key]=old_manifest['original_archive'][key]
del restored['producer_tuple']['artifact_id']
assert restored==old_manifest
for key in ['original_archive','selected_cp312_wheel','complete_current202_python_member_manifest']:
 assert d[key]==old[key];binding(d[key])
assert d['current_counts']==old['current_counts']=={'python':202,'tracked_source_payloads':215,'RECORD_files':221,'RECORD_hashsize_verified':220,'directories':27}
assert d['producer']==old['producer'] and d['actual_integration']==old['actual_integration']

runner=d['runner']['path'];previous_runner=old['runner']['path']
newfunc=functions(runner);oldfunc=functions(previous_runner)
assert len(newfunc)==9 and newfunc.keys()==oldfunc.keys()
for name in newfunc:assert dump(newfunc[name])==dump(oldfunc[name])
newtree,oldtree=tree(runner),tree(previous_runner)
allowed_assignments={'ATTEMPT','SOURCES'}
for name in allowed_assignments:assigned(newtree,name).value=copy.deepcopy(assigned(oldtree,name).value)
assert dump(newtree)==dump(oldtree)
sources=ast.literal_eval(assigned(tree(runner),'SOURCES').value) if False else assigned(tree(runner),'SOURCES').value
source_literals=[n.value for n in ast.walk(sources) if isinstance(n,ast.Constant)]
assert d['input_gate']['path'] in source_literals and d['input_gate']['sha256'] in source_literals
assert d['input_manifest']['path'] in source_literals and d['input_manifest']['sha256'] in source_literals
assert d['known_checkout_roots']==old['known_checkout_roots'] and len(d['known_checkout_roots'])==15
assert d['helpers_current_Git618_and_immutable_snapshots_exact']==old['helpers_current_Git618_and_immutable_snapshots_exact']
for name,row in d['helpers_current_Git618_and_immutable_snapshots_exact'].items():
 binding(row)
 if name!='rcc':
  relative=Path(row['path']).relative_to('/workspace/engineering/pr311' if name=='guard' else R).as_posix()
  assert sha(git('show',d['actual_integration']['sha']+':'+relative))==row['sha256']
helper_snapshots=[row for row in d['all_private_preexecution_files_and_preserved_originals'] if '/unchanged-helper-snapshots/' in row['path']]
assert len(helper_snapshots)==4
for row in helper_snapshots:assert stat.S_IMODE(Path(row['path']).stat().st_mode)==0o444

gate=tree(d['input_gate']['path']);prior_gate=tree(old['input_gate']['path'])
new_gate_functions={n.name:n for n in gate.body if isinstance(n,ast.FunctionDef)}
old_gate_functions={n.name:n for n in prior_gate.body if isinstance(n,ast.FunctionDef)}
assert set(new_gate_functions)-set(old_gate_functions)=={'admit_provenance'}
for name in ['digest','safe_members','validate_payload']:assert dump(new_gate_functions[name])==dump(old_gate_functions[name])
admit=new_gate_functions['admit'];assert isinstance(admit.body[0],ast.Assign)
assert ast.unparse(admit.body[0])=='provenance = admit_provenance(manifest)'
admit.body.pop(0)
updates=[n for n in ast.walk(admit) if isinstance(n,ast.Dict) and any(isinstance(k,ast.Constant) and k.value=='qualified_archive_provenance' for k in n.keys)]
assert len(updates)==1
dictionary=updates[0];idx=next(i for i,k in enumerate(dictionary.keys) if isinstance(k,ast.Constant) and k.value=='qualified_archive_provenance')
assert isinstance(dictionary.values[idx],ast.Name) and dictionary.values[idx].id=='provenance'
dictionary.keys.pop(idx);dictionary.values.pop(idx)
assert dump(admit)==dump(old_gate_functions['admit'])
qual_sha=ast.literal_eval(assigned(tree(d['input_gate']['path']),'TRUSTED_QUALIFICATION_SHA256').value)
assert qual_sha==d['artifact_data_ownerfinal']['sha256']
qual_path=ast.literal_eval(assigned(tree(d['input_gate']['path']),'TRUSTED_QUALIFICATION').value.args[0])
assert qual_path==d['artifact_data_ownerfinal']['path']
provenance_source=ast.get_source_segment(Path(d['input_gate']['path']).read_text(),new_gate_functions['admit_provenance'])
assert 'digest(body) == TRUSTED_QUALIFICATION_SHA256' in provenance_source
assert 'digest(inspected) == reference["sha256"]' in provenance_source
assert 'original[field] == producer[producer_field] == expected[field]' in provenance_source
assert 'len(artifacts) == 1' in provenance_source
assert 'not isinstance(' in provenance_source and 'bool' in provenance_source

class Rebind(ast.NodeTransformer):
 def visit_Constant(self,node):
  if isinstance(node.value,str):
   node.value=node.value.replace('input-and-source-admission-v4.json','input-and-source-admission.json').replace('installed-consumer-runner-v4.py','installed-consumer-runner-v3.py').replace('current-input-admission-v4.py','current-input-admission-v3.py')
  return node
for new,previous in [('test_installed_consumer_runner_v4.py','test_installed_consumer_runner_v3.py'),('test_current_input_admission_v4.py','test_current_input_admission.py')]:
 a,b=functions(B/new),functions(B/previous);assert a.keys()==b.keys()
 for name in a:assert dump(Rebind().visit(a[name]))==dump(b[name])
new_controls=functions(B/'test_current_input_provenance_v4.py')
assert set(new_controls)=={'manifest','admit','test_independently_qualified_current_bytes_and_labels_pass','test_correct_current_archive_bytes_reject_false_provenance','test_independent_qualification_cannot_be_relabelled'}
poison_source=ast.get_source_segment((B/'test_current_input_provenance_v4.py').read_text(),new_controls['test_correct_current_archive_bytes_reject_false_provenance'])
assert 'admit(value)' in poison_source and 'coordinated' in poison_source
assert all(field in poison_source for field in ['path_private','bytes','sha256'])
qual_control=ast.get_source_segment((B/'test_current_input_provenance_v4.py').read_text(),new_controls['test_independent_qualification_cannot_be_relabelled'])
assert 'admit(value)' in qual_control and 'TRUSTED_QUALIFICATION' in qual_control
logs=d['service_free_controls']
for name in ['RED_v3','current_v4_GREEN']:
 binding(logs[name]['log'])
binding(logs['preserved_static_failure'])
red=Path(logs['RED_v3']['log']['path']).read_text();green=Path(logs['current_v4_GREEN']['log']['path']).read_text();static_fail=Path(logs['preserved_static_failure']['path']).read_text()
assert '6 failed, 1 passed in 9.46s' in red and red.count('DID NOT RAISE')>=6 and 'actual main robot run" was FAILURE' in red
assert '93 passed, 2 warnings in 8.53s' in green and 'actual main robot run" was SUCCESS' in green
assert 'E721' in static_fail and 'actual main robot run" was FAILURE' in static_fail and 'passed in' not in static_fail
assert all(command in green for command in ['ruff check','ruff format --check','isort --check'])
assert logs['current_v4_GREEN']['skipped']==0

assert d['budgets']==old['budgets']
assert d['planned_ONE_actual_gateway']['argv'][:4]==['timeout','--signal=TERM','--kill-after=10s','645s']
assert d['planned_ONE_actual_gateway']['cwd']==str(R)
assert d['planned_ONE_actual_gateway']['attempt_root'].endswith('installed-linux-current618-90a785d8-2')
assert not Path(d['planned_ONE_actual_gateway']['attempt_root']).exists()
assert d['harness']==old['harness'];binding(d['harness']['complete_prehash'])
harness=load(d['harness']['complete_prehash']['path'])
assert git('rev-parse','HEAD').decode().strip()==d['harness']['head']=='e736f846557ed1d603348e97c5eb80060d62e3e2'
assert git('rev-parse','HEAD^{tree}').decode().strip()==d['harness']['tree']=='07b716104ba623df81c00bd83be08dde84dd29f1'
assert git('status','--porcelain')==b'' and len(harness['tracked_sha256'])==1433
for path,digest in harness['tracked_sha256'].items():assert sha((R/path).read_bytes())==digest and bool((R/path).stat().st_mode&0o111)==harness['tracked_executable_bits'][path]
binding(d['source_control_scope_proof'])
doc=d['documentation_improvement'];binding(doc['Exact_delta'])
assert doc['Exact_delta']['sha256']=='5f08b459a43e6fe50c6baac0c56f0a6d5241ec6aff913498df39e0d597962aeb'
lesson=Path(doc['Exact_delta']['path']).read_text();assert 'Changing' not in lesson and 'changing both copies' in lesson
assert 'independently' in lesson and 'while retaining the correct archive bytes must still fail before installation' in lesson
assert d['actual_consumer_executed'] is False and d['pip_install_download_publication_executed'] is False
receipt={'schema':'current618-linux-consumer-independent-v4-preexecution-review/v1','status':'GO_PREEXECUTION_PROPOSAL_ONLY_ACTUAL_REQUIRES_DISTINCT_ROOT_AUTHORIZATION','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owner_final_proposal':final,'runner':d['runner'],'input_gate':d['input_gate'],'input_manifest':d['input_manifest'],'previous_v3_proposal':d['previous_held_v3_proposal'],'previous_v3_HOLD':d['previous_independent_HOLD'],'finding_disposition':'Original current bytes with stale archive metadata were admitted by v3. v4 corrects labels and rejects both single and coordinated stale copies through independently pinned9b406 qualification and its digest/size-bound complete inspection. Original v3 HOLD remains historical; no retroactive GO.','independent_expected_archive_identity':expected,'verified':{'all_current_refs':60,'all_v3_refs_untouched':36,'historical776_refs':29,'owner_artifact_log_refs':24,'all_hash_sizes_exact':True,'current_original_ZIP_SHA256':d['original_archive']['sha256'],'current_wheel_SHA256':d['selected_cp312_wheel']['sha256'],'current_counts':d['current_counts'],'current_input_payloads_unchanged_v3_except_identity_schema_labels':True,'trusted_identity_not_derived_from_caller_duplicate_labels':True,'all9_runner_function_ASTs_exact_v3':True,'runner_only_top_level_attempt_and_manifest_gate_pins_changed':True,'original_gate_predicates_AST_exact_after_removing_only_guard_call_and_receiptfield':True,'only_new_guard_function':'admit_provenance','original85controls_ASTs_preserved_filename_rebinding_only':True,'six_coordinated_and_single_stale_label_RED_baseline_pass':True,'new_trusted_qualification_tamper_rejection_control':True,'recorded93_GREEN0skip':True,'E721_static_failure_before_tests_retained':'Strict int excluding bool corrected without predicate waiver','helpers_current_Git618_and4immutable0444_snapshots_exact':True,'roots':15,'INVENTORY_CODE_unchanged':True,'harness1433_e736_07b_clean_prehash':True,'producer_synthetic_not_actual':'e766/a709+618/tree99ac remains builder; equal actual618 tree is separate identity','original_OAuth_two_empty_strings_and_Windows_semantics_modes_HOLD_retained':True},'planned_exact_gateway':d['planned_ONE_actual_gateway'],'budgets':d['budgets'],'execution_capacity':'Root must freshly release serialization/capacity before separately authorizing exactly one actual; no execution by reviewer','documentation_improvement':doc,'remaining_HOLDs':d['remaining_HOLDs'],'not_performed':['Actual consumer/Runtime install/import/CLI','Tests/controls/gateway/installer/download/live polling','Source/index/branch writes','Publication/tag/native/browser/provider/Windows gate/push/merge'],'upstream_disposition':'none'}
dest=O/'independent-frozen-v4-preexecution-review-GO.json';assert not dest.exists();dest.write_text(json.dumps(receipt,indent=2)+'\n');dest.chmod(0o444)
print(json.dumps({'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest.read_bytes()),'status':receipt['status']}))
