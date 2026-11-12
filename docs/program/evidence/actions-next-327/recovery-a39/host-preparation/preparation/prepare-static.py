import os,subprocess,sys
from pathlib import Path
root=Path('/workspace/actions-knowledge-prepare/action_server')
os.chdir(root)
os.environ['MYPYPATH']=str(root/'src')
files=['src/actions/server/data_queries/knowledge_execution.py','tests/action_server_tests/test_knowledge_preparation.py']
for cmd in ([sys.executable,'-m','isort',*files],[sys.executable,'-m','ruff','format',*files],[sys.executable,'-m','ruff','check',*files],[sys.executable,'-m','mypy','--explicit-package-bases','--follow-imports=silent',files[0]]):
 print('COMMAND',cmd,flush=True)
 subprocess.run(cmd,check=True)
