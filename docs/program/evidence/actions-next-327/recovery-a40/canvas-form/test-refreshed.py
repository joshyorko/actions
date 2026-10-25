import subprocess
from pathlib import Path
root=Path('/workspace/actions/action_server/frontend')
raise SystemExit(subprocess.call(['npm','run','test:canvas','--','--reporter=default','--reporter=junit','--outputFile=/workspace/actions-327-a40/canvas-form/tests-refreshed.xml'],cwd=root))
