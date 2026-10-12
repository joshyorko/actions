import toolkit
toolkit.poetry("action_server", "run", "python", "-m", "pytest", "-q", "tests/action_server_tests/mcp/test_canvas_runtime_admission.py", "tests/action_server_tests/test_browser_origin_acceptance.py", "-m", "not integration_test", "-n", "0")
