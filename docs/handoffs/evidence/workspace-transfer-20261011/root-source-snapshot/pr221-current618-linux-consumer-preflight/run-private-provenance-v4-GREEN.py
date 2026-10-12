import hashlib
from pathlib import Path
import toolkit
base=Path('/workspace/engineering/pr221-current618-linux-consumer-preflight')
files=[str(base/name) for name in ['current-input-admission-v4.py','installed-consumer-runner-v4.py','test_current_input_admission_v4.py','test_installed_consumer_runner_v4.py','test_current_input_provenance_v4.py']]
gate=base/'current-input-admission-v4.py';before=hashlib.sha256(gate.read_bytes()).hexdigest()
toolkit.poetry('action_server','run','ruff','format',*files)
toolkit.poetry('action_server','run','isort',*files)
runner=base/'installed-consumer-runner-v4.py';body=runner.read_text();assert before in body;runner.write_text(body.replace(before,hashlib.sha256(gate.read_bytes()).hexdigest()))
toolkit.poetry('action_server','run','ruff','check',*files)
toolkit.poetry('action_server','run','ruff','format','--check',*files)
toolkit.poetry('action_server','run','isort','--check',*files)
toolkit.poetry('action_server','run','python','-m','pytest','-c','/workspace/engineering/pr282/action_server/pyproject.toml','-q',*files[2:])
