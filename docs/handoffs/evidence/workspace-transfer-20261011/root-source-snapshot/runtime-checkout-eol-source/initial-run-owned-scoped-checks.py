import toolkit
from pathlib import Path
r=toolkit.REPOSITORY_ROOT
files=["tests/test_runtime_checkout_bytes.py","tests/test_runtime_release_workflows.py"]
toolkit.poetry("devutils","run","python","-m","pytest","-q",*files,"-k","RuntimeCheckoutBytesTests or runtime_checkout")
toolkit.poetry("devutils","run","ruff","check",*files)
toolkit.poetry("devutils","run","ruff","format","--check","--config",str(r/"devutils/ruff.toml"),*files)
toolkit.poetry("devutils","run","isort","--check",*files)
toolkit.poetry("action_server","run","invoke","lint","typecheck")
