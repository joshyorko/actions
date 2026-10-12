import toolkit
toolkit.poetry("action_server", "run", "python", "-m", "pytest", "-q", "tests/action_server_tests/test_auth_route_inventory.py", "tests/action_server_tests/test_server_cors.py", "tests/action_server_tests/test_browser_session.py", "tests/action_server_tests/test_server.py::test_configured_api_key_rejects_before_body_receive", "-m", "not integration_test")
