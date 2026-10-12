import os
import subprocess
from pathlib import Path
import toolkit

root = toolkit.REPOSITORY_ROOT
assert root == Path('/workspace/engineering/pr306')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip() == 'fada8e068f61f6e0e380ec4685eed2f4cf0b9ade'
assert subprocess.check_output(['git','status','--porcelain'],cwd=root) == b''
os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS'] = '2'
toolkit.poetry('action_server', 'run', 'invoke', 'test-not-integration')
