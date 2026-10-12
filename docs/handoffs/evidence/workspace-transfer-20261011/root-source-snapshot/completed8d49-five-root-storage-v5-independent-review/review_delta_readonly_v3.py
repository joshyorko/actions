import ast,copy,hashlib,json,os,pathlib,stat
P=pathlib.Path('/workspace/engineering/completed8d49-five-root-storage-PREPARATION-v5');O=pathlib.Path('/workspace/engineering/completed8d49-five-root-storage-PREPARATION-v4');R=pathlib.Path('/workspace/engineering/completed8d49-five-root-storage-v5-independent-review')
def digest(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=pathlib.Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();return dict(path=str(p),bytes=s.st_size,sha256=digest(p),mode=oct(stat.S_IMODE(s.st_mode)))
def check(r):assert bind(r['path'])==r
owner=P/'OWNERFINAL-five-completed8d49-roots-capped-storage-PREEXECUTION-v5.json';d=json.loads(owner.read_bytes());assert bind(owner)['sha256']=='e82b78156e3ec08f033555f314faa30bde4a1319f769a796df68a7d556dc2d4a'
for row in d['private_references']:check(row)
od=json.loads((O/'OWNERFINAL-five-completed8d49-roots-capped-storage-PREEXECUTION-v4.json').read_bytes())
for row in od['private_references']:check(row)
audit=json.loads(pathlib.Path(d['predecessor_V4_original_actual_failure_review']['path']).read_bytes())
for row in audit['references']:check(row)
assert audit['removed_roots']==0 and audit['all_selected_originals_remain'] is True
# Only explicit bound alias plan literals may alter original function/class AST.
v4plan=O/'private-fixed-nine-original-row-future-archive-member-plan.json';v5plan=P/v4plan.name;plan0=json.loads(v4plan.read_bytes());plan=json.loads(v5plan.read_bytes())
normalized_plan=copy.deepcopy(plan)
for key in ['archive_path','full_index_path','mapping_path']:normalized_plan[key]=plan0[key]
assert normalized_plan==plan0
old=ast.parse((O/'archive_exact_five_completed_roots_once.py').read_bytes());new=ast.parse((P/'archive_exact_five_completed_roots_once.py').read_bytes())
class Normalize(ast.NodeTransformer):
 def visit_Constant(self,n):
  if n.value==str(v5plan):return ast.copy_location(ast.Constant(str(v4plan)),n)
  if n.value==digest(v5plan):return ast.copy_location(ast.Constant(digest(v4plan)),n)
  return n
def definitions(tree):return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
assert definitions(old)==definitions(Normalize().visit(copy.deepcopy(new)))
loops=lambda t:[ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.For)];assert loops(old)==loops(new)
assign={}
for n in new.body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):assign[n.targets[0].id]=n.value
actual_dest=pathlib.Path(assign['DEST'].args[0].value);actual_index=actual_dest/assign['_FULL_INDEX'].right.value
assert plan['full_index_path']==str(actual_index)
assert plan['archive_path']==str(actual_dest/(plan['archive_label']+'.tar.gz'))
assert pathlib.Path(plan['mapping_path']).parent==actual_dest
assert assign['_CAP'].value==100663296 and assign['_INDEX_CAP'].value==16777216 and assign['_NATIVE_FLOOR'].value==134217728
assert 2*assign['_CAP'].value+assign['_INDEX_CAP'].value+assign['_NATIVE_FLOOR'].value==352321536
stage=pathlib.Path(assign['STAGE'].args[0].value);assert not stage.exists() and not actual_dest.exists()
launch=ast.parse((P/'launch_once.py').read_bytes());la={}
for n in launch.body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):la[n.targets[0].id]=n.value
bindings=ast.literal_eval(la['BINDINGS'])
for row in bindings.values():check(row)
assert bindings['alias_plan']==bind(v5plan)
assert bindings['archiver']==bind(P/'archive_exact_five_completed_roots_once.py')
assert bindings['guard']==bind(P/'guard_readonly.py')
assert la['EXPECTED_REVIEW_DECISION'].value==d['required_review_decision']
# Reuse our own stdlib snapshot function only, not any archiver/module code.
src=ast.parse(pathlib.Path('/workspace/engineering/completed8d49-five-root-storage-independent-review/verify_readonly_v2.py').read_bytes());fn=next(n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='snapshot');ns={'stat':stat,'os':os,'digest':digest};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<reviewer-stdlib-snapshot>','exec'),ns)
s=json.loads((O/'private-five-root-input-supplement.json').read_bytes());check(s['base_config_binding']);base=json.loads(pathlib.Path(s['base_config_binding']['path']).read_bytes());base['selected_snapshots']['original27-log']=base['selected_snapshots'].pop('robocorp-log')
for k,x in s['added_roots'].items():base['selected_snapshots'][k]=x['snapshot']
count=allocation=0
for k,p in d['five_selected_roots'].items():
 v,n=ns['snapshot'](pathlib.Path(p));assert v=={k:x for k,x in base['selected_snapshots'][k].items() if k in ['root','entries','identities']};count+=len(v['entries']);allocation+=n
assert count==9035 and allocation==294944768
check(plan['original_inventory_binding']);iv=json.loads(pathlib.Path(plan['original_inventory_binding']['path']).read_bytes());assert len(iv['files'])==18 and len(plan['aliases'])==9
for x in plan['aliases']:assert x['original_row'] in iv['files'];check(x['original_row'])
# Address RED/GREEN are retained actual static-AST test outputs, not inspector reruns.
red=json.loads((P/'original-index-address-RED-terminal.json').read_bytes());green=json.loads((P/'current-index-address-GREEN-terminal.json').read_bytes());assert red['returncode']==1 and green['returncode']==0
# Verified all addresses explicitly rather than only plan self-consistency.
assert plan0['full_index_path']!=str(pathlib.Path('/tmp/actions-completed8d49-five-root-preserved-v4')/assign['_FULL_INDEX'].right.value)
proof=dict(schema='INDEPENDENT_V5_FINITE_BUDGET_AND_ACTUAL_ARCHIVER_ALIAS_ADDRESS_DELTA',proposal_binding=bind(owner),owner_ref_rows=len(d['private_references']),prior50refs_rehashed=True,prior_actual_cap_failure_references_rehashed=len(audit['references']),all9035_current_snapshots_equal=True,allocated294944768=True,original_inventory18_unchanged=True,nine_alias_original_rows_unchanged=True,archive_function_class_AST_all_normalized_equal=True,unchanged_removal_loop=True,actual_archive_index_mapping_addresses_closed=True,actual_FULL_INDEX=str(actual_index),archive_cap=100663296,index_cap=16777216,TMP_floor=352321536,original48MiB_failure_unchanged=True,original_V4_alias_index_mismatch_verified=True,review_gap='Prior independent V4 review missed direct actual _FULL_INDEX vs plan comparison; observed V4 cap failure occurred before seam and remains unchanged.',source=d['source_head'],tree=d['source_tree'],compression_and_operation='NOT_RUN',fresh_capacity_snapshot={p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in ['/workspace','/tmp','/dev/shm']})
f=R/'independent-V5-budget-address-and-unchanged-current-snapshot-proof.json';f.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');f.chmod(0o400);print(json.dumps(bind(f)))
