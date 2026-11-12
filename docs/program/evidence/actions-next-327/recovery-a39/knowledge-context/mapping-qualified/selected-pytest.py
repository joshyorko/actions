"""Retain exact selected nodes; guard pytest entry for multiprocessing spawn."""
import json
import os
import sys
from pathlib import Path

import pytest


class Inventory:
    def pytest_collection_finish(self, session):
        Path(os.environ["ACTIONS_SELECTED_INVENTORY"]).write_text(
            json.dumps([item.nodeid for item in session.items], indent=2) + "\n"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main(sys.argv[1:], plugins=[Inventory()]))
