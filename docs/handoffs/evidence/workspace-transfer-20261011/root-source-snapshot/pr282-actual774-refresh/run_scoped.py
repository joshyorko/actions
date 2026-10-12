import toolkit
toolkit.poetry("action_server", "run", "python", "-m", "pytest", "-q", "tests/contract_tests/test_source_staging.py", "tests/contract_tests/test_source_read.py")
toolkit.poetry("action_server", "run", "python", "-m", "pytest", "-q", "tests/contract_tests/test_source_staging.py", "-k", "staged_bytes_are_rechecked or constant_timestamp or metadata_change_after_read")
