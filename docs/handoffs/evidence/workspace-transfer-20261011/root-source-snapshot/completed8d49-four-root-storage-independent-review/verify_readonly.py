import ast,collections,hashlib,json,os,pathlib,stat,subprocess,xml.etree.ElementTree as ET
R=pathlib.Path('/workspace/engineering/completed8d49-four-root-storage-independent-review')
P=pathlib.Path('/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v2')
def digest(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=pathlib.Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 return dict(path=str(p),bytes=s.st_size,sha256=digest(p),mode=oct(stat.S_IMODE(s.st_mode)))
checked={}
def check(row):
 if row['path'] in checked: assert checked[row['path']]==row;return
 assert bind(row['path'])==row;checked[row['path']]=row
owner=P/'OWNERFINAL-four-completed8d49-roots-capped-storage-PREEXECUTION-v2.json';d=json.loads(owner.read_bytes());assert bind(owner)['sha256']=='f6cf65eb7dba1500609bee28a9adc8fdda11bf1487e8dded84b62106cde5b9e7'
for row in d['private_references']+[d['predecessor_f113_owner'],d['predecessor_inventory_reused_by_reference'],d['critical_qualified_current_config']]:check(row)
oldowner=json.loads(pathlib.Path(d['predecessor_f113_owner']['path']).read_bytes())
for row in oldowner['original_B28_source_and_review']+[oldowner['current_SOURCEFULL_independent']]:check(row)
s=json.loads((P/'private-four-root-input-supplement.json').read_bytes());check(s['base_config_binding']);check(s['base_owner_binding']);c=json.loads(pathlib.Path(s['base_config_binding']['path']).read_bytes())
c['roots']['original27-log']=c['roots'].pop('robocorp-log');c['selected_snapshots']['original27-log']=c['selected_snapshots'].pop('robocorp-log')
for k,v in s['added_roots'].items():c['roots'][k]=v['path'];c['selected_snapshots'][k]=v['snapshot']
assert c['roots']==d['selected_roots'] and len(set(c['roots'].values()))==4
for row in c['references']+c['completion_bindings']+s['completion_bindings']+[c['source_guard'],c['source_guard_inputs']]:check(row)
q=json.loads(pathlib.Path(s['qualified_current_config_binding']['path']).read_bytes())
# Critical bindings must remain outside the exact selected namespaces. No private payload is emitted.
def binding_rows(v):
 if isinstance(v,dict):
  if {'path','bytes','sha256','mode'}<=v.keys():yield v
  for x in v.values():yield from binding_rows(x)
 elif isinstance(v,list):
  for x in v:yield from binding_rows(x)
rows=list(binding_rows(q));roots=[pathlib.Path(x).resolve() for x in c['roots'].values()]
for row in rows:
 p=pathlib.Path(row['path']).resolve()
 assert not any(p==r or r in p.parents for r in roots)
# Immutable completed parents and explicit logging argv, actual JUnit case counts.
light=json.loads(pathlib.Path(c['completion_owner']['path']).read_bytes());green=json.loads(pathlib.Path(c['completion_green']['path']).read_bytes())
assert light['results']['ToolkitTest_passed']==179 and all(light[k]==0 for k in ['before_returncode','primary_returncode','post_returncode'])
assert green['returncode']==0 and any(str(roots[1]) in x for x in green['argv'])
jn=[]
basej=next(row for row in c['completion_bindings'] if row['path'].endswith('original-GREEN-junit.xml'))
for label,n,row in [('original27-log',27,basej)]+[(x['label'],x['passed'],x['junit']) for x in s['completion_records']]:
 tree=ET.fromstring(pathlib.Path(row['path']).read_bytes());cases=list(tree.iter('testcase'))
 assert len(cases)==n and all(not list(t.iter('failure')) and not list(t.iter('error')) and not list(t.iter('skipped')) for t in cases)
 assert len({(t.attrib.get('classname'),t.attrib['name']) for t in cases})==n
 jn.append(dict(label=label,passed=n,failures=0,errors=0,skips=0))
for x in s['completion_records']:
 t=json.loads(pathlib.Path(x['terminal']['path']).read_bytes());assert t['returncode']==0 and '--robocorp-log-output='+c['roots'][x['label']] in t['argv']
# AST only: no imported archiver, guard, or product code.
def definitions(path):
 return {x.name:x for x in ast.parse(pathlib.Path(path).read_bytes()).body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}
a=definitions(oldowner['original_B28_source_and_review'][0]['path']);b=definitions(P/'archive_exact_four_completed_roots_once.py');two=definitions(pathlib.Path(d['predecessor_f113_owner']['path']).parent/'archive_exact_two_completed_roots_once.py')
exact=['sha','inventory','verify','reject_live_handles','_CappedWriter','_write_and_close_preserving_primary','_snapshot','_ns_text','_strict_verify','_fsync_path','_index_bytes_except','_IndexBudgetPath','_ReadOnlyTar']
for k in exact:assert ast.dump(a[k],include_attributes=False)==ast.dump(b[k],include_attributes=False)
assert ast.dump(two['_prestage_all'],include_attributes=False)==ast.dump(b['_prestage_all'],include_attributes=False)
class UndoKeys(ast.NodeTransformer):
 def visit_Call(self,node):
  node=self.generic_visit(node)
  if isinstance(node.func,ast.Name) and node.func.id=='_key_for_root' and len(node.args)==1 and isinstance(node.args[0],ast.Name) and node.args[0].id=='root':return ast.Attribute(value=ast.Name(id='root',ctx=ast.Load()),attr='name',ctx=ast.Load())
  return node
assert ast.dump(UndoKeys().visit(b['_GuardedShutil']),include_attributes=False)==ast.dump(two['_GuardedShutil'],include_attributes=False)
def snapshot(root):
 entries={};identities={};groups={};s=root.lstat();assert stat.S_ISDIR(s.st_mode)
 ri={k:getattr(s,'st_'+k) for k in ['uid','gid','mtime_ns','dev','ino','nlink']};ri['mode']=stat.S_IMODE(s.st_mode)
 for p in sorted(root.rglob('*')):
  t=p.lstat();rel=str(p.relative_to(root));v=dict(mode=stat.S_IMODE(t.st_mode),mtime_ns=t.st_mtime_ns,uid=t.st_uid,gid=t.st_gid)
  if stat.S_ISREG(t.st_mode):v.update(kind='file',bytes=t.st_size,sha256=digest(p));groups.setdefault((t.st_dev,t.st_ino),[]).append(rel)
  elif stat.S_ISDIR(t.st_mode):v.update(kind='directory')
  elif stat.S_ISLNK(t.st_mode):v.update(kind='symlink',target=os.readlink(p))
  elif stat.S_ISFIFO(t.st_mode):v.update(kind='fifo')
  else:raise RuntimeError('Unsupported owned member type')
  entries[rel]=v;identities[rel]=[t.st_dev,t.st_ino,t.st_nlink]
 for members in groups.values():assert all(identities[k][2]==len(members) for k in members)
 return dict(root=ri,entries=entries,identities=identities)
measured=[]
for label,p in c['roots'].items():
 v=snapshot(pathlib.Path(p));expected={k:x for k,x in c['selected_snapshots'][label].items() if k in ['root','entries','identities']};assert v==expected
 measured.append(dict(label=label,members=len(v['entries']),types=dict(collections.Counter(x['kind'] for x in v['entries'].values())),external_hardlinks=0))
assert sum(x['members'] for x in measured)==9026
# Independent accessible-handle observation; inaccessible races remain UNKNOWN.
links=matched=unknown=0
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 candidates=[p/'cwd']
 try:candidates+=list((p/'fd').iterdir())
 except (OSError,PermissionError):unknown+=1
 for link in candidates:
  try:target=os.readlink(link);links+=1
  except OSError:unknown+=1;continue
  if any(target==str(r) or target.startswith(str(r)+'/') for r in roots):matched+=1
assert matched==0
for row in list(checked.values()):assert bind(row['path'])==row
release=pathlib.Path('/workspace/engineering/root-completed8d49-four-root-storage-reviewed-release-v2.json')
absent=['/workspace/engineering/root-completed8d49-four-root-storage-one-owned-v2','/tmp/actions-completed8d49-four-root-preserved-v2','/tmp/actions-completed8d49-four-root-preservation-stage-v2']
assert not release.exists() and all(not pathlib.Path(x).exists() for x in absent)
proof=dict(owner_binding=bind(owner),bindings_verified=len(checked),source=d['source_head'],tree=d['source_tree'],exact_original_B28_helper_AST=exact,allroot_prestage_AST_exact_f113=True,guarded_removal_delta='Exact physical-root to unique logical-key substitution only',completed_case_counts=jn,ToolkitTest_completed=179,selected_root_snapshots=measured,critical_binding_rows_outside_selection=len(rows),handle_observation=dict(accessible_links=links,selected_matches=matched,unreadable_or_raced=unknown,universal_quiescence='UNKNOWN'),absence_checks_passed=True,operation='NOT_RUN',native_floor='Not restored or waived by proposal; fresh actual capacity recheck required')
p=R/'independent-four-root-source-completion-and-current-snapshot-proof.json';p.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');p.chmod(0o400)
print(json.dumps(bind(p)))
