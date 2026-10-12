from pathlib import Path
import subprocess
import toolkit
assert toolkit.REPOSITORY_ROOT==Path("/workspace/engineering/pr308")
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=toolkit.REPOSITORY_ROOT).decode().strip()=="c10380a4d2ebc6f0aca63eb85c8f84a337da4962"
assert subprocess.check_output(["git","status","--porcelain"],cwd=toolkit.REPOSITORY_ROOT)==b""
toolkit.poetry("action_server", "run", "python", "-m", "pytest", "-q", "tests/action_server_tests/test_dakota_rcc_acceptance.py", "tests/action_server_tests/test_rcc_runtime_adapter.py", "tests/action_server_tests/test_source_staging_rcc_consumer.py", "-m", "not integration_test")
toolkit.poetry("action_server", "run", "invoke", "lint", "typecheck")
