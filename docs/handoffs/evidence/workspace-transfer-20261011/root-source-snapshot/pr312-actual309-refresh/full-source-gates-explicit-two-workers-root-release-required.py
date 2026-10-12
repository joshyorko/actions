import os

import toolkit

# HELD: run only on distinct root serialization/capacity release.
# Runtime's configured pytest -n auto reads this inherited xdist setting.
os.environ["PYTEST_XDIST_AUTO_NUM_WORKERS"] = "2"
toolkit.poetry("devutils", "run", "python", "-m", "pytest", "-q", "tests", "-n", "2")
toolkit.poetry("action_server", "run", "invoke", "test-not-integration")
