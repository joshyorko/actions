from pathlib import Path
import toolkit
root = toolkit.REPOSITORY_ROOT
assert root == Path("/workspace/engineering/runtime-checkout-eol")
toolkit.poetry(
    "action_server", "run", "python", "-m", "pytest", "-n", "0", "-q",
    "tests/action_server_tests/test_shutdown_response_order.py",
    "--junitxml=/workspace/engineering/pr312-shutdown-response-order-source/original-RED-junit.xml",
)
