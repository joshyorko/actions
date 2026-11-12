import os,sys,subprocess
from pathlib import Path
root=Path('/workspace/actions-knowledge-host/action_server')
os.chdir(root)
paths=['src/actions/server/foundry/provider_config.py','src/actions/server/foundry/provider_catalog.py','src/actions/server/foundry/provider_execution.py','src/actions/server/foundry/knowledge_host.py','src/actions/server/_local_provider_setup.py','tests/action_server_tests/test_knowledge_host.py','tests/action_server_tests/test_knowledge_host_postgres.py']
mode=sys.argv[1]
if mode=='format':
 for command in [['ruff','check','--fix',*paths],['ruff','format',*paths],['isort',*paths]]:
  subprocess.run(command,check=True)
elif mode=='check':
 for command in [['ruff','check',*paths],['ruff','format','--check',*paths],['isort','--check',*paths],['mypy','--follow-imports=silent','--show-column-numbers','--namespace-packages','--explicit-package-bases',*paths[:5]]]:
  subprocess.run(command,check=True)
