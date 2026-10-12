import hashlib
from pathlib import Path
import toolkit
base=Path('/workspace/engineering/pr221-current618-linux-consumer-preflight')
files=[str(base/name) for name in ['current-input-admission-v3.py','installed-consumer-runner-v3.py','test_current_input_admission.py','test_installed_consumer_runner_v3.py']]
toolkit.poetry('action_server','run','ruff','format',*files)
toolkit.poetry('action_server','run','isort',*files)
# Bind the exact configured-format input gate before actual source-byte controls.
gate=base/'current-input-admission-v3.py';runner=base/'installed-consumer-runner-v3.py';expected='7474e6fae0e8d8d8211bfc9376697dcd14546b9c1a4ea5925c4042786720ea25';actual=hashlib.sha256(gate.read_bytes()).hexdigest();s=runner.read_text();assert expected in s;runner.write_text(s.replace(expected,actual))
toolkit.poetry('action_server','run','ruff','check',*files)
toolkit.poetry('action_server','run','ruff','format','--check',*files)
toolkit.poetry('action_server','run','isort','--check',*files)
toolkit.poetry('action_server','run','python','-m','pytest','-c','/workspace/engineering/pr282/action_server/pyproject.toml','-q',files[2],files[3])
