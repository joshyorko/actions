import os
import subprocess
from pathlib import Path
import toolkit

root = toolkit.REPOSITORY_ROOT
assert root == Path('/workspace/engineering/pr300')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip() == '7840057a8b055576d11d339d8c0fbb738927a491'
assert subprocess.check_output(['git','status','--porcelain'],cwd=root) == b''
os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS'] = '2'
toolkit.poetry('action_server', 'run', 'invoke', 'test-not-integration')
