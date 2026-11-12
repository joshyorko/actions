import os,sys
from pathlib import Path
root=Path('/workspace/actions-knowledge-prepare')
sys.path[:] = [p for p in sys.path if Path(p).resolve() != Path(__file__).parent]
sys.path[:0]=[str(root/'action_server/src'),str(root/'action_server/tests')]
os.chdir(root/'action_server')
if __name__=='__main__':
 import actions.server.data_queries.knowledge_execution as module
 assert Path(module.__file__).is_relative_to(root)
 print('ISOLATED_IMPORT',module.__file__,flush=True)
 import pytest
 raise SystemExit(pytest.main(sys.argv[1:]))
