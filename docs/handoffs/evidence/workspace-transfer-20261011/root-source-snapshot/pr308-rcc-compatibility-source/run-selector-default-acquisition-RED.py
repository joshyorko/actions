import toolkit
toolkit.poetry("action_server", "run", "python", "-m", "pytest", "-n0", "-q", "tests/action_server_tests/test_rcc_runtime_adapter.py", "-k", "requires_explicit_binary", "--tb=short")
