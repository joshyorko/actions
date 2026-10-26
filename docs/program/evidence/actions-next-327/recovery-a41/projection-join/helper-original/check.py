import os,sys,subprocess
from pathlib import Path
root=Path('/workspace/actions-generic-projection/action_server')
os.chdir(root)
paths=['src/actions/server/foundry/generic_projection.py','tests/contract_tests/test_generic_projection.py']
mode=sys.argv[1]
if mode=='format':
 for command in [['ruff','check','--fix',*paths],['ruff','format',*paths],['isort',*paths]]:
  subprocess.run(command,check=True)
elif mode=='check':
 for command in [['ruff','check',*paths],['ruff','format','--check',*paths],['isort','--check',*paths],['mypy','--follow-imports=silent','--show-column-numbers','--namespace-packages','--explicit-package-bases',*paths[:1]]]:
  subprocess.run(command,check=True)
