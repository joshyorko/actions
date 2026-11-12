import os, sys
from pathlib import Path
root=Path('/workspace/actions-knowledge-host')
sys.path[:0]=[str(root/'action_server/src'),str(root/'action_server/tests')]
os.chdir(root/'action_server')
os.environ['PYTHONPATH']=str(root/'action_server/src')+os.pathsep+os.environ.get('PYTHONPATH','')
if __name__=='__main__':
 import actions.server._local_provider_setup as module
 assert Path(module.__file__).is_relative_to(root)
 print('ISOLATED_IMPORT',module.__file__,flush=True)
 import pytest
 raise SystemExit(pytest.main(sys.argv[1:]))
