import subprocess
from pathlib import Path
root=Path('/workspace/actions/action_server/frontend')
files=['apps/canvas-view/src/semantic-renderer/generic-execution.ts','apps/canvas-view/src/semantic-renderer/generic-view.tsx','apps/canvas-view/vitest.config.ts','apps/canvas-view/src/semantic-renderer/generic-projection-join.test.ts']
subprocess.run(['npx','--no-install','prettier','--write',*files],cwd=root,check=True)
subprocess.run(['npm','run','test:canvas','--','--reporter=default','--reporter=junit','--outputFile=/workspace/actions-327-a40/canvas-v2-import/final-tests.xml'],cwd=root,check=True)
subprocess.run(['npm','run','test:types'],cwd=root,check=True)
