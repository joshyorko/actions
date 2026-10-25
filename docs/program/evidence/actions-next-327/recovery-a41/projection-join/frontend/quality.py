import subprocess
raise SystemExit(subprocess.call(['npm','run','test:quality'],cwd='/workspace/actions/action_server/frontend'))
