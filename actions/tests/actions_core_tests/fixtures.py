from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture(scope="session")
def resources_dir():
    resources = Path(__file__).parent / "resources"
    assert resources.exists()
    return resources


@pytest.fixture(autouse=True)
def _reset_collected_actions() -> Iterator[None]:
    from actions._collect_actions import clear_previously_collected_actions

    clear_previously_collected_actions()
    yield
    clear_previously_collected_actions()
