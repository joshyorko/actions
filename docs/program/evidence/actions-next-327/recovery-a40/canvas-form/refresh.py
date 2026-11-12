import subprocess
raise SystemExit(subprocess.call(['npm','ci','--no-audit','--no-fund'],cwd='/workspace/actions/action_server/frontend'))
