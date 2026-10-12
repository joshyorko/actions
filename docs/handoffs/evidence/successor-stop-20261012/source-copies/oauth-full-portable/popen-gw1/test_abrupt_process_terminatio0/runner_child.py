
import importlib.util
import os
import sys
import threading
from pathlib import Path

runner_path = Path(os.environ["RUNNER_PATH"])
spec = importlib.util.spec_from_file_location("acceptance_runner", runner_path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
sys.argv = [
    "acceptance",
    "--frozen", os.environ["FROZEN"],
    "--go-wrapper", os.environ["WRAPPER"],
    "--rcc-home", os.environ["RCC_HOME"],
    "--receipt", os.environ["RECEIPT"],
    "--source-sha", "a" * 40,
    "--build-version", "test",
]

class BlockingPytest:
    def main(self, args, plugins):
        Path(os.environ["PYTEST_ENTERED"]).write_text("entered", encoding="utf-8")
        threading.Event().wait()

sys.modules["pytest"] = BlockingPytest()
runner.main()
