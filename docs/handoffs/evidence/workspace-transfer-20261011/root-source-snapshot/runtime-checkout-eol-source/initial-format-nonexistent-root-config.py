import toolkit
from pathlib import Path
r=toolkit.REPOSITORY_ROOT
files=[str(r/"devutils/tests/test_runtime_checkout_bytes.py"),str(r/"devutils/tests/test_runtime_release_workflows.py")]
toolkit.poetry("devutils","run","ruff","format","--config",str(r/"ruff.toml"),*files)
toolkit.poetry("devutils","run","isort",*files)
