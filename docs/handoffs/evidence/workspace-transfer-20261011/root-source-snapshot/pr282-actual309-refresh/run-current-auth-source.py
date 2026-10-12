import toolkit
toolkit.poetry("action_server","run","python","-m","pytest","-q","tests/action_server_tests/test_auth_route_inventory.py","tests/action_server_tests/test_auth_route_enforcement.py")
