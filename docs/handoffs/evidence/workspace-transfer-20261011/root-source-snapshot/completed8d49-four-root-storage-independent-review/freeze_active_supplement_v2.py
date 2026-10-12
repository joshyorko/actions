import pathlib,json,hashlib,stat
R=pathlib.Path('/workspace/engineering/completed8d49-four-root-storage-independent-review');p=pathlib.Path('/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v2/OWNERFINAL-readonly-active-a209cc-config-and-all-critical-row-overlap-supplement.json')
def bind(p):
 p=pathlib.Path(p);b=p.read_bytes();s=p.lstat();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),mode=oct(stat.S_IMODE(s.st_mode)))
d=json.loads(p.read_bytes());assert bind(p)['sha256']=='37f28dbde2116ccbe7eaeb543ea47a3f4d4faa8234a35e9ba4e7f44ffbf35705'
for key in ['active_qualified_config','original237_config_binding_verified','four_root_original_owner','retained_constructor_format_failure']:assert bind(d[key]['path'])==d[key]
q=json.loads(pathlib.Path(d['active_qualified_config']['path']).read_bytes());o=json.loads(pathlib.Path(d['original237_config_binding_verified']['path']).read_bytes())
roots=[pathlib.Path(v) for v in d['selected_physical_roots'].values()]
for r in roots:assert r.resolve()==r and not r.is_symlink()
rows=[]
def collect(v):
 if isinstance(v,dict):
  if isinstance(v.get('path'),str) and pathlib.Path(v['path']).is_absolute() and ('sha256'in v or 'bytes'in v):rows.append(pathlib.Path(v['path']))
  for x in v.values():collect(x)
 elif isinstance(v,list):
  for x in v:collect(x)
collect(q);assert len(rows)==304
rows += [pathlib.Path(x['path']) for x in o['bindings']]
rows += [pathlib.Path(q['source_root'])/name for name in q['prepared_inputs']]
rows += [pathlib.Path(q['native_original_root'])/x['path'] for x in q['native_original_members']]
rows += [pathlib.Path(q['source_root'])/x['path'] for x in q['source_body_modes']]
assert len(rows)==3203
for a in rows:
 b=a.resolve();assert all(a!=r and r not in a.parents and b!=r and r not in b.parents for r in roots)
for name,h in q['prepared_inputs'].items():assert bind(pathlib.Path(q['source_root'])/name)['sha256']==h
old=R/'OWNERFINAL-independent-four-completed8d49-roots-capped-storage-PREEXECUTION-review.json';v=json.loads(old.read_bytes());v['predecessor_independent_binding']=bind(old);v['active_config_overlap_supplement_binding']=bind(p);v['active_config_binding']=d['active_qualified_config'];v['active_config_selection_disjoint_rows']=3203;v['active_config_prepared30_independently_rehashed']=True;v['retained_independent_constructor_type_failure']=bind(R/'retained-active-supplement-constructor-type-FAIL.json');v['limits'].append('Active a209cc separately scanned, all3203 lexical/resolved paths disjoint; this does not newly qualify those payloads. Historical a3e191 owner remains unchanged.')
f=R/'OWNERFINAL-independent-four-completed8d49-roots-capped-storage-PREEXECUTION-review-v2.json';f.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n');f.chmod(0o400);print(json.dumps(bind(f)))
