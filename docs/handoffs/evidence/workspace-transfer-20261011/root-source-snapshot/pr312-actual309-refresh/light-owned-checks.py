import runpy
from pathlib import Path
import toolkit
o=Path("/workspace/engineering/pr312-actual309-refresh")
for name in ["verify-own-prepared.py","verify-retained-native-helper-browser-pre-full.py","verify-retained-V5-raw-and-driver-pre-full.py","run-owned-scoped-checks.py"]:
 runpy.run_path(str(o/name),run_name="__main__")
toolkit.poetry("action_server","run","python","-m","pytest","-q","tests/action_server_tests/test_auth_route_inventory.py","tests/action_server_tests/test_auth_route_enforcement.py")
toolkit.poetry("action_server","run","invoke","lint","typecheck")
runpy.run_path(str(o/"generator-all-eight-roundtrip.py"),run_name="__main__")
