from pathlib import Path
import os, runpy
import toolkit
assert toolkit.REPOSITORY_ROOT == Path("/workspace/engineering/pr308")
assert os.environ["ROBOCORP_HOME"] == "/workspace/actions-cloud/robocorp"
os.environ["ACTIONS_RUNTIME_TEST_PYTHON"] = str(toolkit.REPOSITORY_ROOT / "action_server/.venv/bin/python")
files=["src/actions/server/_rcc_runtime_adapter.py", "tests/action_server_tests/test_rcc_runtime_adapter.py", "tests/action_server_tests/test_dakota_rcc_acceptance.py", "tests/action_server_tests/test_source_staging_rcc_consumer.py"]
toolkit.poetry("action_server", "run", "isort", *files)
toolkit.poetry("action_server", "run", "ruff", "format", "--config", "../devutils/ruff.toml", *files)
toolkit.poetry("action_server", "run", "python", "-m", "pytest", "-n0", "-q", "tests/action_server_tests/test_rcc_runtime_adapter.py", "tests/action_server_tests/test_dakota_rcc_acceptance.py", "tests/action_server_tests/test_source_staging_rcc_consumer.py", "-m", "not integration_test", "--tb=short")
toolkit.poetry("action_server", "run", "invoke", "lint")
toolkit.poetry("action_server", "run", "invoke", "typecheck")
toolkit.poetry("action_server", "run", "ruff", "check", "--config", "../devutils/ruff.toml", "scripts/verify_dakota_rcc_acceptance.py")
toolkit.toolkit_test()
runpy.run_path("/workspace/engineering/pr308-rcc-compatibility-source/generator-derived-roundtrip-current-compatibility.py", run_name="__main__")
