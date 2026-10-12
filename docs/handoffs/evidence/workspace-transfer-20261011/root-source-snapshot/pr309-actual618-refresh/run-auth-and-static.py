import toolkit
from pathlib import Path
import json
# Exact standalone73cases plus broader registration/browser/denial/sourcecontrols.
toolkit.poetry("action_server","run","python","-m","pytest","-n","0","-vv","tests/action_server_tests/test_auth_route_enforcement.py","--junitxml",'/workspace/engineering/pr309-actual618-refresh/auth73-junit.xml')
toolkit.poetry("action_server","run","python","-m","pytest","-n","0","-q","-m","not integration_test and not real_rcc","tests/action_server_tests/test_auth_route_enforcement.py","tests/action_server_tests/test_auth_route_inventory.py","tests/action_server_tests/test_browser_session.py","tests/action_server_tests/test_artifact_storage.py","tests/action_server_tests/test_server.py::test_configured_api_key_rejects_before_body_receive","tests/action_server_tests/test_rcc_runtime_adapter.py","tests/action_server_tests/test_source_staging_rcc_consumer.py")
toolkit.poetry("action_server","run","invoke","lint","typecheck")
