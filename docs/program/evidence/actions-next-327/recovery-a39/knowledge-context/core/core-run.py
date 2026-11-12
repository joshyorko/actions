import os,sys
from pathlib import Path
root=Path('/workspace/actions-knowledge-core')
sys.path[:] = [p for p in sys.path if Path(p).resolve() != Path(__file__).parent]
sys.path[:0]=[str(root/'actions/src'),str(root/'actions/tests')]
os.environ['PYTHONPATH']=str(root/'actions/src')+os.pathsep+os.environ.get('PYTHONPATH','')
os.chdir(root/'actions')
if __name__=='__main__':
 import actions.data._context as module
 assert Path(module.__file__).is_relative_to(root)
 print('ISOLATED_IMPORT',module.__file__,flush=True)
 import pytest
 raise SystemExit(pytest.main(sys.argv[1:]))
