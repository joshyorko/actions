import os
import subprocess
from pathlib import Path
import toolkit

root = toolkit.REPOSITORY_ROOT
assert root == Path('/workspace/engineering/pr308')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip() == 'c10380a4d2ebc6f0aca63eb85c8f84a337da4962'
assert subprocess.check_output(['git','status','--porcelain'],cwd=root) == b''
os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS'] = '2'
toolkit.poetry('action_server', 'run', 'invoke', 'test-not-integration')
