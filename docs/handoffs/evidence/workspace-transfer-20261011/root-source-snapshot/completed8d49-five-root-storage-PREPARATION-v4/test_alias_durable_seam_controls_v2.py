"""Actual alias-persistence function under modeled writes/fsync; no root operation."""
import ast,copy,io,json,types,unittest
from pathlib import Path as RealPath
HERE=RealPath(__file__).resolve().parent
source=(HERE/'archive_exact_five_completed_roots_once.py').read_text();tree=ast.parse(source)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_durable_fixed_aliases_before_any_removal')
plan=json.loads((HERE/'private-fixed-nine-original-row-future-archive-member-plan.json').read_bytes())
import hashlib
plan_sha=hashlib.sha256((HERE/'private-fixed-nine-original-row-future-archive-member-plan.json').read_bytes()).hexdigest()
class State:
 def __init__(self):self.writes={};self.trace=[];self.full_size=123;self.fail_flush=False
class FakePath:
 def __init__(self,path,state):self.text=str(path);self.state=state
 def __str__(self):return self.text
 def __truediv__(self,other):return FakePath(str(RealPath(self.text)/other),self.state)
 def __eq__(self,other):return str(other)==self.text
 @property
 def parent(self):return FakePath(str(RealPath(self.text).parent),self.state)
 @property
 def name(self):return RealPath(self.text).name
 def is_symlink(self):return False
 def read_bytes(self):
  if self.text.endswith('private-fixed-nine-original-row-future-archive-member-plan.json'):return json.dumps(plan).encode()
  return self.state.writes[self.text]
 def stat(self):return types.SimpleNamespace(st_size=self.state.full_size)
 def open(self,mode):
  assert mode=='xb';self.state.trace.append(('open',self.text));return Writer(self)
class Writer:
 def __init__(self,path):self.path=path;self.raw=io.BytesIO()
 def __enter__(self):return self
 def __exit__(self,*args):return False
 def write(self,raw):self.path.state.trace.append(('write',self.path.text));self.raw.write(raw);self.path.state.writes[self.path.text]=self.raw.getvalue();return len(raw)
 def flush(self):
  self.path.state.trace.append(('flush',self.path.text))
  if self.path.state.fail_flush:raise OSError('fake flush failure')
 def fileno(self):return 999
class Durability(unittest.TestCase):
 def setUp(self):
  self.state=State();self.path=lambda p:FakePath(p,self.state);self.names=['ToolkitTest','original27-log','fixture42-GREEN-log','fixture51-TEMPORAL-log','Runtime50-robot-output']
  records={}
  for name in self.names:
   records[name]={'original_namespace':plan['original_root'] if name==plan['archive_label'] else '/fake/'+name,'future_destination':plan['archive_path'] if name==plan['archive_label'] else '/fake/'+name+'.tar.gz','archive_bytes':100,'archive_sha256':'a'*64,'snapshot':{'entries':{}},'verified':True}
  records[plan['archive_label']]['snapshot']['entries']={a['member'][len(plan['archive_label'])+1:]:a['expected_member_metadata'] for a in plan['aliases']}
  self.ns={'Path':self.path,'sha':lambda p:plan_sha if str(p).endswith('private-fixed-nine-original-row-future-archive-member-plan.json') else 'b'*64,'json':json,'_STAGE_RECORDS':records,'NAMES':self.names,'_FULL_INDEX':self.path(plan['full_index_path']),'_INDEX_CAP':16777216,'DEST':self.path(str(RealPath(plan['archive_path']).parent)), 'os':types.SimpleNamespace(chmod=lambda *a:self.state.trace.append(('chmod',str(a[0]))),fsync=lambda *a:self.state.trace.append(('fsync_fd',999))), '_fsync_path':lambda p:self.state.trace.append(('fsync_path',str(p))),'_index_bytes_except':lambda p:len(self.state.writes.get(plan['mapping_path'],b''))}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-private-alias-persistence>','exec'),self.ns)
 def invoke(self):self.ns['_durable_fixed_aliases_before_any_removal']()
 def test_valid_all_five_staged_mapping_nine_rows_is_durable(self):
  self.invoke();data=json.loads(self.state.writes[plan['mapping_path']]);self.assertEqual(data['aliases'],plan['aliases']);self.assertEqual(len(data['aliases']),9)
  kinds=[x[0] for x in self.state.trace];self.assertEqual(kinds,['open','chmod','write','flush','fsync_fd','fsync_path','fsync_path'])
  self.assertEqual(self.state.trace[-2][1],plan['mapping_path']);self.assertEqual(self.state.trace[-1][1],str(RealPath(plan['mapping_path']).parent))
 def test_not_all_staged_refuses_alias_before_any_write(self):
  self.ns['_STAGE_RECORDS'].pop('ToolkitTest')
  with self.assertRaises(AssertionError):self.invoke()
  self.assertFalse(self.state.writes)
 def test_wrong_fixed_original_row_metadata_refused(self):
  self.ns['_STAGE_RECORDS'][plan['archive_label']]['snapshot']['entries']=copy.deepcopy(self.ns['_STAGE_RECORDS'][plan['archive_label']]['snapshot']['entries']);self.ns['_STAGE_RECORDS'][plan['archive_label']]['snapshot']['entries']['log.html']['mode']=0 if 'log.html' in self.ns['_STAGE_RECORDS'][plan['archive_label']]['snapshot']['entries'] else 0
  with self.assertRaises(AssertionError):self.invoke()
 def test_alias_index_progress_combined_limit_not_alias_only(self):
  self.invoke();alias_size=len(self.state.writes[plan['mapping_path']]);self.state.writes.clear();self.state.trace.clear();self.ns['_INDEX_CAP']=self.state.full_size+alias_size
  with self.assertRaises(AssertionError):self.invoke()
  self.assertFalse(self.state.writes)
 def test_flush_failure_never_announces_durable_success(self):
  self.state.fail_flush=True
  with self.assertRaises(OSError):self.invoke()
  self.assertFalse(any(x[0]=='fsync_fd' for x in self.state.trace))
 def test_source_order_all_staged_then_alias_then_removal(self):
  calls=[(n.lineno,n.func.id) for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) for n in [n.value]]
  positions={name:line for line,name in calls};remove_loop=next(n.lineno for n in tree.body if isinstance(n,ast.For) and any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='rmtree' for x in ast.walk(n)))
  self.assertLess(positions['_prestage_all'],positions['_durable_fixed_aliases_before_any_removal']);self.assertLess(positions['_durable_fixed_aliases_before_any_removal'],remove_loop)
if __name__=='__main__':unittest.main(verbosity=2)
