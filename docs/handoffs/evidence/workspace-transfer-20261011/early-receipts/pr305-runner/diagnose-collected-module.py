import json
import sys
from pathlib import Path
sys.path.insert(0, '/workspace/engineering/pr305/action_server/tests')
import pytest
from action_server_tests.mcp import test_mcp_apps_authoring as preimport
preimport.CANVAS_OWNED_RUNNER = lambda *args, **kwargs: None
class Inspection:
    def pytest_collection_finish(self, session):
        items=[]
        for item in session.items:
            module=item.module
            items.append(dict(nodeid=item.nodeid, collected_module=module.__name__, collected_file=module.__file__, preimport_module=preimport.__name__, same_object=module is preimport, preimport_hook_callable=callable(preimport.CANVAS_OWNED_RUNNER), collected_hook_callable=callable(module.CANVAS_OWNED_RUNNER)))
        Path('/workspace/actions-cloud/receipts/pr305-runner/collected-module-diagnosis.json').write_text(json.dumps({'phase':'COLLECTION_ONLY_NO_TEST_EXECUTION','items':items},indent=2)+'\n')
raise SystemExit(pytest.main(['tests/action_server_tests/mcp/test_mcp_apps_authoring.py::test_canvas_view_calls_public_action_through_runtime_bridge','--collect-only','-q','-n0'],plugins=[Inspection()]))
