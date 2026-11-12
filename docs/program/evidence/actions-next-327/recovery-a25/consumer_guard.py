import json,sys
from pathlib import Path
import pytest
EXPECTED=Path('/workspace/actions-recovery-327/installed-a25/consumer')
def pytest_sessionstart(session):
 assert Path(sys.prefix)==EXPECTED
 import actions.server,actions.mcp,actions.work_items
 for m in (actions.server,actions.mcp,actions.work_items):assert Path(m.__file__).is_relative_to(EXPECTED),m.__file__
def pytest_sessionfinish(session,exitstatus):
 wrong=[]
 for name,module in tuple(sys.modules.items()):
  path=getattr(module,'__file__',None)
  if name.startswith(('actions.server','actions.mcp','actions.work_items')) and path and not Path(path).is_relative_to(EXPECTED):wrong.append((name,path))
 if wrong:raise AssertionError(wrong)
