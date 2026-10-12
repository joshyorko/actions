import toolkit
toolkit.poetry("action_server", "run", "python", "-m", "pytest", "-q", "tests/action_server_tests/test_dakota_rcc_acceptance.py", "tests/action_server_tests/test_rcc_runtime_adapter.py", "tests/action_server_tests/test_source_staging_rcc_consumer.py", "-m", "not integration_test")
toolkit.poetry("action_server", "run", "invoke", "lint", "typecheck")
