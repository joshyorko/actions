"""Original actual protected() fails a new retention assertion under pure seams."""
import json, os, subprocess, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
OLD=Path('/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v2')
HERE=Path(__file__).resolve().parent
class OriginalRetention(unittest.TestCase):
 def test_failed_original_call_retains_capture_before_assertion(self):
  ns={'__name__':'original_actual_guard'}
  exec(compile((OLD/'guard_readonly.py').read_bytes(),str(OLD/'guard_readonly.py'),'exec'),ns)
  cfg=ns['load_config'](OLD/'private-four-root-input-supplement.json')
  code=json.loads(Path(cfg['source_guard_inputs']['path']).read_bytes())
  ns['exact']=lambda row:None
  ns['sys']=SimpleNamespace(prefix=code['cached_toolkit_prefix'],flags=SimpleNamespace(optimize=0))
  calls=[]
  def fake(argv,**kwargs):
   calls.append(argv)
   return subprocess.CompletedProcess(argv,1,b'original-fake-stdout',b'original-fake-stderr')
  with tempfile.TemporaryDirectory(prefix='original-RED-',dir=HERE) as d:
   with patch.dict(os.environ,{**code['expected_activation_exports'],'PATH':'/workspace/actions-cloud/bin:/usr/bin'},clear=True):
    with patch.object(subprocess,'run',fake):
     with self.assertRaisesRegex(AssertionError,'CURRENT_DATA_ONLY_SOURCE_ENV_NATIVE_GUARD_FAIL'):ns['protected'](cfg)
   self.assertEqual(len(calls),1)
   self.assertTrue((Path(d)/'stdout.private.log').exists(),'ORIGINAL_DISCARDS_CAPTURE_BEFORE_ASSERTION')
if __name__=='__main__':unittest.main(verbosity=2)
