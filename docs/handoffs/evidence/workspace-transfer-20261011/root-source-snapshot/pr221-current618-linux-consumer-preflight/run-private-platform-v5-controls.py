from pathlib import Path
import toolkit
base = Path('/workspace/engineering/pr221-current618-linux-consumer-preflight')
files = [str(base / name) for name in ['installed-consumer-runner-v5.py', 'test_current_input_admission_v5.py', 'test_installed_consumer_runner_v5.py', 'test_current_input_provenance_v5.py', 'test_platform_input_directory_v5.py']]
# Only named v5 files may be formatted; all immutable v3/v4 inputs/helpers stay untouched.
toolkit.poetry('action_server', 'run', 'ruff', 'format', *files)
toolkit.poetry('action_server', 'run', 'isort', *files)
toolkit.poetry('action_server', 'run', 'ruff', 'check', *files)
toolkit.poetry('action_server', 'run', 'ruff', 'format', '--check', *files)
toolkit.poetry('action_server', 'run', 'isort', '--check', *files)
toolkit.poetry('action_server', 'run', 'python', '-m', 'pytest', '-c', str(toolkit.REPOSITORY_ROOT / 'action_server/pyproject.toml'), '-q', *files[1:])
