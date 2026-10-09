"""Keep the repository's community execution-graph validator in ToolkitTest."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_community_execution_graph_regressions_and_projection() -> None:
    subprocess.run(
        [sys.executable, "scripts/test_project_community_execution_graph.py"],
        cwd=REPOSITORY_ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, "scripts/project_community_execution_graph.py", "--check"],
        cwd=REPOSITORY_ROOT,
        check=True,
    )
