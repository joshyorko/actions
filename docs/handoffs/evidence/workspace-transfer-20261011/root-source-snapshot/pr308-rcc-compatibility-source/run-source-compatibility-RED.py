from pathlib import Path
import os
import toolkit

assert toolkit.REPOSITORY_ROOT == Path("/workspace/engineering/pr308")
assert os.environ["ROBOCORP_HOME"] == "/workspace/actions-cloud/robocorp"
os.environ["ACTIONS_RUNTIME_TEST_PYTHON"] = str(toolkit.REPOSITORY_ROOT / "action_server/.venv/bin/python")
toolkit.poetry("action_server", "run", "python", "-m", "pytest", "-n0", "-q", "tests/action_server_tests/test_rcc_runtime_adapter.py", "tests/action_server_tests/test_dakota_rcc_acceptance.py", "tests/action_server_tests/test_source_staging_rcc_consumer.py", "-k", "approved_test_only_rcc5 or unapproved_test_selector or test_only_version_rejection or descriptor_co_mutated or new_selected_binary or new_descriptor_exec or selected_binary_partitions or wrong_binary_or_platform or approved_test_tuples or changed_approved_binary or compatibility_descriptor_namespace or public_harness_uses_shared or public_harness_rejects_pending or staging_fixture_admission or staging_fixture_default", "--tb=short")
