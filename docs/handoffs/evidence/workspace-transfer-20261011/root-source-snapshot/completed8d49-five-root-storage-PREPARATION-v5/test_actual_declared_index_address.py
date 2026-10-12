"""Static actual-archiver AST/index-plan equality; no archiver import or execution."""
import ast,json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=Path('/workspace/engineering/completed8d49-five-root-storage-PREPARATION-v4')
def actual_index(source):
 tree=ast.parse(source.read_text())
 dest=next(n.value.args[0].value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DEST' for t in n.targets))
 index=next(n.value.right.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_FULL_INDEX' for t in n.targets))
 return str(Path(dest)/index)
class OriginalRED(unittest.TestCase):
 def test_original_actual_index_equals_declared_alias_index(self):
  plan=json.loads((OLD/'private-fixed-nine-original-row-future-archive-member-plan.json').read_bytes())
  self.assertEqual(plan['full_index_path'],actual_index(OLD/'archive_exact_five_completed_roots_once.py'))
class CurrentGREEN(unittest.TestCase):
 def test_current_actual_index_equals_declared_alias_index(self):
  plan=json.loads((HERE/'private-fixed-nine-original-row-future-archive-member-plan.json').read_bytes())
  self.assertEqual(plan['full_index_path'],actual_index(HERE/'archive_exact_five_completed_roots_once.py'))
 def test_wrong_index_name_is_rejected_by_exact_address_predicate(self):
  wrong=json.loads((HERE/'private-fixed-nine-original-row-future-archive-member-plan.json').read_bytes());wrong['full_index_path']=str(Path(wrong['full_index_path']).parent/'private-wrong-index.json.gz')
  with self.assertRaises(AssertionError):assert wrong['full_index_path']==actual_index(HERE/'archive_exact_five_completed_roots_once.py')
if __name__=='__main__':
 original=sys.argv[1:] == ['--original-red']
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(OriginalRED if original else CurrentGREEN)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 sys.exit(not result.wasSuccessful())
