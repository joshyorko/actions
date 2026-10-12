import runpy
from pathlib import Path
import toolkit
out=Path("/workspace/engineering/pr312-shutdown-response-order-source")
toolkit.doctor()
runpy.run_path(str(out/"current-verify-own-prepared.py"),run_name="__main__")
toolkit.toolkit_test()
toolkit.poetry("action_server","run","python","-m","pytest","-n","0","-q","tests/action_server_tests/test_shutdown_response_order.py","tests/action_server_tests/test_auth_route_inventory.py","tests/action_server_tests/test_auth_route_enforcement.py","--junitxml="+str(out/"final-scoped-junit.xml"))
toolkit.poetry("devutils","run","python","-m","pytest","-n","0","-q","tests/test_runtime_checkout_bytes.py","tests/test_runtime_checkout_workflows.py","-k","RuntimeCheckoutBytesTests or runtime_checkout")
toolkit.poetry("action_server","run","invoke","lint","typecheck")
runpy.run_path(str(out/"current-generator-all-eight-roundtrip.py"),run_name="__main__")
print("PURE_CACHED_SHUTDOWN_LIGHT_ALL_PASS",flush=True)
